#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path


PYTHON_CANDIDATES = ["python", "python3"]
REQUIRED_CORE_BINARIES = ["git", "rg"]
REQUIRED_SKILL_FILES = [
    "SKILL.md",
    "references/reviewer_prompt.md",
    "references/consensus_prompt.md",
    "references/storage_layout.md",
    "references/setup_cross_platform.md",
    "scripts/init_review_run.py",
    "scripts/manage_project_rules.py",
    "scripts/run_review_cycle.py",
    "scripts/set_run_state.py",
    "scripts/validate_cycle_outputs.py",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preflight check for parallel-consensus-code-review skill."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root for _code_reviews_ai checks.",
    )
    parser.add_argument(
        "--check-auth",
        action="store_true",
        help="Run a lightweight Codex auth probe using codex-wrapper.",
    )
    return parser.parse_args()


def _kill_tree(proc: subprocess.Popen, grace: float = 5.0) -> None:
    """Force-kill a child process and its whole descendant tree, cross-platform.

    A plain ``subprocess.run(timeout=...)`` only kills the direct child; on Windows
    ``codex`` is a ``.CMD`` shim (cmd.exe -> node -> codex.exe), and the orphaned
    grandchildren keep the captured pipes open so the post-timeout drain blocks
    forever. We must tear down the entire tree.
    """
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=max(5.0, float(grace)),
            )
        else:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass


def run_cmd(cmd: list[str], timeout: int = 20) -> tuple[bool, str]:
    """Run a short probe command with a sleep-resistant timeout + tree teardown.

    Drains stdout/stderr in reader threads (so a full pipe can't deadlock) and on
    timeout hard-kills the whole process tree, then joins with a bounded wait so
    this never hangs the preflight even when codex spawns a multi-process tree.
    """
    kwargs: dict = dict(
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen(cmd, **kwargs)
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)

    out_chunks: list[str] = []
    err_chunks: list[str] = []

    def drain(pipe, sink: list[str]) -> None:
        try:
            for line in iter(pipe.readline, ""):
                if line == "":
                    break
                sink.append(line)
        except (OSError, ValueError):
            pass
        finally:
            try:
                pipe.close()
            except OSError:
                pass

    t_out = threading.Thread(target=drain, args=(proc.stdout, out_chunks), daemon=True)
    t_err = threading.Thread(target=drain, args=(proc.stderr, err_chunks), daemon=True)
    t_out.start()
    t_err.start()

    deadline = time.time() + max(1, int(timeout))
    timed_out = False
    while True:
        try:
            proc.wait(timeout=0.5)
            break
        except subprocess.TimeoutExpired:
            pass
        if time.time() >= deadline:
            timed_out = True
            break

    if timed_out:
        _kill_tree(proc)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    t_out.join(timeout=5)
    t_err.join(timeout=5)

    out = "".join(out_chunks).strip()
    err = "".join(err_chunks).strip()
    if timed_out:
        detail = out or err or ""
        msg = (detail + f"\ncommand timed out after {int(timeout)}s; process tree force-killed").strip()
        return False, msg
    text = out if out else err
    return proc.poll() == 0, text


def resolve_binary(name: str) -> str | None:
    return shutil.which(name)


def build_codex_wrapper_command(args: list[str]) -> list[str]:
    wrapper = resolve_binary("codex-wrapper")
    if not wrapper:
        return ["codex-wrapper", *args]
    path = Path(wrapper)
    if os.name == "nt" and path.suffix.lower() == ".ps1":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(path), *args]
    return [str(path), *args]


def build_codex_exec_command(project_root: Path, prompt: str) -> list[str]:
    codex = resolve_binary("codex") or "codex"
    return [codex, "exec", "--skip-git-repo-check", "-C", str(project_root), prompt]


def resolve_python() -> str | None:
    for name in PYTHON_CANDIDATES:
        path = resolve_binary(name)
        if path:
            return path
    return None


def check_binaries() -> tuple[list[str], str | None, str | None]:
    issues: list[str] = []
    python_path = resolve_python()
    if python_path is None:
        issues.append("missing binary: python (python or python3)")

    for name in REQUIRED_CORE_BINARIES:
        if resolve_binary(name) is None:
            issues.append(f"missing binary: {name}")

    transport = resolve_binary("codex-wrapper") or resolve_binary("codex")
    if transport is None:
        issues.append("missing Codex transport: install codex-wrapper or codex")
    return issues, python_path, transport


def check_skill_files(skill_root: Path) -> list[str]:
    issues: list[str] = []
    for rel in REQUIRED_SKILL_FILES:
        if not (skill_root / rel).exists():
            issues.append(f"missing skill file: {rel}")
    return issues


def check_project_write(project_root: Path) -> list[str]:
    issues: list[str] = []
    target = project_root / "_code_reviews_ai"
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".preflight_probe"
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except Exception as exc:
        issues.append(f"cannot write under {target}: {exc}")
    return issues


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    skill_root = Path(__file__).resolve().parent.parent

    issues: list[str] = []
    warnings: list[str] = []
    bin_issues, python_path, transport = check_binaries()
    issues.extend(bin_issues)
    issues.extend(check_skill_files(skill_root))
    issues.extend(check_project_write(project_root))

    cmd_checks: list[tuple[str, bool, str]] = []
    wrapper_path = resolve_binary("codex-wrapper")
    codex_path = resolve_binary("codex")
    cmd_checks.append(
        (
            "codex-wrapper presence (optional)",
            (wrapper_path is not None) or (codex_path is not None),
            wrapper_path or "not found (using codex fallback if available)",
        )
    )
    cmd_checks.append(
        (
            "codex presence (optional)",
            (codex_path is not None) or (wrapper_path is not None),
            codex_path or "not found (using codex-wrapper fallback if available)",
        )
    )
    cmd_checks.append(("codex transport selected", transport is not None, transport or "none"))

    checks = [
        [python_path or "python", "--version"],
        ["git", "--version"],
        ["rg", "--version"],
    ]

    if codex_path:
        checks.append([codex_path, "--version"])

    for cmd in checks:
        ok, output = run_cmd(cmd, timeout=30)
        cmd_checks.append((" ".join(cmd), ok, output))
        if not ok:
            issues.append(f"command failed: {' '.join(cmd)}")

    git_repo_ok, git_repo_output = run_cmd(
        ["git", "-C", str(project_root), "rev-parse", "--is-inside-work-tree"],
        timeout=20,
    )
    if not (git_repo_ok and git_repo_output.strip().lower() == "true"):
        warnings.append(
            "project_root is not a Git work tree; provide explicit touched file list to avoid snapshot-wide reviews"
        )

    if args.check_auth and transport:
        if wrapper_path:
            auth_cmd = build_codex_wrapper_command(["Return only OK.", str(project_root)])
        else:
            auth_cmd = build_codex_exec_command(project_root, "Return only OK.")
        ok, output = run_cmd(auth_cmd, timeout=90)
        cmd_checks.append(("codex auth probe", ok, output))
        if not ok:
            issues.append("codex auth probe failed (run `codex login` in this same environment)")

    print("PRECHECK SUMMARY")
    print(f"project_root: {project_root}")
    print(f"skill_root: {skill_root}")
    print("")
    for cmd, ok, output in cmd_checks:
        status = "PASS" if ok else "FAIL"
        first_line = output.splitlines()[0] if output else ""
        print(f"[{status}] {cmd}")
        if first_line:
            print(f"  {first_line}")

    if issues:
        print("")
        print("PRECHECK: FAIL")
        for issue in issues:
            print(f"- {issue}")
        return 1

    if warnings:
        print("")
        print("PRECHECK: PASS (WITH WARNINGS)")
        for warning in warnings:
            print(f"- {warning}")
        return 0

    print("")
    print("PRECHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
