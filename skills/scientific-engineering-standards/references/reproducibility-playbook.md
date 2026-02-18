# Reproducibility Playbook

Use this playbook for experiments, simulations, and stochastic logic.

## Seed Management

- Expose seed as an explicit input.
- Seed every RNG source in scope.
- Record seed values in outputs/logs for reproducibility.

## Environment Capture

Record at minimum:
- Language/runtime version
- Core dependency versions
- OS and architecture
- Hardware acceleration details (CPU/GPU and settings)

## Deterministic Modes

- Prefer deterministic behavior for tests and validation runs.
- If deterministic mode reduces performance, document the tradeoff.
- Keep deterministic and non-deterministic paths behaviorally consistent in API contracts.

## Reproducible Reporting

Each report should include:
- Seed(s)
- Environment summary
- Input dataset/version
- Exact command/config used
- Timestamp
