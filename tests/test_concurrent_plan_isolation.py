#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_concurrent_plan_isolation.py — 4-Scenario Suite for Concurrent Plan & Worktree Isolation
---------------------------------------------------------------------------------------------------
Verifies automatic slugged plan path generation (.synapse/plans/<slug>.md), collision-free
suffixing across concurrent chat sessions, active plan discovery, workspace concurrency
detection, .synapse/ review/harvester exemption, and CLI route/scaffold --output auto behavior.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class TestConcurrentPlanIsolation(unittest.TestCase):
    """Positive, Negative, Boundary, and CLI tests for collision-free multi-session planning."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Scenario 1: Positive
    # -------------------------------------------------------------------------
    def test_positive_slugged_plan_path_collision_avoidance_and_active_resolution(self):
        from tools.orchestration.solo_contracts import (
            build_plan_slug,
            resolve_active_plan_path,
            resolve_slugged_plan_path,
        )

        self.assertEqual(build_plan_slug("Add OAuth2 login flow"), "add-oauth2-login-flow")
        self.assertEqual(build_plan_slug("Thêm tính năng đăng nhập"), "them-tinh-nang-dang-nhap")

        first_path = resolve_slugged_plan_path("Add OAuth2 login flow", self.temp_dir)
        expected_first = os.path.join(self.temp_dir, ".synapse", "plans", "add-oauth2-login-flow.md")
        self.assertEqual(os.path.normpath(first_path), os.path.normpath(expected_first))

        # Simulate concurrent chat session 1 already wrote the plan
        os.makedirs(os.path.dirname(first_path), exist_ok=True)
        with open(first_path, "w", encoding="utf-8") as fh:
            fh.write("# Plan 1\n")

        second_path = resolve_slugged_plan_path("Add OAuth2 login flow", self.temp_dir)
        expected_second = os.path.join(self.temp_dir, ".synapse", "plans", "add-oauth2-login-flow-2.md")
        self.assertEqual(os.path.normpath(second_path), os.path.normpath(expected_second))

        with open(second_path, "w", encoding="utf-8") as fh:
            fh.write("# Plan 2\n")

        third_path = resolve_slugged_plan_path("Add OAuth2 login flow", self.temp_dir)
        expected_third = os.path.join(self.temp_dir, ".synapse", "plans", "add-oauth2-login-flow-3.md")
        self.assertEqual(os.path.normpath(third_path), os.path.normpath(expected_third))

        # Explicit path overrides slug generation
        explicit = resolve_slugged_plan_path("Add OAuth2 login flow", self.temp_dir, explicit_path="custom/plan.md")
        self.assertEqual(os.path.normpath(explicit), os.path.normpath(os.path.join(self.temp_dir, "custom", "plan.md")))

        # Non-.md files (even with newer mtime) and directories ending in .md must be ignored;
        # newer mtime must win regardless of alphabetical filename order
        plans_dir = os.path.dirname(first_path)
        os.makedirs(os.path.join(plans_dir, "ignored-dir.md"), exist_ok=True)
        notes_path = os.path.join(plans_dir, "notes.txt")
        with open(notes_path, "w", encoding="utf-8") as fh:
            fh.write("ignore me")
        now = time.time()
        os.utime(notes_path, (now + 60, now + 60))
        os.utime(first_path, (now + 20, now + 20))
        os.utime(second_path, (now - 20, now - 20))
        resolved_latest = resolve_active_plan_path(self.temp_dir)
        self.assertEqual(os.path.normpath(resolved_latest), os.path.normpath(first_path))

        with patch.dict(os.environ, {"SYNAPSE_ACTIVE_PLAN": second_path}):
            resolved_env = resolve_active_plan_path(self.temp_dir)
            self.assertEqual(os.path.normpath(resolved_env), os.path.normpath(second_path))

    def test_positive_concurrency_detection_and_scaffold_handoff_path(self):
        from tools.design.super_plan_engine import PlanningTier, scaffold_super_plan
        from tools.orchestration.plan_review_auditor import _EPHEMERAL_PREFIXES
        from tools.orchestration.solo_contracts import inspect_workspace_concurrency

        self.assertIn(".synapse/", _EPHEMERAL_PREFIXES)

        # Clean non-git or clean workspace
        with patch("tools.orchestration.solo_contracts._run_git_status_porcelain", return_value=[]):
            clean_info = inspect_workspace_concurrency(self.temp_dir, task="New feature")
            self.assertEqual(clean_info["concurrency_status"], "CLEAN")
            self.assertEqual(clean_info["active_plans"], [])
            self.assertTrue(clean_info["suggested_plan_path"].startswith(".synapse/plans/"))

        # Another active plan in .synapse/plans/ triggers CONCURRENT_SESSION_DETECTED
        plans_dir = os.path.join(self.temp_dir, ".synapse", "plans")
        os.makedirs(plans_dir, exist_ok=True)
        with open(os.path.join(plans_dir, "other-feature.md"), "w", encoding="utf-8") as fh:
            fh.write("# Other Feature\n")

        with patch("tools.orchestration.solo_contracts._run_git_status_porcelain", return_value=[" M tools/core/cli.py"]):
            busy_info = inspect_workspace_concurrency(self.temp_dir, task="Add OAuth2 login")
            self.assertEqual(busy_info["concurrency_status"], "CONCURRENT_SESSION_DETECTED")
            self.assertIn(".synapse/plans/other-feature.md", busy_info["active_plans"])
            self.assertIn("worktree create", busy_info["recommended_worktree_cmd"])

        plan_md = scaffold_super_plan(
            "Add OAuth2 login",
            ["tools/orchestration/solo_contracts.py"],
            tier=PlanningTier.TIER_0_FAST,
            plan_output_path=".synapse/plans/add-oauth2-login.md",
        )
        self.assertIn(".synapse/plans/add-oauth2-login.md", plan_md)
        self.assertIn("agent-qa solo --from-plan .synapse/plans/add-oauth2-login.md --json", plan_md)

    # -------------------------------------------------------------------------
    # Scenario 2: Negative (Error & Invalid Input Handling)
    # -------------------------------------------------------------------------
    def test_negative_empty_missing_and_non_git_degrade_gracefully(self):
        from types import SimpleNamespace
        from tools.orchestration.solo_contracts import (
            _run_git_status_porcelain,
            build_plan_slug,
            inspect_workspace_concurrency,
            resolve_active_plan_path,
        )

        self.assertEqual(build_plan_slug(""), "plan")
        self.assertEqual(build_plan_slug("   \t\n  "), "plan")
        self.assertEqual(build_plan_slug("!!!@@@###"), "plan")

        with patch.dict(os.environ, {"SYNAPSE_ACTIVE_PLAN": os.path.join(self.temp_dir, "missing.md")}):
            self.assertIsNone(resolve_active_plan_path(self.temp_dir))

        self.assertEqual(_run_git_status_porcelain(""), [])
        self.assertEqual(_run_git_status_porcelain(os.path.join(self.temp_dir, "no_such_dir")), [])

        def _fake_git_run(*args, **kwargs):
            self.assertIs(kwargs.get("capture_output"), True)
            self.assertIs(kwargs.get("text"), True)
            self.assertIs(kwargs.get("check"), False)
            return SimpleNamespace(returncode=0, stdout="?? .synapse/plans/draft.md\n M tools/core/cli.py\n")

        with patch("tools.orchestration.solo_contracts.subprocess.run", side_effect=_fake_git_run) as mock_git:
            dirty = _run_git_status_porcelain(self.temp_dir)
            self.assertEqual(dirty, [" M tools/core/cli.py"])
            self.assertTrue(mock_git.called)
        with patch(
            "tools.orchestration.solo_contracts.subprocess.run",
            return_value=SimpleNamespace(returncode=1, stdout=" M tools/core/cli.py\n"),
        ):
            self.assertEqual(_run_git_status_porcelain(self.temp_dir), [])

        info = inspect_workspace_concurrency(os.path.join(self.temp_dir, "does_not_exist"), task="")
        self.assertEqual(info["concurrency_status"], "CLEAN")
        self.assertEqual(info["active_plans"], [])
        self.assertEqual(info["dirty_files_count"], 0)

    # -------------------------------------------------------------------------
    # Scenario 3: Boundary (Long Slugs & Sequential Pipeline Non-Overwrite)
    # -------------------------------------------------------------------------
    def test_boundary_long_slug_clamping_and_pipeline_no_overwrite(self):
        from tools.design.super_plan_engine import PlanningTier, run_super_plan_pipeline
        from tools.orchestration.solo_contracts import build_plan_slug

        long_task = "Implement comprehensive zero trust authentication verification pipeline across distributed microservices " * 3
        slug = build_plan_slug(long_task, max_len=40)
        self.assertLessEqual(len(slug), 40)
        self.assertFalse(slug.endswith("-"))

        res1 = run_super_plan_pipeline(
            task="Harden stateless security isolation",
            target_files=["tools/orchestration/solo_contracts.py"],
            tier=PlanningTier.TIER_0_FAST,
            non_interactive=True,
            repo_root=self.temp_dir,
        )
        res2 = run_super_plan_pipeline(
            task="Harden stateless security isolation",
            target_files=["tools/orchestration/solo_contracts.py"],
            tier=PlanningTier.TIER_0_FAST,
            non_interactive=True,
            repo_root=self.temp_dir,
        )
        self.assertTrue(os.path.isfile(res1["plan_path"]))
        self.assertTrue(os.path.isfile(res2["plan_path"]))
        self.assertNotEqual(os.path.normpath(res1["plan_path"]), os.path.normpath(res2["plan_path"]))
        self.assertIn(os.path.join(".synapse", "plans"), res1["plan_path"])
        self.assertIn(os.path.join(".synapse", "plans"), res2["plan_path"])

    # -------------------------------------------------------------------------
    # Scenario 4: CLI Flags (route & scaffold --output auto --json)
    # -------------------------------------------------------------------------
    def test_cli_flags_route_concurrency_and_scaffold_auto_output_json(self):
        route_proc = subprocess.run(
            [
                sys.executable,
                os.path.join(REPO_ROOT, "tools", "design", "super_plan_engine.py"),
                "route",
                "--task",
                "Verify concurrent plan routing",
                "--files",
                "tools/orchestration/solo_contracts.py",
                "--json",
            ],
            cwd=self.temp_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        route_data = json.loads(route_proc.stdout)
        self.assertIn("suggested_plan_path", route_data)
        self.assertTrue(route_data["suggested_plan_path"].startswith(".synapse/plans/"))
        self.assertIn("concurrency_status", route_data)
        self.assertIn("recommended_worktree_cmd", route_data)

        scaff_proc = subprocess.run(
            [
                sys.executable,
                os.path.join(REPO_ROOT, "tools", "design", "super_plan_engine.py"),
                "scaffold",
                "--task",
                "Verify concurrent plan scaffold",
                "--files",
                "tools/orchestration/solo_contracts.py",
                "--tier",
                "fast",
                "--output",
                "auto",
                "--json",
            ],
            cwd=self.temp_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        scaff_data = json.loads(scaff_proc.stdout)
        self.assertIn("plan_path", scaff_data)
        self.assertIn("plan_rel_path", scaff_data)
        self.assertTrue(os.path.isfile(scaff_data["plan_path"]))
        self.assertIn(os.path.join(".synapse", "plans"), scaff_data["plan_path"])
        self.assertIn(scaff_data["plan_rel_path"].replace("\\", "/"), scaff_data["plan_markdown"].replace("\\", "/"))
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, "implementation_plan.md")))

    def test_worktree_create_copies_plan_links_deps_and_harvester_cleans_ephemeral(self):
        from types import SimpleNamespace
        from tools.core.git_worktree_manager import WorktreeManager
        from tools.design.plan_harvester import harvest_plan

        plans_dir = os.path.join(self.temp_dir, ".synapse", "plans")
        os.makedirs(plans_dir, exist_ok=True)
        plan_src = os.path.join(plans_dir, "feature-wt.md")
        with open(plan_src, "w", encoding="utf-8") as fh:
            fh.write(
                "# Plan: Feature WT\n\n"
                "## 1. Affected Files\n| Action | File | Scope |\n|---|---|---|\n"
                "| `[MODIFY]` | `tools/core/cli.py` | Dispatch |\n"
            )

        wt_base = os.path.join(self.temp_dir, ".synapse", "worktrees")
        mgr = WorktreeManager(base_dir=wt_base)

        def _fake_wt_git(args, cwd=None):
            if args[:2] == ["worktree", "add"]:
                os.makedirs(args[4], exist_ok=True)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with patch("tools.core.git_worktree_manager.run_git", side_effect=_fake_wt_git), patch(
            "tools.orchestration.worktree_manager.link_shared_dependencies",
            return_value={"linked": [".venv"], "errors": []},
        ) as mock_link:
            wt_res = mgr.create_worktree("feature-wt", plan_path=".synapse/plans/feature-wt.md")

        self.assertTrue(wt_res["success"])
        self.assertEqual(wt_res["copied_plan_path"], ".synapse/plans/feature-wt.md")
        self.assertTrue(os.path.isfile(os.path.join(wt_res["worktree_path"], ".synapse", "plans", "feature-wt.md")))
        self.assertEqual(wt_res["linked_dependencies"]["linked"], [".venv"])
        self.assertTrue(mock_link.called)

        adr_dir = os.path.join(self.temp_dir, "docs", "adr")
        # dry_run=True preserves ephemeral plan
        ok_dry, _, data_dry = harvest_plan(plan_src, adr_dir, dry_run=True, repo_root=self.temp_dir)
        self.assertTrue(ok_dry)
        self.assertFalse(data_dry["cleaned_up_plan"])
        self.assertTrue(os.path.isfile(plan_src))

        # dry_run=False automatically removes ephemeral .synapse/plans/*.md
        ok_real, _, data_real = harvest_plan(plan_src, adr_dir, dry_run=False, repo_root=self.temp_dir)
        self.assertTrue(ok_real)
        self.assertTrue(data_real["cleaned_up_plan"])
        self.assertFalse(os.path.exists(plan_src))


if __name__ == "__main__":
    unittest.main()
