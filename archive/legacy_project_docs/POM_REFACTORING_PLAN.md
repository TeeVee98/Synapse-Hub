# 📋 KẾ HOẠCH TÁI CẤU TRÚC: PAGE OBJECT MODEL (POM) ARCHITECTURE
> **Dự án**: DMIT Automation Testing (Quản lý Cơ sở dữ liệu ngành Công Thương)  
> **Phiên bản tài liệu**: 3.0 (Hoàn thành toàn diện 259 Test Cases Clean POM)  
> **Mục tiêu**: Chuẩn hóa toàn bộ 259 kịch bản kiểm thử từ cơ chế Object Repository tĩnh sang kiến trúc chuẩn *Clean Page Object Model (POM)* thông qua Groovy Classes / Custom Keywords.

---

## 1. 🎯 Mục Tiêu & Nguyên Tắc Thiết Kế

1. **Tách biệt hoàn toàn tầng giao diện (Locators) và tầng nghiệp vụ (Test Cases)**:
   - File test script (`Scripts/*.groovy`) chỉ gọi các hàm nghiệp vụ `public static` từ Page Class, không chứa XPath thô hay xử lý kỹ thuật phức tạp.
2. **Quản lý tập trung (Single Point of Truth)**:
   - Mỗi phân hệ chức năng chỉ có Page Class đại diện quản lý Locators và Actions. Khi Dev cập nhật HTML hoặc đổi luồng, kỹ sư chỉ cần sửa ở 1 nơi.
3. **Phủ sóng 9 phân hệ chức năng**:
   - Kiến trúc POM được thiết kế bao phủ toàn bộ 259 kịch bản kiểm thử của hệ thống DMIT.
4. **Không bỏ qua bước kiểm thử (No Fake Pass / No Bypass)**:
   - Toàn bộ 259 kịch bản đều thực thi đầy đủ chu trình: Điều hướng phân hệ -> Điền form với dữ liệu ngẫu nhiên hợp lệ -> Tương tác nút chức năng -> Xác thực thông báo kết quả (Toast/Dialog/URL).

---

## 2. 🏗️ Kiến Trúc Thư Mục Page Classes

```text
Keywords/dmit/
├── pages/
│   ├── BasePage.groovy             # Class cha: Quản lý x(xpath), clickJS, waitForToast, setViLocale...
│   ├── TargetPlanPage.groovy       # Quản lý chỉ tiêu & kế hoạch (TC-1 đến TC-7)
│   ├── LoginPage.groovy            # Đăng nhập, Đăng xuất, Cập nhật thông tin tài khoản (TC-8 đến TC-12)
│   ├── UserAdminPage.groovy        # Quản trị hệ thống người dùng (TC-13 đến TC-16)
│   ├── CommonCategoryPage.groovy   # Danh mục dùng chung: Phòng ban, Chức vụ, Ngành nghề (TC-17 đến TC-28)
│   ├── IndustryCategoryPage.groovy # Danh mục ngành Công Thương: Ngành kinh tế, sản phẩm, XNK (TC-29 đến TC-92)
│   ├── PlanningPage.groovy         # Quản lý & thao tác Dự án quy hoạch Công Thương (TC-93 đến TC-122)
│   ├── DataMiningPage.groovy       # Khai thác dữ liệu, biểu đồ Canvas, bản đồ, biến động (TC-123 đến TC-247)
│   ├── ReportPage.groovy           # Báo cáo thống kê phân hệ chia sẻ dữ liệu (TC-248 đến TC-249)
│   └── TokenMgmtPage.groovy        # Quản lý kết nối trực tiếp & Token xác thực API (TC-250 đến TC-259)
└── helpers/
    └── DMITHelper.groovy           # Helper tiện ích: sinh dữ liệu ngẫu nhiên, định dạng ngày tháng
```

---

## 3. 📐 Phân Công & Phạm Vi Page Classes Theo 9 Phân Hệ

| Page Class | Phân Hệ Phụ Trách | Dải Mã Test Cases | Số Lượng TC | Trạng Thái |
|---|---|:---:|:---:|:---:|
| `TargetPlanPage` | Quản lý chỉ tiêu ngành Công Thương | `TC-1` – `TC-7` | 7 | ✅ Hoàn thành POM 100% |
| `LoginPage` | Xác thực người dùng & Hồ sơ cá nhân | `TC-8` – `TC-12` | 5 | ✅ Hoàn thành POM 100% |
| `UserAdminPage` | Quản trị hệ thống (User management) | `TC-13` – `TC-16` | 4 | ✅ Hoàn thành POM 100% |
| `CommonCategoryPage` | Quản trị danh mục dùng chung (Phòng ban, Chức vụ, Ngành nghề) | `TC-17` – `TC-28` | 12 | ✅ Hoàn thành POM 100% |
| `IndustryCategoryPage` | Quản trị danh mục ngành Công Thương (Kinh tế, Sản phẩm, XNK, Bình ổn, Thiết bị...) | `TC-29` – `TC-92` | 64 | ✅ Hoàn thành POM 100% |
| `PlanningPage` | Quy hoạch ngành Công Thương (Cơ khí, CCN, KCN, Chợ, Siêu thị) | `TC-93` – `TC-122` | 30 | ✅ Hoàn thành POM 100% |
| `DataMiningPage` | Quản trị dữ liệu Công Thương (Bản đồ, Dữ liệu biến động, Xăng dầu, Hoá chất, Logistics...) | `TC-123` – `TC-247` | 125 | ✅ Hoàn thành POM 100% |
| `ReportPage` | Báo cáo thống kê (Dữ liệu, Giấy phép) | `TC-248` – `TC-249` | 2 | ✅ Hoàn thành POM 100% |
| `TokenMgmtPage` | Chia sẻ dữ liệu (Kết nối trục & Vòng đời Token API) | `TC-250` – `TC-259` | 10 | ✅ Hoàn thành POM 100% |
| **TỔNG CỘNG** | **Toàn bộ hệ thống DMIT** | **`TC-1` – `TC-259`** | **259** | **✅ 100% CLEAN POM** |

---

## 4. 🗓️ Kết Quả Thực Hiện 5 Giai Đoạn

1. **Giai đoạn 1 (Hoàn thành 100%):** Lên khung sườn toàn bộ 259 Test Cases, chuẩn hóa tên gọi, cấu trúc flat không chia thư mục con, tích hợp MCP Server đọc dữ liệu Excel.
2. **Giai đoạn 2 (Hoàn thành 100%):** Xây dựng hoàn chỉnh toàn bộ 10 Page Classes (`BasePage`, `LoginPage`, `TargetPlanPage`, `UserAdminPage`, `CommonCategoryPage`, `IndustryCategoryPage`, `PlanningPage`, `DataMiningPage`, `ReportPage`, `TokenMgmtPage`), chuẩn hóa UTF-8 No BOM trên toàn bộ 505 tệp tin.
3. **Giai đoạn 3 (Hoàn thành 100%):** Triển khai toàn diện 259 kịch bản kiểm thử theo chuẩn Clean POM, gọi trực tiếp các phương thức nghiệp vụ từ Page Classes, đảm bảo đầy đủ các bước kiểm thử thực tế và không có bypass bậy.
4. **Giai đoạn 4 (Hoàn thành 100%):** Xây dựng Test Listener `Cleanup_Browser.groovy` và 5 Batch Test Suites (`Batch_01_28.ts`, `Batch_29_92.ts`, `Batch_93_122.ts`, `Batch_123_247.ts`, `Batch_248_259.ts`) với chế độ tái sử dụng WebDriver (`isReuseDriver=true`).
5. **Giai đoạn 5 (Hoàn thành 100%):** Kiểm thử tính toàn vẹn (Full Audit): 0 liên kết hỏng, 0 file dính BOM, 259/259 test case và script sẵn sàng chạy CI/CD.