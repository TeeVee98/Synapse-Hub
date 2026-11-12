# 🛡️ Tiêu Chuẩn 11 Cổng Chất Lượng DoD (Definition of Done)

[🇻🇳 Tiếng Việt](QUALITY_GATES.md) | [🇬🇧 English Edition](QUALITY_GATES.en.md)

> **Phạm vi:** Hệ thống chốt chặn tự động kiểm tra 11 Cổng Chất Lượng bắt buộc trên Synapse Hub và các dự án kiểm thử con.  
> **Lệnh thực thi:** `python3 tools/verify_all.py` hoặc `npx synapse-hub verify`  
> **Bảo toàn tác quyền:** Synapse Hub được sáng lập bởi **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) theo giấy phép MIT.

---

## 📋 Bảng Tổng Quan 11 Cổng Kiểm Định Chất Lượng

| Cổng | Tên Cổng | Phạm Vi Quét | Công Cụ Kiểm Tra | Mã Thoát | Tiêu Chuẩn Đạt (DoD) |
| :---: | :--- | :--- | :--- | :---: | :--- |
| **Gate 0** | **Bảo Toàn Tác Quyền & Giấy Phép MIT** | Toàn bộ repo | `tools/author_integrity.py` | 0 | Giữ nguyên thông báo bản quyền MIT và tác giả gốc Thế Vị (@TeeVee98). |
| **Gate 1** | **Chuẩn Mã Hóa UTF-8 No BOM** | Toàn bộ file code & config | `tools/verify_all.py` | 0 | 100% file không chứa ký tự BOM rác (`0xEF, 0xBB, 0xBF`). |
| **Gate 2** | **Đường Dẫn Linh Hoạt (Path Portability)** | Code test & script công cụ | `tools/verify_all.py` | 0 | Không hardcode đường dẫn tuyệt đối của máy cá nhân (`/Users/...`, `C:\...`). |
| **Gate 3** | **Kiến Trúc Clean POM (Flat Architecture)** | Thư mục test (`tests/`, `Scripts/`) | `tools/verify_all.py` | 0 | 100% locator nằm trong Page Class; không để XPath/CSS selector trong file test. |
| **Gate 4** | **Chống Bịa Đặt Tài Liệu AI (Anti-Drift)** | `PROJECT_AI_GUIDE.md` & AST code | `tools/lint_ai_docs.py` | 0 | 0 PageClass ảo; 100% hàm tài liệu hóa phải tồn tại thật trong AST codebase. |
| **Gate 5** | **Chặn File Rác Lọt Vào Git** | Toàn bộ cây thư mục | `tools/verify_all.py` | 0 | Không để file rác, file tạm lọt vào git (`*.tmp`, `.ruff_cache`, heap dump, log). |
| **Gate 6** | **Quét Mật Khẩu & Token Bí Mật** | Toàn bộ file & git index | `tools/verify_all.py` | 0 | Không commit mật khẩu dạng plaintext, API key, token JWT hoặc private key. |
| **Gate 7** | **Bắt Lỗi Tĩnh & Test Pass Ảo** | File test & công cụ | `tools/infer_linter.py` | 0 | Chặn đứng test 0 assert, try-catch nuốt lỗi (`pass`), dùng sleep cứng (>= 3000ms). |
| **Gate 8** | **Đo Độ Nhạy Của Assert (Mutation Score)** | Toàn bộ câu lệnh assert | `tools/micro_mutator.py` | 0 | Tỷ lệ diệt đột biến $\ge 80\%$ (bắt được ít nhất 80% đột biến cú pháp cố ý). |
| **Gate 9** | **Điều Phối Kỹ Năng Tránh Trùng Lặp** | File `SKILL.md` của các skill | `tools/skill_collision_guard.py` | 0 | Mô tả kích hoạt kỹ năng không được đè phạm vi của nhau (cosine similarity < 0.75). |
| **Gate 10** | **Kiểm Soát Hiệu Năng & Tiêu Chuẩn SLA** | `Reports/perf/` (`.jtl`, `.csv`, `summary.json`) | `tools/verify_all.py` | 0 | Đạt chuẩn SLA (P95 $\le$ 500ms, P99 $\le$ 1000ms, Error Rate $\le$ 1.0%); tự động SKIPPED/PASS khi dự án không chạy test tải. |

---

## 🔍 Chi Tiết Tiêu Chuẩn Từng Cổng & Cách Khắc Phục

### Gate 0: Bảo Toàn Tác Quyền & Giấy Phép MIT
- **Mục tiêu:** Bảo vệ nguồn gốc xuất xứ và tuân thủ điều khoản Attribution bắt buộc của Giấy phép MIT.
- **Quy tắc kiểm tra:** Chặn đứng mọi hành vi xóa bỏ notice bản quyền, mạo nhận quyền tác giả hoặc gỡ tên tác giả Thế Vị (@TeeVee98).
- **Cách khắc phục:** Khôi phục lại header bản quyền và thông tin nguồn gốc trong `LICENSE` và `NOTICE`.

### Gate 1: Chuẩn Mã Hóa UTF-8 No BOM
- **Mục tiêu:** Tránh lỗi vỡ font hoặc xung đột đọc file giữa Windows, macOS và môi trường Linux CI/CD.
- **Quy tắc kiểm tra:** Quét raw bytes của tất cả file văn bản. Báo lỗi ngay nếu xuất hiện ký tự BOM (`0xEF, 0xBB, 0xBF`).
- **Cách khắc phục:** Chạy `python3 tools/verify_all.py --fix-bom` để công cụ tự động dọn sạch byte BOM.

### Gate 2: Đường Dẫn Linh Hoạt (Path Portability)
- **Mục tiêu:** Đảm bảo code test và script công cụ chạy được trên mọi máy dev, Docker container và CI runner.
- **Quy tắc kiểm tra:** Dùng regex quét tìm các path gắn cứng theo máy cục bộ (`/Users/`, `/home/`, `C:\`, `D:\`).
- **Cách khắc phục:** Dùng đường dẫn tương đối phân giải từ thư mục gốc (`Path(__file__).resolve().parent.parent` hoặc `resolve_target_repo()`).

### Gate 3: Kiến Trúc Clean POM (Flat Architecture)
- **Mục tiêu:** Phân định ranh giới rõ ràng: file test chỉ chứa các bước nghiệp vụ, tuyệt đối không chọc thẳng vào DOM.
- **Quy tắc kiểm tra:** Cấm selector thô (CSS selector, XPath, `findTestObject`) trong thư mục `tests/` hoặc `Scripts/`. Thao tác UI phải thông qua hàm của Page Class kế thừa `BasePage`.
- **Cách khắc phục:** Đưa locator và thao tác click/nhập liệu vào đúng Page Class tương ứng.

### Gate 4: Chống Bịa Đặt Tài Liệu AI (Anti-Drift Linter)
- **Mục tiêu:** Tránh hiện tượng AI bị "ảo giác" (hallucination), đọc tài liệu cũ rồi gọi các Page Class hoặc hàm không hề tồn tại trong code.
- **Quy tắc kiểm tra:** Quét toàn bộ Page Class và method được ghi trong `PROJECT_AI_GUIDE.md`, kiểm tra xem chúng có tồn tại thật trong AST codebase hay không.
- **Cách khắc phục:** Chạy `python3 tools/lint_ai_docs.py` để tìm dòng sai lệch, sau đó chạy `python3 tools/repo_map.py` để đồng bộ lại bản đồ code.

### Gate 5: Chặn File Rác Lọt Vào Git
- **Mục tiêu:** Giữ git index luôn sạch sẽ, không bị phình dung lượng bởi rác build hoặc cache IDE.
- **Quy tắc kiểm tra:** Quét các đuôi file cấm: `*.tmp`, `*.dump`, `*.log`, `*.orig`, `*.bak`, `.ruff_cache/`, `.mypy_cache/`.
- **Cách khắc phục:** Khai báo các mẫu file này vào `.gitignore` và xóa bỏ các file tạm hiện có trong repo.

### Gate 6: Quét Mật Khẩu & Token Bí Mật (Secret Sentinel)
- **Mục tiêu:** Chống rò rỉ thông tin nhạy cảm của dự án (API token, chuỗi kết nối DB, private key, mật khẩu).
- **Quy tắc kiểm tra:** Quét regex entropy cao để phát hiện chuỗi khóa bí mật AWS, Bearer token, RSA key và mật khẩu bị gán cứng.
- **Cách khắc phục:** Chuyển sang dùng biến môi trường hoặc file `.env` (nhớ thêm `.env` vào `.gitignore`).

### Gate 7: Bắt Lỗi Tĩnh & Test Pass Ảo
- **Mục tiêu:** Loại bỏ triệt để các bài test do AI viết chạy xanh nhưng thực chất là vô dụng:
- **Quy tắc kiểm tra:**
  - Bắt các bài test có **0 câu lệnh assert**.
  - Bắt các khối try-catch rỗng (`except Exception: pass`) nuốt mất lỗi khi test fail.
  - Bắt các lệnh sleep cứng (`sleep(5000)`, `Thread.sleep(5000)`).
  - Bắt assertion của Playwright bị quên `await` (`expect(el).toBeVisible()` thiếu `await`).
- **Cách khắc phục:** Bổ sung assert thực tế; thay toàn bộ `sleep` cố định bằng smart wait (`waitForLoadState('networkidle')`, kiểm tra element hiển thị).

### Gate 8: Đo Độ Nhạy Của Assert (Micro-Mutation Testing)
- **Mục tiêu:** Đảm bảo các câu lệnh assert có giá trị kiểm thử thật sự, không phải là biểu thức "luôn luôn đúng" (tautology).
- **Quy tắc kiểm tra:** Tự động tiêm các đột biến cú pháp (đổi `==` thành `!=`, đảo boolean `True` sang `False`, thay giá trị return). Yêu cầu test phải bắt trượt và diệt được ít nhất 80% đột biến (Mutation Score $\ge 80\%$).
- **Cách khắc phục:** Chạy `python3 tools/micro_mutator.py --strict` để xem mutant nào còn sống sót và siết chặt lại assertion.

### Gate 9: Điều Phối Kỹ Năng Tránh Trùng Lặp
- **Mục tiêu:** Tránh việc AI kích hoạt nhầm kỹ năng do mô tả trong các file `SKILL.md` bị chồng chéo nhau.
- **Quy tắc kiểm tra:** Tính độ tương đồng cosine giữa phần mô tả của từng cặp kỹ năng. Yêu cầu chỉ số tương đồng phải $< 0.75$.
- **Cách khắc phục:** Viết lại mô tả kỹ năng theo công thức chuẩn: `[Tính năng] + Dùng khi [ngữ cảnh cụ thể]` (tối đa 350 ký tự).

### Gate 10: Kiểm Soát Hiệu Năng & SLA (Performance & SLA Sentinel)
- **Mục tiêu:** Chặn đứng các bản build hoặc mã gây suy thoái độ trễ nghiêm trọng (latency regressions hoặc lỗi quá ngưỡng) trước khi merge hoặc deploy.
- **Quy tắc kiểm tra:** Tự động phát hiện và phân tích kết quả chạy tải trong `Reports/perf/` (`.jtl`, `.csv`, `k6_summary.json`). Báo lỗi (Exit Code 1) nếu P95 > 500ms, P99 > 1000ms hoặc Error Rate > 1.0%. Tự động ghi nhận `PASS (SKIPPED)` trong < 1ms nếu dự án không phát sinh file kết quả chạy tải.
- **Cách khắc phục:** Tối ưu hóa API/DB query, kiểm tra tài nguyên hệ thống, hoặc tùy chỉnh lại ngưỡng SLA trong `synapse.config.json` theo yêu cầu dự án.

---

## 🚀 Cách Chạy & Tích Hợp Vào CI/CD

### Chạy Cục Bộ Trên Máy:
```bash
# Kiểm định toàn bộ 11 Cổng trên repo hiện tại
python3 tools/verify_all.py

# Kiểm định dự án test mục tiêu từ Hub
python3 tools/verify_all.py --target /duong-dan/toi/du-an-test

# Xuất kết quả ra file JUnit XML để CI/CD đọc
python3 tools/verify_all.py --format junit --output reports/dod_gates.xml
```

### Đường Ống GitHub Actions (`.github/workflows/verify.yml`):
```yaml
name: Synapse Hub 11 DoD Quality Gates
on: [push, pull_request]

jobs:
  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Run 11 Quality Gates
        run: python tools/verify_all.py --mode target
```
