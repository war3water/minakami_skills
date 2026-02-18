# Deduplication Guide

Use this reference when candidate volume is high or duplicate analysis needs stronger evidence.

## Detection Pipeline

1. Inventory files
- Use fast listing first: `rg --files`.
- Segment by language and source roots before deeper analysis.

2. Identify exact duplicates
- Hash file contents (`sha256`) to find byte-identical files.
- Validate path intent before removal (generated files and templates can be intentionally duplicated).

3. Identify near duplicates
- Build symbol inventory with `rg -n` for function/class definitions.
- Compare signatures, control flow shape, and error behavior.
- Treat similarity-only findings as `Medium` confidence until usage analysis passes.

4. Build usage map
- Locate all references with `rg -n "<symbol_or_module>"`.
- Check static and common dynamic loading paths.
- Include tests and scripts in the search scope unless explicitly excluded.

5. Rank by confidence
- `High`: exact duplicate + verified safe dependents.
- `Medium`: near duplicate + mostly aligned behavior.
- `Low`: uncertain reachability, reflection/dynamic loading, or public API exposure.

## Merge Decision Rules

- Merge only if semantics, side effects, and error behavior are compatible.
- Keep one canonical implementation with tests covering merged behavior.
- Do not merge functions that differ in contracts, precision, or failure semantics.

## Dynamic Reference Watchlist

Search for patterns that hide dependencies:
- Python: `importlib`, `__import__`, `getattr` with string module paths
- JavaScript/TypeScript: `import()`, variable `require(...)`
- Java/JVM: reflection and class-name strings
- Framework registries and plugin maps in config files

If dynamic usage is plausible and unproven, keep candidate risk at `Low` and require explicit approval.

## Verification Matrix

Run checks matching project stack:

| Stack | Core checks |
|---|---|
| Python | `python -m compileall`, `pytest` |
| JS/TS | `npm run build`/`pnpm build`, `npm test`, `tsc --noEmit` |
| Go | `go build ./...`, `go test ./...` |
| Rust | `cargo check`, `cargo test` |
| Java | `mvn test` or `gradle test` |
| C/C++ | project build + test target |

For unlisted stacks/frameworks, use this fallback verification sequence:

1. Run syntax/type validation (or equivalent static checks).
2. Run the project build/compile step for impacted modules.
3. Run automated tests for the impacted scope; prefer full suite if risk is high.
4. Run a minimal runtime smoke check for entry points affected by cleanup.
5. Treat failures or missing tooling as `Medium`/`Low` confidence and require explicit user approval before deletion.

## Rollback Pattern

Normative rollback rules are defined in `SKILL.md`; this section provides optional command examples.

Example order:

1. Try the active agent's native undo/revert if available in the current context.
2. Restore from a temporary pre-batch backup stored outside the project repository.
3. Use Git rollback only when explicitly requested by the user.

If Git rollback is explicitly requested:

```bash
git restore -- <affected_paths>
# or
git revert <commit_sha>
```



