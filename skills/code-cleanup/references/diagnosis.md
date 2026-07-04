# Diagnosis — Classify, Map Dependencies, Name the Problems

Turn the discovery artifacts into a ranked, evidence-backed worklist. Loaded with `techniques.md` (the
how-to for each recommended action) at the diagnosis stage. Self-contained for the classification itself.

---

## File classification

Classify important files in a table:

| File Path | Current Responsibility | Imported By | Imports | Entry Point? | Risk | Recommended Location | Recommended Action | Notes |
|---|---|---|---|---|---|---|---|---|

`Risk`: **low / medium / high** (the `safety.md` tiers). When uncertain, treat as high and set the Action to
`needs verification` until resolved — "unknown" is a temporary diagnosis state, not a fourth tier.

`Recommended Action` and when each applies:

| Action | Use when |
|---|---|
| **keep** | actively imported, an entry point, framework-loaded, public API, or plugin-registered; role clear and stable. |
| **rename** | the name doesn't reflect responsibility (vague `manager`/`handler`/`utils`), but it's otherwise in the right place doing the right thing. |
| **move** | responsibility is clear but belongs in a different package; caller updates are mechanical (directness-first, `techniques.md` §3). |
| **split** | mixes unrelated responsibilities, multiple independent clusters, a debugging hotspot, or high fan-out with low cohesion (`techniques.md` §5). |
| **merge** | a thin wrapper / several tiny files create indirection without real meaning; maintainers jump across files for one concept. |
| **simplify** | responsibility is correct but the implementation is excessively nested or indirected (`techniques.md` §1–§2, checked against §4). |
| **delete** | not imported, not referenced in production, not dynamically loaded, not a framework convention, not public, and not exercised by a behavioral test of a live feature — and the user approves. (A symbol referenced *only* by its own tests is a test-only orphan: removable with its tests, `techniques.md` §7.) The Safe-Deletion Playbook (`techniques.md` §6) governs. |
| **needs verification** | static analysis is inconclusive; dynamic import / decorator / reflection / external use possible. Resolve via the loop below, batched — not by guessing. |
| **do not touch without tests** | risky and uncovered; consumer surfaces unclear. Add characterization tests (Feathers) before any change. |

**Marking discipline:** never mark `delete` without evidence; if a file may be dynamically loaded, reached
via CLI / plugin / reflection / decorators / framework conventions, mark `high` risk or `needs verification`;
if genuinely unsure, `needs verification` (resolve in batches).

---

## Dependency and call-path analysis

Build a maintainer-oriented map covering: entry points → major call paths; major import dependencies; high
fan-in files; high fan-out files; circular dependencies; cross-domain imports; deep call chains; overly
broad utility modules; files mixing responsibilities; files that make debugging hard.

```text
EntryPointA -> ModuleA.fn -> ModuleB.fn -> ModuleC.fn

core   imports: config, events, models     imported by: app, eval, runtime
eval   imports: core, diagnostics          imported by: CLI only
```

If static call-graph accuracy is uncertain, say so. For deep chains, apply the `techniques.md` §1 gate per
hop; for dead-code / orphans, the Safe-Deletion Playbook (§6) and, for an exhaustive audit, the dead-weight
rules (§7).

---

## Maintainability diagnosis

Name issues using these categories (precise vocabulary makes the diagnosis shared and searchable —
`glossary.md`):

1. Architecture / module-boundary issues
2. **Multi-hop indirection (inter-file)** — feature logic scattered across forwarding layers / folders
3. **Excessive nesting (intra-file)** — deep control flow or forwarding chains inside one function/file
4. **Entry-vs-implementation mixing** — business logic in the entry/wiring layer, or wiring (config, DI,
   I/O setup) scattered through domain code. Use the call-graph node tags (entry / wiring / domain / I/O).
   The fix is the composition-root pattern (imperative shell, functional core): push wiring to the edges,
   keep the core pure.
5. Hidden side effects
6. Duplicate / drifted logic
7. Dead-code candidates
8. Orphaned files
9. Misleading or vague names (`manager`, `handler`, `processor`, `utils`, `common`)
10. Misplaced files
11. Overly broad utilities
12. Circular dependencies
13. Noisy / redundant tests
14. Ineffective warnings
15. Missing onboarding documentation
16. Risky areas without test coverage

These split into the skill's two equal families — **indirection that hurts tracing** (2, 3, 4) and **dead
weight / redundancy** (6, 7, 8, 13) — both fixed via `techniques.md`.

For each issue record: **file path · category · evidence · why it blocks debugging or change · risk level ·
recommended action · verification method · whether behavior may change.**

---

## Needs-verification resolution loop

To keep the `needs verification` bucket from growing forever, periodically gather, per item: cross-repo
usage (`gh search code`, Sourcegraph); internal usage (LSP "Find References" + string-name grep); last touch
(`git log -1`); last referenced (`git log -S`); dynamic-load risk (decorators, registries, entry points);
test mention. Then present the user **one batched yes/no list** ("items 1–7 look safely removable, 8–10 look
like keepers, 11–12 I still can't determine — confirm?"). Do not delete from this loop; promote items to
`delete` or `keep`, then run the Safe-Deletion Playbook (`techniques.md` §6) on the approved set.
