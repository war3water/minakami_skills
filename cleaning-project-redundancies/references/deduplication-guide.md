# Deduplication Guide

Detailed patterns for identifying and safely removing duplicate code across any programming language.

## Table of Contents

1. [Duplicate Detection Methods](#duplicate-detection-methods)
2. [Safe Merge Patterns](#safe-merge-patterns)
3. [Dependency Analysis](#dependency-analysis)
4. [Verification Steps](#verification-steps)

---

## Duplicate Detection Methods

### Exact Duplicates (Type 1)

Identical code blocks (ignoring whitespace/comments).

**Detection approach:**

1. Read file contents using `view_file`
2. Compare content directly or conceptually
3. Group files with identical logic

### Near Duplicates (Type 2/3)

Similar code with minor variations (renamed variables, reordered statements).

**Detection approach:**

1. Search for similar function names using `grep_search`
2. Read and compare function bodies
3. Identify structural similarities despite naming differences

**Example queries:**

| Language | Function Definition Pattern |
|----------|----------------------------|
| Python | `^def \|^async def ` |
| Java | `public\|private\|protected .* \(` |
| Go | `^func ` |
| JavaScript | `^function \|^const .* = \(` |
| C/C++ | Pattern: return type + name + `(` |
| Rust | `^fn \|^pub fn ` |

### Function-Level Duplicates

Compare individual functions across files:

1. **Find all function definitions** using language-appropriate grep patterns
2. **Group by function name** — Same names in different files may be duplicates
3. **Compare bodies** — Read each and assess similarity
4. **Check signatures** — Identical signatures with different bodies = potential conflict

---

## Safe Merge Patterns

### Pattern 1: Consolidate to Shared Module

**Before:**

```text
src/
├── module_a/utils.py  # def format_date(d): ...
└── module_b/utils.py  # def format_date(d): ...  (duplicate)
```

**After:**

```text
src/
├── shared/date_utils.py  # def format_date(d): ...
├── module_a/             # imports from shared
└── module_b/             # imports from shared
```

### Pattern 2: Extract Base Class/Interface

When multiple classes share methods, extract common behavior.

**Works in:** Python (mixin), Java (interface/abstract), Go (embedded struct), Rust (trait)

### Pattern 3: Parameterize Differences

When functions differ only in configuration, merge with parameters.

**Example concept:**

```text
# Before
process_csv() -> uses ','
process_tsv() -> uses '\t'

# After
process_file(delimiter) -> single implementation
```

---

## Dependency Analysis

### Import Pattern Reference

| Language | Import Search Pattern | Export Search Pattern |
|----------|----------------------|----------------------|
| Python | `^import \|^from .* import` | `^def \|^class \|^__all__` |
| Java | `^import ` | `^public ` |
| Go | `^import ` | Capitalized identifiers |
| JavaScript | `import \|require\(` | `export \|module.exports` |
| TypeScript | `import \|from ` | `export ` |
| C/C++ | `^#include` | Header file declarations |
| Rust | `^use \|^mod ` | `^pub ` |

### Safe Removal Check

Before removing a file/function, verify:

1. **No direct imports**: Search for import statements referencing the target
2. **No dynamic imports**: Search for dynamic loading patterns
3. **No string references**: Search for string literals containing the name
4. **No test dependencies**: Check test files separately

**Language-specific dynamic import patterns:**

| Language | Dynamic Import Pattern |
|----------|----------------------|
| Python | `importlib`, `__import__()` |
| Java | `Class.forName()`, reflection |
| JavaScript | `import()`, `require(var)` |
| Go | Generally not applicable |
| Rust | Generally not applicable |

---

## Verification Steps

### Pre-Removal Checklist

```text
[ ] No imports found for this module/function
[ ] No string references found
[ ] Tests pass with file present
[ ] File is not an entry point (main, index)
[ ] File is not in public exports (__init__.py, index.js, mod.rs)
```

### Post-Removal Verification

Run language-appropriate checks:

| Language | Syntax Check | Import Check | Test Command |
|----------|-------------|--------------|--------------|
| Python | `python -m py_compile file.py` | `python -c "import pkg"` | `pytest` |
| Java | `javac File.java` | Compile succeeds | `mvn test` |
| Go | `go build` | `go build` | `go test ./...` |
| JavaScript | Lint (ESLint) | `node -e "require('pkg')"` | `npm test` |
| TypeScript | `tsc --noEmit` | `tsc` | `npm test` |
| C/C++ | `gcc/g++ -c file.c` | Link succeeds | `make test` |
| Rust | `cargo check` | `cargo build` | `cargo test` |

### Rollback Procedure

If verification fails:

```bash
# Restore from git
git checkout -- removed_file.py

# Or restore from backup
mv removed_file.py.bak removed_file.py
```

---

## Tips for Claude

When using this skill, Claude should:

1. **Use `grep_search`** to find definitions and usages
2. **Use `view_file`** to compare function bodies
3. **Use `find_by_name`** to locate files by extension
4. **Document findings** in a structured report before suggesting removals
5. **Always ask for user approval** before deleting or merging code
