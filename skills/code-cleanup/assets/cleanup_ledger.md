# Cleanup Campaign Ledger

Copy to the agent-work directory (location rules: SKILL.md) for campaign mode. A fresh session reads it and
resumes — see `references/campaign-mode.md`.

- **Goal:** <one line — what "clean enough" means for this repo>
- **Acceptable end state:** <deliberately-imperfect "done" — e.g. "hotspots untangled, dead weight removed,
  test suite deduped; cosmetic nesting in cold code left for later">
- **Scope contract:** auto = low+medium within `<N>` files/round; checkpoint = all high-risk; max `<M>` rounds then ask
- **Coverage:** `<X>` / `<Y>` source files deeply reviewed
- **Started:** `<date>` · **Last updated:** `<date>` (round `<N>`)

## Item index

| ID  | Title                            | Category              | Evidence                            | Risk | Status   | Scope |
|-----|----------------------------------|-----------------------|-------------------------------------|------|----------|-------|
| C01 | Inline `_run_impl` pass-through  | excessive indirection | body is `return run(args)`; 1 caller| low  | done     | in    |
| C07 | Delete `legacy_export.py`        | dead code             | ZERO_REF; untouched 19 mo           | high | soaking  | in    |
| C12 | Split `services.py` (3 clusters) | mixed responsibility  | co-change + vocabulary clusters     | med  | proposed | in    |

## Item detail (for non-trivial items)

### C07 — Delete `legacy_export.py`

- **Evidence:** ZERO_REF (reachability sweep); `git log -1` → untouched 19 months; no dynamic / decorator / registry hit.
- **Risk:** high (irreversible) → checkpointed before execution.
- **Lifecycle:** proposed → approved (round 2) → soaking (tombstoned round 2, confirm round ≥ 3)
- **Soak:** tombstone shipped round 2; hard-delete only after a later round surfaces no consumer.
- **Verification:** project tests green before and after; LSP "Find References" + grep = 0 production refs.

## Status lifecycle

```text
proposed -> approved -> in-progress -> done
   |                        |
   |                        +-> soaking -> done        (deletes only)
   +-> rejected (evidence insufficient, or duplication intentional)
parked  (out-of-scope; reconsidered in a later round's SURVEY)
```
