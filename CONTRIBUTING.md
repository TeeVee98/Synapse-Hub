# Hướng Dẫn Đóng Góp / Contributing to Synapse-Hub

[🇻🇳 Tiếng Việt](#-hướng-dẫn-đóng-góp-tiếng-việt) | [🇬🇧 English Edition](#-english-edition)

---

## 🇻🇳 Hướng Dẫn Đóng Góp (Tiếng Việt)

Chúng tôi rất hoan nghênh các đóng góp từ cộng đồng nhằm mở rộng kỹ năng (Skills), công cụ (Tools) và các quy chuẩn kiểm thử trong hệ sinh thái **Synapse-Hub**. Mọi đóng góp đều cần tuân thủ triệt để nguyên tắc **Truth Anchor** (chống pass ảo, trung thực kỹ thuật) và **Tiết kiệm Token**.

### 1. Quy Chuẩn Viết Kỹ Năng Mới (Skill Standards)

Mỗi kỹ năng nằm trong thư mục `.agents/skills/<category>/<tên-kỹ-năng>/` (thuộc 1 trong 11 nhóm domain) và cần đáp ứng:

1. **Cấu trúc tệp `SKILL.md`:**
   - Bắt buộc có phần mở đầu YAML frontmatter chuẩn xác chứa `name` và `description`.
   - `name` phải trùng khớp 100% với tên thư mục (dạng `kebab-case`).
   - `description` mô tả rõ ràng phạm vi kích hoạt, phân biệt rành mạch với các kỹ năng lân cận để tránh xung đột prompt.
2. **Ngắn Gọn & Tiết Kiệm Token:**
   - Hướng dẫn kỹ thuật viết bằng tiếng Anh ngắn gọn, chuẩn xác để tối ưu hóa lượng token ngữ cảnh cho AI.
   - Áp dụng nguyên lý nạp thông tin lũy tiến (Progressive Disclosure): giữ `SKILL.md` trong khoảng 40 đến 150 dòng; các đoạn code mẫu chi tiết đưa vào `examples/` hoặc `references/`.
3. **Không Ràng Buộc Vào Dự Án Cụ Thể (Decoupled):**
   - Tuyệt đối không gán cứng tên dự án riêng tư, domain bí mật, mật khẩu hay endpoint nội bộ.
   - Luôn sử dụng định danh mẫu: `https://staging.example.com`, `auto_user_123`.

### 2. Quy Trình Kiểm Thử Trước Khi Mở Pull Request

Trước khi gửi PR hoặc đẩy code lên nhánh `develop`:

```bash
# 1. Chạy toàn bộ 170+ bài kiểm thử đơn vị
python3 -m unittest discover tests

# 2. Kiểm định toàn vẹn 9 Cổng Chất Lượng DoD
python3 tools/verify_all.py

# 3. Kiểm tra tính toàn vẹn của tài liệu và công cụ
python3 tools/lint_ai_docs.py
```

### 3. Nguyên Tắc Phát Triển Công Cụ (Tools)

Mọi công cụ tiện ích trong `tools/` cần tuân thủ:
1. **Ưu Tiên Thư Viện Chuẩn Python (Standard Library):** Hạn chế tối đa thư viện bên ngoài để công cụ chạy được ngay trên máy sạch và CI mà không cần cài đặt phức tạp.
2. **Tốc Độ Xử Lý Siêu Tốc:** Các phép quét AST và regex phải hoàn tất dưới 500ms.
3. **Không Ghi Rác Vào Repo:** Khi viết test, bắt buộc sử dụng thư mục tạm `tempfile.TemporaryDirectory()`, không để lại file rác trong repo.
4. **Thông Báo Lỗi Thân Thiện:** Luôn cung cấp gợi ý sửa lỗi rõ ràng (`Fix Hint`) thay vì chỉ in ra stacktrace thô.

---

## 🇬🇧 English Edition

We welcome contributions to expand and refine skills, tools, and rules in the **Synapse-Hub** ecosystem. All contributions must adhere to our **Truth Anchor** (no fake passes) and **Token-Efficiency** standards.

### 1. Skill Authoring Standards

Every skill resides in `.agents/skills/<category>/<skill-name>/` (across 11 domain categories) and must satisfy:

1. **`SKILL.md` Structure:**
   - Must contain valid YAML frontmatter with `name` and `description`.
   - `name` must exactly match the directory name in kebab-case.
   - `description` must clearly articulate the triggering scope and disambiguate itself from adjacent skills.
2. **Conciseness & Token Budget:**
   - Write instructions in concise technical English to minimize LLM token consumption.
   - Use progressive disclosure: keep `SKILL.md` between 40 and 150 lines, and offload deep code patterns to `references/` or `examples/`.
3. **Zero Project Coupling:**
   - Never hardcode specific project names, proprietary URLs, test credentials, or internal namespaces.
   - Always use generic placeholders: `<project_namespace>`, `https://app.example.com`, `APP_PASSWORD`.

### 2. Integrity Verification Workflow

Before submitting a pull request or committing changes:

```bash
# 1. Run regression test suite (770+ tests)
pytest tests -q

# 2. Verify all 10 DoD Quality Gates
python3 tools/verify_all.py

# 3. Test documentation and entity references integrity
python3 tools/lint_ai_docs.py
```

### 3. Tool Development Guidelines

All helper scripts in `tools/` must:
1. **Rely on Standard Libraries:** Minimize third-party package dependencies so tools execute seamlessly across clean host machines and CI pipelines.
2. **Be Fast & Non-Blocking:** AST scans and regex lookups must complete in under 500ms.
3. **Zero Test File Pollution:** Tests must use `tempfile.TemporaryDirectory()` and never write temporary test artifacts to the repository tree.
4. **Handle Errors Gracefully:** Provide clear remedies and pointers rather than dumping raw stack traces.
