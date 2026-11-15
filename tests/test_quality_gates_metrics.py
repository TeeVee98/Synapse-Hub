# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT

"""
Unit & Regression Tests for Milestone M3 (Quality Gates Calibration & Pytest Metrics):
- Validates exact regex parsing of pytest output lines (collected, passed, skipped, failed, xfailed, runtime).
- Validates coverage floor ratchet to 60% and progression towards 80% in pyproject.toml.
- Validates README and README.en.md badges synchronization (950+ passing).
- Validates micro_mutator operator replacement regex syntax guards (no 'is not not None') and sys.executable usage.
- Validates Gate 7 verbatim reporting and JUnit XML / JSON propagation.
"""

import os
import re
import unittest

from tools.verify_all import (
    parse_pytest_metrics,
    parse_pytest_output,
    get_git_commit_sha,
    format_gates_junit,
    REPO_ROOT,
)
from tools.micro_mutator import generate_mutants_for_code


class TestPytestMetricsParser(unittest.TestCase):
    """Verifies regex parser for exact pytest execution metrics."""

    def test_parse_standard_quiet_output(self):
        output = "........................\n952 passed, 4 skipped in 57.40s"
        m = parse_pytest_metrics(output)
        self.assertEqual(m["passed"], 952)
        self.assertEqual(m["skipped"], 4)
        self.assertEqual(m["failed"], 0)
        self.assertEqual(m["xfailed"], 0)
        self.assertEqual(m["xpassed"], 0)
        self.assertEqual(m["errors"], 0)
        self.assertEqual(m["collected"], 956)
        self.assertAlmostEqual(m["duration_seconds"], 57.40, places=2)
        self.assertIn("952 passed", m["raw_summary"])

    def test_parse_output_with_subtests(self):
        output = "952 passed, 4 skipped, 48 subtests passed in 57.40s"
        m = parse_pytest_metrics(output)
        self.assertEqual(m["passed"], 952)
        self.assertEqual(m["skipped"], 4)
        self.assertEqual(m["subtests_passed"], 48)
        self.assertEqual(m["collected"], 956)
        self.assertAlmostEqual(m["duration_seconds"], 57.40, places=2)

    def test_parse_output_with_failures(self):
        output = "1 failed, 951 passed, 4 skipped in 38.25s"
        m = parse_pytest_metrics(output)
        self.assertEqual(m["failed"], 1)
        self.assertEqual(m["passed"], 951)
        self.assertEqual(m["skipped"], 4)
        self.assertEqual(m["collected"], 956)
        self.assertAlmostEqual(m["duration_seconds"], 38.25, places=2)

    def test_parse_output_with_xfailed_and_xpassed(self):
        output = "950 passed, 2 xfailed, 1 xpassed in 30.10s"
        m = parse_pytest_metrics(output)
        self.assertEqual(m["passed"], 950)
        self.assertEqual(m["xfailed"], 2)
        self.assertEqual(m["xpassed"], 1)
        self.assertEqual(m["failed"], 0)
        self.assertEqual(m["collected"], 953)
        self.assertAlmostEqual(m["duration_seconds"], 30.10, places=2)

    def test_parse_output_with_errors(self):
        output = "5 passed, 1 error in 2.34s"
        m = parse_pytest_metrics(output)
        self.assertEqual(m["passed"], 5)
        self.assertEqual(m["errors"], 1)
        self.assertEqual(m["collected"], 6)
        self.assertAlmostEqual(m["duration_seconds"], 2.34, places=2)

    def test_parse_output_with_explicit_collected_line(self):
        output = "collected 120 items\n\n................\n110 passed, 10 skipped in 4.50s"
        m = parse_pytest_metrics(output)
        self.assertEqual(m["collected"], 120)
        self.assertEqual(m["passed"], 110)
        self.assertEqual(m["skipped"], 10)
        self.assertEqual(m["failed"], 0)
        self.assertAlmostEqual(m["duration_seconds"], 4.50, places=2)

    def test_parse_verbose_mode_output(self):
        output = "=== 10 passed in 1.23s ==="
        m = parse_pytest_metrics(output)
        self.assertEqual(m["passed"], 10)
        self.assertEqual(m["skipped"], 0)
        self.assertEqual(m["collected"], 10)
        self.assertAlmostEqual(m["duration_seconds"], 1.23, places=2)

    def test_parse_empty_or_malformed_output(self):
        m = parse_pytest_metrics("")
        self.assertEqual(m["collected"], 0)
        self.assertEqual(m["passed"], 0)
        self.assertEqual(m["failed"], 0)
        self.assertEqual(m["duration_seconds"], 0.0)

        m2 = parse_pytest_metrics("some unrelated random log text\nno pytest summary here")
        self.assertEqual(m2["passed"], 0)
        self.assertEqual(m2["collected"], 0)

    def test_alias_compatibility(self):
        output = "10 passed in 0.50s"
        m = parse_pytest_output(output)
        self.assertEqual(m["passed"], 10)

    def test_parse_ansi_colored_output_standard(self):
        """Verifies parsing pytest summary lines decorated with ANSI color codes."""
        output = "\x1b[32m\x1b[1m968 passed\x1b[0m, \x1b[33m4 skipped\x1b[0m\x1b[32m in 58.57s\x1b[0m"
        m = parse_pytest_metrics(output)
        self.assertEqual(m["passed"], 968)
        self.assertEqual(m["skipped"], 4)
        self.assertEqual(m["failed"], 0)
        self.assertEqual(m["collected"], 972)
        self.assertAlmostEqual(m["duration_seconds"], 58.57, places=2)

    def test_parse_ansi_colored_output_with_failures_and_errors(self):
        """Verifies parsing ANSI colored summary containing failures and errors."""
        output = "\x1b[31m\x1b[1m2 failed\x1b[0m, \x1b[32m950 passed\x1b[0m, \x1b[33m4 skipped\x1b[0m, \x1b[31m1 error\x1b[0m in 45.10s"
        m = parse_pytest_metrics(output)
        self.assertEqual(m["failed"], 2)
        self.assertEqual(m["passed"], 950)
        self.assertEqual(m["skipped"], 4)
        self.assertEqual(m["errors"], 1)
        self.assertEqual(m["collected"], 957)
        self.assertAlmostEqual(m["duration_seconds"], 45.10, places=2)

    def test_parse_ansi_colored_output_with_xfailed_and_subtests(self):
        """Verifies parsing ANSI colored summary with xfailed, xpassed, and subtests."""
        output = "\x1b[32m950 passed\x1b[0m, \x1b[33m4 skipped\x1b[0m, \x1b[35m2 xfailed\x1b[0m, \x1b[36m1 xpassed\x1b[0m, \x1b[32m48 subtests passed\x1b[0m in 30.10s"
        m = parse_pytest_metrics(output)
        self.assertEqual(m["passed"], 950)
        self.assertEqual(m["skipped"], 4)
        self.assertEqual(m["xfailed"], 2)
        self.assertEqual(m["xpassed"], 1)
        self.assertEqual(m["subtests_passed"], 48)
        self.assertEqual(m["collected"], 957)
        self.assertAlmostEqual(m["duration_seconds"], 30.10, places=2)

    def test_parse_ansi_colored_output_all_failures_no_pass(self):
        """Verifies parsing ANSI colored summary where all tests failed."""
        output = "\x1b[31m5 failed\x1b[0m\x1b[31m in 2.10s\x1b[0m"
        m = parse_pytest_metrics(output)
        self.assertEqual(m["failed"], 5)
        self.assertEqual(m["passed"], 0)
        self.assertEqual(m["collected"], 5)
        self.assertAlmostEqual(m["duration_seconds"], 2.10, places=2)


class TestCoverageFloorCalibration(unittest.TestCase):
    """Verifies coverage configuration floor calibrated to 60% and progression towards 80%."""

    def test_pyproject_fail_under_threshold(self):
        pyproject_path = os.path.join(REPO_ROOT, "pyproject.toml")
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify fail_under = 60
        match = re.search(r'\[tool\.coverage\.report\][^\[]*?fail_under\s*=\s*(\d+)', content, re.DOTALL)
        self.assertIsNotNone(match, "Could not find [tool.coverage.report] fail_under in pyproject.toml")
        fail_under_val = int(match.group(1))
        self.assertEqual(fail_under_val, 60, f"fail_under should be 60, but got {fail_under_val}")

        # Verify progression comments
        self.assertIn("60%", content)
        self.assertIn("80%", content)

    def test_pyproject_coverage_precision(self):
        """Verifies precision = 2 in [tool.coverage.report] to prevent rounding bypass."""
        pyproject_path = os.path.join(REPO_ROOT, "pyproject.toml")
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()

        match = re.search(r'\[tool\.coverage\.report\][^\[]*?precision\s*=\s*(\d+)', content, re.DOTALL)
        self.assertIsNotNone(match, "Could not find precision in [tool.coverage.report]")
        self.assertEqual(int(match.group(1)), 2, "precision must be 2")

    def test_coverage_precision_boundary_behavior(self):
        """Verifies that precision=2 strictly rejects 59.90% and 59.99% against fail_under=60."""
        from coverage.results import should_fail_under
        # Without precision (precision=0), 59.90% rounds to 60.0 and bypasses
        self.assertFalse(should_fail_under(59.90, 60, precision=0), "precision=0 incorrectly allows 59.90%")
        # With precision=2, 59.90% and 59.99% strictly fail
        self.assertTrue(should_fail_under(59.90, 60, precision=2), "precision=2 must fail 59.90%")
        self.assertTrue(should_fail_under(59.99, 60, precision=2), "precision=2 must fail 59.99%")
        # 60.00% passes
        self.assertFalse(should_fail_under(60.00, 60, precision=2), "precision=2 must pass 60.00%")

    def test_pyproject_line_vs_branch_coverage_distinction(self):
        """Verifies Requirement R4: explicit branch=false line coverage scope and mutation-tested branch scope."""
        pyproject_path = os.path.join(REPO_ROOT, "pyproject.toml")
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()

        sec_match = re.search(r'\[tool\.coverage\.run\](.*?)(?=\n\[|\Z)', content, re.DOTALL)
        self.assertIsNotNone(sec_match, "Could not find [tool.coverage.run] section")
        sec_content = sec_match.group(1)
        match = re.search(r'branch\s*=\s*(false|true)', sec_content, re.IGNORECASE)
        self.assertIsNotNone(match, "Could not find explicit branch setting in [tool.coverage.run]")
        self.assertEqual(match.group(1).lower(), "false", "Global coverage must specify branch = false for line scope")
        self.assertIn("Requirement R4", content, "Must document Requirement R4 line vs branch coverage scope distinction")


class TestBadgesSynchronization(unittest.TestCase):
    """Verifies that README test count badges reflect current actual passed test count (1,001+ passing)."""

    def test_readme_test_count_badge(self):
        readme_path = os.path.join(REPO_ROOT, "README.md")
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("tests-1001%2B%20passing", content)
        self.assertNotIn("tests-950%2B%20passing", content)

    def test_readme_en_test_count_badge(self):
        readme_en_path = os.path.join(REPO_ROOT, "README.en.md")
        with open(readme_en_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("tests-1001%2B%20passing", content)
        self.assertNotIn("tests-950%2B%20passing", content)


class TestMicroMutatorSyntaxGuards(unittest.TestCase):
    """Verifies operator replacement regex syntax guards and Python syntax validation."""

    def test_identity_inversion_prevents_is_not_not_none(self):
        sample_code = """
def check_val(x):
    if x is not None:
        return True
    return False
"""
        mutants = generate_mutants_for_code(sample_code, file_path="sample.py")
        mutated_snippets = [m["mutated_snippet"] for m in mutants]

        # Ensure NO mutant generated "is not not None"
        for snip in mutated_snippets:
            self.assertNotIn("is not not None", snip, f"Invalid mutant generated: {snip}")

        # Ensure valid mutation "is None" was generated
        has_is_none = any("x is None" in snip for snip in mutated_snippets)
        self.assertTrue(has_is_none, f"Expected 'x is None' mutant, got: {mutated_snippets}")

        # Verify all mutants compile without SyntaxError
        for m in mutants:
            try:
                compile(m["mutated_code"], "sample.py", "exec")
            except SyntaxError as e:
                self.fail(f"Mutant {m['id']} produced invalid Python syntax: {e}")

    def test_identity_inversion_on_is_none(self):
        sample_code = """
def check_empty(val):
    if val is None:
        return 0
    return 1
"""
        mutants = generate_mutants_for_code(sample_code, file_path="sample.py")
        mutated_snippets = [m["mutated_snippet"] for m in mutants]

        has_is_not_none = any("val is not None" in snip for snip in mutated_snippets)
        self.assertTrue(has_is_not_none, f"Expected 'val is not None' mutant, got: {mutated_snippets}")

        for m in mutants:
            compile(m["mutated_code"], "sample.py", "exec")

    def test_scoped_test_cmd_resolves_convention_tests(self):
        from tools.micro_mutator import resolve_scoped_test_cmd
        cmd, impacted = resolve_scoped_test_cmd("pytest {test_files}", "tools/pentest_scope_guard.py")
        self.assertIn("tests/test_pentest_scope_guard.py", cmd)
        self.assertIn("tests/test_pentest_scope_guard.py", impacted)

    def test_scoped_test_cmd_fallback_glob_unmapped_module(self):
        """Verifies Fallback 2 handles unmapped modules without crashing (no NameError for glob)."""
        from tools.micro_mutator import resolve_scoped_test_cmd
        cmd, impacted = resolve_scoped_test_cmd("pytest {test_files}", "tools/nonexistent_module_xyz.py")
        self.assertEqual(impacted, [])
        self.assertEqual(cmd, "pytest")

    def test_scoped_test_cmd_fallback_glob_real_unmapped_tool(self):
        """Verifies Fallback 2 on existing repo tool lacking 1:1 test name (e.g. tools/api_fuzzer.py)."""
        from tools.micro_mutator import resolve_scoped_test_cmd
        cmd, impacted = resolve_scoped_test_cmd("pytest {test_files}", "tools/api_fuzzer.py")
        self.assertIsInstance(cmd, str)
        self.assertIsInstance(impacted, list)

    def test_scoped_test_cmd_fallback_glob_wildcard_discovery(self):
        """Verifies Fallback 2 wildcard glob discovery matches test_*<mod>*.py when exact candidate is missing."""
        import tempfile
        from tools.micro_mutator import resolve_scoped_test_cmd
        with tempfile.TemporaryDirectory() as tmpdir:
            tests_dir = os.path.join(tmpdir, "tests")
            os.makedirs(tests_dir, exist_ok=True)
            tool_path = os.path.join(tmpdir, "tools", "custom_engine.py")
            os.makedirs(os.path.dirname(tool_path), exist_ok=True)
            with open(tool_path, "w") as f:
                f.write("def run(): pass\n")
            wildcard_test = os.path.join(tests_dir, "test_prefix_custom_engine_e2e.py")
            with open(wildcard_test, "w") as f:
                f.write("def test_it(): pass\n")

            cmd, impacted = resolve_scoped_test_cmd("pytest {test_files}", tool_path, repo_root=tmpdir)
            self.assertEqual(len(impacted), 1)
            self.assertEqual(impacted[0], "tests/test_prefix_custom_engine_e2e.py")
            self.assertIn("tests/test_prefix_custom_engine_e2e.py", cmd)


class TestGate8ScopedMutation(unittest.TestCase):
    """Verifies Gate 8 scoped dynamic mutation and zero-modified code handling."""

    def test_gate_8_scoped_dynamic_zero_targets(self):
        from unittest.mock import patch
        from tools.verify_all import gate_8_micro_mutator, LAST_GATE_METRICS

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "README.md\npyproject.toml\n"
            mock_run.return_value.returncode = 0
            # changed_only=True with no python files in tools/
            res = gate_8_micro_mutator(REPO_ROOT, mode="HUB", changed_only=True)
            self.assertTrue(res)
            self.assertEqual(LAST_GATE_METRICS.get("gate_8", {}).get("mode"), "DYNAMIC_SCOPED")


class TestGateJUnitXmlAndCommitSha(unittest.TestCase):
    """Verifies Git commit SHA retrieval and JUnit XML propagation of metrics."""

    def test_git_commit_sha_retrieval(self):
        sha = get_git_commit_sha()
        self.assertIsInstance(sha, str)
        self.assertTrue(len(sha) >= 7, f"SHA should be at least 7 characters, got: {sha}")
        self.assertNotEqual(sha, "unknown")

    def test_format_gates_junit_includes_metrics_and_properties(self):
        gate_results = [
            ("Gate 7: Static Defect Sentinel", True, "PASS"),
            ("Gate 8: Syntactic Mutation Sentinel", True, "PASS")
        ]
        gate_metrics = {
            "gate_7": {
                "collected": 956,
                "passed": 952,
                "skipped": 4,
                "failed": 0,
                "xfailed": 0,
                "duration_seconds": 15.20,
                "commit": "abcdef1234567890"
            }
        }
        xml = format_gates_junit(gate_results, repo_root=REPO_ROOT, gate_metrics=gate_metrics)
        self.assertIn('<testsuite name="synapse-quality-gates"', xml)
        self.assertIn('name="Gate_7"', xml)
        self.assertIn('time="15.20"', xml)
        self.assertIn('<property name="passed" value="952"/>', xml)
        self.assertIn('<property name="skipped" value="4"/>', xml)
        self.assertIn('<property name="commit" value="abcdef1234567890"/>', xml)
        self.assertIn('<system-out>', xml)
        self.assertIn('Hub regression test suite passed: 952 passed, 4 skipped in 15.20s (Git commit: abcdef1234567890).', xml)

    def test_format_gates_junit_reflects_failure_status(self):
        """Verifies that format_gates_junit records 'failed:' rather than 'passed:' when Gate 7 fails."""
        gate_results = [
            ("Gate 7: Static Defect Sentinel", False, "FAIL")
        ]
        gate_metrics = {
            "gate_7": {
                "collected": 100,
                "passed": 98,
                "skipped": 0,
                "failed": 2,
                "duration_seconds": 12.0,
                "commit": "abcdef1234567890"
            }
        }
        xml = format_gates_junit(gate_results, repo_root=REPO_ROOT, gate_metrics=gate_metrics)
        self.assertIn('<failure message="Quality Gate Failed: Gate 7: Static Defect Sentinel">', xml)
        self.assertIn('Hub regression test suite failed: 98 passed, 2 failed', xml)
        self.assertNotIn('Hub regression test suite passed:', xml)

    def test_format_gates_junit_parent_runner_active(self):
        """Verifies format_gates_junit correctly formats PARENT_RUNNER_ACTIVE status."""
        gate_results = [
            ("Gate 7: Static Defect Sentinel", True, "PASS")
        ]
        gate_metrics = {
            "gate_7": {
                "status": "PARENT_RUNNER_ACTIVE",
                "execution_mode": "PARENT_SESSION",
                "uncollected": True,
                "commit": "abcdef1234567890",
                "note": "Regression suite execution managed dynamically by active parent test runner"
            }
        }
        xml = format_gates_junit(gate_results, repo_root=REPO_ROOT, gate_metrics=gate_metrics)
        self.assertIn('Hub regression test suite passed: Regression suite execution managed dynamically by active parent test runner (Git commit: abcdef1234567890).', xml)
        self.assertIn('<property name="status" value="PARENT_RUNNER_ACTIVE"/>', xml)
        self.assertIn('<property name="uncollected" value="True"/>', xml)


class TestGate7MetricsIntegrity(unittest.TestCase):
    """Verifies that Gate 7 metrics are genuine, dynamically extracted, and free of hardcoded pass counts."""

    def test_gate_7_under_parent_runner_sets_uncollected_status_without_hardcoded_numbers(self):
        """Verifies that when running under pytest, Gate 7 sets PARENT_RUNNER_ACTIVE without hardcoding 952 passed."""
        from tools import verify_all

        verify_all.LAST_GATE_METRICS.pop("gate_7", None)
        res = verify_all.gate_7_infer_linter(REPO_ROOT, mode="HUB")
        self.assertTrue(res)
        g7 = verify_all.LAST_GATE_METRICS.get("gate_7", {})
        self.assertEqual(g7.get("status"), "PARENT_RUNNER_ACTIVE")
        self.assertTrue(g7.get("uncollected"))
        self.assertEqual(g7.get("passed"), 0)
        self.assertEqual(g7.get("collected"), 0)
        self.assertIn("active parent test runner", g7.get("note", ""))

    def test_zero_hardcoded_gate7_metrics_in_source(self):
        """Integrity regression guard: ensures verify_all.py contains zero hardcoded pass counts."""
        verify_all_path = os.path.join(REPO_ROOT, "tools", "verify_all.py")
        with open(verify_all_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertNotIn('"passed": 952', content, "Hardcoded metric 'passed': 952 must not exist in verify_all.py")
        self.assertNotIn('"collected": 956', content, "Hardcoded metric 'collected': 956 must not exist in verify_all.py")
        self.assertNotIn("'passed': 952", content, "Hardcoded metric 'passed': 952 must not exist in verify_all.py")
        self.assertNotIn("'collected': 956", content, "Hardcoded metric 'collected': 956 must not exist in verify_all.py")


if __name__ == "__main__":
    unittest.main()
