# Execution — Target Proposal, Staged Plan, Patterns

Target proposal, staged plan, and the canonical refactor patterns. Loaded with `techniques.md` (the how-to
for each move), `safety.md` (the risk tiers and hard rules that govern every change), and `architecture.md`
(exemplars for the target tree) at the execution stage. Self-contained for the planning and patterns.

---

## Target architecture proposal

Propose a target structure; do **not** implement it yet.

**Local conventions first, exemplars as fallback.** The right layout is the one that matches *this*
project's domain and its framework's official documented conventions. Honor the project's own established
patterns where they exist. Only when the project has no clear convention, mirror a reputable OSS exemplar
(`architecture.md`) — and cite which one and why. Do not impose a novel layout, and do not override a
sensible local convention with an external exemplar.

The proposal must include: target directory tree; old→new path mapping; rationale per package; the
directness-first migration strategy (atomic caller updates; a bounded fallback only where consumers are
non-enumerable — `techniques.md` §4); test strategy; rollback strategy; risk tier per move (`safety.md`);
approval requirement per stage. Pick the **smallest move-set that resolves the diagnostic** (Occam) — a
300-move "complete refactor" is rarely right; a 5-move "biggest pain point" usually is.

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

Create the plan before editing. Recommend **plan-first** for any macro work — get agreement on the stages
before changing code, so the agent doesn't see "refactor" and start moving many files at once. (Campaign
mode generalizes this into a continuous ledger-driven loop — `campaign-mode.md`.)

| Stage | Allowed | Not allowed |
|---|---|---|
| **0 Documentation** | architecture notes, project map, entry-point + call-path docs, onboarding notes | moving / deleting files; behavior change |
| **1 Static-analysis tooling** | add/configure lint, dep-graph, dead-code, boundary tools; analysis scripts | source behavior change |
| **2 Architecture boundary rules** | import-boundary / dependency rules; CI checks | moving many files; deleting |
| **3 Low-risk moves** | move isolated scripts / evaluation / diagnostics files; update callers atomically (directness-first) | moving core runtime first; renaming public APIs; logic change |
| **4 Medium-risk reorg** | split mixed-responsibility files (§6); merge duplicates (§7); simplify nesting (§5); rename internal-only | — |
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
(`techniques.md` §4).

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

Directness-first and the bounded-fallback exception are canonical in `techniques.md` §4. One execution-specific
caveat: when updating callers, prefer the LSP rename / move-symbol command over `grep + replace` — grep misses
string-name references (decorators, plugin registries, test-discovery globs), the exact high-risk surfaces.
