#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Deep unit tests for tools/setup_project.py (Stack Detection, AI Guide & Rule Deployment)
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import tools.setup_project as sp


class TestSetupProjectDeep(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="setup_proj_test_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_detect_tech_stack_katalon(self):
        # Create a dummy .prj file
        (Path(self.temp_dir) / "MyProj.prj").write_text("<project></project>", encoding="utf-8")
        stack = sp.detect_tech_stack(self.temp_dir)
        self.assertTrue("Katalon" in stack["framework"])
        self.assertEqual(stack["language"], "Groovy")

    def test_detect_tech_stack_playwright(self):
        p_dir = tempfile.mkdtemp(prefix="pw_")
        try:
            (Path(p_dir) / "playwright.config.ts").write_text("export default {}", encoding="utf-8")
            stack = sp.detect_tech_stack(p_dir)
            self.assertTrue("Playwright" in stack["framework"])
            self.assertEqual(stack["language"], "TypeScript")
        finally:
            if os.path.exists(p_dir):
                shutil.rmtree(p_dir)

    def test_detect_tech_stack_cypress(self):
        c_dir = tempfile.mkdtemp(prefix="cy_")
        try:
            (Path(c_dir) / "cypress.config.js").write_text("module.exports = {}", encoding="utf-8")
            stack = sp.detect_tech_stack(c_dir)
            self.assertTrue("Cypress" in stack["framework"])
            self.assertEqual(stack["language"], "JavaScript")
        finally:
            if os.path.exists(c_dir):
                shutil.rmtree(c_dir)

    def test_detect_tech_stack_pytest(self):
        py_dir = tempfile.mkdtemp(prefix="pytest_")
        try:
            (Path(py_dir) / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
            stack = sp.detect_tech_stack(py_dir)
            self.assertEqual(stack["framework"], "Pytest")
            self.assertEqual(stack["language"], "Python")
        finally:
            if os.path.exists(py_dir):
                shutil.rmtree(py_dir)

    def test_ensure_project_ai_guide(self):
        stack_info = {
            "name": "AcmePlatform",
            "framework": "Playwright Test",
            "language": "TypeScript",
            "page_dir": "src/pages",
            "test_dir": "tests",
            "run_cmd": "npx playwright test"
        }
        created = sp.ensure_project_ai_guide(self.temp_dir, stack_info, profile="standard")
        self.assertTrue(created)
        guide_file = os.path.join(self.temp_dir, "PROJECT_AI_GUIDE.md")
        self.assertTrue(os.path.exists(guide_file))
        with open(guide_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("AcmePlatform", content)

        # Second call does not overwrite existing guide
        created_again = sp.ensure_project_ai_guide(self.temp_dir, stack_info)
        self.assertFalse(created_again)

    def test_install_git_pre_push_hook(self):
        # Non-git directory -> skips safely
        self.assertFalse(sp.install_git_pre_push_hook(self.temp_dir))

        # Git directory -> installs hook
        git_dir = os.path.join(self.temp_dir, ".git")
        os.makedirs(git_dir, exist_ok=True)
        installed = sp.install_git_pre_push_hook(self.temp_dir)
        self.assertTrue(installed)
        hook_path = os.path.join(git_dir, "hooks", "pre-push")
        self.assertTrue(os.path.exists(hook_path))

    def test_resolve_target_repo(self):
        # Resolves explicit target
        res = sp.resolve_target_repo(cli_target=self.temp_dir)
        self.assertEqual(res, os.path.abspath(self.temp_dir))

        # Rejects self (Hub)
        with self.assertRaises(SystemExit):
            sp.resolve_target_repo(cli_target=sp.HUB_ROOT)


if __name__ == "__main__":
    unittest.main()
