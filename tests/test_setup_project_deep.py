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

        # 4. Codex selective: installs only AGENTS.md and .codex/config.toml
        cx_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, cx_dir)
        sp.install_universal_ai_bridges(cx_dir, ide="codex")
        self.assertTrue(os.path.exists(os.path.join(cx_dir, "AGENTS.md")))
        self.assertTrue(os.path.exists(os.path.join(cx_dir, ".codex", "config.toml")))
        self.assertFalse(os.path.exists(os.path.join(cx_dir, "CLAUDE.md")))
        self.assertFalse(os.path.exists(os.path.join(cx_dir, ".cursor")))
        self.assertFalse(os.path.exists(os.path.join(cx_dir, ".windsurfrules")))
        agents_txt = (Path(cx_dir) / "AGENTS.md").read_text(encoding="utf-8")
        toml_txt = (Path(cx_dir) / ".codex" / "config.toml").read_text(encoding="utf-8")
        self.assertIn("synapse_verify", agents_txt)
        self.assertIn("[mcp_servers.synapse-hub]", toml_txt)

    def test_codex_negative_hub_guard_and_boundary_empty_target(self):
        """Negative & Boundary: rejects Hub root target and handles empty target/CLI dry-run safely."""
        with self.assertRaises(ValueError):
            sp.install_codex_skills(sp.HUB_ROOT)

        # Boundary: empty target directory without pre-existing .agents or .codex succeeds cleanly
        empty_dir = tempfile.mkdtemp(prefix="codex_empty_")
        self.addCleanup(shutil.rmtree, empty_dir)
        res = sp.install_codex_skills(empty_dir, profile="auto")
        self.assertGreater(len(res.installed_skills), 0)
        self.assertEqual(res.skipped_existing, [])

    def test_install_codex_skills_merge_idempotency_and_uninstall(self):
        """Codex skills deployment exports valid SKILL.md files, merges idempotently, and cleans up safely."""

        # Pre-existing custom AGENTS.md, .codex/config.toml, and custom user skill
        custom_agents = Path(self.temp_dir) / "AGENTS.md"
        custom_agents.write_text("# Team Rules\nKeep API tests fast.\n", encoding="utf-8")
        codex_dir = Path(self.temp_dir) / ".codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        custom_toml = codex_dir / "config.toml"
        custom_toml.write_text('model = "gpt-5-codex"\n', encoding="utf-8")
        custom_skill_dir = Path(self.temp_dir) / ".agents" / "skills" / "custom-user-skill"
        custom_skill_dir.mkdir(parents=True, exist_ok=True)
        (custom_skill_dir / "SKILL.md").write_text("---\nname: custom-user-skill\ndescription: Custom\n---\n", encoding="utf-8")

        sp.install_universal_ai_bridges(self.temp_dir, ide="codex")
        res1 = sp.install_codex_skills(self.temp_dir, profile="full")
        self.assertGreaterEqual(len(res1.installed_skills), 57)
        self.assertIn("custom-user-skill", res1.skipped_existing)

        # Verify exported SKILL.md starts cleanly with YAML frontmatter '---'
        pom_skill = Path(self.temp_dir) / ".agents" / "skills" / "clean-pom-crafter" / "SKILL.md"
        solo_skill = Path(self.temp_dir) / ".agents" / "skills" / "solo" / "SKILL.md"
        self.assertTrue(pom_skill.is_file())
        self.assertTrue(solo_skill.is_file())
        self.assertTrue(solo_skill.read_text(encoding="utf-8").lstrip().startswith("---"))

        # Verify idempotent second run does not duplicate MCP or AGENTS sections
        sp.install_universal_ai_bridges(self.temp_dir, ide="codex")
        agents_after = custom_agents.read_text(encoding="utf-8")
        toml_after = custom_toml.read_text(encoding="utf-8")
        self.assertIn("Keep API tests fast.", agents_after)
        self.assertEqual(agents_after.count("SYNAPSE-HUB CLIENT AI BRIDGE TEMPLATE"), 1)
        self.assertIn('model = "gpt-5-codex"', toml_after)
        self.assertEqual(toml_after.count("[mcp_servers.synapse-hub]"), 1)

        # Uninstall cleans Synapse-managed skills and Synapse-templated Codex files, preserving user custom assets
        ret = sp.uninstall_setup(self.temp_dir)
        self.assertEqual(ret, 0)
        self.assertTrue((custom_skill_dir / "SKILL.md").is_file(), "Custom user skill must be preserved")
        self.assertFalse(pom_skill.exists(), "Synapse-managed skill should be removed on uninstall")
        self.assertTrue(custom_agents.is_file(), "Custom user-authored AGENTS.md should not be deleted")
        self.assertTrue(custom_toml.is_file(), "Custom user-authored .codex/config.toml should not be deleted")

        # Pure Synapse-created dir gets AGENTS.md and .codex/config.toml cleanly removed on uninstall
        pure_dir = tempfile.mkdtemp(prefix="codex_pure_")
        self.addCleanup(shutil.rmtree, pure_dir)
        sp.install_universal_ai_bridges(pure_dir, ide="codex")
        sp.install_codex_skills(pure_dir, profile="auto")
        self.assertEqual(sp.uninstall_setup(pure_dir), 0)
        self.assertFalse((Path(pure_dir) / "AGENTS.md").exists())
        self.assertFalse((Path(pure_dir) / ".codex" / "config.toml").exists())

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

    def test_codex_skills_auto_sync_on_stale_digest_and_mcp_startup(self):
        """Auto-sync refreshes managed .agents/skills/ when digest drifts while preserving custom skills and clean MCP stdio."""
        import io
        import json
        import sys
        from unittest import mock

        # Negative: Hub root and unmanaged workspace must never be touched
        hub_res = sp.auto_sync_codex_skills_if_stale(sp.HUB_ROOT)
        self.assertFalse(hub_res["synced"])
        self.assertEqual(hub_res["reason"], "hub_root_skipped")

        unmanaged_res = sp.auto_sync_codex_skills_if_stale(self.temp_dir)
        self.assertFalse(unmanaged_res["synced"])
        self.assertEqual(unmanaged_res["reason"], "not_managed")
        self.assertFalse((Path(self.temp_dir) / ".agents").exists())

        # Positive: initial install persists skills_digest; immediate auto-sync is a fast no-op
        custom_skill = Path(self.temp_dir) / ".agents" / "skills" / "team-custom-skill" / "SKILL.md"
        custom_skill.parent.mkdir(parents=True, exist_ok=True)
        custom_skill.write_text("---\nname: team-custom-skill\ndescription: Custom\n---\n", encoding="utf-8")

        sp.install_codex_skills(self.temp_dir, profile="auto")
        manifest_path = Path(self.temp_dir) / ".agents" / "skills" / ".synapse-managed.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertTrue(manifest.get("skills_digest"))
        self.assertEqual(manifest["skills_digest"], sp.compute_codex_skills_digest())

        noop_res = sp.auto_sync_codex_skills_if_stale(self.temp_dir)
        self.assertFalse(noop_res["synced"])
        self.assertEqual(noop_res["reason"], "up_to_date")

        # Boundary: opt-out env var skips sync even when digest is stale
        manifest["skills_digest"] = "stale_digest_v0"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        super_plan_skill = Path(self.temp_dir) / ".agents" / "skills" / "super-plan" / "SKILL.md"
        super_plan_skill.write_text("---\nname: super-plan\n---\nOUTDATED\n", encoding="utf-8")

        with mock.patch.dict(os.environ, {"SYNAPSE_AUTO_SYNC_SKILLS": "0"}):
            disabled_res = sp.auto_sync_codex_skills_if_stale(self.temp_dir)
            self.assertFalse(disabled_res["synced"])
            self.assertEqual(disabled_res["reason"], "disabled_by_env")
            self.assertIn("OUTDATED", super_plan_skill.read_text(encoding="utf-8"))

        # Positive: MCP stdio startup auto-syncs stale skills silently without polluting stdout
        from tools.mcp import mcp_server

        fake_stdout = io.StringIO()
        with (
            mock.patch.dict(os.environ, {"SYNAPSE_AUTO_SYNC_SKILLS": "1"}),
            mock.patch.object(os, "getcwd", return_value=self.temp_dir),
            mock.patch.object(sys, "stdin", io.StringIO("")),
            mock.patch.object(sys, "stdout", fake_stdout),
        ):
            mcp_server.run_stdio_server()

        self.assertEqual(fake_stdout.getvalue(), "", "Auto-sync must never write to MCP JSON-RPC stdout")
        refreshed_txt = super_plan_skill.read_text(encoding="utf-8")
        self.assertNotIn("OUTDATED", refreshed_txt)
        self.assertTrue(refreshed_txt.lstrip().startswith("---"))
        self.assertTrue(custom_skill.is_file(), "Custom user skill must remain untouched")
        updated_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(updated_manifest["skills_digest"], sp.compute_codex_skills_digest())

        # Negative: corrupt manifest JSON is recovered/handled cleanly without crash
        manifest_path.write_text("{corrupt json", encoding="utf-8")
        recovered_res = sp.auto_sync_codex_skills_if_stale(self.temp_dir)
        self.assertTrue(recovered_res["synced"])
        self.assertTrue(custom_skill.is_file())


if __name__ == "__main__":
    unittest.main()
