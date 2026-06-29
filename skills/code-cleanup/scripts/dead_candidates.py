#!/usr/bin/env python
"""Dead-code + test-only-orphan candidate scanner (references/techniques.md sections 8 and 9.A).

PYTHON ONLY. Lists top-level functions / classes in the production source whose
NAME is referenced only by tests, or not at all — the two classes that name/AST
tools (vulture) and runtime coverage both MISS:

  ZERO_REF   — name never referenced outside its own definition (vulture-class).
  TEST_ONLY  — referenced ONLY by tests: the tests exercise dead production code
               (techniques.md section 9.A). Coverage reports these as covered, so it never flags them.

CANDIDATES ONLY — deletes nothing. Name-based and biased toward LIVE (a shared
name protects every same-named def), so it UNDER-reports. Verify each before
removal (techniques.md section 9 "verify, then delete" + section 8 step 2) — rule out decorator / registry /
dynamic dispatch, __all__ / public surfaces, config-enabled paths. The
DECORATED and PUBLIC tags flag likely false positives ("needs verification",
not "delete").

LAYOUT-AGNOSTIC. Pass your project's real source/test dirs (the agent knows them
from the project map) — that is the reliable path. If you omit them the script
AUTO-DETECTS: a src/app/lib/source layout, else top-level packages (dirs with
__init__.py), else the whole repo; it always adds scripts/tools/bin as
production, excludes tests + vendor dirs, and prints exactly what it scanned. It
fails loud with guidance if it finds no source. For non-Python repos, apply the
techniques.md section 9.A method by hand (LSP "Find References", prod vs test).

Usage:
    python scripts/dead_candidates.py [--root .] [--prod DIR ...] [--tests DIR ...] [--json out.json]
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path

_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_VENDOR = {".git", ".venv", "venv", "env", ".env", "node_modules", "__pycache__",
           "build", "dist", ".tox", ".mypy_cache", ".pytest_cache", "site-packages"}


def _resolve_tests(root: Path, explicit: list[str] | None) -> list[Path]:
    if explicit:
        return [root / d for d in explicit if (root / d).is_dir()]
    found = [root / d for d in ("tests", "test") if (root / d).is_dir()]
    seen = {p.resolve() for p in found}
    for p in sorted(root.iterdir()):
        if (p.is_dir() and p.name not in _VENDOR
                and "test" in p.name.lower() and p.resolve() not in seen):
            found.append(p)
    return found


def _resolve_prod(root: Path, explicit: list[str] | None, tests: list[Path]) -> list[Path]:
    if explicit:
        return [root / d for d in explicit if (root / d).is_dir()]
    prod: list[Path] = []
    for name in ("src", "app", "lib", "source"):  # 1) conventional source roots
        d = root / name
        if d.is_dir() and next(d.rglob("*.py"), None):
            prod.append(d)
    if not prod:  # 2) flat layout — top-level packages (have __init__.py)
        test_set = {t.resolve() for t in tests}
        prod = [p for p in sorted(root.iterdir())
                if p.is_dir() and (p / "__init__.py").is_file()
                and p.resolve() not in test_set and p.name not in _VENDOR]
    for name in ("scripts", "tools", "bin"):  # sibling tooling counts as production
        d = root / name
        if d.is_dir() and next(d.rglob("*.py"), None):
            prod.append(d)
    return prod or [root]  # 3) whole-repo fallback (tests/vendor filtered in _py_files)


def _py_files(dirs: list[Path], tests: list[Path]) -> list[Path]:
    test_roots = [str(t.resolve()) for t in tests]
    out: list[Path] = []
    for d in dirs:
        if not d.is_dir():
            continue
        for p in d.rglob("*.py"):
            if _VENDOR & set(p.parts):
                continue
            rp = str(p.resolve())
            if any(rp.startswith(tr) for tr in test_roots):  # never count tests as production
                continue
            out.append(p)
    return out


def _word_counts(files: list[Path]) -> Counter:
    counts: Counter = Counter()
    for f in files:
        try:
            counts.update(_WORD.findall(f.read_text(encoding="utf-8")))
        except OSError:
            continue
    return counts


def _collect_defs(prod_files: list[Path]):
    """Return (defs: name -> [(file, line, decorated, kind)], public: set[name])."""
    defs: dict[str, list] = defaultdict(list)
    public: set[str] = set()
    for f in prod_files:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # don't echo lint warnings from scanned files
                tree = ast.parse(f.read_text(encoding="utf-8"))
        except (OSError, SyntaxError) as exc:
            print(f"warning: skipping {f}: {exc}", file=sys.stderr)
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
            ):
                for el in getattr(node.value, "elts", []):
                    if isinstance(el, ast.Constant) and isinstance(el.value, str):
                        public.add(el.value)
        for node in ast.iter_child_nodes(tree):  # top-level definitions only
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                defs[node.name].append((f, node.lineno, bool(node.decorator_list), kind))
    return defs, public


def main() -> None:
    ap = argparse.ArgumentParser(description="Find ZERO_REF + TEST_ONLY code candidates (Python).")
    ap.add_argument("--root", default=".", help="repo root (default: current dir)")
    ap.add_argument("--prod", nargs="+",
                    help="source dirs (default: auto-detect src/app/lib/source or top-level packages)")
    ap.add_argument("--tests", nargs="+",
                    help="test dirs (default: auto-detect tests/, test/, and *test* dirs)")
    ap.add_argument("--json", help="optional path to write the candidate ledger as JSON")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    test_dirs = _resolve_tests(root, args.tests)
    prod_dirs = _resolve_prod(root, args.prod, test_dirs)
    prod_files = _py_files(prod_dirs, test_dirs)
    rel = lambda p: str(p.relative_to(root)).replace("\\", "/")
    if not prod_files:
        sys.exit(f"error: no production .py files found under {[rel(d) for d in prod_dirs]}.\n"
                 f"Pass --prod with your source dir(s), e.g.  --prod mypackage")
    test_files = _py_files(test_dirs, [])
    print(f"scanned prod: {[rel(d) for d in prod_dirs]} ({len(prod_files)} files) | "
          f"tests: {[rel(d) for d in test_dirs] or '(none)'} ({len(test_files)} files)")

    defs, public = _collect_defs(prod_files)
    prod_counts = _word_counts(prod_files)
    test_counts = _word_counts(test_files)

    candidates = []
    for name, sites in sorted(defs.items()):
        if name.startswith("__") and name.endswith("__"):
            continue  # dunder / protocol methods are framework-driven
        prod_refs = prod_counts.get(name, 0) - len(sites)  # references beyond the def lines
        test_refs = test_counts.get(name, 0)
        if prod_refs > 0:
            continue  # referenced in production -> LIVE (biased to live)
        verdict = "ZERO_REF" if test_refs == 0 else "TEST_ONLY"
        for f, line, decorated, kind in sites:
            tags = []
            if decorated:
                tags.append("DECORATED")
            if name in public:
                tags.append("PUBLIC")
            candidates.append({"verdict": verdict, "name": name, "kind": kind,
                               "file": rel(f), "line": line, "test_refs": test_refs, "tags": tags})

    candidates.sort(key=lambda c: (c["verdict"], c["file"], c["line"]))
    print(f"defs scanned: {sum(len(v) for v in defs.values())} | "
          f"candidates: {len(candidates)} ({dict(Counter(c['verdict'] for c in candidates))})")
    print("-- verify each before removal (DECORATED/PUBLIC = likely false positive) --")
    for c in candidates:
        tagstr = (" [" + ",".join(c["tags"]) + "]") if c["tags"] else ""
        ref = "" if c["verdict"] == "ZERO_REF" else f" test_refs={c['test_refs']}"
        print(f"{c['verdict']:9} {c['file']}:{c['line']}  {c['name']} ({c['kind']}){tagstr}{ref}")

    if args.json:
        Path(args.json).write_text(json.dumps(candidates, indent=2), encoding="utf-8")
        print(f"\nledger -> {args.json}")


if __name__ == "__main__":
    main()
