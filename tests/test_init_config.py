#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Unit Tests for tools/init_config.py
----------------------------------
Validates:
  1. Default and customized .synapse.json generation
  2. Dry-run safety (zero file mutation)
  3. Existing file collision and --force overwrite guard
  4. Compatibility with template_excel_exporter.find_project_config()
"""

import os
import sys
import json
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import init_config as ic
import tools.contrib.template_excel_exporter as tee


class TestInitConfig(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.orig_non_interactive = os.environ.get("SYNAPSE_NON_INTERACTIVE")
        os.environ["SYNAPSE_NON_INTERACTIVE"] = "1"

    def tearDown(self):
        self.temp_dir.cleanup()
        if self.orig_non_interactive is None:
            os.environ.pop("SYNAPSE_NON_INTERACTIVE", None)
        else:
            os.environ["SYNAPSE_NON_INTERACTIVE"] = self.orig_non_interactive

    def test_dry_run_does_not_create_file(self):
        """Verifies that dry-run returns 0 and does not write any file to disk."""
        target_file = os.path.join(self.temp_dir.name, ".synapse.json")
        ret = ic.init_config(target_dir=self.temp_dir.name, dry_run=True)
        self.assertEqual(ret, 0)
        self.assertFalse(os.path.exists(target_file))

    def test_init_config_creates_valid_file(self):
        """Verifies that init_config writes a valid .synapse.json with provided options."""
        ret = ic.init_config(
            target_dir=self.temp_dir.name,
            project_name="MyTestProject",
            author="Test Author",
            tester="QA Tester",
            template_path="templates/custom_tpl.xlsx",
            sample_sheet="MySheet",
            module_code="AUTH",
            module_name="Authentication",
            force=True
        )
        self.assertEqual(ret, 0)
        target_file = os.path.join(self.temp_dir.name, ".synapse.json")
        self.assertTrue(os.path.exists(target_file))

        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["project"]["name"], "MyTestProject")
        self.assertEqual(data["project"]["author"], "Test Author")
        self.assertEqual(data["project"]["tester"], "QA Tester")
        self.assertEqual(data["testcase_export"]["template_path"], "templates/custom_tpl.xlsx")
        self.assertEqual(data["testcase_export"]["sample_sheet"], "MySheet")
        self.assertEqual(data["testcase_export"]["module_code"], "AUTH")
        self.assertEqual(data["testcase_export"]["module_name"], "Authentication")
        self.assertEqual(data["quality_gates"]["mutation_min_score"], 80)
        self.assertTrue(data["quality_gates"]["gates"]["gate_1_bom_check"])

    def test_existing_file_without_force_fails(self):
        """Verifies that init_config refuses to overwrite existing file without --force."""
        target_file = os.path.join(self.temp_dir.name, ".synapse.json")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write('{"existing": true}')

        ret = ic.init_config(target_dir=self.temp_dir.name, force=False)
        self.assertEqual(ret, 1)

        # Content must remain unchanged
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertTrue(data.get("existing"))

    def test_existing_file_with_force_succeeds(self):
        """Verifies that init_config overwrites existing file when force=True."""
        target_file = os.path.join(self.temp_dir.name, ".synapse.json")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write('{"old": true}')

        ret = ic.init_config(
            target_dir=self.temp_dir.name,
            project_name="OverwrittenProject",
            force=True
        )
        self.assertEqual(ret, 0)

        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["project"]["name"], "OverwrittenProject")

    def test_integration_with_template_excel_exporter(self):
        """Verifies that generated config is seamlessly discovered and read by template_excel_exporter."""
        ic.init_config(
            target_dir=self.temp_dir.name,
            project_name="IntegrationApp",
            author="Lead QA",
            template_path="templates/excel.xlsx",
            sample_sheet="TC_Sheet",
            force=True
        )

        cfg = tee.find_project_config(self.temp_dir.name)
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg["project"]["name"], "IntegrationApp")
        self.assertEqual(cfg["project"]["author"], "Lead QA")
        self.assertEqual(cfg["testcase_export"]["template_path"], "templates/excel.xlsx")
        self.assertEqual(cfg["testcase_export"]["sample_sheet"], "TC_Sheet")

    def test_hub_directory_guard_blocks_hub_pollution(self):
        """Verifies that init_config refuses to write .synapse.json into Hub root (Anti-Pattern Rule 7 & 8)."""
        hub_root = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
        target_file = os.path.join(hub_root, ".synapse.json")
        self.assertFalse(os.path.exists(target_file))

        ret = ic.init_config(target_dir=hub_root, force=False, dry_run=False)
        self.assertEqual(ret, 1)
        self.assertFalse(os.path.exists(target_file))

    def test_non_interactive_ci_environment(self):
        """Verifies that in non-interactive CI mode, init_config proceeds with defaults without prompt."""
        old_ci = os.environ.get("CI")
        try:
            os.environ["CI"] = "1"
            ret = ic.init_config(
                target_dir=self.temp_dir.name,
                project_name="CIProject",
                force=True
            )
            self.assertEqual(ret, 0)
            target_file = os.path.join(self.temp_dir.name, ".synapse.json")
            self.assertTrue(os.path.exists(target_file))
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["project"]["name"], "CIProject")
        finally:
            if old_ci is None:
                os.environ.pop("CI", None)
            else:
                os.environ["CI"] = old_ci

    def test_empty_template_path_fallback_integration(self):
        """Verifies that template_excel_exporter gracefully handles empty template_path in .synapse.json."""
        # 1. Initialize .synapse.json with empty template_path (Hub default layout)
        ic.init_config(
            target_dir=self.temp_dir.name,
            project_name="FallbackApp",
            template_path="",
            force=True
        )

        # 2. Write a minimal testcase markdown file
        md_path = os.path.join(self.temp_dir.name, "testcases.md")
        out_xlsx = os.path.join(self.temp_dir.name, "output.xlsx")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Test Module\n\n| TC ID | Summary | Step | Expected | Status |\n|---|---|---|---|---|\n| TC_01 | Login | Step 1 | Success | Pass |\n")

        # 3. Invoke template_excel_exporter main with args
        saved_argv = sys.argv
        try:
            sys.argv = [
                "template_excel_exporter.py",
                md_path,
                "-o", out_xlsx
            ]
            cwd_orig = os.getcwd()
            os.chdir(self.temp_dir.name)
            try:
                ret = tee.main()
                self.assertEqual(ret, 0)
                self.assertTrue(os.path.exists(out_xlsx))
            finally:
                os.chdir(cwd_orig)
        finally:
            sys.argv = saved_argv

    def test_profile_configurations(self):
        """Verifies that starter, standard, and enterprise profiles produce expected quality gate settings."""
        starter_cfg = ic.build_default_config(profile="starter")
        self.assertEqual(starter_cfg["quality_gates"]["profile"], "starter")
        self.assertEqual(starter_cfg["quality_gates"]["mutation_min_score"], 0)
        self.assertFalse(starter_cfg["quality_gates"]["gates"]["gate_3_clean_pom"])
        self.assertFalse(starter_cfg["infer_linter"]["strict"])

        standard_cfg = ic.build_default_config(profile="standard")
        self.assertEqual(standard_cfg["quality_gates"]["profile"], "standard")
        self.assertEqual(standard_cfg["quality_gates"]["mutation_min_score"], 50)
        self.assertTrue(standard_cfg["quality_gates"]["gates"]["gate_3_clean_pom"])
        self.assertTrue(standard_cfg["infer_linter"]["strict"])

        enterprise_cfg = ic.build_default_config(profile="enterprise")
        self.assertEqual(enterprise_cfg["quality_gates"]["profile"], "enterprise")
        self.assertEqual(enterprise_cfg["quality_gates"]["mutation_min_score"], 80)
        self.assertTrue(enterprise_cfg["quality_gates"]["gates"]["gate_10_performance_sla"])

    def test_scaffold_project_integration(self):
        """Verifies that scaffold_project correctly unpacks a template and configures synapse.config.json."""
        from tools.core.scaffold import scaffold_project
        dest = os.path.join(self.temp_dir.name, "my_scaffold_test")
        ret = scaffold_project("my_scaffold_test", template="playwright", profile="starter", target_dir=self.temp_dir.name)
        self.assertEqual(ret, 0)
        self.assertTrue(os.path.isdir(dest))
        cfg_file = os.path.join(dest, "synapse.config.json")
        self.assertTrue(os.path.isfile(cfg_file))
        with open(cfg_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["quality_gates"]["profile"], "starter")
        self.assertFalse(data["infer_linter"]["strict"])


if __name__ == "__main__":
    unittest.main()
