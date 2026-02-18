---
name: scientific-engineering-standards
description: Enforce scientific and engineering software standards for correctness, reproducibility, and performance-aware architecture. Use when implementing or refactoring numerical algorithms, simulations, optimization routines, geometry/physics logic, compute-intensive pipelines, or conducting technical review for mathematically sensitive code.
license: Complete terms in LICENSE.txt
metadata:
  short-description: Scientific rigor rules for numerical and simulation-heavy code
---

# Scientific Engineering Standards

Use this skill to minimize numerical risk and make technical decisions auditable.

For deeper guidance, load references only when needed:
- `references/numerical-stability-checklist.md`
- `references/reproducibility-playbook.md`
- `references/performance-evaluation-protocol.md`

## Operating Priorities

1. Correctness and physical validity
2. Reproducibility and debuggability
3. Maintainability and clarity
4. Performance

If priorities conflict, choose the higher priority unless explicit requirements override.

## Rule Semantics

- `MUST`: mandatory. Deviation requires explicit user-approved rationale.
- `SHOULD`: default recommendation. Deviate only with documented tradeoff.
- `MAY`: optional enhancement.

## Enforcement Standard

Require these in review for logic-changing work:
- Explicit assumptions, constraints, and invariants.
- Testable acceptance criteria.
- Verification evidence (tests, checks, and benchmark data when performance is claimed).
- Clear residual risks.

Reject changes that cannot explain numerical safety, reproducibility behavior, or correctness boundaries.

## Required Practices

1. Numerical correctness (`MUST`)
- Use tolerance-based comparisons for floating-point decisions.
- Specify tolerance rationale for both relative and absolute terms in critical checks.
- Guard domain and singularity risks (`divide-by-near-zero`, invalid `sqrt/log/arccos`, singular solves).
- Handle `NaN` and `Inf` explicitly.

2. Units and coordinate conventions (`MUST`)
- Make units explicit in names/types/docs.
- Declare coordinate frame and angle convention.
- Convert units at boundaries and keep one canonical internal convention.

3. Reproducibility (`MUST`)
- Provide seed control for stochastic behavior.
- Capture environment/version context for reproducible runs.
- State deterministic-mode tradeoffs when determinism impacts performance.

4. Architecture and contracts (`MUST`)
- Keep compute kernel logic separated from transport/UI/storage concerns.
- Keep a single source of truth for authoritative state transitions.
- Define interface contracts with machine-checkable schemas where possible.

5. Typing and docs (`MUST`)
- Type all public interfaces.
- Describe array/tensor shape semantics and dtype expectations.
- Document algorithm assumptions, failure modes, and expected complexity.

6. Validation and invariants (`MUST`)
- Validate domain constraints at boundaries (e.g., physical quantities, dimensions).
- Add invariant checks for conservation, bounds, or monotonicity when applicable.
- Include edge-case handling for degenerate geometry and empty inputs.

7. Performance engineering (`SHOULD`)
- Profile first; optimize measured bottlenecks only.
- Prefer algorithmic complexity improvements before micro-optimization.
- Justify vectorization/JIT/GPU choices with benchmark evidence.

8. Optimization claims (`MUST`)
- Any optimization claim must include before/after benchmark results with method and environment notes.

## Think-Before-Code Protocol

Mandatory for new algorithms and logic-changing refactors.

1. Define constraints
- Accuracy/error tolerance targets.
- Throughput/latency/memory constraints.
- Determinism and reproducibility requirements.

2. Propose the approach
- Algorithm choice and alternatives considered.
- Complexity expectations.
- Key assumptions and known failure modes.

3. Define verification
- Unit tests, invariants, and edge cases.
- Acceptance thresholds for correctness and performance.

4. Implement with guardrails
- Validate inputs.
- Keep contracts explicit.
- Isolate core kernel logic.

5. Verify and report
- Provide evidence, tradeoffs, and residual risks.

Exemption: no-logic-change refactors (rename, move, formatting, comments).

## Verification & Acceptance

Minimum acceptance checks:
- Correctness: tolerance-aware assertions and edge-case coverage.
- Robustness: domain/singularity checks, `NaN/Inf` handling, invariant checks.
- Reproducibility: seed behavior and environment/version capture for reproducible runs.
- Performance (if claimed): before/after benchmark table and method disclosure.

## Failure Modes to Guard

- Equality checks on floats without tolerances.
- Hidden unit/frame mismatches.
- Unseeded randomness in tests or experiments.
- Backend/frontend duplicated authoritative logic.
- Performance claims without measurements.
- Optimization that reduces auditability without justification.

## Deliverable Template

When applying this skill, structure output as:

1. Assumptions and constraints
2. Proposed approach and alternatives
3. Numerical risk analysis
4. Verification plan and acceptance criteria
5. Performance evidence (if optimization is involved)
6. Residual risks and follow-ups

### Template: Algorithm Design Proposal

```text
Goal:
Constraints:
Chosen algorithm:
Alternatives considered:
Complexity target:
Failure modes:
Acceptance criteria:
```

### Template: Numerical Risk Checklist

```text
- Tolerances defined (relative + absolute):
- Domain/singularity guards:
- NaN/Inf handling:
- Units/frames documented:
- Invariants asserted:
```

### Template: Benchmark Report Mini-Format

```text
Scenario:
Hardware/runtime:
Dataset/input shape:
Baseline metrics:
Candidate metrics:
Delta and confidence:
Decision:
```
