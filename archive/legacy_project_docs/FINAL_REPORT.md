# 🎯 BÁO CÁO TỔNG KẾT DỰ ÁN AUTOMATION TESTING DMIT
> **Thời điểm hoàn thành**: 2026-10-21  
> **Hệ thống**: Quản lý Cơ sở dữ liệu ngành Công Thương (DMIT)  
> **Đơn vị phát triển test tự động**: Đội ngũ Automation QA  
> **Kiến trúc**: Flat Architecture + Clean Page Object Model (POM)  
> **Tổng số Test Cases**: **259 / 259 Test Cases**  

---

## 1. 📊 Tổng Quan Kết Quả

| Hạng Mục | Số Lượng / Trạng Thái | Ghi Chú |
|---|:---:|---|
| **Tổng số Test Cases (.tc)** | **259** | Chuẩn hóa tên gọi `TC-[ID] [Tên]` theo Excel phân công |
| **Tổng số Scripts (.groovy)** | **259** | 100% triển khai Clean POM, không có bypass hay code ảo |
| **Page Classes (`Keywords/dmit/pages`)** | **10** | Bao gồm `BasePage` + 9 Page Classes đại diện 9 phân hệ |
| **Helper Classes (`Keywords/dmit/helpers`)** | **1** | `DMITHelper.groovy` (tiện ích PrimeNG, định dạng, sinh dữ liệu) |
| **Test Listeners (`Test Listeners`)** | **1** | `Cleanup_Browser.groovy` (quản lý session và dọn dẹp browser) |
| **Test Suites (`Test Suites`)** | **10** | `All_DMIT_Tests.ts` + 5 Batch Suites + 4 Suite phân hệ |
| **Liên kết hỏng (Broken Links)** | **0** | Đã kiểm toán 100% tính toàn vẹn |
| **Tệp tin dính UTF-8 BOM** | **0** | Đã quét và làm sạch 505 tệp tin toàn dự án |

---

## 2. 🏗️ Phủ Sóng 9 Phân Hệ Theo Kiến Trúc Clean POM

| STT | Phân Hệ Chức Năng | Dải Mã Test Case | Số Lượng TC | Page Object Class Phụ Trách |
|:---:|---|:---:|:---:|---|
| 1 | Quản lý chỉ tiêu ngành Công Thương | `TC-1` – `TC-7` | 7 | `dmit.pages.TargetPlanPage` |
| 2 | Xác thực người dùng & Hồ sơ | `TC-8` – `TC-12` | 5 | `dmit.pages.LoginPage` |
| 3 | Quản trị hệ thống | `TC-13` – `TC-16` | 4 | `dmit.pages.UserAdminPage` |
| 4 | Quản trị danh mục dùng chung | `TC-17` – `TC-28` | 12 | `dmit.pages.CommonCategoryPage` |
| 5 | Quản trị danh mục ngành Công Thương | `TC-29` – `TC-92` | 64 | `dmit.pages.IndustryCategoryPage` |
| 6 | Quy hoạch ngành Công Thương | `TC-93` – `TC-122` | 30 | `dmit.pages.PlanningPage` |
| 7 | Quản trị dữ liệu Công Thương | `TC-123` – `TC-247` | 125 | `dmit.pages.DataMiningPage` |
| 8 | Báo cáo thống kê | `TC-248` – `TC-249` | 2 | `dmit.pages.ReportPage` |
| 9 | Chia sẻ dữ liệu | `TC-250` – `TC-259` | 10 | `dmit.pages.TokenMgmtPage` |
| **TỔNG** | **Toàn bộ hệ thống DMIT** | **`TC-1` – `TC-259`** | **259** | **100% Phủ kín POM** |

---

## 3. 🚀 Danh Sách Batch Test Suites Cho CI/CD

Các Batch Suites được cấu hình `isReuseDriver = true` để chạy hàng loạt tốc độ cao mà không phải tắt/mở trình duyệt liên tục:

1. **01_QuanLyChiTieu.ts** (7 TCs): Phân hệ 1 - Quản lý chỉ tiêu ngành Công Thương.
2. **02_XacThucNguoiDung.ts** (5 TCs): Phân hệ 2 - Xác thực người dùng & Hồ sơ cá nhân.
3. **03_QuanTriHeThong.ts** (4 TCs): Phân hệ 3 - Quản trị hệ thống & Người dùng.
4. **04_DanhMucDungChung.ts** (12 TCs): Phân hệ 4 - Danh mục dùng chung (Phòng ban, Chức vụ, Ngành nghề).
5. **05_DanhMucNganhCongThuong.ts** (64 TCs): Phân hệ 5 - Danh mục ngành Công Thương (16 tiểu danh mục).
6. **06_QuyHoachCongThuong.ts** (30 TCs): Phân hệ 6 - Quy hoạch ngành Công Thương (5 phân lớp quy hoạch).
7. **07_QuanTriDuLieu.ts** (125 TCs): Phân hệ 7 - Quản trị dữ liệu Công Thương & Dữ liệu biến động.
8. **08_BaoCaoThongKe.ts** (2 TCs): Phân hệ 8 - Báo cáo thống kê Dữ liệu & Giấy phép.
9. **09_ChiaSeDuLieu.ts** (10 TCs): Phân hệ 9 - Chia sẻ dữ liệu & Vòng đời Token API.
10. **10_All_DMIT_Tests.ts** (259 TCs): Toàn bộ 259 ca kiểm thử từ TC-1 đến TC-259.
11. **11_PROBE_E2E_Flow.ts** (1 TC): Tự động dò luồng và cào bản đồ XPath toàn hệ thống.

---

## 4. 🛡️ Cam Kết Chất Lượng (Quality Assurance)
- **Không Bypass Bậy:** Mọi test case đều mô phỏng chân thực chu trình tương tác người dùng: đăng nhập, mở menu, điền dữ liệu, tương tác controls, chờ và xác thực thông báo thành công từ Toast hoặc Dialog.
- **Tính Bền Vững:** Khi giao diện thay đổi, kiểm thử viên chỉ cần cập nhật Locators trong thư mục `Keywords/dmit/pages/`, 259 file script giữ nguyên vẹn.
- **Tương Thích Tuyệt Đối:** Loại bỏ 100% BOM ký tự để Katalon Studio trên mọi hệ điều hành (Windows, Linux CI) biên dịch mượt mà không gặp lỗi `Unexpected character: ''`.

---

## 5. 🏆 Báo Cáo Nghiệm Thu Toàn Diện Batch 07 (TC-123 đến TC-247) Đạt 100% PASS

> **Quy mô:** 125 Test Cases (`TC-123` đến `TC-247`) thuộc 19 bộ đối tượng phân hệ Quản lý dữ liệu & Bản đồ GIS.  
> **Chỉ đạo cốt lõi từ Project Lead / Ban Quản Trị:** Nghiệm thu tuần tự từng phân hệ, tuyệt đối không bypass giả lập, kiểm thử thực tế trên hệ thống live, tương tác thật, xác thực thông báo thật; Tạo phải có dữ liệu và tìm kiếm lại mã sau khi tạo; Chỉnh sửa đúng mã đã tạo; Tìm kiếm đúng mã; Dữ liệu biến động đầy đủ chu trình; Xóa thành công và xác thực lại dữ liệu đã xóa.  
> **Kết quả nghiệm thu:** **125/125 Test Cases PASSED 100%** (19/19 Nhóm Test Suite đạt Exit Code: 0).

### Bảng Bằng Chứng Nghiệm Thu 19 Phân Nhóm Đối Tượng (CSV Reports)

| STT | Tên Test Suite | Đối Tượng Kiểm Thử | Dải Test Case | Số Lượng | Kết Quả | Thời Gian | Tệp Báo Cáo CSV Nghiệm Thu |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---|
| 01 | `Group_07_01_CumCongNghiep` | **Cụm công nghiệp** | `TC-123` – `TC-126` | **4/4 (100%)** | :white_check_mark: **PASSED** | 2m - 12.222s | [`20261025_073255.csv`](Reports/20261025_073255/Group_07_01_CumCongNghiep/20261025_073255/20261025_073255.csv) |
| 02 | `Group_07_02_Cho` | **Chợ** | `TC-127` – `TC-134` | **8/8 (100%)** | :white_check_mark: **PASSED** | 13m - 8.195s | [`20261025_004227.csv`](Reports/20261025_004227/Group_07_02_Cho/20261025_004227/20261025_004227.csv) |
| 03 | `Group_07_03_SieuThi` | **Siêu thị** | `TC-135` – `TC-138` | **4/4 (100%)** | :white_check_mark: **PASSED** | 9m - 47.247s | [`20261025_010930.csv`](Reports/20261025_010929/Group_07_03_SieuThi/20261025_010930/20261025_010930.csv) |
| 04 | `Group_07_04_NguonDien` | **Nguồn điện** | `TC-139` – `TC-142` | **4/4 (100%)** | :white_check_mark: **PASSED** | 8m - 17.137s | [`20261025_012027.csv`](Reports/20261025_012027/Group_07_04_NguonDien/20261025_012027/20261025_012027.csv) |
| 05 | `Group_07_05_CHXD` | **Cửa hàng xăng dầu** | `TC-143` – `TC-149` | **7/7 (100%)** | :white_check_mark: **PASSED** | 10m - 20.623s | [`20261025_013133.csv`](Reports/20261025_013133/Group_07_05_CHXD/20261025_013133/20261025_013133.csv) |
| 06 | `Group_07_06_TNPP` | **Thương nhân phân phối xăng dầu** | `TC-150` – `TC-156` | **7/7 (100%)** | :white_check_mark: **PASSED** | 11m - 12.975s | [`20261025_014410.csv`](Reports/20261025_014410/Group_07_06_TNPP/20261025_014410/20261025_014410.csv) |
| 07 | `Group_07_07_VLN` | **Doanh nghiệp VLN công nghiệp** | `TC-157` – `TC-163` | **7/7 (100%)** | :white_check_mark: **PASSED** | 11m - 45.040s | [`20261025_015626.csv`](Reports/20261025_015626/Group_07_07_VLN/20261025_015626/20261025_015626.csv) |
| 08 | `Group_07_08_HoaChat` | **Doanh nghiệp hoá chất** | `TC-164` – `TC-170` | **7/7 (100%)** | :white_check_mark: **PASSED** | 9m - 1.603s | [`20261025_020929.csv`](Reports/20261025_020929/Group_07_08_HoaChat/20261025_020929/20261025_020929.csv) |
| 09 | `Group_07_09_CHTL` | **Cửa hàng tiện lợi** | `TC-171` – `TC-177` | **7/7 (100%)** | :white_check_mark: **PASSED** | 10m - 7.846s | [`20261025_021947.csv`](Reports/20261025_021947/Group_07_09_CHTL/20261025_021947/20261025_021947.csv) |
| 10 | `Group_07_10_TTTM` | **Trung tâm thương mại** | `TC-178` – `TC-184` | **7/7 (100%)** | :white_check_mark: **PASSED** | 10m - 19.297s | [`20261025_023050.csv`](Reports/20261025_023049/Group_07_10_TTTM/20261025_023050/20261025_023050.csv) |
| 11 | `Group_07_11_DaCap_1` | **Doanh nghiệp bán hàng đa cấp 1** | `TC-185` – `TC-191` | **7/7 (100%)** | :white_check_mark: **PASSED** | 10m - 43.214s | [`20261025_024208.csv`](Reports/20261025_024208/Group_07_11_DaCap_1/20261025_024208/20261025_024208.csv) |
| 12 | `Group_07_12_Logistics` | **Trung tâm Logistics** | `TC-192` – `TC-198` | **7/7 (100%)** | :white_check_mark: **PASSED** | 10m - 15.949s | [`20261025_025346.csv`](Reports/20261025_025346/Group_07_12_Logistics/20261025_025346/20261025_025346.csv) |
| 13 | `Group_07_13_BanLeRuou` | **Thương nhân bán lẻ rượu** | `TC-199` – `TC-205` | **7/7 (100%)** | :white_check_mark: **PASSED** | 11m - 42.951s | [`20261025_032433.csv`](Reports/20261025_032433/Group_07_13_BanLeRuou/20261025_032433/20261025_032433.csv) |
| 14 | `Group_07_14_TMDT` | **Doanh nghiệp thương mại điện tử** | `TC-206` – `TC-212` | **7/7 (100%)** | :white_check_mark: **PASSED** | 7m - 26.066s | [`20261025_044123.csv`](Reports/20261025_044123/Group_07_14_TMDT/20261025_044123/20261025_044123.csv) |
| 15 | `Group_07_15_ThuocLa` | **Thương nhân bán buôn thuốc lá** | `TC-213` – `TC-219` | **7/7 (100%)** | :white_check_mark: **PASSED** | 4m - 22.478s | [`20261025_045007.csv`](Reports/20261025_045007/Group_07_15_ThuocLa/20261025_045007/20261025_045007.csv) |
| 16 | `Group_07_16_HTX` | **Hợp tác xã** | `TC-220` – `TC-226` | **7/7 (100%)** | :white_check_mark: **PASSED** | 3m - 2.135s | [`20261025_045532.csv`](Reports/20261025_045532/Group_07_16_HTX/20261025_045532/20261025_045532.csv) |
| 17 | `Group_07_17_DaCap_2` | **Doanh nghiệp bán hàng đa cấp 2** | `TC-227` – `TC-233` | **7/7 (100%)** | :white_check_mark: **PASSED** | 3m - 56.859s | [`20261025_050059.csv`](Reports/20261025_050059/Group_07_17_DaCap_2/20261025_050059/20261025_050059.csv) |
| 18 | `Group_07_18_KinhDoanhKhi` | **Doanh nghiệp kinh doanh khí** | `TC-234` – `TC-240` | **7/7 (100%)** | :white_check_mark: **PASSED** | 7m - 58.219s | [`20261025_050559.csv`](Reports/20261025_050559/Group_07_18_KinhDoanhKhi/20261025_050559/20261025_050559.csv) |
| 19 | `Group_07_19_ThucPhamNhoLe` | **Cơ sở SX KD thực phẩm nhỏ lẻ** | `TC-241` – `TC-247` | **7/7 (100%)** | :white_check_mark: **PASSED** | 3m - 10.572s | [`20261025_051504.csv`](Reports/20261025_051503/Group_07_19_ThucPhamNhoLe/20261025_051504/20261025_051504.csv) |
| **TỔNG** | **19 Phân Nhóm Batch 07** | **Toàn Bộ Phân Hệ Quản Lý Dữ Liệu** | **`TC-123` – `TC-247`** | **125/125 (100%)** | :white_check_mark: **PASSED** | **~2h 45m** | **19/19 Tệp Báo Cáo CSV Hợp Lệ** |

---

## 6. 🏆 Báo Cáo Nghiệm Thu Toàn Diện Batch 01 (TC-1 đến TC-7) Đạt 100% PASS Theo Chuẩn Kỹ Năng Mới

> **Quy mô:** 7 Test Cases (`TC-1` đến `TC-7`) thuộc Phân hệ Quản lý chỉ tiêu ngành Công Thương.  
> **Cơ chế vận hành:** Tự hành đa tác nhân **Autonomous Multi-Agent Swarm** (`teamwork_preview`), giám sát độc lập bởi **Project Sentinel** và thẩm định pháp y bởi **Independent Victory Auditor**.  
> **Chuẩn kỹ thuật áp dụng:** Clean POM (Master Locator Priority Map 6 tầng), Hybrid Data Chain (chuỗi liên hoàn + fallback seeding tự phục hồi), **Tìm kiếm kế hoạch theo Tên (`planName`)**, 100% UTF-8 No BOM, Dual Verification (Toast + Grid Existence).  
> **Kết quả nghiệm thu:** **7/7 Test Cases PASSED 100% (0 Failures, 0 Errors)**, phán quyết: **VICTORY CONFIRMED**.

### Bảng Bằng Chứng Nghiệm Thu Test Suite 01_QuanLyChiTieu (JUnit XML & HTML Allure)

| STT | Mã Test Case | Tên Chức Năng Nghiệp Vụ | Trạng Thái | Thời Gian | Tệp Báo Cáo Nghiệm Thu |
|:---:|:---:|:---|:---:|:---:|:---|
| 01 | `TC-1` | Kiểm tra tạo mới kế hoạch chỉ tiêu thành công | :white_check_mark: **PASSED** | 53.441s | [`JUnit_Report.xml`](Reports/20261025_175205/01_QuanLyChiTieu/20261025_175205/JUnit_Report.xml) |
| 02 | `TC-2` | Kiểm tra chỉnh sửa giai đoạn/kế hoạch thành công | :white_check_mark: **PASSED** | 14.288s | [`JUnit_Report.xml`](Reports/20261025_175205/01_QuanLyChiTieu/20261025_175205/JUnit_Report.xml) |
| 03 | `TC-3` | Kiểm tra nhập báo cáo theo tháng khi - Kế hoạch có chỉ tiêu | :white_check_mark: **PASSED** | 15.529s | [`JUnit_Report.xml`](Reports/20261025_175205/01_QuanLyChiTieu/20261025_175205/JUnit_Report.xml) |
| 04 | `TC-4` | Kiểm tra chỉnh sửa báo cáo thành công | :white_check_mark: **PASSED** | 14.296s | [`JUnit_Report.xml`](Reports/20261025_175205/01_QuanLyChiTieu/20261025_175205/JUnit_Report.xml) |
| 05 | `TC-5` | Xoá báo cáo chỉ tiêu của kế hoạch thành công | :white_check_mark: **PASSED** | 14.774s | [`JUnit_Report.xml`](Reports/20261025_175205/01_QuanLyChiTieu/20261025_175205/JUnit_Report.xml) |
| 06 | `TC-6` | Xoá tất cả chỉ tiêu của kế hoạch thành công | :white_check_mark: **PASSED** | 15.525s | [`JUnit_Report.xml`](Reports/20261025_175205/01_QuanLyChiTieu/20261025_175205/JUnit_Report.xml) |
| 07 | `TC-7` | Kiểm tra xóa giai đoạn/kế hoạch thành công | :white_check_mark: **PASSED** | 15.225s | [`JUnit_Report.xml`](Reports/20261025_175205/01_QuanLyChiTieu/20261025_175205/JUnit_Report.xml) |
| **TỔNG** | **Suite 01** | **Quản Lý Chỉ Tiêu Ngành Công Thương** | **7/7 (100%)** | :white_check_mark: **PASSED** | **143.078s (~2m 23s)** | [`20261025_175205.html`](Reports/20261025_175205/01_QuanLyChiTieu/20261025_175205/20261025_175205.html) |

---

## 7. 🏆 Báo Cáo Nghiệm Thu Toàn Diện Batch 02 (TC-8 đến TC-12) Đạt 100% PASS Theo Chuẩn Kỹ Năng Mới

> **Quy mô:** 5 Test Cases (`TC-8` đến `TC-12`) thuộc Phân hệ Xác thực người dùng, Hồ sơ cá nhân & Đăng xuất.  
> **Cơ chế vận hành:** Tự hành đa tác nhân **Autonomous Multi-Agent Swarm** (`teamwork_preview`), khảo sát DOM & phân tích API qua **Playwright Live Interaction**, tối ưu mã Clean POM và thực thi nghiệm thu trên Katalon KRE CLI.  
> **Chuẩn kỹ thuật áp dụng:**
> - Clean POM (Master Locator Priority Map 6 tầng trên `LoginPage.groovy`).
> - Quản lý phiên cách ly an toàn (Session Isolation), bảo vệ tài khoản quản trị khi chạy Negative Tests (`TC-9`, `TC-10`).
> - Khảo sát live DOM & Angular Form: Điền form an toàn kết hợp Synthetic Events (`setInputValue`), kiểm tra Họ và tên hai tầng (Trực tiếp + Case-insensitive fallback).
> - Tự động hoàn trả tên gốc sau khi cập nhật hồ sơ (`TC-11`), kiểm thử Đăng xuất chuyển hướng chính xác về `/auth` (`TC-12`).
> - 100% tệp đạt chuẩn **UTF-8 No BOM** (không chứa `0xEF, 0xBB, 0xBF`), Flat Architecture bảo toàn trọn vẹn.  
> **Kết quả nghiệm thu:** **5/5 Test Cases PASSED 100% (0 Failures, 0 Errors)**, Thời gian thực thi: **39.982s (~40s)**, KRE Exit code: **0**.

### Bảng Bằng Chứng Nghiệm Thu Test Suite 02_XacThucNguoiDung (JUnit XML & HTML Allure)

| STT | Mã Test Case | Tên Chức Năng Nghiệp Vụ | Trạng Thái | Thời Gian | Tệp Báo Cáo Nghiệm Thu |
|:---:|:---:|:---|:---:|:---:|:---|
| 01 | `TC-8` | Đăng nhập thành công với tài khoản quản trị | :white_check_mark: **PASSED** | 20.514s | [`JUnit_Report.xml`](Reports/20261025_183504/02_XacThucNguoiDung/20261025_183504/JUnit_Report.xml) |
| 02 | `TC-9` | Đăng nhập khi sai mật khẩu (Tài khoản cô lập an toàn) | :white_check_mark: **PASSED** | 3.605s | [`JUnit_Report.xml`](Reports/20261025_183504/02_XacThucNguoiDung/20261025_183504/JUnit_Report.xml) |
| 03 | `TC-10` | Đăng nhập khi sai Tên đăng nhập | :white_check_mark: **PASSED** | 3.317s | [`JUnit_Report.xml`](Reports/20261025_183504/02_XacThucNguoiDung/20261025_183504/JUnit_Report.xml) |
| 04 | `TC-11` | Cập nhật thông tin hợp lệ & Hoàn trả tên gốc | :white_check_mark: **PASSED** | 10.100s | [`JUnit_Report.xml`](Reports/20261025_183504/02_XacThucNguoiDung/20261025_183504/JUnit_Report.xml) |
| 05 | `TC-12` | Kiểm thử chức năng Đăng xuất và trở về `/auth` | :white_check_mark: **PASSED** | 1.717s | [`JUnit_Report.xml`](Reports/20261025_183504/02_XacThucNguoiDung/20261025_183504/JUnit_Report.xml) |
| **TỔNG** | **Suite 02** | **Xác Thực Người Dùng & Hồ Sơ Cá Nhân** | **5/5 (100%)** | :white_check_mark: **PASSED** | **39.982s (~40s)** | [`20261025_183504.html`](Reports/20261025_183504/02_XacThucNguoiDung/20261025_183504/20261025_183504.html) |

---

## 8. 🏆 Báo Cáo Nghiệm Thu Toàn Diện Batch 03 (TC-13 đến TC-16) Đạt 100% PASS Theo Chuẩn Kỹ Năng Mới

> **Quy mô:** 4 Test Cases (`TC-13` đến `TC-16`) thuộc Phân hệ Quản trị hệ thống & Người dùng.  
> **Cơ chế vận hành:** Tự hành đa tác nhân **Autonomous Multi-Agent Swarm** (`teamwork_preview`), phân tích DOM thực tế qua **Playwright Live Interaction**, tái cấu trúc Page Object theo chuẩn Clean POM và nghiệm thu trực tiếp qua Katalon KRE CLI.  
> **Chuẩn kỹ thuật áp dụng:**
> - Clean POM (Master Locator Priority Map 6 tầng trên `UserAdminPage.groovy`).
> - **3-Tier State Persistence**: Memory -> JVM System Properties -> Cross-platform Relative Disk Properties File (`Reports/batch03_user.properties`), loại bỏ hoàn toàn hardcoded Windows path `D:/DMIT/...`.
> - **Fallback Precondition Seeder (`ensureUserExists()`)**: Tự động mồi người dùng mẫu khi chạy lẻ độc lập TC-14, TC-15, TC-16, loại trừ hoàn toàn nguy cơ rớt test do thiếu dữ liệu tiền đề.
> - **Targeted Row Operations**: Tìm kiếm và click chính xác nút Sửa/Xóa theo hàng email đích (`targetEmail`) thay vì click dòng đầu tiên mù quáng.
> - **Angular Form Safe Injection (`setInputValue`)**: Kích hoạt đầy đủ synthetic events (`input`, `change`, `blur`), khắc phục triệt để lỗi Angular Reactive Form không lưu giá trị `firstName` khi sửa người dùng.
> - 100% tệp đạt chuẩn **UTF-8 No BOM** (không chứa `0xEF, 0xBB, 0xBF`), Flat Architecture bảo toàn trọn vẹn.  
> **Kết quả nghiệm thu:** **4/4 Test Cases PASSED 100% (0 Failures, 0 Errors)**, Thời gian thực thi: **84.036s (~1m 24s)**, KRE Exit code: **0**.

### Bảng Bằng Chứng Nghiệm Thu Test Suite 03_QuanTriHeThong (JUnit XML & HTML Allure)

| STT | Mã Test Case | Tên Chức Năng Nghiệp Vụ | Trạng Thái | Thời Gian | Tệp Báo Cáo Nghiệm Thu |
|:---:|:---:|:---|:---:|:---:|:---|
| 01 | `TC-13` | Thêm mới người dùng | :white_check_mark: **PASSED** | 39.134s | [`JUnit_Report.xml`](Reports/20261025_185750/03_QuanTriHeThong/20261025_185750/JUnit_Report.xml) |
| 02 | `TC-14` | Chỉnh sửa người dùng | :white_check_mark: **PASSED** | 18.352s | [`JUnit_Report.xml`](Reports/20261025_185750/03_QuanTriHeThong/20261025_185750/JUnit_Report.xml) |
| 03 | `TC-15` | Tìm kiếm người dùng | :white_check_mark: **PASSED** | 7.677s | [`JUnit_Report.xml`](Reports/20261025_185750/03_QuanTriHeThong/20261025_185750/JUnit_Report.xml) |
| 04 | `TC-16` | Xoá người dung | :white_check_mark: **PASSED** | 18.169s | [`JUnit_Report.xml`](Reports/20261025_185750/03_QuanTriHeThong/20261025_185750/JUnit_Report.xml) |
| **TỔNG** | **Suite 03** | **Quản Trị Hệ Thống & Người Dùng** | **4/4 (100%)** | :white_check_mark: **PASSED** | **84.036s (~1m 24s)** | [`20261025_185750.html`](Reports/20261025_185750/03_QuanTriHeThong/20261025_185750/20261025_185750.html) |

---

## 9. 🏆 Báo Cáo Nghiệm Thu Toàn Diện Batch 04 (TC-17 đến TC-28) Đạt 100% PASS Theo Chuẩn Kỹ Năng Mới

> **Quy mô:** 12 Test Cases (`TC-17` đến `TC-28`) thuộc Phân hệ Quản trị danh mục dùng chung (Phòng ban, Chức vụ, Ngành nghề kinh doanh).  
> **Cơ chế vận hành:** Tự hành đa tác nhân **Autonomous Multi-Agent Swarm** (`teamwork_preview`), khảo sát live DOM/AOM và network request qua **Playwright Live Interaction**, tái cấu trúc hoàn toàn Clean POM và thực thi nghiệm thu trên Katalon KRE CLI.  
> **Chuẩn kỹ thuật áp dụng:**
> - **Clean POM & Master Locators (`CommonCategoryPage.groovy`)**: Chuẩn hóa điều hướng và tương tác trên cả 3 danh mục dùng chung: Phòng ban (`/category/shared/7`), Chức vụ (`/category/shared/8`), Ngành nghề kinh doanh (`/category/shared/15`).
> - **3-Tier State Persistence**: Quản lý chia sẻ dữ liệu liên test case xuyên suốt (Memory -> JVM System Properties -> Cross-platform Relative Disk Properties File `Reports/batch04_category.properties`), xóa bỏ hoàn toàn hardcoded Windows path `D:/DMIT/...`.
> - **Bộ 3 Precondition Seeders Độc lập**: `ensureDepartmentExists()`, `ensurePositionExists()`, `ensureCareerExists()` tự động kiểm tra và mồi dữ liệu khi chạy độc lập bất kỳ test case Tìm kiếm, Sửa hoặc Xóa nào.
> - **Đồng bộ hóa Angular Reactive Form Async (`editItem`)**: Chờ thông minh dữ liệu hiện tại được API tải vào form trước khi clear và gán giá trị mới kèm chuỗi synthetic events (`input`, `change`, `blur`), giải quyết triệt để lỗi async `patchValue` ghi đè giá trị cũ.
> - **Targeted CRUD Operations**: Thao tác Chỉnh sửa / Xóa đúng dòng bản ghi theo mã mục tiêu (`targetCode`), kết hợp tải mới dữ liệu (`WebUI.refresh()`) và xác minh kép (Mã & Tên mới).
> - **100% UTF-8 No BOM**: Toàn bộ tệp mã nguồn được kiểm định không chứa BOM bytes (`0xEF, 0xBB, 0xBF`), Flat Architecture bảo toàn tuyệt đối.  
> **Kết quả nghiệm thu:** **12/12 Test Cases PASSED 100% (0 Failures, 0 Errors)**, Thời gian thực thi: **177.115s (~2m 57s)**, KRE Exit code: **0**.

### Bảng Bằng Chứng Nghiệm Thu Test Suite 04_DanhMucDungChung (JUnit XML & HTML Allure)

| STT | Mã Test Case | Tên Chức Năng Nghiệp Vụ | Trạng Thái | Thời Gian | Tệp Báo Cáo Nghiệm Thu |
|:---:|:---:|:---|:---:|:---:|:---|
| 01 | `TC-17` | Thêm mới Phòng ban | :white_check_mark: **PASSED** | 32.208s | [`JUnit_Report.xml`](Reports/20261025_200732/04_DanhMucDungChung/20261025_200732/JUnit_Report.xml) |
| 02 | `TC-18` | Tìm kiếm phòng ban | :white_check_mark: **PASSED** | 6.383s | [`JUnit_Report.xml`](Reports/20261025_200732/04_DanhMucDungChung/20261025_200732/JUnit_Report.xml) |
| 03 | `TC-19` | Chỉnh sửa phòng ban | :white_check_mark: **PASSED** | 16.489s | [`JUnit_Report.xml`](Reports/20261025_200732/04_DanhMucDungChung/20261025_200732/JUnit_Report.xml) |
| 04 | `TC-20` | Xoá phòng ban | :white_check_mark: **PASSED** | 14.992s | [`JUnit_Report.xml`](Reports/20261025_200732/04_DanhMucDungChung/20261025_200732/JUnit_Report.xml) |
| 05 | `TC-21` | Thêm mới Chức vụ | :white_check_mark: **PASSED** | 10.035s | [`JUnit_Report.xml`](Reports/20261025_200732/04_DanhMucDungChung/20261025_200732/JUnit_Report.xml) |
| 06 | `TC-22` | Kiểm tra tìm kiếm theo - Mã Chức vụ | :white_check_mark: **PASSED** | 6.256s | [`JUnit_Report.xml`](Reports/20261025_200732/04_DanhMucDungChung/20261025_200732/JUnit_Report.xml) |
| 07 | `TC-23` | Kiểm tra chỉnh sửa khi - Nhập thông tin hợp lệ (Chức vụ) | :white_check_mark: **PASSED** | 17.145s | [`JUnit_Report.xml`](Reports/20261025_200732/04_DanhMucDungChung/20261025_200732/JUnit_Report.xml) |
| 08 | `TC-24` | Kiểm tra khi xóa một Chức vụ | :white_check_mark: **PASSED** | 15.713s | [`JUnit_Report.xml`](Reports/20261025_200732/04_DanhMucDungChung/20261025_200732/JUnit_Report.xml) |
| 09 | `TC-25` | Thêm mới Ngành nghề kinh doanh | :white_check_mark: **PASSED** | 10.160s | [`JUnit_Report.xml`](Reports/20261025_200732/04_DanhMucDungChung/20261025_200732/JUnit_Report.xml) |
| 10 | `TC-26` | Kiểm tra tìm kiếm theo - Mã Ngành nghề kinh doanh | :white_check_mark: **PASSED** | 5.575s | [`JUnit_Report.xml`](Reports/20261025_200732/04_DanhMucDungChung/20261025_200732/JUnit_Report.xml) |
| 11 | `TC-27` | Kiểm tra chỉnh sửa khi - Nhập thông tin hợp lệ (Ngành nghề) | :white_check_mark: **PASSED** | 23.218s | [`JUnit_Report.xml`](Reports/20261025_200732/04_DanhMucDungChung/20261025_200732/JUnit_Report.xml) |
| 12 | `TC-28` | Kiểm tra khi xóa một Ngành nghề kinh doanh | :white_check_mark: **PASSED** | 17.990s | [`JUnit_Report.xml`](Reports/20261025_200732/04_DanhMucDungChung/20261025_200732/JUnit_Report.xml) |
| **TỔNG** | **Suite 04** | **Quản Trị Danh Mục Dùng Chung** | **12/12 (100%)** | :white_check_mark: **PASSED** | **177.115s (~2m 57s)** | [`20261025_200732.html`](Reports/20261025_200732/04_DanhMucDungChung/20261025_200732/20261025_200732.html) |




---

## 10. 🏆 Báo Cáo Nghiệm Thu Toàn Diện Batch 05 (TC-29 đến TC-92) Đạt 100% PASS Theo Chuẩn Kỹ Năng Mới

> **Quy mô:** 64 Test Cases (`TC-29` đến `TC-92`) thuộc Phân hệ Danh mục ngành Công Thương, bao quát toàn diện 16 tiểu danh mục chuyên ngành.
> **Cơ chế vận hành:** Tự hành đa tác nhân **Autonomous Multi-Agent Swarm** (`teamwork_preview`), khảo sát live DOM/AOM và URL routing qua **Playwright Live Interaction**, tái cấu trúc hoàn chỉnh Clean POM trên `IndustryCategoryPage.groovy` và thực thi nghiệm thu trên Katalon KRE CLI.
> **Chuẩn kỹ thuật áp dụng:**
> - **Clean POM & 16 Subcategories Master Direct URL Routing (`IndustryCategoryPage.groovy`)**: Điều hướng trực tiếp bằng Angular route URL (`/category/industry-and-trade/1..27`), loại bỏ hoàn toàn độ trễ dò tìm click menu, rút ngắn thời gian thực thi từ 12m17s xuống **8m24s (tiết kiệm ~4 phút, nhanh hơn 32%)**.
> - **3-Tier State Persistence**: Quản lý chia sẻ dữ liệu liên test case giữa Create -> Edit -> Search -> Delete xuyên suốt (In-Memory Cache -> JVM System Properties -> Disk Properties đa nền tảng `Reports/batch05_industry.properties`).
> - **Đồng bộ hóa Angular Reactive Form Async (`setInputValue`)**: Chờ thông minh dữ liệu cũ tải vào form trước khi clear và gán tên mới kèm chuỗi synthetic events (`input`, `change`, `blur`), loại bỏ 100% race condition `patchValue`.
> - **Bộ Precondition Seeders Tự Động (`ensureSubCategoryItemExists`)**: Tự động mồi dữ liệu mẫu khi chạy độc lập bất kỳ test case Sửa/Xóa/Tìm kiếm nào mà không làm gãy flow.
> - **Targeted Selectors**: Định vị thao tác Sửa/Xóa đúng dòng bản ghi theo mã mục tiêu (`BTN_EDIT_TARGETED`, `BTN_DELETE_TARGETED`).
> - **100% UTF-8 No BOM**: Toàn bộ tệp mã nguồn được kiểm định không chứa BOM bytes (`0xEF, 0xBB, 0xBF`), Flat Architecture bảo toàn tuyệt đối.
> **Kết quả nghiệm thu:** **64/64 Test Cases PASSED 100% (0 Failures, 0 Errors)**, Thời gian thực thi: **504.545s (~8m 24s)**, KRE Exit code: **0**.

### Bảng Bằng Chứng Nghiệm Thu Test Suite 05_DanhMucNganhCongThuong (JUnit XML & HTML Allure)

| STT | Mã Test Case | Tên Chức Năng Nghiệp Vụ | Trạng Thái | Thời Gian | Tệp Báo Cáo Nghiệm Thu |
|:---:|:---:|:---|:---:|:---:|:---|
| 01 | `TC-29` | Kiểm tra thêm mới Ngành kinh tế | :white_check_mark: **PASSED** | 34.631s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 02 | `TC-30` | Kiểm tra chỉnh sửa bỏ chọn  Ngành kinh tế cha | :white_check_mark: **PASSED** | 9.422s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 03 | `TC-32` | Tìm kiếm ngành kinh tế | :white_check_mark: **PASSED** | 3.644s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 04 | `TC-31` | Kiểm tra khi xóa một ngành kinh tế | :white_check_mark: **PASSED** | 8.094s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 05 | `TC-33` | Kiểm tra thêm mới Ngành sản phẩm | :white_check_mark: **PASSED** | 8.403s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 06 | `TC-34` | Chỉnh sửa ngành sản phẩm | :white_check_mark: **PASSED** | 8.304s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 07 | `TC-36` | Tìm kiếm ngành sản phẩm | :white_check_mark: **PASSED** | 3.540s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 08 | `TC-35` | Xóa một Ngành sản phẩm | :white_check_mark: **PASSED** | 7.975s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 09 | `TC-37` | Kiểm tra thêm mới Hàng hoá xuất nhập khẩu | :white_check_mark: **PASSED** | 14.285s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 10 | `TC-38` | Chỉnh sửa Hàng hoá xuất nhập khẩu | :white_check_mark: **PASSED** | 12.917s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 11 | `TC-40` | Tìm kiếm Hàng hoá xuất nhập khẩu | :white_check_mark: **PASSED** | 4.175s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 12 | `TC-39` | Xóa một Hàng hoá xuất nhập khẩu | :white_check_mark: **PASSED** | 8.985s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 13 | `TC-41` | Kiểm tra thêm mới Lĩnh vực công thương | :white_check_mark: **PASSED** | 8.221s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 14 | `TC-42` | Kiểm tra chỉnh sửa Lĩnh vực công thương | :white_check_mark: **PASSED** | 7.984s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 15 | `TC-44` | Tìm kiếm lĩnh vực công thương | :white_check_mark: **PASSED** | 4.169s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 16 | `TC-43` | Kiểm tra khi xóa một Lĩnh vực công thương | :white_check_mark: **PASSED** | 7.942s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 17 | `TC-45` | Kiểm tra thêm mới Dịch vụ xuất nhập khẩu | :white_check_mark: **PASSED** | 9.905s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 18 | `TC-46` | Kiểm tra chỉnh sửa Dịch vụ xuất nhập khẩu | :white_check_mark: **PASSED** | 9.208s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 19 | `TC-48` | Tìm kiếm Dịch vụ xuất nhập khẩu | :white_check_mark: **PASSED** | 3.697s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 20 | `TC-47` | Kiểm tra khi xóa một Dịch vụ xuất nhập khẩu | :white_check_mark: **PASSED** | 7.922s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 21 | `TC-49` | Kiểm tra thêm mới Hàng hoá, dịch vụ bình ổn giá | :white_check_mark: **PASSED** | 10.026s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 22 | `TC-50` | Kiểm tra chỉnh sửa Hàng hoá, dịch vụ bình ổn giá | :white_check_mark: **PASSED** | 8.251s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 23 | `TC-52` | Tìm kiếm Hàng hoá, dịch vụ bình ổn giá | :white_check_mark: **PASSED** | 3.490s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 24 | `TC-51` | Kiểm tra khi xóa một Hàng hoá, dịch vụ bình ổn giá | :white_check_mark: **PASSED** | 7.813s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 25 | `TC-53` | Kiểm tra thêm mới Thiết bị SXKD LPGLNGCNG | :white_check_mark: **PASSED** | 9.547s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 26 | `TC-54` | Kiểm tra chỉnh sửa Thiết bị SXKD LPGLNGCNG | :white_check_mark: **PASSED** | 8.127s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 27 | `TC-56` | Tìm kiếm Thiết bị SXKD LPGLNGCNG | :white_check_mark: **PASSED** | 3.489s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 28 | `TC-55` | Kiểm tra khi xóa một Thiết bị SXKD LPGLNGCNG | :white_check_mark: **PASSED** | 7.820s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 29 | `TC-57` | Kiểm tra thêm mới Thiết bị SXKD hoá chất | :white_check_mark: **PASSED** | 8.966s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 30 | `TC-58` | Kiểm tra chỉnh sửa Thiết bị SXKD hoá chất | :white_check_mark: **PASSED** | 8.066s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 31 | `TC-60` | Tìm kiếm Thiết bị SXKD hoá chất | :white_check_mark: **PASSED** | 3.459s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 32 | `TC-59` | Kiểm tra khi xóa một Thiết bị SXKD hoá chất | :white_check_mark: **PASSED** | 7.789s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 33 | `TC-61` | Kiểm tra thêm mới Thiết bị SXKD rượu | :white_check_mark: **PASSED** | 9.295s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 34 | `TC-62` | Kiểm tra chỉnh sửa Thiết bị SXKD rượu | :white_check_mark: **PASSED** | 8.190s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 35 | `TC-64` | Tìm kiếm Thiết bị SXKD rượu | :white_check_mark: **PASSED** | 3.500s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 36 | `TC-63` | Kiểm tra khi xóa một Thiết bị SXKD rượu | :white_check_mark: **PASSED** | 7.800s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 37 | `TC-65` | Kiểm tra thêm mới Thiết bị SXKD Thực phẩm | :white_check_mark: **PASSED** | 9.022s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 38 | `TC-66` | Kiểm tra chỉnh sửa Thiết bị SXKD Thực phẩm | :white_check_mark: **PASSED** | 8.092s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 39 | `TC-68` | Tìm kiếm Thiết bị SXKD Thực phẩm | :white_check_mark: **PASSED** | 3.498s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 40 | `TC-67` | Kiểm tra khi xóa một Thiết bị SXKD Thực phẩm | :white_check_mark: **PASSED** | 7.869s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 41 | `TC-69` | Kiểm tra thêm mới Thiết bị SXKD Xăng dầu | :white_check_mark: **PASSED** | 9.933s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 42 | `TC-70` | Kiểm tra chỉnh sửa Thiết bị SXKD Xăng dầu | :white_check_mark: **PASSED** | 7.934s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 43 | `TC-72` | Tìm kiếm Thiết bị SXKD Xăng dầu | :white_check_mark: **PASSED** | 3.466s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 44 | `TC-71` | Kiểm tra khi xóa một Thiết bị SXKD Xăng dầu | :white_check_mark: **PASSED** | 7.779s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 45 | `TC-73` | Kiểm tra thêm mới Thiết bị SXKD Thuốc lá | :white_check_mark: **PASSED** | 10.354s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 46 | `TC-74` | Kiểm tra chỉnh sửa Thiết bị SXKD Thuốc lá | :white_check_mark: **PASSED** | 7.984s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 47 | `TC-76` | Tìm kiếm Thiết bị SXKD Thuốc lá | :white_check_mark: **PASSED** | 3.564s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 48 | `TC-75` | Kiểm tra khi xóa một Thiết bị SXKD Thuốc lá | :white_check_mark: **PASSED** | 7.802s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 49 | `TC-77` | Kiểm tra thêm mới Thiết bị SXKD lĩnh vực CT | :white_check_mark: **PASSED** | 9.382s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 50 | `TC-78` | Kiểm tra chỉnh sửa Thiết bị SXKD lĩnh vực CT | :white_check_mark: **PASSED** | 7.956s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 51 | `TC-80` | Tìm kiếm Thiết bị SXKD lĩnh vực CT | :white_check_mark: **PASSED** | 3.478s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 52 | `TC-79` | Kiểm tra khi xóa một Thiết bị SXKD lĩnh vực CT | :white_check_mark: **PASSED** | 7.783s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 53 | `TC-81` | Kiểm tra thêm mới Thiết bị SXKD Phát điện | :white_check_mark: **PASSED** | 9.662s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 54 | `TC-82` | Kiểm tra chỉnh sửa Thiết bị SXKD Phát điện | :white_check_mark: **PASSED** | 7.994s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 55 | `TC-84` | Tìm kiếm Thiết bị SXKD Phát điện | :white_check_mark: **PASSED** | 3.450s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 56 | `TC-83` | Kiểm tra khi xóa một Thiết bị SXKD Phát điện | :white_check_mark: **PASSED** | 7.779s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 57 | `TC-85` | Kiểm tra thêm mới Lĩnh vực công nghiệp | :white_check_mark: **PASSED** | 9.193s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 58 | `TC-86` | Kiểm tra chỉnh sửa Lĩnh vực công nghiệp | :white_check_mark: **PASSED** | 9.219s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 59 | `TC-88` | Tìm kiếm Lĩnh vực công nghiệp | :white_check_mark: **PASSED** | 3.463s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 60 | `TC-87` | Kiểm tra khi xóa một Lĩnh vực công nghiệp | :white_check_mark: **PASSED** | 8.043s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 61 | `TC-89` | Kiểm tra thêm mới Lĩnh vực thuong mại | :white_check_mark: **PASSED** | 9.562s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 62 | `TC-90` | Kiểm tra chỉnh sửa Lĩnh vực thuong mại | :white_check_mark: **PASSED** | 8.086s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 63 | `TC-92` | Tìm kiếm Lĩnh vực thuong mại | :white_check_mark: **PASSED** | 3.464s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| 64 | `TC-91` | Kiểm tra khi xóa một Lĩnh vực thuong mại | :white_check_mark: **PASSED** | 7.761s | [`JUnit_Report.xml`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/JUnit_Report.xml) |
| **TỔNG** | **Suite 05** | **Danh Mục Ngành Công Thương** | **64/64 (100%)** | :white_check_mark: **PASSED** | **504.545s (~8m 24s)** | [`20261025_204110.html`](Reports/20261025_204110/05_DanhMucNganhCongThuong/20261025_204110/20261025_204110.html) |

---

## 11. 🏆 Báo Cáo Nghiệm Thu Toàn Diện Batch 06 (TC-93 đến TC-122) Đạt 100% PASS Theo Chuẩn Kỹ Năng Mới

> **Quy mô:** 30 Test Cases (`TC-93` đến `TC-122`) thuộc Phân hệ 6: Quy hoạch ngành Công Thương, bao quát toàn diện 5 phân lớp quy hoạch: Cơ khí và luyện kim, Cụm công nghiệp, Khu công nghiệp, Quy hoạch Chợ, Siêu thị.  
> **Cơ chế vận hành:** Tự hành đa tác nhân **Autonomous Multi-Agent Swarm**, khảo sát live DOM/AOM và `editor-widget` qua **Playwright Live Interaction**, tái cấu trúc hoàn chỉnh Clean POM trên `PlanningPage.groovy` và thực thi nghiệm thu trên Katalon KRE CLI.  
> **Chuẩn kỹ thuật áp dụng:**
> - **Clean POM & Layer Selection Engine (`PlanningPage.groovy`)**: Điều hướng tương tác đồng bộ hóa giữa công cụ biên tập bản đồ GIS (`BTN_PENCIL`), dropdown chọn phân lớp trong `editor-widget` và bảng quản lý danh sách quy hoạch (`BTN_LIST_PLANNING`).
> - **3-Tier State Persistence**: Quản lý chia sẻ dữ liệu mã dự án giữa Create -> Edit -> Search -> Delete xuyên suốt (In-Memory Cache -> JVM System Properties `batch06_...` -> Disk Properties `Reports/batch06_planning.properties`).
> - **Targeted Selectors**: Định vị thao tác Sửa/Xóa chính xác theo mã dự án mục tiêu (`BTN_EDIT_TARGETED`, `BTN_DELETE_TARGETED`), hạn chế tối đa rủi ro thao tác nhầm hàng khi dữ liệu bảng biến động.
> - **Precondition Auto-Seeder (`ensurePlanningExists`)**: Tự động mồi dữ liệu mẫu hợp lệ nếu chạy độc lập bất kỳ ca kiểm thử Sửa/Xóa/Tìm kiếm nào, loại bỏ hoàn toàn lỗi gãy chuỗi phụ thuộc dữ liệu.
> - **Xử Lý Nghiệp Vụ Hai Bước Khi Xóa**: Tự động mở form chỉnh sửa để bỏ chọn cờ *Quy hoạch được áp dụng* (`#IsActive`) trước khi thực hiện xóa vĩnh viễn trên modal xác nhận, giải quyết triệt để ràng buộc dữ liệu phía AUT.
> - **100% UTF-8 No BOM**: Toàn bộ tệp mã nguồn được kiểm định không chứa BOM bytes (`0xEF, 0xBB, 0xBF`), Flat Architecture bảo toàn tuyệt đối.
> **Kết quả nghiệm thu:** **30/30 Test Cases PASSED 100% (0 Failures, 0 Errors)**, Thời gian thực thi: **505.117s (~8m 25s)**, KRE Exit code: **0**.

### Bảng Bằng Chứng Nghiệm Thu Test Suite 06_QuyHoachCongThuong (JUnit XML & HTML Allure)

| STT | Mã Test Case | Tên Chức Năng Nghiệp Vụ | Trạng Thái | Thời Gian | Tệp Báo Cáo Nghiệm Thu |
|:---:|:---:|:---|:---:|:---:|:---|
| 01 | `TC-93` | Tạo mới dự án quy hoạch Cơ khí luyện kim | :white_check_mark: **PASSED** | 39.159s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 02 | `TC-94` | Kiểm tra thêm mới quy hoạch thành công | :white_check_mark: **PASSED** | 13.180s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 03 | `TC-95` | Kiểm tra chỉnh sửa quy hoạch thành công | :white_check_mark: **PASSED** | 15.099s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 04 | `TC-96` | Kiểm tra tìm kiếm quy hoạch theo thuộc tính | :white_check_mark: **PASSED** | 7.967s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 05 | `TC-97` | Kiểm tra xóa quy hoạch thành công | :white_check_mark: **PASSED** | 23.906s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 06 | `TC-98` | Tạo mới dự án quy hoạch Cụm công nghiệp | :white_check_mark: **PASSED** | 12.657s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 07 | `TC-99` | Kiểm tra thêm mới quy hoạch Cụm công nghiệp thành công | :white_check_mark: **PASSED** | 12.620s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 08 | `TC-100` | Kiểm tra chỉnh sửa quy hoạch Cụm công nghiệp thành công | :white_check_mark: **PASSED** | 15.025s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 09 | `TC-101` | Kiểm tra tìm kiếm quy hoạch Cụm công nghiệp theo thuộc tính | :white_check_mark: **PASSED** | 7.988s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 10 | `TC-102` | Kiểm tra xóa quy hoạch Cụm công nghiệp thành công | :white_check_mark: **PASSED** | 23.738s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 11 | `TC-103` | Tạo mới dự án quy hoạch Khu công nghiệp | :white_check_mark: **PASSED** | 12.594s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 12 | `TC-104` | Kiểm tra thêm mới quy hoạch Khu công nghiệp thành công | :white_check_mark: **PASSED** | 12.558s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 13 | `TC-105` | Kiểm tra chỉnh sửa quy hoạch Khu công nghiệp thành công | :white_check_mark: **PASSED** | 14.876s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 14 | `TC-106` | Kiểm tra tìm kiếm quy hoạch Khu công nghiệp theo thuộc tính | :white_check_mark: **PASSED** | 7.922s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 15 | `TC-107` | Kiểm tra xóa quy hoạch Khu công nghiệp thành công | :white_check_mark: **PASSED** | 23.658s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 16 | `TC-108` | Tạo mới dự án quy hoạch Quy hoạch chợ | :white_check_mark: **PASSED** | 12.470s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 17 | `TC-109` | Kiểm tra thêm mới quy hoạch Quy hoạch chợ thành công | :white_check_mark: **PASSED** | 12.524s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 18 | `TC-110` | Kiểm tra chỉnh sửa quy hoạch Quy hoạch chợ thành công | :white_check_mark: **PASSED** | 14.937s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 19 | `TC-111` | Kiểm tra tìm kiếm quy hoạch Quy hoạch chợ theo thuộc tính | :white_check_mark: **PASSED** | 8.458s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 20 | `TC-112` | Kiểm tra xóa quy hoạch Quy hoạch chợ thành công | :white_check_mark: **PASSED** | 23.695s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 21 | `TC-113` | Tạo mới dự án quy hoạch Siêu thị | :white_check_mark: **PASSED** | 12.473s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 22 | `TC-114` | Kiểm tra thêm mới quy hoạch Siêu thị thành công | :white_check_mark: **PASSED** | 12.427s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 23 | `TC-115` | Kiểm tra chỉnh sửa quy hoạch Siêu thị thành công | :white_check_mark: **PASSED** | 14.807s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 24 | `TC-116` | Kiểm tra tìm kiếm quy hoạch Siêu thị theo thuộc tính | :white_check_mark: **PASSED** | 7.828s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 25 | `TC-117` | Kiểm tra xóa quy hoạch Siêu thị thành công | :white_check_mark: **PASSED** | 23.639s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 26 | `TC-118` | Xoá dự án quy hoạch Cơ khí luyện kim | :white_check_mark: **PASSED** | 23.425s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 27 | `TC-119` | Xoá dự án quy hoạch Cụm công nghiệp | :white_check_mark: **PASSED** | 23.418s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 28 | `TC-120` | Xoá dự án quy hoạch Khu công nghiệp | :white_check_mark: **PASSED** | 23.440s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 29 | `TC-121` | Xoá dự án quy hoạch Quy hoạch chợ | :white_check_mark: **PASSED** | 23.936s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| 30 | `TC-122` | Xoá dự án quy hoạch Siêu thị | :white_check_mark: **PASSED** | 23.638s | [`JUnit_Report.xml`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/JUnit_Report.xml) |
| **TỔNG** | **Suite 06** | **Quy Hoạch Ngành Công Thương** | **30/30 (100%)** | :white_check_mark: **PASSED** | **505.117s (~8m 25s)** | [`20261025_210918.html`](Reports/20261025_210918/06_QuyHoachCongThuong/20261025_210918/20261025_210918.html) |

---

## 12. 🏆 Báo Cáo Nghiệm Thu Toàn Diện Batch 08 (TC-248 đến TC-249) Đạt 100% PASS Theo Chuẩn Kỹ Năng Mới

> **Quy mô:** 2 Test Cases (`TC-248` đến `TC-249`) thuộc Phân hệ 8: Báo cáo thống kê, bao quát 2 nghiệp vụ thống kê chuyên sâu: Báo cáo thống kê dữ liệu động ngành Công Thương và Báo cáo thống kê giấy phép.  
> **Cơ chế vận hành:** Tự hành đa tác nhân **Autonomous Multi-Agent Swarm**, khảo sát live DOM/AOM qua **Playwright Live Interaction**, tái cấu trúc hoàn chỉnh Clean POM trên `ReportPage.groovy` và thực thi nghiệm thu trên Katalon KRE CLI.  
> **Chuẩn kỹ thuật áp dụng:**
> - **Direct Route URL Navigation (`ReportPage.groovy`)**: Điều hướng trực tiếp bằng Angular router URLs (`/statistic/data-dynamic` và `/statistic/license`), loại bỏ 100% độ trễ và rủi ro click menu sidebar bị che khuất bởi giao diện bản đồ GIS.
> - **Smart Dropdown Selection**: Tìm kiếm và click option lớp bản đồ thông qua JavaScript scroll & click chuẩn xác, tự động đồng bộ hóa trạng thái enable/disable của nút *Thống kê*.
> - **Multi-Criteria License Statistic**: Hỗ trợ chọn linh hoạt các tiêu chí lọc (Tình trạng kích hoạt, Theo năm, Năm 2026) và tự động kích hoạt tính toán báo cáo giấy phép.
> - **Dual Verification**: Xác thực đa tầng kết hợp Toast thông báo thành công và kiểm tra sự hiển thị của bảng dữ liệu kết quả thống kê.
> - **100% UTF-8 No BOM**: Toàn bộ tệp mã nguồn được kiểm định không chứa BOM bytes (`0xEF, 0xBB, 0xBF`), Flat Architecture bảo toàn tuyệt đối.
> **Kết quả nghiệm thu:** **2/2 Test Cases PASSED 100% (0 Failures, 0 Errors)**, Thời gian thực thi: **36.272s**, KRE Exit code: **0**.

### Bảng Bằng Chứng Nghiệm Thu Test Suite 08_BaoCaoThongKe (JUnit XML & HTML Allure)

| STT | Mã Test Case | Tên Chức Năng Nghiệp Vụ | Trạng Thái | Thời Gian | Tệp Báo Cáo Nghiệm Thu |
|:---:|:---:|:---|:---:|:---:|:---|
| 01 | `TC-248` | Thống kê dữ liệu động ngành Công Thương | :white_check_mark: **PASSED** | 30.149s | [`JUnit_Report.xml`](Reports/20261025_224746/08_BaoCaoThongKe/20261025_224746/JUnit_Report.xml) |
| 02 | `TC-249` | Thống kê giấy phép kinh doanh ngành Công Thương | :white_check_mark: **PASSED** | 5.275s | [`JUnit_Report.xml`](Reports/20261025_224746/08_BaoCaoThongKe/20261025_224746/JUnit_Report.xml) |
| **TỔNG** | **Suite 08** | **Báo Cáo Thống Kê** | **2/2 (100%)** | :white_check_mark: **PASSED** | **36.272s** | [`20261025_224746.html`](Reports/20261025_224746/08_BaoCaoThongKe/20261025_224746/20261025_224746.html) |


---

## 13. 🏆 Báo Cáo Nghiệm Thu Toàn Diện Batch 09 (TC-250 đến TC-259) Đạt 100% PASS Theo Chuẩn Kỹ Năng Mới

> **Quy mô:** 10 Test Cases (`TC-250` đến `TC-259`) thuộc Phân hệ 9: Chia sẻ dữ liệu ngành Công Thương & Quản trị Token API, bao quát trọn vẹn 2 nhóm nghiệp vụ cốt lõi:
> 1. **Quản trị kết nối trục (`TC-250` -> `TC-253`):** Thêm mới kết nối trục hợp lệ, Tìm kiếm thông tin kết nối, Chỉnh sửa kết nối, Xóa kết nối.
> 2. **Vòng đời Token API (`TC-254` -> `TC-259`):** Thêm mới Token, Tìm kiếm Token, Gia hạn kết nối Token, Thu hồi Token (Khóa), Mở khóa Token, Xóa Token kết nối.  
> **Cơ chế vận hành:** Tự hành đa tác nhân **Autonomous Multi-Agent Swarm**, kết hợp khảo sát trực tiếp DOM/AOM qua **Playwright Live Interaction**, hoàn thiện Clean POM trên `TokenMgmtPage.groovy` (kế thừa `BasePage`) và thực thi headless trên Katalon KRE CLI.  
> **Chuẩn kỹ thuật & Kiến trúc giải pháp áp dụng:**
> - **Zero Hardcoded XPath in Test Scripts:** 100% mã kiểm thử trong `Scripts/TC-250` đến `TC-259` gọi qua phương thức của `TokenMgmtPage`, tuân thủ Clean POM và Flat Architecture tuyệt đối.
> - **Dynamic Test Data Generation:** Tự động sinh mã kết nối ngẫu nhiên thông qua `uniqueCode('CTU')` và ghi chú token qua `uniqueCode('TOK')` đảm bảo độc nhất, chống trùng lặp dữ liệu trong hệ thống.
> - **In-Memory & System Properties State Persistence:** Đồng bộ mã kết nối và ghi chú token giữa các test case thông qua bộ nhớ RAM tĩnh kết hợp JVM System Properties, đảm bảo luồng nghiệp vụ tìm kiếm, chỉnh sửa, xóa hoạt động liền mạch.
> - **Self-Healing Precondition Seeders (`ensureConnectionExists`, `ensureTokenExists`):** Tự động phát hiện và khởi tạo bản ghi kết nối hoặc Token nếu bảng dữ liệu trống, biến từng test case thành một đơn vị kiểm thử độc lập, có khả năng chạy riêng rẽ hoặc theo bộ mà không bị phụ thuộc thứ tự.
> - **SPA Navigation Synchronization Hot Patch:** Giải quyết triệt để lỗi bất đồng bộ chuyển trang Angular SPA giữa bảng kết nối trục `/system-management/lgsp` và trang phân quyền Token `/system-management/lgsp/permission/:id`, bảo vệ an toàn trước hiện tượng `StaleElementReferenceException`.
> - **100% UTF-8 No BOM & Zero Credential Leak:** Tất cả tệp nguồn tuân thủ nghiêm ngặt chuẩn UTF-8 No BOM, mật khẩu xác thực được truyền động qua biến môi trường `DMIT_PASSWORD`.
> **Kết quả nghiệm thu:** **10/10 Test Cases PASSED 100% (0 Failures, 0 Errors)**, Thời gian thực thi: **84.092s (~1m 24s)**, KRE Exit code: **0**.

### Bảng Bằng Chứng Nghiệm Thu Test Suite 09_ChiaSeDuLieu (JUnit XML & HTML Allure)

| STT | Mã Test Case | Tên Chức Năng Nghiệp Vụ | Trạng Thái | Thời Gian | Tệp Báo Cáo Nghiệm Thu |
|:---:|:---:|:---|:---:|:---:|:---|
| 01 | `TC-250` | Kiểm tra thêm mới thành công | :white_check_mark: **PASSED** | 24.464s | [`JUnit_Report.xml`](Reports/20261026_012901/09_ChiaSeDuLieu/20261026_012902/JUnit_Report.xml) |
| 02 | `TC-251` | Tìm kiếm thông tin kết nối | :white_check_mark: **PASSED** | 1.429s | [`JUnit_Report.xml`](Reports/20261026_012901/09_ChiaSeDuLieu/20261026_012902/JUnit_Report.xml) |
| 03 | `TC-252` | Chỉnh sửa kết nối | :white_check_mark: **PASSED** | 1.070s | [`JUnit_Report.xml`](Reports/20261026_012901/09_ChiaSeDuLieu/20261026_012902/JUnit_Report.xml) |
| 04 | `TC-253` | Xoá kết nối | :white_check_mark: **PASSED** | 6.863s | [`JUnit_Report.xml`](Reports/20261026_012901/09_ChiaSeDuLieu/20261026_012902/JUnit_Report.xml) |
| 05 | `TC-254` | Thêm mới Token | :white_check_mark: **PASSED** | 3.020s | [`JUnit_Report.xml`](Reports/20261026_012901/09_ChiaSeDuLieu/20261026_012902/JUnit_Report.xml) |
| 06 | `TC-255` | Tìm kiếm Token | :white_check_mark: **PASSED** | 3.798s | [`JUnit_Report.xml`](Reports/20261026_012901/09_ChiaSeDuLieu/20261026_012902/JUnit_Report.xml) |
| 07 | `TC-256` | Gia hạn kết nối | :white_check_mark: **PASSED** | 3.285s | [`JUnit_Report.xml`](Reports/20261026_012901/09_ChiaSeDuLieu/20261026_012902/JUnit_Report.xml) |
| 08 | `TC-257` | Thu hồi Token kết nối | :white_check_mark: **PASSED** | 17.320s | [`JUnit_Report.xml`](Reports/20261026_012901/09_ChiaSeDuLieu/20261026_012902/JUnit_Report.xml) |
| 09 | `TC-258` | Mở khóa Token kết nối | :white_check_mark: **PASSED** | 17.263s | [`JUnit_Report.xml`](Reports/20261026_012901/09_ChiaSeDuLieu/20261026_012902/JUnit_Report.xml) |
| 10 | `TC-259` | Xoá Token kết nối | :white_check_mark: **PASSED** | 4.800s | [`JUnit_Report.xml`](Reports/20261026_012901/09_ChiaSeDuLieu/20261026_012902/JUnit_Report.xml) |
| **TỔNG** | **Suite 09** | **Chia Sẻ Dữ Liệu & Quản Trị Token** | **10/10 (100%)** | :white_check_mark: **PASSED** | **84.092s (~1m 24s)** | [`20261026_012902.html`](Reports/20261026_012901/09_ChiaSeDuLieu/20261026_012902/20261026_012902.html) |
