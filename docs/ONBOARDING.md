# HƯỚNG DẪN ONBOARDING & CÀI ĐẶT MÔI TRƯỜNG DỰ ÁN DMIT
> **DMIT Automation Framework — Setup Guide for Engineers & AI Agents**<br>
> *Dành cho Tester, QA Automation, Developer và AI Coding Agent khi mới tiếp nhận dự án DMIT.*

---

## 1. Tổng Quan Kiến Trúc Dự Án

| Thành phần | Tiêu chuẩn kỹ thuật | Mô tả |
|---|---|---|
| **Công cụ chính** | **Katalon Studio (v8.6.x – v11.x)** | Nền tảng kiểm thử tự động Web UI, viết bằng **Groovy (Java)**. |
| **Vị trí dự án** | Thư mục dự án | Có thể đặt tại bất kỳ ổ đĩa nào hoặc workspace Jenkins/CI. |
| **Cấu trúc lưu trữ** | **Flat Architecture** | Toàn bộ 259 Test Cases và 259 Scripts nằm chung trực tiếp dưới thư mục gốc chuẩn. |
| **Quy mô kịch bản** | **259 Test Cases** | Bao quát 9 phân hệ nghiệp vụ theo file phân công chính thức. |
| **Môi trường Web** | **DEMO / UAT** | `https://doit-demo.vnptit.vn/dmit/auth` |
| **Hồ sơ biến môi trường** | `Profiles/default.glbl` | Chứa các cấu hình toàn cục (URL, tài khoản mặc định, timeout). |
| **Test Suites** | **11 Master Suites (40 Suites tổng cộng)** | Bao gồm `10_All_DMIT_Tests.ts` (259 TCs), `01_` đến `09_` theo từng phân hệ, và các Group Suites chi tiết. |

---

## 2. Checklist Công Cụ Cần Cài Đặt (Prerequisites)

| # | Công cụ | Phiên bản khuyến nghị | Mục đích | Cách kiểm tra |
|---|---|---|---|---|
| 1 | **Google Chrome** | Bản mới nhất (120+) | Trình duyệt thực thi kiểm thử giao diện Web | Mở Chrome $\rightarrow$ Trợ giúp $\rightarrow$ Giới thiệu |
| 2 | **Katalon Studio** | **v8.6.x – v11.x Enterprise / Free** | Môi trường IDE mở dự án, chạy test, sửa script | Mở ứng dụng hoặc kiểm tra thư mục cài đặt |
| 3 | **Java Runtime (JDK)** | **Java 17 hoặc Java 21** | Biên dịch và chạy mã nguồn Groovy *(Katalon đã tích hợp sẵn JRE)* | `java -version` trong Command Prompt |
| 4 | **PowerShell** | v5.1+ (Windows mặc định) | Chạy các script tự động hóa và MCP Server đọc Excel | `$PSVersionTable.PSVersion` |

---

## 3. Cấu Hình Môi Trường & Bảo Mật Mật Khẩu (Security Setup)

Dự án áp dụng chính sách **Zero-Plaintext-Secrets**: mật khẩu quản trị không được lưu cứng trong repository mà được nạp động qua biến môi trường `DMIT_PASSWORD`.

### 3.1. Thiết lập biến môi trường trên máy cục bộ
- **Trên Windows PowerShell:**
  ```powershell
  [System.Environment]::SetEnvironmentVariable('DMIT_PASSWORD', 'MậtKhẩuThậtỞĐây', 'User')
  # Hoặc trong phiên làm việc hiện tại:
  $env:DMIT_PASSWORD = "MậtKhẩuThậtỞĐây"
  ```
- **Trên macOS / Linux:**
  ```bash
  export DMIT_PASSWORD="MậtKhẩuThậtỞĐây"
  # Lưu vĩnh viễn trong ~/.zshrc hoặc ~/.bashrc
  ```

### 3.2. Mở dự án lần đầu trong Katalon Studio
1. Khởi động **Katalon Studio** $\rightarrow$ **File** $\rightarrow$ **Open Project** $\rightarrow$ Trỏ tới tệp `DMIT.prj` trong thư mục dự án.
2. Cập nhật WebDriver Chrome: Vào menu **Tools** $\rightarrow$ **Update WebDrivers** $\rightarrow$ Chọn **Chrome**.
3. Cấu hình Preferences:
   - **Default wait for element timeout:** Đặt `15` giây.
   - **Default page load timeout:** Đặt `30` giây.

---

## 4. Checklist Chạy Thử Nghiệm Lần Đầu & Xác Minh Hệ Thống (DoD)

1. **Cài đặt Git Hooks bảo vệ mã nguồn & Đồng bộ bộ nhớ đệm (Chạy 1 lần):**
   ```bash
   python3 tools/git_pre_commit_guard.py --install
   python3 tools/cache_resolver.py init
   ```
   *(Hook `post-merge` sẽ tự động chạy `cache_resolver.py init` mỗi khi bạn thực hiện `git pull` để kéo code mới về).*

2. **Xác minh toàn bộ chất lượng dự án bằng 1 lệnh:**
   ```bash
   python3 tools/verify_all.py
   ```
   *(Đảm bảo toàn bộ 7 cổng kiểm soát BOM, POM, Docs Linter, Security, Meta Infer đều báo PASS).*
2. Mở `Test Cases` $\rightarrow$ Chọn `TC-8 Đăng nhập thành công`.
3. Bấm nút **Run** (Chrome).
4. **Kỳ vọng:** Mở trình duyệt, vào trang đăng nhập, tự động thiết lập ngôn ngữ Tiếng Việt, đăng nhập tài khoản quản trị thành công và báo **PASSED**.
5. Chạy suite tổng hợp: Mở `Test Suites/10_All_DMIT_Tests` $\rightarrow$ Bấm **Run** để kiểm thử tự động toàn bộ danh mục.
6. Khi kết thúc phiên: Đọc và cập nhật `PROJECT_STATE.md`, báo cáo lỗi nếu có vào `KNOWN_ISSUES.md`.
