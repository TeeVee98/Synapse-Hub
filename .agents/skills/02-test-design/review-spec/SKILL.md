---
name: review-spec
description: "Stress-test specifications, user stories, and BDD feature files with zero-context rigor. Use when reviewing requirements, user stories, or acceptance criteria before code generation."
category: architecture_and_analysis
version: "1.0.0"
policies:
  network: none
  shell: none
  filesystem: read-only
---
# Review Spec — Zero-Context Specification Stress-Tester

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Stress-test specifications, user stories, and BDD feature files with zero-context rigor. Use when reviewing requirements, user stories, or acceptance criteria before code generation.
- **Activation Scope:** Domain workflows for `02-test-design` involving `review-spec`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT accept vague, contradictory, or untestable acceptance criteria without flagging defects.
- Do NOT invent speculative business logic outside stated requirements.
- Do NOT skip boundary condition and error flow analysis.
- **Sibling Skill Boundaries:**
  - architecture-decision-records records architectural choices; review-spec inspects requirement specs against the 5 Goldfish verification vectors.

---

## 3. Ordered Execution Workflow

Review test specifications, User Stories, and BDD `.feature` files with stateless, zero-context rigor (Elephant-Goldfish Model) before generating code.

Order of evaluation: **System Boundaries -> Dynamic Data & Teardown -> Assertion Rigor -> Boundary & Negative Cases -> Concrete Implementation Targets**.

---

### When to Use

- Triggered automatically before `pom-crafter` synthesizes Page Classes or test scripts from natural-language specs.
- Triggered when the user asks to review, audit, or refine requirements, user stories, or acceptance criteria.
- Integrated CLI invocation:
<!-- classification: illustrative -->
```bash
  python tools/goldfish_review.py path/to/spec.md
  python tools/goldfish_review.py path/to/feature.feature --json
  # or via CLI shim:
  agent-qa review-spec path/to/spec.md
```

---

### Five Verification Vectors (Goldfish Protocol)

1. **Comprehension & System Boundaries (20%):**
   - Explicit Actor/Role definition.
   - Clear Preconditions and Initial State.
   - Well-defined Target Scope (no vague "works fine" or "system operates normally").

2. **Dynamic Data & Idempotent Teardown (20%):**
   - Mandatory dynamic timestamps or random prefixes (`AUTO_`, `uniqueCode`) to eliminate database primary key collisions.
   - Explicit post-test cleanup or automated Teardown step for every data-creation path.

3. **Assertion Rigor & Truth Anchor (25%):**
   - Concrete, deterministic expected results instead of tautological assertions.
   - Zero-Fake-Pass guarantee: explicit UI state changes, status codes, or database assertions.

4. **Boundary & Negative Scenarios (20%):**
   - Invalid input values, boundary overflows, and unauthorized access attempts.
   - Explicit error message and validation feedback assertions.

5. **Concrete Implementation Targets (15%):**
   - Concrete Page Class mappings or API endpoint routes.
   - Clean POM Flat Architecture compliance (locators belongs in Page Classes, not test scripts).

---

### Autonomous Execution Workflow

1. Ingest specification file (`.md`, `.feature`, or story text).
2. Run `python tools/goldfish_review.py <spec_file>`.
3. If review score is `< 80/100` or blocking gaps are found, report specific missing vectors to the user or orchestrator.
4. Once verified ($\ge 80/100$), proceed with Clean POM test script codification.

---

## 4. Verification Points & DoD

1. Requirements audited across all 5 vectors (Ambiguity, Testability, Completeness, Consistency, Boundary).
2. Ambiguities documented with specific clarifying questions and risk ratings.
3. Specification readiness verdict issued (APPROVED, BLOCKED, or REVISE).

---

## 5. Handoff Protocol

- **Deliverables:** Requirement review audit report and ambiguity remediation ledger.
- **Next Subagent:** test-designer / orchestrator
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
