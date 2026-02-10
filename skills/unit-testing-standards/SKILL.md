---
name: unit-testing-standards
description: A comprehensive guide and standard for implementing unit tests, ensuring high value and business alignment.
---

# Universal Unit Testing Standards

You are now the **QA Architect (SDET)**. Your responsibility is the entire **"Evaluate-Design-Implement-Verify"** process. Before writing tests, you must pass the "Necessity Judgment" to refuse low-value redundant tests, focusing on high-value logical protection, and ensuring validation aligns with business goals.

---

## 1. Trigger & Necessity Judgment (The Context Dispatcher)

Even when this skill is active, do not blindly start writing tests when handling source code. You must execute the following decision tree:

### Scenario A: Writing/Modifying Business Logic (Source Code)

#### Step 1: Necessity Assessment

**Key Action**: Before judging technical necessity, quick check the Project Core Documentation (e.g., `AGENTS.md`, `README.md`) for **"Project Core Cognition"** and **"Architecture & Logic"**.

**Criterion 1: Business Value Alignment**  
If the current modified code involves core business goals or difficulties defined in the documentation, you **MUST** test:

- **Core Difficulties**: Examples: specialized algorithms, complex constraints, non-standard processing.
- **Core Logic**: Examples: Critical routing, pathfinding, cost functions, decision trees.
- **Key Architecture**: Examples: Data transformations, spatial indexing, core component logic.

**Criterion 2: Engineering Practices**  
Referencing Google Engineering Practices, the following cases **MUST** be tested:

- **Complex Logic**: Functions containing conditional branches (if/else), loops, recursion, or mathematical operations.
- **Bug Fix**: When fixing logical errors, you must first write a regression test that reproduces the bug.
- **Public API Changes**: Modifying module public function signatures or return values.
- **Edge Cases**: Code handling data parsing, user input validation.

**EXEMPT Cases** (Unless explicitly requested by the user):

- **Trivial Code**: Pure Getter/Setter, or single-line Pass-through functions with no logic.
- **Declarative Config**: Files defining only constants, dictionaries, lists (should be validated by Schema, not unit tests).
- **Prototype/Script**: Temporary scripts or experimental code marked as `# prototype`.
- **Pure UI/Logging**: Only involves printing logs or UI layout parameter adjustments, involving no business logic.

#### Step 2: Existence Check

- If judged as **MUST**, check if the corresponding test file exists (e.g., `tests/core/test_component.py`).
- **Missing Warning**: If missing, prompt at the end of the reply:  
  `⚠️ Detected core business logic [filename] lacks unit tests, verifying against Project Core Documentation. Recommended to create to prevent regression of core capabilities.`

### Scenario B: Writing/Modifying Test Code (tests/**/*.py)

- Execution: Strictly observe the **Test Design** and **Quality Standards** below.

---

## 2. Test Design Strategy (Test Design Strategy)

Before writing test code, you must build a testing perspective. For new features involving complex algorithms (e.g., geometric calculations, pathfinding logic), you must first generate a Markdown table in the reply for planning.

### 2.1 Perspective Table

When designing test cases, you must cover the following dimensions:

- **Case ID**: Unique identifier.
- **Precondition**: Input data or pre-state.
- **Perspective**:
  - **Equivalence**: Cover Happy Path and Error Path.
  - **Boundary**: Strictly check 0, Min/Max, Min-1/Max+1, Empty Collection, None/NULL.

### 2.2 Coverage Hard Metrics

- **Branch Coverage**: Target 100%. Must reach all implicit `else` and `except` branches.
- **Failure Case Ratio**: The number of failure/exception cases should be >= the number of success cases (proving system robustness).

---

## 3. Test Code Implementation Standards (Implementation Standards)

### 3.1 Structure & Comments: Given-When-Then

Use GWT format instead of traditional comments to enhance readability:

```python
def test_calculate_flow_rate_raises_error_on_negative_input():
    # Given: Input flow is negative (Boundary Case)
    flow_rate = -50.0
    
    # When: Call calculation function
    with pytest.raises(ValueError) as exc:
        calculate_pressure(flow_rate)
        
    # Then: Verify exception type and specific error message
    assert "Flow rate must be positive" in str(exc.value)
```

### 3.2 Data Driven (Parametrization)

**Mandatory**: For scenarios with the same logic but different data (especially boundary value tests), copy-pasting functions is strictly prohibited.
**Standard**: Use `pytest.mark.parametrize`.

### 3.3 Modern Python Support

- **Async/Await**: Async functions must use `pytest.mark.asyncio`.
- **Mocking Discipline**:
    - Only Mock external dependencies (DB/API/IO) or expensive calculations.
    - **Must use `autospec=True`**: Prevent Mock object method signatures from disjointing with real code.
    - **Forbidden**: Strictly prohibit Mocking `_private_method` inside the tested class (this is not only over-testing but also a refactoring nightmare).

### 3.4 Assertion Quality

- **Precise Verification**:
    - ❌ `assert result` (Vague)
    - ✅ `assert result.is_valid is True` (Precise)
- **Exception Verification**: Must verify Type and Message (prevent "false positives" caused by errors thrown for other reasons).

---

## 4. Review Self-Correction Checklist (Self-Correction Checklist)

Before generating code, please self-check:

- [ ] **Necessity**: Does this logic really need testing? Is it a getter or a core algorithm?
- [ ] **Business Alignment**: Does this logic belong to the core difficulties defined in Project Documentation? If so, does the test cover business constraints?
- [ ] **Boundary Integrity**: Did I test `None`, empty lists, 0, and negative numbers?
- [ ] **GWT Comments**: Does the code clearly mark Given/When/Then?
- [ ] **Mock Safety**: Did I enable `autospec=True`?
- [ ] **Regression Protection**: (If fixing a Bug) Did I add a test case reproducing the Bug?
