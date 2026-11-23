#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/core/agent_runner.py — Context-Shielded Subprocess Runner & Diagnostic Filter
----------------------------------------------------------------------------------
Inspired by n8n agent-check.mjs and Grafana watch-trap guard.
Executes CLI commands in an isolated subprocess with stdout/stderr redirection to disk,
blocks infinite watch/interactive terminal hangs, enforces wall-clock timeouts, and
returns a token-budgeted JSON summary (< 60 tokens on pass, bounded 20-line excerpt on fail).
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import signal
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Enforce UTF-8 stdout/stderr encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Interactive / watch flag patterns to trap and block
_WATCH_FLAG_PATTERNS = [
    re.compile(r"^--watch(?:=.*)?$", re.IGNORECASE),
    re.compile(r"^-w$", re.IGNORECASE),
    re.compile(r"^--watch-?all(?:=.*)?$", re.IGNORECASE),
    re.compile(r"^--interactive$", re.IGNORECASE),
    re.compile(r"^-f$"),
    re.compile(r":(?:dev|watch|ui)(?::|$)", re.IGNORECASE),
]

_FAILURE_MARKERS = [
    re.compile(r"^FAILED\b", re.IGNORECASE),
    re.compile(r"^ERROR\b", re.IGNORECASE),
    re.compile(r"Traceback \(most recent call last\):"),
    re.compile(r"^AssertionError\b"),
    re.compile(r"^FAIL\b"),
]


def detect_watch_flags(command_args: List[str]) -> Optional[str]:
    """
    Scans command arguments for interactive or watch flags.
    Returns the offending flag/token if found, or None if clean.
    """
    for token in command_args:
        for pattern in _WATCH_FLAG_PATTERNS:
            if pattern.search(token):
                return token
    return None


def extract_failure_excerpt(full_text: str, max_lines: int = 20) -> List[str]:
    """
    Extracts a bounded, high-signal failure excerpt from raw execution output.
    Prioritizes failure markers (tracebacks, FAILED lines) or tails the last lines.
    """
    if not full_text.strip():
        return []

    lines = [line.rstrip() for line in full_text.splitlines()]
    if len(lines) <= max_lines:
        return lines

    # Look for known failure start markers
    failure_start_idx = -1
    for idx, line in enumerate(lines):
        for pattern in _FAILURE_MARKERS:
            if pattern.search(line.strip()):
                failure_start_idx = idx
                break
        if failure_start_idx != -1:
            break

    if failure_start_idx != -1 and failure_start_idx + max_lines <= len(lines):
        return lines[failure_start_idx : failure_start_idx + max_lines]

    # Otherwise return tail lines
    return lines[-max_lines:]


def execute_agent_run(
    command: List[str],
    timeout_sec: float = 60.0,
    log_dir: str = "reports/agent_runs",
    label: str = "run",
    max_excerpt: int = 20,
    allow_watch: bool = False,
    sandbox: str = "local",
) -> Dict[str, Any]:
    """
    Executes command with context shielding, watch traps, and log persistence.
    """
    if not command:
        return {
            "status": "FAILED",
            "command": "",
            "exit_code": 2,
            "duration_sec": 0.0,
            "log_path": "",
            "summary": "No command specified to execute.",
            "failure_excerpt": ["No command specified to execute."],
            "artifacts": [],
        }

    # Watch flag circuit breaker
    if not allow_watch:
        offending_flag = detect_watch_flags(command)
        if offending_flag:
            return {
                "status": "FAILED",
                "command": " ".join(command),
                "exit_code": 2,
                "duration_sec": 0.0,
                "log_path": "",
                "summary": f"Watch or interactive mode detected in command: '{offending_flag}'. Blocked by agent safety guard. Use --allow-watch to override.",
                "failure_excerpt": [
                    f"Watch or interactive mode detected in command: '{offending_flag}'. Blocked by agent safety guard. Use --allow-watch to override."
                ],
                "artifacts": [],
            }

    # AST command safety audit
    try:
        from tools.runtime.ast_command_guard import ASTCommandGuard

        audit_res = ASTCommandGuard().audit_command(command)
        if not audit_res.is_safe:
            return {
                "status": "FAILED",
                "command": " ".join(command),
                "exit_code": 2,
                "duration_sec": 0.0,
                "log_path": "",
                "summary": f"Blocked by AST command safety guard: {'; '.join(audit_res.violations)}.",
                "failure_excerpt": [f"AST Violations: {'; '.join(audit_res.violations)}"],
                "artifacts": [],
            }
    except (ImportError, Exception) as guard_err:
        sys.stderr.write(f"[WARN] ASTCommandGuard error: {guard_err}\n")

    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_label = re.sub(r"[^a-zA-Z0-9_-]", "_", label)
    log_filename = f"{timestamp}_{safe_label}.log"
    log_path = os.path.join(log_dir, log_filename)

    start_time = time.perf_counter()
    full_output = ""
    exit_code = 0
    status = "PASSED"
    executed_in_docker = False

    # Optional Docker Sandbox Execution
    if sandbox == "docker":
        try:
            from tools.runtime.docker_sandbox_runner import DockerSandboxRunner, SandboxConfig

            ds_config = SandboxConfig(timeout_sec=timeout_sec)
            dsr = DockerSandboxRunner(config=ds_config)
            if dsr.is_docker_available():
                docker_res = dsr.run_sandboxed(command)
                if docker_res.get("sandboxed"):
                    full_output = (docker_res.get("stdout") or "") + (docker_res.get("stderr") or "")
                    exit_code = docker_res.get("exit_code", 1)
                    status = docker_res.get("status", "FAILED")
                    executed_in_docker = True
        except (ImportError, Exception) as d_err:
            sys.stderr.write(f"[WARN] Docker sandbox runner error, falling back to local: {d_err}\n")

    # Local Process execution fallback/default
    if not executed_in_docker:
        is_posix = sys.platform != "win32"
        try:
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                start_new_session=is_posix,
            )
            try:
                full_output, _ = proc.communicate(timeout=timeout_sec)
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                # Terminate entire process tree
                if is_posix:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except Exception:
                        proc.kill()
                else:
                    proc.kill()
                full_output, _ = proc.communicate()
                exit_code = 124
                status = "TIMEOUT"

        except FileNotFoundError:
            duration_sec = round(time.perf_counter() - start_time, 2)
            return {
                "status": "FAILED",
                "command": " ".join(command),
                "exit_code": 127,
                "duration_sec": duration_sec,
                "log_path": "",
                "summary": f"Command not found: '{command[0]}'.",
                "failure_excerpt": [f"Command not found: '{command[0]}'."],
                "artifacts": [],
            }

    duration_sec = round(time.perf_counter() - start_time, 2)

    # Persist log to disk
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(full_output)

    cmd_display = " ".join(command)
    offloaded_ref_data = None
    try:
        from tools.context.output_offloader import OutputOffloader

        offloader = OutputOffloader()
        was_offloaded, _, offload_ref = offloader.process_output(
            full_output, source_command=command[0] if command else "run"
        )
        if was_offloaded and offload_ref:
            offloaded_ref_data = offload_ref.to_dict()
    except (ImportError, Exception) as offload_err:
        sys.stderr.write(f"[WARN] OutputOffloader error: {offload_err}\n")

    if status == "TIMEOUT":
        summary = f"Process timed out after {timeout_sec:.1f}s. Full log saved to {log_path}."
        excerpt = extract_failure_excerpt(full_output, max_lines=max_excerpt)
    elif exit_code == 0:
        status = "PASSED"
        summary = f"Process completed successfully in {duration_sec:.2f}s."
        excerpt = []
    else:
        status = "FAILED"
        summary = f"Process failed with exit code {exit_code} in {duration_sec:.2f}s. Full log saved to {log_path}."
        excerpt = extract_failure_excerpt(full_output, max_lines=max_excerpt)

    return {
        "status": status,
        "command": cmd_display,
        "exit_code": exit_code,
        "duration_sec": duration_sec,
        "log_path": log_path,
        "summary": summary,
        "failure_excerpt": excerpt,
        "artifacts": [log_path] if os.path.exists(log_path) else [],
        "offloaded": offloaded_ref_data,
    }


def build_parser() -> argparse.ArgumentParser:
    """Builds the CLI parser for agent_runner."""
    parser = argparse.ArgumentParser(
        description="Context-Shielded Subprocess Runner & Diagnostic Filter (n8n/Grafana pattern)"
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="Maximum execution timeout in seconds")
    parser.add_argument("--log-dir", type=str, default="reports/agent_runs", help="Directory for raw run logs")
    parser.add_argument("--label", type=str, default="run", help="Prefix tag for generated log file")
    parser.add_argument("--max-excerpt", type=int, default=20, help="Maximum failure excerpt lines to return")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON to stdout")
    parser.add_argument("--allow-watch", action="store_true", help="Override safety circuit breaker for watch flags")
    parser.add_argument(
        "--sandbox",
        choices=["local", "docker"],
        default="local",
        help="Sandbox execution mode (local, docker; default: local)",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command and arguments to execute")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    command = args.command
    # Strip optional '--' delimiter if passed by caller
    if command and command[0] == "--":
        command = command[1:]

    result = execute_agent_run(
        command=command,
        timeout_sec=args.timeout,
        log_dir=args.log_dir,
        label=args.label,
        max_excerpt=args.max_excerpt,
        allow_watch=args.allow_watch,
        sandbox=getattr(args, "sandbox", "local"),
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["status"] == "PASSED":
            print(f"[PASSED] ({result['duration_sec']}s) {result['summary']}")
            print(f"Log: {result['log_path']}")
        elif result["status"] == "TIMEOUT":
            print(f"[TIMEOUT] {result['summary']}")
            if result["failure_excerpt"]:
                print(f"--- Timeout Excerpt (max {args.max_excerpt} lines) ---")
                for line in result["failure_excerpt"]:
                    print(line)
        else:
            print(f"[FAILED] Exit code {result['exit_code']} ({result['duration_sec']}s)")
            print(result["summary"])
            if result["failure_excerpt"]:
                print(f"--- Failure Excerpt (max {args.max_excerpt} lines) ---")
                for line in result["failure_excerpt"]:
                    print(line)

    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
