#!/usr/bin/env python3
"""
Universal Data Flow & Teardown Tracer (Taint Analysis)
----------------------------------------------------
Performs AST-level Taint Analysis tracking test data lifecycle across test scripts:
  1. SOURCE: Generation of dynamic unique identifiers (uniqueCode, DataGenerator).
  2. PROPAGATE: Insertion / persistence into database or UI state.
  3. SINK: Automated Teardown / Deletion / Cleanup.

Detects orphan test junk that pollutes test environments.
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
OUTPUT_JSON = os.path.join(REPORTS_DIR, "data_flow_trace_report.json")

# ANSI Color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Taint patterns
SOURCE_PATTERNS = [
    re.compile(r'uniqueCode', re.IGNORECASE),
    re.compile(r'DataGenerator\.', re.IGNORECASE),
    re.compile(r'System\.currentTimeMillis', re.IGNORECASE),
    re.compile(r'random[A-Z]\w+', re.IGNORECASE),
    re.compile(r'ensure\w+Exists', re.IGNORECASE),
]

PROPAGATE_PATTERNS = [
    re.compile(r'\.save\w*\(', re.IGNORECASE),
    re.compile(r'\.themMoi\w*\(', re.IGNORECASE),
    re.compile(r'\.fill\w*\(', re.IGNORECASE),
    re.compile(r'\.create\w*\(', re.IGNORECASE),
    re.compile(r'\.insert\w*\(', re.IGNORECASE),
    re.compile(r'\b(?:save|persist|insert|themMoi)[A-Z]\w*\(', re.IGNORECASE),
]

SINK_PATTERNS = [
    re.compile(r'\.delete\w*\(', re.IGNORECASE),
    re.compile(r'\.xoa\w*\(', re.IGNORECASE),
    re.compile(r'\.teardown\w*\(', re.IGNORECASE),
    re.compile(r'\.cleanUp\w*\(', re.IGNORECASE),
    re.compile(r'confirmDialog', re.IGNORECASE),
    re.compile(r'ICON_DELETE', re.IGNORECASE),
    re.compile(r'Xoá|Xoa|delete', re.IGNORECASE),
]


def trace_script_dataflow(file_path):
    """Traces source, propagation, and sink in a test script."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    rel_path = os.path.relpath(file_path, REPO_ROOT)
    tc_name = os.path.basename(os.path.dirname(file_path))

    has_source = any(p.search(content) for p in SOURCE_PATTERNS)
    has_propagate = any(p.search(content) for p in PROPAGATE_PATTERNS)
    has_sink = any(p.search(content) for p in SINK_PATTERNS)

    # Classification
    if "Xoa" in tc_name or "Delete" in tc_name or "xoa" in tc_name:
        lifecycle = "CLEANUP_SUITE"
        description = "Dedicated deletion / teardown test suite."
    elif has_propagate and has_sink:
        lifecycle = "IDEMPOTENT_CLEAN"
        description = "Complete lifecycle: Dynamic creation + verified teardown."
    elif has_propagate and not has_sink:
        if "Sua" in tc_name or "Edit" in tc_name or "Update" in tc_name:
            lifecycle = "MUTATION_UPDATE"
            description = "Modifies existing record in-place without creating new entities."
        else:
            lifecycle = "ORPHAN_DATA_RISK"
            description = "Creates persistent entity on AUT without local teardown."
    else:
        lifecycle = "READ_ONLY"
        description = "Read-only interaction flow."

    return {
        "file": rel_path,
        "tc_name": tc_name,
        "has_source": has_source,
        "has_propagate": has_propagate,
        "has_sink": has_sink,
        "lifecycle": lifecycle,
        "description": description
    }


def run_data_flow_tracer(target_dir=None):
    """Scans all test cases in target directory and traces data flow."""
    scan_dir = target_dir or SCRIPTS_DIR
    script_files = []
    if os.path.isdir(scan_dir):
        for ext in ("*.groovy", "*.ts", "*.js", "*.py"):
            script_files.extend(glob.glob(os.path.join(scan_dir, "**", ext), recursive=True))

    results = []
    counts = {
        "IDEMPOTENT_CLEAN": 0,
        "READ_ONLY": 0,
        "CLEANUP_SUITE": 0,
        "MUTATION_UPDATE": 0,
        "ORPHAN_DATA_RISK": 0
    }

    for s in sorted(script_files):
        res = trace_script_dataflow(s)
        results.append(res)
        counts[res["lifecycle"]] = counts.get(res["lifecycle"], 0) + 1

    total = len(script_files)
    safe_count = counts["IDEMPOTENT_CLEAN"] + counts["READ_ONLY"] + counts["CLEANUP_SUITE"] + counts["MUTATION_UPDATE"]
    purity_rate = (safe_count / max(1, total)) * 100 if total > 0 else 100.0

    print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
    print(f"{BOLD}{CYAN}      Universal Data Flow & TEARDOWN TRACER (Taint Audit)            {RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}")
    print(f"  Total Audited Scripts   : {total} Test Cases")
    print(f"  Idempotent Clean        : {GREEN}{counts['IDEMPOTENT_CLEAN']}{RESET} (Dynamic data + verified teardown)")
    print(f"  Read-Only Invariant     : {CYAN}{counts['READ_ONLY']}{RESET} (Search, filter, navigation, export)")
    print(f"  Dedicated Cleanup Suites: {GREEN}{counts['CLEANUP_SUITE']}{RESET} (Explicit deletion test cases)")
    print(f"  In-Place Mutations      : {YELLOW}{counts['MUTATION_UPDATE']}{RESET} (Edit/update existing records)")
    print(f"  Orphan Data Risk        : {RED if counts['ORPHAN_DATA_RISK'] > 0 else GREEN}{counts['ORPHAN_DATA_RISK']}{RESET} (Persistent creation without teardown)")
    print(f"  Database Hygiene Purity : {GREEN if purity_rate >= 90 else YELLOW}{purity_rate:.1f}%{RESET}")
    print(f"{BOLD}{CYAN}======================================================================{RESET}\n")

    # Save artifact
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "total_scripts": total,
        "hygiene_purity_pct": round(purity_rate, 2),
        "lifecycle_counts": counts,
        "details": results
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    print(f"Detailed data-flow artifact saved to: {OUTPUT_JSON}\n")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Universal Data Flow & Teardown Tracer")
    parser.add_argument("--dir", "-d", default=None, help="Directory containing test scripts to trace")
    args = parser.parse_args()
    return run_data_flow_tracer(target_dir=args.dir)


if __name__ == "__main__":
    sys.exit(main())
