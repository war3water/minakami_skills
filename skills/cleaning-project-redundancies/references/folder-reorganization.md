# Folder Reorganization Guide

Use this reference when redundancy cleanup includes moving files or modules.

## Reorganization Principles

1. Preserve behavior first
- Keep runtime behavior and public contracts stable during structure moves.

2. Group by domain boundaries
- Prefer feature/domain modules over broad type-only folders when it improves cohesion.

3. Keep test discoverability intact
- Preserve existing test conventions and CI paths.

4. Limit migration blast radius
- Move a small cohesive group at a time.

## Safe Migration Workflow

1. Map current and target structure
- Document old path, new path, dependents, and risk level.

2. Move with history

```bash
git mv old/path/module.py new/path/module.py
```

3. Update imports/references in same batch
- Use `rg -n` to locate old path and module references.
- Patch all call sites in one atomic change.

4. Verify immediately
- Run stack-appropriate build/tests after each batch.

5. Commit batch before next move
- Keep commit scope narrow for easy rollback.

## Backward Compatibility Patterns

- Use temporary compatibility shims only when required by consumers.
- Add explicit deprecation note and planned removal horizon.
- Remove shims after migration window closes.

## Risks to Track

- Hidden path references in config, scripts, docs, and CI.
- Circular dependencies introduced by new layout.
- Entry-point breakage from moved bootstrap files.
- Import path mismatches between development and production environments.

## Validation Checklist

```text
[ ] All moved module imports resolve
[ ] Entry points still execute
[ ] Test suite passes for impacted scope
[ ] CI configuration paths remain valid
[ ] No accidental API contract changes
[ ] Rollback path tested or documented
```
