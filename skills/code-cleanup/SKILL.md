---
name: code-cleanup
description: Refactor a messy, hard-to-maintain project so a maintainer can read, debug, and modify it quickly. Use when a codebase has unclear module boundaries, deep call nesting, dead-code candidates, duplicated logic, circular imports, misplaced files, spaghetti dependencies, excessive indirection, technical debt, or onboarding-hostile structure. Triggers on phrases like "my code is messy", "pay down tech debt", "clean up", "reorganize", "modularize", "untangle the repo", "organize folders", "reduce nesting", "remove dead/orphaned files", "improve maintainability", or "make debugging easier". Primary outputs — a project structure map, a maintainer-oriented call graph, a ranked refactor plan, and the execution itself. Both staged behavior-preserving changes and scoped rewrites are legitimate paths; the choice follows from what Phase 1's map and call graph reveal, with the user's agreement on scope. Methodology lives in SKILL.md (navigation map) plus phases/*.md (per-stage detail) and PATCHES.md (evidence-based supplements — same folder as SKILL.md). Where PATCHES.md conflicts with SKILL.md or any phase file, PATCHES.md wins.
---

> **Preamble**
>
> **Goal:** make this project easy for a maintainer to read, debug, and modify. Concrete outputs are a project structure map, a maintainer-oriented call graph, a ranked refactor plan, and the execution itself.
>
> **This SKILL.md is a navigation map.** Per-stage detail lives in the [phases/](phases/) subdirectory and loads only when the agent enters that stage. [PATCHES.md](PATCHES.md) in the same folder carries the evidence-based safety rules (revert-on-red with agent-owned-files-only rollback, commit hygiene, RefactoringMirror, 8-step Safe-Deletion Playbook), the reduce-nesting catalog, the hotspot precondition, OSS structural exemplars (Kubernetes, Django, FastAPI, React, Rust, Bazel), and references to Fowler / Feathers / Ousterhout / Tornhill / arXiv refactor studies. **Where PATCHES.md and any other file disagree, PATCHES.md wins.**
>
> **Trust the invoking context.** The user's message usually already states the project, the pain, and the appetite. If it does, accept those and proceed. Ask only for what you genuinely cannot infer; don't run a mechanical question round when intent is clear.
>
> **The choice between staged behavior-preserving changes and a scoped rewrite follows from what Phase 1 reveals, not from policy.** Both are legitimate paths. Behavior preservation is the right call when the structure can support it; a scoped rewrite is the right call when the structure cannot. The user agrees the scope before either path begins.

---

# Behavior-Preserving Project Refactor Skill

## Purpose

Use this skill when a project is hard for a maintainer to read, debug, or modify — unclear module boundaries, deep call nesting, mixed responsibilities, dead-code candidates, duplicated logic, misplaced files, framework-convention ambiguity, or onboarding-hostile structure.

**Goal:** make navigation and change easy — clear module boundaries, short call paths, predictable layout, no orphaned files.

**Task — adapt to the situation, don't force any single playbook:**

1. **Map** the project for a maintainer (Phase 1 produces a *project structure map* and a *maintainer-oriented call graph* — the two artifacts a new maintainer reads first).
2. **Diagnose** what makes the project hard to navigate or change (Phases 2-4).
3. **Plan** the smallest set of moves that resolves the diagnostic (Phase 5-6).
4. **Execute** — staged behavior-preserving changes or a scoped rewrite, whichever the Phase 1 evidence supports. Both are legitimate paths; the user agrees the scope before either path begins.
5. **Verify** after each step (tests / lint / typecheck, per PATCHES.md §11 tier order).

**Choose staged refactor or scoped rewrite based on what the map and call graph reveal — not on policy or counts.**

If Phase 1 shows the project is mostly navigable — recoverable boundaries, mostly-justified indirection, behavior worth preserving — staged refactor fits the evidence.

If Phase 1's findings reveal **unnecessary and redundant structure** — indirection that doesn't earn its keep, the same logical operation expressed differently in multiple modules, boundaries that no longer match the domain, features whose flow requires stepping through chains of trivial forwarding — **a deeper refactor or scoped rewrite is the right answer, and staged is a trap.**

These are diagnostic patterns to recognize through tracing the call graph and reading the map, not thresholds to count against. Look for:

- **Indirection without a real best-practice driver** — no testing seam, no plugin / extension point, no layer boundary, no genuine reuse (see [PATCHES.md §2 Principle 2](PATCHES.md) for the justification gate). Layers that exist only because someone abstracted "in case" almost always need consolidating.
- **Competing implementations** — the same concept expressed in different modules with different parameter shapes, error conventions, or return types. A sign the abstraction was never settled.
- **Mismatched boundaries / shotgun surgery** — feature changes that require edits across unrelated-seeming directories. Module names no longer describe what lives inside them (see [PATCHES.md §2 Principle 1](PATCHES.md)).
- **Team friction phrased structurally** — "I can't find where to change X", "I'm afraid to touch Y". A structure problem, not a style problem.

When the evidence supports it, propose the deeper rewrite explicitly: scope, rationale, fallback plan, and what is preserved (behavior contracts, public API surfaces, data layouts). The choice is contextual, not a categorical preference.

---

## Core Principles

1. **Primary outputs first.** Phase 1 produces two artifacts that guide every later decision:
   - **Project structure map** — what each directory and major file is for.
   - **Maintainer-oriented call graph** — for each user-facing feature and entry point, the path through the code.
2. **Diagnose before refactoring.** Read the map and call graph before moving, deleting, or rewriting anything.
3. **Staged behavior-preserving changes and scoped rewrites are both legitimate paths.** Choose based on what Phase 1 reveals — not policy. The user agrees the scope before either path begins (see Purpose).
4. **Use evidence**, not file names or guesses — imports, call paths, tests, configs, entry points, runtime conventions.
5. **Treat as high-risk:** dynamic imports, decorators, plugin registration, CLI entry points, framework conventions, reflection, generated code.
6. **If usage is uncertain,** mark "needs verification" and resolve via [PATCHES.md §7](PATCHES.md) (batched yes/no with the user) — not by guessing or deleting.
7. **Prefer boring, explicit, readable code** over clever abstractions.
8. **Verify after each change** — tests, lint, typecheck ([PATCHES.md §11](PATCHES.md) tier order).
9. **Any intentional behavior change requires explicit user approval** and lives in a clearly-scoped commit. This applies whether the work is staged refactor or scoped rewrite.

---

## Resources

This skill ships supplementary files. Read them on demand:

- [phases/discovery.md](phases/discovery.md), [phases/diagnosis.md](phases/diagnosis.md), [phases/execution.md](phases/execution.md) — full specifications for the three workflow stages (Phases 0-1, Phases 2-4, Phases 5-6 plus Implementation Rules / Patterns / Approval Gates). The Required Workflow section below is a table of contents; phase detail lives in these three files and loads only when the agent enters the relevant stage.
- [PATCHES.md](PATCHES.md) — evidence-based safety rules (revert-on-red with agent-owned-files-only rollback, commit hygiene, RefactoringMirror), the reduce-nesting technique catalog with "when NOT to flatten" caveats, the 8-step Safe-Deletion Playbook with tombstones, hotspot precondition, six reputable-OSS structural exemplars (Kubernetes / Django / FastAPI / React / Rust / Bazel), the glossary of professional problem categories, ecosystem-specific verification commands, the splitting and duplicate-merging playbooks, and references to Fowler / Feathers / Ousterhout / Tornhill / arXiv refactor studies. **Where PATCHES.md and this file (or any phase file) disagree, PATCHES.md wins.**
- [templates/architecture_report.md](templates/architecture_report.md), [templates/refactor_plan.md](templates/refactor_plan.md), [templates/migration_stage_report.md](templates/migration_stage_report.md) — canonical output skeletons for Phase 1, Phase 6, and post-stage reports. Copy from these; do not regenerate from memory.
- [scripts/README.md](scripts/README.md) — **roadmap only; no scripts are implemented.** The README contains manual-fallback procedures for each proposed script (entrypoint discovery, import collection, file classification, dead-code detection, report generation). Use the manual fallback unless and until the corresponding script lands.

---

## Professional Problem Categories

When describing maintainability problems, use precise engineering vocabulary so the diagnosis is shared and the remediation is searchable. The full glossary — architectural erosion, technical debt, unclear module boundaries, poor code navigability, high cognitive load, poor change locality, spaghetti dependencies, excessive indirection, deep nesting, hidden side effects, dead code candidates, orphaned files, duplicate logic, circular dependencies, weak ownership boundaries, framework-convention ambiguity, onboarding-hostile structure, shotgun surgery risk — is documented in [PATCHES.md §13 Glossary](PATCHES.md).

---

## Required Workflow

The workflow has three stages, each specified in its own file under [phases/](phases/). Read the phase file when entering that stage; the summaries below let you pick which stage applies. Cross-references go from each phase file directly to PATCHES.md (one-hop rule); phase files do not reference each other — workflow ordering lives only here.

### Discovery — Phase 0 (Safety Preparation) + Phase 1 (Project Map & Call Graph)

Identify the project's language, framework, build / test / lint commands, entry points, config, and framework conventions (Phase 0). Then produce the two artifacts a maintainer reads first: a **project structure map** (what each directory and major file is for — answering where the program starts, where features live, what each top-level directory means, and what is auto-loaded by framework conventions) and a **maintainer-oriented call graph** (shallow trace per user-facing feature, with the "do not multiply entities beyond necessity" justification gate applied to every jump). These artifacts are standalone deliverables and feed every later decision. Calibrate call-graph depth by studying real OSS exemplars (FastAPI / requests / Pydantic / tokio for shallow composition; Django / grpc-go / Kubernetes / Abseil for framework-required depth) — there is no universal "right depth."

**Read [phases/discovery.md](phases/discovery.md) for the full specification, including the PATCHES guards (§1 first-impression test, §4 hotspot precondition, §8 small-project fast path) and the OSS calibration references.**

### Diagnosis — Phase 2 (File Classification) + Phase 3 (Dependency Analysis) + Phase 4 (Maintainability Diagnosis)

Classify files into a table with Risk Level and Recommended Action (keep / rename / move / split / merge / simplify / delete / needs-verification / do-not-touch-without-tests), with marking discipline for dynamic-load and framework-convention risks. Build a dependency and call-path map: entry-point traces, fan-in / fan-out, circular dependencies, deep chains, overly-broad utilities, files that mix responsibilities. Diagnose maintainability issues across 15 categories (architecture erosion, excessive nesting, hidden side effects, duplicate logic, dead code, misleading names, etc.), with per-issue evidence and recommended action.

**Read [phases/diagnosis.md](phases/diagnosis.md) for the full specification, including the Phase 2 decision table and the PATCHES guards (§10 OSS exemplars for Recommended Location, §2 design principles for Recommended Action, §5 reduce-nesting catalog for deep chains, §6 safe-deletion playbook for delete candidates, §7 needs-verification loop for ambiguous items).**

### Execution — Phase 5 (Target Proposal) + Phase 6 (Staged Plan) + Implementation Rules + Common Refactor Patterns + Approval Gates

Propose a target architecture mirrored on a specific [PATCHES.md §10](PATCHES.md) OSS exemplar (no universal layout — cite which one you mirror and why). Then create a staged plan: Stage 0 documentation-only → Stage 1 static-analysis tooling → Stage 2 architecture boundary rules → Stage 3 low-risk file moves → Stage 4 medium-risk reorganization → Stage 5 core refactor → Stage 6 wrapper cleanup. Apply the 14 Implementation Rules during stage execution; consult the five Common Refactor Patterns (Root-Level Module Grouping, Compatibility Move, Boundary Enforcement, Replace Hidden Flow, Reduce Shotgun Surgery) for canonical moves; respect the 10 User Approval Gates for any change that touches public surface, deletion, schema, or plugin systems.

**Read [phases/execution.md](phases/execution.md) for the full specification, including the PATCHES guards (§3 hard safety rules with agent-owned-files-only rollback, §9 macro-vs-micro with Mikado discipline, §10 OSS exemplars for the target tree) and the full Stage 0-6 contract.**

---

## Compatibility Wrapper Pattern

This pattern is cross-cutting — both staged moves and scoped rewrites use it — so it lives in SKILL.md rather than in a phase file.

When moving a module from an old path to a new path, keep a temporary wrapper if external usage is uncertain.

Example:

```python
"""
Compatibility wrapper for old import path.

Old:
    import project.benchmark

New:
    import project.evaluation.benchmark

This wrapper should be removed only after external usage is verified.
"""

from project.evaluation.benchmark import *  # noqa: F401,F403
```

Rules:

1. Use wrappers only as temporary migration aids.
2. Mark them clearly.
3. Track them in the migration report.
4. Remove them only after approval.
5. When updating callers, prefer the IDE's LSP rename / move-symbol command over `grep + replace` — grep misses string-name references like decorators, plugin registries, and test-discovery globs, which are exactly the high-risk surfaces flagged in [PATCHES.md §3](PATCHES.md).

---

## Verification Rules

After each stage, run available checks in this tier order: project-native commands first (whatever `Makefile`, `pyproject.toml`, `package.json`, `Cargo.toml`, etc. defines under `test`, `lint`, `typecheck`), then language built-ins (`python -m compileall`, `tsc --noEmit`, `go vet`, `cargo check`), then optional external analyzers only if they're already installed (`vulture`, `pydeps`, `knip`, `madge`, etc.). The full per-ecosystem command list and the optional-analyzer catalog are in [PATCHES.md §11](PATCHES.md).

**For ecosystems not enumerated in the catalog (Haskell, Elixir, Clojure, C / C++, Swift, Kotlin / Multiplatform, Zig, Nim, Crystal, Erlang, etc.):** consult the project's own build manifest and run that ecosystem's native test / lint / typecheck commands. If the ecosystem is unfamiliar, search the project's `README`, `CONTRIBUTING.md`, or `docs/` for the documented commands before guessing. When still unsure, ask the user — the verification commands they run locally are the most reliable source.

If a documented command is unavailable in the environment, report that clearly and suggest how to install or configure it; do not silently skip the verification step.

---

## Recommended Tools

Pick analyzers and visualization tools that fit the project's language; do not install everything by default. The full per-language catalog (linters, dependency graphers, dead-code detectors, architecture-boundary enforcement, static call-graph generation) is in [PATCHES.md §14](PATCHES.md). For any ecosystem, the language-server "Find References" + `git grep` / `ripgrep` cover most of what the analyzers do, more reliably and without setup cost.

---

## Output Format Reports

The three structured outputs produced during the workflow each have a canonical template in the `templates/` directory. Copy from these files when emitting a report; do not regenerate the skeleton from memory.

- **Phase 1 deliverable** — Architecture Recovery Report: see [templates/architecture_report.md](templates/architecture_report.md).
- **Phase 6 deliverable** — Behavior-Preserving Refactor Plan: see [templates/refactor_plan.md](templates/refactor_plan.md).
- **Post-stage deliverable** — Migration Stage Report (one per executed stage): see [templates/migration_stage_report.md](templates/migration_stage_report.md).

---

## Agent Behavior Requirements

When using this skill, the agent must:

1. Be conservative.
2. Be evidence-driven.
3. Ask for approval before risky changes.
4. Prefer staged migrations.
5. Explain uncertainty.
6. Avoid pretending static analysis is perfect.
7. Avoid deleting files based on names only.
8. Avoid large rewrites.
9. Avoid style-only churn.
10. Preserve behavior first.

---

## Final Success Criteria

The refactor is successful only if:

1. The project has a clear architecture map.
2. Entry points are documented.
3. Major call paths are understandable.
4. Module responsibilities are clear.
5. Debugging requires less cross-file jumping.
6. Dead-code candidates are verified before removal.
7. Architecture rules prevent future erosion.
8. Behavior is preserved.
9. Tests / lint / build pass or failures are clearly explained.
10. Future maintainers can quickly find where to add or fix functionality.
