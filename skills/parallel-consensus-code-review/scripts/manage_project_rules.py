#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


RULE_ID_RE = re.compile(r"^rule_(\d+)$")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def default_payload() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": "",
        "rules": [],
    }


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


def normalize_state(value: str) -> str:
    state = str(value or "").strip().lower()
    if state not in {"pending", "approved"}:
        raise SystemExit(f"invalid rule state `{value}`. Use pending or approved.")
    return state


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Manage project-level review rules under _code_reviews_ai/project_review_rules.* "
            "with explicit pending/approved state."
        )
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root path (default: current working directory).",
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["list", "add", "approve", "revise", "remove"],
        help="Rule operation.",
    )
    parser.add_argument(
        "--rule-id",
        default="",
        help="Rule id for approve/revise/remove (for example: rule_001).",
    )
    parser.add_argument(
        "--text",
        default="",
        help="Rule text for add/revise.",
    )
    parser.add_argument(
        "--state",
        default="pending",
        help="State for add action: pending or approved (default: pending).",
    )
    parser.add_argument(
        "--actor",
        default="agent",
        help="Actor name recorded in metadata (default: agent).",
    )
    parser.add_argument(
        "--note",
        default="",
        help="Optional note for add/revise.",
    )
    parser.add_argument(
        "--keep-state",
        action="store_true",
        help=(
            "For revise action: keep current state instead of moving an approved rule "
            "back to pending."
        ),
    )
    return parser.parse_args()


def next_rule_id(rules: list[dict[str, Any]]) -> str:
    max_num = 0
    for item in rules:
        rid = str(item.get("id", "") or "").strip().lower()
        match = RULE_ID_RE.match(rid)
        if not match:
            continue
        max_num = max(max_num, int(match.group(1)))
    return f"rule_{max_num + 1:03d}"


def find_rule(rules: list[dict[str, Any]], rule_id: str) -> tuple[int, dict[str, Any]]:
    rid = str(rule_id or "").strip().lower()
    if not rid:
        raise SystemExit("--rule-id is required for this action.")
    for idx, item in enumerate(rules):
        if str(item.get("id", "") or "").strip().lower() == rid:
            return idx, item
    raise SystemExit(f"rule not found: {rule_id}")


def render_markdown(payload: dict[str, Any]) -> str:
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
        f"- updated_at: {str(payload.get('updated_at', '') or '-')}",
        f"- approved_count: {len(approved)}",
        f"- pending_count: {len(pending)}",
        "",
        "## Approved Rules",
        "| id | rule | approved_by | updated_at |",
        "| --- | --- | --- | --- |",
    ]
    if approved:
        for item in approved:
            rid = str(item.get("id", "") or "").strip() or "-"
            text = str(item.get("text", "") or "").strip().replace("|", "\\|")
            approved_by = str(item.get("approved_by", "") or "-")
            updated_at = str(item.get("updated_at", "") or item.get("created_at", "") or "-")
            lines.append(f"| {rid} | {text or '-'} | {approved_by} | {updated_at} |")
    else:
        lines.append("| - | No approved project rules yet. | - | - |")

    lines.extend(
        [
            "",
            "## Pending Rules (Require User Approval)",
            "| id | proposed_rule | proposed_by | updated_at |",
            "| --- | --- | --- | --- |",
        ]
    )
    if pending:
        for item in pending:
            rid = str(item.get("id", "") or "").strip() or "-"
            text = str(item.get("text", "") or "").strip().replace("|", "\\|")
            updated_by = str(item.get("updated_by", "") or item.get("created_by", "") or "-")
            updated_at = str(item.get("updated_at", "") or item.get("created_at", "") or "-")
            lines.append(f"| {rid} | {text or '-'} | {updated_by} | {updated_at} |")
    else:
        lines.append("| - | No pending rules. | - | - |")

    lines.extend(
        [
            "",
            "## Workflow",
            "1. Agent proposes rules as `pending`.",
            "2. User approves rules by switching to `approved` (via this script).",
            "3. Only `approved` rules affect reviewer prompts.",
        ]
    )
    return "\n".join(lines) + "\n"


def save_rules(project_root: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    reviews_root = project_root / "_code_reviews_ai"
    reviews_root.mkdir(parents=True, exist_ok=True)
    json_path = reviews_root / "project_review_rules.json"
    md_path = reviews_root / "project_review_rules.md"
    payload["updated_at"] = now_iso()
    write_json(json_path, payload)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    reviews_root = project_root / "_code_reviews_ai"
    reviews_root.mkdir(parents=True, exist_ok=True)
    json_path = reviews_root / "project_review_rules.json"

    payload = read_json(json_path, default_payload())
    rules_raw = payload.get("rules", [])
    rules = rules_raw if isinstance(rules_raw, list) else []
    payload["rules"] = rules

    action = args.action
    actor = str(args.actor or "agent").strip() or "agent"
    changed = False

    if action == "add":
        text = str(args.text or "").strip()
        if not text:
            raise SystemExit("--text is required for add action.")
        state = normalize_state(args.state)
        entry: dict[str, Any] = {
            "id": next_rule_id(rules),
            "state": state,
            "text": text,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "created_by": actor,
            "updated_by": actor,
            "approved_at": now_iso() if state == "approved" else "",
            "approved_by": actor if state == "approved" else "",
            "note": str(args.note or "").strip(),
        }
        rules.append(entry)
        changed = True
        print(f"added_rule={entry['id']}")

    elif action == "approve":
        idx, entry = find_rule(rules, args.rule_id)
        entry["state"] = "approved"
        entry["approved_at"] = now_iso()
        entry["approved_by"] = actor
        entry["updated_at"] = now_iso()
        entry["updated_by"] = actor
        rules[idx] = entry
        changed = True
        print(f"approved_rule={entry.get('id')}")

    elif action == "revise":
        text = str(args.text or "").strip()
        if not text:
            raise SystemExit("--text is required for revise action.")
        idx, entry = find_rule(rules, args.rule_id)
        entry["text"] = text
        entry["note"] = str(args.note or entry.get("note", "") or "").strip()
        if not args.keep_state:
            entry["state"] = "pending"
            entry["approved_at"] = ""
            entry["approved_by"] = ""
        entry["updated_at"] = now_iso()
        entry["updated_by"] = actor
        rules[idx] = entry
        changed = True
        print(f"revised_rule={entry.get('id')}")

    elif action == "remove":
        idx, entry = find_rule(rules, args.rule_id)
        del rules[idx]
        changed = True
        print(f"removed_rule={entry.get('id')}")

    elif action == "list":
        pass
    else:  # pragma: no cover - defensive
        raise SystemExit(f"unsupported action: {action}")

    if changed:
        payload["rules"] = rules
    json_path_written, md_path_written = save_rules(project_root, payload)

    approved_count = 0
    pending_count = 0
    for item in rules:
        state = str(item.get("state", "pending") or "pending").strip().lower()
        if state == "approved":
            approved_count += 1
        else:
            pending_count += 1

    print(f"rules_json={json_path_written}")
    print(f"rules_markdown={md_path_written}")
    print(f"approved_count={approved_count}")
    print(f"pending_count={pending_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
