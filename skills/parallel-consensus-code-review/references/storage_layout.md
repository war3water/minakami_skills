# Storage Layout

All artifacts from this skill must be written under a project-local `_code_reviews_ai/` folder.

## Required Tree

```text
<project-root>/
  _code_reviews_ai/
    project_review_rules.json
    project_review_rules.md
    <run_id>/
      run_manifest.json
      inputs/
        scope.md
        requirements.md
        diff_range.txt
        review_query.md
        audit_items.md
        changed_files.txt
        context_notes.md
      cycles/
        cycle_01/
          cycle_meta.json
          retry_guard.json
          reviewer_run_summary.json
          validation_exec.json
          decision_request.json
          reviewer_<id>_prompt.md
          reviewer_<id>.md
          reviewer_<id>.stderr.log
          reviewer_<id>.stdout.log
          reviewer_<id>.exec.json
          merged_findings.md
          consensus.md
          fix_plan.md
          fix_log.md
          re_review.md
          cycle_summary.md
```

## Naming Rules

1. `run_id` format: `run_YYYYMMDD_HHMMSS`.
2. Cycle folders use zero-padded indices: `cycle_01`, `cycle_02`, ...
3. Reviewer file naming is dynamic by reviewer id (`reviewer_<id>.md` etc), default ids are `reviewer_01`, `reviewer_02`, `reviewer_03`.
4. `scripts/run_review_cycle.py` writes `reviewer_run_summary.json` and per-reviewer execution metadata `reviewer_<id>.exec.json`.
5. Retry safety state is written to `retry_guard.json` each validation pass.
6. If reviewer subprocess diagnostics are captured, use `reviewer_<id>.stderr.log` / `reviewer_<id>.stdout.log`.
7. `review_cycle.lock` is an ephemeral lock file used to prevent concurrent writers on the same cycle.
8. Reviewer prompt templates can include `{{REVIEW_QUERY}}`, `{{AUDIT_ITEMS}}`, `{{SCOPE_CONTEXT}}`, `{{PROJECT_RULES}}`, and optional `{{FIX_LOG_CONTEXT}}`; `run_review_cycle.py` resolves these from run inputs and project-level rules. Historical fix-log context is blinded by default for first-pass independence unless `--inject-fix-log-context` is explicitly enabled.
9. `_code_reviews_ai/run_registry.json` stores active/superseded run pointers so automation can avoid stale historical runs by default.
10. Reviewer prompt overrides use reviewer-id mapping (`--reviewer-prompt reviewer_id=path`), and reviewer ids must match `reviewer_<letters_digits_underscores>`.
11. Project-level review rules are stored in `_code_reviews_ai/project_review_rules.json`; only `approved` rules are injected to reviewers.
12. `cycle_summary.md` captures run/validation/fix-status/blocking-status tables for user-facing progress visibility.

## Portability Rules

1. Use relative paths from project root; do not hardcode machine-specific absolute paths.
2. If `_code_reviews_ai/` does not exist, create it.
3. Keep all generated review artifacts inside this folder to avoid workspace clutter.
