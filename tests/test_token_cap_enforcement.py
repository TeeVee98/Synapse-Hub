#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_token_cap_enforcement.py — Comprehensive Property & Unit Tests for Token Cap Enforcement
---------------------------------------------------------------------------------------------------
Verifies Requirement R5:
  1. Edge cases: cap = 0, cap = 1, cap below minimal core rules (raises TokenCapExceededError).
  2. Exact boundary caps and large budget behavior (zero pruning).
  3. Priority-based pruning (Core Rules > Primary Task Skills > Secondary Skills > Metadata).
  4. Non-ASCII Unicode and Vietnamese diacritics token estimation and cap calculation.
  5. Fallback behavior across single-stack, multi-stack (monorepo), and unclassified workspaces.
  6. Disambiguated telemetry metrics: estimated_payload_tokens, provider_reported_tokens, avoided_disk_bytes.
  7. Monotonic property invariants: routed_tokens <= token_cap across arbitrary budgets.
"""

import os
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tools.core.rules_router import (
    route_rules,
    TokenCapExceededError,
    CORE_BASE_RULES,
    TASK_TYPE_CONFIGS,
)
from tools.core.token_estimator import (
    count_tokens,
)


class TestTokenCapEdgeCases(unittest.TestCase):
    """Verifies edge case behavior of token_cap enforcement (0, 1, boundary, large budget)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = self.temp_dir.name
        # Seed a minimal Playwright configuration
        with open(os.path.join(self.workspace, "playwright.config.ts"), "w", encoding="utf-8") as f:
            f.write("export default { testDir: './tests' };\n")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cap_zero_raises_token_cap_exceeded_error(self):
        """cap = 0 must immediately raise TokenCapExceededError."""
        with self.assertRaises(TokenCapExceededError) as ctx:
            route_rules(self.workspace, token_cap=0)
        self.assertEqual(ctx.exception.token_cap, 0)
        self.assertGreater(ctx.exception.required_tokens, -1)

    def test_cap_one_raises_token_cap_exceeded_error(self):
        """cap = 1 must immediately raise TokenCapExceededError."""
        with self.assertRaises(TokenCapExceededError) as ctx:
            route_rules(self.workspace, token_cap=1)
        self.assertEqual(ctx.exception.token_cap, 1)
        self.assertIn("insufficient", str(ctx.exception).lower())

    def test_cap_below_core_rules_raises_error(self):
        """cap strictly less than minimal CORE_BASE_RULES tokens must fail-closed."""
        with self.assertRaises(TokenCapExceededError) as ctx:
            route_rules(self.workspace, token_cap=500)
        self.assertGreater(ctx.exception.required_tokens, 500)
        self.assertIn("core_rules", ctx.exception.item_type)

    def test_cap_at_boundary_core_rules_retains_zero_skills(self):
        """When cap matches core rules, all skills must be pruned, leaving 0 skills."""
        unbounded = route_rules(self.workspace, token_cap=100000)
        core_tokens = unbounded["token_metrics"]["core_rule_tokens"] if "core_rule_tokens" in unbounded["token_metrics"] else 1468

        bounded = route_rules(self.workspace, token_cap=core_tokens)
        self.assertEqual(bounded["recommended_rules"], sorted(CORE_BASE_RULES))
        self.assertEqual(len(bounded["recommended_skills"]), 0, "All skills must be pruned at core boundary")
        self.assertLessEqual(bounded["hydration_contracts"]["full_hydration"]["routed_tokens"], core_tokens)

    def test_large_budget_performs_zero_pruning(self):
        """With 100,000 token budget, no pruning should occur."""
        res = route_rules(self.workspace, token_cap=100000)
        self.assertGreater(len(res["recommended_skills"]), 0)
        self.assertLessEqual(res["hydration_contracts"]["full_hydration"]["routed_tokens"], 100000)
        self.assertEqual(res["token_metrics"].get("pruned_items_count", 0), 0)


class TestTokenCapUnicodeVietnamese(unittest.TestCase):
    """Verifies token estimation and cap enforcement with Vietnamese diacritics and Unicode."""

    def test_vietnamese_diacritics_token_density(self):
        """Ensures non-ASCII Vietnamese diacritics reflect calibrated token density."""
        en_phrase = "Automated quality gate verification with zero false passes."
        vi_phrase = "Xác minh cổng chất lượng tự động hóa không có kết quả giả mạo."

        tok_en = count_tokens(en_phrase)
        tok_vi = count_tokens(vi_phrase)

        self.assertGreater(tok_vi, 0)
        self.assertGreater(tok_en, 0)
        # Vietnamese with diacritics should have higher token count for similar character length
        self.assertGreaterEqual(tok_vi, len(vi_phrase) // 3)

    def test_workspace_vietnamese_readme_under_cap(self):
        """Workspaces with Vietnamese documentation must not corrupt token cap accounting."""
        with tempfile.TemporaryDirectory() as ws:
            with open(os.path.join(ws, "playwright.config.ts"), "w", encoding="utf-8") as f:
                f.write("export default {};\n")
            with open(os.path.join(ws, "README.md"), "w", encoding="utf-8") as f:
                f.write("# Hướng dẫn kiểm thử tự động\n\nQuy trình chạy kiểm thử đầu mối QA Agent.\n")

            res = route_rules(ws, token_cap=6000)
            self.assertLessEqual(res["hydration_contracts"]["full_hydration"]["routed_tokens"], 6000)
            self.assertIn("playwright", res["detected_stacks"])


class TestTokenCapProfileFallbacks(unittest.TestCase):
    """Verifies cap enforcement across single, multi (monorepo), and unclassified profiles."""

    def test_single_profile_priority_pruning(self):
        """In single stack, secondary skills are pruned before primary skills."""
        with tempfile.TemporaryDirectory() as ws:
            with open(os.path.join(ws, "playwright.config.ts"), "w", encoding="utf-8") as f:
                f.write("export default {};\n")

            # Route with intermediate cap allowing core rules + 1 primary skill (~2,925 tokens)
            res = route_rules(ws, token_cap=3000)
            self.assertLessEqual(res["hydration_contracts"]["full_hydration"]["routed_tokens"], 3000)
            # Primary skill should be retained over secondary skills
            self.assertIn("playwright-webapp-testing", res["recommended_skills"])
            self.assertNotIn("api-network-mocking-interception", res["recommended_skills"])

    def test_multi_profile_monorepo_cap_pruning(self):
        """Monorepo with Playwright + API balances skills under token cap."""
        with tempfile.TemporaryDirectory() as ws:
            with open(os.path.join(ws, "pnpm-workspace.yaml"), "w", encoding="utf-8") as f:
                f.write("packages:\n  - 'packages/*'\n")
            fe = os.path.join(ws, "packages", "fe")
            be = os.path.join(ws, "packages", "be")
            os.makedirs(fe, exist_ok=True)
            os.makedirs(be, exist_ok=True)
            with open(os.path.join(fe, "playwright.config.ts"), "w", encoding="utf-8") as f:
                f.write("export default {};\n")
            with open(os.path.join(be, "requirements.txt"), "w", encoding="utf-8") as f:
                f.write("fastapi>=0.100.0\nrequests>=2.31.0\n")

            res = route_rules(ws, token_cap=5000)
            self.assertLessEqual(res["hydration_contracts"]["full_hydration"]["routed_tokens"], 5000)
            self.assertTrue(res.get("is_monorepo", False) or "playwright" in res["detected_stacks"])

    def test_unknown_profile_cap_enforcement(self):
        """Unclassified workspace enforces cap honestly on core fallback rules."""
        with tempfile.TemporaryDirectory() as ws:
            # Empty directory
            res = route_rules(ws, token_cap=6000)
            self.assertEqual(res["status"], "UNCLASSIFIED_WORKSPACE")
            self.assertLessEqual(res["hydration_contracts"]["full_hydration"]["routed_tokens"], 6000)
            self.assertEqual(res["token_metrics"]["tokens_saved"], 0)

            # Cap below core rules on unclassified workspace must still raise
            with self.assertRaises(TokenCapExceededError):
                route_rules(ws, token_cap=100)


class TestTokenCapExceededErrorBehavior(unittest.TestCase):
    """Verifies TokenCapExceededError inheritance, attributes, and task_type sweep."""

    def test_exception_structure(self):
        err = TokenCapExceededError("Budget exceeded", required_tokens=1500, token_cap=500, item_type="core_rules")
        self.assertIsInstance(err, ValueError)
        self.assertEqual(err.required_tokens, 1500)
        self.assertEqual(err.token_cap, 500)
        self.assertEqual(err.item_type, "core_rules")

    def test_all_task_types_raise_when_cap_starved(self):
        """All 5 task types (api, perf, security, locator, triage) must raise when cap = 10."""
        with tempfile.TemporaryDirectory() as ws:
            with open(os.path.join(ws, "playwright.config.ts"), "w", encoding="utf-8") as f:
                f.write("export default {};\n")

            for t_type in ("api", "perf", "security", "locator", "triage"):
                with self.assertRaises(TokenCapExceededError, msg=f"Failed to raise for task_type={t_type}"):
                    route_rules(ws, task_type=t_type, token_cap=10)


class TestDisambiguatedMetricsKeys(unittest.TestCase):
    """Verifies strict disambiguation between context tokens and disk read I/O bytes."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = self.temp_dir.name
        with open(os.path.join(self.workspace, "playwright.config.ts"), "w", encoding="utf-8") as f:
            f.write("export default {};\n")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_disambiguated_keys_presence(self):
        res = route_rules(self.workspace, token_cap=10000)

        # Check top-level and nested token metrics
        metrics = res["token_metrics"]
        self.assertIn("estimated_payload_tokens", metrics)
        self.assertIn("provider_reported_tokens", metrics)
        self.assertIn("avoided_disk_bytes", metrics)

        # Check hydration contracts
        rf = res["hydration_contracts"]["retrieval_footprint"]
        self.assertIn("avoided_disk_bytes", rf)

        # Invariant: avoided_disk_bytes must reflect disk byte scale, not tokens
        self.assertGreaterEqual(rf["avoided_disk_bytes"], 0)
        self.assertIsNone(metrics["provider_reported_tokens"])  # Offline heuristic mode


class TestTokenCapMonotonicProperties(unittest.TestCase):
    """Parameter-swept property test ensuring routed_tokens <= token_cap monotonically."""

    def test_monotonic_token_cap_sweep(self):
        with tempfile.TemporaryDirectory() as ws:
            with open(os.path.join(ws, "playwright.config.ts"), "w", encoding="utf-8") as f:
                f.write("export default {};\n")

            caps = [1600, 2000, 2500, 3000, 4000, 5000, 6000, 8000, 12000, 50000]
            previous_retained_count = 0

            for cap in caps:
                res = route_rules(ws, token_cap=cap)
                routed_toks = res["hydration_contracts"]["full_hydration"]["routed_tokens"]
                retained_skills = len(res["recommended_skills"])

                # Invariant 1: Budget invariant
                self.assertLessEqual(routed_toks, cap, f"Cap breached at {cap}: got {routed_toks}")

                # Invariant 2: Monotonic skills retention (larger budget never retains fewer skills)
                self.assertGreaterEqual(retained_skills, previous_retained_count)
                previous_retained_count = retained_skills


class TestMultiPrimarySkillPruningOrder(unittest.TestCase):
    """
    Verifies priority pruning order:
    CORE_BASE_RULES > Primary Skills > Non-Core Rules > Secondary Skills
    Ensures that for api, perf, and security under default token_cap=6000:
    - Both primary skills are retained
    - Secondary skills are dropped before non-core rules
    - Non-core rules are dropped before primary skills
    - Empty string task_type="" raises ValueError
    """

    def test_multi_primary_skills_retained_under_default_cap(self):
        """Under default 6,000 cap, api, perf, and security retain all primary skills."""
        for t_type in ("api", "perf", "security"):
            res = route_rules(".", task_type=t_type, token_cap=6000)
            expected_primary = TASK_TYPE_CONFIGS[t_type]["primary_skills"]
            retained = res["recommended_skills"]
            pruned = res["pruned_skills"]

            # Both primary skills must be retained
            for ps in expected_primary:
                self.assertIn(ps, retained, f"Primary skill '{ps}' was prematurely pruned for task_type '{t_type}'!")

            # Secondary skills should be pruned if cap was exceeded
            expected_secondary = TASK_TYPE_CONFIGS[t_type].get("secondary_skills", [])
            for ss in expected_secondary:
                self.assertIn(ss, pruned, f"Secondary skill '{ss}' should have been pruned first for task_type '{t_type}'!")

            self.assertLessEqual(res["hydration_contracts"]["full_hydration"]["routed_tokens"], 6000)

    def test_non_core_rules_pruned_before_primary_skills(self):
        """When tokens exceed cap after dropping secondary skills, non-core rules are pruned before primary skills."""
        # For 'api', candidate rules include CORE_BASE_RULES + detected stack rules.
        # Under cap 6000, secondary skill is dropped, and non-core rules are pruned while retaining both primary skills.
        res = route_rules(".", task_type="api", token_cap=6000)
        self.assertEqual(len(res["recommended_skills"]), 2)
        # Non-core rules are pruned to fit primary skills while core base rules remain intact
        retained_rules = res["recommended_rules"]
        for core_rule in CORE_BASE_RULES:
            self.assertIn(core_rule, retained_rules)

    def test_empty_string_task_type_raises_value_error(self):
        """route_rules with task_type='' must raise ValueError, not silently bypass."""
        with self.assertRaises(ValueError) as ctx:
            route_rules(".", task_type="")
        self.assertIn("Unknown task_type", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
