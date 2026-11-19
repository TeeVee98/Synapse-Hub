# TEST CASES — QUẢN LÝ KHÁCH HÀNG DOANH NGHIỆP (CUSTOMER CRM)

> **Phương pháp:** Auto-Sanity Feasibility Test Suite  
> **Tiêu chuẩn:** ISO/IEC/IEEE 29119-3 (Bảng chuẩn 12 cột)  
> **Tỷ lệ:** 40% Happy Path — 40% Negative & Boundary — 20% Security & Resilience

---

| Case ID | REQ_ID | Module / Screen | Test Title & Objective | Pre-Condition | Test Steps (1-1) | Test Data | Expected Result | Priority / Severity | Risk Score (RPN) | Automatable / Type | Automation Tags |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| CUST_UI_001 | REQ-UI-CUST-01 | Customer UI | Thêm mới khách hàng doanh nghiệp thành công với đầy đủ thông tin chuẩn xác | Người dùng đã đăng nhập hệ thống CRM | 1. Truy cập trang examples/practices/contracts/customer_crm_app.html<br>2. Nhập 'Công ty Công nghệ Synapse' vào ô 'Tên công ty'<br>3. Nhập 'Nguyễn Văn A' vào ô 'Người liên hệ'<br>4. Nhập 'contact@synapse.vn' vào ô 'Email liên hệ'<br>5. Nhập '0912345678' vào ô 'Số điện thoại'<br>6. Nhấp nút 'Lưu khách hàng'<br>7. Kiểm tra hiển thị thông báo 'Khách hàng đã được tạo thành công' | company='Công ty Công nghệ Synapse', name='Nguyễn Văn A', email='contact@synapse.vn', phone='0912345678' | Hệ thống hiển thị thông báo 'Khách hàng đã được tạo thành công' với mã CUST mới | Critical | 24 | Yes / E2E | @Smoke, @Regression, @P0 |
| CUST_UI_002 | REQ-UI-CUST-02 | Customer UI | Bỏ trống các trường bắt buộc và gửi biểu mẫu | Người dùng ở màn hình Tạo mới khách hàng | 1. Truy cập trang examples/practices/contracts/customer_crm_app.html<br>2. Nhấp nút 'Lưu khách hàng' | Bỏ trống toàn bộ các trường bắt buộc | Hệ thống từ chối submit và hiển thị cảnh báo 'Có lỗi xảy ra trong quá trình lưu dữ liệu' | High | 16 | Yes / E2E | @Negative, @Validation |
| CUST_UI_003 | REQ-UI-CUST-03 | Customer UI | Kiểm tra phần tử bị vô hiệu hoá không cho phép tương tác | Người dùng ở màn hình form khách hàng | 1. Truy cập trang examples/practices/contracts/customer_crm_app.html<br>2. Nhấp nút 'Nút bị vô hiệu hoá' | Nút 'Nút bị vô hiệu hoá' | Hệ thống chặn thao tác do phần tử đang ở trạng thái disabled, bảo đảm resilience giao diện | Medium | 8 | Yes / E2E | @Boundary, @Negative, @Resilience |
| CUST_UI_004 | REQ-UI-CUST-04 | Customer UI | Kiểm tra phát hiện nút bấm không tồn tại trong giao diện (Locator Drift) | Mở màn hình tạo mới khách hàng | 1. Truy cập trang examples/practices/contracts/customer_crm_app.html<br>2. Nhấp nút 'Nút bấm ma không có thật' | Tên nút ma: 'Nút bấm ma không có thật' | Hệ thống không tìm thấy phần tử trong cây DOM và cảnh báo locator drift | High | 16 | Yes / E2E | @Drift, @Negative |
| CUST_UI_005 | REQ-UI-CUST-05 | Customer UI | Concurrency - Nhấp đúp nút Lưu khách hàng liên tiếp trong 200ms | Người dùng đã điền đủ các trường bắt buộc chuẩn xác | 1. Điền đủ các trường bắt buộc chuẩn xác<br>2. Nhấp nút 'Lưu khách hàng' 2 lần liên tiếp <200ms | 2 lần submit <200ms | Hệ thống ngăn chặn double submit, xử lý concurrency an toàn chỉ tạo đúng 1 bản ghi duy nhất | Critical | 24 | Yes / E2E | @Concurrency, @Resilience |

---

## Ambiguity & Assumptions Log

| ID | Requirement Reference / Statement | Ambiguity / Gap Detected | Working Assumption / Resolution | Impact / Risk |
|:---|:---|:---|:---|:---|
| AMB-UI-01 | DOM contract stability | Biểu mẫu customer_crm_app.html có thể thay đổi thuộc tính ID hay name | Sử dụng contract locator chuẩn hóa trên giao diện (CUST_UI_001) | Medium |
| AMB-UI-02 | Concurrency window | Thời gian ngưỡng double-click chặn thao tác gửi lặp | Giả định ngưỡng chặn là 200ms với nút submit chuyển sang disabled (CUST_UI_005) | High |
