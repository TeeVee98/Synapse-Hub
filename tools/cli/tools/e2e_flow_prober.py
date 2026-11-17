#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Enterprise E2E Flow Prober & XPath Crawler Dispatcher (Cross-Platform)
----------------------------------------------------------------------
Dispatches autonomous flow probing across Katalon Studio and Playwright.
Replaces PowerShell-only script with a zero-dependency, cross-platform engine.
"""

import os
import sys
import shutil
import argparse
import subprocess
from typing import List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))


def find_katalon_binary():
    """Locates the katalonc binary across Windows, macOS, and Linux."""
    from_path = shutil.which("katalonc") or shutil.which("katalon")
    if from_path:
        return from_path

    env_home = os.environ.get("KATALON_HOME")
    if env_home:
        for candidate in ["katalonc", "katalonc.exe", "katalon", "katalon.exe"]:
            p = os.path.join(env_home, candidate)
            if os.path.isfile(p):
                return p

    standard_paths = [
        "C:\\Katalon_Studio_Engine\\katalonc.exe",
        "C:\\Katalon_Studio\\katalon.exe",
        "/Applications/Katalon Studio Engine.app/Contents/MacOS/katalonc",
        "/opt/katalon/katalonc",
        "/opt/homebrew/bin/katalonc",
    ]
    for p in standard_paths:
        if os.path.isfile(p):
            return p
    return None


try:
    DEFAULT_TIMEOUT = float(os.environ.get("PROBER_TIMEOUT", "60.0"))
except (ValueError, TypeError):
    DEFAULT_TIMEOUT = 60.0


def _run_cmd_supervised(cmd: List[str], timeout: float, error_label: str) -> int:
    """Runs a command with process group supervision, guaranteeing descendant reaping on timeout."""
    try:
        from tools.core.process_supervisor import ProcessSupervisor
    except ImportError:
        try:
            from core.process_supervisor import ProcessSupervisor
        except ImportError:
            ProcessSupervisor = None

    if ProcessSupervisor is not None:
        sup = ProcessSupervisor(default_timeout=timeout)
        res = sup.run(cmd, timeout=timeout, capture_output=False)
        if res.timed_out:
            print(f"[ERROR] {error_label} timed out after {timeout} seconds.")
        return res.returncode
    else:
        try:
            return subprocess.run(cmd, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            print(f"[ERROR] {error_label} timed out after {timeout} seconds.")
            return 124


def run_prober(mode="playwright", suite_path="Test Suites/PROBE_E2E_Flow", timeout=DEFAULT_TIMEOUT):
    """Dispatches flow prober according to selected mode with explicit timeout guards and process supervision."""
    print("==========================================================")
    print("   ENTERPRISE AUTOMATION - E2E FLOW PROBER & XPATH CRAWLER")
    print("==========================================================")

    if mode == "playwright":
        runner_path = os.path.join(PROJECT_ROOT, "real_e2e_runner.py")
        if os.path.exists(runner_path):
            print(f"[+] Launching Playwright E2E Crawler ({runner_path}) [timeout={timeout}s]...")
            return _run_cmd_supervised([sys.executable, runner_path, "--probe"], timeout, "Playwright E2E Crawler")
        else:
            print("[!] real_e2e_runner.py not found in project root.")
            print(f"[+] Falling back to Playwright test runner [timeout={timeout}s]...")
            npx = shutil.which("npx")
            if npx:
                return _run_cmd_supervised([npx, "playwright", "test", "--grep", "@probe"], timeout, "Playwright test runner")
            print("[ERROR] Neither real_e2e_runner.py nor npx found.")
            return 1

    elif mode == "katalon":
        katalon_bin = find_katalon_binary()
        if not katalon_bin:
            print("[!] Katalon Runtime Engine (katalonc) not found on PATH or standard locations.")
            print("    Please set KATALON_HOME or ensure katalonc is installed.")
            return 1

        print(f"[+] Launching Katalon Suite Prober via {katalon_bin} [timeout={timeout}s]...")
        cmd = [
            katalon_bin,
            "-noSplash",
            "-runMode=console",
            f"-testSuitePath={suite_path}",
            "-browserType=Chrome (headless)"
        ]
        return _run_cmd_supervised(cmd, timeout, "Katalon Suite Prober")

    else:
        print(f"[ERROR] Unsupported mode '{mode}'. Choose 'playwright' or 'katalon'.")
        return 2


def main():
    parser = argparse.ArgumentParser(description="E2E Flow Prober and DOM Crawler Dispatcher")
    parser.add_argument("--mode", choices=["playwright", "katalon"], default="playwright",
                        help="Execution engine for prober (default: playwright)")
    parser.add_argument("--suite", default="Test Suites/PROBE_E2E_Flow",
                        help="Katalon test suite path (if mode=katalon)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help=f"Subprocess timeout in seconds (default: {DEFAULT_TIMEOUT})")
    args = parser.parse_args()

    sys.exit(run_prober(mode=args.mode, suite_path=args.suite, timeout=args.timeout))


if __name__ == "__main__":
    main()
