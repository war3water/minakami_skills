#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


REVIEWER_ID_RE = re.compile(r"^reviewer_[a-z0-9_]+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize _code_reviews_ai run folder for parallel consensus code review."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root path (default: current working directory).",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default="",
        help="Optional run id. Default format: run_YYYYMMDD_HHMMSS",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Maximum retry attempts for empty/invalid reviewer outputs (default: 5).",
    )
    parser.add_argument(
        "--permission-confirm-after",
        type=int,
        default=2,
        help=(
            "After this many failed attempts with permission/auth hints, stop and request user "
            "confirmation before continuing (default: 2)."
        ),
    )
    parser.add_argument(
        "--reviewer-count",
        dest="team_size",
        type=int,
        default=3,
        help="Default reviewer count when --reviewers is not provided (default: 3).",
    )
    parser.add_argument(
        "--reviewers",
        nargs="+",
        default=None,
        help=(
            "Explicit reviewer ids (for example: reviewer_01 reviewer_02 reviewer_03). "
            "If provided, this overrides --reviewer-count."
        ),
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def default_project_rules_payload() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": "",
        "rules": [],
    }


def render_project_rules_markdown(payload: dict[str, Any]) -> str:
    rules = payload.get("rules", [])
    approved: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    for item in rules if isinstance(rules, list) else []:
        if not isinstance(item, dict):
            continue
        state = str(item.get("state", "pending") or "pending").strip().lower()
        if state == "approved":
            approved.append(item)
        else:
            pending.append(item)

    lines = [
        "# Project Review Rules",
        "",
        "Project-level review rules shared by all runs under `_code_reviews_ai/`.",
        "Only rules with `state=approved` are injected into reviewer prompts.",
        "",
        "## Approved Rules",
        "| id | rule | updated_at |",
        "| --- | --- | --- |",
    ]
    if approved:
        for item in approved:
            rid = str(item.get("id", "") or "").strip() or "-"
            text = str(item.get("text", "") or "").strip().replace("|", "\\|")
            updated_at = str(item.get("updated_at", "") or item.get("created_at", "") or "").strip() or "-"
            lines.append(f"| {rid} | {text or '-'} | {updated_at} |")
    else:
        lines.append("| - | No approved project rules yet. | - |")

    lines.extend(
        [
            "",
            "## Pending Rules (Require User Approval)",
            "| id | proposed_rule | updated_at |",
            "| --- | --- | --- |",
        ]
    )
    if pending:
        for item in pending:
            rid = str(item.get("id", "") or "").strip() or "-"
            text = str(item.get("text", "") or "").strip().replace("|", "\\|")
            updated_at = str(item.get("updated_at", "") or item.get("created_at", "") or "").strip() or "-"
            lines.append(f"| {rid} | {text or '-'} | {updated_at} |")
    else:
        lines.append("| - | No pending rules. | - |")

    lines.extend(
        [
            "",
            "## Maintenance",
            "Use `scripts/manage_project_rules.py` to add/propose/approve/revise rules in a controlled way.",
        ]
    )
    return "\n".join(lines) + "\n"


def default_reviewer_ids(count: int) -> list[str]:
    width = max(2, len(str(count)))
    return [f"reviewer_{index + 1:0{width}d}" for index in range(count)]


def normalize_reviewers(args: argparse.Namespace) -> list[str]:
    if args.reviewers:
        reviewers = args.reviewers
    else:
        reviewers = default_reviewer_ids(args.team_size)

    uniq: list[str] = []
    seen: set[str] = set()
    for reviewer in reviewers:
        rid = reviewer.strip().lower()
        if not rid:
            continue
        if not REVIEWER_ID_RE.match(rid):
            raise SystemExit(
                f"Invalid reviewer id `{reviewer}`. Expected pattern: reviewer_<letters_digits_underscores>."
            )
        if rid in seen:
            continue
        seen.add(rid)
        uniq.append(rid)
    if not uniq:
        raise SystemExit("At least one reviewer id is required.")
    return uniq


def build_prompt_template(reviewer_id: str) -> str:
    pretty = reviewer_id.replace("_", " ").title()
    return (
        f"# {pretty} Prompt\n\n"
        "Primary review objective (must follow):\n"
        "{{REVIEW_QUERY}}\n\n"
        "Audit checklist (must follow):\n"
        "{{AUDIT_ITEMS}}\n\n"
        "Project-level approved review rules (must follow):\n"
        "{{PROJECT_RULES}}\n\n"
        "Scope context (inputs + file-level signals):\n"
        "{{SCOPE_CONTEXT}}\n\n"
        "Scope rule: touched files are important, but not the only audit basis.\n"
        "If git/diff context is missing, use user query + audit items + context notes to define scope.\n"
        "Do not anchor to prior reviewer outputs or historical issue ids in this independent pass.\n"
        "If you suspect a regression, provide fresh reproducible evidence; recurrence mapping is handled in consensus.\n"
        "Classify findings into MUST_FIX, SHOULD_FIX_IMPORTANT, SHOULD_FIX_MINOR, or NEEDS_CONFIRMATION.\n"
        "If no MUST_FIX and no SHOULD_FIX_IMPORTANT remain, output exact marker: NO_NEW_BLOCKING_ISSUES.\n"
        f"Write final report to {reviewer_id}.md.\n"
    )


def mark_previous_active_run_superseded(root: Path, previous_run_id: str, new_run_id: str) -> None:
    if not previous_run_id or previous_run_id == new_run_id:
        return
    previous_manifest_path = root / "_code_reviews_ai" / previous_run_id / "run_manifest.json"
    if not previous_manifest_path.exists():
        return
    manifest = read_json(previous_manifest_path, {})
    manifest["run_state"] = "superseded"
    manifest["superseded_by_run_id"] = new_run_id
    manifest["superseded_at"] = datetime.now().isoformat(timespec="seconds")
    write_json(previous_manifest_path, manifest)


def main() -> int:
    args = parse_args()
    if args.max_retries < 1:
        raise SystemExit("--max-retries must be >= 1")
    if args.permission_confirm_after < 1:
        raise SystemExit("--permission-confirm-after must be >= 1")
    if args.permission_confirm_after > args.max_retries:
        raise SystemExit("--permission-confirm-after must be <= --max-retries")
    if args.team_size < 1:
        raise SystemExit("--reviewer-count must be >= 1")

    reviewers = normalize_reviewers(args)

    root = args.project_root.resolve()
    run_id = args.run_id.strip() or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    reviews_root = root / "_code_reviews_ai"
    project_rules_json_path = reviews_root / "project_review_rules.json"
    project_rules_md_path = reviews_root / "project_review_rules.md"

    base = reviews_root / run_id
    inputs = base / "inputs"
    cycle = base / "cycles" / "cycle_01"
    for path in (inputs, cycle):
        path.mkdir(parents=True, exist_ok=True)

    files: dict[Path, str] = {
        inputs / "scope.md": "# Scope\n",
        inputs / "requirements.md": "# Requirements\n",
        inputs / "diff_range.txt": "BASE_SHA..HEAD_SHA\n",
        inputs / "review_query.md": (
            "# Review Query\n"
            "Describe what this review must evaluate (intent, risks, quality goals).\n"
        ),
        inputs / "audit_items.md": (
            "# Audit Items\n"
            "- Add explicit checklist items the reviewers must verify.\n"
            "- Include compliance, security, performance, or architecture criteria as needed.\n"
        ),
        inputs / "changed_files.txt": (
            "# Optional changed file list\n"
            "# One path per line. Use this when git diff is unavailable.\n"
        ),
        inputs / "context_notes.md": (
            "# Context Notes\n"
            "Any extra context for reviewers (non-git scope cues, constraints, known tradeoffs).\n"
        ),
        cycle / "cycle_meta.json": json.dumps(
            {
                "cycle": 1,
                "status": "initialized",
                "reviewers": reviewers,
                "retry_state": {
                    "attempts_used": 0,
                    "max_retries": args.max_retries,
                    "permission_confirm_after": args.permission_confirm_after,
                    "last_retry_reason": "",
                    "requires_user_confirmation": False,
                },
            },
            indent=2,
        )
        + "\n",
        cycle / "retry_guard.json": json.dumps(
            {
                "status": "initialized",
                "attempts_used": 0,
                "max_retries": args.max_retries,
                "permission_confirm_after": args.permission_confirm_after,
                "missing_or_invalid_reviewers": [],
                "permission_block_detected": False,
                "requires_user_confirmation": False,
                "reviewers": reviewers,
            },
            indent=2,
        )
        + "\n",
        cycle / "merged_findings.md": "# Merged Findings\n",
        cycle / "consensus.md": "# Consensus\n",
        cycle / "fix_plan.md": "# Fix Plan\n",
        cycle / "fix_log.md": (
            "# Fix Log\n\n"
            "<!-- severity examples: must_fix, critical, should_fix_important_efficiency, should_fix_minor -->\n\n"
            "| issue_id | severity | status | owner | notes |\n"
            "| --- | --- | --- | --- | --- |\n"
        ),
        cycle / "re_review.md": "# Re-Review Result\n",
        cycle / "cycle_summary.md": "# Cycle Summary\n",
    }

    for reviewer_id in reviewers:
        files[cycle / f"{reviewer_id}_prompt.md"] = build_prompt_template(reviewer_id)
        files[cycle / f"{reviewer_id}.md"] = f"# {reviewer_id.replace('_', ' ').title()}\n"

    manifest_path = base / "run_manifest.json"
    new_manifest = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(root),
        "root_folder": "_code_reviews_ai",
        "current_cycle": "cycle_01",
        "max_retries": args.max_retries,
        "permission_confirm_after": args.permission_confirm_after,
        "requires_user_confirmation": False,
        "reviewers": reviewers,
        "team_size": len(reviewers),
        "run_state": "active",
    }
    write_json(manifest_path, new_manifest)

    registry_path = root / "_code_reviews_ai" / "run_registry.json"
    registry = read_json(
        registry_path,
        {
            "active_run_id": "",
            "active_cycle_id": "",
            "updated_at": "",
            "runs": {},
        },
    )
    previous_active = str(registry.get("active_run_id", "") or "")
    mark_previous_active_run_superseded(root, previous_active, run_id)
    runs = registry.get("runs", {})
    if not isinstance(runs, dict):
        runs = {}
    if previous_active and previous_active != run_id and previous_active in runs:
        prev = runs.get(previous_active, {})
        if not isinstance(prev, dict):
            prev = {}
        prev["state"] = "superseded"
        prev["updated_at"] = datetime.now().isoformat(timespec="seconds")
        prev["superseded_by_run_id"] = run_id
        runs[previous_active] = prev
    runs[run_id] = {
        "state": "active",
        "team_size": len(reviewers),
        "reviewers": reviewers,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    registry["active_run_id"] = run_id
    registry["active_cycle_id"] = "cycle_01"
    registry["updated_at"] = datetime.now().isoformat(timespec="seconds")
    registry["runs"] = runs
    write_json(registry_path, registry)

    if not project_rules_json_path.exists():
        default_rules = default_project_rules_payload()
        default_rules["updated_at"] = datetime.now().isoformat(timespec="seconds")
        write_json(project_rules_json_path, default_rules)
    if not project_rules_md_path.exists():
        rules_payload = read_json(project_rules_json_path, default_project_rules_payload())
        project_rules_md_path.write_text(
            render_project_rules_markdown(rules_payload),
            encoding="utf-8",
        )

    for file_path, template in files.items():
        if not file_path.exists():
            file_path.write_text(template, encoding="utf-8")

    print(base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
