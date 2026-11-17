---
name: manual-qa-and-rtm-bridge
description: Manual QA execution standards (ISO/IEC/IEEE 29119-2/3), bug reporting standards, automation candidate selection (ISTQB CTAL-TAE v2.0), RTM traceability bridge, and release go/no-go gates. Use when executing manual QA, logging bugs, selecting automation candidates, or converting manual test cases to automation scripts with RTM tags.
trigger: on_demand
profiles: [manual-qa, web-playwright, mobile-appium, api-pytest, katalon, full]
standards: [ISO/IEC/IEEE 29119-2/3, ISTQB CTAL-TAE v2.0]
category: test_automation_and_execution
version: "1.0.0"
policies:
  network: none
  shell: none
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

### 1. Chuẩn Thực Thi Manual QA (ISO/IEC/IEEE 29119-2/3)
#### A. Bug / Incident Report Standard
Mọi bug log ra bắt buộc đủ 6 trường:
- `Bug_ID` & `REQ_ID / TC_ID`: Liên kết ngược về yêu cầu và test case.
- `Severity` (Blocker/Critical/Major/Minor) & `Priority` (P0/P1/P2/P3).
- `Environment`: Build/Commit, OS/Browser/Device model, tài khoản test (đã che secret).
- `Steps to Reproduce`: Tối giản, tái hiện được 100%.
- `Expected vs Actual Result`: Đối chiếu trực tiếp với Acceptance Criteria.
- `Evidence`: Screenshot/Video + Console log / Network HAR / Request-Response (đã mask PII/JWT).

#### B. Regression Selection & UAT Sign-off
- **Regression Selection:** Khi có thay đổi code, chọn tối thiểu: (1) Smoke P0 toàn hệ thống + (2) Toàn bộ TC thuộc module bị sửa + (3) Các luồng phụ thuộc (Auth, Payment, DB state).
- **UAT / Test Cycle Sign-off:** Ghi nhận tổng số TC Executed / Passed / Failed / Blocked và danh sách Known Issues được chấp nhận trước khi đóng cycle.

### 2. Cầu Nối Manual → Automation (ISTQB CTAL-TAE v2.0)
#### A. Automation Candidate Selection Gate
Chỉ gắn cờ `Auto_Ready = YES` cho Manual Test Case đạt **>= 3/4** tiêu chí:
1. **Risk & Frequency:** Thuộc luồng P0/P1 hoặc chạy lặp lại ở mọi kỳ Regression.
2. **Stability:** UI/API đã ổn định, không đổi thiết kế liên tục trong sprint hiện tại.
3. **Deterministic:** Có dữ liệu cô lập (`synthetic-test-data-generator`) và kiểm chứng tự động được.
4. **ROI:** Chi phí viết + bảo trì thấp hơn thời gian chạy manual lặp lại.

#### B. Quy Tắc RTM Tagging Khi Sinh Code Automation
Khi `pom-crafter` chuyển đổi Manual TC sang code (Playwright, Pytest, Cypress, Appium, Katalon):
- **Bắt buộc giữ nguyên `TC_ID` và `REQ_ID`** trong tag/annotation:
  - Playwright/Cypress: `test('[REQ-102][TC-045] ...', { tag: ['@P0', '@REQ-102', '@TC-045'] }, ...)`
  - Pytest: `@pytest.mark.req("REQ-102")` và `@pytest.mark.tc("TC-045")`
  - Appium/Katalon: Metadata/comment `@TC_ID: TC-045 | @REQ_ID: REQ-102` ở đầu test case.
- **1-to-1 Traceability:** Mỗi `TC_ID` ánh xạ về 1 test function/spec rõ ràng để báo cáo CI/CD map được % coverage theo `REQ_ID`.

### 3. Release Go / No-Go Gate (Tổng Hợp Manual + Auto)
Chỉ cho phép Release khi đạt đồng thời:
- **100% P0 Test Cases Pass** (tổng hợp Manual + Auto).
- **0 Blocker / Critical Bug** đang mở.
- **0 Vi phạm Quality Gates** (Security, Performance SLA, 0-assert lint).

---

## 4. Verification Points & DoD

1. All manual bug reports contain all 6 mandatory ISO 29119-3 fields.
2. Automation candidates evaluated against all 4 CTAL-TAE criteria with >= 3/4 score.
3. Generated automation scripts retain RTM traceability tags linking back to REQ_ID and TC_ID.
4. Release sign-off requires 100% P0 pass rate and 0 open blocker defects.

---

## 5. Handoff Protocol

- **Deliverables:** Bug incident reports, RTM traceability matrices, candidate selection ledgers, and release sign-off checklists.
- **Next Subagent:** `pom-crafter` (for automation synthesis) or `quality-gatekeeper` (for release gate validation).
- **Output Format:** Markdown bug reports, Excel RTM matrices, and tagged test automation specifications.
