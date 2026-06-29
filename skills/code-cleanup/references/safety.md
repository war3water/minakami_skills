# Safety — Risk Tiers, Hard Rules, Verification

The behavior-preservation contract for every change, in single-pass and campaign mode. Loaded whenever the
skill executes a change. Self-contained — apply without a second-hop load.

## Contents

1. Risk-tier model
2. Hard safety rules (always)
3. Agent self-audit (anti-indirection-bias)
4. Macro vs micro
5. Working-tree hygiene
6. Verification tiers

---

## 1. Risk-tier model

Every change is one of three tiers; the tier sets whether the agent may proceed autonomously.

| Tier | Examples | Policy |
|---|---|---|
| **Low (reversible)** | inline a verified pass-through wrapper, move an isolated file with all callers updated (directness-first), rename an internal-only symbol via LSP, documentation edits, add static-analysis config | proceed; verify each (revert-on-red) |
| **Medium** | split a mixed-responsibility file, merge drifted duplicates, simplify deep nesting, reorganize a non-core package | proceed; in campaign mode up to the round's file budget, then summarize and continue |
| **High (irreversible / outward-facing)** | move core runtime files; delete files; rename/change a public function, class, CLI, config format, schema, or file format; change a public import path; remove a compatibility layer; change behavior-defining tests; refactor a dynamic / plugin / registry system | **always checkpoint with the user — never auto** |

"Reversible with a `git checkout`" is the rough test for low; "changes a contract a consumer can observe"
pushes it to high. When unsure of the tier, treat as the higher one.

---

## 2. Hard safety rules (always)

Non-negotiable; they block the dominant agentic-refactor failure modes (see `glossary.md` bibliography:
arXiv 2511.04824, 2411.04444).

### Revert on red — never fix-forward

If a refactor edit makes the build / typecheck or a **behavioral** test go red (a real regression — see *Tests
are signals* below for the behavioral-vs-structure-coupled distinction):

1. **Revert ONLY the files this session edited** — `git restore -- <paths>` listing exact paths. **Never**
   `git restore .`, `git restore --staged .`, or `git checkout -- .` — those wipe unrelated uncommitted
   user changes. If unsure which files are yours, `git stash push --keep-index --include-untracked` stashes
   everything recoverably.
2. Record the broken thing as a **prerequisite** — a smaller slice that must land first (Mikado).
3. Try the smaller slice. Never push through red by writing more refactor on top.

### Tests are signals, not proof of correct structure

A green suite proves *behavior didn't change* — it says nothing about whether the structure is *right*. Don't
conflate behavior-preserving (good) with structure-preserving (often the redundancy you are here to remove).
Risk- and churn-aversion that keeps stale structure alive is the main thing that blocks real reorganization.

- **The real acceptance oracle is end-to-end behavior** — the project's golden / e2e cases, or a full real
  run, dual-audited where possible. A green *unit* suite is necessary, not sufficient. Where no golden cases
  exist, characterize behavior at the public boundary before the reorg and treat that as the bar.
- **Classify every red test:**
  - **Behavioral regression** — asserts on input→output behavior, and the behavior actually changed → a real
    blocker; apply revert-on-red.
  - **Stale structure-coupling** — asserts on internals (a wrapper exists, a mock was called N times, a
    private path / registry is hit), not on behavior; it breaks *because* you correctly removed that
    structure → update / repoint / remove the test and document why. Do **not** revert the improvement, and
    do **not** preserve the dead structure to keep it green.
- **Never preserve a redundant wrapper / shim / registry solely to keep a stale test green or to avoid
  call-site churn.** Prove it is load-bearing — it adds validation, transformation, orchestration over
  multiple real ops, dependency isolation, a stable public boundary, or context-bearing logging, or has real
  external consumers — or remove it.
- **Guardrail:** when unsure whether a failure is behavioral or structural, treat it as **behavioral** (a
  blocker) and ask the user — never rationalize a real regression as "stale coupling." Build / typecheck red
  is always a blocker. Changing or removing a behavior-defining test is a high-tier action (§1).

### Change-boundary hygiene

- **One logical change per boundary.** A refactor boundary contains only refactoring — no feature change,
  no bug fix, no behavior change. (Tangling refactor with feature changes is the dominant agentic-refactor
  failure mode; this blocks it — evidence in `glossary.md` bibliography.)
- **Commit only when the user asks.** Frame work as logical change-units; do not create commits (or commit
  prefixes like `refactor:` / `chore(cleanup):`) unless the user has asked for commits. When committing is
  requested, one logical change per commit.

### RefactoringMirror — plan with the model, execute with deterministic engines

When a deterministic refactor exists (IDE Inline/Rename/Move/Extract; `ruff` autofix; `rope`; LSP code
actions), **prefer it over a hand-written diff.** The model decides *what* and *why*; the engine produces
the *diff*. (Raw LLM refactors sometimes change behavior or break syntax; deterministic engines do not —
evidence in `glossary.md` bibliography.)

---

## 3. Agent self-audit (anti-indirection-bias)

AI agents systematically **over-produce indirection** — wrappers, factories, managers, "for-flexibility"
layers nobody asked for — which is the very disease this skill treats. Guard against introducing it:

- **Apply the "every layer must earn its existence" gate (`techniques.md` §2) to your OWN edits**, not only
  to the existing code. A new layer with no test seam / plugin point / layer boundary / real reuse is net harm.
- **Do not create new `manager`, `handler`, `processor`, `utils`, or `common` layers** without a specific,
  documented responsibility.
- **No permanent compatibility layers.** Fallbacks (wrappers, facades, shims, tombstones) are bounded
  exceptions tracked to removal (`techniques.md` §4). A left-behind "temporary" wrapper is a *new* permanent
  hop — a refactor failure, not a safe outcome. Prefer directness-first (atomic caller update, no fallback).
- **Do not mix algorithm changes with structure refactoring** — separate boundaries, separate approval.
- **Net indirection must not increase.** A touched feature's meaningful-hop count after ≤ before (SKILL.md
  success criteria).

---

## 4. Macro vs micro

- **Micro** — one catalog entry (Inline, Rename, Move, Extract). May complete end-to-end if all rules pass.
- **Macro** — directory regroup, public-API change, splitting a god-module, replacing a subsystem. **Must**
  proceed as a **Mikado graph** (goal → prerequisites → sub-prerequisites), **one leaf at a time**, never a
  big-bang reorganization. AI agents tend to produce no net improvement on macro refactors precisely because
  they attempt macro work the way they attempt micro; the split is the mitigation. Recommend **plan-first**
  for macro work: produce
  and get agreement on the staged plan before editing.

---

## 5. Working-tree hygiene

Before a refactor stage, **inspect** `git status` and note which files are yours, so revert-on-red is
unambiguous. Do **not** demand a pristine tree — agents routinely work in dirty worktrees; agent-owned-files-
only rollback (rule 2.1) handles uncommitted user changes. If the tree is heavily mixed and rollback would
be ambiguous, offer to stash; don't force it.

---

## 6. Verification tiers

After each change, run available checks in this order; report clearly if a documented command is missing —
do not silently skip.

1. **Project-native** — whatever `Makefile` / `pyproject.toml` / `package.json` / `Cargo.toml` /
   `build.gradle` defines under `test`, `lint`, `typecheck`. These reflect the team's own contract.
2. **Language built-ins** — `python -m compileall`, `tsc --noEmit`, `go vet`, `cargo check`. Fast smoke checks.
3. **Optional external analyzers** — `vulture` / `pydeps` / `knip` / `madge` etc. Suggest only after the
   cheaper tiers; never require them.

Per-ecosystem command catalog is in `architecture.md`. For unlisted ecosystems, consult the project manifest
and the language's idiomatic commands; ask the user if conventions are unfamiliar.
