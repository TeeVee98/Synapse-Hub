# 🧠 AI Agent Skills & Intelligence Hub

> **Kho lưu trữ trung tâm các Kỹ năng (Skills), Quy tắc (Rules), Công cụ (Tools) và Quy trình tự động hóa (Workflows) cho Trợ lý AI (Google Antigravity / Cursor / Windsurf / Claude Code).**

---

## 🌟 1. Tổng quan & Mục đích Kiến trúc

Repository này đóng vai trò là **"Bộ não dùng chung" (Shared Intelligence Core)**, tách biệt hoàn toàn khỏi mã nguồn của từng dự án cụ thể.

```mermaid
flowchart TD
    subgraph Hub["🧠 Agent Skills (Intelligence Core)"]
        Skills[".agents/skills/ (22 Skills)"]
        Rules[".agents/rules/ (7 Rules)"]
        Tools["tools/ (20+ Python Tools)"]
        Workflows[".agents/workflows/"]
    end

    subgraph ChatSession["💬 AI Agent Workspace / Chat Session"]
        Hub -->|Mount/Add Workspace| ChatSession
    end

    subgraph Projects["📁 Các Dự Án Mục Tiêu (Target Projects)"]
        ProjectA["Dự án A<br/>(PROJECT_AI_GUIDE.md + Source Code)"]
        ProjectB["Dự án B<br/>(PROJECT_AI_GUIDE.md + Test Code)"]
        ProjectC["Dự án C<br/>(PROJECT_AI_GUIDE.md + App Code)"]
        Other["Dự án khác..."]
    end

    ProjectA -->|Mount Workspace| ChatSession
    ProjectB -.->|Mount Workspace| ChatSession
    ProjectC -.->|Mount Workspace| ChatSession
    Other -.->|Mount Workspace| ChatSession
```

### Lợi ích cốt lõi:
1. **Dùng chung đa dự án (Cross-Project Reusability):** Một lần phát triển skill hay tối ưu tool có thể áp dụng ngay cho bất kỳ dự án nào.
2. **Bảo mật mã nguồn (Privacy & Clean SCM):** Repository dự án hoàn toàn sạch sẽ, không chứa prompt hay AI skill cá nhân.
3. **Quản lý tập trung (Single Source of Truth):** Dễ dàng nâng cấp, thêm skill mới, đồng bộ Global Memory Cache tại một nơi duy nhất.
4. **Nhẹ & Tinh gọn:** Dự án mục tiêu chỉ cần đúng **1 file duy nhất** hướng dẫn AI (`PROJECT_AI_GUIDE.md`).

---

## 🚀 2. Cách Sử Dụng Trong Phiên Chat (How to Mount)

### Bước 1: Mở phiên làm việc đa thư mục (Multi-Root Workspace)
Trong IDE (Google Antigravity / VS Code / Cursor):
1. Mở thư mục dự án mục tiêu của bạn.
2. Thêm thư mục `agent-skills` vào Workspace (`File` -> `Add Folder to Workspace...`).
3. Trong giao diện chat của AI, AI sẽ tự động nhận diện cả 2 thư mục:
   - **Thư mục Hub (`agent-skills`)**: Đọc toàn bộ 22 Skills, 7 Rules, và các Python Tools.
   - **Thư mục dự án**: Đọc file `PROJECT_AI_GUIDE.md` để nắm rõ ngữ cảnh nghiệp vụ của dự án đó.

### Bước 2: Thiết lập file hướng dẫn trong dự án mục tiêu
Trong mỗi dự án riêng biệt, tạo file `PROJECT_AI_GUIDE.md` (tham khảo mẫu tại `templates/PROJECT_AI_GUIDE_TEMPLATE.md`):
- Tên hệ thống & đường dẫn môi trường (URL, Test, Staging, Prod).
- Tài khoản đăng nhập kiểm thử / cấu hình môi trường.
- Cấu trúc thư mục mã nguồn / POM / Test Suites.
- Các lệnh chạy kiểm thử và build đặc thù (CLI, Playwright, Maven, Gradle...).

---

## 📦 3. Danh Mục Kỹ Năng & Quy Tắc (Catalog)

### 3.1. Danh mục 22 Kỹ năng (.agents/skills/)

| STT | Tên Kỹ Năng (Skill) | Phạm Vi Hoạt Động |
|:---:|---|---|
| 1 | `clean-pom-crafter` | Chuẩn hóa Clean Page Object Model, Flat Architecture, Dynamic `uniqueCode`. |
| 2 | `playwright-live-interaction` | Tương tác trực tiếp headless DOM/AOM, bypass overlay, xác thực zero-second. |
| 3 | `self-healing-locator` | Tự phục hồi locator bằng cây Semantic Accessibility (AOM), Role > Label > TestId. |
| 4 | `failure-autopsy-and-healing` | Khám nghiệm tử thi lỗi từ screenshot `FAILED_*.png` và Allure report, tự vá mã. |
| 5 | `antigravity-test-sentinel` | Verification-First gatekeeper, chặn tuyên bố hoàn thành nếu test chưa pass exit code 0. |
| 6 | `katalon-cli-runner` | Điều phối thực thi headless CLI, Community mode và sinh báo cáo Allure. |
| 7 | `lam-script-generator` | Large Action Model, chuyển đổi User Story sang 100% test script không token replay. |
| 8 | `token-and-context-optimizer` | Tối ưu token, lọc log rác, off-context memory cache và nén ngữ cảnh. |
| 9 | `agent-orchestration-multi-agent-optimize` | Điều phối multi-agent swarm, cân bằng tải và giám sát chi phí token. |
| 10 | `api-spec-to-e2e-matrix` | Chuyển đổi OpenAPI/Swagger sang ma trận kiểm thử E2E phân vùng tương đương. |
| 11 | `architecture-decision-records` | Soạn thảo và quản lý tài liệu kiến trúc kỹ thuật (ADR). |
| 12 | `bats-testing-patterns` | Thiết kế kiểm thử tự động cho Shell Scripts và CI/CD pipelines. |
| 13 | `c4-architecture-c4-architecture` | Phân tích và sinh sơ đồ kiến trúc C4 Model từ mã nguồn hiện hữu. |
| 14 | `code-refactoring-refactor-clean` | Tái cấu trúc code chuyên sâu, khử code smells, nợ kỹ thuật và chuẩn SOLID. |
| 15 | `code-review-ai-ai-review` | Kết hợp phân tích tĩnh và AI Review về bảo mật, hiệu năng và kiến trúc. |
| 16 | `context-degradation` | Chẩn đoán và phòng ngừa hiện tượng Lost-in-the-Middle, suy thoái ngữ cảnh. |
| 17 | `e2e-testing-patterns` | Best practices kiểm thử E2E với Playwright và Cypress. |
| 18 | `filesystem-context` | Quản lý scratchpad trên ổ đĩa, lưu trữ trạng thái bền vững ngoài prompt. |
| 19 | `github-actions-templates` | Mẫu pipeline CI/CD GitHub Actions chuẩn sản xuất. |
| 20 | `graphify-impact-analyzer` | Phân tích đồ thị tri thức AST Knowledge Graph và khoanh vùng ảnh hưởng. |
| 21 | `tdd-orchestrator` | Điều phối kỷ luật TDD (Red-Green-Refactor). |
| 22 | `wcag-audit-patterns` | Đánh giá và kiểm thử độ tương thích tiếp cận theo tiêu chuẩn WCAG 2.2. |

### 3.2. Danh mục 7 Quy tắc Cốt lõi (.agents/rules/)
1. `context-engineering.md`: Giao thức lọc log thừa, khai báo lười (lazy loading) và tối ưu KV-cache.
2. `dual-remote-push-protocol.md`: Giao thức bảo mật remote, cách ly hoàn toàn AI asset khỏi SCM công ty.
3. `graphify.md`: Điều hướng đồ thị tri thức mã nguồn thay vì đọc toàn văn mã nguồn lớn.
4. `lessons-learned.md`: Danh sách bài học kinh nghiệm và anti-patterns đã giải quyết.
5. `mandatory-playwright-live.md`: Quy chuẩn chạy headless 1920x1080 và 5 AI paradigms.
6. `skill-precedence.md`: Thứ tự ưu tiên skill cục bộ, chống xung đột với plugin ngoài.
7. `systematic-debugging.md`: Kỷ luật điều tra lỗi có căn cứ, cấm đoán mò và verify-first.

---

## 🛠️ 4. Bộ Công Cụ Tự Động Hóa (tools/ & scripts/)

- `tools/verify_all.py`: Cổng thẩm định 7 Gates (UTF-8, No XPaths, UniqueCode, Meta Infer, Clean POM).
- `tools/infer_linter.py`: Phân tích tĩnh AST phát hiện fake-pass (0 assertion) và khối try-catch rỗng.
- `tools/test_impact.py`: Phân tích git diff và khoanh vùng chính xác test cases bị ảnh hưởng.
- `tools/cache_resolver.py`: Quản lý bộ nhớ đệm lỗi SQLite trung tâm (`~/.agent_memory/global_cache.db`).
- `tools/distill_log.py`: Lọc bỏ 95% log thừa từ CLI/Gradle/Test runners, giữ lại thông tin cốt lõi.
- `tools/agent_canary.py`: Hệ thống tiêm lỗi tự động (Canary & Mutation Testing) đánh giá sức phục hồi của Agent.
- `tools/repo_map.py`: Trích xuất bản đồ cấu trúc hàm và Page Class siêu nén (~500 tokens).
- `tools/visual_diff_canvas.py`: So sánh pixel/SSIM cho màn hình GIS/Canvas không có DOM.
- `tools/wcag_audit.py`: Quét kiểm toán tự động các tiêu chí WCAG 2.2.
- `tools/trace_data_flow.py`: Kiểm tra luồng dữ liệu kiểm thử, phát hiện rác dữ liệu DB (Orphan Data).
