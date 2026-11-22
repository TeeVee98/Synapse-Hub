#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_ratchet_sentinel.py — 4-Scenario Test Battery for Monotonic Quality Ratchet
-------------------------------------------------------------------------------------
Validates ratchet_sentinel.py across:
  1. Positive Scenarios (findings match baseline, improvements locked in via --update)
  2. Negative Scenarios (quality regression, score drops, min-score breaches, malformed inputs)
  3. Boundary Scenarios (stale baseline without --update, initial baseline bootstrap, zero debt)
  4. CLI Flag Scenarios (--json output, --metric choices, --min-score enforcement)
"""

import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
for p in (ROOT_DIR, TOOLS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from tools.lint.ratchet_sentinel import (
    evaluate_ratchet,
    main,
)


class TestRatchetSentinelPositive:
    """Scenario A: Positive paths where quality is maintained or ratcheted down."""

    def test_findings_match_baseline_passes(self, tmp_path):
        findings_file = tmp_path / "findings.json"
        baseline_file = tmp_path / "baseline.json"

        findings_data = {"tools/file_a.py": 2, "tools/file_b.py": 1}
        baseline_data = {
            "metric": "defects",
            "total": 3,
            "files": {"tools/file_a.py": 2, "tools/file_b.py": 1},
        }

        findings_file.write_text(json.dumps(findings_data), encoding="utf-8")
        baseline_file.write_text(json.dumps(baseline_data), encoding="utf-8")

        report, exit_code = evaluate_ratchet(
            findings_path=str(findings_file),
            baseline_path=str(baseline_file),
            metric="defects",
            update=False,
        )

        assert exit_code == 0
        assert report["status"] == "PASS"
        assert report["delta"] == 0
        assert report["ratcheted"] is False
        assert report["regressions"] == {}

    def test_improvement_with_update_ratchets_down_baseline(self, tmp_path):
        findings_file = tmp_path / "findings.json"
        baseline_file = tmp_path / "baseline.json"

        # Improved: file_a dropped from 3 to 1 defect
        findings_data = {"tools/file_a.py": 1}
        baseline_data = {"metric": "defects", "total": 3, "files": {"tools/file_a.py": 3}}

        findings_file.write_text(json.dumps(findings_data), encoding="utf-8")
        baseline_file.write_text(json.dumps(baseline_data), encoding="utf-8")

        report, exit_code = evaluate_ratchet(
            findings_path=str(findings_file),
            baseline_path=str(baseline_file),
            metric="defects",
            update=True,
        )

        assert exit_code == 0
        assert report["status"] == "PASS"
        assert report["ratcheted"] is True
        assert report["improvements"]["tools/file_a.py"] == 2

        # Verify disk baseline was updated
        updated = json.loads(baseline_file.read_text(encoding="utf-8"))
        assert updated["total"] == 1
        assert updated["files"]["tools/file_a.py"] == 1

    def test_score_improvement_with_update_ratchets_up(self, tmp_path):
        findings_file = tmp_path / "score.json"
        baseline_file = tmp_path / "baseline.json"

        findings_file.write_text(json.dumps({"score": 92.5}), encoding="utf-8")
        baseline_file.write_text(json.dumps({"metric": "mutation-score", "score": 88.0}), encoding="utf-8")

        report, exit_code = evaluate_ratchet(
            findings_path=str(findings_file),
            baseline_path=str(baseline_file),
            metric="mutation-score",
            update=True,
        )

        assert exit_code == 0
        assert report["status"] == "PASS"
        assert report["ratcheted"] is True
        assert report["current_total"] == 92.5
        assert report["delta"] == 4.5


class TestRatchetSentinelNegative:
    """Scenario B: Negative paths (regressions, drops below floor, malformed input)."""

    def test_defect_regression_fails_with_exit_code_1(self, tmp_path):
        findings_file = tmp_path / "findings.json"
        baseline_file = tmp_path / "baseline.json"

        # Regressed: file_a went from 1 to 3 defects, and file_c is new
        findings_data = {"tools/file_a.py": 3, "tools/file_c.py": 2}
        baseline_data = {"metric": "defects", "total": 1, "files": {"tools/file_a.py": 1}}

        findings_file.write_text(json.dumps(findings_data), encoding="utf-8")
        baseline_file.write_text(json.dumps(baseline_data), encoding="utf-8")

        report, exit_code = evaluate_ratchet(
            findings_path=str(findings_file),
            baseline_path=str(baseline_file),
            metric="defects",
        )

        assert exit_code == 1
        assert report["status"] == "FAIL_REGRESSION"
        assert "file_a.py" in str(report["regressions"])
        assert "file_c.py" in str(report["regressions"])
        assert report["delta"] == 4

    def test_score_regression_fails(self, tmp_path):
        findings_file = tmp_path / "score.json"
        baseline_file = tmp_path / "baseline.json"

        findings_file.write_text(json.dumps({"score": 85.0}), encoding="utf-8")
        baseline_file.write_text(json.dumps({"metric": "coverage", "score": 90.0}), encoding="utf-8")

        report, exit_code = evaluate_ratchet(
            findings_path=str(findings_file),
            baseline_path=str(baseline_file),
            metric="coverage",
        )

        assert exit_code == 1
        assert report["status"] == "FAIL_REGRESSION"
        assert report["delta"] == -5.0

    def test_min_score_breach_fails(self, tmp_path):
        findings_file = tmp_path / "score.json"
        baseline_file = tmp_path / "baseline.json"

        findings_file.write_text(json.dumps({"score": 82.0}), encoding="utf-8")
        baseline_file.write_text(json.dumps({"score": 80.0}), encoding="utf-8")

        # Current 82.0 > baseline 80.0, but min_score requires 85.0
        report, exit_code = evaluate_ratchet(
            findings_path=str(findings_file),
            baseline_path=str(baseline_file),
            metric="mutation-score",
            min_score=85.0,
        )

        assert exit_code == 1
        assert report["status"] == "FAIL_REGRESSION"
        assert "below minimum required score" in report["message"]

    def test_missing_findings_file_fails_cleanly(self):
        report, exit_code = evaluate_ratchet(findings_path="__non_existent_findings__.json")
        assert exit_code == 1
        assert report["status"] == "FAIL_REGRESSION"
        assert "not found" in report["message"]


class TestRatchetSentinelBoundary:
    """Scenario C: Boundary conditions (stale baseline, uninitialized baseline)."""

    def test_stale_baseline_fails_without_update_flag(self, tmp_path):
        findings_file = tmp_path / "findings.json"
        baseline_file = tmp_path / "baseline.json"

        # 2 defects resolved! But caller did NOT pass --update
        findings_data = {"tools/file_a.py": 1}
        baseline_data = {"metric": "defects", "total": 3, "files": {"tools/file_a.py": 3}}

        findings_file.write_text(json.dumps(findings_data), encoding="utf-8")
        baseline_file.write_text(json.dumps(baseline_data), encoding="utf-8")

        report, exit_code = evaluate_ratchet(
            findings_path=str(findings_file),
            baseline_path=str(baseline_file),
            metric="defects",
            update=False,
        )

        assert exit_code == 1
        assert report["status"] == "FAIL_STALE_BASELINE"
        assert report["ratcheted"] is False
        assert "Baseline is stale!" in report["message"]

    def test_missing_baseline_fails_without_update_flag(self, tmp_path):
        findings_file = tmp_path / "findings.json"
        baseline_file = tmp_path / "non_existent_baseline.json"

        findings_file.write_text(json.dumps({"tools/file_a.py": 1}), encoding="utf-8")

        report, exit_code = evaluate_ratchet(
            findings_path=str(findings_file),
            baseline_path=str(baseline_file),
            metric="defects",
            update=False,
        )

        assert exit_code == 1
        assert report["status"] == "FAIL_STALE_BASELINE"
        assert "Run with --update to initialize" in report["message"]

    def test_initial_baseline_creation_with_update(self, tmp_path):
        findings_file = tmp_path / "findings.json"
        baseline_file = tmp_path / "new_baseline.json"

        findings_file.write_text(json.dumps({"tools/file_a.py": 2}), encoding="utf-8")

        report, exit_code = evaluate_ratchet(
            findings_path=str(findings_file),
            baseline_path=str(baseline_file),
            metric="defects",
            update=True,
        )

        assert exit_code == 0
        assert report["status"] == "PASS"
        assert report["ratcheted"] is True
        assert baseline_file.is_file()


class TestRatchetSentinelCLIFlags:
    """Scenario D: CLI flag tests, JSON formatting, and argument parsing."""

    def test_cli_json_output_contract(self, tmp_path, capsys):
        findings_file = tmp_path / "findings.json"
        baseline_file = tmp_path / "baseline.json"

        findings_file.write_text(json.dumps({"f1.py": 1}), encoding="utf-8")
        baseline_file.write_text(
            json.dumps({"metric": "defects", "total": 1, "files": {"f1.py": 1}}),
            encoding="utf-8",
        )

        exit_code = main([
            "--findings", str(findings_file),
            "--baseline", str(baseline_file),
            "--json",
        ])

        assert exit_code == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["status"] == "PASS"
        assert data["metric"] == "defects"
        assert data["baseline_total"] == 1
        assert data["current_total"] == 1

    def test_cli_human_output_formatting(self, tmp_path, capsys):
        findings_file = tmp_path / "findings.json"
        baseline_file = tmp_path / "baseline.json"

        findings_file.write_text(json.dumps({"f1.py": 1}), encoding="utf-8")
        baseline_file.write_text(
            json.dumps({"metric": "defects", "total": 1, "files": {"f1.py": 1}}),
            encoding="utf-8",
        )

        exit_code = main([
            "--findings", str(findings_file),
            "--baseline", str(baseline_file),
        ])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "[PASS]" in out
        assert "Metric: defects" in out
