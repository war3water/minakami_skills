# Phases 0 & 1 — Discovery

This file specifies the discovery phases of the `code-cleanup` workflow. SKILL.md is the entry point and table of contents; read this file when the task enters the discovery stage (mapping the project + tracing call paths).

Cross-references to PATCHES.md are one hop away (per Anthropic's shallow-reference rule). Cross-references to sibling phase files (`diagnosis.md`, `execution.md`) are intentionally absent — workflow ordering is in SKILL.md.

---

> *PATCHES guard:* Before this phase, run [PATCHES.md §1](../PATCHES.md) (Engineer's First-Impression Test) and check [PATCHES.md §8](../PATCHES.md) — for small projects (the order of magnitude where a single maintainer can hold the whole tree in their head), skip Phase 1-6 entirely and use the small-project fast path instead.

## Phase 0: Safety Preparation

Before analysis or refactoring, identify:

1. Project language and framework.
2. Package manager and build system.
3. Test commands.
4. Lint / typecheck commands.
5. Runtime entry points.
6. CLI commands.
7. Server startup files.
8. Config files.
9. Environment files.
10. Generated files.
11. Framework-convention files.
12. Plugin or registry mechanisms.

**Deliverable artifacts** (produced in Phase 1 from this groundwork — these are the two things a maintainer reads first):

- **Project structure map.**
- **Maintainer-oriented call graph.**

Do not modify code in this phase.

---

> *PATCHES guard:* Apply [PATCHES.md §4](../PATCHES.md) (Hotspot Precondition). The map must prioritize hotspot files (churn × complexity); do not enumerate every module equally.

## Phase 1: Project Map & Call Graph

Produce two artifacts a maintainer can scan quickly. Both feed Phases 2-6 and are the deliverables a new maintainer reads first.

### Artifact 1 — Project Structure Map

A grouped tree with a one-line purpose per directory and major file. At minimum the map answers four questions a new maintainer asks within their first hour: **where does the program start** (entry points and bootstrap path), **where does each user-facing feature live** (the feature-to-directory mapping that lets someone find the code for "the feature I need to change"), **what does each top-level directory mean** in this project (core domain vs. configuration vs. integration vs. tooling vs. tests — naming alone is rarely sufficient), and **what is auto-loaded by framework conventions that won't show in import graphs** (Django apps, pytest plugins, FastAPI routers, gRPC service registration, decorator-based command registration). Include the build / test / lint / dev commands and flag areas that require caution — dynamic imports, generated code, plugin registries, reflection-driven dispatch.

### Artifact 2 — Maintainer-Oriented Call Graph

For each major user-facing feature or entry point, a shallow call trace from entry to first meaningful work:

```text
CLI: `myapp upload <file>`
  -> cli.upload_command(args)
    -> services.uploader.upload(file)
      -> integrations.storage.put_object(key, data)
```

**Principle: do not multiply entities beyond necessity.** Every file jump in a call path must justify itself — a testing seam, a plugin / extension point, a layer boundary that enforces dependency direction, or genuine reuse by demonstrably independent callers (see [PATCHES.md §2 Principle 2](../PATCHES.md) and the technique catalog at [§5](../PATCHES.md)). **If no such justification exists, the jump is shallow indirection** and the function it crosses is a candidate for `Inline Function` in Phase 4 (see `diagnosis.md` via SKILL.md).

The goal is the fewest jumps the code's real needs allow. There is **no universal "right depth"** — it varies by domain, framework, and language. Rather than targeting a number, calibrate by studying call paths in well-maintained open-source projects and comparing against the project being refactored:

- **Shallow, mostly-flat composition** is achievable in library and service code without heavy framework conventions — read source from [fastapi/fastapi](https://github.com/fastapi/fastapi), [psf/requests](https://github.com/psf/requests), [pydantic/pydantic](https://github.com/pydantic/pydantic), [tokio-rs/tokio](https://github.com/tokio-rs/tokio).
- **Framework-required depth that remains readable** — read source from [django/django](https://github.com/django/django) (especially `django/core/handlers/`), [grpc/grpc-go](https://github.com/grpc/grpc-go) (interceptor chains), [kubernetes/kubernetes](https://github.com/kubernetes/kubernetes) (controller pattern), [abseil/abseil-cpp](https://github.com/abseil/abseil-cpp).
- **Engineering-practice references** — [Software Engineering at Google](https://abseil.io/resources/swe-book), [Google Engineering Practices](https://google.github.io/eng-practices/), [Google Style Guides](https://google.github.io/styleguide/).

Record the actual call-path depth in the graph as a **diagnostic measurement**, not a target. For any jump that fails the justification gate above, mark it as a Phase 4 inlining candidate. "How few jumps can this feature be implemented in?" beats "How short is this trace?"

Phase 1's outputs are standalone deliverables — present them to the team or commit them as documentation now. Refactoring decisions belong in Phases 2-6 and depend on what the map and call graph reveal. If the findings already justify a deep rewrite (see SKILL.md Purpose criteria), name it explicitly before starting Phase 2.
