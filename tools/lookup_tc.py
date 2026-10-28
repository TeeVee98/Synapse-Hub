#!/usr/bin/env python3
"""
Enterprise QA: Fast Test Case Metadata Lookup (lookup_tc.py)
-------------------------------------------------------------
Công cụ tra cứu nhanh Test Case từ file JSON testcases của dự án.
Giúp AI Agent chỉ nạp đúng 1 ca kiểm thử (<100 tokens) thay vì đọc toàn bộ file (~45.000 tokens).

Cơ chế nạp dữ liệu đa tầng (Multi-tier Resolution):
  1. CLI Flag: python tools/lookup_tc.py <query> --file <path_to_json> (hoặc -f)
  2. Biến môi trường: TC_DATA_FILE hoặc TESTCASES_JSON
  3. Tự động phát hiện trong dự án: testcases.json, Enterprise_testcases.json, tc_index.json...
  4. Dự phòng nội bộ Hub: archive/legacy_references/Enterprise_testcases.json
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
    """Xác định đường dẫn file JSON Test Case theo thứ tự ưu tiên."""
    # 1. CLI flag
    if cli_file:
        if os.path.exists(cli_file):
            return os.path.abspath(cli_file)
        else:
            print(f"⚠️  Cảnh báo: File chỉ định qua --file '{cli_file}' không tồn tại.")

    # 2. Biến môi trường
    env_file = os.environ.get("TC_DATA_FILE") or os.environ.get("TESTCASES_JSON")
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
        "testcases.json",
        "tc_index.json",
        "Enterprise_testcases.json",
        "test_cases.json",
        "tc_matrix.json"
    ]

    for d in search_dirs:
        for name in candidate_names:
            candidate = os.path.join(d, name)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)

    # 4. Dự phòng Hub Archive
    for legacy_name in ["Enterprise_testcases.json", "dmit_testcases.json", "odp_testcases.json"]:
        legacy_file = os.path.join(hub_root, "archive", "legacy_references", legacy_name)
        if os.path.isfile(legacy_file):
            return os.path.abspath(legacy_file)

    return None


def normalize_testcase_data(raw_data):
    """Chuẩn hóa dữ liệu Test Case từ nhiều định dạng JSON khác nhau (list, dict, dict of dicts)."""
    if isinstance(raw_data, list):
        return raw_data
    elif isinstance(raw_data, dict):
        if "testcases" in raw_data and isinstance(raw_data["testcases"], list):
            return raw_data["testcases"]
        if "items" in raw_data and isinstance(raw_data["items"], list):
            return raw_data["items"]
        
        # Dict map ID -> TC Object
        flat = []
        for k, v in raw_data.items():
            if isinstance(v, dict):
                item = dict(v)
                if "ID" not in item:
                    item["ID"] = k
                flat.append(item)
            else:
                flat.append({"ID": k, "Name": str(v)})
        return flat
    return []


def main():
    parser = argparse.ArgumentParser(description="Tra cứu nhanh Test Case từ file JSON của dự án")
    parser.add_argument("query", help="Mã ID Test Case (ví dụ: TC-132, 132) hoặc từ khóa tìm kiếm")
    parser.add_argument("-f", "--file", dest="file", help="Đường dẫn file JSON chứa danh sách Test Case")
    args = parser.parse_args()

    json_path = resolve_json_path(args.file)

    if not json_path:
        print("❌ Lỗi: Không tìm thấy file JSON dữ liệu Test Case.")
        print("\n👉 Hướng dẫn cấu hình nạp dữ liệu cho target project:")
        print("  1. Dùng CLI flag: python tools/lookup_tc.py <query> --file <đường_dẫn_tới_testcases.json>")
        print("  2. Đặt biến môi trường: export TC_DATA_FILE='path/to/testcases.json' (hoặc set TC_DATA_FILE=...)")
        print("  3. Đặt file 'testcases.json' vào thư mục gốc dự án hoặc khai báo trong PROJECT_AI_GUIDE.md")
        sys.exit(1)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"❌ Lỗi khi đọc file '{json_path}': {e}")
        sys.exit(1)

    data = normalize_testcase_data(raw_data)
    query = args.query.strip().lower()

    exact_matches = []
    fuzzy_matches = []

    for tc in data:
        tc_id = str(tc.get("ID") or tc.get("id") or tc.get("tc_id") or "").strip().lower()
        tc_name = str(tc.get("Name") or tc.get("name") or tc.get("title") or "").strip().lower()

        if query == tc_id or f"tc-{query}" == tc_id or f"tc_{query}" == tc_id:
            exact_matches.append(tc)
        elif query in tc_id or query in tc_name:
            fuzzy_matches.append(tc)

    matches = exact_matches if exact_matches else fuzzy_matches

    if not matches:
        print(f"Không tìm thấy Test Case nào khớp với: '{args.query}' trong file '{os.path.basename(json_path)}'")
        sys.exit(0)

    print(f"=== Tìm thấy {len(matches)} Test Case (Nguồn: {os.path.relpath(json_path, os.getcwd()) if os.path.exists(json_path) else json_path}) ===")
    for tc in matches[:5]:
        tc_id = tc.get("ID") or tc.get("id") or "N/A"
        tc_mod = tc.get("Module") or tc.get("module") or "GLOBAL"
        tc_name = tc.get("Name") or tc.get("name") or tc.get("title") or "N/A"
        tc_expected = tc.get("Expected") or tc.get("expected") or tc.get("expected_result") or "N/A"
        tc_steps = tc.get("Steps") or tc.get("steps") or tc.get("description") or "N/A"

        print(f"ID: {tc_id} | Phân hệ: {tc_mod}")
        print(f"Tên: {tc_name}")
        print(f"Kỳ vọng: {tc_expected}")
        print(f"Các bước:\n{tc_steps}")
        print("-" * 50)


if __name__ == "__main__":
    main()
