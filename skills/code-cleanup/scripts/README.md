# Scripts

> **STATUS: roadmap only — none of the scripts listed below are implemented.**
> This README is non-contractual. The skill does **not** rely on any of these
> scripts existing. Treat the list as "what would be useful if someone wrote
> them," not as "what the skill calls."
>
> **Manual fallbacks** (use these instead of the unimplemented scripts):
>
> | Roadmap script | Manual fallback |
> |---|---|
> | `find_entrypoints.py` | grep for `if __name__ == "__main__"`, `def main(`, `[project.scripts]` in `pyproject.toml`, `bin:` in `package.json`, `cmd/*/main.go` |
> | `collect_imports.py` | `grep -rn "^import\|^from" --include='*.py'`; for graphs, install `pydeps` on demand |
> | `classify_files.py` | LLM read-pass over module docstrings + directory names, classify by responsibility (see PATCHES.md §2) |
> | `detect_dead_candidates.py` | install `vulture` (Python) / `knip` (JS-TS) on demand and follow PATCHES.md §6 Safe-Deletion Playbook |
> | `generate_architecture_report.py` | hand-fill `templates/architecture_report.md` from grep + LSP "Find References" output |

This folder can contain deterministic helper scripts used by the refactor skill.

Recommended scripts (NOT YET IMPLEMENTED):

## `find_entrypoints.py`

Find likely runtime entry points:

- `__main__.py`
- CLI files
- server files
- scripts
- package entry points
- test entry points

## `collect_imports.py`

Collect import relationships and output:

- module imports
- imported-by map
- high fan-in modules
- high fan-out modules
- possible cycles

## `classify_files.py`

Classify files by likely responsibility:

- core
- config
- runtime
- integration
- evaluation
- diagnostics
- tests
- scripts
- generated
- unknown

## `detect_dead_candidates.py`

Find files or symbols that may be unused.

Important:
The script must only mark candidates. It must not delete files.

## `generate_architecture_report.py`

Generate a Markdown architecture report from collected data.
