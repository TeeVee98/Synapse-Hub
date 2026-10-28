#!/usr/bin/env python3
"""
Enterprise QA: Fast XPath / Selector Lookup (lookup_xpath.py)
-------------------------------------------------------------
Công cụ tra cứu nhanh XPath / Selector từ file JSON của Page Classes.
Giúp AI chỉ lấy đúng danh sách selector của Page Class cần dùng (<300 tokens)
thay vì đọc toàn bộ file selectors hay quét lại live DOM.

Cơ chế nạp dữ liệu đa tầng (Multi-tier Resolution):
  1. CLI Flag: python tools/lookup_xpath.py <query> --file <path_to_json> (hoặc -f)
  2. Biến môi trường: XPATH_DATA_FILE hoặc SELECTORS_JSON hoặc LOCATORS_JSON
  3. Tự động tìm kiếm trong dự án: selectors.json, locators.json, scraped_xpaths.json...
  4. Dự phòng nội bộ Hub: archive/legacy_references/dmit_scraped_xpaths.json
"""

import sys
import json
import os
import argparse

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


def resolve_json_path(cli_file=None):
    """Xác định đường dẫn file JSON Selectors/XPath theo thứ tự ưu tiên."""
    # 1. CLI flag
    if cli_file:
        if os.path.exists(cli_file):
            return os.path.abspath(cli_file)
        else:
            print(f"⚠️  Cảnh báo: File chỉ định qua --file '{cli_file}' không tồn tại.")

    # 2. Biến môi trường
    env_file = os.environ.get("XPATH_DATA_FILE") or os.environ.get("SELECTORS_JSON") or os.environ.get("LOCATORS_JSON")
    if env_file and os.path.exists(env_file):
        return os.path.abspath(env_file)

    # 3. Tự động tìm kiếm trong thư mục làm việc hiện tại và các thư mục phổ biến
    script_dir = os.path.dirname(os.path.abspath(__file__))
    hub_root = os.path.abspath(os.path.join(script_dir, ".."))
    cwd = os.getcwd()

    search_dirs = [
        cwd,
        os.path.join(cwd, "references"),
        os.path.join(cwd, "data"),
        os.path.join(cwd, "tools"),
        os.path.join(cwd, "docs"),
        script_dir
    ]

    candidate_names = [
        "selectors.json",
        "scraped_xpaths.json",
        "locators.json",
        "Enterprise_scraped_xpaths.json",
        "page_selectors.json",
        "elements.json"
    ]

    for d in search_dirs:
        for name in candidate_names:
            candidate = os.path.join(d, name)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)

    # 4. Dự phòng Hub Archive
    for legacy_name in ["Enterprise_scraped_xpaths.json", "dmit_scraped_xpaths.json", "batch01_scraped_xpaths.json"]:
        legacy_file = os.path.join(hub_root, "archive", "legacy_references", legacy_name)
        if os.path.isfile(legacy_file):
            return os.path.abspath(legacy_file)

    return None


def normalize_selector_data(raw_data):
    """Chuẩn hóa dữ liệu Selector từ dict of PageClasses hoặc list of selectors."""
    if isinstance(raw_data, dict):
        return raw_data
    elif isinstance(raw_data, list):
        grouped = {}
        for item in raw_data:
            page = item.get("page") or item.get("page_class") or "GLOBAL"
            if page not in grouped:
                grouped[page] = []
            grouped[page].append(item)
        return grouped
    return {}


def main():
    parser = argparse.ArgumentParser(description="Tra cứu nhanh Selector / XPath từ file JSON của dự án")
    parser.add_argument("query", help="Tên PageClass hoặc từ khóa định danh selector (ví dụ: TargetPlanPage, TXT_CODE)")
    parser.add_argument("-f", "--file", dest="file", help="Đường dẫn file JSON chứa danh sách selector/xpaths")
    args = parser.parse_args()

    json_path = resolve_json_path(args.file)

    if not json_path:
        print("❌ Lỗi: Không tìm thấy file JSON dữ liệu Selector / XPath.")
        print("\n👉 Hướng dẫn cấu hình nạp dữ liệu cho target project:")
        print("  1. Dùng CLI flag: python tools/lookup_xpath.py <query> --file <đường_dẫn_tới_selectors.json>")
        print("  2. Đặt biến môi trường: export XPATH_DATA_FILE='path/to/selectors.json' (hoặc set XPATH_DATA_FILE=...)")
        print("  3. Đặt file 'selectors.json' vào thư mục gốc dự án hoặc khai báo trong PROJECT_AI_GUIDE.md")
        sys.exit(1)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"❌ Lỗi khi đọc file '{json_path}': {e}")
        sys.exit(1)

    data = normalize_selector_data(raw_data)
    query = args.query.strip()

    # 1. Tìm theo tên Page Class (chính xác hoặc tương đối)
    matched_page = None
    for page_name in data.keys():
        if query.lower() == page_name.lower():
            matched_page = page_name
            break

    if matched_page:
        selectors = data[matched_page]
        source_label = os.path.relpath(json_path, os.getcwd()) if os.path.exists(json_path) else json_path
        print(f"=== {matched_page} ({len(selectors)} selectors) [Nguồn: {source_label}] ===")
        for item in selectors:
            c = item.get("constant") or item.get("name") or "SELECTOR"
            tag = item.get("tag") or "element"
            xp = item.get("xpath") or item.get("selector") or item.get("css") or ""
            print(f"- {c} ({tag}): {xp}")
        return

    # 2. Tìm theo từ khóa trong constant hoặc xpath
    found = []
    for page_name, selectors in data.items():
        if isinstance(selectors, list):
            for item in selectors:
                c = item.get("constant") or item.get("name") or ""
                xp = item.get("xpath") or item.get("selector") or item.get("css") or ""
                tag = item.get("tag") or "element"
                if query.lower() in c.lower() or query.lower() in xp.lower():
                    found.append((page_name, c, tag, xp))
        elif isinstance(selectors, dict):
            for c, xp in selectors.items():
                if query.lower() in c.lower() or query.lower() in str(xp).lower():
                    found.append((page_name, c, "element", str(xp)))

    if not found:
        print(f"Không tìm thấy selector nào khớp với: '{query}' trong file '{os.path.basename(json_path)}'")
        return

    source_label = os.path.relpath(json_path, os.getcwd()) if os.path.exists(json_path) else json_path
    print(f"=== Tìm thấy {len(found)} selector cho từ khóa '{query}' [Nguồn: {source_label}] ===")
    for page, c, tag, xp in found[:15]:
        print(f"[{page}] {c} ({tag}): {xp}")


if __name__ == "__main__":
    main()
