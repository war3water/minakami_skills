# Execution — Target Proposal, Staged Plan, Patterns

Target proposal, staged plan, and the canonical refactor patterns. Loaded with `techniques.md` (the how-to
for each move) and `safety.md` (the risk tiers and hard rules that govern every change) at the execution
stage. Self-contained for the planning and patterns.

---

## Target architecture proposal

Propose a target structure; do **not** implement it yet.

**Local conventions first, exemplars as fallback.** The right layout is the one that matches *this*
project's domain and its framework's official documented conventions. Honor the project's own established
patterns where they exist. Only when the project has no clear convention, mirror a reputable OSS exemplar
(table below) — and cite which one and why. Do not impose a novel layout, and do not override a
sensible local convention with an external exemplar. **Existing chaos is not a convention** — random placement
with no ownership rule *is* the no-convention case. And when the user explicitly asks to reconstruct toward a
clearer, more intuitive structure, that ask sets the diagnostic: the smallest move-set that resolves it is the
full regroup (staged, approved, executed directness-first) — do not shrink a requested reconstruction out of
churn-aversion.

Exemplars (fallback only; cite which you mirror and why): Kubernetes `cmd/<binary>/` + `pkg/` + `internal/`
(Go services); Django flat per-app `apps/<app>/{models,views,urls,services}.py`; FastAPI single canonical
import surface (libraries); React monorepo `packages/<scope>/` with explicit `index.ts` exports; Rust
`crate/src/{lib,main}.rs` + workspaces; Bazel one-build-target-per-directory.

The proposal must include: target directory tree; old→new path mapping; rationale per package; the
directness-first migration strategy (atomic caller updates; a bounded fallback only where consumers are
non-enumerable — `techniques.md` §3); test strategy; rollback strategy; risk tier per move (`safety.md`);
approval requirement per stage. Pick the **smallest move-set that resolves the diagnostic** (Occam) — a
300-move "complete refactor" is rarely right; a 5-move "biggest pain point" usually is.

**Deriving the target tree (when reconstruction is in scope).** There is no universal right layout — the
exemplar provides the *idiom*, the project's own evidence provides the *content*:

1. **Layers from node tags** — the discovery call graph's entry / wiring / domain / I/O tags define the
   top-level split: entrypoints + wiring at the edges, pure domain core, I/O adapters at the boundary
   (composition root).
2. **Modules from cohesion clusters** — co-call, shared-vocabulary, and co-change clusters (`techniques.md`
   §5) name the directories; each directory gets one specific, nameable responsibility (no
   `manager`/`utils`/`common`).
3. **Idiom from the archetype** — pick the exemplar (table above) matching the project's archetype (Go
   service → `cmd/pkg/internal`; Python web app → per-app; library → single import surface; monorepo →
   packages) and adopt its naming and nesting conventions; cite it.
4. **Validate every directory against the gates** — each level must earn its existence (a directory holding
   one file, or existing only to forward, fails); names specific; import direction declared one-way
   (Pattern 3) and enforced in Stage 2.
5. **Right-size the depth** — the fewest directory levels the real module count requires; never pre-create
   empty layers for a future that may not come.

Illustrative shape for a mid-size service (treat as example, not prescription — adapt to the project):

```text
project/
  app/         entrypoints (cli, api, ui), bootstrap, runtime    # wiring lives here
  core/        domain logic, services, events                    # pure core, no wiring
  config/      explicit config loading and validation
  integrations/ external services, db, filesystem, LLM adapters
  diagnostics/ healthcheck, failure analysis
```

The `app/` vs `core/` split is the composition-root pattern: keep wiring at the edges, the domain pure
(diagnosis category 4, entry-vs-implementation).

---

## Staged plan

Create the plan before editing. Recommend **plan-first** for any macro work (SKILL.md intake; `safety.md`
§4). (Campaign mode generalizes this into a continuous ledger-driven loop — `campaign-mode.md`.)

| Stage | Allowed | Not allowed |
|---|---|---|
| **0 Documentation** | architecture notes, project map, entry-point + call-path docs, onboarding notes | moving / deleting files; behavior change |
| **1 Static-analysis tooling** | add/configure lint, dep-graph, dead-code, boundary tools; analysis scripts | source behavior change |
| **2 Architecture boundary rules** | import-boundary / dependency rules; CI checks | moving many files; deleting |
| **3 Low-risk moves** | move isolated scripts / evaluation / diagnostics files; update callers atomically (directness-first) | moving core runtime first; renaming public APIs; logic change |
| **4 Medium-risk reorg** | split mixed-responsibility files and merge duplicates (`techniques.md` §5); simplify nesting; rename internal-only | — |
| **5 Core refactor** (explicit approval, tests stable) | core restructuring, service extraction, dependency inversion, public-API cleanup | — |
| **6 Retire fallbacks** | remove any compatibility layer once unreferenced | leaving a permanent wrapper (`safety.md` §3) |

Stage gating mirrors the risk tiers in `safety.md` (Stages 0–3 ≈ low, Stage 4 ≈ medium → proceed with
verification within this agreed plan, Stage 5 ≈ high → explicit approval). Stage 6 exists because **no refactor
is complete while a temporary fallback still stands** — landing directly via directness-first means most
efforts skip it entirely.

---

## Common refactor patterns

**1. Root-level module grouping** — flat `a.py b.py c.py …` at the package root → group by responsibility
(`core/ runtime/ evaluation/ config/`). Use only after import and entry-point analysis.

**2. Direct move (preferred) / compatibility move (fallback)** — move `project/benchmark.py` →
`project/evaluation/benchmark.py` and update all callers atomically via LSP (directness-first). A temporary
re-export facade is used only if external consumers are non-enumerable, and is removed in Stage 6
(`techniques.md` §3).

**3. Boundary enforcement** — declare and enforce direction, e.g. `core must not import evaluation / CLI /
runtime integrations`; `evaluation may import core`; `CLI may import everything for composition`.

**4. Replace hidden flow with explicit flow** — `main → global registry → dynamic side effect → implicit
execution` becomes `main → build_config() → build_registry() → build_runtime() → run()`. Explicit
composition over hidden dispatch.

**5. Reduce shotgun surgery** — if one feature requires edits across many unrelated files, find the missing
abstraction / misplaced responsibility / duplicated logic / unclear ownership, then propose one targeted
structure change (cover with characterization tests first).

---

## Compatibility layers

Directness-first and the bounded-fallback exception are canonical in `techniques.md` §3. One execution-specific
caveat: when updating callers, prefer the LSP rename / move-symbol command over `grep + replace` — grep misses
string-name references (decorators, plugin registries, test-discovery globs), the exact high-risk surfaces.
