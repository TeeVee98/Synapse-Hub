---
name: manual-qa-and-rtm-bridge
description: Manual QA execution standards (ISO/IEC/IEEE 29119-2/3), bug reporting standards, automation candidate selection (ISTQB CTAL-TAE v2.0), RTM traceability bridge, and release go/no-go gates. Use when executing manual QA, logging bugs, selecting automation candidates, or converting manual test cases to automation scripts with RTM tags.
trigger: on_demand
profiles: [enterprise-rbt, manual-qa, web-playwright, mobile-appium, api-pytest, katalon, full]
standards: [ISO/IEC/IEEE 29119-2/3, ISTQB CTAL-TAE v2.0]
category: test_automation_and_execution
version: "1.0.0"
policies:
  network: none
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---

# Manual QA Execution, RTM Bridge & Release Gate

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation ('Use when...')

- **Trigger Clause:** Manual QA execution standards (ISO/IEC/IEEE 29119-2/3), bug reporting standards, automation candidate selection (ISTQB CTAL-TAE v2.0), RTM traceability bridge, and release go/no-go gates. Use when executing manual QA, logging bugs, selecting automation candidates, or converting manual test cases to automation scripts with RTM tags.
- **Activation Scope:** Domain workflows for manual QA execution, bug incident management, and test case to automation transformation across all supported tech stacks.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
  - Do NOT log incomplete bug reports lacking REQ_ID/TC_ID, expected vs actual result, or reproducible steps.
  - Do NOT automate unstable or non-deterministic test cases lacking synthetic data isolation.
  - Do NOT approve release if any P0 test case fails or blocker/critical defects remain open.
- **Sibling Skill Boundaries:**
  - `rbt-manual-testing` handles risk-based test matrix design; `manual-qa-and-rtm-bridge` handles manual execution standards, incident triage, and the RTM traceability bridge to automation.

---

## 3. Ordered Execution Workflow

### 1. Manual QA Execution Standard (ISO/IEC/IEEE 29119-2/3)
#### A. Bug / Incident Report Standard
Every logged defect must contain all 6 mandatory fields:
- `Bug_ID` & `REQ_ID / TC_ID`: Traceability back-links to the originating requirement and test case.
- `Severity` (`Blocker` / `Critical` / `Major` / `Minor`) & `Priority` (`P0` Critical / `P1` High / `P2` Medium / `P3` Low).
- `Environment`: Build/Commit SHA, OS/Browser/Device model, and masked test account (never include raw secrets).
- `Steps to Reproduce`: Minimal, deterministic steps with 100% reproducibility.
- `Expected vs Actual Result`: Direct comparison against Acceptance Criteria.
- `Evidence`: Screenshot/Video + Console log / Network HAR / Request-Response (with PII/JWT redacted).

#### B. Regression Selection & UAT Sign-off
- **Regression Selection:** On any code change, execute at minimum: (1) System-wide P0 Smoke suite + (2) All test cases in the modified module + (3) Dependent critical flows (Auth, Payment, DB state).
- **UAT / Test Cycle Sign-off:** Record total Executed / Passed / Failed / Blocked test cases and the approved Known Issues register before closing the cycle.

### 2. Manual -> Automation Bridge (ISTQB CTAL-TAE v2.0)
#### A. Automation Candidate Selection Gate
Flag `Auto_Ready = YES` only for Manual Test Cases satisfying **>= 3/4** criteria:
1. **Risk & Frequency:** Belongs to P0/P1 critical paths or runs repeatedly in every Regression cycle.
2. **Stability:** UI/API contract is stable and not undergoing breaking sprint redesigns.
3. **Deterministic:** Supports isolated test data (`synthetic-test-data-generator`) and deterministic automated assertions.
4. **ROI:** Authoring and maintenance cost is lower than repeated manual execution effort.

#### B. RTM Tagging Rules During Automation Synthesis
When `pom-crafter` or `tools/design/testcase_transpiler.py` converts Manual TCs into automated scripts (Playwright, Pytest, Cypress, Appium, Katalon):
- **Preserve `TC_ID` and `REQ_ID`** in tags/annotations:
  - Playwright/Cypress: `test('[REQ-102][TC-045] ...', { tag: ['@P0', '@REQ-102', '@TC-045'] }, ...)`
  - Pytest: `@pytest.mark.req("REQ-102")` and `@pytest.mark.tc("TC-045")`
  - Appium/Katalon: Header metadata/comment `@TC_ID: TC-045 | @REQ_ID: REQ-102` at the top of the test case.
- **1-to-1 Traceability:** Each `TC_ID` maps to one explicit test function/spec so CI/CD reports can compute requirement coverage % per `REQ_ID`.

##### Playwright RTM Example:
<!-- classification: illustrative -->
```typescript
// Attach RTM tags linking directly to REQ_ID and TC_ID
test('[REQ-102][TC-045] Verify checkout calculation with discount', {
  tag: ['@P0', '@REQ-102', '@TC-045'],
}, async ({ checkoutPage }) => {
  await checkoutPage.applyCoupon('DISCOUNT10');
  await checkoutPage.assertTotalWithDiscount();
});
```

##### Pytest RTM Example:
<!-- classification: illustrative -->
```python
# Attach RTM decorators linking REQ_ID and TC_ID
@pytest.mark.p0
@pytest.mark.req("REQ-102")
@pytest.mark.tc("TC-045")
def test_checkout_discount_calculation(checkout_client):
    res = checkout_client.apply_coupon("DISCOUNT10")
    assert res.total_discounted == 90.0
```

#### C. Bound Hub CLI Automations (Bug Reporting, ALM Sync & Transpilation)
<!-- classification: illustrative -->
```bash
# 1. Generate RCA-classified Jira/Markdown bug report from failure evidence
python tools/report/bug_reporter.py --test-id TC-045 --title "Checkout discount mismatch" --error "AssertionError: expected 90.0" --format jira

# 2. Push defect or sync JUnit XML execution results to Jira/Xray/TestRail (use --dry-run offline)
python tools/alm/alm_bridge.py push-bug --summary "Checkout discount mismatch" --trace "AssertionError: expected 90.0" --dry-run
python tools/alm/alm_bridge.py sync-exec --report reports/junit.xml --platform xray --dry-run

# 3. Transpile Manual TC Markdown into Clean POM Playwright spec
python tools/design/testcase_transpiler.py path/to/manual_tcs.md --out tests/generated/
```

### 3. Release Go / No-Go Gate (Unified Manual + Automated)
Approve Release ONLY when all criteria pass simultaneously:
- **100% P0 Test Cases Pass** (combined Manual + Automated suites).
- **0 Open Blocker / Critical Defects** (`P0` / `Blocker` / `Critical` count = 0).
- **0 Quality Gate Violations** (Security, Performance SLA, 0-assert lint).

### 4. Section 5 — Test Execution & Exit Report (ISO/IEC/IEEE 29119-3)
Standard release closure and sign-off deliverable (Release Exit Report). When closing a test cycle, include all 4 mandatory sections:

#### A. Execution Summary Table
| Metric | Count | Percentage | Notes |
| :--- | :---: | :---: | :--- |
| **Total Test Cases** | 0 | 100.0% | Total test cases in cycle scope |
| **Passed** | 0 | 0.0% | Test cases meeting expected outcomes |
| **Failed** | 0 | 0.0% | Test cases failing with linked defect IDs |
| **Blocked** | 0 | 0.0% | Blocked by environment or upstream defect |
| **Skipped** | 0 | 0.0% | Deferred outside current release scope |
| **Untested** | 0 | 0.0% | Remaining unexecuted test cases |
| **Execution Rate** | — | **0.0%** | `(Passed + Failed + Blocked) / Total * 100%` |
| **Pass Rate** | — | **0.0%** | `Passed / Total * 100%` (or `Passed / Executed`) |

#### B. Defect Severity & Priority Breakdown Table
| Severity / Priority Tier | Open | Fixed | Deferred | Total Logged |
| :--- | :---: | :---: | :---: | :---: |
| **Blocker / Critical (`P0`)** | 0 | 0 | 0 | 0 |
| **Major / High (`P1`)** | 0 | 0 | 0 | 0 |
| **Medium (`P2`)** | 0 | 0 | 0 | 0 |
| **Low / Minor (`P3`)** | 0 | 0 | 0 | 0 |
| **Total Defects** | **0** | **0** | **0** | **0** |

#### C. Quality Metrics & Residual Risks
- **Defect Removal Efficiency (DRE):** `DRE = Defect_pre_release / (Defect_pre_release + Defect_post_release) * 100%` (Quality target: >= 90%).
- **Defect Leakage:** `Leakage = Defect_escaped / Defect_total * 100%` (Quality target: <= 5%).
- **Residual Risks:**
  1. `[RISK-01]`: Describe unresolved risk prior to release, business impact, and mitigation/hotfix fallback plan.
  2. `[RISK-02]`: Flows with partial coverage due to staging data or third-party sandbox constraints.

#### D. Sign-off Matrix (Release Approval Record)
| Role | Name / Title | Decision | Signature / Confirmation | Date (YYYY-MM-DD) |
| :--- | :--- | :---: | :--- | :---: |
| **QA Lead** | | `[ ] GO  [ ] NO-GO` | | |
| **Dev Lead** | | `[ ] GO  [ ] NO-GO` | | |
| **PO / PM** | | `[ ] GO  [ ] NO-GO` | | |

---

### 5. Section 6 — Session-Based Test Management (SBTM) Charter Sheet
Standardized framework for managing and recording Exploratory Testing sessions (paired directly with `tot-exploratory-testing`):

#### A. Charter Metadata & Mission
- **Charter ID:** `SBTM-YYYYMMDD-<MODULE>-<SESSION#>`
- **Mission Statement:** Explore `<Module Name>` focusing on `<Risk Vector / Charter Angle>` to uncover hidden functional and non-functional defects.
- **Timebox:** 60-90 minutes (standard: 75 minutes). Do not exceed 90 minutes to maintain focused coverage.
- **Build / Environment:** Staging vX.Y.Z (Commit SHA: ...), OS: macOS / Windows 11, Browser: Chrome / Safari v...
- **Tester:** Assigned QA Engineer executing the session.

#### B. Areas & Risk Vectors Tested
- Enumerate business workflows, screens, API endpoints, and risk vectors explored:
  - Functional flows: Happy path, input boundary values, edge-case payloads.
  - Non-functional / Attack vectors: Concurrency, double-submit, network throttling (3G), invalid session / multi-tab state.

#### C. Test Notes, Heuristics & Oracles
- Record session observations, verified assumptions, and comparison oracles:
  - Applied heuristics: Boundary Value, Consistency with Past/Competitors, Goldfish spec cross-check.
  - Observed behavior: UI latency, tooltip rendering, special Unicode/emoji handling.

#### D. Bugs & Issues Logged
| Bug_ID | Severity | Summary & Root Observation | Linked REQ / Screen | Status |
| :--- | :---: | :--- | :--- | :---: |
| `BUG-XXX` | Major | Concise defect summary discovered during session | Screen / Module | Open |

#### E. Task Breakdown Split (SBTM Effort Metrics)
- **Session Setup %:** 10% - 15% (test accounts, data seeding, network proxy/throttling setup).
- **Test Execution %:** 65% - 75% (active exploration, state manipulation, oracle verification).
- **Bug Investigation %:** 15% - 20% (repro isolation, HAR/console log capture, ticket filing).

#### F. Debrief & Follow-ups
- **Debrief Notes:** Summary of post-session review between Tester and QA Lead.
- **Next Actions:** Propose follow-up charters or promote high-value scenarios into regression suites via `rbt-manual-testing` / `pom-crafter`.

---

## 4. Verification Points & DoD

1. All manual bug reports contain all 6 mandatory ISO 29119-3 fields.
2. Automation candidates evaluated against all 4 CTAL-TAE criteria with >= 3/4 score.
3. Generated automation scripts retain RTM traceability tags linking back to REQ_ID and TC_ID.
4. Release sign-off requires 100% P0 pass rate and 0 open blocker defects.
5. Exit Report contains complete execution metrics, defect breakdown, DRE/leakage indicators, residual risks, and empty sign-off blocks.
6. SBTM Charter sheet conforms to standard session-based test reporting format with task breakdown percentages and debrief records.

---

## 5. Handoff Protocol

- **Deliverables:** Bug incident reports, RTM traceability matrices, candidate selection ledgers, and release sign-off checklists.
- **Next Subagent:** `pom-crafter` (for automation synthesis) or `quality-gatekeeper` (for release gate validation).
- **Output Format:** Markdown bug reports, Excel RTM matrices, and tagged test automation specifications.
