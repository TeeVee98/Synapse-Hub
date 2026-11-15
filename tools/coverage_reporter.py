#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/coverage_reporter.py — Standardized Coverage Metrics & Roadmap Evaluator
-------------------------------------------------------------------------------
Evaluates and distinguishes:
  1. Statement / Line Coverage (fail_under: 60.00% calibrated floor, roadmap: 70% -> 80%).
  2. Branch Coverage (floor: 50.00% baseline floor, roadmap: 60% -> 70%).
  3. Combined Coverage (statements + branches hit / total).

Maintains strict separation between line coverage, branch coverage, static heuristic,
and dynamic mutation kill scores.

Outputs:
  - reports/coverage_summary.json (Standardized multi-metric artifact)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict

_logger = logging.getLogger("coverage_reporter")
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_COVERAGE_JSON = os.path.join(REPO_ROOT, "reports", "coverage.json")
DEFAULT_COVERAGE_XML = os.path.join(REPO_ROOT, "reports", "coverage.xml")
DEFAULT_SUMMARY_JSON = os.path.join(REPO_ROOT, "reports", "coverage_summary.json")

# Calibrated floors and roadmap milestones
LINE_COVERAGE_FLOOR_PCT = 60.00
BRANCH_COVERAGE_FLOOR_PCT = 50.00

ROADMAP_THRESHOLDS = {
    "current_calibrated": {"line_pct": 60.00, "branch_pct": 50.00},
    "phase_2_consolidation": {"line_pct": 70.00, "branch_pct": 60.00},
    "target_enterprise": {"line_pct": 80.00, "branch_pct": 70.00},
}


def get_git_commit(repo_root: str = REPO_ROOT) -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
        )
        return out.decode("utf-8").strip()
    except (OSError, subprocess.SubprocessError) as err:
        _logger.debug("Could not determine git commit: %s", err)
        return "unversioned"


def parse_coverage_metrics(
    json_path: str = DEFAULT_COVERAGE_JSON,
) -> Dict[str, Any]:
    """Parses coverage metrics from coverage.py json report."""
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Coverage JSON report not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    totals = data.get("totals", {})
    num_statements = totals.get("num_statements", 0)
    covered_lines = totals.get("covered_lines", 0)
    missing_lines = totals.get("missing_lines", 0)

    # Line / Statement coverage
    line_cov_pct = float(
        totals.get(
            "percent_statements_covered",
            (covered_lines / num_statements * 100.0) if num_statements > 0 else 0.0,
        )
    )

    # Branch coverage
    num_branches = totals.get("num_branches", 0)
    covered_branches = totals.get("covered_branches", 0)
    missing_branches = totals.get("missing_branches", 0)
    branch_cov_pct = float(
        totals.get(
            "percent_branches_covered",
            (covered_branches / num_branches * 100.0) if num_branches > 0 else 0.0,
        )
    )

    # Combined coverage
    combined_cov_pct = float(totals.get("percent_covered", 0.0))

    return {
        "num_statements": num_statements,
        "covered_lines": covered_lines,
        "missing_lines": missing_lines,
        "line_coverage_pct": round(line_cov_pct, 2),
        "num_branches": num_branches,
        "covered_branches": covered_branches,
        "missing_branches": missing_branches,
        "branch_coverage_pct": round(branch_cov_pct, 2),
        "combined_coverage_pct": round(combined_cov_pct, 2),
    }


def evaluate_coverage(
    coverage_data: Dict[str, Any],
    line_floor: float = LINE_COVERAGE_FLOOR_PCT,
    branch_floor: float = BRANCH_COVERAGE_FLOOR_PCT,
    enforce_branch: bool = True,
) -> Dict[str, Any]:
    """Evaluates metrics against calibrated floor and roadmap milestones."""
    line_pct = coverage_data["line_coverage_pct"]
    branch_pct = coverage_data["branch_coverage_pct"]

    line_pass = line_pct >= line_floor
    branch_pass = branch_pct >= branch_floor if enforce_branch and coverage_data["num_branches"] > 0 else True
    all_pass = line_pass and branch_pass

    return {
        "line_pass": line_pass,
        "branch_pass": branch_pass,
        "all_pass": all_pass,
        "line_floor": line_floor,
        "branch_floor": branch_floor,
        "enforce_branch": enforce_branch,
    }


def generate_coverage_summary(
    coverage_json: str = DEFAULT_COVERAGE_JSON,
    coverage_xml: str = DEFAULT_COVERAGE_XML,
    output_summary_json: str = DEFAULT_SUMMARY_JSON,
    line_floor: float = LINE_COVERAGE_FLOOR_PCT,
    branch_floor: float = BRANCH_COVERAGE_FLOOR_PCT,
    enforce_branch: bool = True,
    repo_root: str = REPO_ROOT,
) -> Dict[str, Any]:
    """Generates standardized coverage summary artifact and writes to disk."""
    metrics = parse_coverage_metrics(coverage_json)
    eval_res = evaluate_coverage(
        metrics,
        line_floor=line_floor,
        branch_floor=branch_floor,
        enforce_branch=enforce_branch,
    )

    commit_sha = get_git_commit(repo_root)
    now_iso = datetime.now(timezone.utc).isoformat()

    summary_doc = {
        "generated_at": now_iso,
        "commit": commit_sha,
        "metrics": {
            "line_coverage_pct": metrics["line_coverage_pct"],
            "branch_coverage_pct": metrics["branch_coverage_pct"],
            "combined_coverage_pct": metrics["combined_coverage_pct"],
            "statements_total": metrics["num_statements"],
            "statements_covered": metrics["covered_lines"],
            "statements_missing": metrics["missing_lines"],
            "branches_total": metrics["num_branches"],
            "branches_covered": metrics["covered_branches"],
            "branches_missing": metrics["missing_branches"],
        },
        "thresholds": {
            "line_floor_pct": line_floor,
            "branch_floor_pct": branch_floor,
            "roadmap": ROADMAP_THRESHOLDS,
        },
        "evaluation": {
            "line_passed": eval_res["line_pass"],
            "branch_passed": eval_res["branch_pass"],
            "all_passed": eval_res["all_pass"],
        },
        "artifacts": {
            "coverage_json": os.path.relpath(coverage_json, repo_root) if os.path.exists(coverage_json) else None,
            "coverage_xml": os.path.relpath(coverage_xml, repo_root) if os.path.exists(coverage_xml) else None,
            "summary_json": os.path.relpath(output_summary_json, repo_root),
        },
    }

    out_dir = os.path.dirname(output_summary_json)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_summary_json, "w", encoding="utf-8") as f:
        json.dump(summary_doc, f, indent=2)

    return summary_doc


def main() -> int:
    parser = argparse.ArgumentParser(description="Synapse Hub Standardized Coverage Reporter")
    parser.add_argument("--json-report", default=DEFAULT_COVERAGE_JSON, help="Path to coverage.json")
    parser.add_argument("--xml-report", default=DEFAULT_COVERAGE_XML, help="Path to coverage.xml")
    parser.add_argument("--summary-out", default=DEFAULT_SUMMARY_JSON, help="Path to write coverage_summary.json")
    parser.add_argument("--line-floor", type=float, default=LINE_COVERAGE_FLOOR_PCT, help="Statement/line coverage floor")
    parser.add_argument("--branch-floor", type=float, default=BRANCH_COVERAGE_FLOOR_PCT, help="Branch coverage floor")
    parser.add_argument("--no-branch", action="store_true", help="Do not enforce branch coverage threshold")
    parser.add_argument("--check", action="store_true", help="Fail with non-zero exit code if coverage is below threshold")
    parser.add_argument("--json", action="store_true", help="Print summary JSON to stdout")
    args = parser.parse_args()

    if not os.path.exists(args.json_report):
        sys.stderr.write(f"Error: Coverage JSON report not found at {args.json_report}.\n")
        return 1

    summary = generate_coverage_summary(
        coverage_json=args.json_report,
        coverage_xml=args.xml_report,
        output_summary_json=args.summary_out,
        line_floor=args.line_floor,
        branch_floor=args.branch_floor,
        enforce_branch=not args.no_branch,
    )

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        m = summary["metrics"]
        e = summary["evaluation"]
        print("======================================================================")
        print("          SYNAPSE HUB STANDARDIZED TEST COVERAGE REPORT               ")
        print("======================================================================")
        print(f"  Line Coverage (Statements) : {m['line_coverage_pct']}% (Floor: >= {args.line_floor}%) - {'✅ PASS' if e['line_passed'] else '❌ FAIL'}")
        print(f"  Branch Coverage            : {m['branch_coverage_pct']}% (Floor: >= {args.branch_floor}%) - {'✅ PASS' if e['branch_passed'] else '❌ FAIL'}")
        print(f"  Combined (Stmt + Branch)   : {m['combined_coverage_pct']}%")
        print(f"  Total Statements           : {m['statements_total']:,} (Covered: {m['statements_covered']:,})")
        print(f"  Total Branches             : {m['branches_total']:,} (Covered: {m['branches_covered']:,})")
        print(f"  Coverage Summary Artifact  : {summary['artifacts']['summary_json']}")
        print(f"  Coverage XML Artifact      : {summary['artifacts']['coverage_xml']}")
        print("======================================================================")

    if args.check and not summary["evaluation"]["all_passed"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
