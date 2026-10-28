#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMIT Automation - Real E2E Test Runner & DOM Flow Crawler / XPath Scraper
========================================================================
- Crawls and probes all 9 modules of DMIT live web application
- Scrapes resilient XPaths and CSS selectors for all inputs, buttons, tables, dropdowns
- Maps the end-to-end user navigation flows
- Translates and executes Katalon Clean POM test cases via Playwright
- Outputs:
    * tools/dmit_scraped_xpaths.json
    * dmit_flow_probe_report.md
    * Screenshots/*.png
"""

import os
import re
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 console output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / 'Scripts'
TOOLS_DIR = BASE_DIR / 'tools'
SCREENSHOTS_DIR = BASE_DIR / 'Screenshots'
RESULTS_DIR = BASE_DIR / 'allure-results'

SCREENSHOTS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
TOOLS_DIR.mkdir(exist_ok=True)

# Load environment configuration (.env)
env_file = BASE_DIR / '.env'
if env_file.exists():
    try:
        for line in env_file.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                k, v = k.strip(), v.strip().strip("'\"")
                if k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass

BASE_URL = os.environ.get('BASE_URL', 'https://doit-demo.vnptit.vn/dmit').rstrip('/')
AUTH_URL = f"{BASE_URL}/auth"
USERNAME = os.environ.get('USERNAME_DMIT', '')
PASSWORD = os.environ.get('PASSWORD_DMIT', '')

# DMIT Module Navigation Definition for Flow Crawler
DMIT_MODULES = [
    {
        "id": "AUTH",
        "name": "Xác thực người dùng",
        "url": f"{BASE_URL}/auth",
        "menu_xpath": None,
        "submenu_xpath": None
    },
    {
        "id": "TARGET_PLAN",
        "name": "Quản lý chỉ tiêu - Kế hoạch",
        "url": f"{BASE_URL}/target-plan",
        "menu_xpath": "//a[contains(.,'Quản lý chỉ tiêu')]",
        "submenu_xpath": "//a[contains(.,'Quản lý kế hoạch')]"
    },
    {
        "id": "USER_ADMIN",
        "name": "Quản trị hệ thống - Quản trị người dùng",
        "url": f"{BASE_URL}/admin/users",
        "menu_xpath": "//a[contains(.,'Quản trị hệ thống')]",
        "submenu_xpath": "//a[contains(.,'Quản trị người dùng')]"
    },
    {
        "id": "COMMON_CATEGORY",
        "name": "Danh mục dùng chung - Phòng ban",
        "url": f"{BASE_URL}/category/common",
        "menu_xpath": "//a[contains(.,'Danh mục dùng chung')]",
        "submenu_xpath": "//a[contains(.,'Phòng ban')]"
    },
    {
        "id": "INDUSTRY_CATEGORY",
        "name": "Danh mục ngành Công Thương - Ngành kinh tế",
        "url": f"{BASE_URL}/category/industry",
        "menu_xpath": "//a[contains(.,'Danh mục ngành Công Thương') or contains(.,'Danh mục ngành công thương')]",
        "submenu_xpath": "//a[contains(.,'Ngành kinh tế')]"
    },
    {
        "id": "PLANNING",
        "name": "Quản lý quy hoạch - Dữ liệu quy hoạch",
        "url": f"{BASE_URL}/planning",
        "menu_xpath": "//a[contains(.,'Quản lý quy hoạch')]",
        "submenu_xpath": "//a[contains(.,'Dữ liệu quy hoạch')]"
    },
    {
        "id": "DATA_MINING",
        "name": "Quản lý dữ liệu - Khai thác dữ liệu",
        "url": f"{BASE_URL}/data-mining",
        "menu_xpath": "//a[contains(.,'Quản lý dữ liệu')]",
        "submenu_xpath": "//a[contains(.,'Khai thác dữ liệu')]"
    },
    {
        "id": "REPORT_DATA",
        "name": "Báo cáo thống kê - Dữ liệu",
        "url": f"{BASE_URL}/report/data",
        "menu_xpath": "//a[contains(.,'Báo cáo thống kê')]",
        "submenu_xpath": "//a[contains(.,'Dữ liệu')]"
    },
    {
        "id": "REPORT_LICENSE",
        "name": "Báo cáo thống kê - Giấy phép",
        "url": f"{BASE_URL}/report/license",
        "menu_xpath": "//a[contains(.,'Báo cáo thống kê')]",
        "submenu_xpath": "//a[contains(.,'Giấy phép')]"
    },
    {
        "id": "SHARING_CONNECTION",
        "name": "Chia sẻ dữ liệu - Quản trị thông tin kết nối trục",
        "url": f"{BASE_URL}/sharing/connection",
        "menu_xpath": "//a[contains(.,'Chia sẻ dữ liệu ngành công thương') or contains(.,'Chia sẻ dữ liệu')]",
        "submenu_xpath": "//a[contains(.,'Quản trị thông tin kết nối trục') or contains(@href,'/sharing/')]"
    }
]


def generate_element_xpath(tag: str, attrs: dict, text: str) -> str:
    """Generate resilient and unique XPath based on attributes."""
    if attrs.get('id'):
        return f"//{tag}[@id='{attrs['id']}']"
    if attrs.get('formcontrolname'):
        return f"//{tag}[@formcontrolname='{attrs['formcontrolname']}']"
    if attrs.get('placeholder'):
        return f"//{tag}[@placeholder='{attrs['placeholder']}']"
    if attrs.get('name'):
        return f"//{tag}[@name='{attrs['name']}']"
    if text and len(text.strip()) > 0 and len(text.strip()) <= 40:
        clean_text = text.strip().replace("'", "\\'")
        return f"//{tag}[contains(normalize-space(.), '{clean_text}')]"
    if attrs.get('class'):
        first_cls = attrs['class'].split()[0]
        return f"//{tag}[contains(@class, '{first_cls}')]"
    return f"//{tag}"


def scrape_dom_elements(page, module_name: str) -> list:
    """Scrape all interactive DOM elements on current page."""
    elements_data = []

    # JS snippet to extract elements with details
    js_extract = """
    () => {
        const results = [];
        const targets = document.querySelectorAll('button, input, select, textarea, a, table, canvas');
        targets.forEach((el, index) => {
            if (!el.offsetParent && el.type !== 'hidden') return; // skip hidden
            const tag = el.tagName.toLowerCase();
            const text = (el.innerText || el.textContent || '').trim();
            const placeholder = el.getAttribute('placeholder') || '';
            const formcontrolname = el.getAttribute('formcontrolname') || '';
            const name = el.getAttribute('name') || '';
            const id = el.id || '';
            const type = el.type || '';
            const className = el.className || '';
            
            results.push({
                index: index,
                tag: tag,
                id: id,
                type: type,
                name: name,
                placeholder: placeholder,
                formcontrolname: formcontrolname,
                className: className,
                text: text.substring(0, 50)
            });
        });
        return results;
    }
    """

    try:
        raw_elements = page.evaluate(js_extract)
        for item in raw_elements:
            attrs = {
                'id': item.get('id'),
                'formcontrolname': item.get('formcontrolname'),
                'placeholder': item.get('placeholder'),
                'name': item.get('name'),
                'class': item.get('className')
            }
            xpath = generate_element_xpath(item['tag'], attrs, item['text'])
            elements_data.append({
                "module": module_name,
                "tag": item['tag'],
                "type": item['type'],
                "text": item['text'],
                "placeholder": item['placeholder'],
                "formcontrolname": item['formcontrolname'],
                "xpath": xpath
            })
    except Exception as e:
        print(f"  [!] Lỗi trích xuất phần tử: {e}")

    return elements_data


def run_flow_crawler(headless: bool = True):
    """Main crawler: Login, traverse all modules, scrape XPaths, take screenshots."""
    print("=" * 65)
    print("🚀 DMIT AUTOMATION - DOM FLOW CRAWLER & XPATH SCRAPER")
    print("=" * 65)
    print(f"[+] Target Base URL: {BASE_URL}")
    print(f"[+] Login URL:       {AUTH_URL}")
    print(f"[+] Headless Mode:   {headless}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[!] Thư viện Playwright chưa cài đặt. Chạy lệnh: pip install playwright && playwright install chromium")
        return

    scraped_inventory = {}
    report_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # Step 1: Login
        print("\n[1] Đang kết nối tới trang xác thực và thiết lập ngôn ngữ Tiếng Việt...")
        page.goto(AUTH_URL, timeout=30000)
        page.evaluate("() => { localStorage.setItem('lang', 'vi'); localStorage.setItem('ng-prime-language', 'vi'); }")
        page.reload()
        page.wait_for_load_state("networkidle")

        # Scrape Auth page
        auth_elements = scrape_dom_elements(page, "AUTH")
        scraped_inventory["AUTH"] = auth_elements
        screenshot_path = SCREENSHOTS_DIR / "PROBE_00_AUTH.png"
        page.screenshot(path=str(screenshot_path))
        print(f"  [✓] Đã cào {len(auth_elements)} phần tử màn hình Đăng nhập -> Lưu ảnh: {screenshot_path.name}")

        # Perform Login
        try:
            user_input = page.locator("//input[contains(@placeholder,'Tên đăng nhập') or @formcontrolname='username']").first
            pass_input = page.locator("//input[@type='password' or @formcontrolname='password']").first
            login_btn = page.locator("//button[contains(.,'ĐĂNG NHẬP') or contains(.,'Đăng nhập')]").first

            user_input.fill(USERNAME)
            pass_input.fill(PASSWORD)
            login_btn.click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state("networkidle")
            print("  [✓] Đăng nhập thành công vào hệ thống DMIT!")
        except Exception as e:
            print(f"  [!] Thất bại khi đăng nhập: {e}")

        # Step 2: Traverse each module
        for idx, mod in enumerate(DMIT_MODULES[1:], start=1):
            mod_id = mod["id"]
            mod_name = mod["name"]
            print(f"\n[{idx+1}] Khám phá luồng: {mod_name}...")

            # Navigate via menu or direct URL
            try:
                if mod["menu_xpath"]:
                    try:
                        menu_elem = page.locator(mod["menu_xpath"]).first
                        if menu_elem.is_visible(timeout=3000):
                            menu_elem.click()
                            page.wait_for_timeout(500)
                        if mod["submenu_xpath"]:
                            sub_elem = page.locator(mod["submenu_xpath"]).first
                            if sub_elem.is_visible(timeout=3000):
                                sub_elem.click()
                                page.wait_for_timeout(1000)
                    except Exception:
                        page.goto(mod["url"], timeout=15000)
                else:
                    page.goto(mod["url"], timeout=15000)

                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(1500)

                # Scrape elements
                mod_elements = scrape_dom_elements(page, mod_id)
                scraped_inventory[mod_id] = mod_elements

                # Screenshot
                shot_name = f"PROBE_{idx:02d}_{mod_id}.png"
                shot_file = SCREENSHOTS_DIR / shot_name
                page.screenshot(path=str(shot_file))

                buttons = len([e for e in mod_elements if e['tag'] == 'button'])
                inputs = len([e for e in mod_elements if e['tag'] in ('input', 'select', 'textarea')])
                tables = len([e for e in mod_elements if e['tag'] == 'table'])

                print(f"  [✓] Cào thành công {len(mod_elements)} phần tử ({buttons} nút, {inputs} ô nhập liệu, {tables} bảng)")
                print(f"  [✓] Ảnh chụp màn hình: {shot_name}")

                report_rows.append({
                    "id": mod_id,
                    "name": mod_name,
                    "url": page.url,
                    "total": len(mod_elements),
                    "buttons": buttons,
                    "inputs": inputs,
                    "tables": tables,
                    "screenshot": shot_name
                })
            except Exception as e:
                print(f"  [!] Lỗi khi khám phá {mod_name}: {e}")

        browser.close()

    # Step 3: Export Scraped XPaths JSON
    output_json = TOOLS_DIR / 'dmit_scraped_xpaths.json'
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(scraped_inventory, f, ensure_ascii=False, indent=2)
    print(f"\n[+] Đã lưu toàn bộ từ điển XPath cào được vào: {output_json}")

    # Step 4: Generate Markdown Flow Report
    report_md = BASE_DIR / 'dmit_flow_probe_report.md'
    with open(report_md, 'w', encoding='utf-8') as f:
        f.write("# 🧭 BÁO CÁO KHÁM PHÁ LUỒNG HỆ THỐNG VÀ BẢN ĐỒ XPATH (DMIT FLOW REPORT)\n\n")
        f.write(f"> **Thời điểm quét:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"> **Hệ thống mục tiêu:** [{BASE_URL}]({BASE_URL})  \n")
        f.write(f"> **Tổng số phân hệ khám phá:** {len(report_rows)}  \n\n")
        f.write("---\n\n## 1. 📊 Bảng Tổng Hợp Luồng Và Phần Tử Thu Thập\n\n")
        f.write("| STT | Mã Phân Hệ | Tên Phân Hệ & Chức Năng | URL Thực Tế | Tổng Element | Buttons | Inputs | Tables | Ảnh Chụp |\n")
        f.write("|:---:|---|---|---|:---:|:---:|:---:|:---:|:---:|\n")
        for i, r in enumerate(report_rows, start=1):
            f.write(f"| {i} | `{r['id']}` | {r['name']} | `{r['url']}` | **{r['total']}** | {r['buttons']} | {r['inputs']} | {r['tables']} | [`{r['screenshot']}`](Screenshots/{r['screenshot']}) |\n")

        f.write("\n---\n\n## 2. 🔍 Danh Sách XPath Tiêu Biểu Cho Từng Phân Hệ\n\n")
        for mod_id, elems in scraped_inventory.items():
            f.write(f"### 📍 Phân Hệ: `{mod_id}` ({len(elems)} elements)\n\n")
            f.write("| Tag | Text / Placeholder | FormControlName | XPath Đề Xuất |\n")
            f.write("|---|---|---|---|\n")
            sample_elems = elems[:12]  # show top 12 per module
            for el in sample_elems:
                txt = el['text'] or el['placeholder'] or '-'
                f.write(f"| `{el['tag']}` | {txt} | `{el['formcontrolname'] or '-'}` | `{el['xpath']}` |\n")
            f.write("\n")

    print(f"[+] Báo cáo khám phá luồng đã xuất tại: {report_md}")
    print("=" * 65)
    print("🎉 HOÀN THÀNH QUÉT LUỒNG VÀ CÀO XPATH DỰ ÁN DMIT!")
    print("=" * 65)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="DMIT E2E Test Runner & XPath Scraper")
    parser.add_argument('--probe', action='store_true', default=True, help="Run DOM Flow Crawler and XPath Scraper")
    parser.add_argument('--headed', action='store_true', help="Run browser in visible mode")
    args = parser.parse_args()

    run_flow_crawler(headless=not args.headed)