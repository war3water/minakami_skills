---
name: cleaning-project-redundancies
description: Analyze and safely remove project redundancies while preserving behavior. Use when users ask to deduplicate files/functions/modules, remove unused code, consolidate overlapping implementations, or reorganize folder structure with dependency-aware risk control and verification.
---

# Cleaning Project Redundancies

Use this skill to reduce duplication without introducing regressions.

For detailed patterns, load only when needed:
- `references/deduplication-guide.md`
- `references/folder-reorganization.md`

## Operating Priorities

1. Behavior preservation
2. Dependency and API safety
3. Reversibility and rollback readiness
4. Scope discipline
5. Cleanup completeness

If priorities conflict, choose the higher priority unless the user explicitly overrides.

## Rule Semantics

- `MUST`: required for all cleanup changes.
- `SHOULD`: default recommendation; deviation requires rationale.
- `MAY`: optional enhancement.

## Enforcement Standard

Require these before mutation:
- Explicit scope and exclusions.
- Dependency/reachability evidence for each removal.
- Risk tier and rollback path.
- Verification plan with acceptance criteria.
- Explicit user approval before destructive changes.

## Required Practices

1. Define scope and exclusions (`MUST`)
- Identify in-scope directories and file types.
- Exclude generated/vendor/build outputs unless user explicitly includes them.
- Protect entry points, public API surfaces, and critical config by default.

2. Build dependency and reachability map (`MUST`)
- Use fast file/symbol discovery (`rg --files`, `rg -n`) to map definitions, imports, exports, and call sites.
- Check both static references and common dynamic loading patterns.
- Treat unknown usage as risky, not safe.

3. Classify redundancy candidates (`MUST`)
- Separate exact duplicates, near duplicates, unused exports, and dead code.
- Do not classify by name similarity alone; confirm behavior and usage.
- Mark confidence as `High`, `Medium`, or `Low` based on evidence quality.

4. Produce cleanup proposal before edits (`MUST`)
- For every candidate, include reason, dependents, risk tier, and proposed action.
- Request explicit user approval for delete/merge/move operations.

5. Execute in reversible batches (`MUST`)
- Apply changes in small batches with clear commit boundaries.
- Update imports/references in the same batch as the moved/merged artifact.
- Keep rollback path ready (agent-native revert/undo first; use Git rollback only on explicit user request).

6. Verify each batch (`MUST`)
- Run language-appropriate syntax/build/tests.
- Confirm entry points and public API imports still resolve.
- Stop immediately on regression and roll back the failing batch.

7. Use evidence-based optimization for large repos (`SHOULD`)
- Start with cheap detection (path inventory, hashing, symbol index).
- Use deeper semantic comparison only for high-value candidates.
- Prefer scalable methods over manual full-repo inspection when repository size is large.

## Think-Before-Change Protocol

Use this for merges, deletions, and folder reorganization.

1. Define constraints
- Behavior that MUST remain unchanged.
- Public API compatibility expectations.
- Time budget and acceptable cleanup risk.

2. Design the action
- Candidate set and action per item (remove, merge, move, keep).
- Risk tier and rollback method per action.

3. Define verification
- Tests/checks required after each batch.
- Acceptance criteria for correctness and stability.

4. Execute and verify
- Apply one batch.
- Run checks.
- Continue only if acceptance criteria pass.

Exemption: no-behavior-change edits only (comments, formatting, pure rename with verified references).

## Verification & Acceptance

Minimum acceptance checks:
- No broken imports/includes/exports in affected modules.
- Syntax/build/tests pass for impacted scope.
- Entry points still run/import correctly.
- Public API compatibility is preserved or explicitly approved to change.
- All changes are traceable to approved proposal items.


## Rollback Policy

- `MUST`: Attempt agent-available revert/undo first for failed cleanup batches.
- `MUST`: If native revert is interactive or unavailable, stop mutation and request explicit user instruction.
- `SHOULD`: Prefer small reversible batches to minimize rollback scope.
- `MAY`: Use `git restore` or `git revert` only when the user explicitly requests Git-based rollback.

When rollback requires user UI interaction, do not continue edits until user confirms action.

## Failure Modes to Guard

- Removing code with unresolved dynamic references.
- Merging functions with incompatible semantics or error behavior.
- Deleting fixtures/tests because they appear unused.
- Performing large unbatched changes without rollback checkpoints.
- Treating build output changes as proof of behavioral safety.

## Deliverable Template

When applying this skill, output:

1. Scope and assumptions
2. Candidate inventory with confidence and risk tiers
3. Proposed batch sequence and rollback plan
4. Verification plan and acceptance criteria
5. Execution summary and residual risks

### Template: Cleanup Proposal

```text
Scope:
Protected areas:
Candidate set:
Proposed actions:
Risk tiers:
Rollback plan:
Approval required:
```

### Template: Candidate Row

```text
Item:
Type (exact duplicate / near duplicate / unused / dead code):
Evidence:
Dependents:
Risk tier:
Proposed action:
```

### Template: Verification Summary

```text
Batch:
Checks run:
Results:
Regressions found:
Rollback executed (if any):
Decision:
```

