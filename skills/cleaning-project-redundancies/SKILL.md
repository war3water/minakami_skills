---
name: cleaning-project-redundancies
description: Analyze and clean redundant files, duplicate functions, and code in projects while preserving original behavior. Use when users ask to deduplicate code, remove unused files, identify duplicate functions, clean up a codebase, refactor for DRY principles, or reorganize project folder structure. Performs deep dependency analysis to prevent breaking changes.
---

# Cleaning Project Redundancies

Analyze projects to identify and safely remove redundant files, duplicate functions, and unused code while preserving original behavior and preventing breaking changes.

## Core Principles

1. **Behavior Preservation**: Never alter function logic, inputs, or outputs
2. **Dependency Safety**: Deep analysis of imports, usages, and relationships before any removal
3. **Incremental Changes**: Small, verifiable steps with rollback capability
4. **User Approval**: Always present findings before executing changes

## Workflow

Copy this checklist and track progress:

```text
Cleanup Progress:
- [ ] Step 1: Analyze project structure
- [ ] Step 2: Build dependency graph
- [ ] Step 3: Identify duplicates and redundancies
- [ ] Step 4: Generate cleanup report
- [ ] Step 5: Execute approved changes
- [ ] Step 6: Verify no breaking changes
```

### Step 1: Analyze Project Structure

Use available tools to scan the project:

**Principle: Detect language from project files first**

1. Look for language indicators:
   - Build files: `pom.xml` (Java), `go.mod` (Go), `Cargo.toml` (Rust), `package.json` (JS/TS), `requirements.txt`/`pyproject.toml` (Python)
   - File extensions in the project root and src directories

2. Once language is identified, search for source files:
   - Use `find_by_name` with detected extensions
   - Check project conventions for source directories (src/, lib/, app/, pkg/)

3. Use `grep_search` to understand code patterns:
   - Search for import/include statements (language-appropriate)
   - Search for function/class definitions

Document:

- Detected primary language(s)
- Entry points (main files, index files)
- Core modules vs utilities
- Test directories
- Config files

### Step 2: Build Dependency Graph

For each major file, identify:

- **Imports**: What it depends on
- **Exports**: What it exposes (public functions/classes)
- **Usages**: Where it's referenced

**Common import patterns (examples, not exhaustive):**

| Language | Import Pattern | Search Query |
|----------|----------------|--------------|
| Python | `import x`, `from x import y` | `^import\|^from .* import` |
| Java | `import package.Class;` | `^import ` |
| Go | `import "package"` | `^import ` |
| C/C++ | `#include <header>` | `^#include` |
| JavaScript | `import`, `require()` | `import\|require\(` |
| Rust | `use crate::`, `mod` | `^use \|^mod ` |

> [!TIP]
> **For unlisted languages:** Look at the language's documentation for import/include syntax, then construct an appropriate grep pattern. The principle is: find how modules reference each other.

### Step 3: Identify Duplicates and Redundancies

**Detection methods (language-agnostic):**

1. **Exact duplicates**: Files with identical content (compare via reading)
2. **Near duplicates**: Functions with similar structure (read and compare)
3. **Unused exports**: Functions never imported elsewhere
4. **Dead code**: Unreachable code paths

**How to find duplicates without scripts:**

1. Use `grep_search` to find function/class definitions
2. Use `view_file` to read and compare similar-named functions
3. Search for imports of each function to verify usage

**Example workflow:**

```text
# Find all function definitions
grep_search(Query="^def |^function |^func |public .* \(", SearchPath="src/")

# For each function, search for its usages
grep_search(Query="function_name", SearchPath=".")

# If no usages found outside definition file, it may be unused
```

### Step 4: Generate Cleanup Report

Create a structured report:

```markdown
# Cleanup Report: [Project Name]

## Summary
- Files analyzed: [N]
- Duplicate groups found: [N]
- Unused files identified: [N]

## Safe to Remove (No Dependencies)

| File/Function | Reason | Confidence |
|---------------|--------|------------|
| utils/old_helper.py | No imports found | High |

## Requires Review (Has Dependencies)

| File/Function | Dependents | Suggested Action |
|---------------|------------|------------------|
| lib/parser.py:parse_v1() | 2 files | Merge with parse_v2() |
```

### Step 5: Execute Approved Changes

**CRITICAL**: Only proceed after user approval.

For each approved change:

1. **Backup**: Use git or create backup copies
2. **Remove/Refactor**: Execute the change
3. **Update imports**: Fix all dependent files
4. **Test**: Run project tests

### Step 6: Verify No Breaking Changes

Run language-appropriate verification:

| Language | Verification Commands |
|----------|----------------------|
| Python | `pytest`, `python -c "import package"` |
| Java | `mvn test`, `gradle test` |
| Go | `go test ./...`, `go build` |
| JavaScript | `npm test`, `yarn test` |
| C/C++ | `make test`, `cmake --build . --target test` |
| Rust | `cargo test`, `cargo build` |

## Safety Rules

> [!CAUTION]
> Never remove without completing dependency analysis

- **DO NOT** remove files that are imported elsewhere
- **DO NOT** merge functions with different signatures
- **DO NOT** delete test files or fixtures
- **DO NOT** modify files outside project scope
- **ALWAYS** preserve git history (no force rewrites)

## Folder Reorganization

See [references/folder-reorganization.md](references/folder-reorganization.md) for detailed patterns.

Key principles:

- Group by domain/feature, not by type
- Keep related tests near source files
- Separate concerns: core, utils, adapters, tests
- Maintain flat hierarchy (max 3 levels deep)

## Merging Duplicate Functions

When duplicates are found:

1. **Identify the canonical version** — Pick the most complete/tested implementation
2. **Parameterize differences** — If functions differ only in config, add parameters
3. **Create shared module** — Move to shared location
4. **Update all import sites** — Find and replace imports
5. **Verify with tests** — Run tests after each merge

**Merge decision heuristics:**

| Scenario | Action |
|----------|--------|
| Identical functions | Keep one, delete other, update imports |
| >90% similarity | Merge with parameters if signature compatible |
| 80-90% similarity | Review manually, may have subtle differences |
| Different signatures | Do NOT merge, may be intentional |

## Archiving Deprecated Files

Instead of deleting, archive to preserve history:

```bash
# Move with git history preserved
git mv old_module.py _archive/old_module.py
git commit -m "archive: deprecate old_module.py"
```

## Categorizing Files

Use content-based heuristics:

| File Contains | Category |
|---------------|----------|
| HTTP endpoints, routes | `api/` |
| Database models, ORM | `models/` |
| Business logic | `core/` |
| External API clients | `adapters/` |
| Helper functions | `utils/` |
| Test files | `tests/` |

## Language-Specific Patterns

**Python**: Check `__init__.py` exports, `__all__` lists, relative imports.

**Java**: Check `public` visibility, package structure, `pom.xml`/`build.gradle` modules.

**Go**: Check exported names (capitalized), `go.mod` dependencies.

**JavaScript/TypeScript**: Check `index.js` re-exports, `package.json` main/exports.

**C/C++**: Check header guards, `#include` paths, namespace usage.

**Rust**: Check `pub` visibility, `mod.rs` structure, `Cargo.toml` dependencies.

## Error Handling

If analysis fails:

1. Check file encoding (use UTF-8)
2. Verify syntax is valid (no parse errors)
3. Exclude generated files (node_modules, target, build, dist)
4. Retry with smaller scope

## Output Format

Final report structure:

```json
{
  "project": "project-name",
  "language": "detected-language",
  "summary": {
    "files_scanned": 150,
    "duplicates_found": 12,
    "unused_files": 5,
    "safe_removals": 8
  },
  "duplicates": [],
  "unused": [],
  "reorganization": {}
}
```
