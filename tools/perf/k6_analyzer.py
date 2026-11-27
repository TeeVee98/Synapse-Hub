#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tools/perf/k6_analyzer.py — Enterprise k6 Performance Results Analyzer & CI/CD Gatekeeper
------------------------------------------------------------------------------------------
Parses k6 summary JSON exports (--summary-export) and raw JSON telemetry streams,
calculates statistical latencies (Avg, Med, P90, P95, P99, Error Rate, RPS), evaluates
SLA compliance budgets, and enforces zero-tolerance Quality Gates in CI/CD pipelines.

Usage:
  python tools/perf/k6_analyzer.py summary.json --sla-p95 500 --max-error-rate 1.0
  python tools/perf/k6_analyzer.py summary.json --markdown report.md --json metrics.json
"""

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

import json
import math
import argparse
from typing import Dict, List, Any, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def parse_k6_summary(file_path: str) -> Dict[str, Any]:
    """Parses k6 summary JSON export or line-delimited raw JSON stream."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"k6 results file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read().strip()

    if not content:
        raise ValueError(f"k6 results file is empty: {file_path}")

    # Check if standard summary JSON object
    if content.startswith("{") and content.endswith("}"):
        try:
            data = json.loads(content)
            if "metrics" in data:
                return _extract_from_metrics_dict(data, raw_text=content)
        except json.JSONDecodeError:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass

    # Fallback: Line-delimited JSON stream
    return _parse_k6_jsonl_stream(content)


def _parse_k6_jsonl_stream(content: str) -> Dict[str, Any]:
    """Parses line-delimited k6 JSON metric events."""
    durations: List[float] = []
    fails = 0
    total_reqs = 0

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        metric = record.get("metric")
        val = record.get("data", {}).get("value")
        if val is None:
            continue
        if metric == "http_req_duration":
            durations.append(float(val))
        elif metric == "http_req_failed":
            total_reqs += 1
            if float(val) > 0:
                fails += 1

    if not durations and total_reqs == 0:
        raise ValueError("No valid k6 metric points found in log file.")

    durations.sort()
    count = len(durations)
    avg = sum(durations) / count if count > 0 else 0.0
    err_rate = (fails / total_reqs * 100.0) if total_reqs > 0 else 0.0

    def calc_percentile(p: float) -> float:
        if not durations:
            return 0.0
        k = (count - 1) * (p / 100.0)
        f_idx = math.floor(k)
        c_idx = math.ceil(k)
        if f_idx == c_idx:
            return durations[int(k)]
        return durations[f_idx] * (c_idx - k) + durations[c_idx] * (k - f_idx)

    return {
        "total_requests": total_reqs or count,
        "failed_requests": fails,
        "error_rate_pct": round(err_rate, 3),
        "latency_min": round(durations[0], 2) if durations else 0.0,
        "latency_max": round(durations[-1], 2) if durations else 0.0,
        "latency_avg": round(avg, 2),
        "latency_med": round(calc_percentile(50.0), 2),
        "latency_p90": round(calc_percentile(90.0), 2),
        "latency_p95": round(calc_percentile(95.0), 2),
        "latency_p99": round(calc_percentile(99.0), 2),
        "achieved_arrival_rate": None,
        "dropped_iterations": 0,
        "recovery_p95_ms": None,
        "telemetry_kind": "http_load",
        "raw_metrics": {},
    }


def classify_k6_telemetry(data: Dict[str, Any], raw_text: str = "") -> str:
    """Distinguishes real HTTP load summaries from Hub CPU serialization microbenchmarks."""
    blob = raw_text or json.dumps(data)
    if "local://benchmark" in blob or "LOCAL_CPU_JSON_SERIALIZE" in blob:
        return "hub_cpu_microbenchmark"
    return "http_load"


def _extract_from_metrics_dict(data: Dict[str, Any], raw_text: str = "") -> Dict[str, Any]:
    metrics = data.get("metrics", {})
    req_dur = metrics.get("http_req_duration", {})
    dur_values = req_dur.get("values", req_dur)

    req_failed = metrics.get("http_req_failed", {})
    fail_values = req_failed.get("values", req_failed)

    http_reqs = metrics.get("http_reqs", {})
    http_req_values = http_reqs.get("values", http_reqs)

    iterations = metrics.get("iterations", {})
    iter_values = iterations.get("values", iterations)

    if "count" in http_req_values:
        total_reqs = int(http_req_values.get("count", 0))
    else:
        total_reqs = int(iter_values.get("count", 0))

    raw_rate = http_req_values.get("rate", iter_values.get("rate"))
    achieved_arrival_rate = round(float(raw_rate), 3) if raw_rate is not None else None

    dropped_node = metrics.get("dropped_iterations", {})
    dropped_vals = dropped_node.get("values", dropped_node)
    dropped_iterations = int(dropped_vals.get("count", 0))

    rec_node = metrics.get("http_req_duration{scenario:recovery_probe}") or metrics.get("recovery_probe") or {}
    rec_vals = rec_node.get("values", rec_node) if isinstance(rec_node, dict) else {}
    raw_rec_p95 = rec_vals.get("p(95)")
    recovery_p95_ms = round(float(raw_rec_p95), 2) if raw_rec_p95 is not None else None

    error_rate = float(fail_values.get("value", fail_values.get("rate", 0.0))) * 100.0
    fails = int(fail_values.get("passes", 0)) if "passes" in fail_values else int(total_reqs * (error_rate / 100.0))

    return {
        "total_requests": total_reqs,
        "failed_requests": fails,
        "error_rate_pct": round(error_rate, 3),
        "latency_min": round(float(dur_values.get("min", 0.0)), 2),
        "latency_max": round(float(dur_values.get("max", 0.0)), 2),
        "latency_avg": round(float(dur_values.get("avg", 0.0)), 2),
        "latency_med": round(float(dur_values.get("med", dur_values.get("p(50)", 0.0))), 2),
        "latency_p90": round(float(dur_values.get("p(90)", 0.0)), 2),
        "latency_p95": round(float(dur_values.get("p(95)", 0.0)), 2),
        "latency_p99": round(float(dur_values.get("p(99)", 0.0)), 2),
        "achieved_arrival_rate": achieved_arrival_rate,
        "dropped_iterations": dropped_iterations,
        "recovery_p95_ms": recovery_p95_ms,
        "telemetry_kind": classify_k6_telemetry(data, raw_text),
        "raw_metrics": metrics,
    }


def evaluate_sla(
    metrics: Dict[str, Any],
    sla_p95: Optional[float] = 500.0,
    sla_p99: Optional[float] = 1000.0,
    sla_avg: Optional[float] = None,
    max_error_rate: float = 1.0,
    min_arrival_rate: Optional[float] = None,
    max_dropped_iterations: Optional[int] = 0,
    require_recovery: bool = False,
    max_recovery_p95: Optional[float] = None,
) -> Tuple[bool, List[str]]:
    """Evaluates metrics against SLA budgets. Returns (is_pass, list_of_violations)."""
    violations = []

    if metrics.get("telemetry_kind") == "hub_cpu_microbenchmark":
        violations.append("Synthetic Hub CPU microbenchmark telemetry is not valid HTTP load evidence")

    if int(metrics.get("total_requests", 0)) <= 0:
        violations.append("No HTTP request samples recorded (total_requests <= 0)")

    if sla_p95 is not None and metrics["latency_p95"] > sla_p95:
        violations.append(
            f"P95 latency breached: {metrics['latency_p95']}ms > SLA limit {sla_p95}ms"
        )

    if sla_p99 is not None and metrics["latency_p99"] > sla_p99:
        violations.append(
            f"P99 latency breached: {metrics['latency_p99']}ms > SLA limit {sla_p99}ms"
        )

    if sla_avg is not None and metrics["latency_avg"] > sla_avg:
        violations.append(
            f"Average latency breached: {metrics['latency_avg']}ms > SLA limit {sla_avg}ms"
        )

    if metrics["error_rate_pct"] > max_error_rate:
        violations.append(
            f"Error rate breached: {metrics['error_rate_pct']}% > SLA limit {max_error_rate}%"
        )

    if min_arrival_rate is not None:
        achieved = metrics.get("achieved_arrival_rate")
        if achieved is None or achieved < min_arrival_rate:
            violations.append(
                f"Underload: achieved arrival rate {achieved}/s < required {min_arrival_rate}/s"
            )

    if max_dropped_iterations is not None:
        dropped = int(metrics.get("dropped_iterations", 0))
        if dropped > max_dropped_iterations:
            violations.append(
                f"Dropped iterations exceeded: {dropped} > allowed {max_dropped_iterations}"
            )

    rec_p95 = metrics.get("recovery_p95_ms")
    if require_recovery and rec_p95 is None:
        violations.append("Missing post-load recovery probe observations")
    elif max_recovery_p95 is not None and rec_p95 is not None and rec_p95 > max_recovery_p95:
        violations.append(
            f"Recovery probe P95 breached: {rec_p95}ms > SLA limit {max_recovery_p95}ms"
        )

    return len(violations) == 0, violations


def format_markdown_report(metrics: Dict[str, Any], violations: List[str]) -> str:
    status_badge = "✅ **PASSED (Within SLA Budget)**" if not violations else "❌ **FAILED (SLA Breached)**"
    lines = [
        "# 🚀 k6 Performance SLA Verification Report",
        "",
        f"- **Evaluation Status:** {status_badge}",
        f"- **Total Requests Executed:** `{metrics['total_requests']}`",
        f"- **Error Rate:** `{metrics['error_rate_pct']}%` ({metrics['failed_requests']} failures)",
        "",
        "### Latency Percentiles (Response Times)",
        "| Metric | Measured Value | SLA Budget Status |",
        "| :--- | :--- | :--- |",
        f"| **Average Latency** | `{metrics['latency_avg']} ms` | Informational |",
        f"| **Median (P50)** | `{metrics['latency_med']} ms` | Baseline |",
        f"| **90th Percentile (P90)** | `{metrics['latency_p90']} ms` | Expected Nominal |",
        f"| **95th Percentile (P95)** | `{metrics['latency_p95']} ms` | Target SLA |",
        f"| **99th Percentile (P99)** | `{metrics['latency_p99']} ms` | Tail Latency Cap |",
        f"| **Max Recorded** | `{metrics['latency_max']} ms` | Peak Spike |",
        "",
    ]
    if violations:
        lines.append("### ⚠️ SLA Violations Detected")
        for v in violations:
            lines.append(f"- ❌ {v}")
        lines.append("")

    lines.append("> *Generated by Synapse Hub k6 Performance Analyzer (`tools/perf/k6_analyzer.py`)*")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Enterprise k6 Performance Results Analyzer & Gatekeeper")
    parser.add_argument("file", help="Path to k6 summary JSON or line-delimited results file")
    parser.add_argument("--sla-p95", type=float, default=500.0, help="Max acceptable P95 latency in ms (default: 500)")
    parser.add_argument("--sla-p99", type=float, default=1000.0, help="Max acceptable P99 latency in ms (default: 1000)")
    parser.add_argument("--sla-avg", type=float, default=None, help="Max acceptable Average latency in ms (optional)")
    parser.add_argument("--max-error-rate", type=float, default=1.0, help="Max acceptable error rate percentage (default: 1.0%%)")
    parser.add_argument("--markdown", help="Output path for Markdown summary report")
    parser.add_argument("--json", dest="json_out", help="Output path for JSON metric report")
    args = parser.parse_args()

    try:
        metrics = parse_k6_summary(args.file)
    except Exception as e:
        print(f"{RED}❌ Error parsing k6 file: {e}{RESET}", file=sys.stderr)
        sys.exit(2)

    passed, violations = evaluate_sla(
        metrics,
        sla_p95=args.sla_p95,
        sla_p99=args.sla_p99,
        sla_avg=args.sla_avg,
        max_error_rate=args.max_error_rate,
    )

    print("=" * 68)
    print(f"  📊 {BOLD}k6 PERFORMANCE SLA ANALYSIS RESULTS{RESET}")
    print("=" * 68)
    print(f"  Total Requests : {metrics['total_requests']}")
    print(f"  Error Rate     : {metrics['error_rate_pct']}% ({metrics['failed_requests']} failed)")
    print(f"  P50 (Median)   : {metrics['latency_med']} ms")
    print(f"  P90 Latency    : {metrics['latency_p90']} ms")
    print(f"  P95 Latency    : {metrics['latency_p95']} ms (SLA limit: {args.sla_p95} ms)")
    print(f"  P99 Latency    : {metrics['latency_p99']} ms (SLA limit: {args.sla_p99} ms)")
    print(f"  Avg Latency    : {metrics['latency_avg']} ms")
    print("=" * 68)

    if passed:
        print(f"  {GREEN}{BOLD}✅ SLA STATUS: PASS — All performance thresholds satisfied!{RESET}\n")
    else:
        print(f"  {RED}{BOLD}❌ SLA STATUS: FAIL — Performance budget exceeded!{RESET}")
        for v in violations:
            print(f"    • {RED}{v}{RESET}")
        print()

    if args.markdown:
        try:
            with open(args.markdown, "w", encoding="utf-8") as f:
                f.write(format_markdown_report(metrics, violations))
            print(f"  📄 Markdown report written to: {args.markdown}")
        except OSError as e:
            print(f"  ⚠️ Could not write markdown report: {e}", file=sys.stderr)

    if args.json_out:
        try:
            out_data = {
                "passed": passed,
                "violations": violations,
                "metrics": metrics,
            }
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(out_data, f, indent=2)
            print(f"  📄 JSON metrics written to: {args.json_out}")
        except OSError as e:
            print(f"  ⚠️ Could not write JSON metrics: {e}", file=sys.stderr)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
