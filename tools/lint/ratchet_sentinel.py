#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/lint/ratchet_sentinel.py — Monotonic Quality Ratchet (Invariant 11 Sensor)
--------------------------------------------------------------------------------
Inspired by PostHog semgrep_ratchet.py and UNICEF ADT-Studio INVARIANTS.md.
Enforces Invariant 11 (The Ratchet Invariant / Hashimoto Principle: Rules only grow,
debt only shrinks).
Two-sided ratchet:
  1. Fails on regression (findings > baseline, or score < baseline).
  2. Fails on stale baseline (findings < baseline without --update).
  3. Locks in verified improvements when invoked with --update.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

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


def parse_defects_report(data: Any) -> Dict[str, int]:
    """
    Extracts per-file defect counts from varied report formats
    (dict with files/details/raw mapping, or list of findings).
    """
    file_counts: Dict[str, int] = {}

    if isinstance(data, dict):
        if "files" in data and isinstance(data["files"], dict):
            for f, count in data["files"].items():
                file_counts[f] = int(count) if isinstance(count, (int, float)) else len(count)
        elif "details" in data and isinstance(data["details"], list):
            for item in data["details"]:
                if isinstance(item, dict):
                    f = item.get("file") or item.get("path") or "unknown"
                    file_counts[f] = file_counts.get(f, 0) + 1
        elif "defects" in data and isinstance(data["defects"], list):
            for item in data["defects"]:
                if isinstance(item, dict):
                    f = item.get("file") or item.get("path") or "defects"
                    file_counts[f] = file_counts.get(f, 0) + 1
                else:
                    file_counts[str(item)] = file_counts.get(str(item), 0) + 1
        else:
            for k, v in data.items():
                if k in ("metric", "updated_at", "total", "critical_defects", "warnings"):
                    continue
                file_counts[k] = int(v) if isinstance(v, (int, float)) else len(v)

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                f = item.get("file") or item.get("path") or "unknown"
            else:
                f = str(item)
            file_counts[f] = file_counts.get(f, 0) + 1

    return file_counts


def parse_score_report(data: Any) -> float:
    """Extracts floating point score from score reports."""
    if isinstance(data, (int, float)):
        return float(data)
    if isinstance(data, dict):
        for key in ("score", "mutation_score", "coverage", "pct", "health_score"):
            if key in data and isinstance(data[key], (int, float)):
                return float(data[key])
    raise ValueError(f"Unable to extract numerical score from report data: {data}")


def evaluate_ratchet(
    findings_path: str,
    baseline_path: str = "reports/ratchet_baseline.json",
    metric: str = "defects",
    update: bool = False,
    min_score: Optional[float] = None,
) -> Tuple[Dict[str, Any], int]:
    """
    Evaluates current findings against baseline and returns (result_dict, exit_code).
    """
    if not os.path.isfile(findings_path):
        return {
            "status": "FAIL_REGRESSION",
            "metric": metric,
            "baseline_total": 0,
            "current_total": 0,
            "delta": 0,
            "ratcheted": False,
            "regressions": {},
            "improvements": {},
            "message": f"Findings file not found at: {findings_path}",
        }, 1

    try:
        with open(findings_path, "r", encoding="utf-8") as f:
            findings_data = json.load(f)
    except Exception as e:
        return {
            "status": "FAIL_REGRESSION",
            "metric": metric,
            "baseline_total": 0,
            "current_total": 0,
            "delta": 0,
            "ratcheted": False,
            "regressions": {},
            "improvements": {},
            "message": f"Malformed findings JSON: {e}",
        }, 1

    baseline_data: Optional[Dict[str, Any]] = None
    if os.path.isfile(baseline_path):
        try:
            with open(baseline_path, "r", encoding="utf-8") as f:
                baseline_data = json.load(f)
        except Exception as e:
            return {
                "status": "FAIL_REGRESSION",
                "metric": metric,
                "baseline_total": 0,
                "current_total": 0,
                "delta": 0,
                "ratcheted": False,
                "regressions": {},
                "improvements": {},
                "message": f"Malformed baseline JSON: {e}",
            }, 1

    # --- METRIC: DEFECTS ---
    if metric == "defects":
        current_files = parse_defects_report(findings_data)
        current_total = sum(current_files.values())

        if baseline_data is None:
            if update:
                os.makedirs(os.path.dirname(os.path.abspath(baseline_path)), exist_ok=True)
                new_baseline = {
                    "metric": "defects",
                    "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "total": current_total,
                    "files": current_files,
                }
                with open(baseline_path, "w", encoding="utf-8") as f:
                    json.dump(new_baseline, f, indent=2)
                return {
                    "status": "PASS",
                    "metric": "defects",
                    "baseline_total": current_total,
                    "current_total": current_total,
                    "delta": 0,
                    "ratcheted": True,
                    "regressions": {},
                    "improvements": {},
                    "message": f"Baseline initialized with {current_total} defect(s) across {len(current_files)} file(s).",
                }, 0
            else:
                return {
                    "status": "FAIL_STALE_BASELINE",
                    "metric": "defects",
                    "baseline_total": 0,
                    "current_total": current_total,
                    "delta": current_total,
                    "ratcheted": False,
                    "regressions": {},
                    "improvements": {},
                    "message": f"Baseline file does not exist at '{baseline_path}'. Run with --update to initialize the ratchet baseline.",
                }, 1

        if "files" in baseline_data and isinstance(baseline_data["files"], dict):
            baseline_files = baseline_data["files"]
        else:
            baseline_files = parse_defects_report(baseline_data)
        baseline_total = int(baseline_data.get("total", sum(baseline_files.values())))

        regressions: Dict[str, int] = {}
        improvements: Dict[str, int] = {}

        # Check all current files
        for f, c_count in current_files.items():
            b_count = int(baseline_files.get(f, 0))
            if c_count > b_count:
                regressions[f] = c_count - b_count
            elif c_count < b_count:
                improvements[f] = b_count - c_count

        # Check baseline files that might now be completely clean (count = 0)
        for f, b_count in baseline_files.items():
            if f not in current_files and b_count > 0:
                improvements[f] = b_count

        delta = current_total - baseline_total

        if regressions:
            return {
                "status": "FAIL_REGRESSION",
                "metric": "defects",
                "baseline_total": baseline_total,
                "current_total": current_total,
                "delta": delta,
                "ratcheted": False,
                "regressions": regressions,
                "improvements": improvements,
                "message": f"Quality regression detected! Findings increased by {sum(regressions.values())} in {len(regressions)} file(s).",
            }, 1

        if improvements:
            if update:
                os.makedirs(os.path.dirname(os.path.abspath(baseline_path)), exist_ok=True)
                new_baseline = {
                    "metric": "defects",
                    "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "total": current_total,
                    "files": {k: v for k, v in current_files.items() if v > 0},
                }
                with open(baseline_path, "w", encoding="utf-8") as f:
                    json.dump(new_baseline, f, indent=2)
                return {
                    "status": "PASS",
                    "metric": "defects",
                    "baseline_total": baseline_total,
                    "current_total": current_total,
                    "delta": delta,
                    "ratcheted": True,
                    "regressions": {},
                    "improvements": improvements,
                    "message": f"Baseline ratcheted down successfully! Locked in {sum(improvements.values())} resolved defect(s).",
                }, 0
            else:
                return {
                    "status": "FAIL_STALE_BASELINE",
                    "metric": "defects",
                    "baseline_total": baseline_total,
                    "current_total": current_total,
                    "delta": delta,
                    "ratcheted": False,
                    "regressions": {},
                    "improvements": improvements,
                    "message": f"Baseline is stale! {sum(improvements.values())} defect(s) resolved. Run with --update to lock in the improved ratchet baseline.",
                }, 1

        return {
            "status": "PASS",
            "metric": "defects",
            "baseline_total": baseline_total,
            "current_total": current_total,
            "delta": 0,
            "ratcheted": False,
            "regressions": {},
            "improvements": {},
            "message": "Ratchet check passed: findings match baseline.",
        }, 0

    # --- METRIC: MUTATION-SCORE OR COVERAGE ---
    elif metric in ("mutation-score", "coverage"):
        try:
            current_score = parse_score_report(findings_data)
        except ValueError as e:
            return {
                "status": "FAIL_REGRESSION",
                "metric": metric,
                "baseline_total": 0,
                "current_total": 0,
                "delta": 0,
                "ratcheted": False,
                "regressions": {},
                "improvements": {},
                "message": str(e),
            }, 1

        if min_score is not None and current_score < min_score:
            return {
                "status": "FAIL_REGRESSION",
                "metric": metric,
                "baseline_total": min_score,
                "current_total": current_score,
                "delta": round(current_score - min_score, 2),
                "ratcheted": False,
                "regressions": {"minimum_score": round(min_score - current_score, 2)},
                "improvements": {},
                "message": f"Current score {current_score}% is below minimum required score {min_score}%.",
            }, 1

        if baseline_data is None:
            if update:
                os.makedirs(os.path.dirname(os.path.abspath(baseline_path)), exist_ok=True)
                new_baseline = {
                    "metric": metric,
                    "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "score": current_score,
                }
                with open(baseline_path, "w", encoding="utf-8") as f:
                    json.dump(new_baseline, f, indent=2)
                return {
                    "status": "PASS",
                    "metric": metric,
                    "baseline_total": current_score,
                    "current_total": current_score,
                    "delta": 0.0,
                    "ratcheted": True,
                    "regressions": {},
                    "improvements": {},
                    "message": f"Baseline initialized with {metric} score of {current_score}%.",
                }, 0
            else:
                return {
                    "status": "FAIL_STALE_BASELINE",
                    "metric": metric,
                    "baseline_total": 0.0,
                    "current_total": current_score,
                    "delta": current_score,
                    "ratcheted": False,
                    "regressions": {},
                    "improvements": {},
                    "message": f"Baseline file does not exist at '{baseline_path}'. Run with --update to initialize the ratchet baseline.",
                }, 1

        baseline_score = float(baseline_data.get("score", 0.0))
        delta = round(current_score - baseline_score, 2)

        if current_score < baseline_score:
            return {
                "status": "FAIL_REGRESSION",
                "metric": metric,
                "baseline_total": baseline_score,
                "current_total": current_score,
                "delta": delta,
                "ratcheted": False,
                "regressions": {"score_drop": round(baseline_score - current_score, 2)},
                "improvements": {},
                "message": f"Score regressed from {baseline_score}% to {current_score}% (delta: {delta}%).",
            }, 1

        if current_score > baseline_score:
            if update:
                os.makedirs(os.path.dirname(os.path.abspath(baseline_path)), exist_ok=True)
                new_baseline = {
                    "metric": metric,
                    "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "score": current_score,
                }
                with open(baseline_path, "w", encoding="utf-8") as f:
                    json.dump(new_baseline, f, indent=2)
                return {
                    "status": "PASS",
                    "metric": metric,
                    "baseline_total": baseline_score,
                    "current_total": current_score,
                    "delta": delta,
                    "ratcheted": True,
                    "regressions": {},
                    "improvements": {"score_gain": delta},
                    "message": f"Baseline ratcheted up to {current_score}%. Locked in improvement.",
                }, 0
            else:
                return {
                    "status": "FAIL_STALE_BASELINE",
                    "metric": metric,
                    "baseline_total": baseline_score,
                    "current_total": current_score,
                    "delta": delta,
                    "ratcheted": False,
                    "regressions": {},
                    "improvements": {"score_gain": delta},
                    "message": f"Baseline is stale! Score improved from {baseline_score}% to {current_score}%. Run with --update to lock in the higher baseline.",
                }, 1

        return {
            "status": "PASS",
            "metric": metric,
            "baseline_total": baseline_score,
            "current_total": current_score,
            "delta": 0.0,
            "ratcheted": False,
            "regressions": {},
            "improvements": {},
            "message": f"Score matches baseline ({current_score}%).",
        }, 0

    return {
        "status": "FAIL_REGRESSION",
        "metric": metric,
        "baseline_total": 0,
        "current_total": 0,
        "delta": 0,
        "ratcheted": False,
        "regressions": {},
        "improvements": {},
        "message": f"Unsupported metric: '{metric}'. Supported: defects, mutation-score, coverage.",
    }, 1


def build_parser() -> argparse.ArgumentParser:
    """Builds CLI argument parser for ratchet_sentinel."""
    parser = argparse.ArgumentParser(
        description="Monotonic Quality Ratchet (Invariant 11 / Hashimoto Principle Sensor)"
    )
    parser.add_argument("--findings", required=True, type=str, help="Path to current findings JSON report")
    parser.add_argument(
        "--baseline",
        type=str,
        default="reports/ratchet_baseline.json",
        help="Path to persistent baseline JSON (default: reports/ratchet_baseline.json)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Ratchet down the baseline to lock in newly resolved debt",
    )
    parser.add_argument(
        "--metric",
        type=str,
        choices=["defects", "mutation-score", "coverage"],
        default="defects",
        help="Target metric type to evaluate (default: defects)",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=None,
        help="Enforce minimum absolute threshold alongside monotonicity",
    )
    parser.add_argument("--json", action="store_true", help="Output pure JSON report to stdout")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    report, exit_code = evaluate_ratchet(
        findings_path=args.findings,
        baseline_path=args.baseline,
        metric=args.metric,
        update=args.update,
        min_score=args.min_score,
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        status = report["status"]
        if status == "PASS":
            print(f"[PASS] {report['message']}")
            print(f"Metric: {report['metric']} | Baseline: {report['baseline_total']} | Current: {report['current_total']}")
        elif status == "FAIL_STALE_BASELINE":
            print(f"[WARN/STALE] {report['message']}")
            print(f"Baseline: {report['baseline_total']} -> Current: {report['current_total']} (Delta: {report['delta']})")
        else:
            print(f"[FAIL_REGRESSION] {report['message']}")
            if report.get("regressions"):
                print("Regressions detected:")
                for target, diff in report["regressions"].items():
                    print(f"  - {target}: +{diff}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
