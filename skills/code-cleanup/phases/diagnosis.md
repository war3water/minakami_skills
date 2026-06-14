# Phases 2, 3 & 4 — Diagnosis

This file specifies the diagnostic phases of the `code-cleanup` workflow. SKILL.md is the entry point and table of contents; read this file when the task enters the diagnosis stage (classifying files, mapping dependencies, and identifying maintainability issues).

Cross-references to PATCHES.md are one hop away. Workflow ordering (which phase comes next) is in SKILL.md.

---

> *PATCHES guard:* When filling the "Recommended Location" column, draw from [PATCHES.md §10](../PATCHES.md) (Google + OSS exemplars). When filling "Recommended Action", apply [PATCHES.md §2](../PATCHES.md) design principles (especially Principle 2 — no nesting without strong reason) and [PATCHES.md §6](../PATCHES.md) (Safe-Deletion Playbook) for any `delete candidate`.

## Phase 2: File Classification

Classify important files using a table.

Required columns:

| File Path | Current Responsibility | Imported By | Imports | Entry Point? | Risk Level | Recommended Location | Recommended Action | Notes |
|---|---|---|---|---|---|---|---|---|

Allowed values for `Risk Level`: **low**, **medium**, **high**, **unknown**.

Allowed values for `Recommended Action` and when each applies:

| Action | Use when |
|---|---|
| **keep** | actively imported; an entry point; framework-loaded; part of the public API; dynamically / plugin-registered. The file's role is clear and stable. |
| **rename candidate** | the current name doesn't reflect responsibility — but the file is otherwise in the right place and doing the right thing. |
| **move candidate** | responsibility is clear and the file belongs in a different package; import updates are mechanical; a compatibility wrapper can preserve the old path; risk is low or medium. |
| **split candidate** | the file mixes unrelated responsibilities, has multiple independent clusters, is a debugging hotspot, or shows high fan-out with low cohesion. |
| **merge candidate** | several tiny files create unnecessary indirection; the abstractions don't carry real meaning; maintainers must jump across files for one concept. |
| **simplify candidate** | the file's responsibility is correct but the implementation is excessively nested or indirected (apply the [§5 Reduce-Nesting Catalog](../PATCHES.md)). |
| **delete candidate** | not imported, not referenced by scripts, not dynamically loaded, not a framework convention, not part of the public API, not used in tests, and the user approves. **[PATCHES.md §6 — 8-step Safe-Deletion Playbook](../PATCHES.md) supersedes this row's criteria.** |
| **needs verification** | static analysis is inconclusive; a dynamic import may exist; the filename suggests plugin / tool registration; the code uses decorators or reflection; external usage is possible. Resolve via [PATCHES.md §7](../PATCHES.md) batched yes/no, not per-item asking. |
| **do not touch without tests** | the file is risky and no characterization tests cover it; consumer surfaces are unclear. Add characterization tests (Feathers) before any change. |

**Marking discipline:**

- Do not mark a file as `delete candidate` without evidence — see the playbook reference above.
- If the file may be dynamically loaded, mark `high` risk or `needs verification`.
- If the file is reached via CLI, plugin registration, reflection, decorators, or framework conventions, mark `high` risk.
- If genuinely unsure, mark `needs verification`. Resolve in batches, not by guessing.

---

> *PATCHES guard:* While building the call-path map, run [PATCHES.md §5.1](../PATCHES.md) (Reduce-Nesting Diagnostic Pass) on each deep chain — flag pass-through wrappers, single-impl interfaces, and string-keyed single-target dispatchers as nesting-reduction candidates for Phase 4.

## Phase 3: Dependency and Call-Path Analysis

Build a maintainer-oriented map.

Include:

1. Entry point to major call paths.
2. Major import dependencies.
3. High fan-in files.
4. High fan-out files.
5. Circular dependencies.
6. Cross-domain imports.
7. Deep call chains.
8. Overly broad utility modules.
9. Files that mix multiple responsibilities.
10. Files that make debugging difficult.

Represent the result as:

```txt
EntryPointA
  -> ModuleA.function_a
    -> ModuleB.function_b
      -> ModuleC.function_c
```

Also provide a dependency summary:

```txt
core
  imports: config, events, models
  imported by: app, eval, runtime

eval
  imports: core, diagnostics
  imported by: CLI only
```

If static call graph accuracy is uncertain, say so clearly.

---

> *PATCHES guard:* For "excessive nesting" and "excessive indirection" issues, use the full [PATCHES.md §5](../PATCHES.md) technique catalog (allowed micro-refactors + when NOT to flatten). For "dead code candidates" and "orphaned files", route through [PATCHES.md §6](../PATCHES.md) (8-step Safe-Deletion Playbook). For uncertain items, use [PATCHES.md §7](../PATCHES.md) (Needs-Verification Resolution Loop) — batched user yes/no, not per-item asking.

## Phase 4: Maintainability Diagnosis

Identify maintainability issues using these categories:

1. Architecture / module boundary issues.
2. Excessive nesting.
3. Excessive indirection.
4. Hidden side effects.
5. Duplicate logic.
6. Dead code candidates.
7. Orphaned files.
8. Misleading names.
9. Misplaced files.
10. Overly broad utilities.
11. Circular dependencies.
12. Noisy tests.
13. Ineffective warnings.
14. Missing onboarding documentation.
15. Risky areas without test coverage.

For each issue, include:

- File path.
- Problem category.
- Evidence.
- Why it blocks debugging or future changes.
- Risk level.
- Recommended action.
- Verification method.
- Whether behavior may change.
