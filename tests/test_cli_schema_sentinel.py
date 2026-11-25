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


class TestCLISchemaSentinelDeepDriftAndClassification:
    """M7: Deep field-level drift (type, required, default, choices) and public vs excluded_internal_tools."""

    def test_detects_type_required_default_choices_field_drifts(self, tmp_path):
        script_file = tmp_path / "deep_tool.py"
        script_file.write_text(
            """
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--count", type=int, default=5, required=True)
parser.add_argument("--provider", type=str, default="anthropic", choices=["anthropic", "openai"])
""",
            encoding="utf-8",
        )

        schema_file = tmp_path / "schema.json"
        schema_data = {
            "tools": {
                "deep_tool": {
                    "path": str(script_file),
                    "args": {
                        "--count": {"type": "string", "default": 10, "required": False},
                        "--provider": {"type": "str", "default": "gemini", "choices": ["gemini", "openai"]},
                    },
                }
            }
        }
        schema_file.write_text(json.dumps(schema_data), encoding="utf-8")

        report, exit_code = validate_schema_drift(schema_path=str(schema_file), sync=False)
        assert exit_code == 1
        assert report["status"] == "DRIFT_DETECTED"
        assert report["drift_count"] == 1
        assert "field_drifts" in report
        fields_found = {(d["arg"], d["field"]) for d in report["field_drifts"]}
        assert ("--count", "type") in fields_found
        assert ("--count", "required") in fields_found
        assert ("--count", "default") in fields_found
        assert ("--provider", "type") in fields_found
        assert ("--provider", "default") in fields_found
        assert ("--provider", "choices") in fields_found

    def test_sync_reconciles_field_level_drift(self, tmp_path):
        script_file = tmp_path / "sync_deep.py"
        script_file.write_text(
            """
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["fast", "full"], default="fast", required=True)
""",
            encoding="utf-8",
        )

        schema_file = tmp_path / "schema.json"
        schema_file.write_text(
            json.dumps({
                "tools": {
                    "sync_deep": {
                        "path": str(script_file),
                        "args": {
                            "--mode": {"type": "integer", "choices": ["slow"], "default": "slow", "required": False},
                        },
                    }
                }
            }),
            encoding="utf-8",
        )

        report, exit_code = validate_schema_drift(schema_path=str(schema_file), sync=True)
        assert exit_code == 0
        assert report["drift_count"] == 1

        recheck_report, recheck_code = validate_schema_drift(schema_path=str(schema_file), sync=False)
        assert recheck_code == 0
        assert recheck_report["status"] == "PASS"
        assert recheck_report["field_drifts"] == []

    def test_fail_unregistered_respects_excluded_internal_tools_and_flags_public(self, tmp_path):
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        internal_cli = tools_dir / "internal_helper.py"
        internal_cli.write_text(
            "import argparse\np = argparse.ArgumentParser()\np.add_argument('--x')\n",
            encoding="utf-8",
        )
        public_cli = tools_dir / "new_public_tool.py"
        public_cli.write_text(
            "import argparse\np = argparse.ArgumentParser()\np.add_argument('--y')\n",
            encoding="utf-8",
        )

        schema_file = tmp_path / "schema.json"
        schema_file.write_text(
            json.dumps({
                "tools": {},
                "excluded_internal_tools": {
                    str(internal_cli): {"category": "helper", "classification": "internal_helper"}
                },
            }),
            encoding="utf-8",
        )

        report, exit_code = validate_schema_drift(
            schema_path=str(schema_file),
            tools_dir=str(tools_dir),
            fail_unregistered=True,
        )
        assert exit_code == 1
        assert report["status"] == "DRIFT_DETECTED"
        assert report["excluded_internal_count"] == 1
        assert len(report["unregistered_public"]) == 1
        assert "new_public_tool.py" in report["unregistered_public"][0]
        assert not any("internal_helper.py" in u for u in report["unregistered_public"])

    def test_subcommand_schema_drift_and_sync(self, tmp_path):
        from tools.lint.cli_schema_sentinel import extract_ast_subparsers

        script_file = tmp_path / "sub_tool.py"
        script_file.write_text(
            """
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", "--loud", action="store_true")
parser.add_argument("-h", "--help", action="help")
parser.add_argument(123)
sub = parser.add_subparsers(dest="cmd")
p_run = sub.add_parser("run", help="Run task")
p_run.add_argument("-t", "--target", required=True)
p_run.add_argument("-q", action="store_true")
p_info = sub.add_parser("info", help="Show info")
p_info.add_argument("item")
""",
            encoding="utf-8",
        )

        root_args, subs = extract_ast_subparsers(str(script_file))
        assert set(root_args.keys()) == {"--verbose"}
        assert "-h" not in root_args and "--help" not in root_args
        assert set(subs.keys()) == {"run", "info"}
        assert set(subs["run"].keys()) == {"--target", "-q"}
        assert set(subs["info"].keys()) == {"item"}

        schema_file = tmp_path / "schema.json"
        schema_file.write_text(
            json.dumps({
                "tools": {
                    "sub_tool": {
                        "path": str(script_file),
                        "args": {"--verbose": {"type": "boolean", "required": False}},
                        "subcommands": {
                            "run": {"args": {"--target": {"type": "string", "required": False}}},
                            "ghost": {"args": {}},
                        },
                    }
                }
            }),
            encoding="utf-8",
        )

        report, exit_code = validate_schema_drift(schema_path=str(schema_file), sync=False)
        assert exit_code == 1
        assert report["status"] == "DRIFT_DETECTED"
        assert report["drift_count"] == 1
        drift = report["drifts"][0]
        assert drift["missing_subcommands"] == ["info"]
        assert drift["phantom_subcommands"] == ["ghost"]
        assert any(fd["arg"] == "run:--target" and fd["field"] == "required" for fd in report["field_drifts"])

        sync_report, sync_code = validate_schema_drift(schema_path=str(schema_file), sync=True)
        assert sync_code == 0
        assert sync_report["drift_count"] == 1

        recheck_report, recheck_code = validate_schema_drift(schema_path=str(schema_file), sync=False)
        assert recheck_code == 0
        assert recheck_report["status"] == "PASS"

    def test_live_repo_schema_passes_deep_check_and_11_gates_summary(self):
        schema_path = os.path.join(ROOT_DIR, "tools", "tools_schema.json")
        schema_data = json.loads(open(schema_path, "r", encoding="utf-8").read())
        assert "11 Quality Gates" in schema_data["tools"]["verify_all"]["summary"]
        assert "excluded_internal_tools" in schema_data
        assert len(schema_data["excluded_internal_tools"]) >= 120

        expected_automation_tools = {
            "api_drift_sentinel", "api_fuzzer", "contract_validator", "e2e_flow_prober",
            "fuzz_payloads", "generate_api_matrix", "network_mock_shield", "pairwise_generator",
            "spec_drift_sentinel", "spec_reconciler", "vcr_cassette_guard",
            "assertion_optimizer", "ast_assertion_optimizer", "auto_heal", "ci_healing_hook",
            "heal_pr_automator", "lookup_xpath", "reversible_sandbox", "visual_som_helper",
            "action_bundler", "meta_tool_engine", "trajectory_compressor",
            "gherkin_suite", "omni_transpiler", "traffic_session_converter",
        }
        registered_tools = set(schema_data["tools"].keys())
        assert expected_automation_tools.issubset(registered_tools)
        for name in expected_automation_tools:
            rel_path = schema_data["tools"][name]["path"]
            assert rel_path not in schema_data["excluded_internal_tools"]

        agentless_subs = schema_data["tools"]["agentless_patcher"].get("subcommands", {})
        assert set(agentless_subs.keys()) == {"heal-failure", "localize-error", "generate-candidates"}
        assert agentless_subs["heal-failure"]["args"]["--error-log"]["required"] is True

        report, exit_code = validate_schema_drift(
            schema_path=schema_path,
            tools_dir=os.path.join(ROOT_DIR, "tools"),
            fail_unregistered=True,
        )
        assert exit_code == 0
        assert report["status"] == "PASS"
        assert report["field_drifts"] == []
        assert report["unregistered_public"] == []

