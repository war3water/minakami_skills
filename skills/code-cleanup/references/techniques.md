# Techniques — Judgment Gates & Safe Procedures for Cleanup Edits

Loaded during diagnosis and execution. This file does not teach detection — a competent model already finds
forwarding chains, dead code, and duplication on its own. It encodes what models demonstrably get wrong
*without* it: which layers to keep, how to remove things without breaking contracts, and the consolidation /
deletion procedures that preserve behavior. Self-contained; risk tiers and hard rules are in `safety.md`
(co-loaded).

## Contents

1. Every layer must earn its existence
2. How few hops (minimize, then justify)
3. Directness-first; no permanent fallbacks
4. When NOT to flatten
5. Consolidation: splits, merges, cross-entry duplicates
6. Safe-Deletion Playbook
7. Dead-weight verification rules

---

## 1. Every layer must earn its existence

The single governing gate. A function / class / file / branch is worth keeping only if it does at least one
of: defines a real boundary (API, domain, persistence, UI, adapter, CLI); adds validation, transformation,
orchestration, or specific error handling; encapsulates an external dependency; provides a genuine testing
seam or reuse across demonstrably independent callers; or makes the code easier to understand than calling
directly. For inter-file hops: a hop must be a **testing seam**, a **plugin/extension point**, a **layer
boundary a checker enforces**, or **genuine reuse** (callers imposing *different* requirements — not "might
be reused someday"). Pure forwarding, single-impl abstract bases, single-target string dispatchers, and
forwarding manager/service/repo chains fail the gate and are inline/merge *candidates* — judged in context
(§4 first), never removed on pattern-match.

A vague name (`manager`/`handler`/`processor`/`utils`/`common`) you can't make specific usually marks a
layer that does too much or too little (SKILL.md principle 6).

**Judge the gate globally, not only locally** — a hop justified in isolation can be a 1:1 duplicate of
another public entry; always also ask "does another public entry already do this?" (§5 has the sweep).

**The gate applies to your own edits** (`safety.md` self-audit): a layer a refactor *introduces* must pass
the same test, or it is net harm.

---

## 2. How few hops? — minimize, then justify

There is **no target number and no universal "right depth."** Use the fewest hops the feature's real needs
allow; keep only hops that pass the §1 gate, and remove or merge the rest. A low count does not excuse an
unjustified hop; a high count is fine when *every* hop is justified. Record hop counts as a **measurement,
not a goal** — a framework request pipeline that genuinely needs six justified hops keeps all six. A
refactor must not *increase* a touched feature's meaningful-hop count (SKILL.md success criteria).

---

## 3. Directness-first move; no permanent fallbacks

The default way to remove an inter-file hop: **move the code and update every caller atomically, in one
change, with no compatibility wrapper.** Apply when usage is fully enumerable — process-internal code, LSP
"Find References" + grep give the complete caller set, and no dynamic import / reflection / decorator /
registry / config-string dispatch reaches it. Characterize behavior with a test first when coverage is thin,
use deterministic rename/move tooling (`safety.md`), verify green.

**Fallbacks (compatibility wrapper, re-export facade, adapter shim, tombstone) are the bounded exception,
never the default** — only when external or dynamic consumers genuinely cannot be enumerated. When used:
mark clearly as temporary with a **removal trigger**, and track to removal within the same effort (campaign
mode: a ledger item that must reach `done`). **A permanent compatibility layer is a refactor failure** — it
relocated the mess into a new permanent hop. Resolve uncertainty by *enumerating references*, not by
leaving a hop standing.

Removing an **existing** compatibility layer follows the same discipline in reverse: never justify the
removal by breakage **your own refactor created** ("my consolidation broke the shim anyway" is circular —
the consolidation changed a surface the shim was protecting). When consumers cannot be enumerated or no
user is available to approve, **keep-and-flag** the shim; its removal stays high-tier even when cleanup is
broadly commissioned.

---

## 4. When NOT to flatten

Before any inline / collapse, verify the indirection is **not** a real seam. Leave it if it is:

- a **test seam** — grep tests for `mock_<name>` / `patch(... <path> ...)` / `monkeypatch.setattr`; if
  patched, it's a seam (this includes package `__init__` re-exports that tests patch through, and
  module-attribute call styles that patching depends on);
- a **plugin / extension point** — the wrapper, registry, or decorator surface is the stable public
  contract, even when current config selects only one implementation ("unreferenced by shipped config" ≠
  unreachable when dispatch is config-string-driven);
- a **layer boundary with different change cadences** a static checker asserts;
- an **in-progress Branch by Abstraction** — the wrapper is the deliberate abstraction;
- an **audit / compliance hook** wrapping all calls.

If unsure: leave it, mark `needs verification` (`diagnosis.md`), ask the user. And remember scope: a cleanup
ask is not a redesign license — do not replace a live mechanism (registry → static map, decorator →
explicit wiring) or rename a module surface as a side effect of "removing indirection" (`safety.md`).

---

## 5. Consolidation: splits, merges, cross-entry duplicates

**Splitting a mixed-responsibility file:** identify clusters by co-call graph, shared vocabulary, and
co-change history; a cluster you can't give a clear, brief name isn't a cluster. Migrate one cluster at a
time (never big-bang), callers updated per §3 — a facade only if callers are non-enumerable. Don't split
horizontally by layer (interfaces/impls/utils) when the real cohesion is vertical-by-feature.

**Merging drifted duplicates:** compare drift *before* assuming identity — variants often diverge in error
handling, edge cases, or return shape, and sometimes the drift is intentional (keep, with a comment).
Choose the canonical by test coverage → public-surface proximity → error-handling quality (never "newest").
Characterization-test every variant first; migrate callers off temporary shims per §3.

**Parallel public entries (cross-entry duplicate) — sweep ALL public entrypoints, not just the named area.**
Flag any two public functions with near-identical signatures delegating to the same implementation: one is
a redundant Middle Man — delete it and migrate callers to the survivor. A registry/factory/manager resolving
to a single effective implementation on the hot path is the same smell at dispatch level (but check §4's
extension-point test first). When consolidating, prefer **renaming the canonical entry** (subtract a name)
over adding a new name on top of existing wrappers — additive "safety" grows the entry count and makes the
layer worse.

**Tests during consolidation:** when a removed symbol's test asserts a fact a *live* symbol also provides,
**repoint the test at the live symbol** instead of deleting the coverage.

---

## 6. Safe-Deletion Playbook

**All eight steps required before any hard delete.** Deletion is high-tier (`safety.md`).

1. **Establish suspect set** via static tooling (`vulture` / Knip; Python: `scripts/dead_candidates.py`
   flags TEST_ONLY orphans + ZERO_REF). Treat as *suspects*, not a delete list.
2. **Filter through dynamic-use patterns** — string-name references, `importlib` / dynamic `import()`,
   framework decorators, reflection (`getattr`/`hasattr`), config files naming modules, test-discovery
   globs, packaging entry-points.
3. **Cross-repo / external usage check** for library code. Skip only if provably process-internal.
4. **Git last-touched** — `git log -1 -- <path>`, `git log -S 'symbol'`. Unchanged ≠ unused, but
   unchanged-for-years + unreferenced is meaningful.
5. **Tombstone before deletion** — replace body with a logging call, or move to `_archive/` still on the
   import path. Soak (campaign mode: one later-round confirmation). **Dead-until-proven-live.**
6. **Characterize** — a test capturing current behavior even if you intend to delete.
7. **Delete in an isolated change** — one logical deletion per change boundary.
8. **Tag the revert hatch — and verify it exists.** `git tag pre-cleanup-<YYYY-QN>` so restoring is one
   `git revert`. If the tree is **untracked**, there is no git history to restore from — create a baseline
   copy (or preserve removed code verbatim in the report) *before* deleting; never claim a restore path
   without checking it is real.

**Hard rule:** if any of steps (2)(3)(4)(5) is skipped, do not delete — surface the gap and ask the user.

**Proven-dead carve-out:** steps 1–4 are how you *prove* dead. Once they show zero references (including
dynamic and external) and the symbol is a verified test-only orphan or data-flow-dead branch (§7), skip the
tombstone-soak (5) and characterization (6) and remove it directly, with its now-dead tests — **but still
with the user's approval** (the carve-out skips the soak *ceremony*, not the approval).

---

## 7. Dead-weight verification rules

For an exhaustive audit, sweep every top-level symbol in the production tree (waive hotspot ordering — dead
weight collects in cold code). Three finding classes, one shared bar:

- **A — Test-only orphans.** A symbol referenced *only by its own tests* is dead in production unless it is
  a public surface (`__all__`, documented alias, `mock.patch` target). Remove it **with its now-dead tests**
  — but if the orphan's test asserts a fact a *live* symbol also provides, **repoint the test** instead of
  deleting coverage.
- **B — Data-flow dead branches.** A branch gated on a value nothing ever produces (a config flag never set
  on; a field read that nothing writes) is dead even though every name in it resolves.
- **C — Design-level dead weight (reasoning, not tooling).** A symbol, file, or module tied to an
  abandoned upper-layer design — superseded paths, scaffolding for a direction not taken. These are
  *inferences*: hold them to the same evidence bar and be extra careful, since the judgment is yours, not a
  tool's.

**Verify, confirm with the user, then delete.** Every hit is a *candidate*: disprove "live" with code
evidence (dynamic/decorator/registry dispatch, config-enabled paths, public/external surfaces,
non-default-mode fallbacks — §4), then **present the evidence-backed candidates for approval** (batch them
via the needs-verification loop in `diagnosis.md`) and run the §6 playbook. Apply the same lens to tests —
drop tests of removed symbols and *verified*-redundant duplicates, never blanket-cut (the suite is the
behavior-preservation net).
