#!/usr/bin/env python
"""Hotspot finder — churn x size, language-agnostic (PATCHES.md section 4).

Hotspots (files that change often AND are large) are where refactoring pays off;
cold files are not, even when ugly. This ranks tracked files by commit churn over
a window and cross-references current size (LoC, a cheap complexity proxy).
Refactor the top of this list, not whatever happens to be in context.

Usage:
    python scripts/hotspots.py [--root .] [--days 365] [--top 30]

Reads git history only; changes nothing. Output columns: rank, commits (churn),
loc, churn*loc (the hotspot intersection), path.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from collections import Counter
from pathlib import Path


def _git(root: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        sys.exit("error: git not found on PATH")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"error: not a git repo, or git failed: {exc.stderr.strip()}")
    return proc.stdout


def main() -> None:
    ap = argparse.ArgumentParser(description="Rank files by churn x size (hotspots).")
    ap.add_argument("--root", default=".", help="repo root (default: current dir)")
    ap.add_argument("--days", type=int, default=365, help="churn window in days (default: 365)")
    ap.add_argument("--top", type=int, default=30, help="rows to print (default: 30)")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    log = _git(root, "log", f"--since={args.days} days ago", "--pretty=format:", "--name-only")
    churn = Counter(line.strip() for line in log.splitlines() if line.strip())

    rows = []
    for path, commits in churn.items():
        f = root / path
        if not f.is_file():  # renamed or deleted within the window — skip
            continue
        try:
            loc = sum(1 for _ in f.open("rb"))
        except OSError:
            loc = 0
        rows.append((commits, loc, commits * loc, path))

    rows.sort(key=lambda r: r[2], reverse=True)  # by churn x size
    if not rows:
        print("(no churn in the window — widen --days, or confirm the repo has history)")
        return
    print(f"{'rank':>4}  {'commits':>7}  {'loc':>6}  {'churn*loc':>9}  path")
    for i, (commits, loc, product, path) in enumerate(rows[: args.top], 1):
        print(f"{i:>4}  {commits:>7}  {loc:>6}  {product:>9}  {path}")


if __name__ == "__main__":
    main()
