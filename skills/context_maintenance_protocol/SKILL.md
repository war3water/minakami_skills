---
name: context_maintenance_protocol
description: Load project context strategically by understanding goals (AGENTS.md), technical state (README.md), and engineering standards. Maintain documentation ecosystem consistency. Use when starting new features, performing architectural refactoring, fixing complex bugs, or when user asks about project background.
---

## When to Use This Skill

**Trigger Conditions:**
- New feature development
- Architectural refactoring
- Core algorithm modifications
- Complex bug fixes
- User asks about project background or goals
- Working with API integrations or data formats

**Exclusions:**
- Simple syntax fixes
- Bug fixes not involving algorithmic principles
- Pure UI adjustments

## Core Purpose

This protocol simulates a senior engineer's "Context-Aware" workflow, establishing a four-dimensional cognitive alignment mechanism:

1. **Strategy** - What and why (project goals)
2. **Tactics** - Current state and implementation paths
3. **Standards** - Quality and engineering requirements
4. **Reference** - Specialized task-specific documentation

---

## 1. Cognitive Loading Sequence

When this rule triggers, execute the following context addressing steps to build your "mental space":

### Step 1: Anchor Strategy (The AGENTS.md Protocol)

**Goal:** Understand what the project aims to achieve and why.

**Action:** Prioritize finding and reading `AGENTS.md` in the project root directory.

**Standard:** Treat this as a Standardized Agent Protocol. It defines:
- Task and business objectives
- Agent role persona
- Mental model
- Core constraints

**Fallback:** Only if AGENTS.md doesn't exist, try finding GOALS.md, MISSION.md, or seek strategic sections in README.md.

**Guideline:** AGENTS.md is the principle guidance file for AI coding task objectives. Overall execution planning must reference this file's task goals.

### Step 2: Anchor Tactics (Technical State)

**Goal:** Master the project's "current hand" and "implementation paths."

**Action:** Read the project's primary technical overview documentation: `README.md`.

**Key Insights to Extract:**
- Map existing directory structure
- Understand naming conventions
- Identify core libraries and dependencies
- Learn existing architecture patterns

**Guideline:** Respect existing architecture. Strictly forbidden to fabricate non-existent APIs.

### Step 3: Align Standards (Engineering Quality)

**Goal:** Ensure code quality meets project-specific high standards.

**Action:** Check for engineering standards documents:
- CONTRIBUTING.md
- STYLEGUIDE.md
- docs/standards.md or similar

**Self-Correction:** Before coding, ask yourself:
"Does my implementation approach comply with this project's defined engineering standards?"

### Step 4: Discover Reference Documentation (Hub-Based Discovery)

**Goal:** Identify specialized documentation for task-specific guidance using a structured discovery approach.

**Protocol:**

1.  **Phase 1: The Hub Search (Primary)**
    - Scan `README.md` (and `AGENTS.md`) for a "Documentation," "References," or "Further Reading" section.
    - **Action**: Follow explicit links provided in these central files. This is the source of truth.
    - *Rationale*: Users organize projects differently. The README is the universal map.

2.  **Phase 2: Directory Scanning (Secondary Fallback)**
    - If no clear links are found in the hub, check for standard documentation directories:
        - `docs/`
        - `doc/`
        - `documentation/`
        - `wiki/`
    - List the contents of these directories to identify relevant files.

3.  **Phase 3: Pattern Matching (Tertiary Fallback)**
    - If no directories exist, look for files matching functionality:
        - `api.md` / `api_reference.md`
        - `schema.md` / `data_models.md`
        - `architecture.md` / `design.md`

4.  **Phase 4: User Inquiry (Last Resort)**
    - If specific documentation is critically needed (e.g., "I need to know the API schema to build this frontend") and cannot be found:
    - **Prompt**: "I've checked README.md and standard documentation folders but couldn't find the [specific doc type]. Could you point me to the right reference?"

**Task-Documentation Mapping (Heuristic):**

| Task Type | Keywords to Look For |
|-----------|----------------------|
| API changes | `api`, `endpoints`, `interface`, `swagger` |
| Data format changes | `schema`, `data`, `models`, `json` |
| System design | `architecture`, `system`, `design`, `structure` |
| Deployment | `deploy`, `ops`, `env`, `setup` |

---

## 2. Documentation Ecosystem Maintenance

The Agent is not just a code producer but also a project knowledge base maintainer. At task completion, evaluate documentation synchronization needs:

### Scenario A: Technical Documentation Sync

**Trigger Conditions:**
- Implementation details changed substantially
- New modules added or public APIs modified
- Configuration methods changed

**Action:** Automatically update or prompt user to update relevant documentation.

**Crucial Step**: If you create NEW documentation (e.g., `docs/new_api.md`), you **MUST** link it in `README.md` (The Hub) so future agents can find it.

### Scenario B: Strategic Documentation Calibration

**Trigger Conditions:**
- Fundamental goals or assumptions shifted
- Core technical approach changed

**Action:** **STRICTLY FORBIDDEN** to directly modify AGENTS.md without permission. Must ask user for validation.

---

## 3. Resilient Safety Nets

### Context Inferencing & Fallback

If `docs/` directory doesn't exist or is empty:
- **Action**: Check for inline documentation in code (docstrings, comments).
- **Action**: Infer API contracts from type hints and function signatures.

### Conflict Awareness

If strategy documents (ideal) conflict with existing code (reality):
- **Principle**: **Short-term priority** = Maintainability of existing runnable code.
- **Action**: Highlight the deviation to the user unless it is a trivial divergence.

---

## 4. Integration Workflow

1. **Load Context:**
   ```
   AGENTS.md → README.md (The Hub) → [Discovered Refs] → Standards
   ```

2. **During Implementation:**
   - Verify alignment with loaded context.
   - Consult discovered reference docs for specific tasks.

3. **After Implementation:**
   - **Update The Hub**: Ensure `README.md` points to any new or updated docs.
   - Evaluate sync needs across the ecosystem.

---

## 5. Context Loading Checklist

### Strategic & Technical Hub
- [ ] Read `AGENTS.md` (Strategic Goal)
- [ ] Read `README.md` (Technical Hub)

### Reference Discovery
- [ ] **Checked Hub**: Did README.md contain links to other docs?
- [ ] **Loaded References**: Accessed relevant docs based on task (API, Schema, etc.)
- [ ] *(Fallback)*: Scanned `docs/` if hub was silent.

### Standards & Maintenance
- [ ] Applied engineering standards
- [ ] Flagged documentation updates needed (especially adding links to README)
