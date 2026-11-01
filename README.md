# 🧠 Synapse Hub — AI Test Quality Linter & Guardrails for Automated Testing
### *Bộ Linter & Chốt Chặn Chất Lượng Test Dành Cho Thời Đại AI Viết Code*

[🇻🇳 Tiếng Việt](README.md) | [🇬🇧 English Edition](README.en.md)

> **Định vị cốt lõi:** Bộ Linter & Guardrails độc lập (zero external dependencies cho core engine & DoD gates) bảo vệ độ tin cậy của test suite khi AI viết code — Bắt đứng test "pass ảo" (0 assert, tautology), triệt tiêu sleep cứng, nén 95% log CI/CD, và chuẩn hóa cấu trúc Clean POM. Các tính năng nâng cao (xuất bảng Excel chuẩn doanh nghiệp, so sánh ảnh Canvas) sử dụng thư viện mở rộng tùy chọn (`openpyxl`, `Pillow`).  
> **Module mở rộng:** Sẵn sàng kết nối 37 kỹ năng QA chuyên sâu, 6 vai trò AI Swarm và 9 Cổng kiểm định DoD hỗ trợ Playwright, Cypress, Pytest và Katalon.  
> **Tác giả:** Thế Vị ([@TeeVee998](https://github.com/TeeVee998))  
> **Phiên bản Hub:** `v2.3.0` | **Quy mô:** 37 Kỹ năng chuẩn hóa, 6 Vai trò AI Agent, 60+ Công cụ và tiện ích Python, 9 Cổng kiểm định DoD.

[![npm version](https://img.shields.io/npm/v/synapse-hub.svg?style=flat-square&color=blue)](https://www.npmjs.com/package/synapse-hub)
[![node version](https://img.shields.io/badge/node-%3E%3D16.0.0-brightgreen.svg?style=flat-square)](https://nodejs.org)
[![license](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](https://github.com/TeeVee998/Synapse-Hub/blob/main/LICENSE)

---

## ⚡ 1. Trải Nghiệm Nhanh Trong 60 Giây (3 Tính Năng Cốt Lõi 🚀)

Không cần đọc hàng chục tài liệu hay cấu hình phức tạp. Bạn có thể sử dụng ngay 3 tính năng cốt lõi sau để giải quyết trực tiếp nỗi đau kiểm thử hàng ngày:

### 🔍 1. Bắt Test "Pass Ảo", Sleep Cứng & Nuốt Lỗi
```bash
npx synapse-hub lint ./tests
```
* **Vấn đề:** AI viết test thường tạo ra các bài test chạy pass bề ngoài nhưng không kiểm tra gì (0 assert), dùng `Thread.sleep` làm test chậm và flaky, hoặc dùng `try-catch` rỗng nuốt lỗi.
* **Giải pháp:** Phân tích tĩnh heuristic & AST đa ngôn ngữ (Playwright TypeScript/JavaScript, Pytest Python, Cypress, Groovy/Katalon), phát hiện và báo lỗi ngay lập tức mà không tốn token gọi API LLM.

### 📊 2. Chuyển Kịch Bản Sang Bảng Excel Doanh Nghiệp Chuẩn 12 Cột
```bash
npx synapse-hub export-excel
```
* **Vấn đề:** Tester tốn nhiều giờ định dạng bảng tính Excel thủ công từ User Story hoặc kịch bản Markdown.
* **Giải pháp:** Chuyển đổi tự động kịch bản thành file Excel `.xlsx` chuẩn 12 cột, có sẵn ma trận rủi ro P × I, định dạng màu sắc chuyên nghiệp sẵn sàng gửi cho khách hàng và PM.

### 🧹 3. Nén 95% Log CI Thừa — Lấy Đúng Root Cause
```bash
npx synapse-hub distill path/to/ci.log
```
* **Vấn đề:** Log build CI/CD dài hàng chục ngàn dòng làm tràn context của AI hoặc khiến kỹ sư mỏi mắt tìm dòng lỗi.
* **Giải pháp:** Lọc bỏ 95% nhiễu thông tin, cô đọng lại ~30 dòng chứa đúng stacktrace, mã lỗi và kịch bản thất bại.

---

## 🚀 2. Khởi Động Nhanh & Lựa Chọn Cài Đặt (Onboarding Thân Thiện)

Synapse Hub tôn trọng sự riêng tư và cấu hình của bạn. Bạn luôn có toàn quyền kiểm soát những gì được ghi vào hệ thống:

```bash
# 🩺 Chẩn đoán môi trường hệ thống chỉ với 1 lệnh (Kiểm tra Node, Python, Chrome, Git):
npx synapse-hub doctor

# 🔹 Cách 1: Cấu hình chỉ trong dự án hiện tại (An toàn nhất, không can thiệp vào ~/.gemini)
npx synapse-hub setup --local-only

# 🔹 Cách 2: Xem trước các thay đổi giả lập (Dry-Run, không ghi đè bất kỳ file nào)
npx synapse-hub setup --dry-run

# 🔹 Cách 3: Cài đặt đầy đủ (Tạo PROJECT_AI_GUIDE.md, AI Bridges và Plugin toàn cục)
npx synapse-hub setup

# 🔹 Gỡ cài đặt hoàn toàn bất kỳ lúc nào:
npx synapse-hub uninstall
```

### Chạy kiểm định 9 Cổng Chất Lượng (DoD Gates):
```bash
npx synapse-hub verify         # Kiểm tra 9 Cổng Chất Lượng DoD (Gate 0–8)
npx synapse-hub analyze        # Báo cáo sức khỏe dự án (PROJECT_HEALTH_REPORT.md)
```

| Cổng | Tên cổng kiểm soát | Mục tiêu kiểm định thực tế |
| :---: | :--- | :--- |
| **Gate 0** | **Bảo Toàn Tác Quyền & MIT** | Xác thực nguồn gốc tác quyền Thế Vị (@TeeVee998) theo MIT License. |
| **Gate 1** | **Mã Hóa UTF-8 No BOM** | Quét sạch 100% byte BOM và lỗi vỡ ký tự mojibake trên toàn repository. |
| **Gate 2** | **Khả Chuyển Đường Dẫn** | Cấm đường dẫn tuyệt đối gắn với máy trạm cá nhân (`/Users/...`, `C:\...`). |
| **Gate 3** | **Kiến Trúc Clean POM Phẳng** | Đóng gói 100% locator vào Page Class, cấm raw XPath/CSS trong kịch bản test. |
| **Gate 4** | **Chống Lệch Tài Liệu AI** | Đối chiếu AST thực tế với `PROJECT_AI_GUIDE.md`, loại bỏ PageClass ảo. |
| **Gate 5** | **Danh Sách Đen File Tạm** | Chặn rò rỉ file rác (`*.tmp`, memory dump, cache thừa) làm bẩn workspace. |
| **Gate 6** | **Bảo Vệ Bí Mật & Mật Khẩu** | Quét chặn plaintext password, private keys hoặc API token lưu cứng trong code. |
| **Gate 7** | **Lưới Lọc Lỗi Tĩnh & Fake-Pass** | Phân tích tĩnh heuristic bắt đứng test 0 assertion, catch nuốt ngoại lệ, sleep cứng (≥ 3000ms hoặc gán biến), unawaited expect. |
| **Gate 8** | **Đột Biến Cú Pháp (Micro-Mutation)** | Đánh giá độ nhạy assertion qua đột biến cú pháp liên kết dataflow (Score ≥ 80%). |

---

## 🎯 3. Lộ Trình Theo Trình Độ (Tailored For Every Level)

| Trình độ | Điều bạn cần | Điểm chạm phù hợp trong Synapse Hub |
| :--- | :--- | :--- |
| **Fresher / Junior** | Học nhanh, ra việc ngay, hiểu vì sao test yếu | • `agent-qa export-excel`: Tạo test case chuẩn chỉnh.<br/>• `agent-qa lint`: Giải thích vì sao assert yếu hoặc pass ảo.<br/>• Tham khảo mẫu Clean POM chuẩn trong `examples/practices/`. |
| **Mid-Level** | Bớt flaky, giảm chi phí bảo trì locator | • `agent-qa flaky`: Dò tìm test chập chờn và phân nhóm cách ly.<br/>• `agent-qa heal`: Gợi ý thay thế locator hỏng qua phân tích cây AOM.<br/>• Tích hợp linter vào pre-commit hook. |
| **Senior / Lead** | Đo lường, kiểm soát chất lượng, an toàn CI/CD | • `agent-qa verify`: 9 Cổng chất lượng DoD tự động trong CI.<br/>• `agent-qa mutate`: Kiểm tra độ nhạy của assertion trước khi merge PR.<br/>• Báo cáo chuẩn Markdown/JSON dễ dàng gắn vào GitHub Actions/GitLab CI. |

---

## 💎 4. Kiến Trúc & Các Trụ Cột Kỹ Thuật

```mermaid
flowchart TD
    subgraph Hub["🧠 Synapse Hub (Core v2.3.0)"]
        Skills[".agents/skills/ (37 Skills)"]
        Agents[".agents/agents/ (6 Specialized Roles)"]
        Rules[".agents/rules/ (11 Core Rules)"]
        Tools["tools/ (60+ Universal Python Tools)"]
        Workflows[".agents/workflows/ (10 Workflows)"]
    end

    subgraph ChatSession["💬 AI Agent Workspace / IDE"]
        Hub -->|Mount / Plugins| ChatSession
    end

    subgraph Projects["📁 Dự Án Kiểm Thử Mục Tiêu"]
        ProjectA["Playwright (TS/JS)"]
        ProjectB["Pytest (Python)"]
        ProjectC["Cypress / Katalon"]
    end

    ProjectA -->|Verify & Lint| ChatSession
    ProjectB -->|Verify & Lint| ChatSession
    ProjectC -->|Verify & Lint| ChatSession
```

### 🧠 Trụ cột 1: Chống Pass Ảo & Kiểm Tra Độ Nhạy Assertion (Heuristic)
- **Static Defect Sentinel (`tools/infer_linter.py`):** Dò tìm các mẫu phản-quy-chuẩn như test không có assert, catch nuốt ngoại lệ, sleep cứng, unawaited Playwright assertions. Đạt độ chính xác cao trên tập benchmark mẫu.
- **Assertion Sensitivity Sentinel (`tools/micro_mutator.py`):** Tiêm đột biến cú pháp nhẹ (đảo toán tử so sánh, đảo logic boolean) để kiểm tra xem các assertion bên dưới có bắt được lỗi hay không. Bắt buộc độ nhạy assertion ≥ 80% để pass Gate 8.

### ⚡ Trụ cột 2: Tối Ưu Hóa Ngữ Cảnh & Tiết Kiệm Token
- **Lọc Log Thông Minh (`tools/distill_log.py`):** Rút gọn log CI cồng kềnh, đưa đúng thông tin stacktrace vào context của LLM.
- **AST Method Mapping (`tools/repo_map.py`):** Quét chữ ký hàm và cấu trúc lớp Page Object vào bản đồ nén < 600 tokens; agent không cần đọc toàn bộ mã nguồn lớn.
- **Bộ Nhớ Lỗi Cục Bộ (`tools/cache_resolver.py`):** Lưu trữ kinh nghiệm sửa lỗi ngoại tuyến vào SQLite tại `~/.agent_memory/global_cache.db` (truy xuất 0 token).

---

## ⚖️ 5. So Sánh Minh Bạch & Giới Hạn Kỹ Thuật Đã Biết (Comparison & Limitations)

### 📊 Bảng so sánh với các công cụ hiện có trong ngành

| Tiêu chí / Giải pháp | ESLint Plugin (Playwright) | Stryker Mutator | Allure Report | Healenium | Synapse Hub 🧠 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Phạm vi ngôn ngữ** | Chỉ JS / TS | JS / TS, C#, Scala | Mọi ngôn ngữ (nhận XML) | Java / Python / C# (Selenium) | **Đa ngôn ngữ** (TS/JS, Python, Groovy, Java) |
| **Tích hợp sâu trong Agent Context** | ❌ (Chỉ chạy CLI/IDE) | ❌ (Chạy độc lập) | ❌ (Viewer sau test) | ❌ (Proxy trung gian) | ✅ **NATIVE** (Rule, MCP, Prompt Context, 6 Subagents) |
| **Diệt Fake-Pass do AI sinh ra** | ⚠️ Hạn chế (chỉ check lint cú pháp) | ❌ Không (chỉ đột biến code app) | ❌ Không | ❌ Không | ✅ **Chuyên biệt** (AST nhận diện 0 assert, try-catch nuốt lỗi, tautology) |
| **Thời gian chạy Mutation Check** | N/A | ⏱️ Chậm (vài phút đến hàng giờ) | N/A | N/A | ⚡ **Siêu tốc (~0.1s)** với AST Micro-Mutator trước khi commit |
| **Tự chữa Locator (Self-Healing)** | ❌ | ❌ | ❌ | ⚠️ Cần Server JVM + Docker proxy | ⚡ **Nhẹ (< 500 tokens)** dựa trên AOM Diffing trong luồng Agent |
| **Tiết kiệm Token & Lọc Log CI** | ❌ | ❌ | ❌ | ❌ | ✅ **Cắt giảm 95%** log thừa (`distill_log.py`, `repo_map.py`) |
| **Bảo vệ chuẩn kiến trúc Clean POM** | ❌ | ❌ | ❌ | ❌ | ✅ **Bắt buộc Clean POM**, Flat Architecture, cấm selector trong script |

### ⚠️ Giới hạn kỹ thuật đã biết (Known Limitations)

Để duy trì tính minh bạch kỹ thuật (**Truth Anchor**), Synapse Hub công khai các giới hạn thực tế:

1. **Assertion Sensitivity là Heuristic Cú Pháp, không phải Compiler-Grade Mutation Testing:**  
   Công cụ `tools/micro_mutator.py` sử dụng phương pháp phân tích cú pháp tĩnh nhanh (regex/token pattern) để đánh giá sự hiện diện và độ nhạy của các câu lệnh assert xuôi dòng. Nó **không thay thế** các công cụ kiểm thử đột biến cấp runtime biên dịch (như Stryker cho JS/TS hoặc mutmut cho Python). Khi dự án yêu cầu báo cáo Mutation Testing chuẩn công nghiệp cho toàn bộ runtime, hãy sử dụng các công cụ chuyên dụng tương ứng.
2. **Benchmark Nội Bộ:**  
   Các chỉ số đo lường trong benchmark đi kèm được thực hiện trên bộ dữ liệu corpus chuẩn hóa nội bộ của Hub nhằm xác minh hoạt động của rule. Trên các dự án thực tế, hiệu quả thực thi phụ thuộc vào framework, cấu trúc mã nguồn và chất lượng test sẵn có của bạn.
3. **Ưu Tiên Hệ Sinh Thái Phổ Biến:**  
   Hệ thống ưu tiên hỗ trợ các framework tiêu chuẩn hiện đại: **Playwright, Pytest, Cypress, Selenium**. Các framework đặc thù doanh nghiệp như Katalon Studio/Groovy được hỗ trợ thông qua adapter chuyên biệt.
4. **Yêu Cầu Môi Trường Headless Browser:**  
   Các tính năng khảo sát trực tiếp live DOM/AOM và self-healing locator yêu cầu môi trường có cài đặt trình duyệt headless (như Playwright Chromium) để trích xuất cây khả năng truy cập (Accessibility Object Model).

---

## 👥 6. Hệ Thống Multi-Agent Swarm (6 Vai Trò Chuyên Biệt)

| Vai Trò Subagent | Trách Nhiệm Cốt Lõi | Kỹ Năng Tiêu Biểu | Công Cụ Đi Kèm |
| :--- | :--- | :--- | :--- |
| **`orchestrator`** | Trưởng nhóm điều phối, bootstrap dự án, audit sức khỏe, neo state. | `agent-orchestration`, `graphify`, `architecture-decision-records` | `setup_project.py`, `analyze_project.py`, `repo_map.py` |
| **`live-explorer`** | Thám sát live DOM/AOM qua Playwright headless, tường lửa chống click phá hoại. | `playwright-live-interaction`, `self-healing-locator`, `visual-regression-sentinel` | `safety_firewall.py`, `browser_helpers.js` |
| **`pom-crafter`** | Kỹ sư Clean POM, kiểm tra breaking change API, sinh test từ User Story. | `clean-pom-crafter`, `lam-script-generator`, `synthetic-test-data-generator` | `generate_tc_from_story.py`, `api_drift_sentinel.py` |
| **`test-runner`** | Quản lý chạy test headless CLI, chia tải song song CI, lọc log thông minh. | `katalon-cli-runner`, `e2e-testing-patterns`, `flaky-test-sentinel-and-quarantine` | `matrix_sharder.py`, `distill_log.py`, `pinpoint_failure.py` |
| **`failure-analyst`** | Giám định thất bại, trích xuất nguyên nhân gốc rễ (RCA), đề xuất vá lỗi locator. | `failure-autopsy-and-healing`, `token-and-context-optimizer` | `auto_heal.py`, `bug_reporter.py`, `cache_resolver.py` |
| **`quality-gatekeeper`**| Sentinel gác cổng, kiểm định 9 Cổng Chất Lượng DoD và độ nhạy assertion. | `antigravity-test-sentinel`, `wcag-audit-patterns`, `security-dast-sentinel` | `verify_all.py`, `micro_mutator.py`, `infer_linter.py` |

---

## 📦 7. Danh Mục 37 Kỹ Năng Chuẩn Hóa (.agents/skills/)

<details open>
<summary><b>📦 Bấm để xem: Danh Mục 37 Kỹ Năng Chuẩn Hóa</b></summary>

| # | Mã Kỹ Năng | Mô Tả Thực Chiến |
|:---:|---|---|
| 1 | `clean-pom-crafter` | Thiết kế Page Classes chuẩn Clean POM & Flat Architecture (zero locator trong test script). |
| 2 | `playwright-live-interaction` | Thám sát DOM/AOM sống, kiểm định selector < 200ms qua Playwright Headless. |
| 3 | `failure-autopsy-and-healing` | Khám nghiệm lỗi từ JUnit XML/Screenshot, tự động vá locator gãy. |
| 4 | `antigravity-test-sentinel` | Sentinel gác cổng chất lượng, chặn pass ảo và ép tuân thủ 9 cổng DoD. |
| 5 | `token-and-context-optimizer` | Tối ưu hóa prompt context, cô đọng log và chống suy giảm ngữ cảnh (Context Rot). |
| 6 | `flaky-test-sentinel-and-quarantine` | Phát hiện test chập chờn, tính điểm flakiness và quản lý vòng đời cách ly. |
| 7 | `api-spec-to-e2e-matrix` | Chuyển đổi đặc tả OpenAPI/Swagger thành ma trận kiểm thử E2E (Happy, Boundary, Fault). |
| 8 | `api-network-mocking-interception` | Chặn bắt traffic HTTP/GraphQL, giả lập route và tiêm lỗi mạng hỗn loạn (chaos testing). |
| 9 | `synthetic-test-data-generator` | Sinh dữ liệu kiểm thử giả lập, chống trùng lặp khóa chính trong cơ sở dữ liệu. |
| 10 | `db-state-verifier-and-seeder` | Khởi tạo dữ liệu mẫu cô lập và kiểm tra biến đổi DB qua SQL/NoSQL. |
| 11 | `visual-regression-sentinel` | So sánh ảnh chụp màn hình phát hiện lệch pixel với cơ chế che chắn ảnh động (anti-flake mask). |
| 12 | `wcag-audit-patterns` | Kiểm toán khả năng tiếp cận theo tiêu chuẩn WCAG 2.2 A/AA và vai trò ARIA. |
| 13 | `security-dast-sentinel` | Kiểm tra bảo mật động DAST: OWASP Top 10, tiêu đề bảo mật, rò rỉ token và IDOR. |
| 14 | `web-vitals-and-performance-profiler` | Đo lường Core Web Vitals (LCP, CLS, INP) và thác mạng (network waterfall) qua CDP. |
| 15 | `backend-load-and-stress-patterns` | Điều phối kịch bản tải k6, Locust và Apache JMeter đo lường SLA chịu tải. |
| 16 | `auth-session-and-cookie-manager` | Quản lý phiên đăng nhập `storageState`, JWT token và trạng thái đa vai trò. |
| 17 | `file-and-report-validator` | Kiểm tra tính toàn vẹn của tệp tải về/tải lên (Excel, CSV, PDF) so với schema. |
| 18 | `e2e-testing-patterns` | Thiết kế kiến trúc kiểm thử E2E đa trình duyệt, chia tải song song và quản trị retry. |
| 19 | `lam-script-generator` | Chuyển đổi User Story và tiêu chí chấp nhận thành kịch bản kiểm thử tự động. |
| 20 | `katalon-cli-runner` | Điều phối chạy kiểm thử Katalon/Gradle headless với cơ chế tự dọn driver. |
| 21 | `bats-testing-patterns` | Kiểm thử shell script, công cụ CLI và pipeline CI/CD bằng Bats. |
| 22 | `code-refactoring-refactor-clean` | Khử nợ kỹ thuật, tái cấu trúc mã kiểm thử theo nguyên lý SOLID & Clean Code. |
| 23 | `agent-orchestration-multi-agent-optimize` | Đo lường tải và điều phối đa agent tối ưu hóa lưu lượng token. |
| 24 | `architecture-decision-records` | Soạn thảo và duy trì hồ sơ quyết định kiến trúc kỹ thuật (ADR). |
| 25 | `github-actions-templates` | Mẫu pipeline GitHub Actions chuẩn sản xuất cho kiểm thử tự động và CI/CD. |
| 26 | `graphify-impact-analyzer` | Phân tích phạm vi ảnh hưởng của thay đổi mã nguồn qua đồ thị quan hệ AST. |
| 27 | `skillspector-security-guard` | Quét lỗ hổng prompt injection và cấu hình MCP theo tiêu chuẩn an toàn bảo mật. |
| 28 | `gherkin-to-suite` | Biên dịch file `.feature` BDD thành ma trận test, Universal IR và phân tích khoảng trống độ phủ. |
| 29 | `rbt-manual-testing` | Quy trình AI-RBT sinh kịch bản kiểm thử thủ công dựa trên rủi ro, ma trận 12 cột và checklist input field. |
| 30 | `self-healing-locator` | Tự động phát hiện và vá lỗi định vị phần tử bằng phân tích sai khác cây Accessibility (AOM). |
| 31 | `persistent-planning-files` | Lưu kế hoạch, phát hiện và tiến độ xuống 3 file markdown để công việc đa pha sống sót qua reset ngữ cảnh. |
| 32 | `surgical-coding-principles` | Bốn nguyên tắc chỉnh sửa có kỷ luật: nêu giả định, tối giản diff, mọi dòng đổi đều truy về yêu cầu. |
| 33 | `lean-code-ladder` | Thang 7 bậc reuse-first: chọn phương án nhỏ nhất hoàn chỉnh trước khi viết code mới. |
| 34 | `playwright-webapp-testing` | Vòng đời server có kiểm soát (start/ready/teardown) khi chạy Playwright test web app cục bộ. |
| 35 | `test-driven-development` | Kỷ luật RED-GREEN-REFACTOR: chưa xem test fail đúng lý do thì chưa viết code sản phẩm. |
| 36 | `systematic-debugging` | Điều tra gốc rễ 4 pha trước mọi bản vá; 3 lần sửa thất bại là dấu hiệu sai kiến trúc. |
| 37 | `verification-before-completion` | Giao thức bằng chứng: mọi tuyên bố pass/done phải kèm output lệnh chạy tươi trong phiên. |

> **Nguồn mở & credit:** Kỹ năng 31–37 được tiếp biến từ các dự án mã nguồn mở (andrej-karpathy-skills, ponytail, planning-with-files, anthropics/skills, superpowers, wshobson/agents) — license và tác giả chi tiết tại file `NOTICE` (mục 16–21); hướng dẫn công cụ ngoài kèm theo tại `docs/adopted-ecosystem-tools.md`.

</details>

---

## 🛠️ 8. Bộ Công Cụ Dòng Lệnh CLI (tools/)

Dự án đi kèm hơn 60 công cụ tiện ích viết hoàn toàn bằng **thư viện chuẩn Python** (Standard Library), không phụ thuộc package ngoài:

```bash
# 1. Chẩn đoán môi trường hệ thống (Node, Python, Chrome, Git)
npx synapse-hub doctor

# 2. Kiểm tra 9 Cổng Chất Lượng DoD
npx synapse-hub verify

# 3. Quét phát hiện test pass ảo và catch nuốt lỗi
npx synapse-hub lint ./tests

# 4. Nén 95% log CI/CD cồng kềnh
npx synapse-hub distill path/to/ci.log

# 5. Xuất test case sang file Excel .xlsx chuẩn 12 cột
npx synapse-hub export-excel

# 6. Kiểm tra độ nhạy của các câu lệnh assert
npx synapse-hub mutate ./tests

# 7. Dò tìm và cách ly test chập chờn (Flaky Tests)
npx synapse-hub flaky scan ./tests
```

*(Xem toàn bộ hướng dẫn tham số chi tiết tại [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) và [tools/TOOLS_RUNBOOK.md](tools/TOOLS_RUNBOOK.md)).*

---

## 📄 Bản Quyền & Nguồn Gốc (MIT License)

Dự án này được sáng lập và phát triển bởi **Thế Vị ([@TeeVee998](https://github.com/TeeVee998))** dưới giấy phép mã nguồn mở [MIT License](LICENSE).  
Mọi hình thức sao chép, tích hợp hoặc phân phối lại đều được tự do sử dụng, với điều kiện **bắt buộc phải giữ nguyên thông báo bản quyền và nguồn tác giả ban đầu**.
