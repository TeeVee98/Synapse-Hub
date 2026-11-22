#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_eval_runner.py — Unit Tests for Enterprise Harness Scoring Engine ("The Exam")
"""

import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools", "core"))

from eval_runner import EvalRunner, WEIGHT_GATES, WEIGHT_TESTS, WEIGHT_MUTATION, WEIGHT_HARNESS


class TestEvalRunnerScoring(unittest.TestCase):
    """Tests the composite scoring function s(e) and component weights."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runner = EvalRunner(repo_root=REPO_ROOT, baseline_path=os.path.join(self.tmpdir, "baseline.json"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_weights_sum_to_one(self):
        """Weights must sum exactly to 1.0 (100% composite score)."""
        total_weight = WEIGHT_GATES + WEIGHT_TESTS + WEIGHT_MUTATION + WEIGHT_HARNESS
        self.assertAlmostEqual(total_weight, 1.0, places=4)

    def test_perfect_score_calculation(self):
        """When all gates, tests, mutation, and harness are 100%, composite score must be 100.0."""
        gate_data = {
            "all_passed": True,
            "summary": {"total": 10, "passed": 10, "failed": 0},
            "pytest_metrics": {"passed": 100, "failed": 0, "errors": 0},
            "mutation_metrics": {"mutation_score": 100.0},
        }
        harness_data = {"readiness_score": 100.0}

        score = self.runner.compute_composite_score(gate_data, harness_data)
        self.assertEqual(score["composite_score"], 100.0)
        self.assertEqual(score["components"]["gates"]["contribution"], 40.0)
        self.assertEqual(score["components"]["tests"]["contribution"], 30.0)
        self.assertEqual(score["components"]["mutation"]["contribution"], 20.0)
        self.assertEqual(score["components"]["harness"]["contribution"], 10.0)

    def test_degraded_score_calculation(self):
        """Calculates partial scores accurately when gates or mutations degrade."""
        gate_data = {
            "all_passed": False,
            "summary": {"total": 10, "passed": 8, "failed": 2},  # 80% gates -> 32.0 pts
            "pytest_metrics": {"passed": 90, "failed": 10, "errors": 0},  # 90% tests -> 27.0 pts
            "mutation_metrics": {"mutation_score": 80.0},  # 80% mutation -> 16.0 pts
        }
        harness_data = {"readiness_score": 90.0}  # 90% harness -> 9.0 pts

        self.runner.tier = "full"
        score = self.runner.compute_composite_score(gate_data, harness_data)
        # 32.0 + 27.0 + 16.0 + 9.0 = 84.0
        self.assertAlmostEqual(score["composite_score"], 84.0, places=1)


class TestRetentionConstraints(unittest.TestCase):
    """Tests the Retention Constraint (Anti-Capability Erosion / Catastrophic Forgetting)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runner = EvalRunner(repo_root=REPO_ROOT, baseline_path=os.path.join(self.tmpdir, "baseline.json"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_no_baseline_accepts_as_initial(self):
        """When no baseline exists, candidate is accepted as initial reference."""
        res = self.runner.check_retention_constraints(
            candidate_score=95.0,
            candidate_gates=[{"name": "Gate 1", "passed": True}],
            baseline=None,
        )
        self.assertTrue(res["retention_passed"])
        self.assertIn("ACCEPTED", res["decision"])

    def test_candidate_with_higher_score_and_no_regression_accepted(self):
        """Candidate with higher score and 0 regressed gates is ACCEPTED."""
        baseline = {
            "score": {"composite_score": 90.0},
            "gates": [
                {"name": "Gate 1", "passed": True},
                {"name": "Gate 2", "passed": True},
            ],
        }
        candidate_gates = [
            {"name": "Gate 1", "passed": True},
            {"name": "Gate 2", "passed": True},
        ]
        res = self.runner.check_retention_constraints(
            candidate_score=95.5,
            candidate_gates=candidate_gates,
            baseline=baseline,
        )
        self.assertTrue(res["retention_passed"])
        self.assertEqual(res["delta_score"], 5.5)
        self.assertEqual(res["decision"], "ACCEPTED")

    def test_candidate_with_regressed_gate_rejected(self):
        """Candidate that breaks a previously passing gate is REJECTED (Capability Erosion)."""
        baseline = {
            "score": {"composite_score": 90.0},
            "gates": [
                {"name": "Gate 1: UTF-8 No BOM", "passed": True},
                {"name": "Gate 2: Path Portability", "passed": True},
            ],
        }
        # Gate 2 regressed to False
        candidate_gates = [
            {"name": "Gate 1: UTF-8 No BOM", "passed": True},
            {"name": "Gate 2: Path Portability", "passed": False},
        ]
        res = self.runner.check_retention_constraints(
            candidate_score=92.0,  # even if score claimed higher
            candidate_gates=candidate_gates,
            baseline=baseline,
        )
        self.assertFalse(res["retention_passed"])
        self.assertIn("Gate 2: Path Portability", res["regressed_gates"])
        self.assertIn("REJECTED", res["decision"])

    def test_candidate_with_score_drop_rejected(self):
        """Candidate with score lower than baseline is REJECTED."""
        baseline = {
            "score": {"composite_score": 95.0},
            "gates": [{"name": "Gate 1", "passed": True}],
        }
        candidate_gates = [{"name": "Gate 1", "passed": True}]
        res = self.runner.check_retention_constraints(
            candidate_score=88.0,
            candidate_gates=candidate_gates,
            baseline=baseline,
        )
        self.assertFalse(res["retention_passed"])
        self.assertEqual(res["delta_score"], -7.0)
        self.assertIn("REJECTED", res["decision"])


class TestBaselinePersistence(unittest.TestCase):
    """Tests saving and loading baseline JSON and Markdown reports."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.bfile = os.path.join(self.tmpdir, "baseline.json")
        self.rfile = os.path.join(self.tmpdir, "report.json")
        self.runner = EvalRunner(repo_root=REPO_ROOT, baseline_path=self.bfile, report_path=self.rfile)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_and_load_baseline(self):
        """Baseline round-trip serialization."""
        data = {
            "git_commit": "abc1234",
            "score": {"composite_score": 98.5},
            "gates": [{"name": "Gate 1", "passed": True}],
        }
        self.runner.save_baseline(data)
        loaded = self.runner.load_baseline()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["git_commit"], "abc1234")
        self.assertEqual(loaded["score"]["composite_score"], 98.5)


if __name__ == "__main__":
    unittest.main()
