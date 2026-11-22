#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_debug_crumbs.py — 4-Scenario Test Battery for Debug Crumbs Engine
----------------------------------------------------------------------------
Validates debug_crumbs.py across:
  1. Positive Scenarios (clean directory scanning, successful in-place crumb stripping)
  2. Negative Scenarios (single crumb detection, region crumb detection, --check exit code 1)
  3. Boundary Scenarios (empty files, boundary lines, multiple comment syntaxes)
  4. CLI Flag Scenarios (--json output contract, --dir file targeting, --strip execution)
"""

import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
for p in (ROOT_DIR, TOOLS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from tools.core.debug_crumbs import (
    scan_file_for_crumbs,
    strip_crumbs_from_file,
    process_crumbs,
    main,
)


class TestDebugCrumbsPositive:
    """Scenario A: Clean codebases and successful stripping."""

    def test_clean_directory_returns_clean_status(self, tmp_path):
        f1 = tmp_path / "module_a.py"
        f1.write_text("def hello():\n    return 'clean'\n", encoding="utf-8")

        f2 = tmp_path / "module_b.ts"
        f2.write_text("export const PI = 3.14159;\n", encoding="utf-8")

        report, exit_code = process_crumbs(target_path=str(tmp_path), check=True)

        assert exit_code == 0
        assert report["status"] == "CLEAN"
        assert report["crumbs_count"] == 0
        assert report["locations"] == []

    def test_strip_removes_crumbs_and_preserves_clean_code(self, tmp_path):
        f = tmp_path / "dirty.py"
        original_code = (
            "def calculate(x, y):\n"
            "    print(f'DEBUG: x={x}')  # @crumbs\n"
            "    # region @crumbs\n"
            "    temp = x * 2\n"
            "    print(temp)\n"
            "    # endregion @crumbs\n"
            "    return x + y\n"
        )
        f.write_text(original_code, encoding="utf-8")

        # Strip crumbs
        report, exit_code = process_crumbs(target_path=str(tmp_path), strip=True)

        assert exit_code == 0
        assert report["status"] == "CRUMBS_STRIPPED"
        assert report["crumbs_count"] == 5  # 1 single-line + 4 region lines

        # Verify disk content is completely clean
        clean_code = f.read_text(encoding="utf-8")
        assert "@crumbs" not in clean_code
        assert "def calculate(x, y):" in clean_code
        assert "return x + y" in clean_code

        # Subsequent scan should be 100% CLEAN
        verify_report, verify_code = process_crumbs(target_path=str(tmp_path), check=True)
        assert verify_code == 0
        assert verify_report["status"] == "CLEAN"


class TestDebugCrumbsNegative:
    """Scenario B: Crumb detection and check failure modes."""

    def test_single_line_crumb_detected_with_exit_code_1(self, tmp_path):
        f = tmp_path / "probe.py"
        f.write_text("def run():\n    print('probe')  # @crumbs: temporary\n", encoding="utf-8")

        report, exit_code = process_crumbs(target_path=str(tmp_path), check=True)

        assert exit_code == 1
        assert report["status"] == "CRUMBS_DETECTED"
        assert report["crumbs_count"] == 1
        assert report["locations"][0]["line"] == 2
        assert "# @crumbs" in report["locations"][0]["crumb"]

    def test_multiline_region_crumb_detected(self, tmp_path):
        f = tmp_path / "region.ts"
        f.write_text(
            "// #region @crumbs\n"
            "console.log('trace 1');\n"
            "console.log('trace 2');\n"
            "// #endregion @crumbs\n",
            encoding="utf-8",
        )

        report, exit_code = process_crumbs(target_path=str(f), check=True)

        assert exit_code == 1
        assert report["status"] == "CRUMBS_DETECTED"
        assert report["crumbs_count"] == 4

    def test_nonexistent_target_fails_gracefully(self):
        report, exit_code = process_crumbs(target_path="__non_existent_path_xyz__")
        assert exit_code == 1
        assert "does not exist" in report["message"]


class TestDebugCrumbsBoundary:
    """Scenario C: Boundary conditions, comment styles, and empty files."""

    def test_empty_file_handled_cleanly(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("", encoding="utf-8")

        crumbs = scan_file_for_crumbs(str(f))
        assert crumbs == []

        stripped = strip_crumbs_from_file(str(f))
        assert stripped == 0

    def test_various_comment_syntaxes_supported(self, tmp_path):
        samples = [
            ("python.py", "# @crumbs: probe\n"),
            ("typescript.ts", "// @crumbs: probe\n"),
            ("style.css", "/* @crumbs */ body { color: red; }\n"),
            ("markup.html", "<!-- @crumbs --> <div>Test</div>\n"),
            ("bracket.py", "# [crumbs] trace\n"),
        ]

        for filename, content in samples:
            f = tmp_path / filename
            f.write_text(content, encoding="utf-8")
            crumbs = scan_file_for_crumbs(str(f))
            assert len(crumbs) == 1, f"Failed to detect crumb in {filename}"

    def test_strip_on_already_clean_file_is_noop(self, tmp_path):
        f = tmp_path / "noop.py"
        f.write_text("a = 1\nb = 2\n", encoding="utf-8")

        report, exit_code = process_crumbs(target_path=str(f), strip=True)
        assert exit_code == 0
        assert report["status"] == "CLEAN"
        assert report["crumbs_count"] == 0


class TestDebugCrumbsCLIFlags:
    """Scenario D: CLI interface, flags, and JSON output formatting."""

    def test_cli_json_and_check_flags(self, tmp_path, capsys):
        f = tmp_path / "cli_check.py"
        f.write_text("x = 100  # @crumbs\n", encoding="utf-8")

        exit_code = main([
            "--dir", str(f),
            "--check",
            "--json",
        ])

        assert exit_code == 1
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["status"] == "CRUMBS_DETECTED"
        assert data["crumbs_count"] == 1

    def test_cli_strip_flag_json(self, tmp_path, capsys):
        f = tmp_path / "cli_strip.py"
        f.write_text("y = 200  # @crumbs\n", encoding="utf-8")

        exit_code = main([
            "--dir", str(f),
            "--strip",
            "--json",
        ])

        assert exit_code == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["status"] == "CRUMBS_STRIPPED"
        assert data["crumbs_count"] == 1
        assert str(f) in data["modified_files"]

    def test_cli_human_output_formatting(self, tmp_path, capsys):
        f = tmp_path / "human.py"
        f.write_text("clean = True\n", encoding="utf-8")

        exit_code = main([
            "--dir", str(f),
            "--check",
        ])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "[CLEAN]" in out
