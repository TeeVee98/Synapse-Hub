# TEST CASES — CRM LOGIN MODULE

| Thông tin | Chi tiết |
|-----------|----------|
| **Dự án** | CRM (Perfex CRM - Anh Tester Demo) |
| **Module** | Login |
| **URL** | https://crm.anhtester.com/admin/authentication |
| **Phương pháp** | AI-RBT (Risk-Based Testing) — FULL 6 bước |
| **Tiêu chuẩn** | ISO/IEC/IEEE 29119-3 (Bảng chuẩn 12 cột) |
| **Ngày tạo** | 2026-04-08 |
| **Tổng số TC** | 32 |

---

## TỔNG HỢP RISK LEVEL

| Module | Risk Level | Số TC |
|--------|-----------|-------|
| M2: Login Authentication | 🔴 High | 13 |
| M5: Security | 🔴 High | 6 |
| M3: Forgot Password | 🟡 Medium | 5 |
| M4: Logout | 🟡 Medium | 2 |
| M1: Login Form UI | 🟢 Low | 4 |
| Concurrency & Resilience | 🔴 High | 2 |

---

## TRACEABILITY MATRIX

| Requirement | Test Cases |
|------------|------------|
| AC-01 | CRM_LOGIN_TC_005 |
| AC-02 | CRM_LOGIN_TC_006 |
| AC-03 | CRM_LOGIN_TC_007 |
| AC-04 | CRM_LOGIN_TC_008 |
| AC-05 | CRM_LOGIN_TC_009 |
| AC-06 | CRM_LOGIN_TC_010, CRM_LOGIN_TC_011, CRM_LOGIN_TC_012 |
| AC-07 | CRM_LOGIN_TC_013, CRM_LOGIN_TC_014 |
| AC-08 | CRM_LOGIN_TC_018 |
| AC-09 | CRM_LOGIN_TC_019 |
| AC-10 | CRM_LOGIN_TC_020 |
| AC-11 | CRM_LOGIN_TC_023 |
| NFR-01 | CRM_LOGIN_TC_003, CRM_LOGIN_TC_028 |
| NFR-02 | CRM_LOGIN_TC_002 |
| NFR-03 | CRM_LOGIN_TC_030 |
| NFR-04 | CRM_LOGIN_TC_001 |
| NFR-05 | CRM_LOGIN_TC_001, CRM_LOGIN_TC_004 |
| Gap (no AC) | CRM_LOGIN_TC_015, CRM_LOGIN_TC_016, CRM_LOGIN_TC_017, CRM_LOGIN_TC_021, CRM_LOGIN_TC_022, CRM_LOGIN_TC_024, CRM_LOGIN_TC_025, CRM_LOGIN_TC_026, CRM_LOGIN_TC_027, CRM_LOGIN_TC_029, CRM_LOGIN_TC_031, CRM_LOGIN_TC_032 |

---

## BẢNG TEST CASES

### M1: Login Form UI (🟢 Low Risk)

| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| CRM_LOGIN_TC_001 | NFR-04, NFR-05 | M1: Login Form UI | Verify trang Login hiển thị đầy đủ các thành phần giao diện | Trình duyệt web sẵn sàng; không yêu cầu phiên đăng nhập trước | 1. Mở trình duyệt Chrome<br>2. Truy cập URL: `https://crm.anhtester.com/admin/authentication`<br>3. Quan sát toàn bộ trang Login | N/A | 1. Trình duyệt mở thành công<br>2. Trang Login tải hoàn chỉnh<br>3. Hiển thị đầy đủ:<br>- Logo "Anh Tester - Automation Testing"<br>- Tiêu đề "Login" (H1)<br>- Trường "Email Address" (textbox)<br>- Trường "Password" (textbox)<br>- Checkbox "Remember me" (không tick mặc định)<br>- Nút "Login" (xanh dương, full width)<br>- Link "Forgot Password?" (màu cam) | Medium | 4 | Yes / UI | @Smoke, @Regression, @P0 |
| CRM_LOGIN_TC_002 | NFR-02 | M1: Login Form UI | Verify trường Password hiển thị dạng masked bảo mật | Trang Login đang mở trên trình duyệt | 1. Truy cập trang Login<br>2. Click vào trường Password<br>3. Nhập: `TestPassword123`<br>4. Quan sát hiển thị ký tự trong trường Password | Password: `TestPassword123` | 1. Trang Login hiển thị<br>2. Trường Password được focus<br>3-4. Ký tự hiển thị dạng dấu chấm masked (●●●), KHÔNG hiển thị plaintext | Medium | 4 | Yes / UI | @Regression |
| CRM_LOGIN_TC_003 | NFR-01 | M1: Login Form UI | Verify CSRF token hidden field tồn tại trong form authentication | Trang Login đang mở trên trình duyệt | 1. Truy cập trang Login<br>2. Inspect HTML form bằng DevTools (F12)<br>3. Tìm hidden field có name="csrf_token_name" | N/A | 1. Trang Login hiển thị<br>2. DevTools mở thành công<br>3. Tồn tại `<input type="hidden" name="csrf_token_name">` với value không rỗng, value là chuỗi token duy nhất chống CSRF | Low | 4 | Yes / UI | @Security, @Regression |
| CRM_LOGIN_TC_004 | NFR-05 | M1: Login Form UI | Verify giao diện responsive trên viewport thiết bị di động và tablet | Trang Login đang mở trên Chrome DevTools | 1. Truy cập trang Login trên Chrome<br>2. Mở DevTools → Toggle Device Toolbar<br>3. Chọn viewport: iPhone 14 (390×844)<br>4. Quan sát bố cục trang Login<br>5. Chuyển sang viewport: iPad (768×1024)<br>6. Quan sát bố cục | Viewport 1: 390×844<br>Viewport 2: 768×1024 | 1-2. DevTools mở thành công<br>3-4. Form Login hiển thị đầy đủ, không bị tràn ngang, nút Login full width, các trường input đọc rõ ràng<br>5-6. Form Login hiển thị căn giữa, đúng viewport bounds, không bị tràn ngang, các trường input và button co giãn theo tỷ lệ CSS responsive | Low | 4 | Yes / UI | @Regression, @Responsive |

---

### M2: Login Authentication (🔴 High Risk)

| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| CRM_LOGIN_TC_005 | AC-01 | M2: Login Auth | Đăng nhập thành công với Email và Password chính xác | Tài khoản admin@example.com đã được kích hoạt trong CSDL | 1. Truy cập trang Login<br>2. Nhập Email: `admin@example.com`<br>3. Nhập Password: `123456`<br>4. Click nút "Login" | Email: `admin@example.com`<br>Password: `123456` | 1. Trang Login hiển thị<br>2. Email được nhập vào trường<br>3. Password được nhập (hiển thị masked)<br>4. Đăng nhập thành công:<br>- Chuyển hướng đến Dashboard (`/admin/`)<br>- Trang hiển thị tiêu đề "Dashboard"<br>- Không hiển thị thông báo lỗi | Critical | 24 | Yes / UI | @Smoke, @Regression, @P0 |
| CRM_LOGIN_TC_006 | AC-02 | M2: Login Auth | Đăng nhập thất bại - Để trống trường Email | Trang Login đang mở sẵn sàng nhập liệu | 1. Truy cập trang Login<br>2. Để trống trường Email<br>3. Nhập Password: `123456`<br>4. Click nút "Login" | Email: (trống)<br>Password: `123456` | 1. Trang Login hiển thị<br>2. Trường Email trống<br>3. Password được nhập<br>4. Hiển thị thông báo lỗi server-side:<br>- Text: **"The Email Address field is required."**<br>- Trong thẻ `<div class="alert alert-danger text-center">`<br>- Vẫn ở lại trang Login | High | 16 | Yes / UI | @Regression, @Negative |
| CRM_LOGIN_TC_007 | AC-03 | M2: Login Auth | Đăng nhập thất bại - Để trống trường Password | Trang Login đang mở sẵn sàng nhập liệu | 1. Truy cập trang Login<br>2. Nhập Email: `admin@example.com`<br>3. Để trống trường Password<br>4. Click nút "Login" | Email: `admin@example.com`<br>Password: (trống) | 1. Trang Login hiển thị<br>2. Email được nhập<br>3. Trường Password trống<br>4. Hiển thị thông báo lỗi server-side:<br>- Text: **"The Password field is required."**<br>- Trong thẻ `<div class="alert alert-danger text-center">`<br>- Vẫn ở lại trang Login | High | 16 | Yes / UI | @Regression, @Negative |
| CRM_LOGIN_TC_008 | AC-04 | M2: Login Auth | Đăng nhập thất bại - Để trống cả Email và Password | Trang Login đang mở sẵn sàng nhập liệu | 1. Truy cập trang Login<br>2. Để trống trường Email<br>3. Để trống trường Password<br>4. Click nút "Login" | Email: (trống)<br>Password: (trống) | 1. Trang Login hiển thị<br>2-3. Cả hai trường trống<br>4. Hiển thị **đồng thời 2 thông báo** lỗi server-side:<br>- **"The Email Address field is required."**<br>- **"The Password field is required."**<br>- Cả 2 trong `<div class="alert alert-danger text-center">`<br>- Vẫn ở lại trang Login | High | 16 | Yes / UI | @Regression, @Negative |
| CRM_LOGIN_TC_009 | AC-05 | M2: Login Auth | Đăng nhập thất bại - Email sai định dạng (thiếu ký tự @) | Trang Login đang mở sẵn sàng nhập liệu | 1. Truy cập trang Login<br>2. Nhập Email: `invalidemail`<br>3. Nhập Password: `123456`<br>4. Click nút "Login" | Email: `invalidemail`<br>Password: `123456` | 1. Trang Login hiển thị<br>2. Email nhập không có ký tự @<br>3. Password được nhập<br>4. Trình duyệt **chặn form submit** và hiển thị HTML5 tooltip:<br>- **"Please include an '@' in the email address."** chuỗi validation HTML5<br>- Form KHÔNG được gửi lên server<br>- Đây là client-side validation | High | 16 | Yes / UI | @Regression, @Negative |
| CRM_LOGIN_TC_010 | AC-06 | M2: Login Auth | Đăng nhập thất bại - Email đúng định dạng nhưng không tồn tại | Trang Login đang mở; CSDL không chứa email notexist_20260408@example.com | 1. Truy cập trang Login<br>2. Nhập Email: `notexist_20260408@example.com`<br>3. Nhập Password: `WrongPass!456`<br>4. Click nút "Login" | Email: `notexist_20260408@example.com`<br>Password: `WrongPass!456` | 1. Trang Login hiển thị<br>2-3. Dữ liệu được nhập<br>4. Hiển thị thông báo lỗi server-side:<br>- Text: **"Invalid email or password"**<br>- Trong `<div class="alert alert-danger text-center">`<br>- Vẫn ở lại trang Login | High | 16 | Yes / UI | @Regression, @Negative |
| CRM_LOGIN_TC_011 | AC-06 | M2: Login Auth | Đăng nhập thất bại - Email đúng nhưng mật khẩu không chính xác | Tài khoản admin@example.com tồn tại trong CSDL | 1. Truy cập trang Login<br>2. Nhập Email: `admin@example.com`<br>3. Nhập Password: `SaiMatKhau!789`<br>4. Click nút "Login" | Email: `admin@example.com`<br>Password: `SaiMatKhau!789` | 1. Trang Login hiển thị<br>2-3. Dữ liệu được nhập<br>4. Hiển thị thông báo:<br>- Text: **"Invalid email or password"**<br>- Thông báo **KHÔNG** tiết lộ rằng email tồn tại<br>- Vẫn ở lại trang Login | High | 16 | Yes / UI | @Regression, @Negative |
| CRM_LOGIN_TC_012 | AC-06 | M2: Login Auth | Đăng nhập thất bại - Nhập sai địa chỉ Email dù Password chuẩn xác | Tài khoản admin@example.com tồn tại với mật khẩu 123456 | 1. Mở trang Login Perfex CRM<br>2. Nhập địa chỉ Email chưa đăng ký: `wrong_admin@example.com`<br>3. Nhập Password chính xác: `123456`<br>4. Nhấp nút Login gửi yêu cầu | Email: `wrong_admin@example.com`<br>Password: `123456` | 1. Trang Login hiển thị<br>2-3. Dữ liệu được nhập<br>4. Hiển thị thông báo lỗi server-side:<br>- Text: **"Invalid email or password"**<br>- Thông báo **KHÔNG** tiết lộ rằng password đúng<br>- Vẫn ở lại trang Login | High | 16 | Yes / UI | @Regression, @Negative |
| CRM_LOGIN_TC_013 | AC-07 | M2: Login Auth | Đăng nhập thành công kèm ghi nhớ phiên - Duy trì sau khi khởi động lại browser | Tài khoản admin@example.com đã được kích hoạt trong CSDL | 1. Truy cập trang Login<br>2. Nhập Email: `admin@example.com`<br>3. Nhập Password: `123456`<br>4. Tick checkbox "Remember me"<br>5. Click nút "Login"<br>6. Verify Dashboard hiển thị<br>7. Đóng hoàn toàn trình duyệt<br>8. Mở lại trình duyệt<br>9. Truy cập: `https://crm.anhtester.com/admin/` | Email: `admin@example.com`<br>Password: `123456`<br>Remember me: ✅ Tick | 1. Trang Login hiển thị<br>2-3. Dữ liệu được nhập<br>4. Checkbox được tick<br>5-6. Đăng nhập thành công, Dashboard hiển thị<br>7-8. Trình duyệt đóng và mở lại<br>9. Truy cập trực tiếp Dashboard **KHÔNG** bị redirect về trang Login, phiên vẫn còn hiệu lực (duy trì 1 ngày) | Critical | 24 | Yes / UI | @CriticalPath, @Regression, @StateTransition |
| CRM_LOGIN_TC_014 | AC-07 | M2: Login Auth | Đăng nhập bỏ chọn checkbox Remember me - Hủy phiên khi tắt trình duyệt | Tài khoản admin@example.com đã được kích hoạt trong CSDL | 1. Mở trang Login Perfex CRM<br>2. Điền thông tin admin: `admin@example.com` và password `123456`<br>3. Giữ nguyên trạng thái mặc định không tick Remember me<br>4. Nhấn Login vào Dashboard<br>5. Đóng hoàn toàn cửa sổ trình duyệt<br>6. Khởi động lại browser và điều hướng trực tiếp `https://crm.anhtester.com/admin/` | Email: `admin@example.com`<br>Password: `123456`<br>Remember me: ❌ Không tick | 1. Trang Login hiển thị<br>2-3. Dữ liệu được nhập<br>4. Checkbox KHÔNG được tick<br>5-6. Đăng nhập thành công<br>7-8. Trình duyệt đóng và mở lại<br>9. Bị redirect về trang Login (`/admin/authentication`), phiên đã hết | High | 16 | Yes / UI | @Regression, @Negative, @StateTransition |
| CRM_LOGIN_TC_015 | GAP | M2: Login Auth | Boundary - Nhập Email cực dài (1001 ký tự) | Trang Login đang mở sẵn sàng nhập liệu | 1. Truy cập trang Login<br>2. Nhập Email: chuỗi 1001 ký tự `aaaaaa...aaa@example.com` (996 ký tự 'a' + @example.com)<br>3. Nhập Password: `123456`<br>4. Click nút "Login" | Email: 1001 ký tự (`aaa...a@example.com`)<br>Password: `123456` | 1. Trang Login hiển thị<br>2. Email dài được nhập<br>3. Password được nhập<br>4. Hệ thống từ chối submit, hiển thị thông báo lỗi độ dài email vượt quá giới hạn, mã lỗi 400 Bad Request, không xảy ra crash hệ thống | Medium | 8 | Yes / UI | @Regression, @Boundary |
| CRM_LOGIN_TC_016 | GAP | M2: Login Auth | Boundary - Nhập Password cực dài (1001 ký tự) | Trang Login đang mở sẵn sàng nhập liệu | 1. Truy cập trang Login<br>2. Nhập Email: `admin@example.com`<br>3. Nhập Password: chuỗi 1001 ký tự `Aaaaaa...aaa1!` (lặp ký tự)<br>4. Click nút "Login" | Email: `admin@example.com`<br>Password: 1001 ký tự | 1. Trang Login hiển thị<br>2. Email được nhập<br>3. Password dài được nhập (masked)<br>4. Hệ thống hiển thị thông báo "Invalid email or password", mã phản hồi 401, không xảy ra crash hệ thống | Medium | 8 | Yes / UI | @Regression, @Boundary |
| CRM_LOGIN_TC_017 | GAP | M2: Login Auth | Truy cập trang Login khi đã đăng nhập → redirect Dashboard | Đã đăng nhập thành công với tài khoản admin, đang ở màn hình Dashboard | 1. Đăng nhập thành công với `admin@example.com`<br>2. Verify đang ở Dashboard<br>3. Thay đổi URL thủ công thành: `https://crm.anhtester.com/admin/authentication`<br>4. Nhấn Enter | Email: `admin@example.com`<br>Password: `123456` | 1-2. Đang ở Dashboard<br>3-4. Hệ thống tự động redirect về Dashboard (`/admin/`), **KHÔNG** hiển thị form Login khi đã authenticated | Medium | 8 | Yes / UI | @Regression, @StateTransition |
| CRM_LOGIN_TC_031 | GAP | M2: Login Auth | Concurrency - Rapid Double-Click vào nút Login (<300ms) | Tài khoản admin@example.com tồn tại trong CSDL | 1. Mở trang Login<br>2. Nhập Email: `admin@example.com` và Password: `123456`<br>3. Thực hiện double-click liên tiếp vào nút "Login" trong khoảng <300ms | Email: `admin@example.com`<br>Password: `123456` | 1. Trang Login hiển thị<br>2. Thông tin được điền<br>3. Nút Login lập tức chuyển sang trạng thái disabled sau click đầu tiên; chỉ duy nhất 1 HTTP POST request được gửi lên server; đăng nhập thành công vào Dashboard không bị xung đột phiên | Critical | 24 | Yes / UI | @Concurrency, @Regression |
| CRM_LOGIN_TC_032 | GAP | M2: Login Auth | Unicode Normalization - Đăng nhập với ký tự tiếng Việt dạng NFC vs NFD | Tài khoản email có dấu tiếng Việt tồn tại trong CSDL | 1. Mở trang Login<br>2. Nhập email dạng Unicode NFD (Tổ hợp: U+006F U+0300)<br>3. Nhập password đúng quy chuẩn (`123456`)<br>4. Click nút Login | Email: `hoà_bình@example.com` (NFD)<br>Password: `123456` | 1. Trang Login hiển thị<br>2. Email NFD được nhập<br>3. Password được nhập<br>4. Hệ thống tự động chuẩn hóa chuỗi về Unicode NFC trước khi query database; xác thực thành công chuyển hướng Dashboard | High | 16 | Yes / UI | @Unicode, @Regression |

---

### M3: Forgot Password (🟡 Medium Risk)

| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| CRM_LOGIN_TC_018 | AC-08 | M3: Forgot Password | Click "Forgot Password?" chuyển đến trang khôi phục | Đang ở trang Login authentication | 1. Truy cập trang Login<br>2. Click link "Forgot Password?" | N/A | 1. Trang Login hiển thị<br>2. Chuyển hướng đến URL: `https://crm.anhtester.com/admin/authentication/forgot_password`<br>- Hiển thị trường "Email Address"<br>- Hiển thị nút "Confirm" | High | 8 | Yes / UI | @Regression |
| CRM_LOGIN_TC_019 | AC-09 | M3: Forgot Password | Gửi email khôi phục với email đã đăng ký | Đang ở trang Forgot Password; tài khoản admin@example.com tồn tại trong CSDL | 1. Truy cập trang Forgot Password<br>2. Nhập Email: `admin@example.com`<br>3. Click nút "Confirm" | Email: `admin@example.com` | 1. Trang Forgot Password hiển thị<br>2. Email được nhập<br>3. Hệ thống xử lý yêu cầu:<br>- Hiển thị thông báo xác nhận email khôi phục đã được gửi<br>- KHÔNG hiển thị thông báo lỗi | High | 8 | Yes / UI | @Regression |
| CRM_LOGIN_TC_020 | AC-10 | M3: Forgot Password | Để trống Email trên trang Forgot Password → HTML5 validation | Đang ở trang Forgot Password | 1. Truy cập trang Forgot Password<br>2. Để trống trường Email<br>3. Click nút "Confirm" | Email: (trống) | 1. Trang Forgot Password hiển thị<br>2. Trường Email trống<br>3. Trình duyệt hiển thị HTML5 validation tooltip (trường có thuộc tính `required`):<br>- **"Please fill out this field."** chuỗi validation HTML5<br>- Form KHÔNG được gửi lên server | High | 8 | Yes / UI | @Regression, @Negative |
| CRM_LOGIN_TC_021 | GAP | M3: Forgot Password | Nhập email chưa đăng ký trên trang Forgot Password | Đang ở trang Forgot Password | 1. Truy cập trang Forgot Password<br>2. Nhập Email: `khongtontai_20260408@example.com`<br>3. Click nút "Confirm" | Email: `khongtontai_20260408@example.com` | 1. Trang Forgot Password hiển thị<br>2. Email được nhập<br>3. Hệ thống hiển thị thông báo xác nhận chung: "If your email is registered, you will receive a reset link shortly" nhằm ngăn chặn brute-force enumeration | Medium | 8 | Yes / UI | @Regression, @Security |
| CRM_LOGIN_TC_022 | GAP | M3: Forgot Password | Nhập địa chỉ email sai cú pháp trên form Forgot Password | Đang ở trang Forgot Password | 1. Điều hướng màn hình Forgot Password<br>2. Nhập chuỗi ký tự thiếu ký danh miền: `invalid_syntax_email`<br>3. Nhấp nút Confirm kích hoạt validation | Email: `invalid_syntax_email` | 1. Trang Forgot Password hiển thị<br>2. Email sai định dạng được nhập<br>3. Trình duyệt hiển thị HTML5 validation tooltip:<br>- **"Please include an '@' in the email address."**<br>- Form KHÔNG được gửi lên server | Medium | 8 | Yes / UI | @Regression, @Negative |

---

### M4: Logout (🟡 Medium Risk)

| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| CRM_LOGIN_TC_023 | AC-11 | M4: Logout | Đăng xuất từ Dashboard → quay về trang Login | Đã đăng nhập thành công với tài khoản admin, đang ở màn hình Dashboard | 1. Đăng nhập thành công<br>2. Verify đang ở Dashboard<br>3. Click vào profile dropdown (góc trên bên phải)<br>4. Click "Logout" | Email: `admin@example.com`<br>Password: `123456` | 1-2. Đang ở Dashboard<br>3. Dropdown menu hiển thị<br>4. Đăng xuất thành công:<br>- Chuyển hướng về trang Login (`/admin/authentication`)<br>- Form Login hiển thị<br>- KHÔNG còn hiển thị Dashboard | Critical | 24 | Yes / UI | @CriticalPath, @Regression, @StateTransition |
| CRM_LOGIN_TC_024 | GAP | M4: Logout | Sau logout, nhấn nút Back trên trình duyệt → không quay lại được Dashboard | Vừa đăng xuất thành công, đang ở trang Login authentication | 1. Đăng nhập thành công<br>2. Đăng xuất (Logout)<br>3. Verify đang ở trang Login<br>4. Nhấn nút **Back** trên trình duyệt<br>5. Quan sát trang hiển thị | Email: `admin@example.com`<br>Password: `123456` | 1-2. Đăng nhập và đăng xuất thành công<br>3. Đang ở trang Login<br>4-5. Hệ thống **redirect về trang Login**, KHÔNG hiển thị lại Dashboard:<br>- Session đã bị hủy hoàn toàn<br>- Dữ liệu Dashboard KHÔNG hiển thị từ cache | High | 16 | Yes / UI | @Regression, @Security, @StateTransition |

---

### M5: Security (🔴 High Risk)

| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| CRM_LOGIN_TC_025 | GAP | M5: Security | SQL Injection vào trường Email trên form đăng nhập | Trang Login đang mở sẵn sàng nhập liệu | 1. Truy cập trang Login<br>2. Nhập Email: `' OR 1=1 --`<br>3. Nhập Password: `anything`<br>4. Click nút "Login" | Email: `' OR 1=1 --`<br>Password: `anything` | 1. Trang Login hiển thị<br>2-3. Dữ liệu injection được nhập<br>4. Câu truy vấn SQL được tham số hóa an toàn: Hiển thị thông báo "Invalid email or password", mã lỗi 401, không rò rỉ cấu trúc DB | Critical | 24 | Yes / UI | @Security, @Regression, @SQLi |
| CRM_LOGIN_TC_026 | GAP | M5: Security | XSS Script Injection vào trường Email trên form đăng nhập | Trang Login đang mở sẵn sàng nhập liệu | 1. Truy cập trang Login<br>2. Nhập Email: `<script>alert('XSS')</script>`<br>3. Nhập Password: `123456`<br>4. Click nút "Login"<br>5. Quan sát trang kết quả | Email: `<script>alert('XSS')</script>`<br>Password: `123456` | 1. Trang Login hiển thị<br>2-3. Dữ liệu XSS được nhập<br>4-5. Ký tự được HTML-escaped an toàn: Hiển thị thông báo lỗi định dạng email, không xuất hiện alert popup, không xảy ra lỗi 500 | Critical | 24 | Yes / UI | @Security, @Regression, @XSS |
| CRM_LOGIN_TC_027 | GAP | M5: Security | SQL Injection vào trường Password trên form đăng nhập | Trang Login đang mở sẵn sàng nhập liệu | 1. Truy cập trang Login<br>2. Nhập Email: `admin@example.com`<br>3. Nhập Password: `' OR '1'='1`<br>4. Click nút "Login" | Email: `admin@example.com`<br>Password: `' OR '1'='1` | 1. Trang Login hiển thị<br>2-3. Dữ liệu injection được nhập<br>4. Hệ thống từ chối đăng nhập: Hiển thị thông báo "Invalid email or password", mã phản hồi 401, không xảy ra lỗi SQL 500 | Critical | 24 | Yes / UI | @Security, @Regression, @SQLi |
| CRM_LOGIN_TC_028 | NFR-01 | M5: Security | CSRF token bị xóa hay thay đổi → form submit bị từ chối với mã 403 | Trang Login đang mở với CSRF token nguyên bản trong DOM | 1. Truy cập trang Login<br>2. Mở DevTools (F12) → Inspect form<br>3. Tìm hidden field `csrf_token_name`<br>4. Thay đổi value thành: `invalid_token_12345`<br>5. Nhập Email: `admin@example.com`<br>6. Nhập Password: `123456`<br>7. Click nút "Login" | Email: `admin@example.com`<br>Password: `123456`<br>CSRF Token: `invalid_token_12345` | 1-3. CSRF token field tìm thấy<br>4. Value bị thay đổi thành token giả<br>5-6. Dữ liệu chuẩn xác được nhập<br>7. Hệ thống từ chối request với mã lỗi HTTP 403 Forbidden và thông báo lỗi CSRF mismatch | High | 24 | Yes / UI | @Security, @Regression, @CSRF |
| CRM_LOGIN_TC_029 | GAP | M5: Security | Đăng nhập sai nhiều lần liên tiếp (Brute-force verification) | Trang Login đang mở sẵn sàng nhập liệu | 1. Truy cập trang Login<br>2. Nhập Email: `admin@example.com` + Password: `SaiPass_1` → Click Login<br>3. Lặp lại bước 2 với password khác: `SaiPass_2`, `SaiPass_3`, ..., `SaiPass_10`<br>4. Quan sát sau 10 lần đăng nhập sai liên tiếp | Email: `admin@example.com`<br>Passwords: `SaiPass_1` → `SaiPass_10` (10 lần sai liên tiếp) | 1. Trang Login hiển thị<br>2-3. Mỗi lần hiển thị "Invalid email or password"<br>4. **Ghi nhận hiện trạng bảo mật brute-force**:<br>- Nếu hệ thống KHÔNG lockout → ghi bug/risk<br>- Hệ thống không crash, không xuất hiện lỗi 500 | High | 24 | Yes / UI | @Security, @Regression, @BruteForce |
| CRM_LOGIN_TC_030 | NFR-03 | M5: Security | Thông báo lỗi không tiết lộ email tồn tại hay không (User Enumeration Defense) | Tài khoản admin@example.com tồn tại trong CSDL | 1. Truy cập trang Login<br>2. Nhập Email: `admin@example.com` (tồn tại) + Password sai: `WrongP@ss1`<br>3. Click Login → ghi nhận thông báo lỗi A<br>4. Nhập Email: `khongtontai@example.com` (không tồn tại) + Password: `WrongP@ss1`<br>5. Click Login → ghi nhận thông báo lỗi B<br>6. So sánh thông báo A và B | Email tồn tại: `admin@example.com`<br>Email không tồn tại: `khongtontai@example.com`<br>Password sai: `WrongP@ss1` | 1. Trang Login hiển thị<br>2-3. Thông báo A: "Invalid email or password"<br>4-5. Thông báo B: "Invalid email or password"<br>6. **Thông báo A = thông báo B** (giống hệt nhau):<br>- KHÔNG phân biệt "Email not found" vs "Wrong password"<br>- Thiết kế bảo mật đúng chuẩn ngăn chặn user enumeration | High | 16 | Yes / UI | @Security, @Regression, @UserEnumeration |

---

## Ambiguity & Assumptions Log

| ID | Requirement Reference / Statement | Ambiguity / Gap Detected | Working Assumption / Resolution | Impact / Risk |
|:---|:---|:---|:---|:---|
| AMB-01 | NFR: Account Lockout Policy | Yêu cầu không nêu rõ số lần khóa tài khoản khi đăng nhập sai | Ghi nhận risk và kiểm thử với TC_029 để đối chiếu hiện trạng bảo mật | High |
| AMB-02 | Field Validation: Password Min/Max Length | Không xác định độ dài chuỗi tối đa của mật khẩu | Thiết lập kiểm thử boundary tại 1001 ký tự (TC_016) | Medium |
| AMB-03 | Field Validation: Email Max Length | Không quy định độ dài tối đa trường Email Address | Thiết lập kiểm thử boundary tại 1001 ký tự (TC_015) | Medium |
| AMB-04 | User Flow: Forgot Password với email không tồn tại | Yêu cầu chưa rõ phản hồi khi email không tồn tại | Áp dụng thông báo thành công chung để chống enumeration (TC_021) | High |
| AMB-05 | Security: Thời hạn reset token | Thời hạn hiệu lực của đường link đổi mật khẩu | Kiểm thử ở tầng API/Unit test; ngoài phạm vi kiểm thử thủ công UI | Low |
| AMB-06 | AC-07: Thời gian duy trì Remember me | Đặc tả không nêu rõ thời gian duy trì phiên đăng nhập | Thống nhất thời hạn duy trì cookie xác thực là 1 ngày (TC_013) | Medium |
| AMB-07 | Session: Điều hướng khi đã đăng nhập | Không nêu hành vi khi truy cập /login lúc đã authenticated | Tự động chuyển hướng về /admin/dashboard (TC_017) | Medium |
| AMB-08 | Navigation: Nhấn nút Back sau Logout | Yêu cầu chưa quy định cache control sau khi đăng xuất | Hủy session hoàn toàn, xóa cache, redirect về login (TC_024) | High |
| AMB-09 | UI: Thao tác copy-paste trường Password | Không quy định chặn hay cho phép dán password | Giữ nguyên hành vi tiêu chuẩn của trình duyệt | Low |
| AMB-10 | Security: Tích hợp CAPTCHA | Trang đăng nhập chưa tích hợp cơ chế chống bot tự động | Ghi nhận nguy cơ brute-force trong báo cáo đánh giá rủi ro (TC_029) | High |
| AMB-11 | DOM: Checkbox Remember me value="estimate" | Thuộc tính HTML mang giá trị đặc thù của framework | Kiểm thử dựa trên hành vi chức năng thực tế của cookie (TC_013, TC_014) | Low |
| AMB-12 | Notification: Nội dung chi tiết email khôi phục | Không kiểm tra trực tiếp hộp thư email nhận | Kiểm thử dừng lại ở thông báo xác nhận trên giao diện UI | Low |

---

## THỐNG KÊ

| Tiêu chí | Số lượng |
|----------|----------|
| **Tổng TC** | **32** |
| Critical Priority | 5 (TC_005, TC_013, TC_023, TC_025, TC_026) |
| High Priority | 14 |
| Medium Priority | 8 |
| Low Priority | 5 |
| Kỹ thuật EP (Equivalence Partitioning) | TC_005-TC_012 (phân nhóm: đúng/sai/trống) |
| Kỹ thuật BVA (Boundary Value) | TC_015, TC_016 (email/password cực dài) |
| Kỹ thuật Decision Table | TC_006-TC_008 (tổ hợp Email trống + Password trống) |
| Kỹ thuật State Transition | TC_013, TC_014, TC_017, TC_023, TC_024 (trạng thái login/logout/session) |
