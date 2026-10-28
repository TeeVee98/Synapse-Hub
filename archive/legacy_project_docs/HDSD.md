# Hướng Dẫn Sử Dụng & Quy Chuẩn Kiểm Thử Automation DMIT (HDSD)

- **Hệ thống:** DMIT – Quản lý Cơ sở dữ liệu ngành Công Thương
- **Phiên bản tài liệu:** 2.0 (Cập nhật quy mô 259 Test Cases)
- **Môi trường:** DEMO (`https://doit-demo.vnptit.vn/dmit/auth`)
- **Project path:** Thư mục gốc dự án (Repository Root)
- **Quy mô kịch bản:** **259 Test Cases** (`TC-1` đến `TC-259`) thuộc 9 phân hệ chức năng
- **Mục đích:** Tài liệu hướng dẫn sử dụng trung tâm, hợp nhất quy chuẩn kiểm thử (Testing Standards), hướng dẫn viết/sửa script Katalon, khảo sát locator, quản lý dữ liệu kiểm thử và xử lý các tình huống đặc thù trên giao diện PrimeNG của hệ thống DMIT.

---

## 1. Điều Kiện Đánh Giá PASS / FAIL

### 1.1. Nguyên tắc không báo PASS ảo (Zero False-Positive)
- **Không công nhận PASS** nếu script chỉ thực hiện `navigateToUrl`, `delay` hoặc click mà không có bước xác minh kết quả.
- **Bắt buộc có Assertion nghiệp vụ trên DOM:** Mọi testcase phải xác nhận sự thay đổi trạng thái thực tế của hệ thống sau mỗi hành động:
  - **Luồng Tạo mới (Chỉ tiêu, Người dùng, Phòng ban, Quy hoạch, Dữ liệu, Token):** Điền form, bấm Lưu, đợi đóng dialog VÀ xác nhận bản ghi mới hiển thị trên danh sách bảng (hoặc số dòng tăng lên).
  - **Luồng Cập nhật:** Tìm đúng bản ghi, mở form sửa, thay đổi dữ liệu, lưu lại và xác nhận giá trị mới hiển thị chính xác trên đúng dòng đó.
  - **Luồng Xóa:** Ghi nhận tên bản ghi, bấm Xóa, xác nhận modal `[Xác nhận]`, kiểm tra bản ghi biến mất hoàn toàn khỏi bảng.
  - **Luồng Đăng nhập:** Kiểm tra URL chuyển khỏi `/auth` và hiển thị avatar hoặc tên người dùng đăng nhập.
  - **Luồng Đăng xuất:** Bấm Đăng xuất, xác nhận URL chuyển về màn hình đăng nhập và không còn token trong session.

### 1.2. Không phụ thuộc hoàn toàn vào Toast Notification
- PrimeNG Toast có thể biến mất rất nhanh (sau 2-3 giây) hoặc ngược lại, hiển thị toast thành công nhưng API phía sau gặp lỗi (dữ liệu chưa được ghi vào CSDL).
- **Quy chuẩn:** Bắt buộc kết hợp kiểm tra Toast (nếu có) VỚI việc kiểm tra trực tiếp bảng dữ liệu (`p-table`) hoặc thông tin chi tiết trên màn hình.

### 1.3. Phạm vi sử dụng `FailureHandling.OPTIONAL`
- **Chỉ sử dụng cho các bước phụ:** Ví dụ tắt thông báo trôi nổi, đóng tooltip, hoặc kiểm tra xem nút đóng modal có xuất hiện hay không.
- **TUYỆT ĐỐI KHÔNG bọc `OPTIONAL` quanh các bước cốt lõi:** Các bước click nút Lưu, điền dữ liệu bắt buộc và các câu lệnh `verify...` khẳng định kết quả chính PHẢI dùng `FailureHandling.STOP_ON_FAILURE` để phát hiện lỗi ngay khi xảy ra.

---

## 2. Đặc Thù Kỹ Thuật & Tương Tác Giao Diện Hệ Thống DMIT

### 2.1. Thiết lập Ngôn ngữ Tiếng Việt qua LocalStorage
Hệ thống DMIT dựa vào khóa `lang` và `ng-prime-language` trong `localStorage` để hiển thị giao diện tiếng Việt. Trong tất cả kịch bản, luôn khởi tạo:

```groovy
WebUI.executeJavaScript("localStorage.setItem('lang', 'vi');", null)
WebUI.executeJavaScript("localStorage.setItem('ng-prime-language', 'vi');", null)
WebUI.refresh()
WebUI.waitForPageLoad(10)
```

### 2.2. Xử lý các thành phần giao diện PrimeNG

#### A. Dropdown (`p-dropdown`)
- Thao tác: Click vào `div.p-dropdown` $\rightarrow$ Đợi danh sách `p-dropdown-items` hiển thị $\rightarrow$ Click vào mục mong muốn:
  `//li[contains(@class,'p-dropdown-item') and normalize-space()='Giá trị cần chọn']`.

#### B. Ô chọn ngày tháng (`p-calendar`)
- Điền text ngày tháng an toàn kích hoạt sự kiện Angular:
  ```groovy
  BasePage.setText(calendarElement, '20/10/2026') // hoặc DMITHelper.setPrimeNGCalendar(calendarXpath, '20/10/2026')
  calendarElement.sendKeys(Keys.chord(Keys.ENTER))
  ```

#### C. Lớp phủ Modal & Dialog (`p-dialog` / `cdk-overlay-backdrop`)
- Chờ backdrop tan biến trước khi thực hiện bước tiếp theo để tránh `ElementClickInterceptedException`:
  ```groovy
  BasePage.waitForElementNotVisible(BasePage.x("//div[contains(@class,'p-component-overlay') or contains(@class,'cdk-overlay-backdrop')]"), 5)
  ```

### 2.5. Tương Tác Bản Đồ Không Gian (OpenLayers Map) & Form Thuộc Tính (`popup-data`)
1. **Quy tắc tính toạ độ Selenium Actions trên Viewport Bản đồ:**
   - Trong Selenium, lệnh `actions.moveToElement(viewport, x, y)` tính toạ độ tương đối từ **TÂM (CENTER)** của thẻ viewport, KHÔNG PHẢI từ góc trên trái `(0, 0)`.
   - Luôn sử dụng offset an toàn trong phạm vi viewport (ví dụ `x: -180 đến 180`, `y: -100 đến 100`).
2. **Tránh trùng lặp toạ độ hình học (GIS Spatial Overlap):**
   - Bản đồ DMIT kiểm tra phạm vi chồng lấn không gian. Nếu vẽ đè lên khu/cụm công nghiệp đã tồn tại ở các lần chạy trước, hệ thống sẽ báo: *"Phạm vi giữa các khu/cụm không hợp lệ. Vui lòng kiểm tra lại!"* và vô hiệu hóa nút xác nhận toạ độ `[ ✓ ]` (`disabled`).
   - **Giải pháp:** Vẽ đa giác tại phân vùng toạ độ trống không chồng lấn (ví dụ toạ độ âm phía Tây/Tây Bắc `-180, -80`).
3. **Kích hoạt sự kiện Angular Reactive Form khi điền thuộc tính:**
   - Các trường trong `div.card.popup-data` là reactive form controls. Việc dùng `clear()` hay `sendKeys()` đơn thuần dễ gặp lỗi `InvalidElementStateException`.
   - **Giải pháp:** Kết hợp gán giá trị qua JavaScript và bắn các synthetic events:
     ```groovy
     js.executeScript("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true})); arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", inputElement, value)
     ```
4. **Điền đầy đủ tất cả trường bắt buộc trước khi Lưu:**
   - Form tạo mới bản đồ yêu cầu đủ 4 thông tin: **Mã** (CCN_xxx <= 20 ký tự), **Tên CCN \***, **Địa chỉ \***, và **Trạng thái \*** (cả 2 dropdown trạng thái hoạt động và trạng thái). Thiếu bất kỳ trường nào hệ thống sẽ chặn lưu.

---

## 3. Quy Chuẩn Đặt Tên & Phát Triển Kịch Bản Trong 259 Test Cases

1. **Quy chuẩn định danh (Naming Convention):**
   - File Test Case: `Test Cases/TC-[Số_Thứ_Tự] [Tên_Kịch_Bản_Không_Dấu_Đặc_Biệt].tc`
   - Thư mục Script: `Scripts/TC-[Số_Thứ_Tự] [Tên_Kịch_Bản_Không_Dấu_Đặc_Biệt]/`
   - Page Object Model (POM): 100% locators và phương thức thao tác được đóng gói tại **10 Page Classes trong `Keywords/dmit/pages/`** kế thừa từ `BasePage`. Cấm tuyệt đối raw XPaths và `findTestObject` trong kịch bản test.
2. **Khai thác dữ liệu kiểm thử (Dynamic Test Data):**
   - Khi tạo mới dữ liệu (Chỉ tiêu, Phòng ban, Token, Dự án), luôn gắn timestamp để tránh trùng lặp:
     ```groovy
     String uniqueName = "DMIT_TEST_" + System.currentTimeMillis()
     ```
3. **Cấu trúc Log trong mỗi Test Script:**
   ```groovy
   WebUI.comment("=== BẮT ĐẦU KIỂM THỬ: TC-XX [Tên kịch bản] ===")
   WebUI.comment("--- Bước 1: [Mô tả thao tác] ---")
   // Code
   WebUI.comment("--- Bước 2: [Mô tả thao tác] ---")
   // Code
   WebUI.comment("=== HOÀN TẤT KIỂM THỬ: TC-XX THÀNH CÔNG ===")
   ```

---

## 4. Bài Học Rút Ra & Nguyên Tắc Chẩn Đoán Lỗi Nhanh (Lessons Learned)

1. **Không đoán mò khi phần tử không tìm thấy - Luôn xem Ảnh chụp lỗi (Allure Screenshot):**
   - Khi KRE báo `NoSuchElementException` hoặc `invalid element state`, ảnh chụp màn hình tự động trong `Screenshots/FAILED_*.png` là nguồn sự thật khách quan nhất (Ground Truth) để thấy trạng thái giao diện thực tế (ví dụ: cảnh báo trùng toạ độ màu đỏ, nút Lưu bị disable).
2. **Tránh lỗi mã hóa ký tự (UTF-8 vs Windows-1252):**
   - Khi viết XPath trong file `.groovy`, tránh dùng chuỗi tiếng Việt có dấu trực tiếp nếu hệ thống chạy charset Windows-1252, vì `contains(., 'Mã')` sẽ bị biến thành `MÃ£`. Nên dùng ký tự ASCII đại diện hoặc Unicode escape `\u00E3`.
   - File ghi bằng PowerShell luôn chỉ định `New-Object System.Text.UTF8Encoding($false)` để không sinh BOM gây lỗi biên dịch.

### 2.6 Xử lý Toast thông báo tiếng Việt Unicode Tổ hợp (NFD) và Mở thẻ Chỉnh sửa sau khi Tạo mới (TC-123 & TC-124)
- **Toast thông báo thành công lớp Cụm công nghiệp:**
  - Tiêu đề DOM: <div role="alertdialog" aria-live="polite" class="toast-message" aria-label="Tạo mới thành công dữ liệu cho lớp Cụm công nghiệp"> Tạo mới thành công dữ liệu cho lớp Cụm công nghiệp </div>
  - Chuỗi hiển thị dùng mã tiếng Việt tổ hợp (NFD), ví dụ \̣\ (\\\u0061\\u0323\), \ớ\ (\\\u01a1\\u0301\), \̀\ (\\\u0061\\u0300\).
  - Giải pháp so khớp an toàn: Chuẩn hóa bằng \Normalizer.normalize(text, Normalizer.Form.NFD).replaceAll("\\\\p{InCombiningDiacriticalMarks}+", "")\ để kiểm tra không phân biệt NFD/NFC.
- **Luồng chuyển giao chỉnh sửa:**
  - Ngay sau khi lưu thêm mới ở TC-123, tâm đa giác vừa tạo được lưu tại \DataMiningPage.lastDrawnX, lastDrawnY\.
  - Đóng bảng \editor-widget\ ("Tiếp tục thêm mới dữ liệu") và click chuột vào tọa độ tâm đó trên \div.ol-viewport\.
  - Thẻ **"Thông tin dữ liệu - Cụm công nghiệp"** mở ra ở lề phải với 4 nút tác vụ: Liên kết, Bút chì (Sửa), Thùng rác (Xóa), Đóng.
  - TC-124 chỉ cần click nút Bút chì (\mdi-pencil\), sửa tên và bấm tick xanh Lưu để cập nhật thành công.

---

## 5. Lộ trình Nâng cấp Tự hành Cấp độ 5 (Level 5 Roadmap - Dự phòng tương lai)

Phần này ghi nhận 2 định hướng kiến trúc mở rộng khi có điều kiện triển khai hạ tầng:

### 5.1. Bộ Sinh Kịch bản Tự động từ Đặc tả API (Autonomous Spec Crawler & Auto-Gen)
- **Mục tiêu:** AI tự động đọc tài liệu backend Swagger/OpenAPI (`/swagger-ui.html` hoặc `/v3/api-docs`) và tự bò (crawl) toàn bộ cây menu của hệ thống DMIT.
- **Cơ chế vận hành:**
  1. Phân tích JSON Schema của các endpoint: `/api/target-plans`, `/api/industrial-clusters`, `/api/users`.
  2. Tự động suy luận ra các ca kiểm thử biên (Boundary Values), kiểm thử dữ liệu rỗng, sai định dạng (Negative Cases).
  3. Tự động sinh mã Groovy Clean POM hoàn chỉnh mà không cần lập trình viên QA phải viết kịch bản tay ban đầu.

### 5.2. Quản lý Vòng đời Lỗi Ứng dụng Tự hành (Autonomous Bug Lifecycle Manager)
- **Mục tiêu:** Khi test case thất bại do ứng dụng AUT bị lỗi thật (HTTP 500, crash, sai logic nghiệp vụ backend), AI tự động tạo vé báo lỗi (Bug Ticket) mà không cần can thiệp thủ công.
- **Cơ chế vận hành:**
  1. **Đóng gói bằng chứng:** Tự động quay video 10 giây trước khi lỗi, lưu file Network HAR và chụp ảnh DOM thực tế.
  2. **Tích hợp Issue Tracker:** Gọi REST API của Jira / GitLab Issues để tạo ticket lỗi chuẩn mực với:
     - Tiêu đề: `[AUT Bug][Module] <Mô tả ngắn>`
     - Các bước tái hiện (Steps to Reproduce)
     - Payload Backend & Log Console đính kèm
     - Gán nhãn mức độ nghiêm trọng (Severity: Critical / High / Medium)
  3. **Cảnh báo tức thì:** Bắn webhook thông báo tóm tắt vào nhóm Telegram / Slack nội bộ của dự án.

---

## 6. Điều Hướng Kiến Trúc & Phân Tích Vùng Ảnh Hưởng Bằng Graphify (`tools/test_impact.py`)

Hệ thống DMIT tích hợp đồ thị tri thức mã nguồn cục bộ (AST Knowledge Graph) thông qua **Graphify** và công cụ phân tích tác động kiểm thử tự động `tools/test_impact.py`.

### 6.1. Mục đích & Nguyên lý hoạt động
- **Phân tích AST không tốn Token:** Trích xuất tự động quan hệ kế thừa (`inherits`), gọi hàm (`calls`), và `imports` giữa 259 Test Cases và 10 Page Classes.
- **Test Impact Analysis:** Khi một Page Class (ví dụ `CommonCategoryPage.groovy` hoặc `DataMiningPage.groovy`) bị sửa, công cụ tính toán đường đi ngược (reverse graph traversal) để chỉ điểm chính xác các Test Cases bị ảnh hưởng trực tiếp.
- **Tiết kiệm tới 95% thời gian chạy CI/CD:** Thay vì chạy lại cả 259 Test Cases (2.5 tiếng), chỉ cần chạy đúng danh sách Test Cases bị tác động (vài phút).

### 6.2. Lệnh thực thi thực tế

1. **Phân tích khi sửa một Page Class cụ thể:**
   ```bash
   python3 tools/test_impact.py -f Keywords/dmit/pages/CommonCategoryPage.groovy
   ```
   *Kết quả mẫu:* Xác định chính xác 12 Test Cases (TC-17 đến TC-28), bỏ qua 247 Test Cases còn lại, tiết kiệm 95.4% thời gian kiểm thử.

2. **Tự động phân tích các tệp tin thay đổi qua Git:**
   ```bash
   python3 tools/test_impact.py --git-diff
   ```

3. **Cập nhật lại Đồ thị Tri thức sau khi sửa mã nguồn:**
   ```bash
   ~/.venv_graphify/bin/graphify update .
   ```

4. **Xem bản đồ trực quan kiến trúc dự án trên trình duyệt:**
   - Mạng lưới quan hệ 2D/3D: `open graphify-out/graph.html`
   - Sơ đồ tương tác luồng gọi hàm & Mermaid: `open graphify-out/callflow.html`


