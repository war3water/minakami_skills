# Numerical Stability Checklist

Use this checklist for numerical kernels and math-heavy logic.

## Inputs and Domains

- Confirm numeric ranges and expected magnitudes.
- Validate domain constraints before critical operations.
- Reject or sanitize invalid values (`NaN`, `Inf`, out-of-range inputs).

## Tolerances

- Define relative tolerance and absolute tolerance for each critical decision.
- State why each tolerance is appropriate for the domain scale.
- Avoid hardcoded "magic epsilon" without rationale.

## Degenerate Cases

- Near-zero denominators
- Zero-length vectors
- Collinear/coplanar geometry
- Empty sets and singleton edge cases
- Singular or ill-conditioned matrices

## Invariants

- Identify required invariants (bounds, conservation, monotonicity, normalization).
- Assert invariants in tests and, where needed, runtime checks.

## Test Expectations

- Include edge and adversarial inputs.
- Use tolerance-aware assertions.
- Include at least one regression fixture for each critical path.
