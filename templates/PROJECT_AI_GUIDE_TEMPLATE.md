# 🎯 Hướng Dẫn AI Dành Cho Dự Án: [TÊN DỰ ÁN] (PROJECT_AI_GUIDE.md)

> **Mục đích:** File này cung cấp ngữ cảnh nghiệp vụ đặc thù của dự án cho Trợ lý AI (Google Antigravity / AI Agent).
> AI Agent sẽ kết hợp các kỹ năng dùng chung từ repo trung tâm `agent-skills` với các thông tin nghiệp vụ dưới đây để thực thi công việc.

---

## 1. Thông Tin Chung Về Hệ Thống Kiểm Thử (AUT)
- **Tên dự án / Phân hệ:** [Ví dụ: VNPT DMIT - Khai thác Dữ liệu Công Thương]
- **Môi trường Web / App:**
  - URL Kiểm thử (Test): `https://...`
  - URL Staging / Demo: `https://...`
- **Công nghệ Frontend:** [Ví dụ: Angular 17 + PrimeNG, React, Vue, JSP]
- **Framework Kiểm thử:** [Ví dụ: Katalon Studio 10.x / Playwright / Selenium Webdriver / Cypress]
- **Ngôn ngữ kịch bản:** [Ví dụ: Groovy, TypeScript, Python]

---

## 2. Tài Khoản & Thông Tin Xác Thực (Test Credentials)
- **Tài khoản quản trị (Admin):** `username` / `password`
- **Tài khoản nghiệp vụ (User/Staff):** `username` / `password`
- **Cơ chế xác thực:** [Ví dụ: Cookie Session, JWT Bearer, SSO CAS VNPT]

---

## 3. Kiến Trúc Mã Nguồn & Thư Mục Dự Án (Project Structure)
- **Page Objects / Keywords:** `Keywords/...` hoặc `src/pages/...`
- **Test Scripts:** `Scripts/...` hoặc `tests/...`
- **Test Suites / Collections:** `Test Suites/...`
- **Dữ liệu kiểm thử (Test Data):** `Data Files/...`
- **Cấu hình môi trường:** `Profiles/...` hoặc `.env`

---

## 4. Quy Chuẩn Kỹ Thuật Dự Án (Project-Specific Standards)
1. **Kiến trúc Page Object:** [Ví dụ: Clean POM Flat Architecture, kế thừa BasePage]
2. **Khởi tạo dữ liệu kiểm thử:** Bắt buộc dùng `uniqueCode` ngẫu nhiên kèm tiền tố dự án (ví dụ: `AUTO_...`) để tránh xung đột dữ liệu.
3. **Mã hóa file:** Bắt buộc 100% `UTF-8 No BOM`.
4. **Xử lý bất đồng bộ:** Sử dụng Smart Wait (Angular `isStable()` / Playwright `waitForLoadState('networkidle')`), tuyệt đối tránh `Thread.sleep` tĩnh.
5. **Dọn dẹp dữ liệu:** Mọi test case thêm mới dữ liệu phải có teardown xóa dữ liệu tự động.

---

## 5. Lệnh Chạy Kiểm Thử Thường Dùng (Execution Commands)
- **Chạy kiểm thử Headless (CLI):**
  ```bash
  [Lệnh chạy cụ thể, ví dụ: katalon -noSplash -runMode=console ...]
  ```
- **Chạy xác minh chất lượng tổng thể:**
  ```bash
  python D:/agent-skills/tools/verify_all.py
  ```
- **Lọc log khi gặp lỗi:**
  ```bash
  python D:/agent-skills/tools/distill_log.py <path_to_log>
  ```
