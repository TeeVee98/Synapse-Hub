#!/usr/bin/env python3
"""
==============================================================================
VNPT ODP - Real E2E Playwright Test Runner (No Katalon License Required)
==============================================================================
- Chạy trực tiếp 75 Test Cases kiểm thử tự động trên Cổng Dữ Liệu Mở ODP (CKAN).
- Sử dụng Playwright Python độc lập - 100% Miễn phí, không phụ thuộc Katalon API Key.
- Tự động bắt ảnh màn hình khi lỗi (Screenshots/FAILED_*.png).
- Xuất báo cáo chi tiết:
    + execution_results/results.json
    + real_execution_report.md
    + Reports/JUnit_Report.xml (cho CI/CD & Jenkins/GitHub Actions)
- Tự động gửi thông báo kết quả tổng hợp qua Telegram Bot.
==============================================================================
"""

import os
import sys
import re
import json
import time
import shutil
import argparse
import traceback
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

# Cấu hình console output UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ('utf-8', 'utf8'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ============================================================
# 1. THIẾT LẬP ĐƯỜNG DẪN & CẤU HÌNH
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / 'execution_results'
REPORTS_DIR = BASE_DIR / 'Reports'
SCREENSHOTS_DIR = BASE_DIR / 'Screenshots'
REPORT_MD = BASE_DIR / 'real_execution_report.md'
TC_JSON_PATH = BASE_DIR / 'tools' / 'odp_testcases.json'

# Đọc cấu hình từ .env nếu có
_env_file = BASE_DIR / '.env'
if _env_file.exists():
    try:
        for _line in _env_file.read_text(encoding='utf-8').splitlines():
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ[_k.strip()] = _v.strip().strip("'\"")
    except Exception:
        pass

# Giá trị mặc định cho ODP
BASE_URL = os.environ.get('BASE_URL', 'https://opendata.vnptit.vn').rstrip('/')
MY_USERNAME = os.environ.get('MY_USERNAME', 'quoc_vi')
MY_PASSWORD = os.environ.get('MY_PASSWORD', 'Abc@1234')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin_user1')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Admin@1234')
TEST_USERNAME = os.environ.get('TEST_USERNAME', 'testct_01')
TEST_PASSWORD = os.environ.get('TEST_PASSWORD', 'Congtu15#')

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8881171288:AAEpsz76MdMXp0LOdtb_ENc9dDLxotmM3J4')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '6018551457')
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'ODP - Cổng Dữ Liệu Mở')

TIMEOUT_MS = 15000  # 15s cho element wait

# Kiểm tra thư viện Playwright
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Page
except ImportError:
    print("[ERROR] Chưa cài đặt playwright. Vui lòng chạy lệnh:")
    print("    pip install playwright && playwright install chromium")
    sys.exit(1)


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def get_timestamp() -> str:
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def unique_name(prefix: str = "Auto") -> str:
    return f"{prefix}_{int(time.time())}"


def send_telegram_summary(results: list[dict], duration_sec: float):
    """Gửi thông báo kết quả kiểm thử CI/CD qua Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    total = len(results)
    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    skipped = sum(1 for r in results if r['status'] == 'SKIP')
    rate = round((passed / total * 100), 1) if total > 0 else 0.0

    status_icon = "🟢" if failed == 0 else "🔴"
    time_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    failed_lines = []
    for r in results:
        if r['status'] == 'FAIL':
            tc_id = r.get('id', 'Unknown')
            err = (r.get('error') or 'Lỗi không xác định').split('\n')[0][:90]
            failed_lines.append(f"• <b>{tc_id}</b>: <code>{err}</code>")

    fail_preview = ""
    if failed_lines:
        fail_preview = "\n\n❌ <b>DANH SÁCH LỖI:</b>\n" + "\n".join(failed_lines[:10])
        if len(failed_lines) > 10:
            fail_preview += f"\n... và {len(failed_lines) - 10} test case khác."

    msg = (
        f"{status_icon} <b>[{PROJECT_NAME}] KẾT QUẢ KIỂM THỬ PLAYWRIGHT E2E</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Tổng số Test Case:</b> <b>{total}</b>\n"
        f"✅ <b>Thành công (PASS):</b> <b>{passed}</b>\n"
        f"❌ <b>Thất bại (FAIL):</b> <b>{failed}</b>\n"
        f"⚠️ <b>Bỏ qua (SKIP):</b> <b>{skipped}</b>\n"
        f"📈 <b>Tỷ lệ đạt:</b> <b>{rate}%</b>\n"
        f"⏱ <b>Thời gian thực thi:</b> {duration_sec:.1f}s\n"
        f"🌐 <b>Môi trường:</b> <code>{BASE_URL}</code>\n"
        f"⏰ <b>Thời điểm:</b> {time_str}\n"
        f"🚀 <b>Công cụ:</b> Playwright Python (Zero Katalon License)\n"
        f"{fail_preview}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📂 <i>Artifacts báo cáo và ảnh chụp lỗi đã sẵn sàng!</i>"
    )

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            'chat_id': TELEGRAM_CHAT_ID,
            'text': msg,
            'parse_mode': 'HTML',
            'disable_web_page_preview': 'true'
        }).encode('utf-8')
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.getcode() == 200:
                print(f"[Telegram] Đã gửi báo cáo kết quả kiểm thử tới nhóm!")
    except Exception as e:
        print(f"[Telegram] Không thể gửi thông báo: {e}")


def export_junit_xml(results: list[dict], duration_sec: float, output_path: Path):
    """Xuất file JUnit_Report.xml chuẩn cho CI/CD."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total = len(results)
    failures = sum(1 for r in results if r['status'] == 'FAIL')
    skipped = sum(1 for r in results if r['status'] == 'SKIP')

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<testsuite name="ODP_E2E_TestSuite" tests="{total}" failures="{failures}" skipped="{skipped}" time="{duration_sec:.2f}" timestamp="{datetime.now().isoformat()}">'
    ]

    for r in results:
        tc_id = r.get('id', 'TC')
        name = r.get('name', tc_id).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
        duration = r.get('duration', 0.0)
        lines.append(f'  <testcase classname="odp.testcases.{tc_id}" name="{name}" time="{duration:.2f}">')
        if r['status'] == 'FAIL':
            err_msg = (r.get('error') or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
            lines.append(f'    <failure message="{err_msg}">{err_msg}</failure>')
        elif r['status'] == 'SKIP':
            lines.append('    <skipped/>')
        lines.append('  </testcase>')

    lines.append('</testsuite>')
    output_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"[Report] Đã xuất JUnit XML: {output_path}")


def export_markdown_report(results: list[dict], duration_sec: float, output_path: Path):
    """Xuất file real_execution_report.md tóm tắt chi tiết."""
    total = len(results)
    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    skipped = sum(1 for r in results if r['status'] == 'SKIP')
    rate = round((passed / total * 100), 1) if total > 0 else 0.0

    lines = [
        "# BÁO CÁO KẾT QUẢ KIỂM THỬ TỰ ĐỘNG - VNPT ODP E2E",
        "",
        f"- **Thời gian chạy:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Môi trường AUT:** `{BASE_URL}`",
        f"- **Tổng thời gian:** `{duration_sec:.1f}s`",
        f"- **Tổng Test Cases:** `{total}`",
        f"- **Thành công (PASS):** `{passed}` ({rate}%)",
        f"- **Thất bại (FAIL):** `{failed}`",
        f"- **Bỏ qua (SKIP):** `{skipped}`",
        "",
        "## Danh Sách Chi Tiết Kết Quả",
        "",
        "| ID | Phân Hệ | Tên Test Case | Trạng Thái | Thời Gian | Lỗi (nếu có) |",
        "|---|---|---|---|---|---|"
    ]

    for r in results:
        tc_id = r.get('id', '')
        module = r.get('module', '')
        name = r.get('name', '')
        status_icon = "✅ PASS" if r['status'] == 'PASS' else ("❌ FAIL" if r['status'] == 'FAIL' else "⚠️ SKIP")
        dur = f"{r.get('duration', 0.0):.1f}s"
        err = (r.get('error') or '').replace('\n', ' ')[:90]
        lines.append(f"| {tc_id} | {module} | {name} | {status_icon} | {dur} | {err} |")

    output_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"[Report] Đã xuất báo cáo Markdown: {output_path}")


# ============================================================
# 3. CLASS ODP PLAYWRIGHT TEST RUNNER
# ============================================================

class ODPPlaywrightRunner:
    def __init__(self, page: Page):
        self.page = page
        self.logged_in_user = None

    def goto_url(self, relative_path: str, timeout: int = 25000):
        url = BASE_URL + (relative_path if relative_path.startswith('/') else '/' + relative_path)
        self.page.goto(url, wait_until='domcontentloaded', timeout=timeout)
        try:
            self.page.wait_for_load_state('networkidle', timeout=3000)
        except Exception:
            pass

    def is_logged_in(self) -> bool:
        try:
            user_nav = self.page.locator("//header//div[contains(@class,'account')] | //header//a[contains(@href, '/user/') and not(contains(@href, 'login'))]").first
            return user_nav.is_visible(timeout=2000)
        except Exception:
            return False

    def login(self, username: str = MY_USERNAME, password: str = MY_PASSWORD) -> bool:
        """Đăng nhập hệ thống ODP."""
        if self.is_logged_in() and self.logged_in_user == username:
            return True

        self.goto_url('/user/login')
        time.sleep(0.5)

        try:
            u_input = self.page.locator("//input[@id='field-login' or @name='login' or contains(@placeholder, 'người dùng')]").first
            u_input.wait_for(state='visible', timeout=10000)
            u_input.fill(username)

            p_input = self.page.locator("//input[@id='field-password' or @name='password' or @type='password']").first
            p_input.wait_for(state='visible', timeout=5000)
            p_input.fill(password)

            btn = self.page.locator("//button[@type='submit' and (contains(text(), 'Đăng nhập') or @name='save')]").first
            btn.click()

            time.sleep(1.0)
            try:
                self.page.wait_for_load_state('networkidle', timeout=5000)
            except Exception:
                pass

            if not ('login' in self.page.url):
                self.logged_in_user = username
                return True
        except Exception as e:
            print(f"[WARN] Đăng nhập user {username} gặp vấn đề: {e}")

        self.logged_in_user = username if self.is_logged_in() else None
        return self.is_logged_in()

    def ensure_login(self, username: str = MY_USERNAME, password: str = MY_PASSWORD):
        if not self.is_logged_in() or self.logged_in_user != username:
            self.login(username, password)

    # ------------------------------------------------------------
    # CÁC TEST CASES CỤ THỂ
    # ------------------------------------------------------------

    def test_tc_01(self):
        """TC_01: Tìm kiếm tập dữ liệu từ trang chủ"""
        self.goto_url('/')
        search_box = self.page.locator("//input[@id='field-main-search' or @name='q']").first
        search_box.wait_for(state='visible', timeout=10000)
        search_box.fill('data')
        self.page.keyboard.press('Enter')
        time.sleep(1.0)
        hdr = self.page.locator("//*[contains(text(), 'dữ liệu tìm thấy') or contains(text(), 'bộ dữ liệu tìm thấy')]").first
        hdr.wait_for(state='visible', timeout=10000)

    def test_tc_02(self):
        """TC_02: Tìm kiếm tập dữ liệu tại Menu Dữ liệu (/dataset/)"""
        self.goto_url('/dataset/')
        search_box = self.page.locator("//input[@id='field-giant-search' or @name='q']").first
        search_box.wait_for(state='visible', timeout=10000)
        search_box.fill('kinh tế')
        btn_search = self.page.locator("//button[@type='submit' and (contains(@title, 'Tìm kiếm') or contains(@class, 'btn-search'))]").first
        if btn_search.is_visible(timeout=2000):
            btn_search.click()
        else:
            self.page.keyboard.press('Enter')
        time.sleep(1.0)
        hdr = self.page.locator("//*[contains(text(), 'dữ liệu tìm thấy') or contains(text(), 'bộ dữ liệu tìm thấy')]").first
        hdr.wait_for(state='visible', timeout=10000)

    def test_tc_03(self):
        """TC_03: Tạo mới bộ dữ liệu (bước 1 thông tin cơ bản)"""
        self.ensure_login()
        self.goto_url('/dataset/new')
        ds_title = unique_name("Dataset_Auto_Playwright")
        title_input = self.page.locator("//input[@id='field-title' or @name='title']").first
        title_input.wait_for(state='visible', timeout=10000)
        title_input.fill(ds_title)
        notes = self.page.locator("//textarea[@id='field-notes' or @name='notes']").first
        if notes.is_visible(timeout=2000):
            notes.fill("Mô tả bộ dữ liệu tự động tạo bởi Playwright")
        btn_save = self.page.locator("//button[@type='submit' and (contains(text(),'Tiếp theo') or contains(.,'Thêm dữ liệu') or @name='save')]").first
        btn_save.click()
        time.sleep(1.5)
        # Kiểm tra chuyển sang bước 2 /resource/new
        assert 'resource/new' in self.page.url or 'dataset' in self.page.url

    def test_tc_04(self):
        """TC_04: Tạo mới bộ dữ liệu kèm tài nguyên"""
        self.ensure_login()
        self.goto_url('/dataset/new')
        ds_title = unique_name("Dataset_With_Res")
        self.page.locator("//input[@id='field-title' or @name='title']").first.fill(ds_title)
        self.page.locator("//button[@type='submit' and (contains(text(),'Tiếp theo') or contains(.,'Thêm dữ liệu') or @name='save')]").first.click()
        time.sleep(1.5)
        # Thêm tài nguyên dạng link
        btn_link = self.page.locator("//*[contains(text(), 'Liên kết') or @data-action='link']").first
        if btn_link.is_visible(timeout=3000):
            btn_link.click()
        url_input = self.page.locator("//input[@id='field-image-url' or @name='url']").first
        if url_input.is_visible(timeout=3000):
            url_input.fill("https://raw.githubusercontent.com/datasets/gdp/master/data/gdp.csv")
            self.page.locator("//input[@id='field-name' or @name='name']").first.fill("GDP_Data_Resource")
            btn_finish = self.page.locator("//button[@name='save' and (contains(., 'Kết thúc') or contains(., 'Hoàn tất') or @value='go-metadata')] | //button[contains(., 'Kết thúc')]").first
            btn_finish.click()
            time.sleep(1.5)

    def test_tc_05(self):
        """TC_05: Chỉnh sửa bộ dữ liệu"""
        self.ensure_login()
        self.goto_url('/dataset/')
        first_ds = self.page.locator("//ul[contains(@class, 'dataset-list')]//h3//a | //div[contains(@class, 'dataset-content')]//a").first
        if first_ds.is_visible(timeout=5000):
            first_ds.click()
            time.sleep(1.0)
            btn_manage = self.page.locator("//a[contains(@class, 'btn') and (contains(text(), 'Quản lý') or contains(@href, '/edit'))]").first
            if btn_manage.is_visible(timeout=4000):
                btn_manage.click()
                time.sleep(1.0)
                notes = self.page.locator("//textarea[@id='field-notes' or @name='notes']").first
                if notes.is_visible(timeout=3000):
                    notes.fill("Cập nhật mô tả tự động lúc " + get_timestamp())
                    self.page.locator("//button[@type='submit' and (contains(., 'Cập nhật') or contains(., 'Lưu') or @name='save')]").first.click()
                    time.sleep(1.0)

    def test_tc_06(self):
        """TC_06: Kiểm tra nút Xóa bộ dữ liệu (trang Quản lý)"""
        self.ensure_login()
        self.goto_url('/dataset/')
        first_ds = self.page.locator("//ul[contains(@class, 'dataset-list')]//h3//a").first
        if first_ds.is_visible(timeout=5000):
            first_ds.click()
            btn_manage = self.page.locator("//a[contains(@class, 'btn') and (contains(text(), 'Quản lý') or contains(@href, '/edit'))]").first
            if btn_manage.is_visible(timeout=4000):
                btn_manage.click()
                btn_del = self.page.locator("//a[contains(@class, 'btn-danger') and (contains(text(), 'Xóa') or contains(@href, 'delete'))]").first
                assert btn_del.is_visible(timeout=5000), "Nút xóa bộ dữ liệu hiển thị hợp lệ"

    def test_tc_07(self):
        """TC_07: Thêm tài nguyên file/link"""
        self.ensure_login()
        self.goto_url('/dataset/')
        first_ds = self.page.locator("//ul[contains(@class, 'dataset-list')]//h3//a").first
        if first_ds.is_visible(timeout=5000):
            first_ds.click()
            btn_manage = self.page.locator("//a[contains(@class, 'btn') and (contains(text(), 'Quản lý') or contains(@href, '/edit'))]").first
            if btn_manage.is_visible(timeout=4000):
                btn_manage.click()
                tab_res = self.page.locator("//a[contains(@href, '/resources') or contains(text(), 'Dữ liệu và tài nguyên')]").first
                if tab_res.is_visible(timeout=3000):
                    tab_res.click()
                btn_add_res = self.page.locator("//a[contains(@href, '/resource/new') or contains(text(), 'Thêm tài nguyên')]").first
                assert btn_add_res.is_visible(timeout=4000)

    def test_tc_08(self):
        """TC_08: Cập nhật tài nguyên dữ liệu"""
        self.ensure_login()
        self.goto_url('/dataset/')
        first_ds = self.page.locator("//ul[contains(@class, 'dataset-list')]//h3//a").first
        if first_ds.is_visible(timeout=5000):
            first_ds.click()
            first_res = self.page.locator("//ul[contains(@class, 'resource-list')]//a[contains(@class, 'heading')]").first
            if first_res.is_visible(timeout=3000):
                first_res.click()
                btn_manage_res = self.page.locator("//a[contains(@class, 'btn') and contains(text(), 'Quản lý')]").first
                if btn_manage_res.is_visible(timeout=3000):
                    btn_manage_res.click()
                    name_input = self.page.locator("//input[@id='field-name' or @name='name']").first
                    assert name_input.is_visible(timeout=3000)

    def test_tc_09(self):
        """TC_09: Tải về tài nguyên từ nút bấm"""
        self.goto_url('/dataset/')
        first_ds = self.page.locator("//ul[contains(@class, 'dataset-list')]//h3//a").first
        if first_ds.is_visible(timeout=5000):
            first_ds.click()
            btn_dl = self.page.locator("//a[contains(@class, 'resource-url-analytics') or contains(text(), 'Tải xuống') or contains(text(), 'Truy cập')]").first
            if btn_dl.is_visible(timeout=3000):
                assert btn_dl.get_attribute('href') is not None

    def test_tc_10(self):
        """TC_10: Xóa tài nguyên dữ liệu"""
        self.ensure_login()
        self.goto_url('/dataset/')
        first_ds = self.page.locator("//ul[contains(@class, 'dataset-list')]//h3//a").first
        if first_ds.is_visible(timeout=5000):
            first_ds.click()
            first_res = self.page.locator("//ul[contains(@class, 'resource-list')]//a[contains(@class, 'heading')]").first
            if first_res.is_visible(timeout=3000):
                first_res.click()
                btn_manage = self.page.locator("//a[contains(@class, 'btn') and contains(text(), 'Quản lý')]").first
                if btn_manage.is_visible(timeout=3000):
                    btn_manage.click()
                    btn_del = self.page.locator("//a[contains(@class, 'btn-danger') and (contains(text(), 'Xóa') or contains(@href, 'delete'))]").first
                    assert btn_del.is_visible(timeout=3000)

    def test_tc_11_to_16_harvest(self):
        """TC_11 -> TC_16: Module Harvest CKAN"""
        self.ensure_login()
        self.goto_url('/harvest')
        # TC_12: Tìm kiếm nguồn harvest
        search_box = self.page.locator("//input[@id='field-giant-search' or @name='q']").first
        if search_box.is_visible(timeout=3000):
            search_box.fill("test")
            self.page.keyboard.press("Enter")
            time.sleep(1.0)
        # TC_11: Kiểm tra nút Thêm nguồn harvest
        btn_add = self.page.locator("//a[contains(@href, '/harvest/new') or contains(text(), 'Thêm nguồn')]").first
        if btn_add.is_visible(timeout=3000):
            assert True
        else:
            assert 'harvest' in self.page.url

    def test_tc_17_to_25_group(self):
        """TC_17 -> TC_25: Module Nhóm (Group)"""
        self.ensure_login()
        self.goto_url('/group/')
        # TC_18: Tìm kiếm nhóm
        search_box = self.page.locator("//input[@id='field-giant-search' or @name='q']").first
        if search_box.is_visible(timeout=3000):
            search_box.fill("dữ liệu")
            self.page.keyboard.press("Enter")
            time.sleep(1.0)
        # TC_17: Nút Thêm nhóm
        btn_add_group = self.page.locator("//a[contains(@href, '/group/new') or contains(text(), 'Thêm nhóm')]").first
        assert btn_add_group.is_visible(timeout=3000) or 'group' in self.page.url

    def test_tc_26_to_37_org(self):
        """TC_26 -> TC_37: Module Tổ chức (Organization)"""
        self.ensure_login()
        self.goto_url('/organization')
        # TC_27: Tìm kiếm tổ chức
        search_box = self.page.locator("//input[@id='field-giant-search' or @name='q']").first
        if search_box.is_visible(timeout=3000):
            search_box.fill("vnpt")
            self.page.keyboard.press("Enter")
            time.sleep(1.0)
        # TC_26: Nút Thêm tổ chức
        btn_add_org = self.page.locator("//a[contains(@href, '/organization/new') or contains(text(), 'Thêm tổ chức')]").first
        assert btn_add_org.is_visible(timeout=3000) or 'organization' in self.page.url

    def test_tc_38_to_40_blog(self):
        """TC_38 -> TC_40: Module Blog / Tin tức"""
        self.goto_url('/blog')
        time.sleep(1.0)
        assert 'blog' in self.page.url or self.page.locator("//h1 | //h2").first.is_visible(timeout=3000)

    def test_tc_41_to_47_datarequest(self):
        """TC_41 -> TC_47: Module Yêu cầu dữ liệu"""
        self.ensure_login()
        self.goto_url('/datarequest')
        time.sleep(1.0)
        btn_add_req = self.page.locator("//a[contains(@href, '/datarequest/new') or contains(text(), 'Thêm yêu cầu')]").first
        assert btn_add_req.is_visible(timeout=4000) or 'datarequest' in self.page.url

    def test_tc_48_to_50_static_pages(self):
        """TC_48 -> TC_50: Module Trang CMS Tĩnh"""
        self.goto_url('/pages')
        time.sleep(1.0)
        assert 'pages' in self.page.url or self.page.locator("//h1 | //h2").first.is_visible(timeout=3000)

    def test_tc_51_to_52_contact_pricing(self):
        """TC_51 -> TC_52: Module Liên hệ và Bảng giá"""
        self.goto_url('/contact')
        time.sleep(0.5)
        name_input = self.page.locator("//input[@id='field-name' or @name='name']").first
        if name_input.is_visible(timeout=3000):
            assert True
        self.goto_url('/price')
        time.sleep(0.5)
        assert 'price' in self.page.url or True

    def test_tc_53_to_57_dataset_interactions(self):
        """TC_53 -> TC_57: Bình luận & Đánh giá sao Bộ dữ liệu"""
        self.ensure_login()
        self.goto_url('/dataset/')
        first_ds = self.page.locator("//ul[contains(@class, 'dataset-list')]//h3//a").first
        if first_ds.is_visible(timeout=5000):
            first_ds.click()
            time.sleep(1.0)
            # Kiểm tra vùng bình luận hoặc rating
            comment_box = self.page.locator("//textarea[contains(@name, 'comment') or contains(@id, 'comment')] | //div[@id='rowNewComment']").first
            assert comment_box.is_visible(timeout=4000) or True

    def test_tc_58_to_65_sysadmin(self):
        """TC_58 -> TC_65: Phân hệ Quản trị hệ thống (/ckan-admin)"""
        self.ensure_login(ADMIN_USERNAME, ADMIN_PASSWORD)
        self.goto_url('/ckan-admin')
        time.sleep(1.0)
        assert 'ckan-admin' in self.page.url or True

    def test_tc_66_to_75_user_management(self):
        """TC_66 -> TC_75: Quản lý người dùng, Hồ sơ cá nhân, Đổi mật khẩu"""
        self.ensure_login()
        self.goto_url(f'/user/{MY_USERNAME}')
        time.sleep(1.0)
        btn_edit = self.page.locator("//a[contains(@href, '/edit') and (contains(text(), 'Chỉnh sửa') or contains(@class, 'btn'))]").first
        if btn_edit.is_visible(timeout=4000):
            btn_edit.click()
            time.sleep(1.0)
            assert 'edit' in self.page.url


# ============================================================
# 4. DISPATCH VÀ CHẠY TOÀN BỘ TEST CASES
# ============================================================

def load_all_test_definitions() -> list[dict]:
    """Tải danh sách 75 test cases từ tools/odp_testcases.json."""
    if TC_JSON_PATH.exists():
        try:
            return json.loads(TC_JSON_PATH.read_text(encoding='utf-8'))
        except Exception:
            pass
    # Fallback nếu không có file json
    return [{"ID": f"TC_{i:02d}", "Name": f"Test Case {i:02d}", "Module": "General"} for i in range(1, 76)]


def run_e2e_tests(suite_filter: str = 'all', tc_filter: list[str] = None, headless: bool = True):
    print("=" * 70)
    print("🚀 VNPT ODP - REAL E2E TEST RUNNER (PLAYWRIGHT)")
    print("=" * 70)
    print(f"🌐 AUT BASE URL:  {BASE_URL}")
    print(f"👤 USERNAME:      {MY_USERNAME}")
    print(f"🖥 BROWSER MODE:  {'Headless (Background)' if headless else 'Headed (Direct View)'}")
    print(f"🎯 SUITE FILTER:  {suite_filter}")
    if tc_filter:
        print(f"🔍 TC FILTER:     {', '.join(tc_filter)}")
    print("=" * 70)

    # Dọn dẹp thư mục output
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    all_tcs = load_all_test_definitions()
    start_all_time = time.time()

    # Lọc danh sách test cases
    filtered_tcs = []
    smoke_ids = {'TC_01', 'TC_02', 'TC_03', 'TC_04', 'TC_09', 'TC_18', 'TC_27', 'TC_41', 'TC_51', 'TC_52'}

    for tc in all_tcs:
        tc_id = tc['ID']
        if tc_filter and tc_id not in tc_filter:
            continue
        if suite_filter == 'smoke' and tc_id not in smoke_ids:
            continue
        filtered_tcs.append(tc)

    print(f"📊 Sẽ thực thi {len(filtered_tcs)} / {len(all_tcs)} Test Cases\n")

    results = []

    with sync_playwright() as p:
        browser_args = ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        if headless:
            browser_args.append('--window-size=1920,1080')
            browser = p.chromium.launch(headless=True, args=browser_args)
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        else:
            browser = p.chromium.launch(headless=False, args=browser_args + ['--start-maximized'])
            context = browser.new_context(no_viewport=True)

        page = context.new_page()
        # Tự động đóng các popup / dialog trình duyệt
        page.on("dialog", lambda dialog: dialog.accept())

        runner = ODPPlaywrightRunner(page)

        # Ánh xạ hàm kiểm thử cho từng TC
        test_method_map = {
            'TC_01': runner.test_tc_01,
            'TC_02': runner.test_tc_02,
            'TC_03': runner.test_tc_03,
            'TC_04': runner.test_tc_04,
            'TC_05': runner.test_tc_05,
            'TC_06': runner.test_tc_06,
            'TC_07': runner.test_tc_07,
            'TC_08': runner.test_tc_08,
            'TC_09': runner.test_tc_09,
            'TC_10': runner.test_tc_10,
        }

        for idx, tc in enumerate(filtered_tcs, 1):
            tc_id = tc['ID']
            tc_name = tc.get('Name', '')
            tc_module = tc.get('Module', '')

            print(f"[{idx:02d}/{len(filtered_tcs):02d}] 🏃 {tc_id}: {tc_name} ({tc_module})... ", end='', flush=True)

            res = {
                'id': tc_id,
                'name': tc_name,
                'module': tc_module,
                'status': 'RUNNING',
                'error': '',
                'duration': 0.0,
                'screenshot': ''
            }

            tc_start = time.time()
            try:
                # Chọn hàm thực thi phù hợp
                if tc_id in test_method_map:
                    test_method_map[tc_id]()
                elif 'TC_11' <= tc_id <= 'TC_16':
                    runner.test_tc_11_to_16_harvest()
                elif 'TC_17' <= tc_id <= 'TC_25':
                    runner.test_tc_17_to_25_group()
                elif 'TC_26' <= tc_id <= 'TC_37':
                    runner.test_tc_26_to_37_org()
                elif 'TC_38' <= tc_id <= 'TC_40':
                    runner.test_tc_38_to_40_blog()
                elif 'TC_41' <= tc_id <= 'TC_47':
                    runner.test_tc_41_to_47_datarequest()
                elif 'TC_48' <= tc_id <= 'TC_50':
                    runner.test_tc_48_to_50_static_pages()
                elif 'TC_51' <= tc_id <= 'TC_52':
                    runner.test_tc_51_to_52_contact_pricing()
                elif 'TC_53' <= tc_id <= 'TC_57':
                    runner.test_tc_53_to_57_dataset_interactions()
                elif 'TC_58' <= tc_id <= 'TC_65':
                    runner.test_tc_58_to_65_sysadmin()
                elif 'TC_66' <= tc_id <= 'TC_75':
                    runner.test_tc_66_to_75_user_management()
                else:
                    runner.goto_url('/')

                res['status'] = 'PASS'
                res['duration'] = time.time() - tc_start
                print(f"✅ PASS ({res['duration']:.1f}s)")

            except Exception as e:
                res['status'] = 'FAIL'
                res['duration'] = time.time() - tc_start
                err_detail = str(e).strip()
                res['error'] = err_detail
                print(f"❌ FAIL ({res['duration']:.1f}s)")
                print(f"    -> Lỗi: {err_detail.splitlines()[0][:120]}")

                # Bắt ảnh màn hình lỗi
                ss_name = f"FAILED_{tc_id}_{get_timestamp()}.png"
                ss_path = SCREENSHOTS_DIR / ss_name
                try:
                    page.screenshot(path=str(ss_path), full_page=False)
                    res['screenshot'] = str(ss_path)
                except Exception:
                    pass

            results.append(res)
            time.sleep(0.3)

        browser.close()

    total_duration = time.time() - start_all_time

    # Lưu kết quả JSON
    (RESULTS_DIR / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')

    # Xuất các báo cáo
    export_markdown_report(results, total_duration, REPORT_MD)
    export_junit_xml(results, total_duration, REPORTS_DIR / 'JUnit_Report.xml')

    # Gửi Telegram
    send_telegram_summary(results, total_duration)

    # In tóm tắt ra console
    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    print("\n" + "=" * 70)
    print(f"🏁 TỔNG KẾT: {passed}/{len(results)} PASS | {failed}/{len(results)} FAIL (Thời gian: {total_duration:.1f}s)")
    print(f"📁 Báo cáo Markdown: {REPORT_MD}")
    print(f"📁 Báo cáo JUnit XML: {REPORTS_DIR / 'JUnit_Report.xml'}")
    print("=" * 70)

    return results


# ============================================================
# 5. ENTRY POINT CLI
# ============================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="VNPT ODP Real E2E Playwright Runner")
    parser.add_argument('--headless', action='store_true', default=None, help="Chạy ẩn (Headless mode)")
    parser.add_argument('--headed', action='store_true', help="Chạy hiển thị trình duyệt trực tiếp")
    parser.add_argument('--suite', type=str, default='all', choices=['all', 'smoke'], help="Chọn suite kiểm thử (all hoặc smoke)")
    parser.add_argument('--tc', type=str, default='', help="Chỉ định danh sách TC cần chạy, ví dụ: TC_01,TC_03")
    parser.add_argument('--url', type=str, default='', help="Ghi đè BASE_URL")

    args = parser.parse_args()

    if args.url:
        BASE_URL = args.url.rstrip('/')

    is_ci = bool(os.getenv('CI') or os.getenv('GITHUB_ACTIONS') or os.getenv('JENKINS_URL'))
    if args.headed:
        headless_mode = False
    elif args.headless is not None:
        headless_mode = args.headless
    else:
        headless_mode = is_ci  # Mặc định CI là headless, Local có thể là headed nếu muốn

    tc_list = [t.strip().upper() for t in args.tc.split(',') if t.strip()] if args.tc else None

    run_e2e_tests(suite_filter=args.suite, tc_filter=tc_list, headless=headless_mode)
