#!/usr/bin/env python3
"""
Công cụ tra cứu nhanh Test Case từ tools/Enterprise_testcases.json.
Giúp AI Agent chỉ lấy đúng 1 ca kiểm thử (<100 tokens) thay vì đọc toàn bộ file 176 KB (~45.000 tokens).
Sử dụng:
    python3 tools/lookup_tc.py TC-132
    python3 tools/lookup_tc.py "Xóa chợ"
"""
import sys
import json
import os

def main():
    if len(sys.argv) < 2:
        print("Sử dụng: python3 tools/lookup_tc.py <TC-ID hoặc từ khóa>")
        sys.exit(1)

    query = sys.argv[1].strip().lower()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "Enterprise_testcases.json")

    if not os.path.exists(json_path):
        print(f"Lỗi: Không tìm thấy {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    matches = []
    exact_matches = []
    fuzzy_matches = []
    for tc in data:
        tc_id = tc.get("ID", "").strip().lower()
        tc_name = tc.get("Name", "").strip().lower()
        if query == tc_id or f"tc-{query}" == tc_id:
            exact_matches.append(tc)
        elif query in tc_id or query in tc_name:
            fuzzy_matches.append(tc)

    matches = exact_matches if exact_matches else fuzzy_matches

    if not matches:
        print(f"Không tìm thấy Test Case nào khớp với: '{sys.argv[1]}'")
        sys.exit(0)

    print(f"=== Tìm thấy {len(matches)} Test Case ===")
    for tc in matches[:5]:
        print(f"ID: {tc.get('ID')} | Phân hệ: {tc.get('Module')}")
        print(f"Tên: {tc.get('Name')}")
        print(f"Kỳ vọng: {tc.get('Expected')}")
        print(f"Các bước:\n{tc.get('Steps')}")
        print("-" * 50)

if __name__ == "__main__":
    main()
