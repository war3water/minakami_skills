#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_REVIEWER_FILES = ["reviewer_01.md", "reviewer_02.md", "reviewer_03.md"]
HEADER_ONLY_RE = re.compile(r"^#\s*reviewer\b.*$", re.IGNORECASE)
SESSION_ONLY_RE = re.compile(r"^(?:---\s*)?SESSION_ID\s*:\s*$", re.IGNORECASE)
FORCE_MAJEURE_MARKERS = {
    "execution_permissions": (
        "401",
        "403",
        "access denied",
        "approval required",
        "auth failed",
        "authentication",
        "authorization",
        "cannot execute `python`",
        "codex login",
        "eacces",
        "forbidden",
        "insufficient permission",
        "insufficient privileges",
        "not authorized",
        "operation not permitted",
        "permission denied",
        "requires elevated privileges",
        "requires escalated",
        "sandbox policy",
        "unauthorized",
    ),
    "transport_reliability": (
        "backend-api/codex/responses",
        "connection attempt failed",
        "empty output",
        "failed to connect to websocket",
        "returned empty",
        "no output captured",
        "multiline prompt",
        "os error 10060",
        "session_id:",
        "stream disconnected",
        "websocket",
        "argument handling",
        "wrapper",
    ),
    "import_context": (
        "cannot import",
        "importerror",
        "modulenotfounderror",
        "sys.path",
    ),
    "diff_context": (
        "ambiguous argument",
        "bad revision",
        "fatal: not a git repository",
        "no merge base",
        "not a git repository",
        "unknown revision",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate reviewer outputs for one cycle, enforce retry caps, and stop with "
            "user-confirmation state when permission/auth blockers are likely."
        )
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root path (default: current working directory).",
    )
    parser.add_argument("--run-id", required=True, help="Run id under _code_reviews_ai.")
    parser.add_argument(
        "--cycle-id",
        default="cycle_01",
        help="Cycle folder name (default: cycle_01).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Override max retries. If omitted, use cycle/manifest values.",
    )
    parser.add_argument(
        "--permission-confirm-after",
        type=int,
        default=None,
        help=(
            "Override threshold for asking user confirmation when permission/auth markers "
            "are detected. If omitted, use cycle/manifest values."
        ),
    )
    parser.add_argument(
        "--reviewer-files",
        nargs="+",
        default=None,
        help=(
            "Reviewer markdown file names relative to cycle folder. "
            "If omitted, use cycle_meta reviewers (fallback: reviewer_01/02/03)."
        ),
    )
    parser.add_argument(
        "--force-recheck",
        action="store_true",
        help="Ignore pending decision state and re-evaluate outputs immediately.",
    )
    parser.add_argument(
        "--allow-non-active-run",
        action="store_true",
        help="Allow validation for runs marked closed/superseded.",
    )
    return parser.parse_args()


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(default)
    return raw if isinstance(raw, dict) else dict(default)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def parse_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def classify_report(path: Path) -> tuple[bool, str, str]:
    if not path.exists():
        return True, "missing", ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return True, "unreadable", ""

    stripped = text.strip()
    if not stripped:
        return True, "empty", text

    non_empty_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(non_empty_lines) == 1 and HEADER_ONLY_RE.match(non_empty_lines[0]):
        return True, "header_only", text
    if len(non_empty_lines) <= 2 and all(
        line == "---" or SESSION_ONLY_RE.match(line) for line in non_empty_lines
    ):
        return True, "session_stub", text

    return False, "ok", text


def collect_log_texts(cycle_dir: Path) -> list[str]:
    texts: list[str] = []
    seen: set[Path] = set()
    patterns = ("reviewer_*.stderr.log", "reviewer_*.stdout.log", "reviewer_*.log")
    for pattern in patterns:
        for path in sorted(cycle_dir.glob(pattern)):
            if path in seen:
                continue
            seen.add(path)
            try:
                texts.append(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    return texts


def detect_force_majeure_hints(texts: list[str]) -> dict[str, list[str]]:
    combined = "\n".join(texts).lower()
    if not combined:
        return {}

    hits_by_category: dict[str, list[str]] = {}
    for category, markers in FORCE_MAJEURE_MARKERS.items():
        hits = sorted({marker for marker in markers if marker in combined})
        if hits:
            hits_by_category[category] = hits
    return hits_by_category


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    run_root = project_root / "_code_reviews_ai" / args.run_id
    cycle_dir = run_root / "cycles" / args.cycle_id

    if not run_root.exists():
        raise SystemExit(f"run folder not found: {run_root}")
    if not cycle_dir.exists():
        raise SystemExit(f"cycle folder not found: {cycle_dir}")

    manifest_path = run_root / "run_manifest.json"
    cycle_meta_path = cycle_dir / "cycle_meta.json"
    guard_path = cycle_dir / "retry_guard.json"
    decision_request_path = cycle_dir / "decision_request.json"

    manifest = read_json(manifest_path, {})
    cycle_meta = read_json(
        cycle_meta_path,
        {
            "cycle": 1,
            "status": "initialized",
            "reviewers": ["reviewer_01", "reviewer_02", "reviewer_03"],
            "retry_state": {},
        },
    )

    run_state = str(manifest.get("run_state", "active") or "active")
    if run_state in {"closed", "superseded"} and not (args.force_recheck or args.allow_non_active_run):
        print(f"status=run_state_blocked")
        print(f"reason=run_is_{run_state}")
        print("action=skip_validation_for_non_active_run")
        return 22

    retry_state_raw = cycle_meta.get("retry_state", {})
    retry_state = retry_state_raw if isinstance(retry_state_raw, dict) else {}

    previous_guard = read_json(guard_path, {})
    decision_pending = bool(
        previous_guard.get("decision_needed") and previous_guard.get("requires_user_confirmation")
    )
    if decision_pending and not args.force_recheck:
        print("status=awaiting_user_decision")
        print(f"reason={previous_guard.get('reason', 'manual_decision_required')}")
        print(f"decision_request={decision_request_path}")
        print("action=User decision pending; do not keep auto-looping until user decides.")
        return 21

    max_retries = args.max_retries
    if max_retries is None:
        max_retries = parse_int(
            retry_state.get("max_retries", manifest.get("max_retries", 5)),
            5,
        )
    permission_confirm_after = args.permission_confirm_after
    if permission_confirm_after is None:
        permission_confirm_after = parse_int(
            retry_state.get(
                "permission_confirm_after",
                manifest.get("permission_confirm_after", 2),
            ),
            2,
        )

    max_retries = max(1, max_retries)
    permission_confirm_after = max(1, min(permission_confirm_after, max_retries))
    attempts_used = max(0, parse_int(retry_state.get("attempts_used", 0), 0))

    reviewer_files = args.reviewer_files
    if not reviewer_files:
        raw_reviewers = cycle_meta.get("reviewers", DEFAULT_REVIEWER_FILES)
        if isinstance(raw_reviewers, list) and raw_reviewers:
            reviewer_files = [f"{str(r).strip().lower()}.md" for r in raw_reviewers]
        else:
            reviewer_files = list(DEFAULT_REVIEWER_FILES)

    invalid_reviewers: list[dict[str, str]] = []
    reviewer_texts: list[str] = []
    for name in reviewer_files:
        path = cycle_dir / name
        invalid, reason, text = classify_report(path)
        reviewer_texts.append(text)
        if invalid:
            invalid_reviewers.append({"file": name, "reason": reason})

    force_majeure_hits: dict[str, list[str]] = {}
    force_majeure_confirmed = False
    if invalid_reviewers:
        log_texts = collect_log_texts(cycle_dir)
        force_majeure_hits = detect_force_majeure_hints(reviewer_texts + log_texts)
        force_majeure_confirmed = bool(force_majeure_hits)
        attempts_used += 1

    status = "ready_for_consensus"
    reason = "all_reviewer_outputs_valid"
    requires_user_confirmation = False
    exit_code = 0

    if invalid_reviewers:
        status = "retry_required"
        reason = "empty_or_invalid_reviewer_output"
        exit_code = 10
        reached_retry_cap = attempts_used >= max_retries
        permission_threshold_reached = attempts_used >= permission_confirm_after

        if reached_retry_cap:
            status = "awaiting_user_confirmation"
            reason = "max_retries_reached"
            requires_user_confirmation = True
            exit_code = 20
        elif force_majeure_confirmed and permission_threshold_reached:
            status = "awaiting_user_confirmation"
            reason = "force_majeure_blocker_detected"
            requires_user_confirmation = True
            exit_code = 20

    cycle_meta["status"] = status
    cycle_meta["retry_state"] = {
        "attempts_used": attempts_used,
        "max_retries": max_retries,
        "permission_confirm_after": permission_confirm_after,
        "last_retry_reason": reason if invalid_reviewers else "",
        "requires_user_confirmation": requires_user_confirmation,
    }
    write_json(cycle_meta_path, cycle_meta)

    manifest["max_retries"] = max_retries
    manifest["permission_confirm_after"] = permission_confirm_after
    manifest["requires_user_confirmation"] = requires_user_confirmation
    manifest["last_retry_reason"] = reason if invalid_reviewers else ""
    write_json(manifest_path, manifest)

    guard_payload = {
        "evaluated_at": datetime.now().isoformat(timespec="seconds"),
        "run_id": args.run_id,
        "cycle_id": args.cycle_id,
        "status": status,
        "reason": reason,
        "attempts_used": attempts_used,
        "max_retries": max_retries,
        "permission_confirm_after": permission_confirm_after,
        "reviewer_files": reviewer_files,
        "missing_or_invalid_reviewers": invalid_reviewers,
        "execution_permission_block_detected": "execution_permissions" in force_majeure_hits,
        "force_majeure_confirmed": force_majeure_confirmed,
        "force_majeure_categories": sorted(force_majeure_hits.keys()),
        "force_majeure_hits": force_majeure_hits,
        "low_overhead_mode_allowed": requires_user_confirmation and force_majeure_confirmed,
        "requires_user_confirmation": requires_user_confirmation,
        "decision_needed": requires_user_confirmation,
        "decision_request_file": str(decision_request_path),
        "next_action": (
            "ask_user_for_decision_once_and_wait"
            if requires_user_confirmation
            else "continue_or_retry"
        ),
    }
    write_json(guard_path, guard_payload)

    if requires_user_confirmation:
        decision_options = [
            "fix_environment_or_permissions_then_retry_full_mode",
            "abort_review",
        ]
        if force_majeure_confirmed:
            decision_options.insert(1, "enable_low_overhead_mode_after_user_confirmation")

        decision_request = {
            "requested_at": datetime.now().isoformat(timespec="seconds"),
            "run_id": args.run_id,
            "cycle_id": args.cycle_id,
            "reason": reason,
            "attempts_used": attempts_used,
            "max_retries": max_retries,
            "force_majeure_confirmed": force_majeure_confirmed,
            "force_majeure_categories": sorted(force_majeure_hits.keys()),
            "blocking_reviewers": invalid_reviewers,
            "options": decision_options,
            "instruction": (
                "Ask the user once to choose a processing decision. Wait for that decision "
                "before continuing to avoid repeated interruption loops."
            ),
        }
        write_json(decision_request_path, decision_request)

    print(f"status={status}")
    print(f"reason={reason}")
    print(f"attempts_used={attempts_used}/{max_retries}")
    if invalid_reviewers:
        print(f"invalid_reviewers={invalid_reviewers}")
    if force_majeure_hits:
        print(f"force_majeure_categories={sorted(force_majeure_hits.keys())}")
        print(f"force_majeure_hits={force_majeure_hits}")
    if requires_user_confirmation:
        print(
            "action=Stop and ask user to confirm/grant required external system permissions "
            "or auth before continuing."
        )
        print(f"decision_request={decision_request_path}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
