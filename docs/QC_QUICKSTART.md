# ⚡ Synapse Hub — Hướng Dẫn Nhanh 1 Trang Cho Đội QC

[🇻🇳 Tiếng Việt](QC_QUICKSTART.md) | [🇬🇧 English Edition](QC_QUICKSTART.en.md) • [⬅️ Quay lại README](../README.md)

> **Tác giả:** Thế Vị ([@TeeVee98](https://github.com/TeeVee98)) | **Giấy phép:** MIT  
> **Mục tiêu:** Bắt đầu dùng Synapse Hub trong **3 phút** — không cần học hết 57 kỹ năng hay 153 lệnh CLI.

---

## 📦 Cài Đặt (Chọn 1 Trong 2 Cách)

- **Cách A — Khuyên dùng (Node.js >= 18 + Python >= 3.10):** Chạy ngay không cần cài cố định bằng `npx @teevee98/synapse-hub <lệnh>`, hoặc cài toàn cục:
  ```bash
  npm install -g @teevee98/synapse-hub
  ```
- **Cách B — Thuần Python >= 3.10 (từ GitHub):**
  ```bash
  pip install git+https://github.com/TeeVee98/Synapse-Hub.git
  ```

---

## 👔 Lộ Trình 1: Manual QC / Zero-Code (3 Lệnh Hàng Ngày)

> Dùng **VS Code Extension** ([QA Sentinel Toolkit](https://marketplace.visualstudio.com/items?itemName=Teevee98.synapse-hub-vscode)) để thao tác 1-click, hoặc dùng 3 lệnh sau:

| # | Lệnh Hàng Ngày | Mục Đích |
|---|---|---|
| **1** | `npx @teevee98/synapse-hub doctor` | Kiểm tra nhanh Python, Node.js, Git và môi trường máy QC |
| **2** | `npx @teevee98/synapse-hub export-excel` | Xuất User Story / Test Case sang bảng Excel chuẩn 12 cột |
| **3** | `npx @teevee98/synapse-hub scaffold-tc testcase.md --out tests/e2e/` | Chuyển test case Markdown thủ công sang mã Playwright Clean POM |

---

## 🤖 Lộ Trình 2: Automation QC (4 Lệnh Hàng Ngày)

> Áp dụng cho dự án Playwright, Cypress, Pytest, Katalon để chặn test pass ảo, sleep cứng và lộ secret trước khi push:

| # | Lệnh Hàng Ngày | Mục Đích |
|---|---|---|
| **1** | `npx @teevee98/synapse-hub doctor` | Xác nhận môi trường đạt chuẩn trước khi chạy kiểm định |
| **2** | `npx @teevee98/synapse-hub init --profile standard` | Khởi tạo cấu hình Synapse Hub cho repository kiểm thử |
| **3** | `npx @teevee98/synapse-hub lint` | Bắt test 0-assert, sleep tĩnh (`sleep`/`waitForTimeout`), nuốt ngoại lệ |
| **4** | `npx @teevee98/synapse-hub verify` | Chạy đầy đủ 11 Cổng Chất Lượng DoD trước khi tạo Pull Request |

---

## 🔧 Xử Lý Sự Cố Nhanh Trên Windows / PATH (3 Lỗi Phổ Biến)

| Triệu Chứng | Nguyên Nhân | Cách Khắc Phục |
|---|---|---|
| `python3` mở Microsoft Store hoặc báo `not found` | Windows App Execution Alias trỏ vào stub `WindowsApps` | Cài Python >= 3.10 từ python.org, bật **Add python.exe to PATH**, hoặc tắt `python3.exe` trong *Manage app execution aliases* |
| `npx @teevee98/synapse-hub` báo thiếu Python / Node | Chưa có trên `PATH` của terminal hiện tại | Mở terminal mới sau khi cài và chạy `npx @teevee98/synapse-hub doctor` để xem đường dẫn bị thiếu |
| Lỗi hiển thị tiếng Việt / Gate 1 UTF-8 BOM trên Windows | File lưu kèm BOM hoặc console dùng codepage cũ | Lưu file ở chế độ **UTF-8** (không BOM) và đặt `PYTHONIOENCODING=utf-8` trước khi chạy |

> 📚 **Xem thêm khi cần:** [11 Cổng DoD](QUALITY_GATES.md) • [Cẩm Nang CLI Đầy Đủ](CLI_REFERENCE.md)
