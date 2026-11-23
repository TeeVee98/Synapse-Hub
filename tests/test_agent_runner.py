#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_agent_runner.py — 4-Scenario Test Battery for Context-Shielded Agent Runner
-------------------------------------------------------------------------------------
Validates agent_runner.py across:
  1. Positive Scenarios (successful process execution, log generation, <60 token summary)
  2. Negative Scenarios (exit code preservation, failure excerpt extraction, missing binary)
  3. Boundary Scenarios (empty command, watch/interactive trap guard, process timeout termination)
  4. CLI Flag Scenarios (--json formatting, --allow-watch override, custom --label and --log-dir)
"""

import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
for p in (ROOT_DIR, TOOLS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from tools.core.agent_runner import (
    execute_agent_run,
    detect_watch_flags,
    extract_failure_excerpt,
    main,
)


class TestAgentRunnerPositive:
    """Scenario A: Positive paths with successful command execution."""

    def test_successful_command_execution(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        cmd = [sys.executable, "-c", "print('Hello Synapse Agent'); print('Line 2')"]

        result = execute_agent_run(
            command=cmd,
            timeout_sec=10.0,
            log_dir=log_dir,
            label="positive_test",
        )

        assert result["status"] == "PASSED"
        assert result["exit_code"] == 0
        assert result["duration_sec"] >= 0.0
        assert os.path.isfile(result["log_path"])
        assert result["failure_excerpt"] == []
        assert "completed successfully" in result["summary"]

        with open(result["log_path"], "r", encoding="utf-8") as f:
            content = f.read()
        assert "Hello Synapse Agent" in content
        assert "Line 2" in content

    def test_summary_under_60_tokens_token_budget(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        cmd = [sys.executable, "-c", "print('OK')"]

        result = execute_agent_run(
            command=cmd,
            timeout_sec=5.0,
            log_dir=log_dir,
        )

        summary_words = result["summary"].split()
        # Word count is strict upper bound for token count in simple English
        assert len(summary_words) < 30
        assert result["status"] == "PASSED"


class TestAgentRunnerNegative:
    """Scenario B: Negative paths with failures, exit codes, and excerpts."""

    def test_failed_command_captures_exit_code_and_excerpt(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        cmd = [
            sys.executable,
            "-c",
            "import sys; sys.stderr.write('Fatal DB connection failed\\n'); sys.exit(42)",
        ]

        result = execute_agent_run(
            command=cmd,
            timeout_sec=10.0,
            log_dir=log_dir,
            label="fail_test",
            max_excerpt=5,
        )

        assert result["status"] == "FAILED"
        assert result["exit_code"] == 42
        assert os.path.isfile(result["log_path"])
        assert len(result["failure_excerpt"]) >= 1
        assert any("Fatal DB connection failed" in line for line in result["failure_excerpt"])
        assert "exit code 42" in result["summary"]

    def test_nonexistent_binary_returns_127_without_crash(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        cmd = ["__definitely_non_existent_binary_synapse_999__", "--flag"]

        result = execute_agent_run(
            command=cmd,
            timeout_sec=5.0,
            log_dir=log_dir,
        )

        assert result["status"] == "FAILED"
        assert result["exit_code"] == 127
        assert "Command not found" in result["summary"]
        assert len(result["failure_excerpt"]) == 1


class TestAgentRunnerBoundary:
    """Scenario C: Boundary conditions, watch traps, timeouts, and limits."""

    def test_empty_command_fails_gracefully(self):
        result = execute_agent_run(command=[])
        assert result["status"] == "FAILED"
        assert result["exit_code"] == 2
        assert "No command specified" in result["summary"]

    def test_watch_flag_circuit_breaker_intercepts_before_spawning(self, tmp_path):
        log_dir = str(tmp_path / "logs")

        # Test various watch tokens
        watch_cmds = [
            ["pytest", "--watch"],
            ["pnpm", "test", "-w"],
            ["jest", "--watchAll"],
            ["npm", "run", "test:watch"],
            ["npm", "run", "dev:ui"],
        ]

        for cmd in watch_cmds:
            offending = detect_watch_flags(cmd)
            assert offending is not None

            result = execute_agent_run(
                command=cmd,
                log_dir=log_dir,
                allow_watch=False,
            )
            assert result["status"] == "FAILED"
            assert result["exit_code"] == 2
            assert "Blocked by agent safety guard" in result["summary"]
            # Zero log file created since process was blocked before spawn
            assert result["log_path"] == ""

    def test_process_timeout_cleanly_terminates_and_returns_124(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        # Command that would hang without timeout
        cmd = [
            sys.executable,
            "-c",
            "import time; time.sleep(10)",
        ]

        result = execute_agent_run(
            command=cmd,
            timeout_sec=0.5,
            log_dir=log_dir,
            label="timeout_test",
        )

        assert result["status"] == "TIMEOUT"
        assert result["exit_code"] == 124
        assert "timed out after 0.5s" in result["summary"]
        assert os.path.isfile(result["log_path"])

    def test_excerpt_truncation_boundary(self):
        long_log = "\n".join([f"Log line {i}" for i in range(100)])
        excerpt = extract_failure_excerpt(long_log, max_lines=15)
        assert len(excerpt) == 15
        assert excerpt[-1] == "Log line 99"


class TestAgentRunnerCLIFlags:
    """Scenario D: CLI interface, flags, and JSON output formatting."""

    def test_cli_json_flag_output(self, tmp_path, capsys):
        log_dir = str(tmp_path / "logs")
        exit_code = main([
            "--json",
            "--log-dir", log_dir,
            "--label", "cli_json",
            "--",
            sys.executable, "-c", "print('JSON CLI Output Test')",
        ])

        assert exit_code == 0
        captured = capsys.readouterr().out
        data = json.loads(captured)
        assert data["status"] == "PASSED"
        assert data["exit_code"] == 0
        assert "JSON CLI Output Test" in open(data["log_path"]).read()

    def test_cli_allow_watch_override(self, tmp_path, capsys):
        log_dir = str(tmp_path / "logs")
        # With --allow-watch, runner does not block watch flag
        exit_code = main([
            "--allow-watch",
            "--json",
            "--log-dir", log_dir,
            "--",
            sys.executable, "-c", "import sys; print('Watch allowed'); sys.exit(0)", "--watch",
        ])

        assert exit_code == 0
        data = json.loads(capsys.readouterr().out)
        assert data["status"] == "PASSED"

    def test_cli_non_json_human_output(self, tmp_path, capsys):
        log_dir = str(tmp_path / "logs")
        exit_code = main([
            "--log-dir", log_dir,
            "--",
            sys.executable, "-c", "print('Human Output Test')",
        ])
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "[PASSED]" in out
        assert "Log:" in out

    def test_ast_command_guard_intercepts_destructive_command(self, tmp_path):
        res = execute_agent_run(["rm", "-rf", "/"], log_dir=str(tmp_path))
        assert res["status"] == "FAILED"
        assert res["exit_code"] == 2
        assert "Blocked by AST command safety guard" in res["summary"]

    def test_output_offloader_integrated_on_large_output(self, tmp_path):
        # Generate large output > 2KB
        script = "print('X' * 3000)"
        res = execute_agent_run([sys.executable, "-c", script], log_dir=str(tmp_path))
        assert res["status"] == "PASSED"
        assert res["offloaded"] is not None
        assert res["offloaded"]["total_bytes"] >= 3000
