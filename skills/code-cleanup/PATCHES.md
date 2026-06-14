# Patches and Reference Material

These are evidence-based augmentations to `SKILL.md`. `SKILL.md` is the
backbone (the user-authored brief). This file extends or overrides it
where empirical research and a best-practice survey reveal gaps.

Loaded on demand by the agent — either when `SKILL.md` references this
file, or when the agent needs concrete techniques the backbone names
but does not detail.

**Where this file conflicts with `SKILL.md`, this file wins.**

Sources behind these patches: Fowler (*Refactoring*), Feathers (*Working Effectively with Legacy Code*),
Ousterhout (*A Philosophy of Software Design*), Tornhill/CodeScene (hotspots), the Mikado Method, *Software
Engineering at Google*, and arXiv 2511.04824 + 2411.04444 (agentic-refactoring studies) — full list in §12.

---

## Contents

1. Engineer's First-Impression Test · 2. Four Design Principles · 3. Hard Safety Rules · 4. Hotspot Precondition · 5. Reduce-Nesting Technique Catalog · 6. Safe-Deletion Playbook · 7. Needs-Verification Resolution Loop · 8. Small-Project Fast Path · 9. Macro vs Micro Refactor · 10. Google + Reputable OSS Structural Exemplars · 11. Errata to SKILL.md · 12. References · 13. Glossary of Professional Problem Categories · 14. Recommended Tools · 15. Dead-weight sweep — reachability + data-flow

---

## 1. Engineer's First-Impression Test

Apply **before** SKILL.md Phase 0. Read the project as a software
engineer who just walked in. Answer four questions out loud:

1. **Entry point** — Can you find the program's startup path quickly, or are you hunting through layers of bootstrap and conditional initialization to figure out where execution actually begins? Is the wiring-up separated from the real work?
2. **Trace** — Pick one user-visible feature. Can you follow its execution end-to-end without losing the thread, or do you keep losing context across file jumps and have to backtrack?
3. **Vocabulary** — Do module names mean the same thing across the
   project? Does `core/` describe one thing, or three different things?
4. **One way** — For each responsibility (config loading, HTTP, logging,
   storage), is there ONE implementation, or competing implementations?

A "no" answer is the refactor target. Don't invent other targets.

---

## 2. Four Design Principles (apply throughout)

Priority order — earlier wins ties.

### Principle 1 — Clear, ambiguity-free classification

Every module has a single nameable responsibility. If a module's name keeps growing into compound phrases that hedge across multiple jobs, or you find yourself reaching for words like "helpers" or "utilities" or "common", it's doing too much — split it.

**Concrete techniques:**

- Name modules by responsibility, not by technology (`billing/`, not `utils/`; `auth/`, not `helpers/`). If a module's purpose resists a brief, scannable name — if you keep falling back to "stuff" or "helpers" or compound names that hedge across responsibilities — it does too much. Split into modules whose names actually describe what's inside.
- The module's `__init__.py` / `index.ts` / `mod.rs` re-exports the public surface; nothing else.
- If two functions are consistently used together — same callers, same contexts, same change-reasons — they belong in the same file. Test imports and co-call frequency are useful signals to triangulate, not a threshold to count against.

### Principle 2 — No call nesting unless strongly justified

**Default: flat composition.** Indirection must justify itself with
ONE of:

1. **Testing seam** — wrapper exists to be mocked. Verify: grep tests
   for `mock_<name>` or `patch(... <path> ...)`. If zero hits, it's
   not a seam.
2. **Plugin / extension point** — third parties will provide
   implementations.
3. **Layer boundary** — wrapper enforces a one-way dependency
   direction a static checker is asserting.
4. **Genuine reuse** — demonstrated reuse across multiple callers with independent change-reasons, not "someone might use it eventually." The rule of three is a useful Fowler-derived heuristic, but the real test is whether the callers actually impose different requirements on the abstraction.

If none apply, **inline the wrapper**.

**Anti-patterns to inline on sight:**

- A function whose entire body is `return other_thing(args)`.
- An interface / abstract base with exactly one production
  implementation (test doubles don't count if mock-by-spec works).
- A dispatcher forwarding by string-name lookup to one concrete type.
- A manager → service → repository → DAO chain where each layer adds
  no logic.

Background: Ousterhout's "deep modules" principle — prefer one deep
module to many shallow wrappers.

### Principle 3 — Match Google + reputable OSS structure

When proposing a target layout (SKILL.md Phase 5), **cite which
exemplar you mirror and why**. Don't invent novel layouts. See §10
for the exemplar table.

### Principle 4 — Less is more (Occam's Razor)

- Fewer files beats more files.
- Fewer abstractions beats more abstractions.
- Fewer layers beats more layers.
- Fewer config knobs beats more config knobs.

Apply to the refactor itself: prefer the smallest set of moves that
resolves the diagnostic. If two designs are equivalent in correctness
and testability, **pick the smaller one**.

A "complete refactor" with 300 file moves is rarely the right answer.
A "single biggest pain point" refactor with 5 file moves usually is.

---

## 3. Hard Safety Rules (override SKILL.md "Implementation Rules" where they conflict)

Non-negotiable. They block the most common failure modes documented
in arXiv 2511.04824 and arXiv 2411.04444.

### A1. Revert on Red — never fix-forward during refactor

If a refactor edit makes tests / typecheck / build go red:

1. **Revert ONLY the files the agent edited this session.**
   `git restore -- <file1> <file2> ...` listing the exact paths.
   **Never** run `git restore .`, `git restore --staged .`, or
   `git checkout -- .` — those wipe uncommitted user changes in
   unrelated files. If unsure which files belong to this session,
   `git stash push --keep-index --include-untracked -m "refactor-rollback"`
   stashes everything safely so the user can recover.
2. Record the broken thing as a **prerequisite node** — a smaller
   slice that must land first.
3. Try the smaller slice.

Never push through a red build by writing more refactor code on top.
This is the Mikado-method discipline.

**Pre-refactor hygiene:** before starting a refactor stage, confirm
the working tree is clean (`git status`). If the user has uncommitted
changes, ask them to stash or commit first. Refactor in a clean tree
so rollbacks are unambiguous.

### A2. Commit hygiene

- One refactor catalog entry per commit where feasible.
- Commit prefix: `refactor:` or `chore(cleanup):` for deletions.
- **A refactor commit contains only refactoring.** No feature changes,
  no bug fixes, no behavior changes.
- arXiv 2511.04824 (Nov 2025): **53.9% of AI-agent refactors are
  tangled with feature commits.** This rule blocks that dominant
  failure mode.

### A3. RefactoringMirror — plan with LLM, execute with deterministic engines

When a deterministic refactor exists (IDE Inline Function / Rename /
Move / Extract; `ruff` autofix; `rope`; LSP code actions; IntelliJ /
VS Code refactor actions), **prefer it over a hand-written diff**.

LLM proposes *what* to refactor and *why*. Deterministic engine
produces the *diff*. arXiv 2411.04444 found 7.4% of LLM-generated
refactors changed behavior or broke syntax — deterministic engines
do not have this failure mode.

---

## 4. Hotspot Precondition (extends SKILL.md Phase 5 target selection)

Before nominating any structural change, gather evidence:

```bash
# Churn — files touched most in the last 365 days
git log --since='365 days ago' --pretty=format: --name-only \
  | grep -v '^$' | sort | uniq -c | sort -rn | head -30
```

Or run `python scripts/hotspots.py` (churn × LoC, language-agnostic — the same
intersection in one command).

Then cross-reference churn ∩ complexity (LoC, cyclomatic, cognitive).
That intersection is the hotspot set.

Tornhill / CodeScene published data: **2–3% of files attract 11–16%
of commits.** Refactor those, not whichever file is in context.

If the user asks "clean up everything", reply with the hotspot
shortlist first. Don't propose moves to cold files unless the user
names them explicitly.

---

## 5. Reduce-Nesting Technique Catalog (extends SKILL.md Phase 4 "excessive nesting")

This section is the concrete answer to "reduce nesting of calling
for debug friendliness."

### 5.1 Diagnostic pass (read-only)

For each function in the hotspot set, ask:

- **One caller?** → Inline Function candidate.
- **Body is a single `return next.call(args)`?** → Pass-through wrapper
  (Ousterhout's "shallow module" smell).
- **Abstract base with exactly one production implementation?** (test
  doubles don't count if mock-by-spec works) → Collapse Hierarchy /
  Replace Superclass with Delegate.
- **Manager → service → repository → DAO chain** where each layer
  just forwards? → flatten by Removing Middle Men.
- **String-keyed dispatcher routing to one concrete type?** → Remove
  Middle Man.

### 5.2 Allowed micro-refactors (one per commit, tests green between)

The "When" column describes the diagnostic — a recognizable pattern — not a counting trigger. Numeric heuristics (rule of three, fan-in/out, line counts) are useful signals to triangulate but should not be treated as preconditions.

| Operation | When |
|---|---|
| Inline Function | A wrapper obscures the real work, adds no meaningful vocabulary, and is not serving as a seam, extension point, or recursion boundary. |
| Inline Class | A class exists as ceremony around data or pass-through behavior, and collapsing it would make the collaborating code easier to read. |
| Combine Functions into Class | Several functions orbit the same domain concept or evolving state, and callers already understand them as one responsibility. |
| Move Function | A function's vocabulary, data, and change reasons belong more naturally with another module's responsibility. |
| Move Class | A class changes with another module's concept, depends on its vocabulary, or makes the current package boundary harder to explain. |
| Replace Subclass with Delegate | Inheritance is being used for convenience or code reuse rather than genuine substitutability. |
| Remove Middle Man | An object mostly relays calls and makes tracing behavior harder without adding policy, isolation, or domain meaning. |

### 5.3 When NOT to flatten

Before any inline / collapse, verify the indirection is **not**:

- **A test seam** — grep the test suite for `mock_<name>`,
  `patch(... <path> ...)`. If tests patch it, it's a seam.
- **A plugin / extension point** — wrapper is the stable public
  surface.
- **A layer boundary with different change cadences** — pass-through
  enforces a one-way dependency direction a static checker is
  asserting.
- **An in-progress Branch by Abstraction** — the wrapper is the
  deliberate abstraction.
- **An audit / compliance hook** — wrapper exists to add logging
  around all calls.

If unsure: leave it, mark as `needs verification`, ask the user.

### 5.4 Splitting an over-long or mixed-responsibility file

Operationalizes the `split candidate` action from SKILL.md Phase 2. The goal is one cohesive responsibility per file; the work is identifying which functions belong together and migrating callers without breaking behavior.

**Recognize the clusters within the file.** Three signals to triangulate — none alone is sufficient, none alone is required:

- **Co-call graph.** Functions that call each other or share helpers tend to belong together; functions that stand alone often belong elsewhere.
- **Shared vocabulary.** Functions that operate on the same domain object, or take similar parameter shapes / return shapes, are usually one cluster.
- **Co-change history.** `git log --name-only --follow -- <file>` plus blame on adjacent line ranges reveals which functions get edited in the same commits — a strong signal they share a reason to change.

If a candidate cluster can't be given a clear, brief name (per [§2 Principle 1](PATCHES.md)), it's probably not a cluster — re-evaluate before extracting.

**Migrate one cluster at a time, not in a single big-bang split.** For each cluster:

1. Extract to a new module whose name reflects its responsibility (match the project's naming convention — noun-led, verb-led, or domain-led — rather than imposing a generic `_<cluster>` suffix).
2. Leave a re-export facade at the original path so out-of-tree callers keep working. The facade is temporary, not permanent.
3. Characterize the moved behavior with tests before migrating callers — see [§6 step 6](PATCHES.md) for the Feathers pattern.
4. Migrate internal callers using the LSP rename / move-symbol command per [§3 A3](PATCHES.md), one logical caller-group per PR.
5. Verify between PRs (project-native tests / lint / typecheck must stay green per [§11](PATCHES.md)).
6. Retire the facade only when the Phase 6 Stage 6 criteria pass.

**Anti-patterns to recognize.** Splitting horizontally by layer (one file for interfaces, one for impls, one for utils) usually just moves the cognitive load elsewhere when the real cohesion is vertical-by-feature. Creating modules so granular that each needs its own `__init__.py` re-exports to be usable inflates ceremony without simplifying anything.

**Illustration — one project's split, not a template.** A 1,200-line `utils.py` in a Python service held time helpers (`format_iso8601`, `parse_relative`, ...), string helpers (`slugify`, `normalize_whitespace`, ...), and filesystem helpers (`atomic_write`, `tmp_path_for`, ...). Co-change history showed time and string helpers rarely changed together; filesystem helpers changed with deployment-config code. After:

```text
project/
  time_utils.py        # 320 lines — owns datetime parsing/formatting
  string_utils.py      # 280 lines — owns text normalization
  path_utils.py        # 240 lines — owns FS path manipulation
  utils.py             # re-export facade (temporary)
```

This project happened to land on three files because cohesion clustered that way; another project might land on two, five, or a different shape entirely. *What matters is the process, not this specific decomposition.* The cluster naming follows the project's existing convention (this codebase uses `<domain>_utils.py`); a different project might prefer `time.py`, `text.py`, `paths.py` (Django-style nouns) or `format_time.py`, `slug.py` (verb-led). **This approach wouldn't apply** when a file is intentionally a thin facade (a correctly-re-exporting `__init__.py`), a generated artifact, or when its apparent length is illusion (one big config object with high internal cohesion). Source: SkillsBench (arXiv 2602.12670) — one worked example outperforms exhaustive abstract documentation when paired with explicit per-step reasoning.

### 5.5 Consolidating duplicate / drifted implementations

Operationalizes the `merge candidate` action and the `Duplicate logic` glossary entry ([§13](PATCHES.md)). The goal is one canonical implementation per logical operation; the work is detecting drift, choosing canonical behavior, and migrating callers safely.

**Detect duplicates by cohesion of intent, not by exact text match.** Useful signals, cheapest first:

- Shared signature / similar parameter shapes across modules (grep, `ripgrep --multiline`).
- Functions that read the same domain inputs and produce the same logical output, regardless of internal style.
- AST-level similarity via tree-sitter or language-specific normalizers when grep is inconclusive.

**Compare drift before assuming identity.** Drifted variants usually diverge in error handling, edge cases, or return-shape. List the differences explicitly. Sometimes drift is intentional (different error policies for different domains) — those variants should stay as `keep` with a comment explaining why the duplication is real.

**Choose canonical when consolidation is warranted.** A useful priority order — not an absolute ranking, local context can override:

- The variant with the highest test coverage (its behavior is verified).
- The variant closest to the public API surface (its callers are most exposed).
- The variant with the cleanest error handling (matches Fowler's preference for explicit failure modes).

Don't pick the newest variant just because it's newest — recency bias is its own failure mode.

**Migrate without losing behavior.** Write characterization tests for every drifted variant first ([§6 step 6](PATCHES.md)) so the merged function has to satisfy every behavior any caller relied on. Promote the canonical variant; for each non-canonical variant, add an adapter shim that translates its old signature to the canonical one (preserves callers). Migrate callers off shims in subsequent PRs, one logical caller-group per PR. Remove shims once no callers reference them (Phase 6 Stage 6 criteria). Source: Fowler's *Consolidate Duplicate Code* + Feathers' characterization-tests-before-modify pattern (PATCHES [§12](PATCHES.md)).

---

## 6. Safe-Deletion Playbook (replaces SKILL.md "Delete Candidate" rule)

**All eight steps required before any hard delete.**

1. **Establish suspect set** via static tooling (vulture / Knip /
   ts-unused-exports; for Python, `scripts/dead_candidates.py` also flags
   TEST_ONLY orphans + ZERO_REF and tags likely false positives — see §15).
   Treat as *suspects*, never as a delete list.
2. **Filter through dynamic-use patterns** — string-name references
   (`"FunctionName"`), `importlib` / `__import__` / dynamic `import()`,
   framework decorators (`@app.route`, `@pytest.fixture`, Django URLs,
   serializer `Meta`), reflection (`getattr`, `hasattr`), config files
   naming modules, test discovery globs, `[project.entry-points]` in
   `pyproject.toml` / `setup.cfg`.
3. **Cross-repo / external usage check** — for library code:
   `gh search code 'symbol'`, Sourcegraph global search, or grep
   across sibling repos. Skip only if provably process-internal.
4. **Git last-touched** — `git log -1 --format=%ad -- <path>` and
   `git log -S 'symbol'`. >12 months untouched AND no recent
   references = stronger candidate. Unchanged ≠ unused, but
   unchanged-for-years + unreferenced is meaningful.
5. **Tombstone before deletion** — replace the body with a logging
   call, OR move the file to `_archive/<path>` still on the import
   path, with a deprecation-log on first use. Ship and wait one
   release / N weeks. **Dead-until-proven-live, not the other way
   around.**
6. **Characterize** (Feathers) — write a characterization test
   capturing current behavior even if you intend to delete. If a
   consumer surfaces during the soak period, you know what they
   relied on.
7. **Delete in an isolated commit** — one logical deletion per commit.
   Message: `chore(cleanup): remove <thing> — unreferenced since
   <date>, archived <date>`.
8. **Tag the revert hatch** — `git tag pre-cleanup-<YYYY-QN>` on the
   commit before the deletions. Restoring must be one `git revert`,
   not archaeology.

**Hard rule:** if any of steps (2)(3)(4)(5) is skipped, the agent must
not delete — surface the gap and ask the user.

---

## 7. Needs-Verification Resolution Loop

To prevent the `needs verification` bucket from growing forever,
periodically (or on user prompt) run this loop.

For each item in the bucket, gather:

| Field | How |
|---|---|
| Cross-repo usage | `gh search code`, Sourcegraph |
| Internal usage | LSP "Find References" + grep for string-name |
| Last touch (git) | `git log -1 --format='%ad %s' -- <path>` |
| Last referenced | `git log -S '<symbol>' --oneline` |
| Dynamic-load risk | grep for decorators, plugin registries, entry points |
| Test mention | grep test suite for the name |

Then present the user **one batched yes/no list**:

> "Here are 12 items currently in `needs verification`. Based on the
> evidence I gathered, items 1–7 look safely removable (tombstone first
> recommended), items 8–10 look like keepers, items 11–12 I still can't
> determine — can you confirm?"

Do not delete from this loop; promote items to `delete candidate` or
`keep` based on user response, then run the Safe-Deletion Playbook on
the approved set.

---

## 8. Small-Project Fast Path (alternative to SKILL.md 6 phases)

If the project has **fewer than ~30 source files** OR a single clear
entry point with shallow imports, skip the 6-phase ceremony. Run:

1. **Inventory** — list source files + entry points (one bullet each).
2. **Smallest safe move** — identify the single highest-value change
   (one move, one inline, one rename, or one deletion candidate).
3. **Execute that one change** with verification (project-native
   tests / lint / typecheck).
4. **Repeat** until the user says stop.

The full 6-phase workflow is for medium / large codebases. Forcing
it on small projects produces more documentation than code.

---

## 9. Macro vs Micro Refactor (extends SKILL.md "Implementation Rules")

- **Micro-refactor** — one catalog entry (Inline, Rename, Move,
  Extract). Agent may complete end-to-end in one PR if all rules
  above pass.
- **Macro-refactor** — directory regroup, public API change,
  splitting a god-module, replacing a subsystem. Agent **must**
  produce a **Mikado graph** (a checklist file with goal →
  prerequisites → sub-prerequisites) and proceed **one leaf per PR**.
  No "big-bang" reorganization commits.

arXiv 2511.04824 (Nov 2025) found AI agents have median 0.00
smell-count change on real refactor PRs precisely because they
attempt macro work the way they attempt micro work. The micro/macro
split is the mitigation.

---

## 10. Google + Reputable OSS Structural Exemplars (for SKILL.md Phase 5 target proposals)

When proposing a target layout, cite which exemplar you mirror.

**Authoritative Google references:**

- *Software Engineering at Google* (Winters / Manshreck / Wright) —
  <https://abseil.io/resources/swe-book>
- Google Engineering Practices —
  <https://google.github.io/eng-practices/>
- Google Style Guides — <https://google.github.io/styleguide/>

**OSS structural exemplars:**

| Project | Pattern to copy |
|---|---|
| Kubernetes (Go) | `cmd/<binary>/` for entry points, `pkg/` for importable library code, `internal/` for non-exported. One binary per `cmd` dir. |
| Django (Py) | `apps/<app_name>/{models,views,urls,services}.py` — flat per-app, predictable, no nested helper trees. |
| FastAPI (Py) | Single canonical public import surface; `from fastapi import FastAPI` is the one import. Runnable examples in `docs/`. |
| React (TS) | Monorepo `packages/<scope>/` with explicit public exports via each package's `index.ts`. |
| Rust std + Cargo | `crate/src/{lib,main}.rs` + `tests/` for integration; trait-over-inheritance. Workspaces for multi-crate projects. |
| Bazel | One build target per directory; `BUILD` files name dependencies explicitly. No transitive guesswork. |

Rule: do not invent novel layouts when an exemplar applies. Match
the closest exemplar to the project's archetype.

---

## 11. Errata to SKILL.md

- **Templates** — `templates/architecture_report.md`,
  `templates/refactor_plan.md`, and `templates/migration_stage_report.md`
  are **canonical**. The inline "Output Format" sections in SKILL.md
  are quick-read previews only. When emitting a report, copy from the
  template file.
- **Helper scripts** — `scripts/hotspots.py` (§4) and `scripts/dead_candidates.py` (§6, §15) are implemented;
  the rest in `scripts/README.md` are a roadmap with manual fallbacks. See that README (single source of truth).
- **Verification commands** — the per-language analyzers (`vulture`, `pydeps`, `import-linter`, `madge`, `knip`, etc.) are **optional**. Tier order:
  1. **Project-native** — whatever the project's `pyproject.toml` / `package.json` / `Makefile` / `Cargo.toml` / `build.gradle` defines under `test`, `lint`, `typecheck`. These reflect the team's own contract.
  2. **Language built-ins** — `python -m compileall`, `tsc --noEmit`, `go vet`, `cargo check`. Fast smoke checks that catch most regressions without setup.
  3. **Optional external analyzers** — vulture / pydeps / knip / madge etc. (full catalog: §14). Suggest installing only after the cheaper tiers have run; never require them.

### Per-ecosystem commands (reference catalog)

Use these as starting points. Always prefer project-native commands (tier 1) if they exist.

**Python:**

```bash
python -m pytest
ruff check .
mypy .
python -m compileall .
```

**JavaScript / TypeScript:**

```bash
npm test
npm run lint
npm run typecheck
npm run build
```

**Go:**

```bash
go test ./...
go vet ./...
```

**Rust:**

```bash
cargo test
cargo clippy
cargo build
```

**Java / Kotlin (Gradle):**

```bash
./gradlew test
./gradlew build
```

**Java / Kotlin (Maven):**

```bash
mvn test
mvn verify
```

For ecosystems not listed (Haskell, Elixir, Clojure, C / C++, Swift, Kotlin / Multiplatform, Zig, Nim, Crystal, Erlang, OCaml, F#, Scala, Ruby, PHP, etc.): consult the project manifest first, then the language's idiomatic test/lint/typecheck commands. Ask the user if the project has unfamiliar conventions.

---

## 12. References

- Fowler, *Refactoring* (2nd ed., 2018) — <https://refactoring.com/catalog/>
- Fowler, *Strangler Fig Application* — <https://martinfowler.com/bliki/StranglerFigApplication.html>
- Humble, *Branch by Abstraction* — <https://martinfowler.com/bliki/BranchByAbstraction.html>
- Feathers, *Working Effectively with Legacy Code* — seams, characterization tests, sprout/wrap.
- Ellnestam & Brolund, *The Mikado Method* — <https://mikadomethod.wordpress.com/>
- Ousterhout, *A Philosophy of Software Design* — deep modules, shallow-wrapper smell.
- Tornhill, *Software Design X-Rays* / CodeScene hotspot methodology — <https://codescene.com/blog/tech-debt-examples-prioritize-technical-debt-with-codescene>
- Lemaire, *Refactoring at Scale* — Slack's dark/light cutover.
- *Software Engineering at Google* — <https://abseil.io/resources/swe-book>
- Google Engineering Practices — <https://google.github.io/eng-practices/>
- Google Style Guides — <https://google.github.io/styleguide/>
- Palomba et al., "On the diffuseness and the impact on maintainability of code smells" (EMSE 2017) — <https://link.springer.com/article/10.1007/s10664-017-9535-z>
- Romano et al., "A Multi-Study Investigation into Dead Code" (IEEE TSE 2018) — <https://www.cs.wm.edu/~denys/pubs/TSE'18-DeadCode.pdf>
- "Agentic Refactoring: An Empirical Study" (arXiv 2511.04824, Nov 2025) — <https://arxiv.org/abs/2511.04824>
- "Empirical Study on the Potential of LLMs in Automated Software Refactoring" + RefactoringMirror (arXiv 2411.04444, Nov 2024) — <https://arxiv.org/abs/2411.04444>
- scheb/tombstone — runtime-evidence pattern for dead-code detection — <https://github.com/scheb/tombstone>

---

## 13. Glossary of Professional Problem Categories

When describing what makes a project hard to maintain, use precise engineering vocabulary. Each term is a recognized diagnosis with a remediation path in the literature, not just a generic complaint.

| Term | Meaning | Typical remediation |
|---|---|---|
| **Architectural erosion** | The implemented architecture has drifted from the intended one — boundaries that once existed now leak. | Re-establish boundaries via import-linter / dependency-cruiser rules (§3 A-rules), then enforce in CI. |
| **Technical debt** | Shortcuts taken under time pressure that compound future change costs. | Hotspot-prioritized cleanup (§4), one debt item per refactor commit (§3 A2). |
| **Unclear module boundaries** | Module names no longer describe what lives inside; responsibilities overlap across modules. | Match an OSS exemplar layout (§10), then move files in low-risk batches with compatibility wrappers. |
| **Poor code navigability** | A maintainer cannot quickly find where a feature is implemented. | Phase 1 Map + Call Graph; flatten unjustified indirection (§5). |
| **High cognitive load** | Reading one feature requires holding many unrelated concepts in mind. | Inline shallow wrappers (§5.2), split mixed-responsibility files. |
| **Poor change locality** | A small feature change requires editing many unrelated files. | Identify the missing abstraction or misplaced responsibility (§2 Principle 1); consolidate. |
| **Spaghetti dependencies** | Modules import each other transitively across unrelated domains. | Break cycles via Branch by Abstraction; add boundary rules. |
| **Excessive indirection** | Many layers between the call site and the work being done. | Apply the §5 Reduce-Nesting Catalog; inline pass-through wrappers. |
| **Deep nesting** | Either control-flow nesting inside one function, or call-graph nesting across files. Both raise cognitive complexity (Sonar). | Extract early returns for in-function; inline wrappers for cross-file. |
| **Hidden side effects** | Calls that mutate state or perform I/O without that being obvious from the name or signature. | Rename to surface the effect; isolate to a clearly-named module; document at the call site. |
| **Dead code candidates** | Code that appears unused. *Candidate*, not confirmed — see §6 Safe-Deletion Playbook before deletion. | Tombstone, soak, verify zero hits, delete. Never delete on first suspicion. |
| **Orphaned files** | Files not imported by anything traceable through static analysis. May still be loaded dynamically. | Same playbook as dead-code (§6). |
| **Duplicate logic** | The same operation implemented in multiple places, often with subtle drift. | Extract once a third caller appears (rule of three); see Fowler. |
| **Circular dependencies** | A imports B, B imports A. Often a sign of a missing shared abstraction. | Pull the shared concept up into a third module; or invert the dependency direction with an interface. |
| **Weak ownership boundaries** | Multiple teams or features write into the same module; nobody "owns" it. | Split by feature, or designate a single owner and route changes through them. |
| **Framework-convention ambiguity** | Files that are auto-loaded by a framework (Django apps, pytest plugins, FastAPI routers) but don't follow the framework's documented conventions, leaving the loading rules unclear. | Adopt the framework's idiomatic structure (§10); cite which exemplar. |
| **Onboarding-hostile structure** | A new maintainer cannot find the entry point, trace one feature, or identify the test harness within their first session. | Phase 1 Map + Call Graph as a documentation artifact; flatten obvious wrappers. |
| **Shotgun surgery risk** | A feature change requires edits across many files; a maintainer cannot predict the blast radius. | Identify the missing abstraction; consolidate; cover with characterization tests before the consolidation move (Feathers). |

---

## 14. Recommended Tools

Pick analyzers and visualization tools that fit the project's language; do not install everything by default. For any ecosystem, the IDE's language server "Find References" plus `git grep` / `ripgrep` cover most analysis needs without setup cost.

**Python:**

- `ruff` — linting and unused imports.
- `pydeps` — import dependency graph.
- `import-linter` — architecture boundary enforcement (declarative contracts in `pyproject.toml`).
- `vulture` — dead-code candidates (use with `--min-confidence 80` + allowlist to suppress framework-decorator false positives).
- `pyan3` — rough static call graph.
- `CodeQL` — deeper static analysis for security-relevant patterns.

**JavaScript / TypeScript:**

- `eslint` — linting.
- `tsc --noEmit` — type checking without emit.
- `madge` — dependency graph and circular-import detection.
- `dependency-cruiser` — rule-driven architecture dependency validation; emits dot/SVG.
- `knip` — unused files, unused exports, unused dependencies. Preferred over `ts-prune` (now in maintenance).
- `depcheck` — package.json dependency cleanup.

**Go:**

- `go vet` — built-in static checks.
- `staticcheck` — comprehensive static analysis.
- `golangci-lint` — meta-linter that runs many tools together.

**Rust:**

- `cargo clippy` — lints idiomatic Rust.
- `cargo udeps` — unused dependencies (nightly).
- `cargo machete` — alternative unused-dependency detector (stable).

**JVM (Java / Kotlin / Scala):**

- `ArchUnit` — architecture rules as unit tests.
- `Detekt` (Kotlin), `PMD` / `SpotBugs` (Java) — static analysis.
- `jdeps` / `jdeprscan` — dependency and deprecation scanning.

**General / language-agnostic:**

- `tree` — project tree visualization.
- `ripgrep` (`rg`) — fast usage and pattern search.
- `git grep` — tracked-only search; ignores `.gitignore`d files.
- `cloc` — line-count overview per language.
- `CodeQL` — multi-language semantic analysis.
- `Sourcegraph` — cross-repo code navigation, especially for library code with external consumers.
- IDE language-server "Find References" — most reliable single-repo cross-reference, no installation beyond the IDE.

---

## 15. Dead-weight sweep — reachability + data-flow (extends §6)

[§6](PATCHES.md) seeds dead-code suspects from name/AST tools (`vulture` / `knip`), which catch **name-orphans**
(the name is never referenced) but miss code that is *referenced yet dead*. Run this sweep for an **exhaustive
dead-weight audit** (not a navigability pass): scan **every** top-level symbol in the whole production tree —
that exhaustiveness, not a sample, is what guarantees no corner is omitted — and **waive the [§4](PATCHES.md)
hotspot precondition** (dead weight collects in cold code, not hotspots).

**A — Production reachability (test-only orphans).** A symbol referenced *only by its own tests* passes both
name-resolution ("live") and coverage ("covered"). For each suspect, split references into production (app/`src`
+ the entry→dispatch graph) vs test-only (Python: `scripts/dead_candidates.py`
emits this partition — pass your source/test dirs, or let it auto-detect). A test-only symbol that is **not** a public surface (`__all__`, a
documented back-compat alias, or a `mock.patch` target — [§5.3](PATCHES.md)) is an orphan; remove it **with its
now-dead tests**.

**B — Data-flow dead branches (unwired code).** A branch is unreachable even when its function runs if it turns on
a value that is never produced: a config flag defaulting off and never set on; a key/field **read** from a
produced artifact that nothing **writes**; a struct field the sole constructor never sets and no consumer reads.
Name-reachability says "live"; only "is this value ever produced?" disproves it.

**Verify, then delete.** Treat each A/B hit as a *candidate* and disprove "live" with code evidence — rule out
dynamic / decorator / registry dispatch, config-enabled paths, public / external surfaces, and non-default-mode
fallbacks ([§5.3](PATCHES.md), [§6 step 2](PATCHES.md)). A test-only symbol on a public surface is a **user
decision**, not an auto-delete ([§7](PATCHES.md)). Then run the full [§6](PATCHES.md) playbook; delete large
blocks by exact line-range. Apply the same lens to the test suite — drop tests of removed symbols and
*verified*-redundant duplicates, but never blanket-cut (the suite is the behavior-preservation net; keep
before == after green on the survivors).
