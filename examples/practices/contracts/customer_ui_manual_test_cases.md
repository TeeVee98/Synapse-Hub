# TEST CASES — QUẢN LÝ KHÁCH HÀNG DOANH NGHIỆP (CUSTOMER CRM)

> **Phương pháp:** Auto-Sanity Feasibility Test Suite  
> **Tiêu chuẩn:** ISO/IEC/IEEE 29119-3 (Bảng chuẩn 12 cột)  
> **Tỷ lệ:** 40% Happy Path — 40% Negative & Boundary — 20% Security & Resilience

---

| TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| CUST_UI_001 | Customer | High | Thêm mới khách hàng doanh nghiệp thành công với đầy đủ thông tin hợp lệ | Người dùng đã đăng nhập hệ thống CRM | 1. Truy cập trang examples/practices/contracts/customer_crm_app.html<br>2. Nhập 'Công ty Công nghệ Synapse' vào ô 'Tên công ty'<br>3. Nhập 'Nguyễn Văn A' vào ô 'Người liên hệ'<br>4. Nhập 'contact@synapse.vn' vào ô 'Email liên hệ'<br>5. Nhập '0912345678' vào ô 'Số điện thoại'<br>6. Nhấp nút 'Lưu khách hàng'<br>7. Kiểm tra hiển thị thông báo 'Khách hàng đã được tạo thành công' | Hệ thống hiển thị thông báo 'Khách hàng đã được tạo thành công' với mã CUST mới | Critical | company='Công ty Công nghệ Synapse', name='Nguyễn Văn A', email='contact@synapse.vn', phone='0912345678' | Yes | E2E | @Smoke, @Regression, @P0 |
| CUST_UI_002 | Customer | Medium | Bỏ trống các trường bắt buộc và gửi biểu mẫu | Người dùng ở màn hình Tạo mới khách hàng | 1. Truy cập trang examples/practices/contracts/customer_crm_app.html<br>2. Nhấp nút 'Lưu khách hàng' | Hệ thống từ chối submit và hiển thị cảnh báo 'Có lỗi xảy ra trong quá trình lưu dữ liệu' | High | Bỏ trống toàn bộ các trường bắt buộc | Yes | E2E | @Negative, @Validation |
| CUST_UI_003 | Customer | Medium | Kiểm tra phần tử bị vô hiệu hoá không cho phép tương tác | Người dùng ở màn hình form khách hàng | 1. Truy cập trang examples/practices/contracts/customer_crm_app.html<br>2. Nhấp nút 'Nút bị vô hiệu hoá' | Hệ thống chặn thao tác do phần tử đang ở trạng thái disabled | Medium | Nút 'Nút bị vô hiệu hoá' | Yes | E2E | @Boundary, @Negative |
| CUST_UI_004 | Customer | High | Kiểm tra phát hiện nút bấm không tồn tại trong giao diện (Locator Drift) | Mở màn hình tạo mới khách hàng | 1. Truy cập trang examples/practices/contracts/customer_crm_app.html<br>2. Nhấp nút 'Nút bấm ma không có thật' | Hệ thống không tìm thấy phần tử trong cây DOM và cảnh báo locator drift | High | Tên nút ma: 'Nút bấm ma không có thật' | Yes | E2E | @Drift, @Negative |
| CUST_UI_005 | Customer | High | Concurrency - Nhấp đúp nút Lưu khách hàng liên tiếp trong 200ms | Người dùng đã điền đủ thông tin hợp lệ | 1. Điền đủ thông tin hợp lệ<br>2. Nhấp nút 'Lưu khách hàng' 2 lần liên tiếp <200ms | Hệ thống ngăn chặn double submit, chỉ tạo đúng 1 bản ghi duy nhất | Critical | 2 lần submit <200ms | Yes | E2E | @Concurrency, @Resilience |
