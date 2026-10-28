#!/usr/bin/env python3
"""
Công cụ tra cứu nhanh XPath / Selector trực tiếp từ Keywords/odp/pages/*.groovy.
Quét trực tiếp mã nguồn Page Class (không cần file JSON scrape trung gian) nên
không bao giờ lệch với code thật (anti-drift by design).
Giúp AI chỉ lấy đúng danh sách selector của Page Class cần dùng (<300 tokens)
thay vì đọc toàn bộ file Groovy (DatasetPage ~60KB ~ 15.000 tokens).
Sử dụng:
    python3 tools/lookup_xpath.py DatasetPage
    python3 tools/lookup_xpath.py "field-title"
    python3 tools/lookup_xpath.py "TXT_DATASET_TITLE"
"""
import sys
import os
import re

PAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Keywords", "odp", "pages")

# Hằng XPath khai báo trong Page Class: protected static final String NAME = "..."
CONST_PATTERN = re.compile(
    r'(?:protected|public|private)\s+static\s+final\s+String\s+([A-Z][A-Z0-9_]+)\s*=\s*"([^"]*)"'
)

def scan_page_class(file_path):
    """Trích xuất (constant, xpath) từ 1 file Page Class."""
    selectors = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                m = CONST_PATTERN.search(line)
                if m:
                    name, xpath = m.group(1), m.group(2)
                    if xpath.startswith("/") or xpath.startswith("("):
                        selectors.append({"constant": name, "xpath": xpath})
    except Exception as e:
        print(f"Cảnh báo: không đọc được {file_path}: {e}")
    return selectors

def main():
    if len(sys.argv) < 2:
        print("Sử dụng: python3 tools/lookup_xpath.py <Tên PageClass hoặc Từ khóa>")
        sys.exit(1)

    query = sys.argv[1].strip()
    pages_dir = os.path.abspath(PAGES_DIR)

    if not os.path.isdir(pages_dir):
        print(f"Lỗi: Không tìm thấy thư mục {pages_dir}")
        sys.exit(1)

    # Load toàn bộ selectors theo Page Class
    data = {}
    for f in sorted(os.listdir(pages_dir)):
        if f.endswith(".groovy"):
            data[f[:-7]] = scan_page_class(os.path.join(pages_dir, f))

    # 1. Tìm theo tên Page Class (chính xác hoặc tương đối)
    matched_page = None
    for page_name in data.keys():
        if query.lower() == page_name.lower():
            matched_page = page_name
            break

    if matched_page:
        selectors = data[matched_page]
        print(f"=== {matched_page} ({len(selectors)} selectors) ===")
        for item in selectors:
            print(f"- {item['constant']}: {item['xpath']}")
        return

    # 2. Tìm theo từ khóa trong constant hoặc xpath
    found = []
    for page_name, selectors in data.items():
        for item in selectors:
            if query.lower() in item["constant"].lower() or query.lower() in item["xpath"].lower():
                found.append((page_name, item["constant"], item["xpath"]))

    if not found:
        print(f"Không tìm thấy selector nào khớp với: '{query}'")
        return

    print(f"=== Tìm thấy {len(found)} selector cho từ khóa '{query}' ===")
    for page, c, xp in found[:15]:
        print(f"[{page}] {c}: {xp}")

if __name__ == "__main__":
    main()
