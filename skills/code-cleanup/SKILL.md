---
name: code-cleanup
description: Refactors a messy, hard-to-maintain project so a maintainer can read, debug, and modify it quickly. Use when a codebase has multi-hop indirection (a simple feature buried under wrappers, factories, registries, or deep nesting), unclear module boundaries, dead/orphaned code, duplicated logic, circular imports, misplaced files, spaghetti dependencies, stale or redundant files and tests, technical debt, or onboarding-hostile structure. Triggers on phrases like "my code is messy", "pay down tech debt", "clean up", "reorganize", "modularize", "untangle the repo", "reduce nesting", "remove dead code", "too many layers", "improve maintainability", or "make debugging easier". Produces a project structure map, a maintainer-oriented call graph with a hop audit, a ranked refactor plan, and the execution — staged behavior-preserving changes or a scoped rewrite, chosen from the evidence with the user's agreement on scope.
---

# Code Cleanup

Make a project easy for a maintainer to read, debug, and modify, while preserving behavior. The skill removes
the maintainability problems that raise read-and-understand cost, in **two equally-important families** (a
real cleanup does both):

- **Indirection that hurts tracing** — **multi-hop code** (inter-file scattering or intra-file deep
  nesting) and **entry/wiring mixed into implementation** (so you can't find where execution begins).
  Fixed by flattening unjustified hops and the composition-root pattern (wiring at the edges, pure core); the
  call graph tags every node entry / wiring / domain / I/O to surface it.
- **Dead weight and redundancy** — **dead / stale / orphaned code and files**, **duplicated or drifted
  logic**, and **redundant or stale tests**. Found by reachability + data-flow sweeps and cross-entry
  duplicate detection; removed via the Safe-Deletion Playbook (verified before removal, never on first
  suspicion).

This SKILL.md is the **dispatcher**: it selects the mode, tells the agent exactly which reference files to
load for each stage, and owns the principles and success criteria. The detailed procedures live in
[references/](references/) and load on demand. The references assume a competent model — they do not teach
how to *find* problems; they enforce the judgment gates, edit-safety rules, and consistent deliverables
that are easy to get wrong even when detection is easy.

> **Trust the invoking context.** The user's message usually states the project, the pain, and the appetite.
> Accept those and proceed; ask only for what you genuinely cannot infer. Don't run a mechanical question
> round when intent is clear.

---

## Intake — pick the mode

| Mode | When | Then |
|---|---|---|
| **Single-pass** | a targeted, scoped request ("inline this wrapper", "split `utils.py`", "this one feature is hard to trace") | run the relevant stage(s) once, report, stop |
| **Campaign** | deep / exhaustive / whole-repo cleanup, a multi-objective brief, or "keep going" | establish a ledger + scope contract, then run the bounded loop — load [references/campaign-mode.md](references/campaign-mode.md) |
| **Small project** (< ~30 source files) | the whole tree fits in one head | still do a full inventory first, then work the highest-value items; skip the heavy staging. Never one-change-at-a-time without a survey. |

Recommend **plan-first** for anything macro: produce and agree the staged plan before editing, so the agent
doesn't see "refactor" and start moving many files at once.

---

## Loading manifest — what to load when (this solves the skill's own multi-hop)

The agent learns the **complete** file set for a stage here and loads it in one batch. It never discovers a
needed file by reading another file mid-procedure. Every reference is **one hop** from this file.

| Stage / trigger | Load (together, one hop) |
|---|---|
| Intake / mode selection | this file |
| Analysis-only ask (map / call graph / hop audit, no edits) | [references/discovery.md](references/discovery.md) **only — stop there**; a competent model needs no more to analyze |
| Diagnosis (classify, dependencies, name problems) | [references/diagnosis.md](references/diagnosis.md) + [references/techniques.md](references/techniques.md) |
| Execution (target proposal, staged plan, patterns) | [references/execution.md](references/execution.md) + [references/techniques.md](references/techniques.md) + [references/safety.md](references/safety.md) |
| Campaign mode | [references/campaign-mode.md](references/campaign-mode.md) + [references/safety.md](references/safety.md) |
| Any deletion / dead-weight audit | [references/techniques.md](references/techniques.md) + [references/safety.md](references/safety.md) |
| Optional enrichment (leaf — only if needed) | [references/glossary.md](references/glossary.md), [scripts/](scripts/), [assets/](assets/) |

**Rule:** each reference file is **self-sufficient to execute its own procedure** — it may *cite* a companion
(already loaded via this manifest) or an optional leaf, but it must never say "to proceed, now go read X."
The execution spine is one hop; only optional enrichment may be deeper, and it is marked optional.

Output templates live in [assets/](assets/) — copy from them, don't regenerate from memory:
`architecture_report.md` (discovery), `refactor_plan.md` (plan), `migration_stage_report.md` (per stage),
`cleanup_ledger.md` (campaign). These are **blank, read-only skeletons with no project data.** Write every
*filled* report, plan, or ledger into a **skill-named agent-work directory in the target project** — default
`.agent_works/code-cleanup/` (namespacing by skill name avoids collisions with other agents sharing
`.agent_works/`; fall back to a user-named path if it can't be created or conflicts). The live ledger is a
tracked `.agent_works/code-cleanup/CLEANUP_LEDGER.md` (repo root only if the user wants it highly visible).
**Do not** drop these
into the project's source tree, core code, or its existing `docs/` structure — that pollutes or breaks the
project's own layout. And **never write project data, logs, or filled outputs back into this skill folder** —
the skill is immutable at runtime; contaminating it would pollute every future run on every other project.

---

## Core principles

1. **Primary outputs first.** Discovery produces the two artifacts a maintainer reads first — a project
   structure map and a call graph with a per-hop audit. They guide every later decision.
2. **Diagnose before refactoring.** Read the map and call graph before moving, deleting, or rewriting.
3. **Every layer must earn its existence.** Default to flat composition. A hop (function, class, file,
   branch) is kept only if it is a real boundary, adds validation/transformation/orchestration/error
   handling, encapsulates an external dependency, gives a genuine test seam or reuse, or makes the code
   easier to understand than calling directly. Otherwise it's a candidate to inline or merge — judged in
context, not removed on pattern-match. **This gate applies to your own
   edits too** — agents over-produce indirection; don't add a layer the project didn't ask for. Judge it
   **globally, not in isolation** — sweep all public entrypoints for parallel/duplicate entries (two public
   entries → one impl; a registry/factory → one impl), since a hop that looks justified locally can be a 1:1
   duplicate of another entry.
4. **Directness-first; no permanent fallbacks.** When callers are fully enumerable, move code and update all
   callers atomically — land clean, no wrapper. A compatibility layer is a bounded exception (non-enumerable
   consumers only), tracked to removal. A permanent "temporary" wrapper is a new permanent hop — a failure.
5. **Use evidence**, not file names or guesses — imports, call paths, tests, configs, entry points, runtime
   conventions. Static analysis is not complete: dynamic imports, decorators, reflection, and
   framework/plugin paths are invisible to it — verify before acting.
6. **Clear classification, specific names.** One nameable responsibility per module; avoid vague
   `manager` / `handler` / `processor` / `utils` / `common` unless the job is specific and documented.
7. **Local conventions first; smallest move-set that resolves the diagnostic.** Honor the project's and its
   framework's own conventions where a *sensible* convention exists — existing chaos is not a convention.
   When there is none, or the user asks to reconstruct toward a clearer structure, a full evidence-derived
   regroup mirrored on an OSS exemplar (cited) is the right-sized move: "smallest" bounds scope creep, it
   does not cap a reconstruction the diagnostic actually requires.
8. **Risk-tiered safety.** Low (reversible) → proceed; medium → proceed with verification; high
   (irreversible / outward-facing) → checkpoint with the user. Verify after each change; revert-on-red.
9. **Behavior change needs explicit approval.** One logical change per boundary — no tangling refactor with
   features or fixes. Commit only when the user asks.
10. **No style-only churn.** Every change resolves a named diagnostic from the map or call graph.

Full safety contract: [references/safety.md](references/safety.md). The vocabulary for naming problems:
[references/glossary.md](references/glossary.md).

---

## Deletion gates — binding at every stage; these override every other consideration

A deletion target is **approval-tier** if it is any of: an extension point documented anywhere (README,
docs, comments, example configs) even if currently unwired; an outward-facing surface — a compatibility
shim, re-export, or entry point whose consumers may live **outside this repo** ("zero in-tree references"
says nothing about out-of-tree consumers); a registered plugin / stage / handler reachable by configuration;
or a test pinning any of the above.

- Approval-tier deletion requires the user's explicit confirmation **for that item**.
- **No reachable user = no approval.** The default disposition is **keep + flag in the report** with the
  evidence and the question you would have asked. A backup copy, a verbatim restore block, or
  zero-reference evidence is **not a substitute for approval** — it makes the mistake recoverable, not
  authorized.
- Never justify a deletion with this skill's own vocabulary ("permanent temporary wrapper",
  "violates directness-first"). The skill's rules *nominate* candidates; only verification evidence plus
  approval retires one.

Everything below approval-tier (proven data-flow-dead branches, zero-reference private code, exact
duplicates) follows the Safe-Deletion Playbook procedure in
[references/techniques.md](references/techniques.md).

---

## Minimal workflow

1. **Discovery** — language/framework/build/test commands, entry points, conventions; then the structure map
   and the call-graph hop audit (classify each hop KEEP / MERGE / DELETE / RENAME / MOVE / TEST FIRST).
2. **Diagnosis** — classify files, map dependencies, name the maintainability issues (multi-hop, entry-vs-
   implementation mixing, duplication, dead code, …) with per-issue evidence.
3. **Execution** — propose a target (local-first), plan the smallest staged set of moves, execute behavior-
   preservingly with verification — staged refactor or, when the evidence supports it, a scoped rewrite the
   user has agreed to. **If the project has no test suite or goldens, build the behavior net first** —
   capture the output of every documented command *before* the first edit and re-verify against it after.
   Campaign mode runs this as a continuous ledger-driven loop.

Deep rewrite is the right answer when the structure is unnecessary and
redundant (indirection that doesn't earn its keep, competing implementations, boundaries that no longer
match the domain); staged is the trap there.

---

## Success criteria

The refactor is successful only if:

1. The project has a clear structure map and documented entry points.
2. Major call paths are understandable; entry/wiring is separated from domain logic, so a maintainer can see
   where execution begins and debugging requires less cross-file jumping.
3. **Every touched feature's meaningful-hop count after ≤ before** (multi-hop reduced, not relocated).
4. **No orphaned compatibility layers remain** (no permanent "temporary" wrappers).
5. Module responsibilities and names are clear.
6. Dead / stale / orphaned code and files, duplicated logic, and redundant tests were removed — each verified
   before removal (never on first suspicion).
7. Behavior is preserved and verified against the project's end-to-end / golden cases — a green unit suite is
   a signal, not proof of correct structure; stale, structure-coupled tests were updated or removed with a
   reason, never used to preserve redundant structure.
8. Future maintainers can quickly find where to add or fix functionality.
