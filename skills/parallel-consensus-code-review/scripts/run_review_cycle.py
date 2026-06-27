#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_REVIEWERS = ["reviewer_01", "reviewer_02", "reviewer_03"]
REVIEWER_ID_RE = re.compile(r"^reviewer_[a-z0-9_]+$")
DEFAULT_BLOCKING_CLEAR_MARKERS = ["NO_NEW_BLOCKING_ISSUES", "NO_NEW_ISSUES"]
DEFAULT_BLOCKING_CLEAR_PHRASES = [
    "no new blocking issues",
    "no new blocking actionable issues",
    "no blocking findings",
    "no blocking finding",
    "no blocking, important, or minor defects found",
    "no blocking, important, or minor regressions found",
]
DEFAULT_SHOULD_FIX_PRIORITY_TAGS = [
    "important",
    "efficiency",
    "performance",
    "reliability",
    "security",
    "correctness",
]
STATUS_FIXED = {"fixed", "done", "closed", "resolved", "completed"}
STATUS_IN_PROGRESS = {"in_progress", "in-progress", "doing"}
STATUS_OPEN = {"open", "todo", "pending", "reopened", "reopen"}
STATUS_DEFERRED = {"deferred", "backlog", "wontfix", "won't fix", "postponed"}
BLIND_FIX_LOG_CONTEXT_TEXT = (
    "Independent first pass mode: historical fix-log context intentionally withheld "
    "to reduce anchoring bias. Judge only from current code evidence."
)
# Grace added on top of a per-reviewer timeout for the process-tree kill + pipe
# drain to settle before the next layer's bound takes over.
REVIEWER_KILL_GRACE_SECONDS = 30
# How often a running reviewer / the orchestrator emits a liveness heartbeat.
HEARTBEAT_INTERVAL_SECONDS = 30
# Hard bound for the post-run validator subprocess (pure-Python, file-only work;
# this is only a backstop against an unexpected wedge).
VALIDATION_TIMEOUT_SECONDS = 600


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run one review cycle with real process orchestration: isolated reviewer "
            "subprocesses in parallel (default team size 3), atomic output writes, and optional post-run validation."
        )
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument("--run-id", required=True, help="Run id under _code_reviews_ai.")
    parser.add_argument("--cycle-id", default="cycle_01", help="Cycle folder name.")
    parser.add_argument(
        "--reviewers",
        nargs="+",
        default=None,
        help=(
            "Reviewer ids to run in parallel. If omitted, use reviewers from cycle_meta.json "
            "(default initialized value is 3 reviewers)."
        ),
    )
    parser.add_argument(
        "--prompt-dir",
        type=Path,
        default=None,
        help="Directory containing reviewer prompt files. Defaults to cycle folder.",
    )
    parser.add_argument(
        "--reviewer-prompt",
        action="append",
        default=[],
        help=(
            "Override prompt path for a reviewer via reviewer_id=path. "
            "Repeat for multiple reviewers (for example: --reviewer-prompt reviewer_01=./r1.md)."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=900,
        help="Per-reviewer timeout in seconds (default: 900).",
    )
    parser.add_argument(
        "--max-empty-retries",
        type=int,
        default=1,
        help="Automatic retries when stdout is empty (default: 1).",
    )
    parser.add_argument(
        "--parallelism",
        type=int,
        default=3,
        help="Parallel worker count (default: 3).",
    )
    parser.add_argument(
        "--global-timeout-seconds",
        type=int,
        default=None,
        help=(
            "Hard ceiling for the whole reviewer cycle so a single wedged reviewer can never "
            "hang the run forever. Default: derived from per-reviewer timeout x attempts x waves."
        ),
    )
    parser.add_argument(
        "--transport",
        choices=["auto", "codex-wrapper", "codex", "mock"],
        default="auto",
        help="Reviewer backend transport (default: auto).",
    )
    parser.add_argument(
        "--pythonpath-mode",
        choices=["append", "replace"],
        default="append",
        help="How to set PYTHONPATH for reviewer subprocesses (default: append).",
    )
    parser.add_argument(
        "--review-mode",
        choices=["full", "low_overhead"],
        default="full",
        help="Review mode marker passed to subprocess env (default: full).",
    )
    parser.add_argument(
        "--review-query-file",
        type=Path,
        default=None,
        help="File containing user review query/objective. Defaults to <run>/inputs/review_query.md.",
    )
    parser.add_argument(
        "--audit-items-file",
        type=Path,
        default=None,
        help="File containing required audit checklist items. Defaults to <run>/inputs/audit_items.md.",
    )
    parser.add_argument(
        "--changed-files-file",
        type=Path,
        default=None,
        help="Optional changed-file list (one path per line). Defaults to <run>/inputs/changed_files.txt.",
    )
    parser.add_argument(
        "--context-notes-file",
        type=Path,
        default=None,
        help="Optional context notes file. Defaults to <run>/inputs/context_notes.md.",
    )
    parser.add_argument(
        "--project-rules-file",
        type=Path,
        default=None,
        help=(
            "Project-level review rules file. Defaults to "
            "<project>/_code_reviews_ai/project_review_rules.json."
        ),
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Optional override forwarded to validate_cycle_outputs.py.",
    )
    parser.add_argument(
        "--permission-confirm-after",
        type=int,
        default=None,
        help="Optional override forwarded to validate_cycle_outputs.py.",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip post-run validate_cycle_outputs.py call.",
    )
    parser.add_argument(
        "--force-recheck",
        action="store_true",
        help="Forward --force-recheck to validate_cycle_outputs.py.",
    )
    parser.add_argument(
        "--validate-script",
        type=Path,
        default=None,
        help="Path to validate_cycle_outputs.py. Defaults to sibling script.",
    )
    parser.add_argument(
        "--mock-empty-reviewers",
        nargs="*",
        default=[],
        help="Only for --transport mock: reviewers that should return empty stdout.",
    )
    parser.add_argument(
        "--mock-latency-ms",
        type=int,
        default=80,
        help="Only for --transport mock: synthetic latency per attempt (default: 80).",
    )
    parser.add_argument(
        "--lock-wait-seconds",
        type=int,
        default=30,
        help="Wait up to N seconds for a cycle lock before failing (default: 30).",
    )
    parser.add_argument(
        "--allow-non-active-run",
        action="store_true",
        help="Allow running a run that is not marked active in run_manifest/run_registry.",
    )
    parser.add_argument(
        "--preserve-review-outputs",
        dest="preserve_review_outputs",
        action="store_true",
        help="Do not clear previous review output/log files before executing this cycle.",
    )
    parser.add_argument(
        "--auto-close-on-no-new-issues",
        dest="auto_close_on_no_new_issues",
        action="store_true",
        default=True,
        help=(
            "Automatically close run when validator passes, blocking-clear marker threshold "
            "is met, and fix_log has no unresolved blocking issues."
        ),
    )
    parser.add_argument(
        "--no-auto-close-on-no-new-issues",
        dest="auto_close_on_no_new_issues",
        action="store_false",
        help="Disable automatic run closure after blocking-clear consensus.",
    )
    parser.add_argument(
        "--blocking-clear-marker",
        action="append",
        default=None,
        help=(
            "Marker meaning 'no new blocking issues' in reviewer reports. "
            "Repeatable; defaults to NO_NEW_BLOCKING_ISSUES and NO_NEW_ISSUES."
        ),
    )
    parser.add_argument(
        "--blocking-consensus-threshold",
        type=int,
        default=None,
        help=(
            "Minimum reviewer count that must include a blocking-clear marker for auto-close. "
            "Default: majority of current reviewers."
        ),
    )
    parser.add_argument(
        "--blocking-clear-phrase",
        action="append",
        default=None,
        help=(
            "Additional narrative phrase that indicates no new blocking issues in reviewer reports. "
            "Repeatable."
        ),
    )
    parser.add_argument(
        "--strict-marker-clear",
        action="store_true",
        help="Only explicit clear markers count for closure; disable narrative phrase fallback.",
    )
    parser.add_argument(
        "--blocking-should-fix-tag",
        action="append",
        default=None,
        help=(
            "Priority tags that make should_fix items blocking when present in fix_log severity/notes. "
            "Repeatable; default includes important, efficiency, performance, reliability, security, correctness."
        ),
    )
    parser.add_argument(
        "--inject-fix-log-context",
        action="store_true",
        help=(
            "Inject fix_log snapshot into reviewer prompts. Disabled by default to keep "
            "first-pass reviewers independent from historical anchoring."
        ),
    )
    return parser.parse_args()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(1, 7):
        tmp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
        try:
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(path)
            return
        except PermissionError as exc:
            last_error = exc
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            time.sleep(0.05 * attempt)
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise
    assert last_error is not None
    raise last_error


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(default)
    return raw if isinstance(raw, dict) else dict(default)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2) + "\n")


def read_text_or_default(path: Path, default: str) -> str:
    try:
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            return text if text else default
    except OSError:
        pass
    return default


def normalize_reviewer_id(value: str, *, context: str = "reviewer id") -> str:
    rid = str(value).strip().lower()
    if not REVIEWER_ID_RE.match(rid):
        raise SystemExit(
            f"invalid {context}: `{value}`. Expected pattern: reviewer_<letters_digits_underscores>."
        )
    return rid


def resolve_cycle_reviewers(cycle_meta_path: Path, cli_reviewers: list[str] | None) -> list[str]:
    if cli_reviewers:
        requested = cli_reviewers
    else:
        cycle_meta = read_json(
            cycle_meta_path,
            {
                "reviewers": DEFAULT_REVIEWERS,
            },
        )
        raw = cycle_meta.get("reviewers", DEFAULT_REVIEWERS)
        requested = raw if isinstance(raw, list) and raw else list(DEFAULT_REVIEWERS)

    reviewers: list[str] = []
    seen: set[str] = set()
    for reviewer in requested:
        rid = normalize_reviewer_id(str(reviewer))
        if rid in seen:
            continue
        seen.add(rid)
        reviewers.append(rid)
    if not reviewers:
        raise SystemExit("no reviewers resolved for this cycle")
    return reviewers


def parse_reviewer_prompt_overrides(raw_items: list[str]) -> dict[str, Path]:
    overrides: dict[str, Path] = {}
    for raw_item in raw_items:
        item = str(raw_item or "").strip()
        if not item:
            continue
        if "=" not in item:
            raise SystemExit(
                f"invalid --reviewer-prompt `{raw_item}`. Use reviewer_id=path format."
            )
        reviewer_raw, path_raw = item.split("=", 1)
        reviewer = normalize_reviewer_id(
            reviewer_raw,
            context="reviewer id in --reviewer-prompt",
        )
        prompt_path_text = path_raw.strip()
        if not prompt_path_text:
            raise SystemExit(
                f"invalid --reviewer-prompt `{raw_item}`. Prompt path is required."
            )
        if reviewer in overrides:
            raise SystemExit(f"duplicate --reviewer-prompt for reviewer `{reviewer}`")
        overrides[reviewer] = Path(prompt_path_text).expanduser().resolve()
    return overrides


def assert_active_run_or_fail(
    project_root: Path,
    run_root: Path,
    run_id: str,
    allow_non_active_run: bool,
) -> None:
    if allow_non_active_run:
        return

    manifest_path = run_root / "run_manifest.json"
    manifest = read_json(manifest_path, {})
    run_state = str(manifest.get("run_state", "active") or "active")
    if run_state != "active":
        raise SystemExit(
            f"run `{run_id}` is `{run_state}`. Use --allow-non-active-run only when user explicitly requests reopening archived/closed runs."
        )

    registry = read_json(project_root / "_code_reviews_ai" / "run_registry.json", {})
    active_run = str(registry.get("active_run_id", "") or "")
    if active_run and active_run != run_id:
        raise SystemExit(
            f"run `{run_id}` is not active (active run is `{active_run}`). "
            "Initialize a new run or use --allow-non-active-run with explicit user intent."
        )


def clear_review_outputs(cycle_dir: Path, reviewers: list[str]) -> None:
    static_files = [
        cycle_dir / "reviewer_run_summary.json",
        cycle_dir / "validation_exec.json",
        cycle_dir / "review_cycle.lock",
    ]
    for path in static_files:
        path.unlink(missing_ok=True)

    for reviewer in reviewers:
        for path in (
            cycle_dir / f"{reviewer}.md",
            cycle_dir / f"{reviewer}.stdout.log",
            cycle_dir / f"{reviewer}.stderr.log",
            cycle_dir / f"{reviewer}.exec.json",
        ):
            path.unlink(missing_ok=True)


def normalize_text_list(values: list[str] | None, default: list[str]) -> list[str]:
    if values is None:
        source = default
    else:
        source = values
    out: list[str] = []
    seen: set[str] = set()
    for item in source:
        text = str(item).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    if out:
        return out
    return list(default)


def resolve_blocking_consensus_threshold(reviewer_count: int, explicit: int | None) -> int:
    if reviewer_count < 1:
        return 1
    if explicit is None:
        return (reviewer_count // 2) + 1
    if explicit < 1:
        raise SystemExit("--blocking-consensus-threshold must be >= 1")
    if explicit > reviewer_count:
        raise SystemExit(
            f"--blocking-consensus-threshold ({explicit}) cannot exceed reviewer count ({reviewer_count})."
        )
    return explicit


def evaluate_blocking_clear_markers(
    cycle_dir: Path,
    reviewers: list[str],
    clear_markers: list[str],
    clear_phrases: list[str],
    strict_marker_clear: bool,
) -> dict[str, Any]:
    marker_map = {marker: marker.upper() for marker in clear_markers}
    phrase_map = {phrase: phrase.lower() for phrase in clear_phrases}
    details: list[dict[str, Any]] = []
    clear_count = 0
    for reviewer in reviewers:
        report_path = cycle_dir / f"{reviewer}.md"
        if not report_path.exists():
            details.append(
                {
                    "reviewer": reviewer,
                    "status": "missing_report",
                    "matched_markers": [],
                }
            )
            continue
        text = read_text_or_default(report_path, "")
        upper = text.upper()
        lower = text.lower()
        matched = [marker for marker, upper_marker in marker_map.items() if upper_marker in upper]
        matched_phrases = []
        if not strict_marker_clear:
            matched_phrases = [
                phrase
                for phrase, lower_phrase in phrase_map.items()
                if lower_phrase in lower
            ]
        if matched or matched_phrases:
            clear_count += 1
            details.append(
                {
                    "reviewer": reviewer,
                    "status": "clear",
                    "matched_markers": matched,
                    "matched_phrases": matched_phrases,
                }
            )
        else:
            details.append(
                {
                    "reviewer": reviewer,
                    "status": "has_blocking_or_unclear",
                    "matched_markers": [],
                    "matched_phrases": [],
                }
            )
    not_clear = [d["reviewer"] for d in details if d["status"] != "clear"]
    return {
        "clear_count": clear_count,
        "total_reviewers": len(reviewers),
        "not_clear_reviewers": not_clear,
        "details": details,
    }


def set_run_state(
    project_root: Path,
    run_root: Path,
    run_id: str,
    state: str,
    reason: str,
) -> None:
    manifest_path = run_root / "run_manifest.json"
    manifest = read_json(manifest_path, {})
    manifest["run_state"] = state
    manifest["state_reason"] = reason
    manifest["state_updated_at"] = datetime.now().isoformat(timespec="seconds")
    write_json(manifest_path, manifest)

    registry_path = project_root / "_code_reviews_ai" / "run_registry.json"
    registry = read_json(
        registry_path,
        {"active_run_id": "", "active_cycle_id": "", "updated_at": "", "runs": {}},
    )
    runs = registry.get("runs", {})
    if not isinstance(runs, dict):
        runs = {}
    run_entry = runs.get(run_id, {})
    if not isinstance(run_entry, dict):
        run_entry = {}
    run_entry["state"] = state
    run_entry["updated_at"] = datetime.now().isoformat(timespec="seconds")
    run_entry["reason"] = reason
    runs[run_id] = run_entry

    if state == "active":
        registry["active_run_id"] = run_id
    elif str(registry.get("active_run_id", "")) == run_id:
        registry["active_run_id"] = ""
        registry["active_cycle_id"] = ""
    registry["runs"] = runs
    registry["updated_at"] = datetime.now().isoformat(timespec="seconds")
    write_json(registry_path, registry)


def resolve_input_file(run_root: Path, candidate: Path | None, filename: str) -> Path:
    if candidate is not None:
        return candidate.resolve()
    return (run_root / "inputs" / filename).resolve()


def build_scope_context(
    scope_text: str,
    requirements_text: str,
    diff_range_text: str,
    changed_files_text: str,
    context_notes_text: str,
) -> str:
    blocks = [
        "Scope Summary:",
        scope_text,
        "",
        "Requirements Reference:",
        requirements_text,
        "",
        "Diff Range Signal:",
        diff_range_text,
        "",
        "Changed File Signal:",
        changed_files_text,
        "",
        "Context Notes:",
        context_notes_text,
    ]
    return "\n".join(blocks).strip()


def render_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    safe_headers = [str(h).strip() for h in headers]
    out = [
        "| " + " | ".join(safe_headers) + " |",
        "| " + " | ".join(["---"] * len(safe_headers)) + " |",
    ]
    for row in rows:
        cells = [str(cell).replace("\n", " ").strip() for cell in row]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def load_project_rules(
    project_root: Path,
    rules_file: Path | None,
) -> tuple[str, dict[str, Any]]:
    path = (
        rules_file.resolve()
        if rules_file is not None
        else (project_root / "_code_reviews_ai" / "project_review_rules.json").resolve()
    )
    meta: dict[str, Any] = {
        "path": str(path),
        "format": path.suffix.lower() or "unknown",
        "approved_count": 0,
        "pending_count": 0,
    }
    if not path.exists():
        return "No approved project-level review rules configured.", meta

    if path.suffix.lower() != ".json":
        text = read_text_or_default(path, "")
        if text:
            meta["approved_count"] = 1
            return text, meta
        return "No approved project-level review rules configured.", meta

    raw = read_json(path, {"rules": []})
    rules_raw = raw.get("rules", [])
    rules = rules_raw if isinstance(rules_raw, list) else []
    approved_lines: list[str] = []
    pending_count = 0
    for item in rules:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "") or "").strip()
        if not text:
            continue
        state = str(item.get("state", "pending") or "pending").strip().lower()
        rid = str(item.get("id", "") or "").strip()
        if state == "approved":
            prefix = f"[{rid}] " if rid else ""
            approved_lines.append(f"- {prefix}{text}")
        else:
            pending_count += 1
    meta["approved_count"] = len(approved_lines)
    meta["pending_count"] = pending_count
    if not approved_lines:
        return "No approved project-level review rules configured.", meta
    return "\n".join(approved_lines), meta


def parse_fix_log_entries(fix_log_path: Path) -> list[dict[str, str]]:
    text = read_text_or_default(fix_log_path, "")
    rows: list[dict[str, str]] = []
    header_map: dict[str, int] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue
        if all(not cell.replace("-", "").replace(":", "").strip() for cell in cells):
            continue

        cells_lower = [cell.lower() for cell in cells]
        if not header_map and "status" in cells_lower and ({"issue_id", "id"} & set(cells_lower)):
            for idx, name in enumerate(cells_lower):
                if name and name not in header_map:
                    header_map[name] = idx
            continue
        if cells_lower and (cells_lower[0] in {"issue_id", "id"}):
            continue

        if header_map:
            def pick(*aliases: str, fallback_idx: int = -1) -> str:
                for alias in aliases:
                    idx = header_map.get(alias)
                    if idx is not None and 0 <= idx < len(cells):
                        return cells[idx]
                if 0 <= fallback_idx < len(cells):
                    return cells[fallback_idx]
                return ""

            rows.append(
                {
                    "issue_id": pick("issue_id", "id", "issue", fallback_idx=0),
                    "severity": pick("severity", "class", "category", "priority", fallback_idx=1),
                    "status": pick("status", fallback_idx=2),
                    "owner": pick("owner", "assignee", fallback_idx=3),
                    "notes": pick("notes", "note", "details", "description", "comment", fallback_idx=4),
                }
            )
            continue

        if len(cells) >= 3:
            rows.append(
                {
                    "issue_id": cells[0],
                    "severity": cells[1] if len(cells) > 1 else "",
                    "status": cells[2] if len(cells) > 2 else "",
                    "owner": cells[3] if len(cells) > 3 else "",
                    "notes": cells[4] if len(cells) > 4 else "",
                }
            )
    return rows


def normalize_status(status: str) -> str:
    normalized = str(status).strip().lower().replace(" ", "_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized


def status_bucket(status: str) -> str:
    normalized = normalize_status(status)
    if normalized in STATUS_FIXED:
        return "fixed"
    if normalized in STATUS_IN_PROGRESS:
        return "in_progress"
    if normalized in STATUS_OPEN:
        return "open"
    if normalized in STATUS_DEFERRED:
        return "deferred"
    return "other"


def summarize_fix_status(entries: list[dict[str, str]]) -> dict[str, int]:
    counts = {
        "fixed": 0,
        "in_progress": 0,
        "open": 0,
        "deferred": 0,
        "other": 0,
    }
    for entry in entries:
        bucket = status_bucket(entry.get("status", ""))
        counts[bucket] += 1
    return counts


def is_blocking_issue(
    entry: dict[str, str],
    should_fix_priority_tags: list[str],
) -> bool:
    severity = str(entry.get("severity", "")).strip().lower()
    notes = str(entry.get("notes", "")).strip().lower()
    combined = f"{severity} {notes}".strip()
    if not combined:
        return False

    must_fix_markers = ("must_fix", "must-fix", "critical", "blocker")
    if any(marker in combined for marker in must_fix_markers):
        return True

    if "important" in combined and "minor" not in combined:
        return True

    if ("should_fix" in combined or "should-fix" in combined) and any(
        tag in combined for tag in should_fix_priority_tags
    ):
        return True

    return False


def summarize_blocking_fix_status(
    entries: list[dict[str, str]],
    should_fix_priority_tags: list[str],
) -> dict[str, int]:
    counts = {
        "blocking_fixed": 0,
        "blocking_in_progress": 0,
        "blocking_open": 0,
        "blocking_deferred": 0,
        "blocking_other": 0,
        "blocking_unresolved_total": 0,
        "blocking_reopened_unresolved": 0,
    }
    issue_history: dict[str, str] = {}
    for entry in entries:
        if not is_blocking_issue(entry, should_fix_priority_tags):
            continue
        issue_id = str(entry.get("issue_id", "")).strip().lower()
        bucket = status_bucket(entry.get("status", ""))
        key = f"blocking_{bucket}" if f"blocking_{bucket}" in counts else "blocking_other"
        counts[key] += 1
        unresolved = bucket != "fixed"
        if unresolved:
            counts["blocking_unresolved_total"] += 1

        if issue_id:
            previous_state = issue_history.get(issue_id, "")
            current_state = "resolved" if not unresolved else "unresolved"
            if previous_state == "resolved" and current_state == "unresolved":
                counts["blocking_reopened_unresolved"] += 1
            issue_history[issue_id] = current_state
    return counts


def parse_validation_kv(stdout_text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw_line in (stdout_text or "").splitlines():
        line = raw_line.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def write_cycle_summary(
    cycle_dir: Path,
    run_id: str,
    cycle_id: str,
    reviewers: list[str],
    results: list[dict[str, Any]],
    fix_status: dict[str, int],
    blocking_status: dict[str, int],
    rules_meta: dict[str, Any],
    validation_info: dict[str, str],
) -> None:
    reviewer_rows: list[list[str]] = []
    for item in results:
        attempts = item.get("attempts", [])
        reviewer_rows.append(
            [
                str(item.get("reviewer", "")),
                str(item.get("status", "")),
                str(len(attempts)),
                str(item.get("final_returncode", "")),
                str(item.get("final_empty_stdout", "")),
            ]
        )

    reviewer_table = render_markdown_table(
        ["reviewer", "status", "attempts", "final_returncode", "empty_stdout"],
        reviewer_rows or [["-", "-", "-", "-", "-"]],
    )
    fix_table = render_markdown_table(
        ["status", "count"],
        [[name, str(value)] for name, value in fix_status.items()],
    )
    blocking_table = render_markdown_table(
        ["metric", "count"],
        [[name, str(value)] for name, value in blocking_status.items()],
    )
    validation_table = render_markdown_table(
        ["key", "value"],
        [[k, v] for k, v in sorted(validation_info.items())] or [["status", "not_run"]],
    )
    rules_table = render_markdown_table(
        ["field", "value"],
        [
            ["path", str(rules_meta.get("path", "-"))],
            ["format", str(rules_meta.get("format", "-"))],
            ["approved_count", str(rules_meta.get("approved_count", 0))],
            ["pending_count", str(rules_meta.get("pending_count", 0))],
        ],
    )
    lines = [
        "# Cycle Summary",
        "",
        f"- run_id: {run_id}",
        f"- cycle_id: {cycle_id}",
        f"- reviewers: {', '.join(reviewers)}",
        "",
        "## Reviewer Execution",
        reviewer_table,
        "",
        "## Validation",
        validation_table,
        "",
        "## Issue Fix Status (from fix_log.md)",
        fix_table,
        "",
        "## Blocking Closure Status",
        blocking_table,
        "",
        "## Project Rules",
        rules_table,
        "",
    ]
    atomic_write_text(cycle_dir / "cycle_summary.md", "\n".join(lines))


def render_prompt_with_inputs(
    prompt_template: str,
    review_query: str,
    audit_items: str,
    scope_context: str,
    project_rules: str,
    fix_log_context: str,
) -> str:
    token_map = {
        "{{REVIEW_QUERY}}": review_query,
        "{{AUDIT_ITEMS}}": audit_items,
        "{{SCOPE_CONTEXT}}": scope_context,
        "{{PROJECT_RULES}}": project_rules,
        "{{FIX_LOG_CONTEXT}}": fix_log_context,
    }
    rendered = prompt_template
    found_tokens = False
    for token, value in token_map.items():
        if token in rendered:
            found_tokens = True
            rendered = rendered.replace(token, value)

    if found_tokens:
        return rendered

    # Backward-compatible fallback for legacy prompt templates without tokens.
    return (
        "## Review Inputs\n"
        f"### User Review Query\n{review_query}\n\n"
        f"### Audit Items\n{audit_items}\n\n"
        f"### Project-Level Approved Rules\n{project_rules}\n\n"
        f"### Fix Log Snapshot\n{fix_log_context}\n\n"
        f"### Scope Context\n{scope_context}\n\n"
        "## Reviewer Prompt\n"
        f"{rendered}"
    )


def resolve_binary(name: str) -> str | None:
    return shutil.which(name)


def resolve_transport(transport: str) -> tuple[str, str]:
    if transport == "mock":
        return "mock", "mock"

    wrapper = resolve_binary("codex-wrapper")
    codex = resolve_binary("codex")

    if transport == "auto":
        if wrapper:
            return "codex-wrapper", wrapper
        if codex:
            return "codex", codex
        raise RuntimeError("Neither codex-wrapper nor codex is available in PATH.")

    if transport == "codex-wrapper":
        if not wrapper:
            raise RuntimeError("Requested --transport codex-wrapper but codex-wrapper not found.")
        return "codex-wrapper", wrapper

    if transport == "codex":
        if not codex:
            raise RuntimeError("Requested --transport codex but codex not found.")
        return "codex", codex

    raise RuntimeError(f"Unsupported transport: {transport}")


def build_transport_cmd(
    transport_kind: str,
    transport_path: str,
    project_root: Path,
) -> list[str]:
    if transport_kind == "codex-wrapper":
        wrapper_path = Path(transport_path)
        if os.name == "nt" and wrapper_path.suffix.lower() == ".ps1":
            return [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(wrapper_path),
                "-",
                str(project_root),
            ]
        return [str(wrapper_path), "-", str(project_root)]

    if transport_kind == "codex":
        return [
            transport_path,
            "exec",
            "--skip-git-repo-check",
            "-C",
            str(project_root),
            "-",
        ]

    raise RuntimeError(f"Unsupported transport kind for command build: {transport_kind}")


def build_base_env(project_root: Path, pythonpath_mode: str, review_mode: str) -> dict[str, str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    if pythonpath_mode == "replace":
        env["PYTHONPATH"] = str(project_root)
    else:
        env["PYTHONPATH"] = (
            f"{project_root}{os.pathsep}{existing_pythonpath}"
            if existing_pythonpath
            else str(project_root)
        )
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PARALLEL_REVIEW_MODE"] = review_mode
    return env


def kill_process_tree(proc: subprocess.Popen, kill_grace_seconds: float = 10.0) -> None:
    """Hard-kill a child process AND its entire descendant tree, cross-platform.

    Why this exists: ``subprocess.run(timeout=...)`` only kills the *direct* child
    on timeout. On Windows the codex transport resolves to a ``.CMD`` shim, so the
    real tree is ``cmd.exe -> node -> codex.exe``. Killing only ``cmd.exe`` leaves
    the node/codex grandchildren alive holding the stdout/stderr pipe write-ends
    open, which deadlocks an unbounded ``communicate()`` drain forever. We must
    tear down the whole tree instead.
    """
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            # /T = terminate the whole child tree, /F = force.
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=max(5.0, float(kill_grace_seconds)),
            )
        else:
            # Child was started in its own session/group; kill the group.
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
    except Exception:
        pass
    # Best-effort direct kill as a fallback (covers taskkill miss / race).
    try:
        proc.kill()
    except Exception:
        pass


def _open_live_log(path: Path | None):
    """Open a per-attempt live log (truncating) for incremental streaming."""
    if path is None:
        return None
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        return open(path, "w", encoding="utf-8", errors="replace")
    except OSError:
        return None


def _drain_pipe(pipe, chunks: list[str], live_handle, live_lock: threading.Lock) -> None:
    """Reader-thread body: copy a child pipe into a buffer + (optional) live log.

    Draining in a dedicated thread guarantees the OS pipe buffer can never fill
    and deadlock the child, and that whatever the child emitted before a kill is
    still captured. Writing each line to the live log as it arrives gives the run
    a visible liveness signal instead of a 0-byte file.
    """
    try:
        for line in iter(pipe.readline, ""):
            if line == "":
                break
            chunks.append(line)
            if live_handle is not None:
                try:
                    with live_lock:
                        live_handle.write(line)
                        live_handle.flush()
                except (OSError, ValueError):
                    pass
    except (OSError, ValueError):
        pass
    finally:
        try:
            pipe.close()
        except OSError:
            pass


def _feed_stdin(stdin, data: str | None) -> None:
    """Writer-thread body: feed the prompt via stdin without risking a deadlock."""
    try:
        if data:
            stdin.write(data)
    except (OSError, ValueError):
        pass
    finally:
        try:
            stdin.close()
        except (OSError, ValueError):
            pass


def run_subprocess_resilient(
    cmd: list[str],
    *,
    timeout_seconds: int,
    input_text: str | None = None,
    cwd: Path | str | None = None,
    env: dict[str, str] | None = None,
    stdout_log_path: Path | None = None,
    stderr_log_path: Path | None = None,
    heartbeat_label: str | None = None,
    heartbeat_interval: float = HEARTBEAT_INTERVAL_SECONDS,
    kill_grace_seconds: float = REVIEWER_KILL_GRACE_SECONDS,
    poll_interval: float = 1.0,
) -> dict[str, Any]:
    """Run a child process with a sleep-resistant timeout and guaranteed teardown.

    Returns the same contract as the legacy path:
    ``{returncode, stdout, stderr, timed_out, command}`` with ``returncode=124``
    and ``timed_out=True`` on timeout. Never blocks unbounded: stdout/stderr are
    drained by reader threads, the timeout is a wall-clock deadline checked by a
    watchdog loop, on timeout the WHOLE process tree is force-killed, and every
    join after the kill is bounded.
    """
    popen_kwargs: dict[str, Any] = dict(
        cwd=str(cwd) if cwd is not None else None,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    # Put the child in its own group/session so we can kill the whole tree.
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **popen_kwargs)

    out_chunks: list[str] = []
    err_chunks: list[str] = []
    out_handle = _open_live_log(stdout_log_path)
    err_handle = _open_live_log(stderr_log_path)
    err_lock = threading.Lock()

    writer = threading.Thread(
        target=_feed_stdin, args=(proc.stdin, input_text), daemon=True
    )
    out_reader = threading.Thread(
        target=_drain_pipe, args=(proc.stdout, out_chunks, out_handle, threading.Lock()), daemon=True
    )
    err_reader = threading.Thread(
        target=_drain_pipe, args=(proc.stderr, err_chunks, err_handle, err_lock), daemon=True
    )
    writer.start()
    out_reader.start()
    err_reader.start()

    # Wall-clock deadline (time.time, not a single timer) so that a system suspend
    # which freezes the child is recognized on resume instead of silently
    # extending the wait. The poll loop wakes frequently to re-check the clock.
    start_wall = time.time()
    deadline = start_wall + max(1, int(timeout_seconds))
    next_heartbeat = start_wall + max(1.0, float(heartbeat_interval))
    timed_out = False
    while True:
        try:
            proc.wait(timeout=poll_interval)
            break  # process exited on its own
        except subprocess.TimeoutExpired:
            pass
        now = time.time()
        if now >= deadline:
            timed_out = True
            break
        if heartbeat_label and err_handle is not None and now >= next_heartbeat:
            elapsed = int(now - start_wall)
            line = (
                f"[heartbeat] {heartbeat_label} running — "
                f"{elapsed}s elapsed / {int(timeout_seconds)}s\n"
            )
            try:
                with err_lock:
                    err_handle.write(line)
                    err_handle.flush()
            except (OSError, ValueError):
                pass
            next_heartbeat = now + max(1.0, float(heartbeat_interval))

    if timed_out:
        kill_process_tree(proc, kill_grace_seconds=kill_grace_seconds)
        try:
            proc.wait(timeout=kill_grace_seconds)
        except subprocess.TimeoutExpired:
            pass

    # Bounded joins: after the tree is dead the pipes hit EOF and the readers
    # return immediately; the timeout guarantees we never block forever even if a
    # stray descendant somehow survived and still holds a pipe handle.
    writer.join(timeout=kill_grace_seconds)
    out_reader.join(timeout=kill_grace_seconds)
    err_reader.join(timeout=kill_grace_seconds)

    for handle in (out_handle, err_handle):
        if handle is not None:
            try:
                handle.close()
            except OSError:
                pass

    stdout_text = "".join(out_chunks)
    stderr_text = "".join(err_chunks)
    returncode = proc.poll()
    if returncode is None:
        returncode = -1

    if timed_out:
        return {
            "returncode": 124,
            "stdout": stdout_text,
            "stderr": stderr_text
            + f"\nreviewer subprocess timed out after {int(timeout_seconds)}s; "
            "process tree force-killed\n",
            "timed_out": True,
            "command": list(cmd),
        }
    return {
        "returncode": int(returncode),
        "stdout": stdout_text,
        "stderr": stderr_text,
        "timed_out": False,
        "command": list(cmd),
    }


def execute_reviewer_once(task: dict[str, Any]) -> dict[str, Any]:
    reviewer = task["reviewer"]
    prompt_text = task["prompt_text"]
    project_root = Path(task["project_root"])
    timeout_seconds = int(task["timeout_seconds"])
    transport_kind = task["transport_kind"]
    transport_path = task["transport_path"]
    mock_empty_reviewers = set(task.get("mock_empty_reviewers", []))
    mock_latency_ms = int(task.get("mock_latency_ms", 80))
    env = dict(task["env"])

    if transport_kind == "mock":
        time.sleep(max(0, mock_latency_ms) / 1000.0)
        if reviewer in mock_empty_reviewers:
            return {
                "returncode": 0,
                "stdout": "",
                "stderr": "mock: empty output requested for reviewer\n",
                "timed_out": False,
                "command": ["mock-runner"],
            }
        mock_out = (
            f"# {reviewer.replace('_', ' ').title()}\n\n"
            "## Strengths\n"
            "- Mock run generated a deterministic review output.\n\n"
            "## Issues by severity\n"
            "- minor: placeholder mock finding.\n\n"
            "## Recommendation\n"
            "- Continue pipeline.\n\n"
            "## Merge readiness verdict\n"
            "NO_NEW_BLOCKING_ISSUES\n"
            "NO_NEW_ISSUES\n"
        )
        return {
            "returncode": 0,
            "stdout": mock_out,
            "stderr": "",
            "timed_out": False,
            "command": ["mock-runner"],
        }

    cmd = build_transport_cmd(transport_kind, transport_path, project_root)
    cycle_dir = Path(task.get("cycle_dir") or project_root)
    stdout_log_path = cycle_dir / f"{reviewer}.stdout.log"
    stderr_log_path = cycle_dir / f"{reviewer}.stderr.log"
    try:
        return run_subprocess_resilient(
            cmd,
            timeout_seconds=timeout_seconds,
            input_text=prompt_text,
            cwd=project_root,
            env=env,
            stdout_log_path=stdout_log_path,
            stderr_log_path=stderr_log_path,
            heartbeat_label=reviewer,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": f"reviewer subprocess exception: {exc}\n",
            "timed_out": False,
            "command": cmd,
        }


def reviewer_worker(task: dict[str, Any]) -> dict[str, Any]:
    reviewer = task["reviewer"]
    cycle_dir = Path(task["cycle_dir"])
    prompt_path = Path(task["prompt_path"])
    output_path = cycle_dir / f"{reviewer}.md"
    stdout_log = cycle_dir / f"{reviewer}.stdout.log"
    stderr_log = cycle_dir / f"{reviewer}.stderr.log"
    exec_meta_path = cycle_dir / f"{reviewer}.exec.json"
    max_empty_retries = max(0, int(task["max_empty_retries"]))
    max_attempts = 1 + max_empty_retries

    attempts: list[dict[str, Any]] = []
    started_at = datetime.now().isoformat(timespec="seconds")

    if not prompt_path.exists():
        message = f"missing prompt file: {prompt_path}\n"
        atomic_write_text(output_path, "")
        atomic_write_text(stdout_log, "")
        atomic_write_text(stderr_log, message)
        meta = {
            "reviewer": reviewer,
            "status": "failed_missing_prompt",
            "started_at": started_at,
            "completed_at": datetime.now().isoformat(timespec="seconds"),
            "attempts": [],
            "prompt_path": str(prompt_path),
            "output_file": str(output_path),
        }
        atomic_write_text(exec_meta_path, json.dumps(meta, indent=2) + "\n")
        return meta

    task = dict(task)

    final_result: dict[str, Any] | None = None
    for attempt in range(1, max_attempts + 1):
        attempt_started = time.time()
        result = execute_reviewer_once(task)
        duration_ms = int((time.time() - attempt_started) * 1000)
        stdout_text = result["stdout"]
        stderr_text = result["stderr"]
        returncode = int(result["returncode"])
        empty_stdout = not stdout_text.strip()
        success = (returncode == 0) and (not empty_stdout)
        attempts.append(
            {
                "attempt": attempt,
                "returncode": returncode,
                "timed_out": bool(result["timed_out"]),
                "stdout_bytes": len(stdout_text.encode("utf-8", errors="replace")),
                "stderr_bytes": len(stderr_text.encode("utf-8", errors="replace")),
                "duration_ms": duration_ms,
                "empty_stdout": empty_stdout,
                "success": success,
                "command": result["command"],
            }
        )
        final_result = result
        if success:
            break
        if not empty_stdout:
            break
        if attempt >= max_attempts:
            break

    assert final_result is not None  # defensive
    final_stdout = final_result["stdout"]
    final_stderr = final_result["stderr"]
    final_returncode = int(final_result["returncode"])
    final_success = (final_returncode == 0) and bool(final_stdout.strip())

    # Keep report file empty on failed execution so validator can classify it reliably.
    report_payload = final_stdout if final_success else ""
    atomic_write_text(output_path, report_payload)
    atomic_write_text(stdout_log, final_stdout)
    atomic_write_text(stderr_log, final_stderr)

    meta = {
        "reviewer": reviewer,
        "status": "success" if final_success else "failed",
        "started_at": started_at,
        "completed_at": datetime.now().isoformat(timespec="seconds"),
        "prompt_path": str(prompt_path),
        "prompt_preview": (task.get("prompt_text", "") or "").splitlines()[:20],
        "output_file": str(output_path),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "attempts": attempts,
        "final_returncode": final_returncode,
        "final_empty_stdout": not bool(final_stdout.strip()),
        "transport": task["transport_kind"],
    }
    atomic_write_text(exec_meta_path, json.dumps(meta, indent=2) + "\n")
    return meta


def resolve_prompt_path(
    prompt_dir: Path | None,
    reviewer: str,
    cycle_dir: Path,
    reviewer_prompt_overrides: dict[str, Path],
) -> Path:
    specific = reviewer_prompt_overrides.get(reviewer)
    if specific:
        return specific

    base_dir = (prompt_dir.resolve() if prompt_dir else cycle_dir.resolve())
    candidate = base_dir / f"{reviewer}_prompt.md"
    return candidate


def run_validation(
    args: argparse.Namespace,
    project_root: Path,
    reviewers: list[str],
) -> tuple[int, str, str, list[str]]:
    validate_script = (
        args.validate_script.resolve()
        if args.validate_script
        else (Path(__file__).resolve().parent / "validate_cycle_outputs.py")
    )
    cmd = [
        sys.executable,
        str(validate_script),
        "--project-root",
        str(project_root),
        "--run-id",
        args.run_id,
        "--cycle-id",
        args.cycle_id,
    ]
    if args.max_retries is not None:
        cmd.extend(["--max-retries", str(args.max_retries)])
    if args.permission_confirm_after is not None:
        cmd.extend(["--permission-confirm-after", str(args.permission_confirm_after)])
    if args.force_recheck:
        cmd.append("--force-recheck")
    if args.allow_non_active_run:
        cmd.append("--allow-non-active-run")
    cmd.append("--reviewer-files")
    cmd.extend([f"{reviewer}.md" for reviewer in reviewers])

    # Bounded + tree-killed: the validator is pure-Python file work, but it must
    # never be able to wedge the orchestrator the way the codex path could.
    result = run_subprocess_resilient(
        cmd,
        timeout_seconds=VALIDATION_TIMEOUT_SECONDS,
        kill_grace_seconds=10.0,
    )
    return result["returncode"], result["stdout"], result["stderr"], cmd


def update_cycle_meta(cycle_meta_path: Path, run_payload: dict[str, Any]) -> None:
    cycle_meta = read_json(
        cycle_meta_path,
        {
            "cycle": 1,
            "status": "initialized",
            "reviewers": DEFAULT_REVIEWERS,
            "retry_state": {},
        },
    )
    cycle_meta["review_run"] = run_payload
    atomic_write_text(cycle_meta_path, json.dumps(cycle_meta, indent=2) + "\n")


def acquire_cycle_lock(lock_path: Path, wait_seconds: int) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + max(0, wait_seconds)
    payload = json.dumps(
        {
            "pid": os.getpid(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "lock_file": str(lock_path),
        },
        indent=2,
    ) + "\n"

    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            return
        except FileExistsError:
            if time.time() >= deadline:
                raise RuntimeError(f"cycle lock busy: {lock_path}")
            time.sleep(0.5)


def release_cycle_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink(missing_ok=True)
    except OSError:
        pass


def resolve_global_timeout(
    *,
    explicit: int | None,
    per_reviewer_timeout: int,
    max_attempts: int,
    reviewer_count: int,
    max_workers: int,
) -> int:
    """Derive a hard ceiling for the whole cycle when not explicitly set.

    Even with the per-reviewer tree-kill in place, this is a final backstop so a
    wedged worker process (not just a wedged codex child) can never hang the run.
    """
    if explicit is not None:
        return max(1, int(explicit))
    grace = REVIEWER_KILL_GRACE_SECONDS + 30
    per_reviewer_worst = (int(per_reviewer_timeout) + grace) * max(1, int(max_attempts))
    workers = max(1, int(max_workers))
    waves = -(-max(1, int(reviewer_count)) // workers)  # ceil division
    return max(1, per_reviewer_worst * waves + 120)


def _list_process_table() -> list[tuple[int, int]]:
    """Best-effort snapshot of (pid, ppid) for every process, cross-platform."""
    table: list[tuple[int, int]] = []
    try:
        if os.name == "nt":
            out = subprocess.run(
                [
                    "powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process | "
                    "ForEach-Object { \"$($_.ProcessId) $($_.ParentProcessId)\" }",
                ],
                capture_output=True, text=True, timeout=20,
            )
        else:
            # `-A` (all processes) is portable across Linux and macOS/BSD, where
            # `-e` instead means "show environment"; `-o field=` suppresses headers.
            out = subprocess.run(
                ["ps", "-A", "-o", "pid=,ppid="], capture_output=True, text=True, timeout=20
            )
        for line in (out.stdout or "").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                table.append((int(parts[0]), int(parts[1])))
    except Exception:
        pass
    return table


def _descendant_pids(root_pids: set[int], table: list[tuple[int, int]]) -> set[int]:
    """All transitive descendants of root_pids given a (pid, ppid) table."""
    children: dict[int, list[int]] = {}
    for pid, ppid in table:
        children.setdefault(ppid, []).append(pid)
    seen: set[int] = set()
    stack = list(root_pids)
    while stack:
        current = stack.pop()
        for child in children.get(current, []):
            if child not in seen:
                seen.add(child)
                stack.append(child)
    return seen


def terminate_pool_workers(executor: ProcessPoolExecutor) -> None:
    """Force-kill any still-running pool worker process trees (global backstop).

    ``executor.shutdown(cancel_futures=True)`` cancels only *pending* work; a
    worker mid-run keeps going. We must therefore hard-kill the workers AND the
    codex trees beneath them. Two robustness measures matter here:

    1. Root pids are double-sourced — from the pool's own ``_processes`` registry
       AND from the direct children of this process — because ``_processes`` can
       still be mid-population when the ceiling fires (which would otherwise leave
       whole worker trees alive).
    2. We kill the FULL descendant forest by pid (not just a single taskkill /T
       per worker), so a snapshot/cascade race under parallel teardown can't leave
       orphaned grandchildren behind.
    """
    roots: set[int] = set()
    procs = getattr(executor, "_processes", None) or {}
    for proc in list(procs.values()):
        pid = getattr(proc, "pid", None)
        if pid:
            roots.add(int(pid))

    table = _list_process_table()
    me = os.getpid()
    for pid, ppid in table:
        if ppid == me and pid != me:
            roots.add(pid)

    if not roots:
        return

    targets = _descendant_pids(roots, table) | roots
    for pid in targets:
        if pid == me:
            continue
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True, timeout=10,
                )
            else:
                os.kill(pid, signal.SIGKILL)
        except Exception:
            pass


def _synthetic_timeout_result(reviewer: str, global_timeout: int) -> dict[str, Any]:
    """Result stub for a reviewer the global ceiling had to kill before it finished."""
    return {
        "reviewer": reviewer,
        "status": "failed",
        "attempts": [
            {
                "attempt": 1,
                "returncode": 124,
                "timed_out": True,
                "stdout_bytes": 0,
                "stderr_bytes": 0,
                "duration_ms": int(global_timeout) * 1000,
                "empty_stdout": True,
                "success": False,
                "command": ["<global-timeout>"],
            }
        ],
        "final_returncode": 124,
        "final_empty_stdout": True,
        "error": "global_run_timeout_exceeded",
    }


def run_reviewers_bounded(
    tasks: list[dict[str, Any]],
    reviewers: list[str],
    max_workers: int,
    global_timeout: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Run reviewer workers in parallel under a hard, bounded global ceiling.

    Emits a run-level heartbeat every ~30s (so the run log is never empty), and
    if the global deadline is hit, force-kills the worker trees and synthesizes a
    timeout result for every reviewer that never reported.
    """
    results: list[dict[str, Any]] = []
    completed_reviewers: set[str] = set()
    stop_heartbeat = threading.Event()
    start = time.time()

    def heartbeat_loop(future_map: dict) -> None:
        while not stop_heartbeat.wait(HEARTBEAT_INTERVAL_SECONDS):
            total = len(future_map)
            done = sum(1 for f in future_map if f.done())
            pending = sorted(future_map[f] for f in future_map if not f.done())
            elapsed = int(time.time() - start)
            print(
                f"[heartbeat] cycle running — {elapsed}s / {int(global_timeout)}s budget — "
                f"{done}/{total} reviewers done; active: {', '.join(pending) or 'none'}",
                flush=True,
            )

    executor = ProcessPoolExecutor(max_workers=max_workers)
    hb_thread: threading.Thread | None = None
    ceiling_hit = False
    try:
        future_map = {
            executor.submit(reviewer_worker, task): task["reviewer"] for task in tasks
        }
        hb_thread = threading.Thread(
            target=heartbeat_loop, args=(future_map,), daemon=True
        )
        hb_thread.start()
        try:
            for future in as_completed(list(future_map), timeout=global_timeout):
                reviewer = future_map.get(future, "unknown")
                try:
                    res = future.result()
                except Exception as exc:  # worker crashed / pool broke
                    res = {
                        "reviewer": reviewer,
                        "status": "failed",
                        "attempts": [],
                        "final_returncode": 1,
                        "final_empty_stdout": True,
                        "error": f"worker_crashed: {exc}",
                    }
                results.append(res)
                completed_reviewers.add(res.get("reviewer", reviewer))
        except FuturesTimeoutError:
            ceiling_hit = True
            print(
                f"[global-timeout] cycle exceeded {int(global_timeout)}s; "
                "force-killing unfinished reviewer worker trees",
                flush=True,
            )
    finally:
        stop_heartbeat.set()
        # Only the rare ceiling-hit path needs the heavy force-kill of worker
        # trees; on normal completion a plain shutdown reaps the idle workers.
        if ceiling_hit:
            terminate_pool_workers(executor)
        executor.shutdown(wait=False, cancel_futures=True)
        if hb_thread is not None:
            hb_thread.join(timeout=5)

    timed_out_reviewers = [r for r in reviewers if r not in completed_reviewers]
    for reviewer in timed_out_reviewers:
        results.append(_synthetic_timeout_result(reviewer, global_timeout))
    return results, timed_out_reviewers


def main() -> int:
    args = parse_args()
    if args.timeout_seconds < 1:
        raise SystemExit("--timeout-seconds must be >= 1")
    if args.max_empty_retries < 0:
        raise SystemExit("--max-empty-retries must be >= 0")
    if args.parallelism < 1:
        raise SystemExit("--parallelism must be >= 1")
    if args.global_timeout_seconds is not None and args.global_timeout_seconds < 1:
        raise SystemExit("--global-timeout-seconds must be >= 1")
    if args.lock_wait_seconds < 0:
        raise SystemExit("--lock-wait-seconds must be >= 0")
    if args.blocking_consensus_threshold is not None and args.blocking_consensus_threshold < 1:
        raise SystemExit("--blocking-consensus-threshold must be >= 1")

    project_root = args.project_root.resolve()
    run_root = project_root / "_code_reviews_ai" / args.run_id
    cycle_dir = run_root / "cycles" / args.cycle_id
    cycle_meta_path = cycle_dir / "cycle_meta.json"
    summary_path = cycle_dir / "reviewer_run_summary.json"
    lock_path = cycle_dir / "review_cycle.lock"

    if not run_root.exists():
        raise SystemExit(f"run folder not found: {run_root}")
    if not cycle_dir.exists():
        raise SystemExit(f"cycle folder not found: {cycle_dir}")

    assert_active_run_or_fail(project_root, run_root, args.run_id, args.allow_non_active_run)
    reviewers = resolve_cycle_reviewers(cycle_meta_path, args.reviewers)
    blocking_clear_markers = normalize_text_list(
        args.blocking_clear_marker,
        DEFAULT_BLOCKING_CLEAR_MARKERS,
    )
    blocking_clear_phrases = [
        phrase.lower()
        for phrase in normalize_text_list(
            args.blocking_clear_phrase,
            DEFAULT_BLOCKING_CLEAR_PHRASES,
        )
    ]
    should_fix_priority_tags = [
        tag.lower()
        for tag in normalize_text_list(
            args.blocking_should_fix_tag,
            DEFAULT_SHOULD_FIX_PRIORITY_TAGS,
        )
    ]
    blocking_consensus_threshold = resolve_blocking_consensus_threshold(
        len(reviewers),
        args.blocking_consensus_threshold,
    )
    reviewer_prompt_overrides = parse_reviewer_prompt_overrides(args.reviewer_prompt)
    unknown_prompt_overrides = sorted(set(reviewer_prompt_overrides) - set(reviewers))
    if unknown_prompt_overrides:
        unknown_text = ", ".join(unknown_prompt_overrides)
        raise SystemExit(
            f"--reviewer-prompt specified reviewers not in this cycle: {unknown_text}"
        )

    acquire_cycle_lock(lock_path, args.lock_wait_seconds)
    try:
        transport_kind, transport_path = resolve_transport(args.transport)
        base_env = build_base_env(project_root, args.pythonpath_mode, args.review_mode)

        if not args.preserve_review_outputs:
            clear_review_outputs(cycle_dir, reviewers)

        review_query_file = resolve_input_file(run_root, args.review_query_file, "review_query.md")
        audit_items_file = resolve_input_file(run_root, args.audit_items_file, "audit_items.md")
        changed_files_file = resolve_input_file(run_root, args.changed_files_file, "changed_files.txt")
        context_notes_file = resolve_input_file(run_root, args.context_notes_file, "context_notes.md")
        scope_file = run_root / "inputs" / "scope.md"
        requirements_file = run_root / "inputs" / "requirements.md"
        diff_range_file = run_root / "inputs" / "diff_range.txt"

        review_query_text = read_text_or_default(
            review_query_file,
            "No explicit review query provided. Use available requirements and context.",
        )
        audit_items_text = read_text_or_default(
            audit_items_file,
            "- No explicit audit checklist provided. Apply standard defect/risk checks.",
        )
        scope_context_text = build_scope_context(
            scope_text=read_text_or_default(scope_file, "No scope.md provided."),
            requirements_text=read_text_or_default(
                requirements_file,
                "No requirements.md provided.",
            ),
            diff_range_text=read_text_or_default(
                diff_range_file,
                "No diff range provided.",
            ),
            changed_files_text=read_text_or_default(
                changed_files_file,
                "No changed_files.txt provided.",
            ),
            context_notes_text=read_text_or_default(
                context_notes_file,
                "No context_notes.md provided.",
            ),
        )

        # Packet sufficiency (soft + non-blocking): a review objective is the
        # hard-required input. Warn — don't block — when it still looks like the
        # template, since thin context biases reviewers toward scope-blind nitpicks
        # and invented findings. Small / CLI-driven runs are intentionally not stopped.
        objective_unfilled = (
            review_query_text.startswith("No explicit review query")
            or "Describe what this review must evaluate" in review_query_text
        )
        if objective_unfilled:
            print(
                "WARNING: review objective looks unfilled (review_query.md still holds the "
                "template/placeholder); reviewers lack intent and may produce scope-blind or "
                "invented findings. Fill it in, or record why it is absent.",
                file=sys.stderr,
            )

        project_rules_text, project_rules_meta = load_project_rules(
            project_root=project_root,
            rules_file=args.project_rules_file,
        )
        if args.inject_fix_log_context:
            fix_log_context_text = read_text_or_default(
                cycle_dir / "fix_log.md",
                "No fix log snapshot is available yet.",
            )
        else:
            fix_log_context_text = BLIND_FIX_LOG_CONTEXT_TEXT

        tasks: list[dict[str, Any]] = []
        for reviewer in reviewers:
            prompt_path = resolve_prompt_path(
                prompt_dir=args.prompt_dir,
                reviewer=reviewer,
                cycle_dir=cycle_dir,
                reviewer_prompt_overrides=reviewer_prompt_overrides,
            )
            prompt_template = read_text_or_default(
                prompt_path,
                "Reviewer prompt file missing. Fail this reviewer and report missing prompt path.",
            )
            rendered_prompt = render_prompt_with_inputs(
                prompt_template=prompt_template,
                review_query=review_query_text,
                audit_items=audit_items_text,
                scope_context=scope_context_text,
                project_rules=project_rules_text,
                fix_log_context=fix_log_context_text,
            )
            tasks.append(
                {
                    "reviewer": reviewer,
                    "project_root": str(project_root),
                    "cycle_dir": str(cycle_dir),
                    "prompt_path": str(prompt_path),
                    "prompt_text": rendered_prompt,
                    "timeout_seconds": args.timeout_seconds,
                    "max_empty_retries": args.max_empty_retries,
                    "transport_kind": transport_kind,
                    "transport_path": transport_path,
                    "env": base_env,
                    "mock_empty_reviewers": list(args.mock_empty_reviewers),
                    "mock_latency_ms": args.mock_latency_ms,
                }
            )

        started_at = datetime.now().isoformat(timespec="seconds")
        max_workers = min(args.parallelism, len(tasks))
        global_timeout = resolve_global_timeout(
            explicit=args.global_timeout_seconds,
            per_reviewer_timeout=args.timeout_seconds,
            max_attempts=1 + max(0, args.max_empty_retries),
            reviewer_count=len(tasks),
            max_workers=max_workers,
        )
        print(f"global_timeout_seconds={global_timeout}", flush=True)
        results, timed_out_reviewers = run_reviewers_bounded(
            tasks=tasks,
            reviewers=reviewers,
            max_workers=max_workers,
            global_timeout=global_timeout,
        )
        if timed_out_reviewers:
            print(
                "global_timeout_reviewers=" + ",".join(timed_out_reviewers),
                flush=True,
            )

        results.sort(key=lambda x: x.get("reviewer", ""))
        failed_reviewers = [item["reviewer"] for item in results if item.get("status") != "success"]
        run_payload = {
            "started_at": started_at,
            "completed_at": datetime.now().isoformat(timespec="seconds"),
            "status": "completed_with_failures" if failed_reviewers else "completed",
            "reviewers": reviewers,
            "review_mode": args.review_mode,
            "transport": transport_kind,
            "timeout_seconds": args.timeout_seconds,
            "global_timeout_seconds": global_timeout,
            "global_timeout_reviewers": timed_out_reviewers,
            "max_empty_retries": args.max_empty_retries,
            "parallelism": max_workers,
            "reviewer_prompt_overrides": {
                reviewer: str(path) for reviewer, path in reviewer_prompt_overrides.items()
            },
            "closure_policy": {
                "blocking_clear_markers": blocking_clear_markers,
                "blocking_clear_phrases": blocking_clear_phrases,
                "strict_marker_clear": bool(args.strict_marker_clear),
                "blocking_consensus_threshold": blocking_consensus_threshold,
                "blocking_should_fix_tags": should_fix_priority_tags,
                "inject_fix_log_context": bool(args.inject_fix_log_context),
            },
            "project_rules": project_rules_meta,
            "input_files": {
                "review_query_file": str(review_query_file),
                "audit_items_file": str(audit_items_file),
                "changed_files_file": str(changed_files_file),
                "context_notes_file": str(context_notes_file),
                "scope_file": str(scope_file),
                "requirements_file": str(requirements_file),
                "diff_range_file": str(diff_range_file),
            },
            "failed_reviewers": failed_reviewers,
            "results": results,
        }
        atomic_write_text(summary_path, json.dumps(run_payload, indent=2) + "\n")
        update_cycle_meta(cycle_meta_path, run_payload)

        print("REVIEW RUN SUMMARY")
        print(f"run_id={args.run_id}")
        print(f"cycle_id={args.cycle_id}")
        print(f"transport={transport_kind}")
        print(f"review_mode={args.review_mode}")
        print(f"parallelism={max_workers}")
        reviewer_table_rows: list[list[str]] = []
        for item in results:
            attempts = item.get("attempts", [])
            reviewer_table_rows.append(
                [
                    str(item.get("reviewer", "")),
                    str(item.get("status", "")),
                    str(len(attempts)),
                    str(item.get("final_returncode", "")),
                    str(item.get("final_empty_stdout", "")),
                ]
            )
        print(
            render_markdown_table(
                ["reviewer", "status", "attempts", "final_returncode", "empty_stdout"],
                reviewer_table_rows,
            )
        )
        print("PROJECT RULES SUMMARY")
        print(
            render_markdown_table(
                ["field", "value"],
                [
                    ["path", str(project_rules_meta.get("path", "-"))],
                    ["approved_count", str(project_rules_meta.get("approved_count", 0))],
                    ["pending_count", str(project_rules_meta.get("pending_count", 0))],
                ],
            )
        )
        fix_entries = parse_fix_log_entries(cycle_dir / "fix_log.md")
        fix_status = summarize_fix_status(fix_entries)
        blocking_status = summarize_blocking_fix_status(
            fix_entries,
            should_fix_priority_tags=should_fix_priority_tags,
        )
        print("ISSUE FIX STATUS (from fix_log.md)")
        print(
            render_markdown_table(
                ["status", "count"],
                [[name, str(value)] for name, value in fix_status.items()],
            )
        )
        print("BLOCKING ISSUE STATUS (must_fix + important should_fix)")
        print(
            render_markdown_table(
                ["metric", "count"],
                [[name, str(value)] for name, value in blocking_status.items()],
            )
        )
        print("BLOCKING CLOSURE POLICY")
        print(
            render_markdown_table(
                ["field", "value"],
                [
                    ["clear_markers", ", ".join(blocking_clear_markers)],
                    ["clear_phrases", ", ".join(blocking_clear_phrases)],
                    ["strict_marker_clear", "yes" if args.strict_marker_clear else "no"],
                    ["consensus_threshold", str(blocking_consensus_threshold)],
                    ["priority_should_fix_tags", ", ".join(should_fix_priority_tags)],
                    ["inject_fix_log_context", "yes" if args.inject_fix_log_context else "no"],
                ],
            )
        )

        if args.skip_validate:
            print("validation=skipped")
            write_cycle_summary(
                cycle_dir=cycle_dir,
                run_id=args.run_id,
                cycle_id=args.cycle_id,
                reviewers=reviewers,
                results=results,
                fix_status=fix_status,
                blocking_status=blocking_status,
                rules_meta=project_rules_meta,
                validation_info={"status": "skipped"},
            )
            return 0 if not failed_reviewers else 10

        val_rc, val_stdout, val_stderr, val_cmd = run_validation(args, project_root, reviewers)
        atomic_write_text(
            cycle_dir / "validation_exec.json",
            json.dumps(
                {
                    "ran_at": datetime.now().isoformat(timespec="seconds"),
                    "command": val_cmd,
                    "returncode": val_rc,
                    "stdout_preview": val_stdout.splitlines()[:12],
                    "stderr_preview": val_stderr.splitlines()[:12],
                },
                indent=2,
            )
            + "\n",
        )
        if val_stdout:
            print(val_stdout.strip())
        if val_stderr:
            print(val_stderr.strip(), file=sys.stderr)
        validation_info = parse_validation_kv(val_stdout)
        if "status" not in validation_info:
            validation_info["status"] = "unknown"
        validation_info["returncode"] = str(val_rc)
        marker_eval = evaluate_blocking_clear_markers(
            cycle_dir=cycle_dir,
            reviewers=reviewers,
            clear_markers=blocking_clear_markers,
            clear_phrases=blocking_clear_phrases,
            strict_marker_clear=args.strict_marker_clear,
        )
        blocking_close_ready = (
            marker_eval["clear_count"] >= blocking_consensus_threshold
            and blocking_status["blocking_unresolved_total"] == 0
        )
        validation_info["blocking_clear_count"] = str(marker_eval["clear_count"])
        validation_info["blocking_consensus_threshold"] = str(blocking_consensus_threshold)
        validation_info["blocking_unresolved_total"] = str(
            blocking_status["blocking_unresolved_total"]
        )
        validation_info["blocking_reopened_unresolved"] = str(
            blocking_status["blocking_reopened_unresolved"]
        )
        validation_info["blocking_close_ready"] = "yes" if blocking_close_ready else "no"
        if marker_eval["not_clear_reviewers"]:
            validation_info["blocking_not_clear_reviewers"] = ",".join(
                marker_eval["not_clear_reviewers"]
            )
        print("BLOCKING CLEARANCE CHECK")
        print(
            render_markdown_table(
                ["field", "value"],
                [
                    ["clear_count", str(marker_eval["clear_count"])],
                    ["threshold", str(blocking_consensus_threshold)],
                    ["unresolved_blocking_in_fix_log", str(blocking_status["blocking_unresolved_total"])],
                    ["reopened_blocking_in_fix_log", str(blocking_status["blocking_reopened_unresolved"])],
                    ["close_ready", "yes" if blocking_close_ready else "no"],
                    [
                        "not_clear_reviewers",
                        ", ".join(marker_eval["not_clear_reviewers"]) or "-",
                    ],
                ],
            )
        )
        write_cycle_summary(
            cycle_dir=cycle_dir,
            run_id=args.run_id,
            cycle_id=args.cycle_id,
            reviewers=reviewers,
            results=results,
            fix_status=fix_status,
            blocking_status=blocking_status,
            rules_meta=project_rules_meta,
            validation_info=validation_info,
        )

        if val_rc == 0 and args.auto_close_on_no_new_issues and blocking_close_ready:
            set_run_state(
                project_root=project_root,
                run_root=run_root,
                run_id=args.run_id,
                state="closed",
                reason="blocking_clearance_reached",
            )
            print("run_state=closed")
            print("run_state_reason=blocking_clearance_reached")
        elif val_rc == 0 and args.auto_close_on_no_new_issues:
            print("run_state=active")
            print("run_state_reason=blocking_clearance_not_reached")
        return val_rc
    finally:
        release_cycle_lock(lock_path)


if __name__ == "__main__":
    raise SystemExit(main())
