# HƯỚNG DẪN THIẾT LẬP VÀ VẬN HÀNH CI/CD — DMIT AUTOMATION

Tài liệu hướng dẫn cấu hình và vận hành hệ thống CI/CD cho dự án kiểm thử tự động **DMIT** (Quản lý Cơ sở dữ liệu ngành Công Thương), hỗ trợ lịch chạy tự động hàng ngày lúc **7:00 AM (Giờ Việt Nam)** cho toàn bộ **259 Test Cases** và khả năng kích hoạt thủ công theo yêu cầu (On-Demand).

---

## 1. Tổng Quan Kiến Trúc CI/CD

| Nền tảng | Phương thức cấu hình | Chế độ kích hoạt | Báo cáo & Thông báo |
|---|---|---|---|
| **GitHub Actions (Khuyến nghị)** | `.github/workflows/dmit-scheduled-e2e.yml` | **Tự động 7h sáng hàng ngày** (`cron: '0 0 * * *'`) & Thủ công (`workflow_dispatch`) | Katalon Report HTML, Artifacts Screenshots, Telegram Bot Notification |
| **Jenkins DevOps VNPT** | `Jenkinsfile` | **Tự động 6h30 sáng hàng ngày** (`cron('H 6 * * *')`) & Build with Parameters | Katalon Reports, JUnit XML, Telegram / Email Alert |
| **GitLab CI** | `.gitlab-ci.yml` | Scheduled Pipeline hoặc Push vào nhánh `main` | GitLab Test Reports, Artifacts HTML download |

---

## 2. Lịch Chạy Tự Động Định Kỳ (Scheduled Automation)

- **Thời gian chạy:** **06:30 AM** trên Jenkins (`cron('H 6 * * *')`) và **07:00 AM** trên GitHub Actions (`cron: '0 0 * * *'`).
- **Biểu thức Cron UTC:** `0 0 * * *` (00:00 UTC = 07:00 AM GMT+7).
- **Quy trình thực thi:**
  1. Tự động kéo mã nguồn mới nhất từ nhánh `main`.
  2. Khởi tạo môi trường (Java 17, Google Chrome Headless, ChromeDriver tự động cập nhật).
  3. Chạy Suite `Test Suites/10_All_DMIT_Tests` gồm toàn bộ **259 Test Cases**.
  4. Đóng gói kết quả: Báo cáo thực thi HTML, log chi tiết và ảnh chụp màn hình khi có case bị FAIL.
  5. Gửi thông báo tóm tắt tỷ lệ PASS / FAIL kèm link chi tiết vào kênh Telegram của đội ngũ.

---

## 3. Cấu Hình Biến Môi Trường & Secrets

| Tên Secret | Mô Tả | Giá Trị Ví Dụ |
|---|---|---|
| `DMIT_BASE_URL` | URL hệ thống kiểm thử DMIT | `https://doit-demo.vnptit.vn/dmit/auth` |
| `DMIT_USERNAME` | Tài khoản đăng nhập kiểm thử | `your_test_username` |
| `DMIT_PASSWORD` | Mật khẩu tài khoản kiểm thử | `your_test_password` |
| `KATALON_API_KEY` | API Key bản quyền Katalon Runtime Engine | `your_katalon_api_key` |
| `TELEGRAM_BOT_TOKEN` | Token Bot Telegram nhận thông báo | `your_telegram_bot_token` |
| `TELEGRAM_CHAT_ID` | ID nhóm Telegram nhận báo cáo | `your_telegram_chat_id` |

---

## 4. File Cấu Hình Mẫu Cho GitHub Actions

Tạo file `.github/workflows/dmit-scheduled-e2e.yml` trong dự án:

```yaml
name: DMIT - Scheduled & On-Demand E2E Automation (259 Test Cases)

on:
  schedule:
    # 07:00 AM Giờ Việt Nam (GMT+7) = 00:00 UTC
    - cron: '0 0 * * *'
  workflow_dispatch:
    inputs:
      test_suite:
        description: 'Test Suite cần chạy'
        required: true
        default: 'Test Suites/10_All_DMIT_Tests'
        type: choice
        options:
          - 'Test Suites/01_QuanLyChiTieu'
          - 'Test Suites/02_XacThucNguoiDung'
          - 'Test Suites/03_QuanTriHeThong'
          - 'Test Suites/04_DanhMucDungChung'
          - 'Test Suites/05_DanhMucNganhCongThuong'
          - 'Test Suites/06_QuyHoachCongThuong'
          - 'Test Suites/07_QuanTriDuLieu'
          - 'Test Suites/08_BaoCaoThongKe'
          - 'Test Suites/09_ChiaSeDuLieu'
          - 'Test Suites/10_All_DMIT_Tests'
          - 'Test Suites/11_PROBE_E2E_Flow'

jobs:
  run-dmit-automation:
    runs-on: ubuntu-latest
    container:
      image: katalonstudio/katalon:latest

    steps:
      - name: 1. Checkout Source Code
        uses: actions/checkout@v4

      - name: 2. Create Reports & Allure directories
        run: mkdir -p Reports Screenshots allure-results

      - name: 3. Execute Katalon Suite
        run: |
          katalon-execute.sh \
            -noSplash \
            -runMode=console \
            -projectPath="$GITHUB_WORKSPACE" \
            -retry=0 \
            -testSuitePath="${{ github.event.inputs.test_suite || 'Test Suites/10_All_DMIT_Tests' }}" \
            -browserType="Chrome (headless)" \
            -apiKey="${{ secrets.KATALON_API_KEY }}" \
            -g_BASE_URL="${{ secrets.DMIT_BASE_URL || 'https://doit-demo.vnptit.vn/dmit' }}" \
            -g_USERNAME="${{ secrets.DMIT_USERNAME }}" \
            -g_PASSWORD="${{ secrets.DMIT_PASSWORD }}"

      - name: 5. Archive Test Reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: dmit-katalon-reports
          path: Reports/
          retention-days: 30

      - name: 6. Send Telegram Notification
        if: always()
        run: |
          STATUS="${{ job.status }}"
          MSG="🚀 *BÁO CÁO KIỂM THỬ DMIT AUTOMATION (259 TEST CASES)*%0A- Trạng thái: *${STATUS}*%0A- Thời gian: $(date '+%d/%m/%Y %H:%M:%S')%0A- Suite: \`${{ github.event.inputs.test_suite || 'All_DMIT_Tests' }}\`%0A- Commit: \`${{ github.sha }}\`"
          curl -s -X POST "https://api.telegram.org/bot${{ secrets.TELEGRAM_BOT_TOKEN }}/sendMessage" \
            -d "chat_id=${{ secrets.TELEGRAM_CHAT_ID }}&text=${MSG}&parse_mode=Markdown"
```

---

## 5. Thực Thi Cục Bộ Trên Windows (Local Runner)

Dự án cung cấp bộ script PowerShell và Batch để chạy kiểm thử và kiểm tra môi trường nhanh chóng:

### 5.1. Kiểm tra môi trường hệ thống
```powershell
powershell -ExecutionPolicy Bypass -File tools/check_environment.ps1
# Hoặc nhấp đúp file: tools/check_environment.bat
```

### 5.2. Chạy Test Suite với runner tự động
```powershell
# Chọn Suite tương tác từ menu:
powershell -ExecutionPolicy Bypass -File run_tests_windows.ps1

# Hoặc chỉ định cụ thể Suite và Browser:
powershell -ExecutionPolicy Bypass -File run_tests_windows.ps1 -Suite "10_All_DMIT_Tests" -Browser "Chrome"
```

### 5.3. Xuất và xem báo cáo Allure HTML
```powershell
powershell -ExecutionPolicy Bypass -File tools/generate_allure_report.ps1
# Hoặc nhấp đúp file: tools/generate_allure_report.bat
```

---

## 6. Thực Thi Bằng Docker Container (Không Phụ Thuộc Môi Trường Host)

```bash
# 1. Sao chép và cấu hình biến môi trường
cp .env.example .env

# 2. Khởi chạy kiểm thử trong Docker Container
docker-compose up --build
```

---

## 7. Cấu Hình Jenkins & GitLab CI

### 7.1. Cấu hình chi tiết trên Jenkins (VNPT DevOps / Enterprise CI)

1. **Khởi tạo Jenkins Pipeline Job:**
   - Tạo mới một **Pipeline** Job trên Jenkins (hoặc Multibranch Pipeline).
   - Chọn **Pipeline script from SCM** -> Chọn **Git** -> Nhập Repository URL và cấu hình Credentials Git.
   - Nhánh chỉ định: `*/main`.
   - Script Path: `Jenkinsfile`.

2. **Cấu hình Credentials trên Jenkins (Manage Jenkins -> Credentials):**
   - **`DMIT_PASSWORD` (Bắt buộc - Secret text):** Mật khẩu đăng nhập tài khoản quản trị hệ thống DMIT (ví dụ `admin_nan`).
   - **`KATALON_API_KEY` (Khuyến nghị nếu chạy KRE - Secret text):** API Key bản quyền Katalon Runtime Engine.
   - **`DMIT_TELEGRAM_BOT_TOKEN` (Tùy chọn - Secret text):** Token Telegram Bot nhận thông báo tức thời.
   - **`DMIT_TELEGRAM_CHAT_ID` (Tùy chọn - Secret text):** ID nhóm chat Telegram nhận báo cáo.

3. **Các cơ chế chống lỗi vặt được tích hợp sẵn trong `Jenkinsfile`:**
   - **Tự động diệt Zombie Process:** Dọn sạch các tiến trình `chromedriver.exe`, `katalonc.exe` còn sót lại từ build trước để tránh xung đột cổng và khóa file.
   - **Chống treo lệnh (Non-Interactive Safe):** Không gọi lệnh nhắc lệnh `Read-Host` khi chạy trong Jenkins, tự động chọn Suite `10_All_DMIT_Tests` nếu tham số rỗng.
   - **Tối ưu Chrome Headless trên Windows Service:** Tự động kích hoạt cờ `--headless --window-size=1920,1080 --disable-gpu --no-sandbox --disable-dev-shm-usage` nhằm ngăn ngừa lỗi crash trình duyệt do phân mảnh bộ nhớ hoặc Session 0 Isolation.
   - **Tích hợp báo cáo JUnit & Allure:** Tự động tổng hợp file JUnit XML từ thư mục `Reports/` vào biểu đồ Test Result Trend của Jenkins, đồng thời lưu trữ toàn bộ Screenshots khi thất bại và Allure Report.
   - **Đa nền tảng (Adaptive Agent):** Tự động nhận diện Windows Agent hoặc Linux Agent (`isUnix()`) để thực thi script phù hợp.

### 7.2. Cấu hình GitLab CI
- **GitLab CI:** Cấu hình Pipeline trỏ tới [.gitlab-ci.yml](.gitlab-ci.yml) với 2 stages `test` và `report`.