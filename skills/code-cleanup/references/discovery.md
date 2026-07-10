# Discovery — Map, Call Graph, Hop Audit

Understand the project and trace how features actually run, before changing anything. Produces the two
artifacts a maintainer reads first — a **project structure map** and a **maintainer-oriented call graph with
a hop audit**. Loaded at the discovery stage. Self-contained.

---

## First-impression test (run first)

Read the project as an engineer who just walked in. Answer four questions out loud:

1. **Entry point** — Can you find where execution begins quickly, or are you hunting through bootstrap and
   conditional init? **Is the wiring-up separated from the real work?**
2. **Trace** — Pick one user-visible feature. Can you follow it end-to-end without losing the thread across
   file jumps?
3. **Vocabulary** — Do module names mean the same thing throughout? Does `core/` describe one thing or three?
4. **One way** — For each responsibility (config, HTTP, logging, storage), is there ONE implementation or
   competing ones?

A "no" is a refactor target. Don't invent other targets.

---

## Safety preparation

Identify, without modifying code: project language and framework; package manager and build system; test
command; lint/typecheck command; runtime entry points; CLI commands; server startup files; config files;
environment files; generated files; framework-convention files; plugin/registry mechanisms.

Flag areas needing caution — dynamic imports, generated code, plugin registries, reflection-driven dispatch.

---

## Artifact 1 — Project structure map

A grouped tree with a one-line purpose per directory and major file. At minimum it answers the four
questions a new maintainer asks within their first hour:

- **Where does the program start** — entry points and bootstrap path.
- **Where does each user-facing feature live** — the feature → directory mapping.
- **What does each top-level directory mean here** — core domain vs config vs integration vs tooling vs
  tests (naming alone is rarely enough).
- **What is auto-loaded by framework conventions** that won't show in an import graph — Django apps, pytest
  plugins, FastAPI routers, gRPC registration, decorator-based command registration.

Include build / test / lint / dev commands.

---

## Artifact 2 — Call graph + hop audit

For each major user-facing feature, trace the call path from entry to the real logic, then **classify every
hop**. This is the core diagnostic for multi-hop code (`techniques.md`).

```text
Feature: upload a file

Current call path (a hop = one node on the path; meaningful = nodes that pass the `techniques.md` §1 gate):
  cli.py:main()                             KEEP   (entry / composition)
    -> app.py:run()                         MERGE  (thin bootstrap — folds into the entry)
    -> controller.py:handle()               MERGE  (overlaps service.execute)
    -> dispatcher.py:dispatch()             MERGE  (forwards only)
    -> service_factory.py:get_service()     DELETE (one service exists)
    -> service.py:execute()                 KEEP   (orchestration + validation)
    -> storage.py:put_object()              KEEP   (external boundary)
Hop count: 7 (meaningful: 3)

Suggested target:
  cli.py:main() -> service.execute() -> storage.py:put_object()
Expected hops: 3
```

Classify each hop:

```text
KEEP       meaningful boundary (earns its existence — techniques.md §1)
MERGE      thin wrapper / overlapping responsibility
DELETE     unused / dead layer
RENAME     vague responsibility (manager/handler/utils with no specific job)
MOVE       wrong module / folder location
TEST FIRST risky behavior with no coverage — characterize before touching
```

**Justification gate** (per `techniques.md` §1): every hop must be a testing seam, a plugin/extension point,
a layer boundary a checker enforces, or genuine reuse. A hop that fails the gate is shallow indirection — a
`MERGE`/`DELETE` candidate for diagnosis. Record actual vs meaningful hop count as a **measurement, not a
target** — the right number is whatever the feature's real boundaries, seams, and reuse require
(`techniques.md` §2). Tag each node
**entry / wiring / domain / I/O** so "business logic in the entry layer" or "wiring scattered through domain
code" surfaces as a finding.

**Sweep every public entrypoint, not only the user-named area.** Redundant multi-hop most often hides as
*cross-entry duplication* you cannot see from one feature: two public entries delegating to the same impl, or a
registry / factory resolving to a single effective impl on the hot path. A hop that passes the justification
gate locally can still be globally redundant — for each, also ask "does another public entry already do this?"
(`techniques.md` §5). Produce a before/after call-path per candidate (format above).

Also note dependency signals for `diagnosis.md`'s dependency analysis (fan-in/out, cycles, cross-domain
imports, deep chains, mixed responsibilities), and flag if static call-graph accuracy is uncertain.

These artifacts are standalone deliverables — present them, or write them to the agent-work directory (per
SKILL.md).

---

## Prioritization — structure first, git only orders

Problems are found by **reading the repo, not git logs.** Churn / `git log` answers "where has change
concentrated?" — not "where are the design problems?" Inherent problems are often churn-invisible: a
god-module nobody dares touch, dead code in cold corners, stable-but-wrong boundaries.

- **Discovery is git-independent and whole-tree** — the map, the call-graph hop audit, the reachability /
  data-flow sweep (`techniques.md` §7), and the design checks find the problems.
- **Prioritization uses churn as one input, never a gate.** `scripts/hotspots.py` (churn × LoC) *orders*
  already-found problems so limited effort hits the highest-pain ones first. Churn never filters a cold-code
  problem out of the worklist. (Tornhill/CodeScene: 2–3% of files attract 11–16% of commits.)
- **History edge cases never degrade discovery.** Fresh import, squashed history, shallow clone, vendored
  subtree, or a monorepo path may have little `git log`; structure discovery runs unchanged and orders by
  LoC × complexity × fan-in. On a very long history, time-box the churn window (e.g. 365 days).

For an **exhaustive dead-weight audit**, waive churn ordering entirely and sweep the whole tree
(`techniques.md` §7).
