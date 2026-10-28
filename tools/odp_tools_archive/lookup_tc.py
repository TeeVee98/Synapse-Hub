#!/usr/bin/env python3
"""
Công cụ tra cứu nhanh Test Case từ tools/odp_testcases.json (75 TCs ODP).
Giúp AI Agent chỉ lấy đúng 1 ca kiểm thử (<100 tokens) thay vì đọc toàn bộ
POM_REFACTORING_PLAN.md (~75 dòng ma trận + bảng mô tả).
Sử dụng:
    python3 tools/lookup_tc.py TC_03
    python3 tools/lookup_tc.py "Xóa bộ dữ liệu"
    python3 tools/lookup_tc.py 05
"""
import sys
import json
import os

def main():
    if len(sys.argv) < 2:
        print("Sử dụng: python3 tools/lookup_tc.py <TC-ID hoặc từ khóa>")
        sys.exit(1)

    raw = sys.argv[1].strip()
    # Chuẩn hóa: "5", "05", "TC 05", "TC_05", "tc-05" -> "tc_05"
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits:
        query = "tc_" + digits.zfill(2)
    else:
        query = raw.lower()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "odp_testcases.json")

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
        if query == tc_id:
            exact_matches.append(tc)
        elif query in tc_id or (not digits and query in tc_name):
            fuzzy_matches.append(tc)

    matches = exact_matches if exact_matches else fuzzy_matches

    if not matches:
        print(f"Không tìm thấy Test Case nào khớp với: '{sys.argv[1]}' (đã chuẩn hóa: '{query}')")
        sys.exit(0)

    print(f"=== Tìm thấy {len(matches)} Test Case ===")
    for tc in matches[:5]:
        print(f"ID: {tc.get('ID')} | Phân hệ: {tc.get('Module')}")
        print(f"Tên: {tc.get('Name')}")
        print(f"Test Script: {tc.get('Script')}")
        print(f"Page Object: {tc.get('Page')}")
        print("-" * 50)

if __name__ == "__main__":
    main()
