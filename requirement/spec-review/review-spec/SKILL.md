---
name: review-spec
description: "Stress-test specifications, user stories, and BDD feature files with zero-context rigor. Use when reviewing requirements, user stories, or acceptance criteria before code generation."
profiles: [enterprise-rbt, manual-qa]
category: architecture_and_analysis
version: "1.0.0"
policies:
  network: none
  shell: read-only
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
  python tools/orchestration/goldfish_review.py path/to/spec.md
  python tools/orchestration/goldfish_review.py path/to/feature.feature --json
  # or in BRD mode for pure business requirement documents (exempts teardown & DOM selectors):
  python tools/orchestration/goldfish_review.py path/to/brd.md --mode brd
  # or via CLI shim:
  agent-qa review-spec path/to/spec.md
  agent-qa review-spec path/to/brd.md --mode brd
```

---

### Verification Modes & Vector Re-weighting

| Mode | Target Document Scope | Vector Re-weighting & Behavior |
| :--- | :--- | :--- |
| **`automation-ready`** (Default) | Test specs intended for `pom-crafter` code synthesis | Enforces all 5 vectors: Comprehension (20%), Dynamic Data & Idempotent Teardown (20%), Assertion Rigor (25%), Boundary & Negative Scenarios (20%), and Concrete Implementation Targets (15%). |
| **`brd`** | Business Requirements (BRD / PRD / User Story) | Re-weights vectors to: Comprehension & Actor Matrix (25%), Business Rules & Logic (25%), Assertion Rigor & Testability (25%), Boundary & Exception Flows (25%). **Completely exempts database teardown hooks and DOM PageClass/selector requirements**. |

---

### Pre-Check: BRD/PRD Business & NFR Gate (ISO/IEC/IEEE 29148 & ISO/IEC 25010)
Trước khi chấm 5 vector Elephant-Goldfish, kiểm tra nhanh tài liệu đầu vào:
- **Unambiguous & Measurable:** Gắn cờ mọi mô tả cảm tính ("nhanh", "mượt", "hợp lý") và yêu cầu quy đổi ra số liệu cụ thể.
- **3-Flow AC Completeness:** Mỗi `REQ_ID` phải đủ Happy Path, Validation/Negative và Error Recovery (timeout, mất mạng, hủy giữa chừng).
- **NFR Attached:** Với luồng Auth/Giao dịch/Tải cao, bắt buộc có sẵn: (1) Security Baseline (RBAC, chống IDOR, che PII, rate-limit), (2) Performance SLA/SLO (Read vs Write P95, CCV/RPS dự kiến), và (3) Platform/Offline matrix (OS/Browser tối thiểu).

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

#### Conditional Gate — Vector 6: Concurrency & Race Condition Readiness (Auto-Triggered Only)
- **Trigger:** Activate ONLY when the spec involves financial/balance changes, limited stock/slots/vouchers, shared multi-user mutations, state-machine transitions, or retryable APIs. Skip automatically for read-only or simple single-user CRUD specs.
- **Checks when active:**
  - Does the spec define expected behavior on **double-submit** or duplicate requests (UI debounce + backend idempotency)?
  - Does the spec specify conflict resolution when **2+ actors mutate the same resource** (e.g., `409 Conflict`, optimistic locking, or atomic decrement)?
  - If missing in a high-risk transactional spec, flag as `[CONCURRENCY GAP]` before approving the spec for test script generation.

---

### Autonomous Execution Workflow

1. Ingest specification file (`.md`, `.feature`, or story text).
2. Run `python tools/orchestration/goldfish_review.py <spec_file>`.
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
