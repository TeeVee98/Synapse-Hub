# Cẩm Nang Tra Cứu Lệnh CLI & Công Cụ Synapse-Hub

[🇻🇳 Tiếng Việt](CLI_REFERENCE.md) | [🇬🇧 English Edition](CLI_REFERENCE.en.md)

Hệ sinh thái Synapse Hub cung cấp công cụ dòng lệnh `synapse-hub` (hoặc `agent-qa`, cùng các script Python trực tiếp trong `tools/`) để kiểm định chất lượng, lint code test, phân tích tác động và cô đọng log CI.

---

## 1. Điểm Vào Dòng Lệnh Thống Nhất (`synapse-hub` / `agent-qa`)

Sau khi cài đặt qua `npm install -g synapse-hub` hoặc `pip install -e .`, bạn có thể gõ trực tiếp:

```bash
synapse-hub <lệnh> [tùy_chọn]
# hoặc
agent-qa <lệnh> [tùy_chọn]
```

### Danh Mục 53 Lệnh Hỗ Trợ

#### A. Cốt Lõi Kiểm Định & 11 Cổng DoD
| Lệnh | Nhóm Chức Năng | Mô Tả Thực Tế | Ví Dụ |
| :--- | :--- | :--- | :--- |
| `verify` | Gác Cổng DoD | Chạy toàn diện 11 Cổng Chất Lượng trước khi commit/push | `synapse-hub verify` |
| `lint` | Bắt Lỗi Tĩnh | Quét lỗi tĩnh, bắt test 0-assert, try-catch nuốt lỗi (TS, Python, Groovy) | `synapse-hub lint ./tests` |
| `mutate` | Kiểm Thử Đột Biến | Bắn vi đột biến kiểm tra độ nhạy của các câu lệnh assert | `synapse-hub mutate ./tests --min-score 80` |
| `watch` | HUD Thời Gian Thực | Tự động quét và báo lỗi ngay khi có file code thay đổi | `synapse-hub watch` |
| `wcag-audit` | Khả Năng Tiếp Cận | Kiểm toán chuẩn accessibility WCAG 2.2 và độ tương phản màu | `synapse-hub wcag-audit ./reports/WELCOME.html` |
| `trace-data-flow` | Dòng Dữ Liệu | Lần vết vòng đời dữ liệu test để phát hiện rò rỉ cơ sở dữ liệu | `synapse-hub trace-data-flow ./tests` |
| `verify-author` | Bản Quyền Tác Giả | Kiểm tra tính toàn vẹn của watermark tác giả và giấy phép MIT | `synapse-hub verify-author` |
| `debt` | Nợ Kỹ Thuật | Gom toàn bộ chú thích `shortcut:` trong code thành sổ cái nợ | `synapse-hub debt` |
| `review` | Senior Review | Review thay đổi code theo 6 trụ cột (Lỗi, Bảo mật, Quy mô, Test, Tốc độ, Rác) | `synapse-hub review` |

#### B. Chẩn Đoán Môi Trường, Khởi Tạo & Tiện Ích
| Lệnh | Nhóm Chức Năng | Mô Tả Thực Tế | Ví Dụ |
| :--- | :--- | :--- | :--- |
| `doctor` | Kiểm Tra Môi Trường | Chẩn đoán 1-click cho Node.js, Python, Chrome, Git | `synapse-hub doctor` |
| `welcome` | Trang Hướng Dẫn | Mở trang landing giới thiệu trực quan trên trình duyệt | `synapse-hub welcome` |
| `setup` | Khởi Tạo Dự Án | Bootstrap dự án test, tự tạo AI Guide và kết nối các AI Bridge | `synapse-hub setup --local-only` |
| `uninstall` | Gỡ Bỏ Cấu Hình | Gỡ sạch các AI Bridge, git hook và file cấu hình tạm | `synapse-hub uninstall` |
| `sync-rules` | Đồng Bộ Quy Tắc AI | Đồng bộ nội dung AGENTS.md tới Cursor, Claude, Copilot, Windsurf | `synapse-hub sync-rules` |
| `version` | Xem Phiên Bản | Hiển thị phiên bản Hub và danh mục kỹ năng hiện có | `synapse-hub version` |
| `update` | Cập Nhật 1-Click | Tự động kéo bản cập nhật mới nhất từ kho lưu trữ trung tâm | `synapse-hub update` |
| `clean` | Dọn Dẹp File Rác | Xóa sạch các file tạm thời, cache và log thừa trong repo | `synapse-hub clean` |

#### C. Tự Sửa Lỗi, Khám Nghiệm Thất Bại & Nén Log
| Lệnh | Nhóm Chức Năng | Mô Tả Thực Tế | Ví Dụ |
| :--- | :--- | :--- | :--- |
| `heal` | Bộ Nhớ Tra Cứu | Tra cứu cách sửa lỗi đã được kiểm chứng (0 tốn token AI) | `synapse-hub heal query "StaleElement"` |
| `auto-heal` | Tự Động Sửa Test | Tự động đọc file JUnit XML lỗi và cập nhật lại locator bị hỏng | `synapse-hub auto-heal` |
| `heal-pr` | Mở PR Sửa Lỗi | Tự tạo nhánh Git và mở Pull Request kèm bản vá sửa test | `synapse-hub heal-pr --branch heal/fix-login` |
| `distill` | Nén Log CI | Lọc sạch 95% log thừa, chỉ giữ lại đúng stacktrace nguyên nhân gốc | `synapse-hub distill build.log` |
| `pinpoint-failure` | Khám Nghiệm Lỗi | Phân tích file JUnit XML, chỉ ra ngay dòng code gây fail trong 0.1s | `synapse-hub pinpoint-failure report.xml` |
| `flaky` | Cách Ly Test Chập Chờn | Nhận diện test chạy chập chờn (flaky) và đưa vào vùng cách ly | `synapse-hub flaky --detect` |
| `lookup-tc` | Tra Cứu Test Case | Tìm nhanh test case theo ID, tag, độ ưu tiên hoặc tên luồng | `synapse-hub lookup-tc TC-101` |
| `lookup-xpath` | Bộ Nhớ Locator | Tìm locator hoặc XPath ổn định đã được cache trong bộ nhớ | `synapse-hub lookup-xpath "Submit"` |
| `impact` | Đo Bán Kính Ảnh Hưởng | Phân tích AST xem thay đổi git diff ảnh hưởng tới những test nào | `synapse-hub impact --git-diff` |
| `canary` | Thao Trường Phục Hồi | Thử nghiệm tiêm lỗi để đo tốc độ tự phục hồi MTTR của agent | `synapse-hub canary --run` |
| `report-bug` | Tạo Báo Cáo Bug | Xuất báo cáo lỗi chuẩn Markdown/Jira từ phân tích nguyên nhân gốc | `synapse-hub report-bug --junit report.xml` |
| `ci-hook` | Hook Tự Động Trên CI | Chạy tự động phân tích nguyên nhân ngay khi build CI bị fail | `synapse-hub ci-hook --log ci.log` |
| `tokens` | Đo Đếm Token | Đếm chính xác số lượng token của prompt hoặc tài liệu | `synapse-hub tokens path/to/prompt.md` |

#### D. Kiểm Thử API, Hiệu Năng & Bảo Mật
| Lệnh | Nhóm Chức Năng | Mô Tả Thực Tế | Ví Dụ |
| :--- | :--- | :--- | :--- |
| `fuzz-api` | Fuzzing API | Quét fuzzing bảo mật, boundary & chaos test cho API (chỉ non-prod) | `synapse-hub fuzz-api --spec openapi.json` |
| `contract-drift` | Bắt Lệch Hợp Đồng API | Phát hiện breaking changes và schema drift so với bản baseline | `synapse-hub contract-drift --baseline v1.json --current v2.json` |
| `generate-jmx` | Sinh Kịch Bản Tải | Biên dịch User Story / API spec thành kịch bản Apache JMeter JMX | `synapse-hub generate-jmx --threads 50` |
| `analyze-jtl` | Phân Tích Kết Quả Tải | Đọc log JMeter JTL và kiểm định các ngưỡng SLA thời gian phản hồi | `synapse-hub analyze-jtl results.jtl` |
| `analyze-newman` | Đánh Giá Chạy Postman | Đọc file JSON kết quả chạy Newman để đánh giá chất lượng API | `synapse-hub analyze-newman newman_run.json` |
| `export-postman` | Xuất Bộ Sưu Tập Postman | Xuất file đặc tả OpenAPI thành Postman Collection v2.1 | `synapse-hub export-postman --spec swagger.json` |
| `mock-shield` | Giả Lập Route Mạng | Tự động sinh route mock mạng cho Playwright từ OpenAPI spec | `synapse-hub mock-shield --spec openapi.json` |
| `skillspector` | Rà Soát Bảo Mật AI | Quét các kỹ năng AI Agent và cấu hình MCP chống prompt injection | `synapse-hub skillspector --dir .agents/skills` |
| `safety-check` | Tường Lửa Thao Tác | Kiểm tra snippet code để chặn các hành động UI có tính phá hủy | `synapse-hub safety-check --snippet "btn.click()"` |

#### E. Sinh Mã, Chuyển Đổi Framework & Báo Cáo
| Lệnh | Nhóm Chức Năng | Mô Tả Thực Tế | Ví Dụ |
| :--- | :--- | :--- | :--- |
| `generate-tc` | Biên Dịch User Story | Chuyển đổi User Story ngôn ngữ tự nhiên thành test case Clean POM | `synapse-hub generate-tc story.md` |
| `export-excel` | Xuất Báo Cáo Excel | Xuất các test case Markdown thành file Excel 12 cột tiêu chuẩn | `synapse-hub export-excel` |
| `gherkin` | Biên Dịch BDD | Biên dịch file Gherkin .feature thành kịch bản test thực thi | `synapse-hub gherkin specs/checkout.feature` |
| `transpile` | Chuyển Đổi Framework | Chuyển đổi mã test qua lại giữa Playwright, Pytest, Katalon | `synapse-hub transpile tests/spec.ts --to pytest` |
| `omni-scan` | Nhận Diện Framework | Tự động quét repo để nhận diện framework test đang sử dụng | `synapse-hub omni-scan` |
| `shard` | Phân Mảnh Chạy Song Song | Chia đều test suite thành nhiều phần để chạy song song trên CI | `synapse-hub shard ./tests --runners 4` |
| `visual-mask` | Tạo Mask Chống Flaky | Tính toán tọa độ che các vùng động khi so sánh screenshot UI | `synapse-hub visual-mask screenshot.png` |
| `som` | Đánh Dấu UI Cho Vision AI | Tiện ích Set-of-Marks đánh dấu số thứ tự lên phần tử giao diện | `synapse-hub som screen.png` |
| `decouple-config`| Tách Biệt Cấu Hình | Tách rời biến môi trường và mật khẩu ra khỏi mã nguồn test | `synapse-hub decouple-config config.groovy` |
| `correlate-telemetry` | Đối Chiếu Log Đa Kênh | Khớp nối dấu vết browser trace, HTTP log và server log khi debug | `synapse-hub correlate-telemetry --trace trace.zip` |
| `dashboard` | Bảng Điều Khiển HUD | Tạo bảng điều khiển HTML5 tổng quan sức khỏe dự án test | `synapse-hub dashboard` |
| `analyze` | Kiểm Toán Toàn Diện | Báo cáo sức khỏe dự án 5-trong-1 và kiểm định 11 cổng DoD | `synapse-hub analyze` |
| `mcp-serve` | Khởi Chạy Máy Chủ MCP | Chạy máy chủ Model Context Protocol (MCP) qua giao thức stdio | `synapse-hub mcp-serve` |

---

## 2. Hướng Dẫn Chạy Trực Tiếp Qua Script Python

Nếu bạn không muốn cài đặt package toàn cục, toàn bộ công cụ đều có thể chạy trực tiếp bằng Python:

### 2.1. Chạy 11 Cổng Kiểm Định DoD (Gate 0 - Gate 10)
```bash
# Tự động nhận diện chế độ (mặc định: tự phát hiện Hub hoặc Dự án test con)
python tools/verify_all.py

# Chọn chế độ rõ ràng
python tools/verify_all.py --mode hub      # Kiểm tra tính toàn vẹn của QA Hub
python tools/verify_all.py --mode target   # Kiểm định dự án kiểm thử thực tế
```
- **Ý Nghĩa Các Chế Độ:**
  - `--mode hub`: Kiểm tra tài nguyên của Hub, tính toàn vẹn của các kỹ năng, công cụ, không byte BOM rác, đường dẫn linh hoạt và bảo mật secret trên toàn bộ repo mà không bắt buộc có file test nghiệp vụ.
  - `--mode target`: Bắt buộc tuân thủ chuẩn kiểm thử cho dự án thực tế: 100% selector nằm trong Page Class (Clean POM) và không lộ mật khẩu.
- **Gate 0:** Bảo Toàn Tác Quyền & Giấy Phép MIT (giữ thông báo bản quyền của Thế Vị @TeeVee98).
- **Gate 1:** Quét 100% file không chứa ký tự UTF-8 BOM rác.
- **Gate 2:** Đường Dẫn Linh Hoạt (không hardcode path máy cá nhân).
- **Gate 3:** Kiến Trúc Clean POM (Flat Architecture) (không chứa XPath/CSS selector trong file test).
- **Gate 4:** Chống Bịa Đặt Tài Liệu AI (không nhắc tới class hay hàm ảo giác).
- **Gate 5:** Dọn dẹp sạch file tạm thời, file rác build và sandbox.
- **Gate 6:** Quét Bảo Mật Thông Tin Nhạy Cảm (chặn mật khẩu và token bị hardcode).
- **Gate 7:** Bắt Lỗi Tĩnh & Test Pass Ảo (Meta Infer-style).
- **Gate 8:** Đo Độ Nhạy Assert Bằng Micro-Mutation (yêu cầu điểm diệt mutant >= 80%).
- **Gate 9:** Điều Phối Kỹ Năng Tránh Trùng Lặp (độ tương đồng cosine < 0.75).
- **Gate 10:** Chốt Chặn Hiệu Năng & SLA (kiểm định P95 <= 500ms, P99 <= 1000ms, Error Rate <= 1.0% từ k6, JMeter, Playwright CWV).

### 2.2. Quét Lỗi Tĩnh & Bắt Test Pass Ảo AST
```bash
python tools/infer_linter.py
```

### 2.3. Bộ Nhớ Ngữ Nghĩa & Danh Sách Đen Chống Lặp Lại Sai Lầm
```bash
# Khởi tạo database với giải pháp mẫu và các bản vá cấm kỵ
python tools/cache_resolver.py init

# Tra cứu bản vá đã kiểm chứng VÀ lấy danh sách bản vá cấm kỵ (0 tốn token)
python tools/cache_resolver.py query --error "ElementClickInterceptedException"

# Lưu giải pháp chuẩn khi sửa lỗi thành công (Positive Memory)
python tools/cache_resolver.py learn --error "Timeout" --cause "Slow API" --patch "waitForNetworkIdle()" --symptom "Spinner"

# Lưu lần thử sửa lỗi thất bại vào danh sách đen (Negative Memory để AI không lặp lại)
python tools/cache_resolver.py record-failed --error "StaleElement" --patch "sleep(5000)" --reason "Van fail khi mang lag"
```

### 2.4. Cô Đọng Log Lọc Rác CI
```bash
python tools/distill_log.py execution.log
```

### 2.5. Thu Hoạch Nợ Kỹ Thuật (Technical Debt)
```bash
python tools/debt_harvester.py --scan
python tools/debt_harvester.py --scan ./src --output DEBT_LEDGER.md
```

### 2.6. Senior Review Đánh Giá Code (6 Trụ Cột)
```bash
python tools/senior_code_review.py
python tools/senior_code_review.py --staged
```

---

## 3. Quy Ước Mã Thoát Tiêu Chuẩn (Exit Codes) & Môi Trường Terminal

Synapse Hub áp dụng mã thoát tiêu chuẩn UNIX tất định trên toàn bộ công cụ CLI:

| Mã Thoát | Hằng Số | Ý Nghĩa Thực Tế | Cách Xử Lý |
| :---: | :--- | :--- | :--- |
| **`0`** | `EXIT_SUCCESS` | Thành công; tất cả Cổng Chất Lượng đều đạt; 0 lỗi nghiêm trọng. | Tiến hành bước tiếp theo của pipeline hoặc commit. |
| **`1`** | `EXIT_FAILURE` | Cổng kiểm định từ chối; test bị fail; phát hiện lỗi tĩnh linter. | Đọc chi tiết báo lỗi; bổ sung câu lệnh assert hoặc gỡ khối nuốt ngoại lệ. |
| **`2`** | `EXIT_USAGE_ERROR` | Tham số CLI không hợp lệ; gõ sai lệnh; lỗi cú pháp. | Gõ thêm `--help` sau lệnh để xem cú pháp chuẩn. |
| **`3`** | `EXIT_SECURITY_BLOCK` | Thao tác nguy hiểm bị firewall chặn; lộ token; sửa giấy phép MIT. | Kiểm tra lại vi phạm bảo mật; đặt `ALLOW_DESTRUCTIVE=1` nếu thật sự cố ý. |
| **`4`** | `EXIT_ENVIRONMENT_ERROR` | Môi trường không tương thích; thiếu công cụ bắt buộc (ví dụ Python < 3.9). | Cài đặt runtime khuyến nghị (Python 3.10+, Node 20+). |

### Tiêu Chuẩn Hiển Thị Trên Terminal:
- **Hỗ Trợ `NO_COLOR`:** Tuân thủ chuẩn [no-color.org](https://no-color.org), khi đặt biến môi trường `NO_COLOR`, hệ thống tự tắt mọi mã màu ANSI.
- **Cờ `--quiet` / `-q`:** Thêm cờ `-q` để ẩn bớt banner giới thiệu và chỉ in ra kết quả phán quyết hoặc định dạng dữ liệu cho máy đọc.
- **Định Dạng Dành Cho CI:** Sử dụng `--format json`, `--format sarif`, hoặc `--format junit` để xuất dữ liệu sạch cho các pipeline CI/CD tích hợp tự động.
