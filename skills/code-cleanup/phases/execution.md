# Phases 5 & 6 — Execution

This file specifies the execution phases of the `code-cleanup` workflow plus the Implementation Rules, Common Refactor Patterns, and User Approval Gates that govern any refactor commit. SKILL.md is the entry point and table of contents; read this file when the task enters the execution stage (proposing a target architecture, planning stages, and committing changes).

Cross-references to PATCHES.md are one hop away. Workflow ordering (which phase comes next) is in SKILL.md. The Compatibility Wrapper Pattern is cross-cutting and lives in SKILL.md — refer back there for the wrapper template and the import-update sentence.

---

> *PATCHES guard:* The target tree MUST cite which [PATCHES.md §10](../PATCHES.md) exemplar it mirrors (Kubernetes `cmd / pkg / internal`, Django `apps/`, FastAPI single-import, React monorepo `packages/`, Rust Cargo workspaces, Bazel one-target-per-dir). Apply [PATCHES.md §2 Principle 4](../PATCHES.md) (Occam's Razor) — pick the smallest move set that resolves the diagnostic, not the most-complete-looking redesign.

## Phase 5: Target Architecture Proposal

Propose a target structure, but do not implement it yet.

The proposal must include:

1. Target directory tree.
2. Old path to new path mapping.
3. Rationale for each package / module.
4. Compatibility strategy.
5. Import update strategy.
6. Test strategy.
7. Rollback strategy.
8. Risk level for each move.
9. Approval requirement for each stage.

**There is no universal target layout.** Pick the structural exemplar from [PATCHES.md §10](../PATCHES.md) that matches the project's archetype — `cmd / pkg / internal` for Go services, `apps/<name>/{models, views, urls, services}` for Django, single canonical import surface for FastAPI, monorepo `packages/<scope>/` for React, Cargo workspaces for Rust, one-build-target-per-directory for Bazel. Cite which exemplar you mirror and why it fits.

The tree below is one common shape for a mid-size Python service; treat it as an illustrative example, not a prescription. The right layout for any given project is the one that matches its domain and conventions, not this one:

```txt
src/project_name/
  app/         { cli.py, bootstrap.py, runtime.py }
  core/        { domain.py, services.py, events.py }
  config/      { settings.py, loaders.py }
  integrations/{ external_service_a.py, external_service_b.py }
  evaluation/  { benchmark.py, reports.py }
  diagnostics/ { healthcheck.py, failure_analysis.py }
```

Adapt to the actual project — do not force this exact layout.

---

> *PATCHES guard:* Apply [PATCHES.md §3](../PATCHES.md) (Hard Safety Rules) to every stage — revert-on-red with **agent-owned-files-only** rollback (A1), one-refactor-per-commit hygiene (A2), prefer deterministic IDE / `ruff` / LSP refactor engines over hand-written diffs (A3). Apply [PATCHES.md §9](../PATCHES.md) (Macro vs Micro) — directory regroups and subsystem replacements require a Mikado graph, one leaf per PR, never a big-bang commit.

## Phase 6: Staged Refactor Plan

Create a staged plan before editing.

Recommended order:

### Stage 0: Documentation Only

Allowed:

- Add architecture notes.
- Add project map.
- Add entry point documentation.
- Add call path documentation.
- Add maintainer onboarding notes.

Not allowed:

- Moving files.
- Deleting files.
- Changing runtime behavior.

### Stage 1: Static Analysis Tooling

Allowed:

- Add or configure lint tools.
- Add dependency graph tools.
- Add dead-code detection tools.
- Add architecture boundary tools.
- Add scripts for project analysis.

Not allowed:

- Source behavior changes.

### Stage 2: Architecture Boundary Rules

Allowed:

- Add import boundary rules.
- Add dependency rules.
- Add CI checks if appropriate.

Not allowed:

- Moving many files at once.
- Deleting files.

### Stage 3: Low-Risk File Moves

Allowed:

- Move isolated scripts.
- Move benchmark / evaluation files.
- Move diagnostics / report files.
- Update imports mechanically (see SKILL.md Compatibility Wrapper Pattern for the LSP-rename-first sequence).
- Add compatibility wrappers.

Not allowed:

- Moving core runtime modules first.
- Renaming public APIs.
- Changing logic.

### Stage 4: Medium-Risk Module Reorganization

Allowed:

- Split mixed-responsibility files (see [PATCHES.md §5.4](../PATCHES.md) splitting playbook).
- Merge duplicate small modules (see [PATCHES.md §5.5](../PATCHES.md) duplicate-merging playbook).
- Simplify excessive nesting.
- Improve function names if internal only.

Requires approval.

### Stage 5: Core Refactor

Allowed only after tests and architecture rules are stable.

May include:

- Core module restructuring.
- Service extraction.
- Dependency inversion.
- Public API cleanup.

Requires explicit approval.

### Stage 6: Cleanup Compatibility Wrappers

Allowed only after:

1. Tests pass.
2. No internal imports use old paths.
3. CLI / script references are updated.
4. External usage risk is reviewed.
5. User approves removal.

---

## Implementation Rules

These rules apply when implementing a refactor stage along the **behavior-preserving path**. When the user has explicitly approved a **scoped rewrite**, the rules below apply only outside the rewrite scope; inside the rewrite scope, the user-agreed deltas govern (the rewrite's contract is itself a stage of the plan).

1. Implement only the approved stage.
2. Keep the diff small.
3. Avoid unrelated cleanup.
4. Do not rename functions / classes unless required.
5. Do not change behavior.
6. Do not change config formats.
7. Do not change CLI behavior.
8. Do not change database schemas.
9. Do not change file formats.
10. Do not delete files unless explicitly approved.
11. Update imports mechanically (see SKILL.md Compatibility Wrapper Pattern).
12. Add compatibility wrappers when moving public or uncertain modules.
13. Update documentation when structure changes.
14. Run verification commands.

---

## Common Refactor Patterns

### Pattern 1: Root-Level Module Grouping

Problem:

```txt
project/
  benchmark.py
  report.py
  runtime.py
  server.py
  config.py
  domain.py
```

Better:

```txt
project/
  core/
  runtime/
  evaluation/
  diagnostics/
  config/
```

Use only after import and entry-point analysis.

### Pattern 2: Compatibility Move

Old:

```txt
project/benchmark.py
```

New:

```txt
project/evaluation/benchmark.py
```

Temporary wrapper:

```python
from project.evaluation.benchmark import *  # noqa: F401,F403
```

### Pattern 3: Boundary Enforcement

Add rules such as:

```txt
core must not import evaluation
core must not import CLI
core must not import runtime integrations
evaluation may import core
runtime may import core
CLI may import everything needed for composition
```

### Pattern 4: Replace Hidden Flow with Explicit Flow

Bad:

```txt
main
  -> global registry
    -> dynamic side effect
      -> implicit tool execution
```

Better:

```txt
main
  -> build_config()
  -> build_registry()
  -> build_runtime()
  -> run()
```

### Pattern 5: Reduce Shotgun Surgery

If one feature requires edits in many unrelated files, identify:

- missing abstraction
- misplaced responsibility
- duplicated logic
- unclear ownership
- poor module boundary

Then propose a targeted structure change.

---

## User Approval Gates

Ask for approval before:

1. Moving core runtime files.
2. Deleting files.
3. Renaming public functions / classes.
4. Changing CLI commands.
5. Changing config formats.
6. Changing schemas.
7. Changing public import paths without wrappers.
8. Removing compatibility wrappers.
9. Changing tests that define expected behavior.
10. Refactoring dynamic / plugin systems.
