#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_router_token_cap_contract.py — Comprehensive Contract Tests for Router & Token-Cap
---------------------------------------------------------------------------------------------
Verifies:
  1. Matrix tests for all task types (api, perf, security, locator, triage, None) across
     workspace states (empty, unknown, known single-stack, conflicting markers, monorepo multi-stack).
  2. Unknown workspaces receive task-specific rules and primary skills when task_type is provided.
  3. Real hard floor definition: when token_cap < floor, raises TokenCapExceededError (or partial if requested);
     mandatory skills are NEVER silently dropped to report false success.
  4. Boundary tests at cap = floor - 1, floor, floor + 1 with non-contradictory metrics.
  5. Recalculated metrics: catalog_summary_tokens, estimated_hydration_tokens, token_cap,
     measurement_kind, and explicit disclaimer that cap excludes host system prompt / provider wrapper.
  6. Cache invalidation: modifying skills_manifest content while freezing mtime (via os.utime)
     guarantees cache invalidation via SHA-256 content digest.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tools.rules_router import (
    route_rules,
    TokenCapExceededError,
    CORE_BASE_RULES,
    TASK_TYPE_CONFIGS,
    _find_repo_root,
)
from tools.core.token_estimator import (
    calculate_hydration_payload,
    _get_skills_manifest,
    clear_skills_manifest_cache,
)


class TestRouterTaskWorkspaceMatrix(unittest.TestCase):
    """Matrix tests for all task types across empty, unknown, known, conflicting, and monorepo workspaces."""

    def setUp(self):
        self.temp_base = tempfile.mkdtemp(prefix="test_router_matrix_")
        self.workspaces = {}

        # 1. Empty workspace
        ws_empty = os.path.join(self.temp_base, "empty")
        os.makedirs(ws_empty, exist_ok=True)
        self.workspaces["empty"] = ws_empty

        # 2. Unknown workspace (non-test files e.g. C / Makefile / docs)
        ws_unknown = os.path.join(self.temp_base, "unknown")
        os.makedirs(ws_unknown, exist_ok=True)
        with open(os.path.join(ws_unknown, "main.c"), "w", encoding="utf-8") as f:
            f.write("int main() { return 0; }\n")
        with open(os.path.join(ws_unknown, "Makefile"), "w", encoding="utf-8") as f:
            f.write("all:\n\tgcc main.c\n")
        with open(os.path.join(ws_unknown, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Embedded Project\n")
        self.workspaces["unknown"] = ws_unknown

        # 3. Known single-stack (Playwright)
        ws_known = os.path.join(self.temp_base, "known")
        os.makedirs(ws_known, exist_ok=True)
        with open(os.path.join(ws_known, "playwright.config.ts"), "w", encoding="utf-8") as f:
            f.write("export default { testDir: './tests' };\n")
        self.workspaces["known_single"] = ws_known

        # 4. Conflicting markers (Cypress + Playwright + Selenium)
        ws_conflicting = os.path.join(self.temp_base, "conflicting")
        os.makedirs(ws_conflicting, exist_ok=True)
        with open(os.path.join(ws_conflicting, "playwright.config.ts"), "w", encoding="utf-8") as f:
            f.write("export default {};\n")
        with open(os.path.join(ws_conflicting, "cypress.json"), "w", encoding="utf-8") as f:
            f.write("{}\n")
        with open(os.path.join(ws_conflicting, "wdio.conf.js"), "w", encoding="utf-8") as f:
            f.write("exports.config = {};\n")
        self.workspaces["conflicting"] = ws_conflicting

        # 5. Monorepo multi-stack (pnpm-workspace with fe=playwright, be=perf/locust, api=openapi)
        ws_monorepo = os.path.join(self.temp_base, "monorepo")
        os.makedirs(ws_monorepo, exist_ok=True)
        with open(os.path.join(ws_monorepo, "pnpm-workspace.yaml"), "w", encoding="utf-8") as f:
            f.write("packages:\n  - 'packages/*'\n")
        fe_dir = os.path.join(ws_monorepo, "packages", "fe")
        be_dir = os.path.join(ws_monorepo, "packages", "be")
        api_dir = os.path.join(ws_monorepo, "packages", "api")
        os.makedirs(fe_dir, exist_ok=True)
        os.makedirs(be_dir, exist_ok=True)
        os.makedirs(api_dir, exist_ok=True)
        with open(os.path.join(fe_dir, "playwright.config.ts"), "w", encoding="utf-8") as f:
            f.write("export default {};\n")
        with open(os.path.join(be_dir, "locustfile.py"), "w", encoding="utf-8") as f:
            f.write("from locust import HttpUser, task\n")
        with open(os.path.join(api_dir, "openapi.yaml"), "w", encoding="utf-8") as f:
            f.write("openapi: 3.0.0\ninfo:\n  title: API\n  version: 1.0\n")
        self.workspaces["monorepo_multi"] = ws_monorepo

    def tearDown(self):
        shutil.rmtree(self.temp_base, ignore_errors=True)

    def test_full_matrix_task_type_and_workspace_states(self):
        """Matrix test: all 5 task types + None across all 5 workspace archetypes."""
        task_types = [None, "locator", "triage", "api", "perf", "security"]

        for ws_name, ws_path in self.workspaces.items():
            for t_type in task_types:
                with self.subTest(workspace=ws_name, task_type=t_type):
                    result = route_rules(ws_path, task_type=t_type)

                    # Invariant 1: Result must contain core structure
                    self.assertIn("status", result)
                    self.assertIn("recommended_rules", result)
                    self.assertIn("recommended_skills", result)
                    self.assertIn("token_metrics", result)
                    self.assertIn("hydration_contracts", result)

                    # Invariant 2: CORE_BASE_RULES are always present in recommended_rules
                    for core_r in CORE_BASE_RULES:
                        self.assertIn(core_r, result["recommended_rules"])

                    # Invariant 3: If task_type is provided, primary skills and task rules must be present
                    if t_type is not None:
                        cfg = TASK_TYPE_CONFIGS[t_type]
                        # Verify primary skills
                        for ps in cfg["primary_skills"]:
                            self.assertIn(
                                ps,
                                result["recommended_skills"],
                                f"Task '{t_type}' lost primary skill '{ps}' on workspace '{ws_name}'",
                            )
                        # Verify task rules
                        for tr in cfg.get("rules", []):
                            self.assertIn(
                                tr,
                                result["recommended_rules"],
                                f"Task '{t_type}' lost task rule '{tr}' on workspace '{ws_name}'",
                            )

                    # Invariant 4: Classification honesty
                    if ws_name in ("empty", "unknown"):
                        if t_type is None:
                            self.assertEqual(result["status"], "UNCLASSIFIED_WORKSPACE")
                            self.assertEqual(result["recommended_skills"], [])
                            self.assertEqual(result["token_metrics"]["tokens_saved"], 0)
                        else:
                            self.assertEqual(result["status"], "UNCLASSIFIED_WORKSPACE")
                            self.assertIn(f"Task: {t_type}", result["classification"])
                    elif ws_name == "known_single":
                        self.assertIn("playwright", result["detected_stacks"])
                    elif ws_name == "conflicting":
                        self.assertGreaterEqual(len(result["detected_stacks"]), 2)
                    elif ws_name == "monorepo_multi":
                        self.assertTrue(result.get("is_monorepo") or len(result["detected_stacks"]) >= 2)


class TestHardFloorAndBoundaryCorrectness(unittest.TestCase):
    """Verifies the true hard floor and boundary behavior at cap = floor - 1, floor, floor + 1."""

    def setUp(self):
        self.repo_root = _find_repo_root()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ws = self.temp_dir.name
        # Seed an empty workspace
        with open(os.path.join(self.ws, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Project\n")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_untyped_boundary_floor_minus_one_exact_and_plus_one(self):
        """Untyped route (task_type=None) boundary tests at floor-1, floor, floor+1."""
        core_payload = calculate_hydration_payload(self.repo_root, sorted(CORE_BASE_RULES), [])
        floor = core_payload["rule_tokens"]

        # 1. cap = floor - 1 must raise TokenCapExceededError
        with self.assertRaises(TokenCapExceededError) as ctx:
            route_rules(self.ws, task_type=None, token_cap=floor - 1)
        self.assertEqual(ctx.exception.required_tokens, floor)
        self.assertEqual(ctx.exception.token_cap, floor - 1)
        self.assertEqual(ctx.exception.item_type, "core_rules")

        # 2. cap = floor must pass and retain exact CORE_BASE_RULES with 0 skills
        res_exact = route_rules(self.ws, task_type=None, token_cap=floor)
        self.assertEqual(res_exact["recommended_rules"], sorted(CORE_BASE_RULES))
        self.assertEqual(res_exact["recommended_skills"], [])
        self.assertEqual(res_exact["token_metrics"]["estimated_hydration_tokens"], floor)

        # 3. cap = floor + 1 must pass
        res_plus = route_rules(self.ws, task_type=None, token_cap=floor + 1)
        self.assertLessEqual(res_plus["token_metrics"]["estimated_hydration_tokens"], floor + 1)

    def test_task_types_boundary_floor_minus_one_exact_and_plus_one(self):
        """All 5 task types boundary tests at floor-1, floor, floor+1."""
        for t_type, cfg in TASK_TYPE_CONFIGS.items():
            primary = cfg["primary_skills"]
            floor_payload = calculate_hydration_payload(self.repo_root, sorted(CORE_BASE_RULES), primary)
            floor = floor_payload["total_hydrated_tokens"]

            with self.subTest(task_type=t_type, floor=floor):
                # Boundary 1: cap = floor - 1 must fail fast with structured TokenCapExceededError
                with self.assertRaises(TokenCapExceededError) as ctx:
                    route_rules(self.ws, task_type=t_type, token_cap=floor - 1)
                self.assertEqual(ctx.exception.required_tokens, floor)
                self.assertEqual(ctx.exception.token_cap, floor - 1)
                self.assertEqual(ctx.exception.item_type, "mandatory_skills")

                # Boundary 2: cap = floor must succeed and retain ALL primary skills
                res_exact = route_rules(self.ws, task_type=t_type, token_cap=floor)
                for ps in primary:
                    self.assertIn(ps, res_exact["recommended_skills"],
                                  f"Mandatory skill '{ps}' was lost at exact floor for task '{t_type}'!")
                self.assertEqual(res_exact["token_metrics"]["estimated_hydration_tokens"], floor)
                self.assertEqual(res_exact["recommended_rules"], sorted(CORE_BASE_RULES))

                # Boundary 3: cap = floor + 1 must succeed and retain ALL primary skills
                res_plus = route_rules(self.ws, task_type=t_type, token_cap=floor + 1)
                for ps in primary:
                    self.assertIn(ps, res_plus["recommended_skills"])
                self.assertLessEqual(res_plus["token_metrics"]["estimated_hydration_tokens"], floor + 1)

    def test_mandatory_skills_never_silently_pruned_to_empty(self):
        """
        Critical Contract: A task profile must NEVER silently drop mandatory primary skills
        and return route success with an empty skill list when cap is starved.
        """
        for t_type in ("api", "perf", "security", "locator", "triage"):
            # Set cap strictly between core rules floor (~1468) and task floor (>2400)
            starved_cap = 2000
            with self.assertRaises(TokenCapExceededError, msg=f"Silent drop permitted for task={t_type}"):
                route_rules(self.ws, task_type=t_type, token_cap=starved_cap)

    def test_allow_partial_returns_explicit_partial_status(self):
        """When allow_partial=True and cap < floor, returns PARTIAL_CAP_EXCEEDED instead of raising."""
        res = route_rules(self.ws, task_type="api", token_cap=2000, allow_partial=True)
        self.assertEqual(res["status"], "PARTIAL_CAP_EXCEEDED")
        self.assertIn("PARTIAL_CAP_EXCEEDED", res["classification"])
        self.assertIn("partial_reason", res["token_metrics"])


class TestMetricsConsistencyAndDisclaimers(unittest.TestCase):
    """Verifies that all 4 required token metric keys are present, non-contradictory, and documented."""

    def test_metrics_keys_and_host_prompt_disclaimer(self):
        """Verifies catalog_summary_tokens, estimated_hydration_tokens, token_cap, measurement_kind."""
        res = route_rules(".", task_type="api", token_cap=6000)
        metrics = res["token_metrics"]

        # Required 4 keys
        self.assertIn("catalog_summary_tokens", metrics)
        self.assertIn("estimated_hydration_tokens", metrics)
        self.assertIn("token_cap", metrics)
        self.assertIn("measurement_kind", metrics)
        self.assertEqual(metrics["token_cap"], 6000)

        # Mathematical consistency: catalog summary <= estimated hydration
        self.assertGreater(metrics["catalog_summary_tokens"], 0)
        self.assertGreater(metrics["estimated_hydration_tokens"], metrics["catalog_summary_tokens"])
        self.assertLessEqual(metrics["estimated_hydration_tokens"], 6000)

        # Hard floor and core rule tokens presence
        self.assertIn("hard_floor_tokens", metrics)
        self.assertIn("core_rule_tokens", metrics)
        self.assertGreater(metrics["hard_floor_tokens"], metrics["core_rule_tokens"])

        # Cap excludes host system prompt / provider wrapper disclaimer
        self.assertTrue(metrics.get("cap_excludes_system_prompt_and_wrapper"))
        self.assertIn("system prompt", metrics["note"].lower())


class TestManifestCacheInvalidationSameMtime(unittest.TestCase):
    """
    Verifies that modifying skills_manifest.json content while freezing mtime (via os.utime)
    invalidates the in-memory cache using the SHA-256 content digest.
    """

    def setUp(self):
        clear_skills_manifest_cache()
        self.temp_dir = tempfile.mkdtemp(prefix="test_manifest_cache_")

    def tearDown(self):
        clear_skills_manifest_cache()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_invalidates_on_content_change_with_identical_mtime(self):
        """Manifest content change must invalidate cache even if mtime is artificially frozen."""
        manifest_path = os.path.join(self.temp_dir, "skills_manifest.json")

        # 1. Initial manifest version
        data_v1 = {
            "skills": [
                {"id": "skill-alpha", "name": "Alpha Skill", "description": "Version 1"}
            ]
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(data_v1, f)

        # Record initial mtime
        initial_mtime = os.path.getmtime(manifest_path)

        # First query -> must return skill-alpha
        m1 = _get_skills_manifest(self.temp_dir)
        self.assertIn("skill-alpha", m1)
        self.assertEqual(m1["skill-alpha"]["description"], "Version 1")

        # 2. Mutate manifest content in-place with different skill
        data_v2 = {
            "skills": [
                {"id": "skill-beta", "name": "Beta Skill", "description": "Version 2"}
            ]
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(data_v2, f)

        # Artificially freeze mtime back to initial_mtime (same mtime)
        os.utime(manifest_path, (initial_mtime, initial_mtime))
        self.assertEqual(os.path.getmtime(manifest_path), initial_mtime)

        # 3. Second query -> must detect content change and return skill-beta, NOT stale skill-alpha!
        m2 = _get_skills_manifest(self.temp_dir)
        self.assertNotIn("skill-alpha", m2, "Stale cache was returned despite content change!")
        self.assertIn("skill-beta", m2, "Updated manifest content was not loaded!")
        self.assertEqual(m2["skill-beta"]["description"], "Version 2")


if __name__ == "__main__":
    unittest.main()
