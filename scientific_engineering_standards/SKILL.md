---
name: scientific_engineering_standards
description: Enforce scientific computing standards, numerical stability, and architectural quality for projects involving complex algorithms, physics simulations, or mathematical modeling. Use when implementing core algorithms, performing architectural refactoring, or making technical design decisions.
---

## When to Use This Skill

**Trigger Conditions:**
- Implementing core computational algorithms (pathfinding, physics engines, numerical solvers)
- Designing system architecture for scientific/engineering applications
- Performing code refactoring that involves mathematical or physical logic
- Making technical stack decisions for performance-critical systems

**Exclusions:**
- Simple UI adjustments
- Documentation-only changes
- Generic code modifications unrelated to business logic

## Core Principles

### 1. Scientific Axioms (Physical & Mathematical Consistency)

#### 1.1 Numerical Stability

**Principle**: Floating-point arithmetic has inherent precision errors. Use tolerance-based comparisons for critical geometric/topological decisions.

**Guidelines:**
- ✅ Use standard library tools (`math.isclose`, `np.allclose`) instead of hardcoded epsilon values
- ✅ Maintain code cleanliness while ensuring numerical robustness

**Singularity & Domain Handling:**
- Be aware of domain safety for mathematical operations
- Handle degenerate cases (e.g., zero vectors) in division, normalization, or inversion
- Ensure system doesn't crash due to mathematical exceptions

#### 1.2 Physical Units & Dimensions

**Explicit Units:**
- Variable names/types must imply units unless there's a global SI convention
- ✅ `time_sec = 10` or `time: Seconds = 10`

**Coordinate Systems:**
- Declare coordinate system standards in docstrings (left/right-handed, local/global)

#### 1.3 Determinism

**Seed Management:**
- Random processes must support seed injection for reproducibility
- Ensure experiments are deterministic when needed

### 2. System Architecture Guidelines

#### 2.1 Separation of Concerns

Focus on logical responsibility purity rather than physical layering:

**Kernel (Computational Core):**
- Design as stateless or pure functions
- **Why**: Pure functions are easier to test, parallelize, and reuse
- Avoid coupling database I/O or business context directly in computational logic

**Domain (Business Layer):**
- Manage state transitions and object lifecycle

**Interface Layer:**
- Handle data serialization and interaction

#### 2.2 Data Flow & Contracts

**Schema Consistency:**
- Interface contracts must be explicit (TypeScript Interfaces, Pydantic Models, OpenAPI/Swagger)
- No need for rigid 1:1 mapping between backend classes and frontend JSON
- Flexibility allowed if both sides agree on the contract

**Visualization Strategy:**
- **Source of Truth**: Backend physics engine is the single source of truth for positions and states
- **Frontend Interpolation**: Frontend may interpolate for visual smoothness
- ⚠️ **Forbidden**: Independent collision logic on frontend that could conflict with backend

### 3. Code Quality Standards

#### 3.1 Type System

**Full Coverage:**
- All functions must have complete type annotations
- For multi-dimensional arrays: use `NDArray[Shape["N,3"], Float]` notation

#### 3.2 Documentation

**Math Context:**
- Core algorithm docstrings must explain underlying mathematical principles
- Example: "Uses SAT (Separating Axis Theorem)"

**Complexity:**
- Must declare time/space complexity (O(N), O(N²), etc.)

#### 3.3 Defensive Programming

**Boundary & Validity:**
- Handle empty sets, infinity, degenerate geometries
- Public APIs must validate input physical meaning (e.g., mass > 0)

### 4. Think Before Code Protocol

Before implementing changes, determine the nature of the change. Follow this protocol when improvements depend on business logic changes (not internal refactoring):

#### 4.1 Protocol Flow

1. **Context Alignment:**
   - Consult project goal files (e.g., AGENTS.md)
   - Confirm algorithm fits specific physical/business constraints
   - Questions to ask: Non-convex geometry allowed? Real-time requirements?

2. **Logic Proof:**
   - Describe solution with pseudocode or formulas
   - For complex algorithms, attempt mathematical correctness proof in comments

3. **Consensus:**
   - Before implementing high-risk algorithms, propose solution and evaluate accuracy vs. performance tradeoffs

#### 4.2 Exemptions

**When this protocol is NOT required:**
- **Refactoring**: Module extraction, variable renaming without logic changes
- **Optimization**: Vectorization improvements (Loop → Matrix) that don't change mathematical results

### 5. Technology Evolution & SOTA Principles

#### 5.1 Dynamic Evolution

- Don't be limited by current tech stack when facing performance bottlenecks or precision issues
- Evaluate new approaches objectively

#### 5.2 SOTA Deep Search Protocol

**Trigger:**
- Solving O(N²) bottlenecks
- High-dimensional optimization
- Complex simulations

**Action:**
- Search ArXiv papers or industry SOTA solutions
- Evaluate PyTorch, JAX, CUDA, and other frameworks
- Let data drive decisions, not trends

### 6. Vectorization Strategy

#### 6.1 Scale vs. Readability Tradeoff

**High Scale (N > 10³) or Explicit Performance Hotspots:**
- Use broadcasting mechanisms and matrix operations
- Mandatory for performance-critical code

**Low Scale / Complex Logic:**
- If business logic contains extremely complex conditional branches and data scale is small
- Explicit loops allowed to maintain readability

#### 6.2 Performance Hot Paths

- Inner loops with high call frequency MUST be vectorized or use JIT (`numba`, `jax.jit`)

## Integration Checklist

When applying this skill, verify:

- [ ] Numerical operations use tolerance-based comparisons where needed
- [ ] Physical units are explicit or well-documented
- [ ] Random processes support seeding
- [ ] Code follows separation of concerns
- [ ] Full type annotations present
- [ ] Algorithm complexity documented
- [ ] Defensive programming for edge cases
- [ ] Vectorization applied to hot paths
