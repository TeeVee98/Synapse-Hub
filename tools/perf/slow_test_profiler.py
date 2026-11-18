#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/slow_test_profiler.py — Slowest Test Execution Profiler (JUnit XML)
-------------------------------------------------------------------------
Inspired by Oven Bun test profiling and CI runtime optimization standards.

Core Capabilities:
  1. Automated JUnit XML Parsing: Parses testsuites/testcase records from JUnit XML.
  2. Performance Tier Categorization: Classifies tests into SLOW (>= 5.0s),
     MODERATE (1.0s - 5.0s), and FAST (< 1.0s) execution tiers.
  3. Actionable Bottleneck Identification: Highlights the Top-N slowest tests
     consuming CI/CD worker resources, helping QA teams refactor or parallelize them.
"""
from __future__ import annotations

import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import argparse
import json
import logging
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger("slow_test_profiler")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_SLOW_THRESHOLD_SEC = 5.0
DEFAULT_MODERATE_THRESHOLD_SEC = 1.0
DEFAULT_TOP_N = 10


def parse_junit_report(report_path: str) -> List[Dict[str, Any]]:
    """
    Parses a JUnit XML file and extracts all testcase timing records.
    """
    if not os.path.isfile(report_path):
        raise FileNotFoundError(f"JUnit XML report not found: {report_path}")

    tree = ET.parse(report_path)
    root = tree.getroot()

    records: List[Dict[str, Any]] = []

    # Find all testcase elements (supports both <testsuite> and <testsuites> roots)
    testcases = root.findall(".//testcase")
    for tc in testcases:
        classname = tc.get("classname", "")
        name = tc.get("name", "")
        time_str = tc.get("time", "0.0")

        try:
            duration_sec = round(float(time_str), 3)
        except (ValueError, TypeError):
            duration_sec = 0.0

        # Determine status
        status = "PASSED"
        if tc.find("failure") is not None:
            status = "FAILED"
        elif tc.find("error") is not None:
            status = "ERROR"
        elif tc.find("skipped") is not None:
            status = "SKIPPED"

        records.append({
            "classname": classname,
            "name": name,
            "duration_sec": duration_sec,
            "status": status,
            "identifier": f"{classname}::{name}" if classname else name,
        })

    return records


def profile_slowest_tests(
    report_path: str,
    top_n: int = DEFAULT_TOP_N,
    slow_threshold_sec: float = DEFAULT_SLOW_THRESHOLD_SEC,
    moderate_threshold_sec: float = DEFAULT_MODERATE_THRESHOLD_SEC,
) -> Dict[str, Any]:
    """
    Analyzes test suite performance and generates timing percentiles and rankings.
    """
    records = parse_junit_report(report_path)
    if not records:
        return {
            "total_tests": 0,
            "total_duration_sec": 0.0,
            "avg_duration_sec": 0.0,
            "p95_sec": 0.0,
            "p99_sec": 0.0,
            "slow_count": 0,
            "moderate_count": 0,
            "fast_count": 0,
            "top_slowest": [],
        }

    # Sort records descending by duration
    sorted_records = sorted(records, key=lambda x: x["duration_sec"], reverse=True)

    durations = [r["duration_sec"] for r in sorted_records]
    total_duration = round(sum(durations), 3)
    total_tests = len(durations)
    avg_duration = round(total_duration / total_tests, 3)

    # Calculate percentiles
    p95_idx = max(0, int(total_tests * 0.05) - 1)
    p99_idx = max(0, int(total_tests * 0.01) - 1)
    p95_sec = sorted_records[p95_idx]["duration_sec"] if sorted_records else 0.0
    p99_sec = sorted_records[p99_idx]["duration_sec"] if sorted_records else 0.0

    slow_tests = [r for r in sorted_records if r["duration_sec"] >= slow_threshold_sec]
    moderate_tests = [
        r
        for r in sorted_records
        if moderate_threshold_sec <= r["duration_sec"] < slow_threshold_sec
    ]
    fast_tests = [r for r in sorted_records if r["duration_sec"] < moderate_threshold_sec]

    top_slowest = sorted_records[:top_n]

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "report_path": report_path,
        "total_tests": total_tests,
        "total_duration_sec": total_duration,
        "avg_duration_sec": avg_duration,
        "p95_sec": p95_sec,
        "p99_sec": p99_sec,
        "slow_threshold_sec": slow_threshold_sec,
        "moderate_threshold_sec": moderate_threshold_sec,
        "slow_count": len(slow_tests),
        "moderate_count": len(moderate_tests),
        "fast_count": len(fast_tests),
        "top_slowest": top_slowest,
    }


def format_markdown_report(profile: Dict[str, Any]) -> str:
    """Format profiling results into a scannable Markdown summary table."""
    lines: List[str] = [
        "# Test Execution Performance & Bottleneck Profile",
        "",
        f"- **Total Tests Analyzed:** `{profile['total_tests']}`",
        f"- **Total Execution Time:** `{profile['total_duration_sec']}s` (~{profile['total_duration_sec'] / 60:.1f} min)",
        f"- **Average Duration:** `{profile['avg_duration_sec']}s` | **P95:** `{profile['p95_sec']}s` | **P99:** `{profile['p99_sec']}s`",
        f"- **Slow Tests (>= {profile['slow_threshold_sec']}s):** `{profile['slow_count']}` | **Moderate (1-5s):** `{profile['moderate_count']}` | **Fast (< 1s):** `{profile['fast_count']}`",
        "",
        "## Top Slowest Test Cases",
        "",
        "| Rank | Duration (s) | Status | Test Identifier |",
        "|:---:|:---:|:---:|---|",
    ]

    for rank, tc in enumerate(profile.get("top_slowest", []), 1):
        status_badge = "✅" if tc["status"] == "PASSED" else "❌" if tc["status"] in ("FAILED", "ERROR") else "⏸️"
        lines.append(
            f"| #{rank} | `{tc['duration_sec']}s` | {status_badge} {tc['status']} | `{tc['identifier']}` |"
        )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Slow Test Profiler — JUnit XML Execution Bottleneck Analyzer"
    )
    parser.add_argument(
        "--report",
        default="reports/junit_test_report.xml",
        help="Path to JUnit XML test report (default: reports/junit_test_report.xml).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=DEFAULT_TOP_N,
        help="Number of slowest tests to report (default: 10).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_SLOW_THRESHOLD_SEC,
        help="Threshold in seconds to classify tests as slow (default: 5.0).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON results.",
    )
    parser.add_argument(
        "--md",
        action="store_true",
        help="Output formatted Markdown report.",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.report):
        print(f"[FAIL] JUnit report not found: {args.report}")
        return 1

    profile = profile_slowest_tests(
        args.report,
        top_n=args.top,
        slow_threshold_sec=args.threshold,
    )

    if args.json:
        print(json.dumps(profile, indent=2))
        return 0

    if args.md:
        print(format_markdown_report(profile))
        return 0

    print(
        f"\n[SLOW-TEST-PROFILER] Analyzed {profile['total_tests']} tests in {profile['total_duration_sec']}s "
        f"(Avg: {profile['avg_duration_sec']}s, P95: {profile['p95_sec']}s)"
    )
    print(
        f"Distribution: {profile['slow_count']} Slow (>= {args.threshold}s) | "
        f"{profile['moderate_count']} Moderate | {profile['fast_count']} Fast"
    )
    print(f"\nTop {len(profile['top_slowest'])} Slowest Tests:")
    for idx, tc in enumerate(profile["top_slowest"], 1):
        print(f"  {idx:2d}. [{tc['duration_sec']:6.2f}s] {tc['status']} -> {tc['identifier']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
