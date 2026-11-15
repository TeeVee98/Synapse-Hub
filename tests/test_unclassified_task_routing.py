#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/test_unclassified_task_routing.py — Integration Tests for Task Routing on Unclassified Workspaces
-------------------------------------------------------------------------------------------------------
Verifies:
  1. Empty/unclassified workspace with each task_type (api, perf, security, locator, triage)
     correctly retains the task-specific profile (primary skills and task rules).
  2. Boundary cap testing at floor-1 (raises TokenCapExceededError), floor (exact core rules),
     and floor+1 (valid hydration estimate).
  3. Total hydration estimate and reporting fields are mutually consistent and non-contradictory.
  4. Disambiguated metrics contain measurement_kind (static_estimate / synthetic),
     tokenizer_or_model, measurement_source, and context_scope.
"""

import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from tools.rules_router import (
    route_rules,
    TokenCapExceededError,
    CORE_BASE_RULES,
    TASK_TYPE_CONFIGS,
    _find_repo_root,
)
from tools.core.token_estimator import calculate_hydration_payload


class TestUnclassifiedTaskRouting(unittest.TestCase):
    """Integration test suite for unclassified workspace task routing and cap boundaries."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.empty_ws = self.temp_dir.name
        self.repo_root = _find_repo_root()
        core_payload = calculate_hydration_payload(self.repo_root, sorted(CORE_BASE_RULES), [])
        self.floor = core_payload["rule_tokens"]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_all_task_types_retain_task_profile_on_empty_workspace(self):
        """Empty workspace with explicit task_type must retain task-specific primary skills."""
        for t_type, cfg in TASK_TYPE_CONFIGS.items():
            routed = route_rules(self.empty_ws, task_type=t_type)
            self.assertEqual(routed["task_type"], t_type)
            self.assertEqual(routed["status"], "UNCLASSIFIED_WORKSPACE")
            self.assertIn("Task: " + t_type, routed["classification"])

            # Verify primary skills are retained
            for ps in cfg["primary_skills"]:
                self.assertIn(ps, routed["recommended_skills"],
                              f"Task '{t_type}' did not retain primary skill '{ps}' on empty workspace")

            # Verify rules include both CORE_BASE_RULES and task rules
            for cr in CORE_BASE_RULES:
                self.assertIn(cr, routed["recommended_rules"])
            for tr in cfg.get("rules", []):
                self.assertIn(tr, routed["recommended_rules"])

    def test_floor_minus_one_raises_structured_error(self):
        """Cap at floor - 1 must raise TokenCapExceededError with structured attributes."""
        with self.assertRaises(TokenCapExceededError) as ctx:
            route_rules(self.empty_ws, token_cap=self.floor - 1)
        err = ctx.exception
        self.assertEqual(err.item_type, "core_rules")
        self.assertEqual(err.token_cap, self.floor - 1)
        self.assertEqual(err.required_tokens, self.floor)

    def test_floor_boundary_retains_core_rules_zero_skills(self):
        """Cap exactly at floor must retain CORE_BASE_RULES and prune all skills."""
        routed = route_rules(self.empty_ws, token_cap=self.floor)
        self.assertEqual(routed["recommended_rules"], sorted(CORE_BASE_RULES))
        self.assertEqual(routed["recommended_skills"], [])
        self.assertLessEqual(routed["hydration_contracts"]["full_hydration"]["routed_tokens"], self.floor)

    def test_floor_plus_one_retains_core_rules_consistently(self):
        """Cap at floor + 1 must retain CORE_BASE_RULES and provide non-contradictory metrics."""
        routed = route_rules(self.empty_ws, token_cap=self.floor + 1)
        self.assertLessEqual(routed["hydration_contracts"]["full_hydration"]["routed_tokens"], self.floor + 1)
        self.assertEqual(routed["recommended_rules"], sorted(CORE_BASE_RULES))

    def test_hydration_estimates_non_contradictory(self):
        """Verify summary and full hydration token metrics do not contradict each other."""
        for t_type in TASK_TYPE_CONFIGS:
            routed = route_rules(self.empty_ws, task_type=t_type)
            cat = routed["hydration_contracts"]["catalog_summary"]
            hyd = routed["hydration_contracts"]["full_hydration"]
            rf = routed["hydration_contracts"]["retrieval_footprint"]

            # Mathematical consistency: full hydration tokens >= catalog summary tokens
            self.assertGreaterEqual(hyd["routed_tokens"], cat["routed_tokens"])
            self.assertGreaterEqual(hyd["baseline_tokens"], cat["baseline_tokens"])

            # Consistency between token_metrics and hydration_contracts
            metrics = routed["token_metrics"]
            self.assertEqual(metrics["routed_tokens"], cat["routed_tokens"])
            self.assertEqual(metrics["estimated_payload_tokens"], hyd["routed_tokens"])

            # Measurement kind fields presence
            self.assertIn(metrics["measurement_kind"], ("static_estimate", "synthetic"))
            self.assertIn(cat["measurement_kind"], ("static_estimate", "synthetic"))
            self.assertIn(hyd["measurement_kind"], ("static_estimate", "synthetic"))
            self.assertEqual(rf["measurement_kind"], "synthetic")

            # Provider reported tokens must be None (no ungrounded provider savings claims)
            self.assertIsNone(metrics["provider_reported_tokens"])
            self.assertIsNone(hyd["provider_reported_tokens"])

            # Tokenizer and source presence
            self.assertTrue(bool(metrics["tokenizer_or_model"]))
            self.assertEqual(metrics["measurement_source"], "offline_token_estimator")
            self.assertEqual(metrics["context_scope"], "hydrated_documentation_and_rules")


if __name__ == "__main__":
    unittest.main()
