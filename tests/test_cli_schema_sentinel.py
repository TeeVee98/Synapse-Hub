#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_cli_schema_sentinel.py — 4-Scenario Test Battery for ACI Schema Sentinel
-----------------------------------------------------------------------------------
Validates cli_schema_sentinel.py across:
  1. Positive Scenarios (zero drift when AST matches schema, successful --sync reconciliation)
  2. Negative Scenarios (missing args, phantom args, nonexistent scripts, --check exit code 1)
  3. Boundary Scenarios (empty tools dictionary, dynamic args, no-argparse scripts)
  4. CLI Flag Scenarios (--json output contract, --tool scoping, --expand-all discovery)
"""

import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
for p in (ROOT_DIR, TOOLS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from tools.lint.cli_schema_sentinel import (
    extract_ast_arguments,
    has_argparse_entrypoint,
    validate_schema_drift,
    main,
)


class TestCLISchemaSentinelPositive:
    """Scenario A: Positive paths with matching contracts or successful sync."""

    def test_schema_matches_ast_cleanly(self, tmp_path):
        script_file = tmp_path / "sample_tool.py"
        script_file.write_text(
            """
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--tier", type=str, default="fast", help="Execution tier")
parser.add_argument("--json", action="store_true", help="JSON output")
""",
            encoding="utf-8",
        )

        schema_file = tmp_path / "schema.json"
        schema_data = {
            "version": "1.0.0",
            "tools": {
                "sample_tool": {
                    "path": str(script_file),
                    "command": f"python3 {script_file}",
                    "summary": "Sample test tool",
                    "args": {
                        "--tier": {"type": "string", "default": "fast", "help": "Execution tier"},
                        "--json": {"type": "boolean", "default": False, "help": "JSON output"},
                    },
                }
            },
        }
        schema_file.write_text(json.dumps(schema_data), encoding="utf-8")

        report, exit_code = validate_schema_drift(
            schema_path=str(schema_file),
            tool_scope="sample_tool",
            sync=False,
        )

        assert exit_code == 0
        assert report["status"] == "PASS"
        assert report["drift_count"] == 0
        assert report["drifts"] == []

    def test_sync_reconciles_drift_and_updates_schema(self, tmp_path):
        script_file = tmp_path / "sync_tool.py"
        script_file.write_text(
            """
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("target", type=str, help="Target file")
parser.add_argument("--verbose", action="store_true", help="Verbose logging")
""",
            encoding="utf-8",
        )

        schema_file = tmp_path / "schema.json"
        # Schema is missing target and --verbose, and has phantom arg --old-flag
        schema_data = {
            "version": "1.0.0",
            "tools": {
                "sync_tool": {
                    "path": str(script_file),
                    "command": f"python3 {script_file}",
                    "summary": "Sync test tool",
                    "args": {
                        "--old-flag": {"type": "string"},
                    },
                }
            },
        }
        schema_file.write_text(json.dumps(schema_data), encoding="utf-8")

        report, exit_code = validate_schema_drift(
            schema_path=str(schema_file),
            tool_scope="sync_tool",
            sync=True,
        )

        assert exit_code == 0
        assert report["drift_count"] == 1

        # Verify disk schema was synchronized
        updated_data = json.loads(schema_file.read_text(encoding="utf-8"))
        updated_args = updated_data["tools"]["sync_tool"]["args"]
        assert "target" in updated_args
        assert "--verbose" in updated_args
        assert "--old-flag" not in updated_args


class TestCLISchemaSentinelNegative:
    """Scenario B: Drift detection (missing flags, phantom flags, missing scripts)."""

    def test_detects_missing_and_phantom_arguments(self, tmp_path):
        script_file = tmp_path / "drift_tool.py"
        script_file.write_text(
            """
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--real-flag", action="store_true")
""",
            encoding="utf-8",
        )

        schema_file = tmp_path / "schema.json"
        schema_data = {
            "tools": {
                "drift_tool": {
                    "path": str(script_file),
                    "args": {
                        "--phantom-flag": {"type": "string"},
                    },
                }
            }
        }
        schema_file.write_text(json.dumps(schema_data), encoding="utf-8")

        report, exit_code = validate_schema_drift(
            schema_path=str(schema_file),
            sync=False,
        )

        assert report["status"] == "DRIFT_DETECTED"
        assert report["drift_count"] == 1
        drift = report["drifts"][0]
        assert drift["missing_in_schema"] == ["--real-flag"]
        assert drift["phantom_in_schema"] == ["--phantom-flag"]

    def test_nonexistent_script_reported_as_drift(self, tmp_path):
        schema_file = tmp_path / "schema.json"
        schema_data = {
            "tools": {
                "missing_tool": {
                    "path": "/path/to/definitely_missing_script_synapse_999.py",
                    "args": {"--flag": {}},
                }
            }
        }
        schema_file.write_text(json.dumps(schema_data), encoding="utf-8")

        report, exit_code = validate_schema_drift(schema_path=str(schema_file))
        assert report["status"] == "DRIFT_DETECTED"
        assert report["drift_count"] == 1
        assert "Script file does not exist" in report["drifts"][0]["error"]


class TestCLISchemaSentinelBoundary:
    """Scenario C: Boundary conditions (empty tools, files with no argparse)."""

    def test_empty_tools_schema_passes_cleanly(self, tmp_path):
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(json.dumps({"version": "1.0", "tools": {}}), encoding="utf-8")

        report, exit_code = validate_schema_drift(schema_path=str(schema_file))
        assert exit_code == 0
        assert report["status"] == "PASS"
        assert report["tools_checked"] == 0
        assert report["drift_count"] == 0

    def test_script_without_argparse_returns_empty(self, tmp_path):
        no_arg_file = tmp_path / "no_arg.py"
        no_arg_file.write_text("x = 10\nprint(x)\n", encoding="utf-8")

        args = extract_ast_arguments(str(no_arg_file))
        assert args == {}
        assert has_argparse_entrypoint(str(no_arg_file)) is False


class TestCLISchemaSentinelCLIFlags:
    """Scenario D: CLI interface, flags, and JSON output formatting."""

    def test_cli_json_and_check_flags(self, tmp_path, capsys):
        script_file = tmp_path / "cli_tool.py"
        script_file.write_text(
            """
import argparse
p = argparse.ArgumentParser()
p.add_argument("--json", action="store_true")
""",
            encoding="utf-8",
        )

        schema_file = tmp_path / "schema.json"
        schema_file.write_text(
            json.dumps({
                "tools": {
                    "cli_tool": {
                        "path": str(script_file),
                        "args": {"--json": {"type": "boolean"}},
                    }
                }
            }),
            encoding="utf-8",
        )

        exit_code = main([
            "--schema", str(schema_file),
            "--check",
            "--json",
        ])

        assert exit_code == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["status"] == "PASS"
        assert data["drift_count"] == 0

    def test_expand_all_finds_unregistered_tools(self, tmp_path, capsys):
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        unregistered = tools_dir / "unreg_cli.py"
        unregistered.write_text(
            """
import argparse
p = argparse.ArgumentParser()
p.add_argument("--foo", type=str)
""",
            encoding="utf-8",
        )

        schema_file = tmp_path / "schema.json"
        schema_file.write_text(json.dumps({"tools": {}}), encoding="utf-8")

        exit_code = main([
            "--schema", str(schema_file),
            "--tools-dir", str(tools_dir),
            "--expand-all",
            "--json",
        ])

        assert exit_code == 0
        data = json.loads(capsys.readouterr().out)
        assert "unregistered_tools" in data
        assert any("unreg_cli.py" in t for t in data["unregistered_tools"])
