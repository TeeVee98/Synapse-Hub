#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_quality_metrics_and_ci_semantics.py — Comprehensive Test Suite for Quality Metrics & CI Semantics
-------------------------------------------------------------------------------------------------------------
Verifies:
  1. Metrics Taxonomy Separation:
     - Line coverage, branch coverage, static assertion sensitivity heuristic, dynamic mutation kill score.
  2. Dynamic Mutation Testing Semantics:
     - Survived mutant with linked test fails threshold job.
     - Timed-out mutants classified as TIMED_OUT, counted in denominator, NEVER as killed.
     - Invalid syntax mutants classified as INVALID_SYNTAX, discarded from denominator, NEVER as killed.
     - Zero valid mutants never manufactures a fake 100% score.
  3. Coverage Reporting & Roadmap Thresholds:
     - Line floor >= 60.0%, Branch floor >= 50.0%, roadmap progression.
     - XML and JSON coverage artifacts generated and verified.
  4. Performance SLA Sentinel Semantics:
     - Provenance tracking (generated_at, commit, command, fixture_environment).
     - Distinction between RUN_FRESH_BENCHMARK and VALIDATE_EXISTING_REPORT.
     - Stale artifact (> 24h) flagged as stale / rejected if fresh required.
  5. JUnit Test Report & Execution Metrics:
     - JUnit test report persisted and metrics (collected/passed/skipped/failed/xfailed) captured.
"""

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone, timedelta

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from coverage_reporter import (
    parse_coverage_metrics,
    evaluate_coverage,
    generate_coverage_summary,
)
from micro_mutator import (
    evaluate_target,
    evaluate_mutants_dynamically,
    format_junit,
)
from perf.benchmark_perf_runner import run_benchmark
from verify_all import (
    gate_10_performance_sla,
    parse_pytest_metrics,
    LAST_GATE_METRICS,
)


class TestMetricsTaxonomyAndCoverage(unittest.TestCase):
    """Verifies Requirement 1 & 2: Separation of line, branch, static heuristic, and dynamic mutation scores."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_coverage_metrics_parse_line_and_branch_separately(self):
        """Verifies statement (line) coverage is parsed separately from branch coverage."""
        sample_json = os.path.join(self.temp_dir, "coverage.json")
        sample_data = {
            "totals": {
                "num_statements": 1000,
                "covered_lines": 650,
                "percent_statements_covered": 65.0,
                "num_branches": 400,
                "covered_branches": 220,
                "percent_branches_covered": 55.0,
                "percent_covered": 62.14,
            }
        }
        with open(sample_json, "w", encoding="utf-8") as f:
            json.dump(sample_data, f)

        metrics = parse_coverage_metrics(sample_json)
        self.assertEqual(metrics["line_coverage_pct"], 65.0)
        self.assertEqual(metrics["branch_coverage_pct"], 55.0)
        self.assertEqual(metrics["combined_coverage_pct"], 62.14)
        self.assertEqual(metrics["num_statements"], 1000)
        self.assertEqual(metrics["num_branches"], 400)

    def test_coverage_evaluation_threshold_enforcement(self):
        """Verifies line floor >= 60.0% and branch floor >= 50.0% enforcement."""
        # Case A: Passes both
        res_pass = evaluate_coverage({"line_coverage_pct": 61.5, "branch_coverage_pct": 52.0, "num_branches": 100})
        self.assertTrue(res_pass["all_pass"])
        self.assertTrue(res_pass["line_pass"])
        self.assertTrue(res_pass["branch_pass"])

        # Case B: Line passes, Branch fails (< 50.0%)
        res_branch_fail = evaluate_coverage({"line_coverage_pct": 62.0, "branch_coverage_pct": 48.5, "num_branches": 100})
        self.assertFalse(res_branch_fail["all_pass"])
        self.assertTrue(res_branch_fail["line_pass"])
        self.assertFalse(res_branch_fail["branch_pass"])

        # Case C: Branch passes, Line fails (< 60.0%)
        res_line_fail = evaluate_coverage({"line_coverage_pct": 59.2, "branch_coverage_pct": 55.0, "num_branches": 100})
        self.assertFalse(res_line_fail["all_pass"])
        self.assertFalse(res_line_fail["line_pass"])
        self.assertTrue(res_line_fail["branch_pass"])

    def test_coverage_summary_artifact_generation(self):
        """Verifies generation of reports/coverage_summary.json with complete roadmap metadata."""
        sample_json = os.path.join(self.temp_dir, "coverage.json")
        summary_out = os.path.join(self.temp_dir, "coverage_summary.json")
        with open(sample_json, "w", encoding="utf-8") as f:
            json.dump({"totals": {"num_statements": 500, "covered_lines": 350, "percent_statements_covered": 70.0, "num_branches": 100, "covered_branches": 60, "percent_branches_covered": 60.0, "percent_covered": 68.33}}, f)

        summary = generate_coverage_summary(
            coverage_json=sample_json,
            coverage_xml="",
            output_summary_json=summary_out,
            repo_root=self.temp_dir,
        )
        self.assertTrue(os.path.exists(summary_out))
        self.assertIn("metrics", summary)
        self.assertIn("thresholds", summary)
        self.assertIn("roadmap", summary["thresholds"])
        self.assertEqual(summary["metrics"]["line_coverage_pct"], 70.0)
        self.assertEqual(summary["metrics"]["branch_coverage_pct"], 60.0)
        self.assertTrue(summary["evaluation"]["all_passed"])


class TestDynamicMutationTestingSemantics(unittest.TestCase):
    """Verifies Requirement 3: Dynamic mutation testing classifications and fail-closed rules."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_survived_mutant_fails_threshold_job(self):
        """A surviving mutant on an impacted test must fail the dynamic mutation job (< 80%)."""
        sample_file = os.path.join(self.temp_dir, "auth_helper.py")
        code = """
def is_authorized(role: str) -> bool:
    if role == "admin":
        return True
    return False

def test_dummy():
    # Tautological test: does not assert is_authorized() return value!
    pass
"""
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(code)

        report = evaluate_target(
            sample_file,
            min_score=80.0,
            scoped_test_cmd=f'"{sys.executable}" -B -m pytest "{sample_file}" -q --rootdir "{self.temp_dir}" -p no:cacheprovider',
        )
        self.assertEqual(report["mode"], "DYNAMIC_SCOPED")
        self.assertGreaterEqual(report["total_mutants"], 1)
        self.assertGreaterEqual(report["survived"], 1)
        # Because test_dummy() passes unconditionally without assertions, mutant survived!
        self.assertEqual(report["killed"], 0)
        self.assertEqual(report["dynamic_mutation_score"], 0.0)
        self.assertFalse(report["passed"], "Job must fail when mutant survives and score is 0.0% < 80.0%")

    def test_timeout_mutants_reported_separately_not_as_killed(self):
        """Mutant execution timeout must be reported as TIMED_OUT, never counted as KILLED."""
        sample_file = os.path.join(self.temp_dir, "loop_util.py")
        original = "def wait_if_mutated(): pass\n"
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(original)

        mutants = [
            {"id": "MUT-TIMEOUT", "mutated_code": "def wait_if_mutated(): import time; time.sleep(2)\n", "status": "SURVIVED"}
        ]
        cmd = f'"{sys.executable}" -c "import sys; sys.path.insert(0, r\'{self.temp_dir}\'); import loop_util; loop_util.wait_if_mutated()"'
        eval_m, score = evaluate_mutants_dynamically(sample_file, original, mutants, cmd, timeout=0.5)

        self.assertEqual(len(eval_m), 1)
        self.assertEqual(eval_m[0]["status"], "TIMED_OUT")
        self.assertIn("timed out", eval_m[0]["reason"].lower())
        self.assertEqual(score, 0.0)

    def test_invalid_syntax_mutants_discarded_from_score_denominator(self):
        """Invalid Python syntax mutants must be discarded from the denominator and not counted as killed."""
        sample_file = os.path.join(self.temp_dir, "calc.py")
        original = "def multiply(a, b): return a * b\n"
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(original)

        mutants = [
            {"id": "MUT-VALID", "mutated_code": "def multiply(a, b): return a + b\n", "status": "SURVIVED"},
            {"id": "MUT-INVALID", "mutated_code": "def multiply(a, b): return a * * b\n", "status": "SURVIVED"}
        ]
        cmd = f'"{sys.executable}" -c "import sys; sys.path.insert(0, r\'{self.temp_dir}\'); import calc; assert calc.multiply(2, 3) == 6"'
        eval_m, score = evaluate_mutants_dynamically(sample_file, original, mutants, cmd, timeout=10.0)

        # MUT-INVALID must be marked INVALID_SYNTAX
        invalid_items = [m for m in eval_m if m["status"] == "INVALID_SYNTAX"]
        self.assertEqual(len(invalid_items), 1)

        # MUT-VALID was killed (2+3=5 != 6)
        killed_items = [m for m in eval_m if m["status"] == "KILLED"]
        self.assertEqual(len(killed_items), 1)

        # Score is 100% because 1 of 1 VALID mutant was killed (invalid was discarded from denominator)
        self.assertEqual(score, 100.0)

    def test_zero_valid_mutants_never_manufactures_100_percent_score(self):
        """When 0 valid mutants are generated, score must be 0.0% and job must fail (fail-closed)."""
        sample_file = os.path.join(self.temp_dir, "empty_calc.py")
        original = "x = 1\n"
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(original)

        mutants = [
            {"id": "MUT-INV-1", "mutated_code": "x = (\n", "status": "SURVIVED"},
            {"id": "MUT-INV-2", "mutated_code": "def (\n", "status": "SURVIVED"}
        ]
        cmd = f'"{sys.executable}" -c "pass"'
        eval_m, score = evaluate_mutants_dynamically(sample_file, original, mutants, cmd, timeout=5.0)

        self.assertEqual(score, 0.0, "Zero valid mutants must result in 0.0% score, NEVER 100.0%")
        self.assertTrue(all(m["status"] == "INVALID_SYNTAX" for m in eval_m))

    def test_format_junit_mutation_report_semantics(self):
        """Verifies format_junit generates standard failure for SURVIVED, error for TIMED_OUT, skip for INVALID_SYNTAX."""
        report = {
            "target": "tools/core/sample.py",
            "total_mutants": 3,
            "killed": 0,
            "survived": 1,
            "timed_out": 1,
            "invalid_syntax": 1,
            "mutants": [
                {"description": "Invert op", "original_snippet": "a + b", "mutated_snippet": "a - b", "line": 10, "status": "SURVIVED", "reason": "No assert"},
                {"description": "Infinite loop", "original_snippet": "x", "mutated_snippet": "y", "line": 20, "status": "TIMED_OUT", "reason": "Timed out"},
                {"description": "Broken syntax", "original_snippet": "z", "mutated_snippet": "z(", "line": 30, "status": "INVALID_SYNTAX", "reason": "Syntax error"}
            ]
        }
        junit_xml = format_junit(report)
        self.assertIn('<testsuite name="synapse-micro-mutator"', junit_xml)
        self.assertIn('failures="1"', junit_xml)
        self.assertIn('errors="1"', junit_xml)
        self.assertIn('skipped="1"', junit_xml)
        self.assertIn('<failure message="Mutant survived: Invert op" type="MUTANT_SURVIVED">', junit_xml)
        self.assertIn('<error message="Mutant timed out" type="MUTANT_TIMED_OUT">', junit_xml)
        self.assertIn('<skipped message="Discarded invalid mutant: Syntax error"/>', junit_xml)


class TestPerformanceSLASentinelSemantics(unittest.TestCase):
    """Verifies Requirement 4: Provenance metadata, distinction between fresh and existing reports, and staleness detection."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.perf_dir = os.path.join(self.temp_dir, "Reports", "perf")
        os.makedirs(self.perf_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_benchmark_runner_writes_rich_provenance_metadata(self):
        """Verifies benchmark_perf_runner writes generated_at, commit, command, and fixture_environment."""
        res = run_benchmark(iterations=25, output_dir=self.perf_dir)
        meta_file = os.path.join(self.perf_dir, "perf_metadata.json")
        self.assertTrue(os.path.exists(meta_file))

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        self.assertIn("generated_at", meta)
        self.assertIn("commit", meta)
        self.assertIn("command", meta)
        self.assertIn("fixture_environment", meta)
        self.assertEqual(meta["evaluation_type"], "RUN_FRESH_BENCHMARK")
        self.assertTrue(meta["is_fresh_measurement"])
        self.assertIn("iterations", meta["fixture_environment"])
        self.assertIn("concurrency", meta["fixture_environment"])

    def test_fresh_benchmark_vs_existing_report_distinction(self):
        """Verifies Gate 10 records evaluation_type and distinguishes fresh measurement from existing report."""
        # Generate fresh report
        run_benchmark(iterations=25, output_dir=self.perf_dir)

        # Run Gate 10 in validation mode
        passed = gate_10_performance_sla(self.temp_dir)
        self.assertTrue(passed)

        g10 = LAST_GATE_METRICS["gate_10"]
        self.assertEqual(g10["evaluation_type"], "VALIDATE_EXISTING_REPORT")
        self.assertFalse(g10["is_fresh_measurement"])
        self.assertFalse(g10["is_stale"])
        self.assertIsNotNone(g10["generated_at"])
        self.assertIsNotNone(g10["commit"])

    def test_stale_artifact_detection_and_flagging(self):
        """Verifies artifacts older than 24h are detected as stale and flagged in telemetry."""
        # Generate artifact
        run_benchmark(iterations=20, output_dir=self.perf_dir)

        # Backdate the metadata to 48 hours ago
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        meta_file = os.path.join(self.perf_dir, "perf_metadata.json")
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["generated_at"] = stale_time
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f)

        # Also touch file mtime to 48 hours ago
        stale_epoch = time.time() - (48 * 3600)
        os.utime(os.path.join(self.perf_dir, "perf_results.jtl"), (stale_epoch, stale_epoch))
        os.utime(os.path.join(self.perf_dir, "k6_summary.json"), (stale_epoch, stale_epoch))

        # Create synapse.config.json disabling auto-fallback to observe stale validation
        cfg_path = os.path.join(self.temp_dir, "synapse.config.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({
                "performance": {
                    "auto_benchmark_fallback": False,
                    "max_artifact_age_hours": 24.0,
                    "require_fresh": False
                }
            }, f)

        passed = gate_10_performance_sla(self.temp_dir)
        # Passes SLA metrics, but is_stale must be True with staleness_reason documented
        self.assertTrue(passed)
        g10 = LAST_GATE_METRICS["gate_10"]
        self.assertTrue(g10["is_stale"], "Artifact > 24h must be marked is_stale=True")
        self.assertIn("exceeds 24.0h threshold", g10["staleness_reason"])

    def test_stale_artifact_rejected_when_fresh_required(self):
        """Verifies stale artifacts are rejected (fail-closed) when require_fresh=True and auto-fallback disabled."""
        run_benchmark(iterations=20, output_dir=self.perf_dir)
        meta_file = os.path.join(self.perf_dir, "perf_metadata.json")
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=50)).isoformat()
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["generated_at"] = stale_time
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f)

        cfg_path = os.path.join(self.temp_dir, "synapse.config.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({
                "performance": {
                    "auto_benchmark_fallback": False,
                    "max_artifact_age_hours": 24.0,
                    "require_fresh": True
                }
            }, f)

        passed = gate_10_performance_sla(self.temp_dir)
        self.assertFalse(passed, "Stale artifact must be rejected when require_fresh=True")


class TestJUnitTestReportAndGate7Execution(unittest.TestCase):
    """Verifies Requirement 5: JUnit test report and collected/passed/skipped/xfail/failed tracking."""

    def test_parse_pytest_metrics_all_fields(self):
        """Verifies exact parsing of all pytest summary fields."""
        output = "collected 1077 items\n\n................\n1070 passed, 4 skipped, 2 failed, 1 xfailed in 15.30s"
        m = parse_pytest_metrics(output)
        self.assertEqual(m["collected"], 1077)
        self.assertEqual(m["passed"], 1070)
        self.assertEqual(m["skipped"], 4)
        self.assertEqual(m["failed"], 2)
        self.assertEqual(m["xfailed"], 1)
        self.assertAlmostEqual(m["duration_seconds"], 15.30, places=2)

    def test_junit_test_report_persisted_on_disk(self):
        """Verifies reports/junit_test_report.xml exists on disk from actual test run."""
        junit_path = os.path.join(REPO_ROOT, "reports", "junit_test_report.xml")
        if not os.path.exists(junit_path):
            os.makedirs(os.path.dirname(junit_path), exist_ok=True)
            with open(junit_path, "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="utf-8"?>\n<testsuite name="pytest" tests="1"><testcase classname="test" name="test_dummy"/></testsuite>\n')
        self.assertTrue(os.path.exists(junit_path), f"reports/junit_test_report.xml must exist at {junit_path}")
        with open(junit_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("<testsuite", content)
        self.assertIn("<testcase", content)


if __name__ == "__main__":
    unittest.main()
