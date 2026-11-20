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

##### Playwright RTM Example:
<!-- classification: illustrative -->
```typescript
// Gắn RTM Tagging liên kết trực tiếp REQ_ID và TC_ID
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
# Gắn RTM Decorators liên kết REQ_ID và TC_ID
@pytest.mark.p0
@pytest.mark.req("REQ-102")
@pytest.mark.tc("TC-045")
def test_checkout_discount_calculation(checkout_client):
    res = checkout_client.apply_coupon("DISCOUNT10")
    assert res.total_discounted == 90.0
```

### 3. Release Go / No-Go Gate (Tổng Hợp Manual + Auto)
Chỉ cho phép Release khi đạt đồng thời:
- **100% P0 Test Cases Pass** (tổng hợp Manual + Auto).
- **0 Blocker / Critical Bug** đang mở.
- **0 Vi phạm Quality Gates** (Security, Performance SLA, 0-assert lint).

### 4. Section 5 — Test Execution & Exit Report (ISO/IEC/IEEE 29119-3)
Chuẩn báo cáo đóng kỳ kiểm thử và bàn giao phát hành (Release Exit Report). Khi tổng kết đợt kiểm thử, bắt buộc lập đầy đủ 4 thành phần:

#### A. Execution Summary Table
| Metric | Count | Percentage | Ghi Chú |
| :--- | :---: | :---: | :--- |
| **Total Test Cases** | 0 | 100.0% | Tổng số test cases trong phạm vi kỳ test |
| **Passed** | 0 | 0.0% | Số test cases đạt kết quả mong đợi |
| **Failed** | 0 | 0.0% | Số test cases không đạt (có bug kèm theo) |
| **Blocked** | 0 | 0.0% | Bị chặn do môi trường hoặc bug phụ thuộc |
| **Skipped** | 0 | 0.0% | Tạm hoãn ngoài phạm vi release này |
| **Untested** | 0 | 0.0% | Chưa kịp thực thi |
| **Execution Rate** | — | **0.0%** | `(Passed + Failed + Blocked) / Total * 100%` |
| **Pass Rate** | — | **0.0%** | `Passed / Total * 100%` (hoặc `Passed / Executed`) |

#### B. Defect Severity Breakdown Table
| Severity Tier | Open | Fixed | Deferred | Total Logged |
| :--- | :---: | :---: | :---: | :---: |
| **Blocker / Critical (P0)** | 0 | 0 | 0 | 0 |
| **Major / High (P1)** | 0 | 0 | 0 | 0 |
| **Medium (P2)** | 0 | 0 | 0 | 0 |
| **Low / Trivial (P3)** | 0 | 0 | 0 | 0 |
| **Total Defects** | **0** | **0** | **0** | **0** |

#### C. Quality Metrics & Residual Risks
- **Defect Removal Efficiency (DRE):** `DRE = Defect_pre_release / (Defect_pre_release + Defect_post_release) * 100%` (Mục tiêu chất lượng: ≥ 90%).
- **Defect Leakage:** `Leakage = Defect_escaped / Defect_total * 100%` (Mục tiêu chất lượng: ≤ 5%).
- **Residual Risks (Rủi ro tồn đọng):**
  1. `[RISK-01]`: Mô tả rủi ro còn tồn đọng trước release, mức độ ảnh hưởng và phương án xử lý giảm thiểu (fallback / hotfix plan).
  2. `[RISK-02]`: Các luồng chưa được kiểm thử toàn diện do hạn chế dữ liệu môi trường staging.

#### D. Sign-off Matrix (Biên bản phê duyệt phát hành)
| Role | Name / Title | Decision | Signature / Confirmation | Date (YYYY-MM-DD) |
| :--- | :--- | :---: | :--- | :---: |
| **QA Lead** | | `[ ] GO  [ ] NO-GO` | | |
| **Dev Lead** | | `[ ] GO  [ ] NO-GO` | | |
| **PO / PM** | | `[ ] GO  [ ] NO-GO` | | |

---

### 5. Section 6 — Session-Based Test Management (SBTM) Charter Sheet
Khung chuẩn quản lý và ghi nhận phiên Exploratory Testing (kết nối trực tiếp với `tot-exploratory-testing`):

#### A. Charter Metadata & Mission
- **Charter ID:** `SBTM-YYYYMMDD-<MODULE>-<SESSION#>`
- **Mission Statement:** Khám phá chức năng và đánh giá các rủi ro phi chức năng trên module `<Tên Module>` theo hướng `<Góc thử nghiệm>` nhằm phát hiện khiếm khuyết tiềm ẩn.
- **Timebox:** 60–90 phút (tiêu chuẩn: 75 phút). Không kéo dài quá 90 phút để đảm bảo sự tập trung cao độ.
- **Build / Environment:** Staging vX.Y.Z (Commit SHA: ...), OS: macOS / Windows 11, Browser: Chrome / Safari v...
- **Tester:** Tên QA / Tester thực hiện session.

#### B. Areas & Risk Vectors Tested
- Liệt kê các luồng nghiệp vụ, màn hình, API endpoints và các vector rủi ro được khảo sát:
  - Functional flow: Happy path, input boundary, edge data.
  - Non-functional / Attack vectors: Concurrency, double-submit, network lag (3G throttling), invalid session / multi-tab state.

#### C. Test Notes, Heuristics & Oracles
- Ghi chép chi tiết diễn biến, các giả định đã kiểm chứng và oracles đối soát:
  - Heuristics áp dụng: Boundary Value, Consistency with Past/Competitors, Goldfish spec cross-check.
  - Quan sát thực tế: Độ trễ UI, hành vi tooltip, phản hồi khi nhập ký tự Unicode đặc biệt.

#### D. Bugs & Issues Logged
| Bug_ID | Severity | Summary & Root Observation | Linked REQ / Screen | Status |
| :--- | :---: | :--- | :--- | :---: |
| `BUG-XXX` | Major | Mô tả ngắn gọn lỗi phát hiện trong session | Screen / Module | Open |

#### E. Task Breakdown Split (SBTM Effort Metrics)
- **Session Setup %:** 10% – 15% (chuẩn bị tài khoản test, seed dữ liệu, cấu hình network proxy/throttling).
- **Test Execution %:** 65% – 75% (thực tế khám phá, biến tấu thao tác, đối soát oracles).
- **Bug Investigation %:** 15% – 20% (cô lập bước tái hiện, trích xuất HAR/console log, log ticket).

#### F. Debrief & Follow-ups
- **Debrief Notes:** Tóm tắt thảo luận giữa Tester và QA Lead ngay sau phiên test.
- **Next Actions:** Đề xuất mở rộng charter tiếp theo hoặc chuyển đổi các test case giá trị cao sang kịch bản hồi quy trong `rbt-manual-testing` / `pom-crafter`.

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
