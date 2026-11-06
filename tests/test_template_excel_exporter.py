#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Unit Tests for tools/template_excel_exporter.py
------------------------------------------------
Validates:
  1. Markdown test case parser (sections, subsections, preconditions, table rows)
  2. Project config discovery (.synapse.json)
  3. Template cloning, metadata injection, and formula updates
"""

import json
import os
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import template_excel_exporter as tee
import openpyxl


class TestTemplateExcelExporter(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        # Build a minimal mock template workbook
        self.template_path = os.path.join(self.temp_dir.name, "mock_template.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "TemplateSheet"

        # Headers and formulas
        ws["B2"] = "OLD_CODE"
        ws["D2"] = "OLD_NAME"
        ws["B3"] = "OLD_AUTHOR"
        ws["H3"] = "Pass"
        ws["H4"] = "Fail"
        ws["I2"] = "High"
        ws["J2"] = "Medium"
        ws["K2"] = "Low"

        # Headers at row 9-10
        ws["A9"] = "Testcase_ID"
        ws["B9"] = "Tên testcase"
        ws["I9"] = "Độ ưu tiên"
        ws["T9"] = "Kết quả hiện tại"

        # Mock initial row 11
        ws["A11"] = "TC_OLD_01"
        ws["I11"] = "High"
        ws["T11"] = "Pass"

        wb.save(self.template_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_markdown_tables(self):
        md = """
### 1. Màn hình [Quản lý người dùng]
## Truy cập và kiểm tra
Tiền điều kiện: Đăng nhập thành công với admin.

| Testcase_ID | Tên testcase | Tiền điều kiện | Các bước thực hiện | Data test | Kết quả mong đợi | Mức độ nghiêm trọng lỗi | Độ ưu tiên | Kết quả hiện tại | Ghi chú |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC_01 | Kiểm tra đăng nhập | Đã có tài khoản | 1. Nhập user<br>2. Nhập pass | user=admin | Đăng nhập thành công | Major | High | Pass | Note A |
| TC_02 | Kiểm tra tìm kiếm | Đang ở màn hình | 1. Nhập từ khóa | kw=abc | Tìm thấy kết quả | Minor | Medium | Pass | Note B |
"""
        rows = tee.parse_testcases_from_markdown(md)
        self.assertGreaterEqual(len(rows), 4)
        self.assertEqual(rows[0]["type"], "section")
        self.assertIn("1. Màn hình", rows[0]["text"])
        self.assertEqual(rows[1]["type"], "subsection")
        self.assertEqual(rows[2]["type"], "precondition")

        case_rows = [r for r in rows if r.get("type") == "case"]
        self.assertEqual(len(case_rows), 2)
        self.assertEqual(case_rows[0]["testcase_id"], "TC_01")
        self.assertEqual(case_rows[1]["testcase_id"], "TC_02")

    def test_clone_and_export_template(self):
        rows = [
            {"type": "section", "text": "1. Màn hình [Test Feature]"},
            {"type": "precondition", "text": "Đăng nhập admin"},
            {
                "type": "case",
                "testcase_id": "TC_NEW_01",
                "tên testcase": "Verify New Flow",
                "các bước thực hiện": "1. Step 1\n2. Step 2",
                "kết quả mong đợi": "Expected result",
                "mức độ nghiêm trọng lỗi": "Major",
                "độ ưu tiên": "High",
                "kết quả hiện tại": "Pass",
                "ghi chú": "Verified"
            }
        ]

        out_path = os.path.join(self.temp_dir.name, "exported_result.xlsx")
        result = tee.clone_and_export_template(
            rows=rows,
            output_path=out_path,
            template_path=self.template_path,
            sample_sheet_name="TemplateSheet",
            target_sheet_name="New Feature",
            module_code="NEW_MOD",
            module_name="New Module Name",
            author="Phạm Thế Vị"
        )

        self.assertTrue(os.path.exists(result))

        # Check workbook contents
        wb = openpyxl.load_workbook(result, data_only=False)
        self.assertIn("New Feature", wb.sheetnames)
        ws = wb["New Feature"]
        self.assertEqual(ws["B2"].value, "NEW_MOD")
        self.assertEqual(ws["D2"].value, "New Module Name")
        self.assertEqual(ws["B3"].value, "Phạm Thế Vị")
        self.assertIn("COUNTIFS", ws["I3"].value)

    def test_find_project_config_found(self):
        """Validates finding .synapse.json in the specified start directory."""
        cfg_path = os.path.join(self.temp_dir.name, ".synapse.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({"project": {"name": "DemoApp"}}, f)

        cfg = tee.find_project_config(self.temp_dir.name)
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.get("project", {}).get("name"), "DemoApp")
        self.assertEqual(cfg.get("_config_dir"), str(os.path.realpath(self.temp_dir.name)))

    def test_find_project_config_parent_traversal(self):
        """Validates finding .synapse.json by walking up parent directories."""
        cfg_path = os.path.join(self.temp_dir.name, ".synapse.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({"project": {"author": "Tester"}}, f)

        sub_dir = os.path.join(self.temp_dir.name, "deep", "nested", "path")
        os.makedirs(sub_dir, exist_ok=True)

        cfg = tee.find_project_config(sub_dir)
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.get("project", {}).get("author"), "Tester")
        self.assertEqual(cfg.get("_config_dir"), str(os.path.realpath(self.temp_dir.name)))

    def test_find_project_config_not_found(self):
        """Validates that find_project_config returns None when no .synapse.json exists."""
        with tempfile.TemporaryDirectory() as empty_dir:
            cfg = tee.find_project_config(empty_dir)
            self.assertIsNone(cfg)

    def test_find_project_config_corrupt_json_fallback(self):
        """Validates that corrupt .synapse.json does not raise unhandled exception and falls back to None."""
        with tempfile.TemporaryDirectory() as isolated_dir:
            cfg_path = os.path.join(isolated_dir, ".synapse.json")
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write("{ invalid json corrupted content }")

            cfg = tee.find_project_config(isolated_dir)
            self.assertIsNone(cfg)

    def test_find_project_config_non_dict_json(self):
        """Validates that non-dict JSON (e.g. array) is caught gracefully and returns None."""
        with tempfile.TemporaryDirectory() as isolated_dir:
            cfg_path = os.path.join(isolated_dir, ".synapse.json")
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write("[\"not\", \"a\", \"dict\"]")

            cfg = tee.find_project_config(isolated_dir)
            self.assertIsNone(cfg)

    def test_fallback_to_default_exporter_without_template(self):
        """Validates that main() falls back to md_to_xlsx.convert_markdown_to_xlsx when template is missing."""
        md_path = os.path.join(self.temp_dir.name, "sample_testcases.md")
        out_xlsx = os.path.join(self.temp_dir.name, "exported_default.xlsx")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Module\n\n| TC ID | Summary | Step | Expected | Status |\n|---|---|---|---|---|\n| TC_01 | Check | Do | Pass | Pass |\n")

        saved_argv = sys.argv
        try:
            sys.argv = [
                "template_excel_exporter.py",
                md_path,
                "-o", out_xlsx
            ]
            ret = tee.main()
            self.assertEqual(ret, 0)
            self.assertTrue(os.path.exists(out_xlsx))
        finally:
            sys.argv = saved_argv


if __name__ == "__main__":
    unittest.main()

