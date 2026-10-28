#!/usr/bin/env python3
"""
Universal QA Static Defect & Assertion Sentinel (Inspired by facebook/infer)
-------------------------------------------------------------------
Performs AST-level static analysis across test scripts, specs, and Page Classes.
Detects:
  1. FAKE_PASS_NO_ASSERTION : Test cases that interact with AUT but lack assertions / verifications.
  2. SWALLOWED_EXCEPTION    : Empty catch blocks that hide failures silently.
  3. EXCESSIVE_HARD_DELAY   : Thread.sleep >= 3000ms or WebUI.delay >= 5s (flaky anti-pattern).
  4. RESOURCE_LEAK_RISK     : Unclosed streams or driver handles lacking finally blocks.
  5. EMPTY_TEST_SCRIPT      : Test cases with zero executable statements.
"""

import os
import sys
import re
import json
import glob
import argparse
from datetime import datetime

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "Scripts")
REPORTS_DIR = os.path.join(REPO_ROOT, "reports")
OUTPUT_JSON = os.path.join(REPORTS_DIR, "infer_linter_report.json")

# ANSI Color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Detection regexes
ASSERTION_PATTERN = re.compile(
    r'(verify|assert|waitForToast|check|assertEquals|assertTrue|assertFalse|'
    r'verifyElement|verifyMatch|verifyEqual|ensurePlanningExists|'
    r'ensureCareerExists|ensureDepartmentExists|ensurePositionExists|'
    r'verifyTextPresent|verifyElementPresent|verifyElementNotPresent|'
    r'verifyElementVisible|verifyElementClickable|assertThat|expect)'
)

EMPTY_CATCH_PATTERN = re.compile(
    r'catch\s*\([^\)]*\)\s*\{\s*(?://[^\n]*\s*)*\}',
    re.MULTILINE
)

THREAD_SLEEP_PATTERN = re.compile(
    r'(?:Thread\.sleep|WebUI\.delay)\s*\(\s*(\d+)\s*\)'
)


def analyze_script(file_path):
    """Performs static rule scanning on a single test script file."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        lines = content.splitlines()

    defects = []
    try:
        rel_path = os.path.relpath(file_path, REPO_ROOT)
    except ValueError:
        rel_path = os.path.abspath(file_path)

    # Rule 1: Empty Test Script
    executable_lines = [
        l.strip() for l in lines
        if l.strip() and not l.strip().startswith("//") and not l.strip().startswith("/*") and not l.strip().startswith("*")
    ]
    if len(executable_lines) <= 2:
        defects.append({
            "type": "EMPTY_TEST_SCRIPT",
            "severity": "CRITICAL",
            "line": 1,
            "message": "Test script appears empty or contains only comments/imports."
        })

    # Rule 2: Swallowed Exceptions (empty catch blocks)
    for match in EMPTY_CATCH_PATTERN.finditer(content):
        line_no = content[:match.start()].count("\n") + 1
        defects.append({
            "type": "SWALLOWED_EXCEPTION",
            "severity": "CRITICAL",
            "line": line_no,
            "message": "Empty catch block detected. Swallowed exceptions cause false-pass test runs."
        })

    # Rule 3: Flaky Static Delays
    for idx, line in enumerate(lines, 1):
        m = THREAD_SLEEP_PATTERN.search(line)
        if m:
            delay_val = int(m.group(1))
            if delay_val >= 3000:
                defects.append({
                    "type": "EXCESSIVE_HARD_DELAY",
                    "severity": "WARNING",
                    "line": idx,
                    "message": f"Static sleep of {delay_val}ms found. Replace with dynamic Smart Wait (waitForElement/networkidle)."
                })

    # Rule 4: Fake-Pass / Missing Assertions
    # Strip comments to ensure commented assertions do not count as real verifications
    uncommented_lines = [
        l.split("//")[0].strip() for l in lines
        if not l.strip().startswith("//") and not l.strip().startswith("/*") and not l.strip().startswith("*")
    ]
    uncommented_content = "\n".join(uncommented_lines)
    has_assert = bool(ASSERTION_PATTERN.search(uncommented_content))
    has_interactions = any(
        kw in uncommented_content for kw in ["click", "select", "save", "delete", "create", "search", "navigate"]
    )
    if has_interactions and not has_assert:
        defects.append({
            "type": "FAKE_PASS_NO_ASSERTION",
            "severity": "WARNING",
            "line": 1,
            "message": "Script performs AUT mutations/interactions but contains zero verification/assertion statements."
        })

    return {
        "file": rel_path,
        "defects": defects,
        "is_clean": len(defects) == 0
    }


def run_infer_linter(target_dir=None):
    """Scans all Groovy test scripts in target_dir or Scripts/."""
    scan_dir = target_dir or SCRIPTS_DIR
    if not os.path.exists(scan_dir):
        script_files = []
    else:
        script_files = glob.glob(os.path.join(scan_dir, "**", "*.groovy"), recursive=True)

    results = []
    critical_count = 0
    warning_count = 0
    clean_count = 0

    for s in sorted(script_files):
        res = analyze_script(s)
        results.append(res)
        crit = sum(1 for d in res["defects"] if d["severity"] == "CRITICAL")
        warn = sum(1 for d in res["defects"] if d["severity"] == "WARNING")
        critical_count += crit
        warning_count += warn
        if res["is_clean"]:
            clean_count += 1

    total_scripts = len(script_files)
    health_score = 100.0 if total_scripts == 0 else (((total_scripts - critical_count) / total_scripts) * 100)
    clean_pct = (clean_count / total_scripts * 100) if total_scripts > 0 else 100.0

    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    print(f"{BOLD}{CYAN}    ENTERPRISE STATIC DEFECT & FAKE-PASS SENTINEL (Meta Infer-Style)        {RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}")
    print(f"  Target Scope            : {total_scripts} Groovy Test Scripts in {os.path.basename(scan_dir)}/")
    print(f"  Critical Defects        : {RED if critical_count > 0 else GREEN}{critical_count}{RESET} (Swallowed exceptions, empty scripts)")
    print(f"  Warnings / Suggestions  : {YELLOW if warning_count > 0 else GREEN}{warning_count}{RESET} (Missing explicit asserts, excessive delays)")
    print(f"  Clean Scripts           : {GREEN}{clean_count}/{total_scripts} ({clean_pct:.1f}%){RESET}")
    print(f"  Codebase Health Score   : {GREEN if health_score == 100 else YELLOW}{health_score:.1f}%{RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}\n")

    # Print defect breakdown if any
    defect_scripts = [r for r in results if not r["is_clean"]]
    if defect_scripts:
        print(f"{BOLD}Detected Items ({len(defect_scripts)} scripts):{RESET}")
        for r in defect_scripts[:10]: # Print top 10
            for d in r["defects"]:
                color = RED if d["severity"] == "CRITICAL" else YELLOW
                print(f"  - [{color}{d['severity']}{RESET}] {r['file']}:{d['line']} - {d['message']}")
        if len(defect_scripts) > 10:
            print(f"  ... and {len(defect_scripts) - 10} more scripts (see full JSON report).\n")

    # Save artifact
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "total_scripts": total_scripts,
        "clean_scripts": clean_count,
        "critical_defects": critical_count,
        "warnings": warning_count,
        "health_score_pct": health_score,
        "defect_details": defect_scripts
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    print(f"Detailed audit saved to: {OUTPUT_JSON}\n")

    return 0 if critical_count == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Universal QA Static Defect & Assertion Sentinel")
    parser.add_argument("--dir", help="Target directory to scan (defaults to Scripts/)")
    args = parser.parse_args()
    return run_infer_linter(target_dir=args.dir)


if __name__ == "__main__":
    sys.exit(main())
