# Cross-Platform Setup

Use this when preflight fails on a new machine.

## Windows (PowerShell)

1. Verify tools:
   - `python --version`
   - `git --version`
   - `rg --version`
   - `Get-Command codex-wrapper`
   - `Get-Command codex`
2. If auth probe fails:
   - `codex login`

## Ubuntu / WSL (Linux)

1. Install baseline tools:
```bash
sudo apt-get update
sudo apt-get install -y python3 git ripgrep nodejs npm
```
2. Verify:
```bash
python3 --version
git --version
rg --version
which codex-wrapper || true
which codex || true
codex --version
```
3. If auth probe fails:
```bash
codex login
```

## macOS (Homebrew)

1. Install baseline tools:
```bash
brew install python git ripgrep node
```
2. Verify:
```bash
python3 --version
git --version
rg --version
which codex-wrapper || true
which codex || true
codex --version
```
3. If auth probe fails:
```bash
codex login
```

## Notes

1. Codex auth is environment-local (Windows host auth does not automatically apply to WSL).
2. On WSL, non-ASCII Windows paths may fail; mirror files to ASCII-only paths for tooling checks.
3. If reviewer output reports sandbox policy blocks (for example, cannot execute `python`), treat it as an environment-permission signal and switch to user-confirmation flow.
4. Prefer prompt files over multiline command-line prompt arguments to avoid wrapper argument/quoting drop that can produce empty reviewer outputs.
5. Run reviewers via `scripts/run_review_cycle.py` (process orchestration) instead of ad-hoc manual shell fan-out; this enforces shared workdir, PYTHONPATH, timeout, and atomic writes.
