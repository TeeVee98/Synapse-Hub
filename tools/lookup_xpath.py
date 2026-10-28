#!/usr/bin/env python3
"""
Công cụ tra cứu nhanh XPath / Selector từ tools/Enterprise_scraped_xpaths.json.
Giúp AI chỉ lấy đúng danh sách selector của Page Class cần dùng (<300 tokens)
thay vì đọc toàn bộ file 169 KB (~43.000 tokens).
Sử dụng:
    python3 tools/lookup_xpath.py TargetPlanPage
    python3 tools/lookup_xpath.py "TXT_CODE"
"""
import sys
import json
import os

def main():
    if len(sys.argv) < 2:
        print("Sử dụng: python3 tools/lookup_xpath.py <Tên PageClass hoặc Từ khóa>")
        sys.exit(1)

    query = sys.argv[1].strip()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "Enterprise_scraped_xpaths.json")

    if not os.path.exists(json_path):
        print(f"Lỗi: Không tìm thấy {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

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
            c = item.get("constant", "")
            tag = item.get("tag", "")
            xp = item.get("xpath", "")
            print(f"- {c} ({tag}): {xp}")
        return

    # 2. Tìm theo từ khóa trong constant hoặc xpath
    found = []
    for page_name, selectors in data.items():
        for item in selectors:
            c = item.get("constant", "")
            xp = item.get("xpath", "")
            if query.lower() in c.lower() or query.lower() in xp.lower():
                found.append((page_name, c, item.get("tag", ""), xp))

    if not found:
        print(f"Không tìm thấy selector nào khớp với: '{query}'")
        return

    print(f"=== Tìm thấy {len(found)} selector cho từ khóa '{query}' ===")
    for page, c, tag, xp in found[:15]:
        print(f"[{page}] {c} ({tag}): {xp}")

if __name__ == "__main__":
    main()
