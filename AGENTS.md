# AGENTS.md — Quy Chuẩn & Kỷ Luật Vận Hành Cho AI Agent (Enterprise QA Hub)

> **Phạm vi áp dụng:** Google Antigravity, Cursor, Claude Code, GitHub Copilot, Codex, Windsurf và mọi kỹ sư AI/QA tham gia các dự án kiểm thử tự động.  
> Mọi quy tắc dưới đây là **BẮT BUỘC (MANDATORY)**, áp dụng nhất quán trên toàn bộ các dự án liên kết với Hub kỹ năng này.

---

## 0. KHỐI XÁC NHẬN BẮT BUỘC TRƯỚC KHI THỰC HIỆN TÁC VỤ (PRE-FLIGHT)

Trước khi sinh mã nguồn, chỉnh sửa kịch bản kiểm thử, hoặc tái cấu trúc file, AI Agent **BẮT BUỘC** đọc file hướng dẫn đặc thù của dự án mục tiêu (`PROJECT_AI_GUIDE.md`) và **mở đầu mỗi phản hồi bằng khối xác nhận chuẩn:**

```text
> ✅ Đã nạp Hub Kỹ Năng (agent-skills) & Đọc Hướng dẫn Dự án (PROJECT_AI_GUIDE.md)
> ✅ Cấu trúc kiểm thử: Clean POM Architecture — 100% Locator đóng gói trong Page Class
> ✅ Kỹ thuật bắt buộc: Playwright Live Interaction (Khảo sát DOM/AOM thật trước khi codify)
> ✅ Cơ chế vận hành: Truth Anchor (No Fake Pass) + Zero-Token Memory Cache
> ✅ Kế hoạch thực hiện: <1–3 dòng tóm tắt ngắn gọn các bước sẽ làm>
```

---

## 1. TIÊU CHUẨN KIẾN TRÚC & MÃ NGUỒN CỐT LÕI (CORE ARCHITECTURE)

1. **Clean Page Object Model (POM):**
   - Kịch bản kiểm thử (`Scripts/` hoặc `tests/`) chỉ chứa các lệnh gọi phương thức nghiệp vụ từ Page Class.
   - **Tuyệt đối cấm** viết XPath thô, CSS selector, hay `findTestObject` trực tiếp trong file kịch bản.
   - Mọi locator và thao tác phần tử DOM phải được đóng gói tại Page Class tương ứng kế thừa từ `BasePage`.

2. **100% UTF-8 No BOM:**
   - Mọi file (`.groovy`, `.java`, `.ts`, `.py`, `.json`, `.md`, `.ps1`, `.sh`) **không được phép** chứa ký tự UTF-8 BOM (`0xEF, 0xBB, 0xBF`).

3. **Dữ liệu kiểm thử động & Tránh xung đột (Idempotent Test Data):**
   - Luôn sử dụng hàm sinh mã ngẫu nhiên có tiền tố (ví dụ: `BasePage.uniqueCode("AUTO_")` hoặc `DataGenerator`) để tránh xung đột khóa chính DB khi chạy song song.
   - Luôn đi kèm bước dọn dẹp dữ liệu (Teardown Cleanup) sau khi chạy test thêm mới.

4. **Đồng bộ hóa & Xử lý bất đồng bộ (Smart Wait):**
   - Tuyệt đối cấm sử dụng `Thread.sleep` tĩnh làm chậm pipeline và gây flaky test.
   - Sử dụng cơ chế Smart Wait: chờ phần tử hiển thị, chờ Angular `zone.isStable()`, hoặc Playwright `waitForLoadState('networkidle')`.

---

## 2. GIAO THỨC TƯƠNG TÁC THỜI GIAN THỰC (PLAYWRIGHT LIVE PROTOCOL)

1. **Chu trình 3 giai đoạn (Mandatory 3-Stage Lifecycle):**
   - **Giai đoạn 1 (Khám phá):** Khảo sát DOM/AOM thật bằng headless browser. Tuyệt đối không tự suy đoán URL hoặc selector.
   - **Giai đoạn 2 (Tạo kịch bản):** Xác minh selector trên browser thực tế đạt tỷ lệ trúng 100% dưới 200ms trước khi đưa vào Page Class.
   - **Giai đoạn 3 (Sửa lỗi tại chỗ):** Khi test thất bại, tạm dừng browser tại bước lỗi để khám nghiệm và vá locator; không chạy lại từ đầu.
2. **Cấu hình chuẩn:** Headless mode, độ phân giải Full HD `1920x1080`.

---

## 3. KỶ LUẬT "TRUTH ANCHOR" & CHỐNG PHÁN ĐOÁN MÒ (ZERO-HALLUCINATION)

1. **Truth Anchor (No Fake Pass):**
   - Nếu test thất bại do lỗi của ứng dụng (AUT Bug), phải trung thực báo cáo lỗi; **tuyệt đối không hạ thấp điều kiện assertion, bỏ qua kiểm tra, hoặc sửa kết quả mong đợi để tạo test pass giả mạo**.
2. **Không để mã dở dang (No Lazy Truncation):**
   - Xuất mã hoàn chỉnh, có thể thực thi ngay. Không dùng `// ... existing code ...` hoặc `// TODO` làm gián đoạn kịch bản.
3. **Bảo mật tuyệt đối thông tin xác thực:**
   - Tuyệt đối không commit mật khẩu văn bản thô, token, hay private key vào git. Luôn truyền qua biến môi trường hoặc profile mã hóa.

---

## 4. HỆ THỐNG VAI TRÒ MULTI-AGENT SWARM (AGENT ROLES)

Repository hỗ trợ phân công nhiệm vụ chuyên biệt cho các Agent trong hệ thống:

1. **Lead QA Orchestrator (`orchestrator`):**
   - Tiếp nhận yêu cầu, phân tích phạm vi, chia nhỏ task và điều phối các agent chuyên trách.
2. **Live Interaction Explorer (`live-explorer`):**
   - Sử dụng Playwright / browser tools để khảo sát DOM/AOM thực tế, trích xuất selector bền vững.
3. **Clean POM Crafter (`pom-crafter`):**
   - Thiết kế Page Classes, đóng gói phương thức thao tác UI, tạo test scripts chuẩn Clean POM.
4. **Test Execution Runner (`test-runner`):**
   - Chạy test suites qua KRE CLI / Playwright / Gradle, giám sát quá trình chạy headless.
5. **Failure Autopsy Analyst (`failure-analyst`):**
   - Khám nghiệm tử thi lỗi từ screenshot `FAILED_*.png` và Allure report, chẩn đoán nguyên nhân gốc (RCA).
6. **Quality Gatekeeper & Sentinel (`quality-gatekeeper`):**
   - Thẩm định 7 Cổng Chất Lượng qua `verify_all.py`, quét Fake-Pass qua `infer_linter.py`, đảm bảo zero code smell trước khi bàn giao.

---

## 5. CÔNG CỤ ĐIỀU PHỐI TẬP TRUNG (TOOLS RUNBOOK)

Mọi thao tác kiểm tra và quản trị chất lượng đều được thực thi nhanh chóng thông qua thư mục `tools/`:

```bash
# 1. Chạy thẩm định 7 Cổng Chất Lượng
python tools/verify_all.py

# 2. Quét AST linter phát hiện Fake-Pass & Catch rỗng
python tools/infer_linter.py

# 3. Phân tích ảnh hưởng thay đổi mã nguồn
python tools/test_impact.py --git-diff

# 4. Lọc log rút gọn 95% thông tin thừa
python tools/distill_log.py <path_to_log>

# 5. Tra cứu bộ nhớ đệm lỗi 0-token
python tools/cache_resolver.py query "<error_message>"
```
