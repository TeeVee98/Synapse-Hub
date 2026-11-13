---
name: review-spec
description: "Stress-test specifications, user stories, and BDD feature files with zero-context rigor. Use when reviewing requirements, user stories, or acceptance criteria before code generation."
category: architecture_and_analysis
version: "1.0.0"
---

# Review Spec — Zero-Context Specification Stress-Tester

Review test specifications, User Stories, and BDD `.feature` files with stateless, zero-context rigor (Elephant-Goldfish Model) before generating code.

Order of evaluation: **System Boundaries -> Dynamic Data & Teardown -> Assertion Rigor -> Boundary & Negative Cases -> Concrete Implementation Targets**.

---

## 1. When to Use

- Triggered automatically before `pom-crafter` synthesizes Page Classes or test scripts from natural-language specs.
- Triggered when the user asks to review, audit, or refine requirements, user stories, or acceptance criteria.
- Integrated CLI invocation:
  ```bash
  python tools/goldfish_review.py path/to/spec.md
  python tools/goldfish_review.py path/to/feature.feature --json
  # or via CLI shim:
  agent-qa review-spec path/to/spec.md
  ```

---

## 2. Five Verification Vectors (Goldfish Protocol)

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

## 3. Autonomous Execution Workflow

1. Ingest specification file (`.md`, `.feature`, or story text).
2. Run `python tools/goldfish_review.py <spec_file>`.
3. If review score is `< 80/100` or blocking gaps are found, report specific missing vectors to the user or orchestrator.
4. Once verified ($\ge 80/100$), proceed with Clean POM test script codification.
