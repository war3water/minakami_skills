# Scripts

Two deterministic helpers are **implemented** and called by the workflow; the
rest remain a roadmap (use the manual fallback). All scripts are stdlib-only and
mark **candidates** — they never delete anything (see PATCHES.md §6).

## Implemented

### `hotspots.py` — churn × size (PATCHES.md §4)

```bash
python scripts/hotspots.py [--root .] [--days 365] [--top 30]
```

Ranks tracked files by commit churn × current LoC so you refactor the hotspots,
not whatever file is in context. Git history only; language-agnostic.

### `dead_candidates.py` — dead-code + test-only-orphan scanner (PATCHES.md §6, §15) — Python only

```bash
python scripts/dead_candidates.py [--root .] [--prod DIR ...] [--tests DIR ...] [--json out.json]
```

Lists top-level functions/classes that are `ZERO_REF` (never referenced) or
`TEST_ONLY` (referenced only by tests — the class `vulture` and coverage both
miss). **Pass your project's real source/test dirs** (from the Phase-1 map); omit
them to auto-detect a `src`/`app`/`lib`/`source` layout or top-level packages
(plus `scripts`/`tools`), which it prints. Candidates only; tags `DECORATED` /
`PUBLIC` as likely false positives — verify each per §15.3 before removal. For
non-Python repos, apply the §15.A method by hand (LSP "Find References", prod vs test).

## Roadmap (not implemented — manual fallback)

| Script | Manual fallback |
|---|---|
| `find_entrypoints.py` | grep for `if __name__ == "__main__"`, `def main(`, `[project.scripts]` in `pyproject.toml`, `bin:` in `package.json`, `cmd/*/main.go` |
| `collect_imports.py` | `grep -rn "^import\|^from" --include='*.py'`; install `pydeps` on demand for graphs |
| `classify_files.py` | LLM read-pass over module docstrings + directory names (PATCHES.md §2) |
| `generate_architecture_report.py` | hand-fill `templates/architecture_report.md` from grep + LSP "Find References" |
