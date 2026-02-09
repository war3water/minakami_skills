# Folder Reorganization Guide

Patterns for restructuring project directories to improve maintainability.

## Table of Contents

1. [Reorganization Principles](#reorganization-principles)
2. [Common Structures](#common-structures)
3. [Migration Strategy](#migration-strategy)
4. [Import Update Automation](#import-update-automation)

---

## Reorganization Principles

### Group by Feature, Not Type

**Avoid** (type-based):
```
src/
├── controllers/
│   ├── user_controller.py
│   └── order_controller.py
├── models/
│   ├── user_model.py
│   └── order_model.py
└── services/
    ├── user_service.py
    └── order_service.py
```

**Prefer** (feature-based):
```
src/
├── users/
│   ├── controller.py
│   ├── model.py
│   └── service.py
└── orders/
    ├── controller.py
    ├── model.py
    └── service.py
```

### Keep Tests Near Source

**Good**:
```
src/
├── users/
│   ├── service.py
│   └── test_service.py
```

**Also Good** (parallel structure):
```
src/users/service.py
tests/users/test_service.py
```

### Flat Hierarchy (Max 3 Levels)

**Avoid**:
```
src/core/domain/users/handlers/admin/permissions/check.py
```

**Prefer**:
```
src/users/admin_permissions.py
```

### Separate Concerns

Standard layers:

| Layer | Purpose | Example |
|-------|---------|---------|
| `core/` | Business logic, domain models | entities, rules |
| `adapters/` | External integrations | API clients, DB |
| `utils/` | Shared utilities | formatters, validators |
| `config/` | Configuration | settings, constants |
| `tests/` | Test suites | unit, integration |

---

## Common Structures

### Python Package

```
my_package/
├── __init__.py          # Package exports
├── core/
│   ├── __init__.py
│   └── domain.py        # Core business logic
├── adapters/
│   ├── __init__.py
│   ├── database.py
│   └── api_client.py
├── utils/
│   ├── __init__.py
│   └── helpers.py
└── tests/
    ├── __init__.py
    ├── test_domain.py
    └── test_adapters.py
```

### JavaScript/TypeScript

```
src/
├── index.ts             # Main exports
├── features/
│   ├── users/
│   │   ├── index.ts
│   │   ├── UserService.ts
│   │   └── UserService.test.ts
│   └── orders/
│       └── ...
├── shared/
│   ├── utils/
│   └── types/
└── config/
    └── index.ts
```

### Monorepo

```
packages/
├── core/                # Shared business logic
│   ├── package.json
│   └── src/
├── api/                 # Backend service
│   ├── package.json
│   └── src/
└── web/                 # Frontend app
    ├── package.json
    └── src/
```

---

## Migration Strategy

### Step-by-Step Process

```
Migration Progress:
- [ ] Map current structure
- [ ] Design target structure
- [ ] Create new directories
- [ ] Move files one group at a time
- [ ] Update imports after each move
- [ ] Run tests after each group
- [ ] Remove empty old directories
```

### Safe Move Procedure

1. **Create target directory**
   ```bash
   mkdir -p src/features/users
   ```

2. **Copy file (don't move yet)**
   ```bash
   cp src/controllers/user_controller.py src/features/users/controller.py
   ```

3. **Update imports in copied file**
   - Fix relative imports
   - Update any hardcoded paths

4. **Update all importers**
   ```bash
   # Find files importing the old location
   grep -r "from controllers.user_controller" --include="*.py"
   ```

5. **Run tests**
   ```bash
   pytest -x
   ```

6. **Remove old file**
   ```bash
   rm src/controllers/user_controller.py
   ```

---

## Import Update Automation

### Python Import Fixer

```python
import re
from pathlib import Path

def update_imports(filepath, old_module, new_module):
    """Update import statements in a file."""
    content = Path(filepath).read_text()
    
    # from old.module import X -> from new.module import X
    pattern = rf'from {re.escape(old_module)} import'
    replacement = f'from {new_module} import'
    updated = re.sub(pattern, replacement, content)
    
    # import old.module -> import new.module
    pattern = rf'import {re.escape(old_module)}'
    replacement = f'import {new_module}'
    updated = re.sub(pattern, replacement, updated)
    
    if updated != content:
        Path(filepath).write_text(updated)
        return True
    return False
```

### Batch Update Script

```python
def batch_update_imports(project_root, mapping):
    """
    Update imports across project.
    
    mapping: dict of {old_module: new_module}
    """
    updated_files = []
    for filepath in find_source_files(project_root):
        for old, new in mapping.items():
            if update_imports(filepath, old, new):
                updated_files.append(filepath)
    return updated_files
```

### __init__.py Re-exports

When moving modules, maintain backward compatibility:

```python
# old_location/__init__.py
# Deprecation shim for backward compatibility
from new_location.module import *  # Re-export everything

import warnings
warnings.warn(
    "Importing from old_location is deprecated. "
    "Use new_location instead.",
    DeprecationWarning,
    stacklevel=2
)
```

---

## Validation Checklist

After reorganization:

```
[ ] All imports resolve (python -c "import package")
[ ] No circular imports
[ ] Tests pass
[ ] Entry points work (main.py, CLI, etc.)
[ ] Documentation paths updated
[ ] CI/CD configs updated if paths changed
```
