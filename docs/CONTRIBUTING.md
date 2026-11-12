# Hướng Dẫn Đóng Góp Vào Synapse-Hub

[🇻🇳 Tiếng Việt](CONTRIBUTING.md) | [🇬🇧 English Edition](CONTRIBUTING.en.md)

Chào mừng bạn tham gia đóng góp mở rộng kỹ năng (Skills), công cụ (Tools) và các quy tắc kiểm thử trong hệ sinh thái **Synapse Hub**. Mọi đóng góp đều cần tuân thủ 2 nguyên tắc then chốt: **Truth Anchor** (chống test pass ảo, trung thực kỹ thuật) và **Tiết Kiệm Token Tối Đa**.

---

## 1. Quy Chuẩn Khi Viết Kỹ Năng Mới (Skill Standards)

Mỗi kỹ năng nằm trong thư mục riêng `.agents/skills/<ten-ky-nang>/` và cần đáp ứng các tiêu chí sau:

1. **Cấu trúc file `SKILL.md`:**
   - Bắt buộc có phần mở đầu YAML frontmatter chuẩn xác chứa `name` và `description`.
   - `name` phải trùng khớp 100% với tên thư mục (định dạng `kebab-case`).
   - `description` phải nêu rõ phạm vi và ngữ cảnh kích hoạt, phân biệt rõ ràng với các kỹ năng khác để AI không bao giờ gọi nhầm.
2. **Ngắn Gọn & Tiết Kiệm Token:**
   - Nội dung chỉ dẫn kỹ thuật viết bằng tiếng Anh ngắn gọn, súc tích để tránh làm đầy ngữ cảnh của AI.
   - Áp dụng nguyên lý tải thông tin lũy tiến (Progressive Disclosure): giữ file `SKILL.md` trong khoảng 40 đến 150 dòng; các đoạn code mẫu dài nên đưa vào thư mục `examples/` hoặc `references/`.
3. **Tuyệt Đối Không Phụ Thuộc Vào Dự Án Cụ Thể (Decoupled):**
   - Không được hardcode tên dự án nội bộ, domain riêng tư, mật khẩu hay endpoint bí mật.
   - Luôn dùng định danh mẫu: `https://staging.example.com`, `auto_user_123`.

---

## 2. Quy Trình Kiểm Thử Trước Khi Mở Pull Request

Trước khi mở PR hoặc đẩy code lên nhánh `develop`:

```bash
# 1. Chạy toàn bộ 260+ bài unit test
python3 -m unittest discover tests

# 2. Kiểm định toàn vẹn 10 Cổng Chất Lượng DoD (Gate 1–10)
python3 tools/verify_all.py

# 3. Kiểm tra tính toàn vẹn của tài liệu và công cụ
python3 tools/lint_ai_docs.py
```

---

## 3. Nguyên Tắc Phát Triển Công Cụ Mới (Tools)

Mọi công cụ tiện ích trong thư mục `tools/` cần tuân thủ:
1. **Ưu Tiên Thư Viện Chuẩn Python (Standard Library):** Hạn chế tối đa thư viện bên ngoài để công cụ chạy được ngay trên máy sạch và CI mà không cần `pip install` phức tạp.
2. **Tốc Độ Xử Lý Phải Nhanh:** Các phép quét AST và regex phải hoàn tất dưới 500ms.
3. **Không Làm Bẩn Repo:** Khi viết test cho công cụ, bắt buộc dùng thư mục tạm `tempfile.TemporaryDirectory()`, không được để lại bất kỳ file rác nào trong repo.
4. **Báo Lỗi Thân Thiện Kèm Cách Sửa:** Luôn cung cấp gợi ý khắc phục (`Fix Hint`) rõ ràng thay vì chỉ in ra stacktrace thô.
