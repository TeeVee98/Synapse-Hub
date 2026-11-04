#!/usr/bin/env python3
"""
Enterprise Allure HTML Report Generator (Cross-Platform)
---------------------------------------------------------
Dispatches Allure report generation and local web serving across Windows, macOS, and Linux.
Replaces legacy PowerShell-only scripts with a zero-dependency, cross-platform engine.
"""

import os
import sys
import shutil
import subprocess
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))


def generate_allure_report(results_dir=None, report_dir=None, clean=True, open_browser=False):
    """Generates an Allure HTML report from raw result files."""
    results_path = results_dir or os.path.join(PROJECT_ROOT, "allure-results")
    report_path = report_dir or os.path.join(PROJECT_ROOT, "allure-report")

    if not os.path.exists(results_path):
        print(f"[!] Results directory not found: {results_path}")
        print("[!] Please execute your test suite first to generate raw test result files.")
        return 0

    allure_cmd = shutil.which("allure")
    if not allure_cmd:
        print("[!] Allure CLI executable was not found on PATH.")
        print("[*] Quick installation instructions:")
        print("    npm install -g allure-commandline")
        print("    brew install allure  (macOS)")
        print("    scoop install allure  (Windows)")
        return 1

    cmd = [allure_cmd, "generate", results_path, "-o", report_path]
    if clean:
        cmd.append("--clean")

    print(f"[+] Generating Allure HTML report from '{results_path}' to '{report_path}'...")
    try:
        subprocess.run(cmd, check=True)
        print(f"[+] Report generated successfully at: {report_path}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Allure report generation failed with exit code {e.returncode}")
        return e.returncode

    if open_browser:
        print("[+] Launching Allure report server...")
        try:
            subprocess.run([allure_cmd, "open", report_path])
        except KeyboardInterrupt:
            print("\n[+] Allure server closed.")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Generate and serve Allure HTML test reports")
    parser.add_argument("--results-dir", default=None, help="Directory containing raw allure-results")
    parser.add_argument("--report-dir", default=None, help="Output directory for generated HTML report")
    parser.add_argument("--no-clean", action="store_true", help="Do not clean output report directory before generation")
    parser.add_argument("--open", action="store_true", help="Automatically open report in browser via local server")
    args = parser.parse_args()

    sys.exit(generate_allure_report(
        results_dir=args.results_dir,
        report_dir=args.report_dir,
        clean=not args.no_clean,
        open_browser=args.open
    ))


if __name__ == "__main__":
    main()
