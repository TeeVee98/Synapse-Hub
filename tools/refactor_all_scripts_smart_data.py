#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMIT Automation - Batch Refactor Scripts with Smart Vietnamese Business Data
=============================================================================
Refactors ad-hoc test data generation strings ("Auto...", "Sua...", hardcoded addresses)
across all 259 test cases in Scripts/ with standardized Vietnamese business data from
DataGenerator, CommonCategoryPage, IndustryCategoryPage, and DataMiningPage.
"""

import os
import sys
import glob
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "Scripts")

# Subcategory key map for Batch 05
CAT_MAP = {
    "TC-29": "nkt", "TC-30": "nkt",
    "TC-33": "nsp", "TC-34": "nsp",
    "TC-37": "xnk", "TC-38": "xnk",
    "TC-41": "lvct", "TC-42": "lvct",
    "TC-45": "dvk", "TC-46": "dvk",
    "TC-49": "bog", "TC-50": "bog",
    "TC-53": "lpg", "TC-54": "lpg",
    "TC-57": "hc", "TC-58": "hc",
    "TC-61": "ruou", "TC-62": "ruou",
    "TC-65": "tp", "TC-66": "tp",
    "TC-69": "xd", "TC-70": "xd",
    "TC-73": "tl", "TC-74": "tl",
    "TC-77": "ct", "TC-78": "ct",
    "TC-81": "pd", "TC-82": "pd",
    "TC-85": "cn", "TC-86": "cn",
    "TC-89": "tm", "TC-90": "tm",
}

def refactor_script(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    tc_dir = os.path.basename(os.path.dirname(file_path))
    tc_num = tc_dir.split(" ")[0]

    # --- 1. Batch 04: Danh mục dùng chung (TC-17 đến TC-28) ---
    if tc_num == "TC-17":
        content = re.sub(r'String\s+deptName\s*=\s*"Phòng Ban Auto "\s*\+\s*ts',
                         'String deptName = CommonCategoryPage.randomDepartmentName()', content)
    elif tc_num == "TC-19":
        content = re.sub(r'String\s+newName\s*=\s*"Phòng Ban Sửa "\s*\+\s*\(System\.currentTimeMillis\(\)\s*%\s*10000\)',
                         'String newName = CommonCategoryPage.randomEditedDepartmentName()', content)
    elif tc_num == "TC-21":
        content = re.sub(r'String\s+posName\s*=\s*"Chức Vụ Auto "\s*\+\s*ts',
                         'String posName = CommonCategoryPage.randomTitleName()', content)
    elif tc_num == "TC-23":
        content = re.sub(r'String\s+newName\s*=\s*"Chức Vụ Sửa "\s*\+\s*\(System\.currentTimeMillis\(\)\s*%\s*10000\)',
                         'String newName = CommonCategoryPage.randomEditedTitleName()', content)
    elif tc_num == "TC-25":
        content = re.sub(r'String\s+careerName\s*=\s*"Ngành Nghề Auto "\s*\+\s*ts',
                         'String careerName = CommonCategoryPage.randomOccupationName()', content)
    elif tc_num == "TC-27":
        content = re.sub(r'String\s+newName\s*=\s*"Ngành Nghề Sửa "\s*\+\s*\(System\.currentTimeMillis\(\)\s*%\s*10000\)',
                         'String newName = CommonCategoryPage.randomEditedOccupationName()', content)

    # --- 2. Batch 05: Danh mục ngành Công Thương (TC-29 đến TC-92) ---
    elif tc_num in CAT_MAP:
        key = CAT_MAP[tc_num]
        # Tạo mới: "Auto [KEY] " + ts
        content = re.sub(
            r'String\s+name\s*=\s*"Auto\s+[A-Z0-9_]+\s*"\s*\+\s*ts',
            f"String name = IndustryCategoryPage.randomCategoryName('{key}')",
            content
        )
        # Sửa: "Sua [KEY] " + (System.currentTimeMillis() % 10000)
        content = re.sub(
            r'String\s+newName\s*=\s*"Sua\s+[A-Z0-9_]+\s*"\s*\+\s*\(System\.currentTimeMillis\(\)\s*%\s*10000\)',
            f"String newName = IndustryCategoryPage.randomEditedCategoryName('{key}')",
            content
        )

    # --- 3. Batch 07: Khai phá dữ liệu (TC-123 đến TC-144) ---
    elif tc_num == "TC-123":
        content = re.sub(
            r'String\s+recordName\s*=\s*"Cụm công nghiệp Auto "\s*\+\s*\(System\.currentTimeMillis\(\)\s*%\s*10000L\)',
            'String recordName = DataMiningPage.randomMiningRecordName("Cụm công nghiệp")',
            content
        )
    elif tc_num == "TC-127":
        content = re.sub(
            r'String\s+name\s*=\s*"Chợ Trung Tâm Auto "\s*\+\s*\(System\.currentTimeMillis\(\)\s*%\s*10000L\)',
            'String name = DataMiningPage.randomMiningRecordName("Chợ Trung Tâm")',
            content
        )
    elif tc_num == "TC-135":
        content = re.sub(
            r'String\s+recordName\s*=\s*"Siêu thị Auto "\s*\+\s*\(System\.currentTimeMillis\(\)\s*%\s*10000L\)',
            'String recordName = DataMiningPage.randomMiningRecordName("Siêu thị")',
            content
        )
    elif tc_num == "TC-139":
        content = re.sub(
            r'String\s+recordName\s*=\s*"Nguồn điện Auto "\s*\+\s*\(System\.currentTimeMillis\(\)\s*%\s*10000L\)',
            'String recordName = DataMiningPage.randomMiningRecordName("Nguồn điện")',
            content
        )
    elif tc_num == "TC-143":
        content = re.sub(
            r'String\s+recordName\s*=\s*"Cửa hàng xăng dầu Auto "\s*\+\s*\(System\.currentTimeMillis\(\)\s*%\s*10000L\)',
            'String recordName = DataMiningPage.randomMiningRecordName("Cửa hàng xăng dầu")',
            content
        )

    # --- 4. User Profile & Account (TC-11, TC-14) ---
    elif tc_num == "TC-11":
        content = re.sub(
            r'String\s+newFirstName\s*=\s*"Auto_"\s*\+\s*\(System\.currentTimeMillis\(\)\s*%\s*100000\)',
            'String newFirstName = "Hùng_" + (System.currentTimeMillis() % 10000)',
            content
        )
    elif tc_num == "TC-14":
        content = re.sub(
            r'String\s+newFirstName\s*=\s*"CapNhat"\s*\+\s*\(System\.currentTimeMillis\(\)\s*%\s*1000\)',
            'String newFirstName = "Tuấn_" + (System.currentTimeMillis() % 1000)',
            content
        )

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False

def main():
    script_files = glob.glob(os.path.join(SCRIPTS_DIR, "**", "*.groovy"), recursive=True)
    modified_count = 0
    print(f"Bắt đầu quét và refactor {len(script_files)} tệp tin kịch bản kiểm thử...")

    for sf in sorted(script_files):
        if refactor_script(sf):
            tc = os.path.basename(os.path.dirname(sf))
            print(f"  [REFACTORED] {tc}")
            modified_count += 1

    print(f"\n✅ Hoàn thành refactor: {modified_count} tệp tin kịch bản đã được nâng cấp sang dữ liệu nghiệp vụ chuẩn!")

if __name__ == "__main__":
    main()
