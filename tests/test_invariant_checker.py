#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_invariant_checker.py — 4-Scenario Battery for Invariant Sentinel
--------------------------------------------------------------------------
Validates Positive, Negative, Boundary, and CLI Flag scenarios for invariant_checker.py.
"""

import json
import os
import subprocess
import sys


from tools.lint.invariant_checker import evaluate_invariants


class TestInvariantCheckerPositive:
    def test_clean_rule_1_utf8_passes(self, tmp_path):
        clean_file = tmp_path / "clean.py"
        clean_file.write_text("x = 1\n", encoding="utf-8")
        report, code = evaluate_invariants(repo_root=str(tmp_path), rule_scope=1)
        assert code == 0
        assert report["status"] == "PASS"
        assert report["violations_count"] == 0

    def test_all_invariants_pass_on_synapse_hub(self):
        report, code = evaluate_invariants(rule_scope=1)
        assert code == 0
        assert report["status"] == "PASS"


class TestInvariantCheckerNegative:
    def test_bom_bytes_detected_as_violation(self, tmp_path):
        bom_file = tmp_path / "bad.py"
        bom_file.write_bytes(b"\xef\xbb\xbfx = 1\n")
        report, code = evaluate_invariants(repo_root=str(tmp_path), rule_scope=1)
        assert code == 1
        assert report["status"] == "VIOLATIONS_DETECTED"
        assert report["violations_count"] >= 1
        assert report["violations"][0]["rule"] == 1

    def test_static_sleep_detected_in_tests(self, tmp_path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        sleep_file = tests_dir / "test_flaky.py"
        sleep_file.write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
        report, code = evaluate_invariants(repo_root=str(tmp_path), rule_scope=3)
        assert code == 1
        assert report["violations_count"] >= 1
        assert report["violations"][0]["rule"] == 3

    def test_rule_16_detects_non_english_text_in_skill_scripts(self, tmp_path):
        script_dir = tmp_path / "skills" / "06-healing-and-resilience" / "demo" / "scripts"
        script_dir.mkdir(parents=True)
        bad_sh = script_dir / "triage.sh"
        bad_sh.write_text("#!/usr/bin/env bash\necho 'Kiểm tra thất bại'\n", encoding="utf-8")
        report, code = evaluate_invariants(repo_root=str(tmp_path), rule_scope=16)
        assert code == 1
        assert report["violations_count"] >= 1
        assert report["violations"][0]["rule"] == 16

    def test_live_rule_16_passes_on_synapse_hub(self):
        report, code = evaluate_invariants(rule_scope=16)
        assert code == 0
        assert report["status"] == "PASS"


class TestInvariantCheckerBoundary:
    def test_empty_repo_directory(self, tmp_path):
        report, code = evaluate_invariants(repo_root=str(tmp_path), rule_scope=1)
        assert code == 0
        assert report["status"] == "PASS"

    def test_invalid_rule_number_defaults_safely(self, tmp_path):
        report, code = evaluate_invariants(repo_root=str(tmp_path), rule_scope=99)
        assert report["rules_checked"] == 1


class TestInvariantCheckerCLIFlags:
    def test_cli_json_flag(self):
        tool = os.path.join(os.path.dirname(__file__), "..", "tools", "lint", "invariant_checker.py")
        cmd = [sys.executable, tool, "--rule", "1", "--json"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        data = json.loads(res.stdout.strip())
        assert data["status"] == "PASS"
        assert data["rules_checked"] == 1

    def test_cli_human_output(self):
        tool = os.path.join(os.path.dirname(__file__), "..", "tools", "lint", "invariant_checker.py")
        cmd = [sys.executable, tool, "--rule", "1"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "[PASS]" in res.stdout
