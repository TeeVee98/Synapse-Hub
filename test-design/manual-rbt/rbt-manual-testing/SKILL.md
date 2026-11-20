---
name: rbt-manual-testing
description: "Comprehensive Risk-Based Testing (AI-RBT) 6-stage manual test case generation, Ambiguity Q&A analysis, Traceability Matrix, Field-Level Validation Checklist (25 input field types), Non-Functional scenarios (Double-Submit, Race Conditions), and Excel export formatting. Use when generating risk-based manual test cases and exploratory charters."
profiles: [enterprise-rbt, manual-qa]
category: test_automation_and_execution
version: "2.0.0"
policies:
  network: none
  shell: none
  filesystem: workspace-sandbox
---
# RBT Manual Testing (AI-Driven Risk-Based Testing Engine)

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Comprehensive Risk-Based Testing (AI-RBT) 6-stage manual test case generation, Ambiguity Q&A analysis, Traceability Matrix, Field-Level Validation Checklist (25 input field types), Non-Functional scenarios (Double-Submit, Race Conditions), and Excel export formatting. Use when generating risk-based manual test cases and exploratory charters.
- **Activation Scope:** Domain workflows for `02-test-design` involving `rbt-manual-testing`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT assign high risk scores uniformly across all features; differentiate by business impact and likelihood.
- Do NOT generate manual test suites without explicit step-by-step instructions and expected results.
- Do NOT omit test data setup and prerequisite teardown procedures.
- **Sibling Skill Boundaries:**
  - gherkin-to-suite compiles automated BDD suites; rbt-manual-testing designs risk-weighted manual test suites and Excel matrix exports.

---

## 3. Ordered Execution Workflow

### Overview & Capabilities

**RBT Manual Testing** is an enterprise-grade skill for designing manual test suites using **Risk-Based Testing (RBT)** and coverage matrix analysis (fully aligned with **ISO/IEC/IEEE 29119-2** test processes and **ISO/IEC/IEEE 29119-3** test documentation standards). It provides two operational modes:

| Mode | When to Use | Scope & Characteristics | Execution Time |
| :--- | :--- | :--- | :--- |
| **QUICK Mode** | Standalone modules, simple forms, rapid prototyping | 5-step pipeline with mandatory Ambiguity Checkpoint & EP/BVA coverage | Fast (~1-2 min) |
| **FULL RBT Mode** | Enterprise workflows, complex business rules, high risk | 6-stage sequential pipeline with checkpoints for Ambiguity & RTM | Thorough & structured |

### Core Tenets:
1. **Human Strategy:** Engineers define business boundaries, risk appetite, and resolve flagged ambiguities.
2. **AI Execution:** Agent decomposes modules, builds coverage matrices, applies the 25-field validation checklist, and computes risk scores.
3. **Enterprise Deliverables (ISO/IEC/IEEE 29119-3 Aligned):** Standardized 12-column Markdown tables with automation metadata and mandatory Ambiguity & Assumptions Log, ready for export to Excel (`.xlsx`), Jira Xray, or TestRail.

---

### Mode Routing

- **Trigger QUICK Mode:**
  - "quick test cases", "generate test cases for registration form", "generate test cases from requirement".
  - Small scope (single screen, isolated dialog), clear requirements.
- **Trigger FULL RBT Mode:**
  - "/generate_manual_testcases_rbt", "6-step RBT process", "risk-based test plan", "comprehensive manual suite".
  - Complex multi-step flows, cross-module dependencies, or audit requirements.

---

### Mode 1: QUICK Mode (Fast 5-Step Pipeline)

1. **Step 1: Requirement Analysis & Boundary Mapping:**
   - Decompose requirements into functional flows: Happy Paths, Negative Paths, Boundary Conditions, and Edge Cases.
   - Extract form inputs, business rules, acceptance criteria, and interaction states.
2. **Step 2: Mandatory Ambiguity Checkpoint & Assumptions Log:**
   - Scan requirement statements for ambiguities, omissions, unspecified boundary lengths, undefined error messages, missing timeouts, and implicit system assumptions.
   - Format and emit a dedicated `## Ambiguity & Assumptions Log` table in the deliverable:
     <!-- classification: illustrative -->
     ```markdown
     | ID | Requirement Reference / Statement | Ambiguity / Gap Detected | Working Assumption / Resolution | Impact / Risk |
     | :--- | :--- | :--- | :--- | :--- |
     ```
   - 🛑 **Checkpoint Guard:** If a critical blocking contradiction or missing core business logic is identified, halt test generation immediately and prompt the user for clarification before proceeding. For non-blocking gaps, record explicit working assumptions in the log.
3. **Step 3: Test Design Techniques:**
   - **Equivalence Partitioning (EP):** Partition valid and invalid input classes.
   - **Boundary Value Analysis (BVA):** Support 2-value BVA (`Min-1`, `Min`, `Max`, `Max+1` for standard forms) and 3-value BVA (`Min-1`, `Min`, `Min+1`, `Max-1`, `Max`, `Max+1` for high-precision financial, currency, and security boundaries).
   - **Decision Table:** Combinatorial matrix for multi-conditional business rules (pricing tiers, approval rules, discount triggers).
   - **State Transition:** Sequence of object lifecycle states (`Draft` -> `Pending` -> `Approved` -> `Rejected`/`Cancelled`).
4. **Step 4: Field-Level Validation (25 Field Types):**
   - **Token-Efficient Checklist Loading:** If the target screen/feature has **≤ 8 field types**, query only the required rules on demand via `agent-qa checklist --fields <fields> --invariants <invariants>` (0-token Python tool) instead of loading the entire 24 KB file (always append `--invariants payment-ui-latency` when analyzing checkout, payment, or financial transaction flows). Read the full `references/field_validation_checklist.md` ONLY if the screen contains > 8 field types or if performing a full compliance audit.
   - Apply the [**Field-Level Validation Checklist (25 Field Types)**](references/field_validation_checklist.md) across all form inputs.
   - Generate dedicated, isolated validation test cases for each input field (do not merge disparate field validations into a single catch-all test case).
5. **Step 5: Standard ISO 29119-3 Table & Metadata Export:**
   - Format test cases into the standardized 12-column Markdown table conforming to ISO/IEC/IEEE 29119-3.
   - Populate automation metadata: `Automatable` (`Yes`/`No`/`Partial`), `Auto Type` (`UI`/`API`/`Unit`/`N/A`), `@Tags` (`@Smoke`, `@Regression`, `@CriticalPath`).
   - Append the mandatory `## Ambiguity & Assumptions Log` section to the test suite deliverable.

---

### Mode 2: FULL RBT (6-Stage Sequential Pipeline)

```mermaid
flowchart TD
    S1["<b>Stage 1: Context & Framing</b><br/>Role-play, scope & MVP boundaries"] --> S2["<b>Stage 2: Analysis & QnA</b><br/>Ambiguity detection (Checkpoint)"]
    S2 --> S3["<b>Stage 3: Decomposition</b><br/>Module hierarchy & dependencies"]
    S3 --> S4["<b>Stage 4: Traceability & Gap</b><br/>RTM & High-Level Scenarios (Checkpoint)"]
    S4 --> S5["<b>Stage 5: Test Case Authoring</b><br/>Risk Scoring (H/M/L) + 25 Field Types"]
    S5 --> S6["<b>Stage 6: Template Mapping</b><br/>12-column table + Automation tags"]
```

### Stage 1: Context & Framing
- Identify target system goals, user personas, testing standards, and release scope (MVP vs Full).
- Confirm understanding with the user before proceeding.

### Stage 2: Analysis & Ambiguity Q&A
- Map business paths: Happy Path, Alternate Paths, Exception Paths.
- Detect ambiguities: missing rules, contradictions, undefined error messages, missing timeouts.
- **OpenAPI / Swagger Ingestion Reconciler:** When an API spec is available, invoke `python tools/api/spec_reconciler.py <story> <spec>` to automatically cross-examine User Story rules against backend Schema constraints (`minLength`, `maxLength`, `pattern`, `enum`, `required`), anchoring boundary cases directly to Ground-Truth.
- Format numbered Q&A table (`Q1, Q2, Q3...`) with context, detected schema discrepancies, and proposed assumptions.
- 🛑 **Checkpoint:** Pause and wait for user/stakeholder response before Stage 3.

### Stage 3: System Decomposition
- Decompose system into Modules -> Sub-modules -> Components.
- Map functional dependencies and shared state across modules.

### Stage 4: Traceability Matrix (RTM) & Gap Analysis
- Build Requirements Traceability Matrix linking requirement IDs (`REQ-xxx`) to high-level test scenarios.
- Perform gap analysis to detect uncovered edge cases or orphan flows.
- 🛑 **Checkpoint:** Present scenario outline for user sign-off.

### Stage 5: Detailed Test Case Generation & Risk Scoring
- Assign Risk Level:
  - **High:** Core revenue flows, payment processing, authentication, data loss risks.
  - **Medium:** CRUD operations, table filtering, search, pagination.
  - **Low:** Cosmetic UI, tooltips, static informational content.
- Non-Functional & Resilience Scenarios:
  - **Network Interruption:** Connection drops mid-transaction.
  - **Browser Navigation:** Browser Back/Forward or page refresh during multi-step wizards.

#### Conditional Concurrency & Race Condition Matrix
> **Activation Rule:** Evaluate the feature against the *Concurrency Gate* first.
> - **AUTO-ENABLE** only if the feature involves: financial transactions/balances, limited inventory/bookings/vouchers, multi-step state approvals, shared multi-user edits, or async webhooks/retries.
> - **AUTO-SKIP** for read-only views, static pages, or single-user non-transactional CRUD forms (log `Concurrency Gate: SKIPPED — non-contentious feature`).

When `Concurrency Gate = ON`, generate targeted cases for applicable vectors:
1. **Double-Submit / Rapid Click:** Trigger submit/pay/create twice within <300ms (UI click or duplicate POST) -> verify only 1 record/charge is created and button disables or backend rejects duplicate.
2. **Resource Contention (Last-Item / Overselling):** Two concurrent sessions claim the last available stock/slot/voucher at the exact same timestamp -> verify exactly 1 succeeds and 1 receives a clear conflict error (`409 Conflict` / out-of-stock message), with zero negative balance/stock.
3. **Stale State / Optimistic Locking:** User A and User B open the same record; User A saves first, then User B saves outdated data -> verify system blocks silent overwrite (version/ETag check) or prompts merge/refresh.
4. **Retry & Idempotency:** Simulate network timeout after server commits, then retry with the same `Idempotency-Key` -> verify server returns the original result without creating duplicate records.

#### Conditional ISTQB & ISO/IEC/IEEE 29119 Advanced Test Design Techniques
In addition to Equivalence Partitioning (EP), Boundary Value Analysis (BVA), and Exploratory Testing, conditionally activate targeted formal techniques (CT-FL / CT-TAE / ISO 29119-4):

| Technique | Auto-Activation Rule | Mandatory Generation Rule |
| :--- | :--- | :--- |
| **Decision Table** | Business logic has **≥ 2 combined conditions** governing outputs (pricing, discounts, loan limits, RBAC permissions). | Enumerate combinatorial matrix of condition states (`True/False` or distinct levels) covering valid combinations, conflicting rules, and precedence ordering. |
| **State Transition** | Entities with an **explicit lifecycle or finite states** (`Draft -> Pending -> Approved -> Cancelled / Refunded`). | Generate valid sequential lifecycle transitions and invalid/illegal leapfrog or backwards transitions that must be blocked. |
| **Pairwise / All-Pairs** | Screens or APIs with **≥ 3 independent combinatorial selection/filter fields** (e.g. OS × Browser × Payment × Currency). | Apply orthogonal/all-pairs combinatorial reduction to test 100% of two-way parameter interactions instead of combinatorial explosion. |

#### Conditional Data Integrity Checklist
> **Activation Rule:** AUTO-ENABLE only for features with DB mutations, multi-step transactions, financial/numeric calculations, or file import/export. AUTO-SKIP for static/read-only views.

When `Data Integrity Gate = ON`, generate targeted cases for applicable vectors:
1. **Atomicity & Rollback:** Simulate a failure mid-transaction (e.g., balance deducted / stock decremented, then order creation fails) -> verify full DB rollback with zero orphaned records or balance drift.
2. **3-Tier Consistency (UI ↔ API ↔ DB):** After save/update, reload UI (F5), call GET API, and verify DB state -> confirm 100% match across UTF-8 Vietnamese text, currency rounding, and timezone formatting.
3. **Referential Integrity / Soft Delete:** Delete or archive a parent record referenced by child data (e.g., product linked to existing orders) -> verify historical child records remain intact and render without errors.
4. **Partial Update Safety & Audit Trail:** Update a single field (e.g., display name) -> verify unrelated fields are not wiped/reset (`PATCH` vs `PUT`), `created_at` stays immutable, and `updated_at` / audit log updates accurately.

- Field-Level Validation: Generate dedicated test cases for each input field.

### Stage 6: Template Mapping & Automation Metadata
- Assemble all test cases into the standard 12-column Markdown table.
- Populate automation metadata: `Automatable` (`Yes`/`No`/`Partial`), `Auto Type` (`UI`/`API`/`Unit`/`N/A`), `@Tags` (`@Smoke`, `@Regression`, `@CriticalPath`).

---

### Field-Level Validation Checklist (25 Field Types)

Field-level validation rules cover positive, boundary/negative (BVA), and security vectors across 25 standard enterprise field types:
1. Text (Name, Title) • 2. Email • 3. Phone • 4. Password • 5. Number • 6. Date • 7. Date Range • 8. Dropdown • 9. Multi-Select • 10. Checkbox/Radio • 11. Textarea • 12. File Upload • 13. OTP/MFA • 14. Range Slider • 15. Rich Text Editor (Basic WYSIWYG) • 16. Geo Location & Address Autocomplete • 17. Digital Signature Pad (Canvas) • 18. Biometric / WebAuthn • 19. Camera / Barcode / QR Scanner • 20. Currency & FX (Multi-Currency & Dynamic FX) • 21. Credit Card / IBAN / Masked Input • 22. Async Autocomplete / Typeahead • 23. Cron Expression & Recurring Schedule • 24. JSON / Code / Formula Editor • 25. Inline Editable Data Grid.

👉 **Token-Efficient On-Demand Query:** For screens with **≤ 8 field types**, execute `agent-qa checklist --fields <field1,field2,...> --invariants <inv1,inv2,...>` (or `python tools/manual/checklist_query.py ...`) to inject only the relevant micro-slice without consuming context budget. Always append `--invariants payment-ui-latency` when analyzing checkout, payment, or financial transaction flows.
👉 **Full Checklist & Edge Cases:** Refer to [**Field-Level Validation Reference (`references/field_validation_checklist.md`)**](references/field_validation_checklist.md) for complete equivalence partitions, SQLi/XSS attack strings, and race condition test matrices when > 8 field types are present or full audit is requested.

---

### Standard Table Output Specification

All generated test cases must adhere to the 12-column Markdown specification:

<!-- classification: illustrative -->
```markdown
| TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| CRM_CUST_TC_001 | Customer | High | Verify create customer with valid data | 1. User logged in as Admin<br>2. On Customer page | 1. Click "New Customer"<br>2. Fill all mandatory fields<br>3. Click "Save" | 1. Alert "Customer added successfully"<br>2. Record visible in customer table | High | Company="AutoCorp", Phone="+123456789" | Yes | UI | @Smoke, @Regression |
```

> **Formatting Invariants:**
> - Numbered test steps and expected results must use `<br>` for multi-line formatting inside table cells.
> - `Risk Level`: `High`, `Medium`, `Low`.
> - `Priority`: `Critical`, `High`, `Medium`, `Low`.

---

### Export to Styled Excel (.xlsx)

Export Markdown test cases directly into styled Excel workbooks via the CLI tool:

<!-- classification: illustrative -->
```bash
# Convert Markdown table into styled Excel
synapse export-excel path/to/test_cases.md -o output.xlsx --sheet-name "Regression Suite"

# Or via unified CLI dispatcher:
agent-qa export-excel path/to/test_cases.md
```

Generated workbooks automatically include:
- Corporate Navy Blue header styling (`#1F4E78`, bold, white).
- Frozen header pane (`A2`) and enabled `AutoFilter`.
- Color-coded badges for Risk Level and Priority.
- Multi-line text wrapping and optimized column widths.

---

### Zero-Review Trust Engine (Triple-Filter, Spec Reconciler & Auto-Sanity)

Synapse-Hub embeds an automated 3-tier verification pipeline guaranteeing 100% Zero-Review Trust:

1. **Spec Reconciliation (`tools/api/spec_reconciler.py`):**
   - Ingests User Stories and OpenAPI/Swagger specifications simultaneously.
   - Detects boundary mismatches and generates standardized 12-column test suites anchored to JSON schema AST constraints.

   <!-- classification: illustrative -->
   ```bash
   python tools/api/spec_reconciler.py path/to/story.md --swagger path/to/swagger.json -o test_cases.md
   ```

2. **Triple-Filter Linter Gate (`tools/lint/manual_tc_linter.py`):**
   - **Filter 1 (Completeness Guard):** Enforces 12 standard columns and eliminates speculative language (`HOẶC`, `tùy backend`).
   - **Filter 2 (Deduplication):** Flags semantic duplication (> 85% similarity) to eliminate test bloat.
   - **Filter 3 (Golden Ratio Enforcement):** Guarantees at least 15–20% Security & Resilience vectors (40% Happy / 40% Negative / 20% Security).

   <!-- classification: illustrative -->
   ```bash
   python tools/lint/manual_tc_linter.py path/to/test_cases.md
   ```

3. **Auto-Sanity Verification Engine (`tools/design/auto_sanity_engine.py`):**
   - Verifies test steps against live DOM/AOM contracts or via Headless Playwright Chrome.
   - Tags verified test cases with `@Live-Verified` and exports executable Clean POM TypeScript specs (`.spec.ts`).

   <!-- classification: illustrative -->
   ```bash
   python tools/design/auto_sanity_engine.py path/to/test_cases.md --html app.html --export-spec sanity.spec.ts
   ```

---

### TMMi (Test Maturity Model integration) Maturity Assessment
- Assess repository and test engineering practices against TMMi Levels 1 through 5 (Level 2 Managed, Level 3 Defined, Level 4 Measured, Level 5 Optimization) via `tools/tmmi_auditor.py` (`agent-qa tmmi`).

---

## 4. Verification Points & DoD

1. Every test case carries explicit Risk Priority Number (RPN = Impact x Likelihood).
2. Test steps include preconditions, concrete test data, and verifiable expected outcomes.
3. Every test suite document includes a mandatory `## Ambiguity & Assumptions Log` table (required deliverable across all modes, including QUICK Mode and FULL RBT Mode).
4. Test process conforms to ISO/IEC/IEEE 29119-2/3 and meets TMMi Level 3+ maturity requirements (`agent-qa tmmi --gate-level 3`).
5. Exported test suite generates clean tabular data (Excel / CSV / Markdown).

---

## 5. Handoff Protocol

- **Deliverables:** Risk-based manual test suite documents (conforming to 12-column ISO 29119-3 layout and including mandatory `## Ambiguity & Assumptions Log` section) and Excel-compatible test case matrices.
- **Next Subagent:** test-designer
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
