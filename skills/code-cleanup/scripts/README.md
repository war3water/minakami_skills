# Scripts

Two deterministic helpers are **implemented** and used by the workflow; everything else the skill needs is a
cheap manual procedure (below). Both scripts are stdlib-only and mark **candidates** — they never delete
anything (the Safe-Deletion Playbook in `references/techniques.md` §8 governs deletion).

## Implemented

### `hotspots.py` — churn × size (prioritization signal)

```bash
python scripts/hotspots.py [--root .] [--days 365] [--top 30]
```

Ranks tracked files by commit churn × current LoC so you *order* found problems by likely pain, not decide
what to inspect. Git history only; language-agnostic. Churn is a prioritization signal, never a gate — see
`references/discovery.md` (cold-code problems are never filtered out).

### `dead_candidates.py` — dead-code + test-only-orphan scanner — Python only

```bash
python scripts/dead_candidates.py [--root .] [--prod DIR ...] [--tests DIR ...] [--json out.json]
```

Lists top-level functions/classes that are `ZERO_REF` (never referenced) or `TEST_ONLY` (referenced only by
tests — the class `vulture` and coverage both miss). **Pass your project's real source/test dirs** (from the
project map); omit them to auto-detect a `src`/`app`/`lib`/`source` layout or top-level packages (plus
`scripts`/`tools`), which it prints. Candidates only; tags `DECORATED` / `PUBLIC` as likely false positives
— verify each per `references/techniques.md` §9 before removal. For non-Python repos, apply the §9 method by
hand (LSP "Find References", production vs test).

## Manual procedures (no script needed)

These analysis steps are cheap to do by hand — no script required:

| Task | How |
|---|---|
| Find entry points | grep for `if __name__ == "__main__"`, `def main(`, `[project.scripts]` in `pyproject.toml`, `bin:` in `package.json`, `cmd/*/main.go` |
| Collect imports | `grep -rn "^import\|^from" --include='*.py'`; install `pydeps` on demand for graphs |
| Classify files | LLM read-pass over module docstrings + directory names (`references/techniques.md` §2) |
| Fill the architecture report | hand-fill `assets/architecture_report.md` from grep + LSP "Find References" |
