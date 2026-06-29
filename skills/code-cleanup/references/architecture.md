# Architecture — Exemplars, Tools, Verification Commands

Reference material for proposing a target layout, picking analyzers, and running checks. Loaded with
`execution.md` when proposing a target tree, and consulted for verification commands. Optional enrichment —
not required to execute the core procedure.

---

## Structural exemplars (fallback, after local conventions)

**Local conventions and the project's framework docs come first** (`execution.md`, target proposal). Use an exemplar
only when the project has no clear convention, and cite which one you mirror and why. Do not invent novel
layouts; do not override a sensible local convention.

| Project | Pattern to copy |
|---|---|
| Kubernetes (Go) | `cmd/<binary>/` entry points, `pkg/` importable library code, `internal/` non-exported. One binary per `cmd` dir. |
| Django (Py) | `apps/<app>/{models,views,urls,services}.py` — flat per-app, predictable, no nested helper trees. |
| FastAPI (Py) | single canonical public import surface; runnable examples in `docs/`. |
| React (TS) | monorepo `packages/<scope>/` with explicit public exports via each `index.ts`. |
| Rust + Cargo | `crate/src/{lib,main}.rs` + `tests/`; trait-over-inheritance; workspaces for multi-crate. |
| Bazel | one build target per directory; `BUILD` files name dependencies explicitly. |

Authoritative references: *Software Engineering at Google* (<https://abseil.io/resources/swe-book>), Google
Engineering Practices (<https://google.github.io/eng-practices/>), Google Style Guides
(<https://google.github.io/styleguide/>). For call-path depth calibration, read source from FastAPI /
requests / Pydantic / tokio (shallow composition) and Django / grpc-go / Kubernetes / Abseil
(framework-required depth) — there is no universal "right depth."

---

## Recommended tools (pick per language; don't install everything)

For any ecosystem, the IDE language-server "Find References" + `git grep` / `ripgrep` cover most analysis
needs without setup cost.

- **Python** — `ruff` (lint, unused imports); `pydeps` (import graph); `import-linter` (boundary contracts);
  `vulture` (dead code, use `--min-confidence 80` + allowlist); `pyan3` (rough call graph); `CodeQL`.
- **JS/TS** — `eslint`; `tsc --noEmit`; `madge` (dep graph, cycles); `dependency-cruiser` (boundary rules);
  `knip` (unused files/exports/deps, preferred over maintenance-mode `ts-prune`); `depcheck`.
- **Go** — `go vet`; `staticcheck`; `golangci-lint`.
- **Rust** — `cargo clippy`; `cargo udeps` (nightly) / `cargo machete` (stable) for unused deps.
- **JVM** — `ArchUnit` (rules as tests); `Detekt` (Kotlin) / `PMD` / `SpotBugs` (Java); `jdeps` / `jdeprscan`.
- **General** — `tree`, `ripgrep`, `git grep`, `cloc`, `CodeQL`, `Sourcegraph`, IDE "Find References".

---

## Verification commands (catalog)

Always prefer project-native commands (tier 1, `safety.md` §6) if they exist.

```bash
# Python
python -m pytest ; ruff check . ; mypy . ; python -m compileall .
# JavaScript / TypeScript
npm test ; npm run lint ; npm run typecheck ; npm run build
# Go
go test ./... ; go vet ./...
# Rust
cargo test ; cargo clippy ; cargo build
# Java / Kotlin (Gradle)
./gradlew test ; ./gradlew build
# Java / Kotlin (Maven)
mvn test ; mvn verify
```

For unlisted ecosystems (Haskell, Elixir, Clojure, C/C++, Swift, KMP, Zig, Nim, Crystal, Erlang, OCaml, F#,
Scala, Ruby, PHP, …): consult the project manifest first, then the language's idiomatic test/lint/typecheck
commands; ask the user if conventions are unfamiliar.
