#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_eval_runner.py — Unit Tests for Enterprise Harness Scoring Engine ("The Exam")
"""

import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.core.eval_runner import EvalRunner, get_git_commit, WEIGHT_GATES, WEIGHT_TESTS, WEIGHT_MUTATION, WEIGHT_HARNESS


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


class TestM1GateDTOAndHarnessSmokeProbes(unittest.TestCase):
    """M1 tests for in-memory verify_all DTO and callable HarnessSentinel smoke probes."""

    def test_run_all_gates_detailed_returns_tuple_and_isolated_report(self):
        """run_all_gates_detailed must return (exit_code, result_dict) and respect report_path."""
        from tools.core.verify_all import run_all_gates_detailed

        with tempfile.TemporaryDirectory() as tmpdir:
            isolated_report = os.path.join(tmpdir, "nested", "custom_verify.json")
            with open(os.path.join(tmpdir, "clean.py"), "w", encoding="utf-8") as f:
                f.write("def test_ok():\n    assert 1 == 1\n")

            rc, bundle = run_all_gates_detailed(
                tmpdir,
                mode="TARGET",
                fast=True,
                output_format="json",
                report_path=isolated_report,
            )
            self.assertIn(rc, (0, 1))
            self.assertIsInstance(bundle, dict)
            self.assertIn("summary", bundle)
            self.assertIn("gates", bundle)
            self.assertEqual(bundle["summary"]["total"], 11)
            self.assertTrue(os.path.exists(isolated_report))

    def test_harness_sentinel_smoke_probes_pass_on_hub(self):
        """HarnessSentinel Step 2 and Step 6 must execute real callable smoke probes."""
        from tools.core.harness_sentinel import HarnessSentinel

        sentinel = HarnessSentinel(REPO_ROOT)
        report = sentinel.run_full_audit()
        self.assertEqual(report["readiness_score"], 100.0)
        step2 = next(s for s in report["steps"] if s["step"] == 2)
        step6 = next(s for s in report["steps"] if s["step"] == 6)
        self.assertTrue(step2["passed"])
        self.assertTrue(step6["passed"])
        self.assertTrue(any("Infer-Linter callable smoke probe verified (TEST_SCRIPT)" in d for d in step2["details"]))
        self.assertTrue(any("Verify-All (11 Gates) callable smoke probe verified" in d for d in step2["details"]))
        self.assertTrue(any("Fact-Forcing Gate callable smoke probe verified" in d for d in step2["details"]))
        self.assertTrue(any("probe" in d.lower() or "verified" in d.lower() for d in step6["details"]))

    def test_harness_sentinel_fails_closed_when_probe_raises(self):
        """HarnessSentinel must not mask import/runtime errors in Step 2 or Step 6."""
        from unittest.mock import patch
        from tools.core.harness_sentinel import HarnessSentinel

        sentinel = HarnessSentinel(REPO_ROOT)
        with patch("tools.core.token_estimator.count_tokens", side_effect=RuntimeError("boom")):
            step6 = sentinel.audit_step6_observability()
            self.assertFalse(step6["passed"])
            self.assertEqual(step6["status"], "FAIL")

        with patch("tools.lint.infer_linter.classify_file_role", side_effect=RuntimeError("boom")):
            step2 = sentinel.audit_step2_sensors()
            self.assertFalse(step2["passed"])
            self.assertEqual(step2["status"], "FAIL")
            self.assertTrue(any("Infer-Linter smoke probe failed" in d for d in step2["details"]))

        with patch("tools.lint.infer_linter.classify_file_role", return_value="WRONG"):
            step2 = sentinel.audit_step2_sensors()
            self.assertFalse(step2["passed"])
            self.assertTrue(any("unexpected role" in d for d in step2["details"]))

        with patch("tools.core.verify_all.ALL_GATES", []):
            step2 = sentinel.audit_step2_sensors()
            self.assertFalse(step2["passed"])
            self.assertTrue(any("Verify-All smoke probe failed" in d for d in step2["details"]))

        with patch("tools.core.verify_all.run_all_gates_detailed", None):
            step2 = sentinel.audit_step2_sensors()
            self.assertFalse(step2["passed"])
            self.assertTrue(any("Verify-All smoke probe failed" in d for d in step2["details"]))

        with patch("tools.core.fact_forcing_gate.evaluate_content", return_value=(True, ["unexpected"])):
            step2 = sentinel.audit_step2_sensors()
            self.assertFalse(step2["passed"])
            self.assertTrue(any("Fact-Forcing Gate smoke probe failed" in d for d in step2["details"]))

        with patch("tools.core.fact_forcing_gate.evaluate_content", side_effect=RuntimeError("ffg boom")):
            step2 = sentinel.audit_step2_sensors()
            self.assertFalse(step2["passed"])
            self.assertTrue(any("Fact-Forcing Gate smoke probe failed" in d for d in step2["details"]))

        with tempfile.TemporaryDirectory() as empty_repo:
            empty_sentinel = HarnessSentinel(empty_repo)
            step2_empty = empty_sentinel.audit_step2_sensors()
            self.assertFalse(step2_empty["passed"])
            self.assertTrue(any("Infer-Linter: Missing" in d for d in step2_empty["details"]))
            self.assertTrue(any("Verify-All: Missing" in d for d in step2_empty["details"]))


class TestM2EvalRunnerTruthAnchor(unittest.TestCase):
    """M2 tests for fail-closed HarnessSentinel wiring, in-memory DTOs, proportional fast proxy, and no 95.58 fallback."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runner = EvalRunner(
            repo_root=REPO_ROOT,
            tier="fast",
            baseline_path=os.path.join(self.tmpdir, "baseline.json"),
            report_path=os.path.join(self.tmpdir, "eval_report.json"),
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_harness_readiness_fails_closed_on_exception(self):
        """Injected RuntimeError in HarnessSentinel must drop score to 0.0 and record HARNESS_LAYER_DEFECT."""
        from unittest.mock import patch

        with patch("tools.core.harness_sentinel.HarnessSentinel.run_full_audit", side_effect=RuntimeError("sentinel crash")):
            hdata, failures = self.runner.run_harness_readiness()
            self.assertEqual(hdata["readiness_score"], 0.0)
            self.assertGreaterEqual(len(failures), 1)
            self.assertEqual(failures[0]["category"], "HARNESS_LAYER_DEFECT")

    def test_harness_readiness_reports_step_defect_from_run_full_audit(self):
        """Broken step from run_full_audit() must reduce readiness_score below 100.0 and record HARNESS_LAYER_DEFECT."""
        from unittest.mock import patch

        mock_report = {
            "readiness_score": 83.3,
            "overall_status": "DEGRADED",
            "steps": [
                {"step": 1, "name": "Guides", "passed": True, "details": []},
                {"step": 2, "name": "Sensors", "passed": False, "details": ["probe failed"]},
            ],
        }
        with patch("tools.core.harness_sentinel.HarnessSentinel.run_full_audit", return_value=mock_report):
            hdata, failures = self.runner.run_harness_readiness()
            self.assertEqual(hdata["readiness_score"], 83.3)
            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0]["category"], "HARNESS_LAYER_DEFECT")
            self.assertEqual(failures[0]["name"], "Sensors")

    def test_proportional_fast_proxy_and_no_magic_mutation_fallback(self):
        """1 failed static gate in fast mode yields 90.91 s_tests proxy; missing mutation_metrics yields 0.0 (no 95.58)."""
        gate_data = {
            "all_passed": False,
            "summary": {"total": 11, "passed": 10, "failed": 1},
            "pytest_metrics": {},
            "mutation_metrics": {},
        }
        harness_data = {"readiness_score": 100.0}
        score = self.runner.compute_composite_score(gate_data, harness_data)

        self.assertEqual(score["tests_measurement_mode"], "static_fast_proxy")
        self.assertEqual(score["components"]["tests"]["measurement_mode"], "static_fast_proxy")
        self.assertAlmostEqual(score["components"]["tests"]["score"], 90.91, places=2)
        self.assertEqual(score["components"]["mutation"]["score"], 0.0)

    def test_run_quality_gates_consumes_in_memory_bundle(self):
        """run_quality_gates must consume run_all_gates_detailed() in memory without reading global reports/verify_all_report.json."""
        from unittest.mock import patch

        fake_bundle = {
            "all_passed": True,
            "return_code": 0,
            "summary": {"total": 11, "passed": 11, "skipped": 0, "failed": 0},
            "gates": [{"name": f"Gate {i}", "passed": True, "status": "PASS"} for i in range(1, 12)],
            "pytest_metrics": {"passed": 50, "failed": 0, "errors": 0},
            "assertion_and_mutation_metrics": {"static_assertion_sensitivity_score": 98.5},
            "performance_metrics": {},
        }
        with patch("tools.core.verify_all.run_all_gates_detailed", return_value=(0, fake_bundle)) as mock_detailed:
            gate_payload, failures = self.runner.run_quality_gates(silent=True)
            self.assertTrue(mock_detailed.called)
            self.assertTrue(gate_payload["all_passed"])
            self.assertEqual(gate_payload["summary"]["total"], 11)
            self.assertEqual(len(failures), 0)

    def test_run_quality_gates_summary_fallback_and_missing_readiness_keys(self):
        """Fallback summary when bundle omits summary, and fail-closed defaults on missing HarnessSentinel keys."""
        from unittest.mock import patch

        with patch("tools.core.verify_all.run_all_gates_detailed", return_value=(0, {"gates": []})):
            gp_ok, _ = self.runner.run_quality_gates(silent=True)
            self.assertTrue(gp_ok["all_passed"])
            self.assertEqual(gp_ok["summary"]["total"], 11)
            self.assertEqual(gp_ok["summary"]["passed"], 11)
            self.assertEqual(gp_ok["summary"]["failed"], 0)

        with patch("tools.core.verify_all.run_all_gates_detailed", return_value=(1, {"gates": []})):
            gp_fail, _ = self.runner.run_quality_gates(silent=True)
            self.assertFalse(gp_fail["all_passed"])
            self.assertEqual(gp_fail["summary"]["passed"], 0)
            self.assertEqual(gp_fail["summary"]["failed"], 1)

        with patch("tools.core.harness_sentinel.HarnessSentinel.run_full_audit", return_value={"steps": [{"step": 1, "name": "G"}]}):
            hdata, failures = self.runner.run_harness_readiness()
            self.assertEqual(hdata["readiness_score"], 0.0)
            self.assertEqual(len(failures), 1)

        self.runner.tier = "full"
        s_empty = self.runner.compute_composite_score(
            {"all_passed": False, "summary": {"total": 0, "passed": 0}, "pytest_metrics": {}},
            {"readiness_score": 100.0},
        )
        self.assertEqual(s_empty["components"]["gates"]["score"], 0.0)
        self.assertEqual(s_empty["components"]["tests"]["score"], 0.0)

        s_partial_pytest = self.runner.compute_composite_score(
            {"all_passed": True, "summary": {"total": 11, "passed": 11}, "pytest_metrics": {"passed": 10}},
            {"readiness_score": 100.0},
        )
        self.assertEqual(s_partial_pytest["components"]["tests"]["score"], 100.0)

        s_single_pytest = self.runner.compute_composite_score(
            {"all_passed": False, "summary": {"total": 11, "passed": 10}, "pytest_metrics": {"passed": 1, "failed": 0, "errors": 0}},
            {"readiness_score": 100.0},
        )
        self.assertEqual(s_single_pytest["tests_measurement_mode"], "pytest")
        self.assertEqual(s_single_pytest["components"]["tests"]["score"], 100.0)


class TestM3EvalRunnerMutationKillers(unittest.TestCase):
    """M3 tests covering git commit resolution, stdout handling, gate flags/fallbacks, and pytest error totals."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runner = EvalRunner(
            repo_root=REPO_ROOT,
            tier="fast",
            baseline_path=os.path.join(self.tmpdir, "baseline.json"),
            report_path=os.path.join(self.tmpdir, "eval_report.json"),
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_get_git_commit_returns_str_sha_and_unknown_on_failure(self):
        """get_git_commit returns decoded str SHA on valid repo and 'unknown' on non-git or missing dir."""
        sha = get_git_commit(REPO_ROOT)
        self.assertIsInstance(sha, str)
        self.assertNotEqual(sha, "unknown")
        self.assertGreaterEqual(len(sha), 1)
        self.assertLessEqual(len(sha), 10)

        self.assertEqual(get_git_commit(self.tmpdir), "unknown")
        self.assertEqual(get_git_commit(os.path.join(self.tmpdir, "nonexistent")), "unknown")

    def test_run_quality_gates_silent_default_and_stdout_restoration(self):
        """Default silent=False writes to stdout; silent=True suppresses stdout and always restores sys.stdout."""
        def _emitting_gates(*args, **kwargs):
            print("GATE_STDOUT_MARKER")
            return 0, {"gates": [], "summary": {"total": 1, "passed": 1, "failed": 0}}

        with patch("tools.core.verify_all.run_all_gates_detailed", side_effect=_emitting_gates):
            buf_default = io.StringIO()
            with patch("sys.stdout", buf_default):
                self.runner.run_quality_gates()
                self.assertIs(sys.stdout, buf_default)
            self.assertIn("GATE_STDOUT_MARKER", buf_default.getvalue())

            buf_silent = io.StringIO()
            with patch("sys.stdout", buf_silent):
                self.runner.run_quality_gates(silent=True)
                self.assertIs(sys.stdout, buf_silent)
            self.assertEqual(buf_silent.getvalue(), "")

    def test_run_quality_gates_passes_tier_and_fast_flag(self):
        """run_quality_gates forwards fast=True only when tier=='fast' and fast=False otherwise."""
        bundle = {"gates": [], "summary": {"total": 1, "passed": 1, "failed": 0}}
        with patch("tools.core.verify_all.run_all_gates_detailed", return_value=(0, bundle)) as mock_detailed:
            self.runner.tier = "fast"
            self.runner.run_quality_gates(silent=True)
            self.assertIs(mock_detailed.call_args.kwargs["fast"], True)
            self.assertEqual(mock_detailed.call_args.kwargs["tier"], "fast")

            self.runner.tier = "full"
            self.runner.run_quality_gates(silent=True)
            self.assertIs(mock_detailed.call_args.kwargs["fast"], False)
            self.assertEqual(mock_detailed.call_args.kwargs["tier"], "full")

    def test_run_quality_gates_all_passed_requires_rc_zero_and_failed_zero(self):
        """all_passed must be False when either rc != 0 or summary['failed'] != 0."""
        with patch(
            "tools.core.verify_all.run_all_gates_detailed",
            return_value=(0, {"gates": [], "summary": {"total": 11, "passed": 10, "failed": 1}}),
        ):
            gp_failed_summary, _ = self.runner.run_quality_gates(silent=True)
            self.assertFalse(gp_failed_summary["all_passed"])

        with patch(
            "tools.core.verify_all.run_all_gates_detailed",
            return_value=(1, {"gates": [], "summary": {"total": 11, "passed": 11, "failed": 0}}),
        ):
            gp_failed_rc, _ = self.runner.run_quality_gates(silent=True)
            self.assertFalse(gp_failed_rc["all_passed"])

    def test_run_quality_gates_missing_passed_key_records_failure(self):
        """A gate entry missing the 'passed' key must default to False and be recorded in failures."""
        bundle = {
            "gates": [{"name": "Gate Missing Passed", "status": "FAIL"}],
            "summary": {"total": 1, "passed": 0, "failed": 1},
        }
        with patch("tools.core.verify_all.run_all_gates_detailed", return_value=(1, bundle)):
            _, failures = self.runner.run_quality_gates(silent=True)
            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0]["gate"], "Gate Missing Passed")

    def test_run_quality_gates_metrics_prefer_vdata_and_fallback_to_last_gate_metrics(self):
        """run_quality_gates uses vdata metrics when present and falls back to LAST_GATE_METRICS when absent."""
        bundle_with_metrics = {
            "gates": [],
            "summary": {"total": 11, "passed": 11, "failed": 0},
            "pytest_metrics": {"passed": 5, "failed": 0, "errors": 0},
            "assertion_and_mutation_metrics": {"static_assertion_sensitivity_score": 98.5},
            "performance_metrics": {"p95_ms": 12.5},
        }
        with patch("tools.core.verify_all.LAST_GATE_METRICS", {}), patch(
            "tools.core.verify_all.run_all_gates_detailed",
            return_value=(0, bundle_with_metrics),
        ):
            gp, _ = self.runner.run_quality_gates(silent=True)
            self.assertEqual(gp["pytest_metrics"], {"passed": 5, "failed": 0, "errors": 0})
            self.assertEqual(gp["mutation_metrics"], {"static_assertion_sensitivity_score": 98.5})
            self.assertEqual(gp["perf_metrics"], {"p95_ms": 12.5})

        fallback_cache = {
            "gate_7": {"passed": 3, "failed": 1, "errors": 0},
            "gate_8": {"mutation_score": 88.0},
            "gate_10": {"p95_ms": 42.0},
        }
        with patch("tools.core.verify_all.LAST_GATE_METRICS", fallback_cache), patch(
            "tools.core.verify_all.run_all_gates_detailed",
            return_value=(0, {"gates": [], "summary": {"total": 11, "passed": 11, "failed": 0}}),
        ):
            gp_fb, _ = self.runner.run_quality_gates(silent=True)
            self.assertEqual(gp_fb["pytest_metrics"], fallback_cache["gate_7"])
            self.assertEqual(gp_fb["mutation_metrics"], fallback_cache["gate_8"])
            self.assertEqual(gp_fb["perf_metrics"], fallback_cache["gate_10"])

    def test_compute_composite_score_includes_pytest_errors_in_failed_total(self):
        """Pytest score denominator must include both failed and errors counts."""
        self.runner.tier = "full"
        score_both = self.runner.compute_composite_score(
            {
                "all_passed": False,
                "summary": {"total": 10, "passed": 10, "failed": 0},
                "pytest_metrics": {"passed": 8, "failed": 1, "errors": 1},
            },
            {"readiness_score": 100.0},
        )
        self.assertEqual(score_both["tests_measurement_mode"], "pytest")
        self.assertAlmostEqual(score_both["components"]["tests"]["score"], 80.0, places=2)

        score_errors_only = self.runner.compute_composite_score(
            {
                "all_passed": False,
                "summary": {"total": 10, "passed": 10, "failed": 0},
                "pytest_metrics": {"passed": 4, "failed": 0, "errors": 1},
            },
            {"readiness_score": 100.0},
        )
        self.assertAlmostEqual(score_errors_only["components"]["tests"]["score"], 80.0, places=2)


if __name__ == "__main__":
    unittest.main()
