#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Deep unit tests for tools/setup_project.py (Stack Detection, AI Guide & Rule Deployment)
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import tools.core.setup_project as sp


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

    def test_install_universal_ai_bridges_ide_selective(self):
        # 1. Cursor selective: installs only .cursor/rules/synapse-qa.mdc
        c_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, c_dir)
        sp.install_universal_ai_bridges(c_dir, ide="cursor")
        self.assertTrue(os.path.exists(os.path.join(c_dir, ".cursor", "rules", "synapse-qa.mdc")))
        self.assertFalse(os.path.exists(os.path.join(c_dir, "CLAUDE.md")))
        self.assertFalse(os.path.exists(os.path.join(c_dir, ".windsurfrules")))

        # 2. Claude selective: installs only CLAUDE.md
        cl_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, cl_dir)
        sp.install_universal_ai_bridges(cl_dir, ide="claude")
        self.assertTrue(os.path.exists(os.path.join(cl_dir, "CLAUDE.md")))
        self.assertFalse(os.path.exists(os.path.join(cl_dir, ".cursor")))
        self.assertFalse(os.path.exists(os.path.join(cl_dir, ".windsurfrules")))

        # 3. Windsurf selective: installs only .windsurfrules
        w_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, w_dir)
        sp.install_universal_ai_bridges(w_dir, ide="windsurf")
        self.assertTrue(os.path.exists(os.path.join(w_dir, ".windsurfrules")))
        self.assertFalse(os.path.exists(os.path.join(w_dir, ".cursor")))
        self.assertFalse(os.path.exists(os.path.join(w_dir, "CLAUDE.md")))

    def test_git_hooks_are_portable_and_uninstall_restores_backup(self):
        """P0-5: Installed git hooks must not leak machine absolute paths and uninstall must restore original hooks."""
        git_dir = Path(self.temp_dir) / ".git"
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(parents=True)
        orig_hook = hooks_dir / "pre-push"
        orig_hook.write_text("#!/bin/sh\necho 'original husky hook'\n", encoding="utf-8")

        self.assertTrue(sp.install_git_pre_push_hook(self.temp_dir))
        self.assertTrue(sp.install_git_post_merge_hook(self.temp_dir))

        pre_push_txt = orig_hook.read_text(encoding="utf-8")
        post_merge_txt = (hooks_dir / "post-merge").read_text(encoding="utf-8")
        hub_root_norm = sp.HUB_ROOT.replace("\\", "/")

        self.assertNotIn(hub_root_norm, pre_push_txt, "pre-push hook leaked Hub machine absolute path")
        self.assertNotIn(hub_root_norm, post_merge_txt, "post-merge hook leaked Hub machine absolute path")
        self.assertNotIn("tools/core/welcome_page.py", post_merge_txt, "post-merge references non-existent welcome_page path")

        # Install client artifacts then uninstall
        sp.install_universal_ai_bridges(self.temp_dir, ide="all")
        sp.ensure_synapse_config(self.temp_dir)
        sp.project_state.init_state(self.temp_dir)

        ret = sp.uninstall_setup(self.temp_dir)
        self.assertEqual(ret, 0)
        self.assertTrue(orig_hook.exists(), "Original pre-push hook must be restored from backup")
        self.assertIn("original husky hook", orig_hook.read_text(encoding="utf-8"))
        self.assertFalse((hooks_dir / "post-merge").exists())
        self.assertFalse((Path(self.temp_dir) / "CLAUDE.md").exists())
        self.assertFalse((Path(self.temp_dir) / "synapse.config.json").exists())
        self.assertFalse((Path(self.temp_dir) / "PROJECT_STATE.md").exists())


if __name__ == "__main__":
    unittest.main()
