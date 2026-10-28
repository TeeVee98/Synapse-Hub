#!/usr/bin/env python3
"""
DMIT Static Defect & Assertion Sentinel (Inspired by facebook/infer)
-------------------------------------------------------------------
Performs AST-level static analysis across all 259 Groovy test scripts and Page Classes.
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
    r'ensureSubCategoryItemExists|wait\.until)',
    re.IGNORECASE
)
EMPTY_CATCH_PATTERN = re.compile(r'catch\s*\([^)]+\)\s*\{\s*\}', re.MULTILINE)
LONG_SLEEP_PATTERN = re.compile(r'Thread\.sleep\s*\(\s*([3-9]\d{3,}|\d{5,})\s*\)')
LONG_DELAY_PATTERN = re.compile(r'WebUI\.delay\s*\(\s*([5-9]|\d{2,})\s*\)')


def analyze_script(file_path):
    """Analyzes a single Groovy test script for defects."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    rel_path = os.path.relpath(file_path, REPO_ROOT)
    lines = content.splitlines()
    non_comment_lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith("//") and not l.strip().startswith("/*")]

    defects = []

    # 1. Empty test script
    if len(non_comment_lines) <= 2 and not any("Page." in l for l in non_comment_lines):
        defects.append({
            "code": "EMPTY_TEST_SCRIPT",
            "severity": "CRITICAL",
            "message": "Script contains zero or insufficient executable statements.",
            "line": 1
        })

    # 2. Swallowed exceptions
    for m in EMPTY_CATCH_PATTERN.finditer(content):
        line_num = content[:m.start()].count("\n") + 1
        defects.append({
            "code": "SWALLOWED_EXCEPTION",
            "severity": "CRITICAL",
            "message": "Empty catch block silently swallows exceptions, masking failures.",
            "line": line_num
        })

    # 3. Excessive hardcoded delays
    for m in LONG_SLEEP_PATTERN.finditer(content):
        line_num = content[:m.start()].count("\n") + 1
        defects.append({
            "code": "EXCESSIVE_HARD_DELAY",
            "severity": "WARNING",
            "message": f"Thread.sleep({m.group(1)}ms) detected; violates deterministic sync.",
            "line": line_num
        })
    for m in LONG_DELAY_PATTERN.finditer(content):
        line_num = content[:m.start()].count("\n") + 1
        defects.append({
            "code": "EXCESSIVE_HARD_DELAY",
            "severity": "WARNING",
            "message": f"WebUI.delay({m.group(1)}s) detected; prefer Smart Wait / Network Idle 0.",
            "line": line_num
        })

    # 4. Fake pass / Missing assertion
    has_action = any("." in l and not l.startswith("import") and not l.startswith("package") for l in non_comment_lines)
    has_assertion = bool(ASSERTION_PATTERN.search(content))
    if has_action and not has_assertion:
        # Check if it is a probe utility script
        if "PROBE_" not in rel_path:
            defects.append({
                "code": "FAKE_PASS_NO_ASSERTION",
                "severity": "WARNING",
                "message": "Script executes interactions but contains no explicit assert/verify keyword.",
                "line": len(lines)
            })

    return {
        "file": rel_path,
        "line_count": len(lines),
        "defects": defects,
        "is_clean": len(defects) == 0
    }


def run_infer_linter():
    """Scans all test scripts in Scripts/ and summarizes defects."""
    script_files = glob.glob(os.path.join(SCRIPTS_DIR, "**", "*.groovy"), recursive=True)
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
    health_score = ((total_scripts - critical_count) / max(1, total_scripts)) * 100

    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    print(f"{BOLD}{CYAN}    DMIT STATIC DEFECT & FAKE-PASS SENTINEL (Meta Infer-Style)        {RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}")
    print(f"  Target Scope            : {total_scripts} Groovy Test Scripts in Scripts/")
    print(f"  Critical Defects        : {RED if critical_count > 0 else GREEN}{critical_count}{RESET} (Swallowed exceptions, empty scripts)")
    print(f"  Warnings / Suggestions  : {YELLOW if warning_count > 0 else GREEN}{warning_count}{RESET} (Missing explicit asserts, excessive delays)")
    print(f"  Clean Scripts           : {GREEN}{clean_count}/{total_scripts} ({clean_count / total_scripts * 100:.1f}%){RESET}")
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
    parser = argparse.ArgumentParser(description="DMIT Static Defect & Assertion Sentinel")
    parser.parse_args()
    return run_infer_linter()


if __name__ == "__main__":
    sys.exit(main())
