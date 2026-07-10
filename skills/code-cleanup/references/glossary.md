# Glossary & Bibliography

Optional enrichment — precise vocabulary for the diagnosis, plus the evidence behind the skill's rules. Not
required to execute any procedure.

---

## Problem-category glossary

Each term is a recognized diagnosis with a remediation path, not a generic complaint.

| Term | Meaning | Typical remediation |
|---|---|---|
| **Multi-hop code** | Umbrella for indirection that hurts tracing: a simple feature is reachable only after layers that add no clear meaning — inter-file (scattered call chain) or intra-file (deep nesting / forwarding, catalogued separately as **Deep nesting**). | `techniques.md`: every layer earns its existence; directness-first. |
| **Architectural erosion** | Implemented architecture has drifted from intended; boundaries leak. | Re-establish boundaries via import-linter / dependency-cruiser; enforce in CI. |
| **Unclear module boundaries** | Module names no longer describe contents; responsibilities overlap. | Match a layout (local-first); move files in low-risk batches. |
| **Poor code navigability** | A maintainer can't quickly find where a feature lives. | Map + call graph; flatten unjustified indirection. |
| **High cognitive load** | Reading one feature requires holding many unrelated concepts. | Inline shallow wrappers; split mixed-responsibility files. |
| **Poor change locality** | A small change requires editing many files. | Find the missing abstraction / misplaced responsibility; consolidate. |
| **Spaghetti dependencies** | Modules import each other across unrelated domains. | Break cycles via Branch by Abstraction; add boundary rules. |
| **Deep nesting** | Control-flow nesting in one function, or call-graph nesting across files. | Early returns (intra-file); inline wrappers (cross-file). |
| **Hidden side effects** | Calls mutate state or do I/O not obvious from name/signature. | Rename to surface; isolate; document at the call site. |
| **Entry-vs-implementation mixing** | Business logic in the entry/wiring layer, or wiring scattered through domain code. | Composition root — wiring at the edges, pure core. |
| **Dead-code candidates** | Code that appears unused. *Candidate*, not confirmed. | Safe-Deletion Playbook: tombstone, soak, verify, delete. |
| **Orphaned files** | Not imported by anything traceable statically; may be loaded dynamically. | Same playbook as dead-code. |
| **Duplicate logic** | Same operation in multiple places, often drifted. | Consolidate to one canonical impl (rule of three for general logic; parallel *public entries* consolidate at two — `techniques.md` §5). |
| **Circular dependencies** | A imports B, B imports A — often a missing shared abstraction. | Pull the shared concept up, or invert with an interface. |
| **Unfinished split (re-export back-edge)** | A god-module split left the parent re-exporting its own shards, or shards importing shared helpers back from the parent — a cycle hidden by bottom-imports / `# noqa: E402` / "acyclic either order" comments. | Sink shared helpers into a leaf (cycle → DAG); promote private shards to a subpackage with a facade `__init__` (`techniques.md` §5). |
| **Weak ownership boundaries** | Many features write the same module; nobody owns it. | Split by feature, or designate an owner. |
| **Framework-convention ambiguity** | Auto-loaded files that don't follow the framework's documented conventions. | Adopt the framework's idiomatic structure; cite which. |
| **Onboarding-hostile structure** | A new maintainer can't find the entry point or trace a feature in the first session. | Map + call graph as documentation; flatten obvious wrappers. |
| **Shotgun surgery risk** | A change requires edits across many files; blast radius is unpredictable. | Find the missing abstraction; consolidate; characterize first. |

---

## Bibliography

- Fowler, *Refactoring* (2nd ed.) — <https://refactoring.com/catalog/> ; *Opportunistic Refactoring*,
  *Strangler Fig*, *Branch by Abstraction* (martinfowler.com/bliki).
- Feathers, *Working Effectively with Legacy Code* — seams, characterization tests.
- Ousterhout, *A Philosophy of Software Design* — deep modules, shallow-wrapper smell.
- Ellnestam & Brolund, *The Mikado Method* — <https://mikadomethod.wordpress.com/>.
- Tornhill, *Software Design X-Rays* / CodeScene hotspot methodology.
- Lemaire, *Refactoring at Scale* — campaign discipline, dark/light cutover, acceptable end state.
- *Software Engineering at Google* — <https://abseil.io/resources/swe-book>.
- Romano et al., "A Multi-Study Investigation into Dead Code" (IEEE TSE 2018).
- "Agentic Refactoring: An Empirical Study" (arXiv 2511.04824) — 53.9% of agentic refactors tangle with
  feature changes; ~median 0 smell reduction.
- "LLMs in Automated Software Refactoring" + RefactoringMirror (arXiv 2411.04444) — ~7.4% of raw LLM
  refactors change behavior or break syntax; deterministic re-application eliminates them.
- scheb/tombstone — runtime dead-code evidence pattern — <https://github.com/scheb/tombstone>.
