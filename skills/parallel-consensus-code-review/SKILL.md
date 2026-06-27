---
name: parallel-consensus-code-review
description: Use whenever the user asks for a parallel code review team, reviewer discussion/consensus, anti-bias review process, or iterative re-review after fixes. This skill runs independent CodeX CLI reviewers in parallel (default 3, user-configurable), merges evidence, reaches consensus, fixes, and repeats until no new blocking issues remain.
---

# Parallel Consensus Code Review

Run a reusable parallel-reviewer CodeX CLI workflow (default team size: 3) that minimizes anchoring bias and stores review artifacts in a deterministic folder.

## Trigger Boundaries

Use this skill:
1. User requests "parallel reviewers", "review committee", "consensus review", or "reviewers discuss with each other".
2. User requires anti-bias review or post-fix re-review loops.

Do not use this skill:
1. Routine single-review checkpoints (`requesting-code-review`).
2. Feedback handling only (`receiving-code-review`).
3. Generic Codex execution without review-orchestration policy (`codex`).

## Related Skills

Use this skill for the multi-reviewer consensus loop; hand its consensus findings to `receiving-code-review` for disciplined implementation, and re-enter for post-fix re-review until no new blocking issues. For a single routine checkpoint use `requesting-code-review`; for raw Codex CLI invocation mechanics use `codex`.

## New-Machine Setup (Preflight)

Before first use on a new computer, verify prerequisites:
1. Python available (`python --version` or `python3 --version`)
2. Git available (`git --version`)
3. Ripgrep available (`rg --version`)
4. Codex transport available: `codex-wrapper` or native `codex`
5. Authentication already completed for the local Codex CLI

Use script:
1. `python scripts/preflight_check.py --project-root <project-root>`
2. Optional auth probe: `python scripts/preflight_check.py --project-root <project-root> --check-auth`
3. If setup fails, follow `references/setup_cross_platform.md`.

Cross-platform notes:
1. Windows PowerShell: `Get-Command codex-wrapper`, `Get-Command codex`
2. macOS/Linux: `which codex-wrapper`, `which codex`
3. Linux verification from Windows can use WSL.
4. WSL/Linux auth is environment-local: run `codex login` inside WSL if auth probe fails.
5. If WSL cannot resolve non-ASCII host paths, mirror skill/project to an ASCII-only path before testing.

## Required Inputs

1. User review query/objective (`review_query.md`) - primary audit intent.
2. Audit checklist items (`audit_items.md`) - explicit review standards.
3. Project-level approved review rules (`_code_reviews_ai/project_review_rules.json`) shared by all reviewers.
4. Review scope (`WHAT_WAS_IMPLEMENTED`) and requirements/plan reference (`PLAN_OR_REQUIREMENTS`).
5. Diff range (`BASE_SHA`, `HEAD_SHA`) or non-git fallback file scope (`changed_files.txt` + `context_notes.md`).
6. Completion criterion (for example: "no new blocking issues in a full post-fix cycle").
7. Retry policy:
   - `max_retries` (default `5`)
   - `permission_confirm_after` (default `2`)
8. Reviewer team policy:
   - default reviewer count `3`
   - user can override via explicit reviewer count or reviewer ids
9. Blocking closure policy:
   - clear marker(s): default `NO_NEW_BLOCKING_ISSUES` (legacy-compatible `NO_NEW_ISSUES`)
   - narrative clear phrase fallback is enabled by default (for reports like "No blocking findings") and can be customized
   - set strict marker-only mode when required by governance
   - consensus threshold: default majority (`ceil(team_size/2)`)
   - blocking classes: `must_fix` + `should_fix` items with important efficiency/performance/reliability/security/correctness impact

## Workflow

1. Run preflight checks (`scripts/preflight_check.py`) on new environments.
2. Create run folder under `_code_reviews_ai/` using `scripts/init_review_run.py --max-retries <N> --reviewer-count <K>` (defaults: `5`, `3`) or equivalent deterministic layout from `references/storage_layout.md`.
3. Maintain project-level rules through `scripts/manage_project_rules.py`:
   - agent proposes rules as `pending`
   - user approves rules to `approved`
   - only approved rules are applied in reviewer prompts
4. Prepare one shared review packet: user review query, audit checklist, scope, requirements, diff/files (or non-git fallback scope), and test/gate evidence. Hard-require at least a review objective and explicit code scope before fan-out; other inputs are conditional (requirements only when judging conformance, test/gate evidence only for runtime claims). Record any missing input as an explicit known-unknown in `context_notes.md` — thin context biases reviewers toward scope-blind nitpicks and invented issues, so name the gap rather than letting them guess.
5. If project root is not a Git repo (or diff range is unavailable), require an explicit touched file list and forbid snapshot-wide review.
6. Run reviewer execution through `scripts/run_review_cycle.py` (real process orchestration, not prompt-only policy):
   - separate reviewer processes
   - fixed workdir at project root
   - normalized `PYTHONPATH`
   - per-reviewer timeout
   - automatic retry on empty output
   - atomic writes (`tmp -> rename`)
   - cycle lock to prevent concurrent writer collisions
   - injects `review_query.md` + `audit_items.md` + scope context into reviewer prompts
   - injects project-level approved rules from `_code_reviews_ai/project_review_rules.json`
   - keeps independent first pass blind to historical `fix_log` context by default (`--inject-fix-log-context` only when explicitly requested)
   - prompt resolution is reviewer-id based: `<prompt-dir>/<reviewer_id>_prompt.md` (or default cycle folder) with optional repeatable overrides via `--reviewer-prompt reviewer_id=path`
   - emits markdown table summary to stdout and writes `cycle_summary.md` for reviewer/validation/fix-status visibility
   - enforces active run guard (prevents accidentally running superseded/closed historical runs unless explicitly allowed)
7. Validate reviewer outputs with `scripts/validate_cycle_outputs.py --run-id <run_id> --cycle-id <cycle_id>` (auto-called by `run_review_cycle.py` unless skipped).
8. If validator returns `retry_required`, rerun `scripts/run_review_cycle.py` for failed reviewers and repeat step 7.
9. If validator returns `awaiting_user_confirmation`, stop loop, ask the user to confirm/grant required external permissions/auth, and wait for user confirmation before continuing.
10. Collect first-pass outputs before sharing peer reports (independence first).
11. Merge findings into one matrix by severity and evidence (`file:line`, failing behavior, risk).
12. Run consensus (see `references/consensus_prompt.md`): merge and *synthesize* findings — surface issues that emerge only from combining reviewers — and treat every finding as a nomination, re-grounding each blocking finding in the code before it enters the fix queue. Escalate to a second adjudicator only for claims you cannot cheaply verify or contested high-cost fixes; do not run an open debate round, which re-introduces the anchoring the independent first pass removes.
13. Build consensus action items:
   - `must_fix` (only reproducible failures or direct contract/requirement violations)
   - `should_fix_important` (blocking)
   - `should_fix_minor` (non-blocking)
   - `needs_confirmation`
   - `rejected_with_reason`
14. Apply `must_fix` + `should_fix_important` by default; `should_fix_minor` is optional unless user elevates it. Update `fix_log.md` status table.
15. In standard mode (default), rerun steps 6-14 until a full re-review cycle reports no new blocking issues and `fix_log.md` has no unresolved blocking entries.
16. If validator reports `awaiting_user_confirmation` with `force_majeure_confirmed=true`, ask the user whether to enable low-overhead mode.
17. If user confirms low-overhead mode, run one closure cycle and stop when reproducible defects are cleared; keep `needs_confirmation` items logged.
18. If `force_majeure_confirmed=false`, do not enable low-overhead mode; resolve root cause and continue standard mode.

## Loop Safety and Permission Gates

1. Never run unbounded loops; every run must have `max_retries`.
2. Default `max_retries=5` unless user overrides it.
3. If repeated failures suggest force-majeure blockers (transport reliability, execution permissions, import context, or diff context), switch to `awaiting_user_confirmation`.
4. In `awaiting_user_confirmation`, do not continue automatically. Ask user to confirm required external/system actions and wait.
5. If reviewer output says command execution is blocked by sandbox policy (for example, cannot execute `python`), treat it as a force-majeure signal.
6. If full evaluation confirms the agent cannot resolve directly, generate one decision request and pause. Do not repeatedly ask user in every retry cycle.
7. Use `scripts/validate_cycle_outputs.py --force-recheck` only after environment changes when you intentionally want to bypass pending decision state.
8. To intentionally reopen a non-active run, user must explicitly request it and run `scripts/set_run_state.py --state active` (or pass explicit override flags).

## Conditional Low-Overhead Mode

Default is full-quality mode — do not reduce review depth by default, because the whole point is to catch what a single pass misses. Low-overhead mode is allowed only when `retry_guard.json` confirms a force-majeure category (`execution_permissions`, `transport_reliability`, `import_context`, `diff_context`) AND the user explicitly confirms it. In that mode keep scope narrow (touched files first), keep severity strict (`must_fix` needs reproducible evidence or a direct contract violation; blocking = `must_fix` + `should_fix_important` only), and run a single closure cycle after fixes. If force-majeure is not confirmed, stay in full mode to preserve quality.

## Artifact Contract

Always write review artifacts under `_code_reviews_ai/` in the current project root: project-level rules (`project_review_rules.json` / `.md`) plus, per cycle, the reviewer outputs and diagnostics, execution/validation metadata, merged findings, consensus, fix plan + log, re-review, and cycle summary. See `references/storage_layout.md` for the exact tree, file names, and naming rules — the scripts create and maintain these for you.

## Anti-Bias Guardrails

1. Independence first: each reviewer produces an initial report before seeing peers.
2. Evidence required: every issue must include concrete code evidence.
3. No authority shortcut: consensus is evidence-based, not seniority-based.
4. Drift control: unresolved disagreements must be logged with rationale.
5. Reopen discipline: recurrence mapping to historical `issue_id` happens in consensus/orchestrator step, not in independent reviewer pass.

## References

Use:

1. `references/reviewer_prompt.md` for each independent reviewer prompt.
2. `references/consensus_prompt.md` for consensus: synthesis, nomination verification, and convergence.
3. `references/storage_layout.md` for required `_code_reviews_ai` file layout.
4. `scripts/init_review_run.py` to initialize a deterministic run folder.
5. `scripts/run_review_cycle.py` to orchestrate real parallel reviewer subprocesses with atomic writes and retry control.
   - key controls: `--blocking-clear-marker`, `--blocking-clear-phrase`, `--strict-marker-clear`, `--blocking-consensus-threshold`, `--blocking-should-fix-tag`, `--inject-fix-log-context`
6. `scripts/set_run_state.py` to mark run states (`active/paused/closed/superseded`) and intentionally reopen a run when user requests.
7. `scripts/validate_cycle_outputs.py` to enforce retry bounds and permission-gate stops.
8. `scripts/preflight_check.py` to verify environment readiness.
9. `references/setup_cross_platform.md` for Windows/macOS/Linux/WSL setup and remediation.
10. `scripts/manage_project_rules.py` to propose/approve/revise project-level review rules.
