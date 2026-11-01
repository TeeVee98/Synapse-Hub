#!/usr/bin/env python3
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


def run_prober(mode="playwright", suite_path="Test Suites/PROBE_E2E_Flow"):
    """Dispatches flow prober according to selected mode."""
    print("==========================================================")
    print("   ENTERPRISE AUTOMATION - E2E FLOW PROBER & XPATH CRAWLER")
    print("==========================================================")

    if mode == "playwright":
        runner_path = os.path.join(PROJECT_ROOT, "real_e2e_runner.py")
        if os.path.exists(runner_path):
            print(f"[+] Launching Playwright E2E Crawler ({runner_path})...")
            return subprocess.run([sys.executable, runner_path, "--probe"]).returncode
        else:
            print("[!] real_e2e_runner.py not found in project root.")
            print("[+] Falling back to Playwright test runner...")
            npx = shutil.which("npx")
            if npx:
                return subprocess.run([npx, "playwright", "test", "--grep", "@probe"]).returncode
            print("[ERROR] Neither real_e2e_runner.py nor npx found.")
            return 1

    elif mode == "katalon":
        katalon_bin = find_katalon_binary()
        if not katalon_bin:
            print("[!] Katalon Runtime Engine (katalonc) not found on PATH or standard locations.")
            print("    Please set KATALON_HOME or ensure katalonc is installed.")
            return 1

        print(f"[+] Launching Katalon Suite Prober via {katalon_bin}...")
        cmd = [
            katalon_bin,
            "-noSplash",
            "-runMode=console",
            f"-testSuitePath={suite_path}",
            "-browserType=Chrome (headless)"
        ]
        return subprocess.run(cmd).returncode

    else:
        print(f"[ERROR] Unsupported mode '{mode}'. Choose 'playwright' or 'katalon'.")
        return 2


def main():
    parser = argparse.ArgumentParser(description="E2E Flow Prober and DOM Crawler Dispatcher")
    parser.add_argument("--mode", choices=["playwright", "katalon"], default="playwright",
                        help="Execution engine for prober (default: playwright)")
    parser.add_argument("--suite", default="Test Suites/PROBE_E2E_Flow",
                        help="Katalon test suite path (if mode=katalon)")
    args = parser.parse_args()

    sys.exit(run_prober(mode=args.mode, suite_path=args.suite))


if __name__ == "__main__":
    main()
