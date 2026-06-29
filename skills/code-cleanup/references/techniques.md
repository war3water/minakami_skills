# Techniques — Reducing Multi-Hop Code

The concrete catalog for the skill's central job: making a feature **directly** readable and debuggable
by removing indirection that does not earn its keep. Loaded during diagnosis and execution (SKILL.md
names when). This file is self-contained — apply it without a second-hop load. High-risk actions
(delete, public-surface change) follow the tiers in `safety.md`, which SKILL.md loads alongside this file.

## Contents

1. What multi-hop code is (intra-file and inter-file)
2. Every layer must earn its existence
3. How few hops (minimize, then justify)
4. Directness-first move (no fallback)
5. Reduce-nesting catalog
6. Splitting a mixed-responsibility file
7. Consolidating duplicate / drifted implementations
8. Safe-Deletion Playbook
9. Dead-weight sweep (reachability + data-flow)

---

## 1. What multi-hop code is

**Multi-hop code** = a simple feature cannot be understood or debugged directly because the real logic is
reached only after jumping through layers that add no clear meaning. It appears in **two forms, both of
which raise read-and-understand cost** and both of which this skill targets:

- **Inter-file (call-graph) multi-hop** — the logic is scattered across many files, wrappers, factories,
  registries, callbacks, or inheritance layers, often spanning unrelated folders. Tracing one feature
  means losing the thread across file jumps.

  ```text
  Bad:  entry → wrapper → dispatcher → resolver → handler factory → base class
              → plugin registry → service wrapper → utility → actual logic
  Good: entry point → clear orchestrator → core domain logic → adapter/repository (if needed)
  ```

- **Intra-file multi-hop** — within a single function or file: deep control-flow nesting, long forwarding
  chains, or a "god" function where the real step is buried under guard pyramids and ceremony. No file
  jump, but the same effect — you cannot see the real logic directly.

The problem is **not** "many files" or "many lines." The problem is hops that **do not add meaning**:

```text
Bad:  run_task() → execute_task() → process_task() → handle_task() → do_task()   (pure forwarding)
Good: API layer → domain logic → repository/external service                      (real boundaries)
```

---

## 2. Every layer must earn its existence

This is the single governing rule. A function / class / file / branch is worth keeping only if it does at
least one of these:

1. Defines a real boundary — API, domain, persistence, UI, adapter, CLI.
2. Adds validation, transformation, orchestration, or specific error handling.
3. Encapsulates an external dependency's behavior.
4. Provides a genuine testing seam or reuse across **demonstrably independent** callers.
5. Makes the code easier to understand than calling the next layer directly.

For inter-file hops the same gate is stated as four justifications — a hop must be a **testing seam**, a
**plugin/extension point**, a **layer boundary a static checker enforces**, or **genuine reuse**. The "rule
of three" is a useful Fowler heuristic, but the real test is whether callers impose *different*
requirements on the abstraction. (Background: Ousterhout's deep modules — prefer one deep module to many
shallow wrappers.)

**Signals a layer probably doesn't earn its keep** — inline/merge *candidates* to weigh with judgment, not an
auto-remove checklist. Check §5.3 ("when NOT to flatten") and the surrounding design first; a matching layer
can still be justified by context the pattern can't see. When value is unclear, leave it and mark
`needs verification` rather than removing on pattern-match alone:

- renames a function, or forwards arguments unchanged (`return other_thing(args)`);
- calls another wrapper;
- is an interface / abstract base with exactly one production implementation (test doubles don't count if
  mock-by-spec works);
- is a dispatcher forwarding by string-name lookup to a single concrete type;
- is a manager → service → repository → DAO chain where each layer just forwards;
- adds generic logging with no useful context, or hides the real implementation;
- uses dynamic dispatch where a static direct call is enough.

**Avoid vague names** — `manager`, `handler`, `processor`, `utils`, `common`, `helpers` — unless the
responsibility is specific and documented. A name you can't make specific is usually a layer that does too
much or too little.

**Judge the gate globally, not only locally.** A hop can pass the test in isolation ("it's a public
back-compat API") while being *globally* redundant — a 1:1 duplicate of another public entry that already does
the same thing. For every layer also ask: **does another public entry already do this?** Sweep all public
entrypoints, not just the one in front of you (§7, cross-entry duplicates).

**This gate applies to your own edits, not only to the existing code.** See `safety.md` (Agent self-audit):
AI agents systematically over-produce indirection; every layer a refactor *introduces* must pass this same
test, or it is net harm.

---

## 3. How few hops? — minimize, then justify

There is **no target number, and no universal "right depth."** The rule is: **use the fewest hops the
feature's real needs allow, and keep a hop only when it is the *necessary* choice** — when it earns its
existence (§2) through a real boundary or specialized module, a testing/verification seam, a
plugin/extension point, or genuine reuse. If a hop is not necessary for one of those reasons, remove or
merge it. A low count does not excuse an unjustified hop; a high count is fine when *every* hop is justified.

Treat the hop count as a **measurement, not a goal** — record it to compare before/after and to surface
unjustified hops, never to hit a quota. A well-factored basic feature usually collapses to a small handful
of meaningful hops, but that is a *result* of removing the unjustified ones, not a band to aim for: a feature
that genuinely needs six justified hops (e.g. a framework request pipeline) keeps all six; one that needs one
keeps one. Calibrate "necessary" by reading well-maintained OSS (`architecture.md`). A refactor must not
*increase* a touched feature's meaningful-hop count (SKILL.md success criteria).

---

## 4. Directness-first move (no fallback)

The default way to reduce an inter-file hop is to **move the code to where it belongs and update every
caller atomically, in one change, with no compatibility wrapper** — landing directly at the clean state.

Apply directness-first when usage is **fully enumerable**:

- the code is process-internal (not a published library surface);
- LSP "Find References" + `git grep` give the *complete* caller set;
- no dynamic import / reflection / decorator / registry / config-named-module dispatch reaches it.

Procedure: characterize behavior with a test first (§8 step 6 pattern), then use the IDE / LSP
rename / move-symbol command across all callers (deterministic engines per `safety.md`), verify green,
done. No wrapper, no facade, no shim.

**Fallbacks (compatibility wrapper, re-export facade, adapter shim, tombstone) are the bounded exception,
never the default.** Use one *only* when external or dynamic consumers genuinely cannot be enumerated
(published API, plugin entry points, reflection). When you must:

- mark it clearly as temporary and record a **removal trigger**;
- track it to removal **within the same effort** (in campaign mode, a ledger item that must reach `done`);
- **a permanent compatibility layer is a refactor failure, not a safe outcome** — it merely relocated the
  mess into a new permanent hop.

Resolve uncertainty by *enumerating references*, not by leaving a hop standing: a wrapper is justified only
by genuinely non-enumerable consumers, never by "this might be used."

---

## 5. Reduce-nesting catalog

Covers both inter-file call chains and intra-file control-flow nesting.

### 5.1 Diagnostic pass (read-only)

For each function on the path, ask:

- **One caller?** → Inline Function candidate.
- **Body is a single `return next.call(args)`?** → pass-through wrapper (Ousterhout "shallow module").
- **Abstract base with exactly one production implementation?** → Collapse Hierarchy / Replace Superclass
  with Delegate.
- **Manager → service → repository → DAO chain that only forwards?** → flatten by Removing Middle Men.
- **String-keyed dispatcher routing to one concrete type?** → Remove Middle Man.
- **Intra-file: guard pyramids / deep `if` nesting?** → extract early returns (guard clauses); lift the
  happy path to the top level of the function.

### 5.2 Allowed micro-refactors (one logical change at a time, tests green between)

The "When" describes a recognizable pattern, not a counting trigger. Numeric heuristics (rule of three,
fan-in/out, line counts) are signals to triangulate, not preconditions.

| Operation | When |
|---|---|
| Inline Function | A wrapper obscures the real work, adds no vocabulary, and is not a seam, extension point, or recursion boundary. |
| Inline Class | A class is ceremony around data or pass-through behavior; collapsing it makes the caller clearer. |
| Combine Functions into Class | Several functions orbit one concept or evolving state and callers already treat them as one responsibility. |
| Move Function / Move Class | Its vocabulary, data, and change reasons belong with another module's responsibility. |
| Replace Subclass with Delegate | Inheritance is used for reuse rather than genuine substitutability. |
| Remove Middle Man | An object mostly relays calls without adding policy, isolation, or domain meaning. |
| Replace Guard Pyramid with Early Returns | Intra-file: deep nesting hides the main path. |

### 5.3 When NOT to flatten

Before any inline / collapse, verify the indirection is **not** a real seam. Leave it if it is:

- a **test seam** — grep tests for `mock_<name>` / `patch(... <path> ...)`; if patched, it's a seam;
- a **plugin / extension point** — the wrapper is the stable public surface;
- a **layer boundary with different change cadences** a static checker asserts;
- an **in-progress Branch by Abstraction** — the wrapper is the deliberate abstraction;
- an **audit / compliance hook** wrapping all calls.

If unsure: leave it, mark `needs verification` (`diagnosis.md`), ask the user.

---

## 6. Splitting a mixed-responsibility file

Goal: one cohesive responsibility per file. Recognize clusters within the file by triangulating three
signals — none alone sufficient:

- **Co-call graph** — functions that call each other / share helpers belong together.
- **Shared vocabulary** — same domain object, similar parameter / return shapes.
- **Co-change history** — `git log --name-only --follow -- <file>` + blame on line ranges shows which
  functions get edited together.

If a candidate cluster can't be given a clear, brief name, it isn't a cluster — re-evaluate.

Migrate one cluster at a time, not big-bang: extract to a responsibility-named module (match the project's
naming convention), characterize behavior with tests, migrate callers via LSP move-symbol (directness-first
§4 — only leave a facade if callers are non-enumerable), verify green between steps.

**Anti-patterns:** splitting horizontally by layer (interfaces / impls / utils) when the real cohesion is
vertical-by-feature just relocates cognitive load; modules so granular each needs `__init__.py` re-exports
inflate ceremony. **Wouldn't apply** to an intentional thin facade, a generated artifact, or a single
high-cohesion config object whose length is illusory.

---

## 7. Consolidating duplicate / drifted implementations

Goal: one canonical implementation per logical operation. Detect duplicates by **cohesion of intent**, not
exact text — shared signatures, same domain inputs → same logical output, or AST similarity when grep is
inconclusive.

**Parallel public entries (cross-entry duplicate) — sweep ALL public entrypoints, not just the named area.**
Flag any two public functions with near-identical signatures that delegate to the same implementation: one is
a redundant Middle Man — delete it and migrate callers to the survivor. A registry / factory / manager that
resolves to a single effective implementation on the hot path is the same smell at the dispatch level — inline
it. When consolidating, prefer **renaming the canonical entry** (subtract a name) over adding a new name on top
of existing wrappers (additive "safety" that grows the entry count and makes the layer *worse*).

Compare drift before assuming identity: variants usually diverge in error handling, edge cases, or return
shape. Sometimes drift is intentional (different error policies per domain) — keep those, with a comment
explaining why the duplication is real.

Choose canonical (priority, local context can override): highest test coverage → closest to the public API
surface → cleanest error handling. Don't pick the newest just because it's newest.

Migrate without losing behavior: characterization tests for every variant first; promote the canonical;
for each non-canonical variant add a temporary adapter shim (a *bounded* fallback per §4), migrate callers
off shims, remove shims once unreferenced.

---

## 8. Safe-Deletion Playbook

**All eight steps required before any hard delete.** Deletion is a high-risk tier (`safety.md`).

1. **Establish suspect set** via static tooling (`vulture` / Knip / ts-unused-exports; for Python,
   `scripts/dead_candidates.py` also flags TEST_ONLY orphans + ZERO_REF). Treat as *suspects*, not a delete list.
2. **Filter through dynamic-use patterns** — string-name references, `importlib` / `__import__` / dynamic
   `import()`, framework decorators (`@app.route`, `@pytest.fixture`, Django URLs, serializer `Meta`),
   reflection (`getattr`/`hasattr`), config files naming modules, test-discovery globs,
   `[project.entry-points]`.
3. **Cross-repo / external usage check** for library code (`gh search code`, Sourcegraph, sibling-repo
   grep). Skip only if provably process-internal.
4. **Git last-touched** — `git log -1 --format=%ad -- <path>`, `git log -S 'symbol'`. Unchanged ≠ unused,
   but unchanged-for-years + unreferenced is meaningful.
5. **Tombstone before deletion** — replace body with a logging call, or move to `_archive/` still on the
   import path, with a deprecation-log on first use. Soak (in campaign mode, one later-round confirmation).
   **Dead-until-proven-live.**
6. **Characterize** (Feathers) — write a test capturing current behavior even if you intend to delete.
7. **Delete in an isolated change** — one logical deletion per change boundary. Message (if committing):
   `chore(cleanup): remove <thing> — unreferenced since <date>, archived <date>`.
8. **Tag the revert hatch** — `git tag pre-cleanup-<YYYY-QN>` before the deletions so restoring is one
   `git revert`.

**Hard rule:** if any of steps (2)(3)(4)(5) is skipped, do not delete — surface the gap and ask the user.

**Proven-dead carve-out (avoid ceremony when evidence is conclusive).** Steps 1–4 are how you *prove* dead.
Once they show zero references (including dynamic / decorator / registry / external), and the symbol is a
verified test-only orphan or a data-flow-dead branch (§9), skip the tombstone-soak (5) and characterization
(6) and remove it directly, with its now-dead tests — **but still with the user's approval** (deletion stays
high-tier, `safety.md` §1; the carve-out skips the soak *ceremony*, not the approval). The full soak is for
suspected-but-possibly-live code, not code already proven dead.

---

## 9. Dead-weight sweep (reachability + data-flow)

§8 seeds suspects from name/AST tools, which catch **name-orphans** but miss code that is *referenced yet
dead*. For an **exhaustive dead-weight audit** (not a navigability pass): scan **every** top-level symbol
in the whole production tree — exhaustiveness, not a sample, is what guarantees no corner is omitted — and
**waive the hotspot prioritization** (dead weight collects in cold code).

- **A — Production reachability (test-only orphans).** A symbol referenced *only by its own tests* passes
  both name-resolution and coverage. Split references into production vs test-only (Python:
  `scripts/dead_candidates.py` emits this partition). A test-only symbol that is **not** a public surface
  (`__all__`, documented alias, or a `mock.patch` target) is an orphan; remove it **with its now-dead tests**.
- **B — Data-flow dead branches.** A branch is unreachable even when its function runs if it turns on a
  value never produced: a config flag defaulting off and never set on; a key/field **read** that nothing
  **writes**; a struct field the sole constructor never sets and no consumer reads.
- **C — Design-level dead weight (reasoning, not tooling).** A symbol, file, or whole module tied to an
  upper-layer design that is no longer used — an abandoned feature, a superseded code path, scaffolding for a
  direction not taken. These surface from architectural reasoning and context, not a mechanical scan, so they
  are *inferences*: hold them to the same evidence bar (prove nothing live reaches them) and be extra careful,
  since the judgment is yours, not a tool's.

**Verify, confirm with the user, then delete.** Treat each hit — from tooling, data-flow, or design reasoning
— as a *candidate*; disprove "live" with code evidence (rule out dynamic/decorator/registry dispatch,
config-enabled paths, public/external surfaces, non-default-mode fallbacks). Deletion is high-risk
(`safety.md` §1): **present the evidence-backed candidates to the user and get approval before removing**
(batch them via the needs-verification loop in `diagnosis.md`), then run the §8 playbook. Apply the same lens
to tests — drop tests of removed symbols and *verified*-redundant duplicates, but never blanket-cut (the suite
is the behavior-preservation net).
