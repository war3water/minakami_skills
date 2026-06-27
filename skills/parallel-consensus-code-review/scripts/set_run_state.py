#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set run state for a _code_reviews_ai run and sync run_registry."
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument("--run-id", required=True, help="Run id under _code_reviews_ai.")
    parser.add_argument(
        "--state",
        required=True,
        choices=["active", "paused", "closed", "superseded"],
        help="Target run state.",
    )
    parser.add_argument(
        "--reason",
        default="manual_update",
        help="Reason for state transition (default: manual_update).",
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


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    run_root = project_root / "_code_reviews_ai" / args.run_id
    manifest_path = run_root / "run_manifest.json"

    if not run_root.exists():
        raise SystemExit(f"run folder not found: {run_root}")
    if not manifest_path.exists():
        raise SystemExit(f"run_manifest missing: {manifest_path}")

    manifest = read_json(manifest_path, {})
    manifest["run_state"] = args.state
    manifest["state_reason"] = args.reason
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
    run_entry = runs.get(args.run_id, {})
    if not isinstance(run_entry, dict):
        run_entry = {}
    run_entry["state"] = args.state
    run_entry["reason"] = args.reason
    run_entry["updated_at"] = datetime.now().isoformat(timespec="seconds")
    runs[args.run_id] = run_entry
    registry["runs"] = runs

    if args.state == "active":
        registry["active_run_id"] = args.run_id
        if not registry.get("active_cycle_id"):
            registry["active_cycle_id"] = str(manifest.get("current_cycle", "cycle_01"))
    else:
        if str(registry.get("active_run_id", "")) == args.run_id:
            registry["active_run_id"] = ""
            registry["active_cycle_id"] = ""
    registry["updated_at"] = datetime.now().isoformat(timespec="seconds")
    write_json(registry_path, registry)

    print(f"run_id={args.run_id}")
    print(f"state={args.state}")
    print(f"reason={args.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
