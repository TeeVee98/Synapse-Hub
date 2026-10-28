# TOOLS RUNBOOK — Sổ Tay Vận Hành Công Cụ Tự Động Cho AI Agent

> **Tài liệu tham chiếu chuẩn cho AI Agent (Google Antigravity, Cursor, Claude Code, Windsurf)**  
> Mọi script trong thư mục `tools/` đều có mục đích, cú pháp CLI và tình huống kích hoạt bắt buộc rõ ràng. Tuyệt đối không đoán mò cú pháp.

---

## 1. BẢNG TRA CỨU TÌNH HUỐNG KÍCH HOẠT (DISPATCH MATRIX)

| Tình Huống Thực Tế Của Agent | Script Phải Dùng | Lệnh Thực Thi Điển Hình |
| :--- | :--- | :--- |
| **Bắt đầu task / Tra cứu hàm Page Class** | `tools/repo_map.py` | `python tools/repo_map.py` (Đọc `tools/repo_map.txt`) |
| **Trước khi Commit / Hoàn Thành Task** | `tools/verify_all.py` | `python tools/verify_all.py` |
| **Vừa tạo / Sửa Test Script (Check Fake-Pass)** | `tools/infer_linter.py` | `python tools/infer_linter.py` |
| **Sau khi sửa đổi Page Class (Xác định ảnh hưởng)** | `tools/test_impact.py` | `python tools/test_impact.py --git-diff` |
| **Khi Test bị FAIL (Xác định dòng lỗi trong 0.1s)** | `tools/pinpoint_failure.py` | `python tools/pinpoint_failure.py` |
| **Khi log dài nghìn dòng (Tránh Context Rot)** | `tools/distill_log.py` | `python tools/distill_log.py <path_to_log>` |
| **Khi gặp lỗi UI / Overlay / Stale Element** | `tools/cache_resolver.py` | `python tools/cache_resolver.py query "<error_msg>"` |
| **Sinh kịch bản test từ User Story tự nhiên** | `tools/generate_tc_from_story.py`| `python tools/generate_tc_from_story.py "<story>"` |
| **Sinh ma trận kiểm thử E2E từ OpenAPI/Swagger** | `tools/generate_api_matrix.py` | `python tools/generate_api_matrix.py --spec <swagger.json>` |
| **Kiểm định khả năng tiếp cận WCAG 2.2** | `tools/wcag_audit.py` | `python tools/wcag_audit.py <path_to_html_or_url>` |
| **Kiểm tra rò rỉ dữ liệu DB (Taint Analysis)** | `tools/trace_data_flow.py` | `python tools/trace_data_flow.py` |
| **Kiểm tra lệch giao diện Canvas / Map GIS** | `tools/visual_diff_canvas.py` | `python tools/visual_diff_canvas.py --baseline <b> --actual <a>` |
| **Sát hạch năng lực tự phục hồi (Canary Audit)** | `tools/agent_canary.py` | `python tools/agent_canary.py --run` |
| **Tra cứu Locator XPath trong bộ nhớ Cache** | `tools/lookup_xpath.py` | `python tools/lookup_xpath.py "<keyword>"` |
| **Tra cứu thông tin Test Case** | `tools/lookup_tc.py` | `python tools/lookup_tc.py "<keyword_or_id>"` |
| **Kiểm tra chất lượng tài liệu Markdown** | `tools/lint_ai_docs.py` | `python tools/lint_ai_docs.py` |

---

## 2. HƯỚNG DẪN CHI TIẾT TỪNG CÔNG CỤ (DETAILED USAGE)

### 1. `tools/generate_api_matrix.py`
- **Mục đích:** Đọc tài liệu OpenAPI / Swagger JSON và tự động tính toán sinh ma trận kiểm thử đầy đủ: Positive, Boundary Value (min/max length, special chars, XSS payloads), và Negative (invalid data types, missing required attributes).
- **Cú pháp CLI:**
  ```bash
  # Sinh ma trận Markdown từ file Swagger JSON
  python tools/generate_api_matrix.py --spec path/to/swagger.json --format md -o api_matrix.md

  # Sinh ma trận dưới dạng JSON
  python tools/generate_api_matrix.py --spec path/to/swagger.json --format json -o api_matrix.json

  # Sinh thử mẫu với demo schema có sẵn
  python tools/generate_api_matrix.py --sample
  ```

---

### 2. `tools/wcag_audit.py`
- **Mục đích:** Linter tự động kiểm định tiêu chuẩn tiếp cận Web Accessibility WCAG 2.2 Level A và AA (thiếu thẻ alt ảnh, input thiếu nhãn label/aria-label, bảng thiếu header, vi phạm phân cấp thẻ tiêu đề H1-H6, nút bấm rỗng).
- **Cú pháp CLI:**
  ```bash
  # Quét file HTML cục bộ
  python tools/wcag_audit.py path/to/page.html -o wcag_report.md

  # Quét trực tiếp URL đang chạy
  python tools/wcag_audit.py https://staging.example.com/dashboard --url -o wcag_report.md
  ```

---

### 3. `tools/verify_all.py`
- **Mục đích:** Cổng gác kiểm định chất lượng tối cao (7 Quality Gates DoD) trước khi kết thúc task hoặc commit git.
- **Cú pháp CLI:**
  ```bash
  python tools/verify_all.py
  ```

---

### 4. `tools/infer_linter.py`
- **Mục đích:** Phân tích cú pháp AST của file test script để phát hiện Fake-Pass (kịch bản không chứa assertion nào hoặc chứa khối try-catch rỗng nuốt lỗi).
- **Cú pháp CLI:**
  ```bash
  python tools/infer_linter.py
  ```

---

### 5. `tools/test_impact.py`
- **Mục đích:** Dựa trên `git diff`, phân tích cây phụ thuộc mã nguồn để chỉ ra chính xác những Test Case nào cần chạy lại, tránh chạy lãng phí toàn bộ test suite.
- **Cú pháp CLI:**
  ```bash
  python tools/test_impact.py --git-diff
  ```

---

### 6. `tools/pinpoint_failure.py`
- **Mục đích:** Trích xuất nhanh số dòng và nguyên nhân lỗi (Stacktrace & Exception) từ JUnit XML mà không cần mở file XML nặng.
- **Cú pháp CLI:**
  ```bash
  python tools/pinpoint_failure.py
  ```

---

### 7. `tools/distill_log.py`
- **Mục đích:** Nén và lọc log thực thi KRE / Gradle / CLI, loại bỏ 95% dòng log thừa, chỉ giữ lại lỗi và pointer đường dẫn file.
- **Cú pháp CLI:**
  ```bash
  python tools/distill_log.py path/to/execution.log
  ```

---

### 8. `tools/cache_resolver.py`
- **Mục đích:** Tra cứu giải pháp xử lý lỗi từ cơ sở dữ liệu SQLite `tools/memory_cache.db` bằng kỹ thuật cosine similarity/keyword match (chi phí 0 token).
- **Cú pháp CLI:**
  ```bash
  python tools/cache_resolver.py query "ElementClickInterceptedException"
  python tools/cache_resolver.py add --pattern "Timeout waiting for primeNG" --fix "BasePage.waitForAngular()"
  ```

---

### 9. `tools/generate_tc_from_story.py`
- **Mục đích:** Large Action Model (LAM) parser chuyển đổi câu chuyện người dùng tự nhiên thành khung kịch bản Clean POM hoàn chỉnh.
- **Cú pháp CLI:**
  ```bash
  python tools/generate_tc_from_story.py "User navigates to login, inputs valid credentials, and verifies dashboard table loaded"
  ```

---

### 10. `tools/visual_diff_canvas.py`
- **Mục đích:** So sánh ảnh pixel và chỉ số SSIM cho các thành phần Canvas/GIS không thể bắt locator bằng DOM thông thường.
- **Cú pháp CLI:**
  ```bash
  python tools/visual_diff_canvas.py --baseline baseline.png --actual actual.png --diff diff.png
  ```
