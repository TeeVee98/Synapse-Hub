---
name: api-spec-to-e2e-matrix
description: "Generate automated positive, boundary, and negative test matrices from OpenAPI specifications. Use when converting an OpenAPI/Swagger spec into an end-to-end test matrix."
category: architecture_and_analysis
version: "2.0.0"
policies:
  network: none
  shell: none
  filesystem: workspace-sandbox
---
# API Spec to E2E Matrix — Contract-Based Test Generator

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Generate automated positive, boundary, and negative test matrices from OpenAPI specifications. Use when converting an OpenAPI/Swagger spec into an end-to-end test matrix.
- **Activation Scope:** Domain workflows for `03-api-and-contracts` involving `api-spec-to-e2e-matrix`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT generate positive-only test matrices; boundary and negative status codes must be fully mapped.
- Do NOT generate tests against outdated OpenAPI specifications without running schema diffing.
- Do NOT hardcode unauthenticated test credentials in generated matrices.
- **Sibling Skill Boundaries:**
  - consumer-driven-contract-testing verifies CDC contracts; api-spec-to-e2e-matrix compiles exhaustive test matrices from OpenAPI specs.

---

## 3. Ordered Execution Workflow

This skill converts OpenAPI / Swagger specifications, JSON Schemas, or REST endpoint contracts into a structured, executable End-to-End (E2E) testing matrix covering happy path, boundary values, and negative error scenarios.

---

### Test Generation Matrix Taxonomy

```mermaid
flowchart TD
    Spec["OpenAPI / Swagger / JSON Schema"] --> Parse["Extract Endpoint Contracts"]
    Parse --> Pos["1. Positive Happy Path<br/>• Valid payload<br/>• HTTP 200/201<br/>• Response schema match"]
    Parse --> Bound["2. Boundary Value Analysis<br/>• Min/Max string length<br/>• Zero, negative numbers<br/>• Unicode & special chars"]
    Parse --> Neg["3. Negative & Fault Scenarios<br/>• Missing required fields (400)<br/>• Invalid auth token (401/403)<br/>• Malformed payload (422)"]

    Pos & Bound & Neg --> Suite["Executable Test Suite"]
```

---

### Boundary Value Generation Rules

For every field defined in the endpoint schema, generate targeted edge cases:

| Field Data Type | Schema Constraint | Generated Boundary Test Inputs |
| :--- | :--- | :--- |
| **String (Code / ID)** | `minLength: 3, maxLength: 20` | Empty string `""`, 2 chars, exactly 3 chars, 20 chars, 21 chars, special chars `<script>`, SQL `' OR 1=1--` |
| **Number / Integer** | `minimum: 0, maximum: 1000` | `-1`, `0`, `1`, `999`, `1000`, `1001`, floating point `10.5` |
| **Date / Timestamp** | `format: date-time` | Past date, today, future date, leap year `2024-02-29`, invalid format `31/12/2026` |
| **Enum** | `["ACTIVE", "INACTIVE"]` | Exactly `"ACTIVE"`, lowercase `"active"`, null, undefined, unknown enum `"DELETED"` |
| **Required Properties** | `required: ["code", "name"]` | Omit `code`, omit `name`, send `null` values |

---

### Negative Scenario Validation Checklist

Every negative test case must assert two distinct layers:
1. **API Layer Assertion:**
   - Verify HTTP Status Code is appropriately 400, 401, 403, 404, or 422.
   - Verify error payload contains expected error codes and localization messages.
2. **UI / Toast Notification Layer Assertion:**
   - Verify that the web UI displays the appropriate red toast notification (e.g. *"Dữ liệu không hợp lệ"* or *"Mã đã tồn tại"*).
   - Verify that the form remains open and input fields preserve user state without losing entered data.

---

### Automation Output Standards

- Generated test cases must adhere to the project's **Clean POM** structure.
- All requests should utilize dynamic test data with unique timestamp prefixes to ensure idempotency.

---

### Automated Execution via Tooling

Agent can automatically invoke `tools/generate_api_matrix.py` and `tools/export_postman_collection.py`:

<!-- classification: illustrative -->
```bash
# 1. Generate Markdown matrix
python3 tools/generate_api_matrix.py --spec path/to/openapi.json --format md -o docs/api_matrix.md

# 2. Generate JSON matrix for programmatic ingestion
python3 tools/generate_api_matrix.py --spec path/to/openapi.json --format json -o reports/api_matrix.json

# 3. Export directly to Postman Collection v2.1.0 with AJV JSON Schema & DDT
synapse export-postman --spec path/to/openapi.json -o postman_collection.json --env-output postman_env.json --ddt-output test_data.csv

# 4. Zero-Input Autonomous Synthesis (No input file provided!)
agent-qa export-postman --domain banking -o banking_col.json --env-output env.json --ddt-output ddt.csv
agent-qa export-postman --domain ecommerce -o ecom_col.json

# 5. Execute Newman & Enforce CI/CD Quality Gate
newman run postman_collection.json -e postman_env.json -d test_data.csv -r cli,json --reporter-json-export report.json
agent-qa analyze-newman report.json --max-failures 0 --sla-avg 500 --markdown pr_report.md
```

---

## 4. Verification Points & DoD

1. All endpoints and HTTP methods mapped to positive, boundary, and negative test scenarios.
2. Validation rules (min, max, pattern, required, enum) mapped to specific assertions.
3. Output matrix compiles into runnable API test skeletons (Pytest / Playwright).

---

## 5. Handoff Protocol

- **Deliverables:** API test matrix documentation and runnable API test suite skeletons.
- **Next Subagent:** api-engineer / test-runner
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
