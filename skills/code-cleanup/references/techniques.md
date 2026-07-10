# Techniques — Judgment Gates & Safe Procedures for Cleanup Edits

Loaded during diagnosis and execution. This file does not teach detection — a competent model already finds
forwarding chains, dead code, and duplication on its own. It encodes what models demonstrably get wrong
*without* it: which layers to keep, how to remove things without breaking contracts, and the consolidation /
deletion procedures that preserve behavior. Self-contained; risk tiers and hard rules are in `safety.md`
(co-loaded whenever this file executes a change).

## Contents

1. Every layer must earn its existence
2. How few hops (minimize, then justify)
3. Directness-first; no permanent fallbacks
4. When NOT to flatten
5. Restructuring: splits, decomposition, merges, cross-entry duplicates
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

**Decomposition is not a hop increase.** That "no increase" rule targets cross-unit *tracing* hops —
forwarding layers a maintainer must jump through to follow one feature. Breaking a single over-large unit
into cohesive, named local helpers (§5) adds functions but *reduces* what a maintainer holds in their head;
it does not count against the hop budget. Adding functions is the correct fix for a god function — the §1
gate is the brake against over-extraction, not a reason to leave the monolith intact.

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

*Which "facade"?* A **re-export facade** here means a **compatibility shim** — it forwards to code that lives
elsewhere, so it is bounded and tracked to removal (Stage 6). A package's own `__init__` re-exporting its
private submodules is **not** that: it is the package's **canonical public surface** — one permanent hop, the
correct end-state of a subpackage split (§5), never a fallback to retire.

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

## 5. Restructuring: splits, decomposition, merges, cross-entry duplicates

**Splitting a mixed-responsibility file:** identify clusters by co-call graph, shared vocabulary, and
co-change history; a cluster you can't give a clear, brief name isn't a cluster. Migrate one cluster at a
time (never big-bang), callers updated per §3 — a facade only if callers are non-enumerable. Don't split
horizontally by layer (interfaces/impls/utils) when the real cohesion is vertical-by-feature.

**Finishing a split — the back-edge test.** A split is not done while a *back-edge* remains: the parent
re-exporting symbols it imports from its own new shards, or a shard importing shared helpers / base types /
constants back from the parent. That back-edge is a module-level cycle (an import at file-bottom or under
`# noqa: E402` is the same cycle, only hidden), and a re-export facade whose callers *are* enumerable is the
permanent-forwarding failure of §3, not an end state. Two moves finish it: (1) **sink the shared surface into
a leaf** — move the helpers / base types / constants both sides need into a lower module the parent and every
shard import *downward only*, turning the cycle into a DAG; (2) **if the shards are private to the unit**
(callers reach them only through the one facade), **promote the group to a subpackage** whose `__init__` is
the facade and whose shards are `_`-prefixed private modules — mirror the repo's own package idiom if it has
one. A package `__init__` re-exporting its own private leaves is the unit's canonical
public surface (one hop), not the inter-module forwarding hop §3 discourages. **Flatness itself is not the
smell:** genuinely independent shards — no shared-helper back-edge, no cross-import — stay flat as siblings;
the back-edge, not the file count, is what forces the package.

**Decomposing an over-large function/class (long method / god function):** extract cohesive, named
sub-units along the seams where the body shifts responsibility — each extraction is one nameable job over a
related set of locals (if you can't name it in a few words, it isn't a clean seam). Keep helpers private and
adjacent unless independently reused; don't build a forwarding chain, and don't extract one-line or
un-nameable fragments (that trades a long body for scattered noise — the §1 gate applies in the additive
direction too). This ADDS functions on purpose; §2 says why that is not an indirection increase.

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

**Work all eight steps for any hard delete** — steps 1–6 before you delete, step 7 is the deletion itself,
step 8 secures the revert hatch. Deletion is high-tier (`safety.md`). Approval
semantics are owned by the **Deletion gates in SKILL.md**: approval-tier items (documented extension
points, outward-facing shims/re-exports, config-reachable registrations, and their pinning tests) need the
user's explicit per-item confirmation, and **when no user is reachable the disposition is keep + flag —
delete-with-backup is not a substitute for approval.** This playbook is the *procedure* for items the
gates have cleared.

1. **Establish suspect set** via static tooling (`vulture` / Knip; Python: `scripts/dead_candidates.py`
   flags TEST_ONLY orphans + ZERO_REF). Treat as *suspects*, not a delete list.
2. **Filter through dynamic-use patterns** — string-name references, `importlib` / dynamic `import()`,
   framework decorators, reflection (`getattr`/`hasattr`), config files naming modules, test-discovery
   globs, packaging entry-points.
3. **Cross-repo / external usage check** for library code. Skip only if provably process-internal.
4. **Git last-touched** — `git log -1 -- <path>`, `git log -S 'symbol'`. Unchanged ≠ unused, but
   unchanged-for-years + unreferenced is meaningful.
5. **Tombstone before deletion** — keep the original behavior and *add* a logging call (log-and-delegate:
   record the call, then run the real body), or move to `_archive/` still on the import path. Do **not**
   replace the body with a bare log — that changes behavior, and a non-enumerable live consumer (the exact
   thing the soak exists to catch) would break *during* the soak. Soak = **one later-round confirmation**
   (campaign mode). **A single pass has no later round, so a not-proven-dead deletion cannot COMPLETE in one
   pass** — defer it to campaign mode or keep-and-flag for the user; only the proven-dead carve-out below
   deletes without a soak. **Dead-until-proven-live.**
6. **Characterize** — a test capturing current behavior even if you intend to delete.
7. **Delete in an isolated change** — one logical deletion per change boundary.
8. **Secure the revert hatch — and verify it exists.** Tag the pre-deletion commit with a unique,
   non-colliding name (e.g. `git tag pre-cleanup-<short-sha>` — not a date, which collides on a second
   cleanup) so a removed file is restorable with `git restore --source=<tag> -- <path>`. (A tag only marks a
   commit; `git revert <tag>` would invert the *tagged* commit, not the deletion — and it creates a commit,
   which the commit-only-when-asked rule forbids.) If the tree is **untracked**, there is no git history to
   restore from — create a baseline copy (or preserve removed code verbatim in the report) *before* deleting;
   never claim a restore path without checking it is real.

**Hard rule:** if any of steps (2)(3)(4) — or (5), unless the Proven-dead carve-out below applies — is
skipped, do not delete: surface the gap and ask the user.

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
non-default-mode fallbacks — §4), then **present the evidence-backed candidates for approval as one batched
yes/no list** (grouped: safely-removable / keepers / still-undetermined) and run the §6 playbook. Apply the same lens to tests —
drop tests of removed symbols and *verified*-redundant duplicates, never blanket-cut (the suite is the
behavior-preservation net).
