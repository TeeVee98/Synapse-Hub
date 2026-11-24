#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_gate_11_all_15_tiers.py — Verification of Gate 11 across all 15 Tiers
--------------------------------------------------------------------------------
Validates that Gate 11 verifies all 15 token reduction and intelligence tiers:
  - Tiers 1-10: Baseline Token Reduction Architecture
  - Tier 11: Repo Speculative Decoding & Prompt Lookup
  - Tier 12: Kolmogorov-Minimal Symbolic Micro-DSL
  - Tier 13: Logprob-Triggered Prefix Branching
  - Tier 14: Boundary Counterfactual Few-Shot Distiller
  - Tier 15: Neuro-Symbolic Constraint Offloading
"""

import json
import os
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.context.high_density_encoder import HighDensityEncoder
from tools.core.gates.base import LAST_GATE_METRICS
from tools.core.gates.gate_11_token_reduction import Gate11TokenReduction, gate_11_token_reduction
from tools.mcp.synapse_meta_mcp import SynapseMetaMCPServer


class TestGate11All15Tiers(unittest.TestCase):
    """Test Suite verifying Gate 11 checks all 15 Tiers with Core-6 behavioral assertions."""

    def setUp(self) -> None:
        self.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_gate_11_verifies_all_15_tiers(self) -> None:
        t0 = time.perf_counter()
        with patch.object(
            HighDensityEncoder,
            "encode_records_to_toon",
            wraps=HighDensityEncoder.encode_records_to_toon,
        ) as encode_spy:
            passed = gate_11_token_reduction(self.repo_root)
        elapsed = time.perf_counter() - t0
        self.assertTrue(passed, "Gate 11 must pass for all 15 tiers in Hub repo")
        self.assertLess(elapsed, 1.0, f"Gate 11 must execute in < 1.0s, took {elapsed:.3f}s")
        encode_spy.assert_any_call(
            [{"id": 1, "name": "alpha", "ok": True}, {"id": 2, "name": "beta", "ok": False}]
        )

        metrics = LAST_GATE_METRICS.get("gate_11_token_reduction", {})
        self.assertIs(metrics.get("passed"), True)
        self.assertEqual(metrics.get("status"), "PASS")
        self.assertEqual(metrics.get("score"), "15/15")
        self.assertEqual(metrics.get("checks_passed"), 15)
        self.assertEqual(metrics.get("total_checks"), 15)
        self.assertEqual(len(metrics.get("details", [])), 15)

        # Core-6 Production verification metadata
        self.assertIs(metrics.get("core_production_verified"), True)
        self.assertEqual(metrics.get("core_production_passed"), 6)
        self.assertEqual(metrics.get("core_production_total"), 6)
        self.assertEqual(
            metrics.get("tier_classification", {}).get("core_production"),
            [1, 2, 3, 4, 10, 15],
        )

        # Research-simulation separation metadata
        self.assertEqual(metrics.get("research_tiers_inventoried"), 6)
        self.assertEqual(metrics.get("research_simulation_tiers"), [8, 9, 11, 12, 13, 14])
        self.assertEqual(LAST_GATE_METRICS.get("gate_11"), metrics)

        expected_tok = round(len(json.dumps(SynapseMetaMCPServer.TOOLS)) / 3.8, 1)
        details_text = " ".join(metrics.get("details", []))
        self.assertIn(f"({expected_tok} tok)", details_text)

        # Check that Tiers 11 to 15 are explicitly reported in details
        self.assertIn("Tier 11: Repo Speculative Decoding", details_text)
        self.assertIn("Tier 12: Kolmogorov-Minimal Symbolic Micro-DSL", details_text)
        self.assertIn("Tier 13: Logprob-Triggered Prefix Branching", details_text)
        self.assertIn("Tier 14: Boundary Counterfactual Few-Shot Distiller", details_text)
        self.assertIn("Tier 15: Neuro-Symbolic Constraint Offloading", details_text)

    def test_gate_11_class_interface(self) -> None:
        gate_obj = Gate11TokenReduction()
        self.assertEqual(gate_obj.gate_id, 11)
        res = gate_obj.run(self.repo_root)
        self.assertTrue(res)

    def test_gate_11_fails_when_tier_1_prefix_lint_fails(self) -> None:
        with patch("tools.lint.lint_cache_prefix.run_prefix_lint", return_value=(False, ["prefix broken"])):
            passed = gate_11_token_reduction(self.repo_root)
        self.assertFalse(passed)
        metrics = LAST_GATE_METRICS["gate_11_token_reduction"]
        self.assertEqual(metrics.get("status"), "FAIL")
        self.assertIs(metrics.get("core_production_verified"), False)
        self.assertEqual(len(metrics.get("details", [])), 15)
        self.assertEqual(metrics.get("core_production_passed"), 5)

    def test_gate_11_fails_when_tier_2_meta_tool_fails(self) -> None:
        with patch("tools.runtime.meta_tool_engine.MetaToolEngine._load_catalogs", lambda self_obj: setattr(self_obj, "schema_source", "tools_schema.json")):
            passed = gate_11_token_reduction(self.repo_root)
        self.assertFalse(passed)
        metrics = LAST_GATE_METRICS["gate_11_token_reduction"]
        self.assertEqual(metrics.get("status"), "FAIL")
        self.assertIs(metrics.get("core_production_verified"), False)
        self.assertEqual(len(metrics.get("details", [])), 15)
        expected_tok = round(len(json.dumps(SynapseMetaMCPServer.TOOLS)) / 3.8, 1)
        self.assertIn(f"tokens={expected_tok}", " ".join(metrics.get("details", [])))

        with patch("tools.runtime.meta_tool_engine.MetaToolEngine.search_tools", return_value="not-toon"):
            passed_toon = gate_11_token_reduction(self.repo_root)
        self.assertFalse(passed_toon)
        self.assertEqual(LAST_GATE_METRICS["gate_11_token_reduction"].get("status"), "FAIL")
        self.assertIs(LAST_GATE_METRICS["gate_11_token_reduction"].get("core_production_verified"), False)

        oversized_tools = [{"name": "x", "description": "d" * 2000}]
        with patch("tools.mcp.synapse_meta_mcp.SynapseMetaMCPServer.TOOLS", oversized_tools):
            passed_mcp = gate_11_token_reduction(self.repo_root)
        self.assertFalse(passed_mcp)
        self.assertIs(LAST_GATE_METRICS["gate_11_token_reduction"].get("core_production_verified"), False)

    def test_gate_11_fails_when_tier_3_ast_slicer_or_toon_fails(self) -> None:
        low_compression_stub = "class CachePrefixEnforcer:\n" + ("# pad\n" * 1500)
        with patch("tools.context.context_slicer.ASTSkeletonExtractor.extract_skeleton", return_value=low_compression_stub):
            passed = gate_11_token_reduction(self.repo_root)
        self.assertFalse(passed)
        metrics = LAST_GATE_METRICS["gate_11_token_reduction"]
        self.assertEqual(metrics.get("status"), "FAIL")
        self.assertIs(metrics.get("core_production_verified"), False)
        self.assertEqual(len(metrics.get("details", [])), 15)

        with patch("tools.context.high_density_encoder.HighDensityEncoder.decode_toon_to_records", return_value=[]):
            passed_toon = gate_11_token_reduction(self.repo_root)
        self.assertFalse(passed_toon)
        self.assertIs(LAST_GATE_METRICS["gate_11_token_reduction"].get("core_production_verified"), False)

    def test_gate_11_fails_when_tier_4_state_or_masking_fails(self) -> None:
        with patch("tools.core.project_state.export_stateless_working_block", return_value="x" * 1000):
            passed = gate_11_token_reduction(self.repo_root)
        self.assertFalse(passed)
        self.assertEqual(LAST_GATE_METRICS["gate_11_token_reduction"].get("status"), "FAIL")
        self.assertIs(LAST_GATE_METRICS["gate_11_token_reduction"].get("core_production_verified"), False)

        with patch(
            "tools.runtime.trajectory_compressor.TrajectoryCompressor.mask_tool_observation",
            return_value={"masked": False, "saved_tokens": 0, "log_file": None},
        ):
            passed_mask = gate_11_token_reduction(self.repo_root)
        self.assertFalse(passed_mask)
        self.assertIs(LAST_GATE_METRICS["gate_11_token_reduction"].get("core_production_verified"), False)

    def test_gate_11_fails_when_tier_10_macro_cache_fails(self) -> None:
        with patch(
            "tools.core.macro_cache.MacroCacheEngine.execute_zero_token_repair",
            return_value={"repaired": False, "tokens_consumed": 5},
        ):
            passed = gate_11_token_reduction(self.repo_root)
        self.assertFalse(passed)
        metrics = LAST_GATE_METRICS["gate_11_token_reduction"]
        self.assertEqual(metrics.get("status"), "FAIL")
        self.assertIs(metrics.get("core_production_verified"), False)
        self.assertEqual(len(metrics.get("details", [])), 15)

    def test_gate_11_fails_when_tier_15_cycle_solver_fails(self) -> None:
        with patch(
            "tools.reasoning.neuro_symbolic_solver.DependencyCycleSolver.solve",
            return_value=SimpleNamespace(has_cycle=False),
        ):
            passed = gate_11_token_reduction(self.repo_root)
        self.assertFalse(passed)
        metrics = LAST_GATE_METRICS["gate_11_token_reduction"]
        self.assertEqual(metrics.get("status"), "FAIL")
        self.assertIs(metrics.get("core_production_verified"), False)
        self.assertEqual(len(metrics.get("details", [])), 15)
        self.assertEqual(metrics.get("core_production_passed"), 5)

        with patch(
            "tools.reasoning.neuro_symbolic_solver.DependencyCycleSolver.solve",
            return_value=SimpleNamespace(has_cycle=True),
        ):
            passed_acyclic = gate_11_token_reduction(self.repo_root)
        self.assertFalse(passed_acyclic)
        self.assertIs(LAST_GATE_METRICS["gate_11_token_reduction"].get("core_production_verified"), False)

    def test_gate_11_target_mode_boundary(self) -> None:
        passed = gate_11_token_reduction(self.repo_root, mode="TARGET")
        self.assertTrue(passed)
        metrics = LAST_GATE_METRICS.get("gate_11_token_reduction", {})
        self.assertIs(metrics.get("passed"), True)
        self.assertEqual(metrics.get("status"), "PASS")
        self.assertEqual(metrics.get("checks_passed"), 15)
        self.assertEqual(metrics.get("total_checks"), 15)
        self.assertGreaterEqual(metrics.get("duration", -1), 0.0)
        self.assertLess(metrics.get("duration", 999.0), 1.0)

        with tempfile.TemporaryDirectory() as tmpdir:
            auto_passed = gate_11_token_reduction(tmpdir, mode="AUTO")
            self.assertTrue(auto_passed)
            self.assertEqual(LAST_GATE_METRICS.get("gate_11_token_reduction", {}).get("status"), "PASS")


if __name__ == "__main__":
    unittest.main()
