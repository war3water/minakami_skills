# Performance Evaluation Protocol

Use this protocol before adopting optimization changes.

## 1) Measure Baseline

- Profile current implementation with representative workloads.
- Capture wall time, memory, and throughput/latency as relevant.

## 2) Define Candidate

- State optimization hypothesis.
- Specify expected improvement and acceptable regression limits.

## 3) Execute Benchmarks

- Keep dataset/input shape constant.
- Run enough repetitions to reduce noise.
- Report environment (hardware/runtime/dependencies).

## 4) Compare Results

Report:
- Baseline vs candidate metrics
- Absolute and percentage deltas
- Any quality/correctness impact

## 5) Decision Rule

Adopt only if:
- Correctness is preserved,
- Improvement is meaningful for target workload,
- Added complexity is justified and maintainable.

## 6) Record and Rollback

- Save benchmark evidence with methodology.
- Keep a rollback path if production behavior degrades.
