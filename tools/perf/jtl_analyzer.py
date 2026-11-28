#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tools/jtl_analyzer.py — Enterprise Apache JMeter JTL Results Analyzer & CI/CD Gatekeeper
-----------------------------------------------------------------------------------------
Parses Apache JMeter JTL log results (CSV or XML format), calculates statistical percentiles
(P50, P90, P95, P99, Throughput, Error Rate), evaluates SLA compliance thresholds, and
enforces zero-tolerance Quality Gates in CI/CD pipelines with deterministic exit codes.

Features:
  1. Universal Parsing: Supports standard JMeter CSV JTL and legacy XML JTL formats.
  2. Statistical Engine: Calculates Min, Max, Average, P50 (Median), P90, P95, P99,
     Throughput (TPS/RPS), Network KB/s, and Error Rate (%) per sampler and aggregate.
  3. CI/CD Quality Gate: Evaluates user-defined SLA thresholds:
     - Maximum acceptable P95 / P99 latency (ms)
     - Maximum acceptable Average latency (ms)
     - Maximum acceptable Error Rate (%)
     Returns Exit Code 0 on PASS, Exit Code 1 on SLA breach.
  4. Multi-Format Reporting:
     - ANSI terminal summary table
     - GitHub / GitLab Markdown report for Pull Request annotations
     - Raw JSON export for downstream telemetry and APM indexing.

Usage:
  python tools/jtl_analyzer.py results.jtl --sla-p95 500 --max-error-rate 1.0
  python tools/jtl_analyzer.py results.jtl --markdown report.md --json metrics.json
  agent-qa analyze-jtl results.jtl --sla-p95 400
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


import os
import sys
import csv
import json
import math
import argparse
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple

# Enforce UTF-8 stdout encoding for Windows/macOS/Linux console compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def calculate_percentile(sorted_values: List[float], percentile: float) -> float:
    """Calculates percentile from a pre-sorted list using linear interpolation."""
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_values[int(k)])
    d0 = sorted_values[int(f)] * (c - k)
    d1 = sorted_values[int(c)] * (k - f)
    return float(d0 + d1)


class SamplerStats:
    """Aggregates metrics for a single sampler label."""
    def __init__(self, label: str):
        self.label = label
        self.samples: int = 0
        self.errors: int = 0
        self.elapsed_times: List[float] = []
        self.success_elapsed_times: List[float] = []
        self.failed_elapsed_times: List[float] = []
        self.total_bytes: int = 0
        self.start_time: Optional[int] = None
        self.end_time: Optional[int] = None
        self.response_codes: Dict[str, int] = {}

    def add_sample(self, elapsed: float, success: bool, timestamp: int, bytes_recv: int, response_code: str):
        self.samples += 1
        if success:
            self.success_elapsed_times.append(elapsed)
        else:
            self.errors += 1
            self.failed_elapsed_times.append(elapsed)
        self.elapsed_times.append(elapsed)
        self.total_bytes += bytes_recv

        if self.start_time is None or timestamp < self.start_time:
            self.start_time = timestamp
        if self.end_time is None or timestamp > self.end_time:
            self.end_time = timestamp

        code = str(response_code).strip() or "UNKNOWN"
        self.response_codes[code] = self.response_codes.get(code, 0) + 1

    def compute(self) -> Dict[str, Any]:
        if not self.elapsed_times:
            return {
                "label": self.label,
                "samples": 0,
                "errors": 0,
                "error_rate_pct": 0.0,
                "avg_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
                "median_ms": 0.0,
                "p90_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "p999_ms": 0.0,
                "p95_success_ms": 0.0,
                "p99_success_ms": 0.0,
                "p95_failed_ms": 0.0,
                "throughput_tps": 0.0,
                "kb_per_sec": 0.0,
                "response_codes": self.response_codes,
            }

        sorted_times = sorted(self.elapsed_times)
        total_time = sum(sorted_times)
        count = len(sorted_times)
        avg_ms = total_time / count
        min_ms = sorted_times[0]
        max_ms = sorted_times[-1]
        p50 = calculate_percentile(sorted_times, 50.0)
        p90 = calculate_percentile(sorted_times, 90.0)
        p95 = calculate_percentile(sorted_times, 95.0)
        p99 = calculate_percentile(sorted_times, 99.0)
        p999 = calculate_percentile(sorted_times, 99.9)

        # Google SRE Golden Signal: Disaggregate Latency by Success vs Failure
        sorted_success = sorted(self.success_elapsed_times) if self.success_elapsed_times else []
        p95_success = calculate_percentile(sorted_success, 95.0) if sorted_success else p95
        p99_success = calculate_percentile(sorted_success, 99.0) if sorted_success else p99

        sorted_failed = sorted(self.failed_elapsed_times) if self.failed_elapsed_times else []
        p95_failed = calculate_percentile(sorted_failed, 95.0) if sorted_failed else 0.0

        error_rate = (self.errors / count) * 100.0 if count > 0 else 0.0

        # Duration in seconds
        duration_sec = 0.0
        if self.start_time is not None and self.end_time is not None:
            duration_sec = max((self.end_time - self.start_time) / 1000.0, 0.001)

        tps = count / duration_sec if duration_sec > 0 else 0.0
        kb_sec = (self.total_bytes / 1024.0) / duration_sec if duration_sec > 0 else 0.0

        return {
            "label": self.label,
            "samples": count,
            "errors": self.errors,
            "error_rate_pct": round(error_rate, 2),
            "avg_ms": round(avg_ms, 2),
            "min_ms": round(min_ms, 2),
            "max_ms": round(max_ms, 2),
            "median_ms": round(p50, 2),
            "p90_ms": round(p90, 2),
            "p95_ms": round(p95, 2),
            "p99_ms": round(p99, 2),
            "p999_ms": round(p999, 2),
            "p95_success_ms": round(p95_success, 2),
            "p99_success_ms": round(p99_success, 2),
            "p95_failed_ms": round(p95_failed, 2),
            "throughput_tps": round(tps, 2),
            "kb_per_sec": round(kb_sec, 2),
            "response_codes": self.response_codes,
        }


try:
    from tools.report.telemetry_correlator import parse_jtl_timestamp
except ImportError:
    from telemetry_correlator import parse_jtl_timestamp


def _aggregate_samples(
    samples: List[Tuple[str, float, bool, int, int, str]],
    warmup_sec: float = 0.0,
    cooldown_sec: float = 0.0,
) -> Tuple[Dict[str, SamplerStats], SamplerStats]:
    """Aggregates raw sample tuples with optional steady-state warmup/cooldown exclusion."""
    per_sampler: Dict[str, SamplerStats] = {}
    aggregate = SamplerStats("TOTAL AGGREGATE")
    if not samples:
        return per_sampler, aggregate

    if warmup_sec > 0 or cooldown_sec > 0:
        timestamps = [s[3] for s in samples if s[3] > 0]
        if timestamps:
            win_start = min(timestamps) + int(warmup_sec * 1000)
            win_end = max(timestamps) - int(cooldown_sec * 1000)
            if win_start <= win_end:
                samples = [s for s in samples if win_start <= s[3] <= win_end]

    for label, elapsed, success, timestamp, bytes_recv, resp_code in samples:
        if label not in per_sampler:
            per_sampler[label] = SamplerStats(label)
        per_sampler[label].add_sample(elapsed, success, timestamp, bytes_recv, resp_code)
        aggregate.add_sample(elapsed, success, timestamp, bytes_recv, resp_code)

    return per_sampler, aggregate


def _read_csv_jtl_rows(filepath: str) -> List[Tuple[str, float, bool, int, int, str]]:
    """Reads raw sample tuples from standard comma/tab delimited JTL CSV file."""
    rows: List[Tuple[str, float, bool, int, int, str]] = []
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        first_line = f.readline()
        if not first_line:
            return rows
        delimiter = "\t" if "\t" in first_line else ","
        f.seek(0)

        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            try:
                elapsed = float(row.get("elapsed") or row.get("Elapsed") or row.get("time") or 0)
                label = row.get("label") or row.get("Label") or "Unknown"
                success_val = row.get("success") or row.get("Success") or "true"
                success = str(success_val).strip().lower() in ("true", "1")
                ts_raw = row.get("timeStamp") or row.get("Timestamp") or row.get("t") or 0
                timestamp = parse_jtl_timestamp(ts_raw)
                bytes_val = row.get("bytes") or row.get("Bytes") or 0
                bytes_recv = int(float(bytes_val))
                resp_code = row.get("responseCode") or row.get("ResponseCode") or row.get("rc") or "200"
                rows.append((label, elapsed, success, timestamp, bytes_recv, resp_code))
            except Exception:
                continue
    return rows


def _read_xml_jtl_rows(filepath: str) -> List[Tuple[str, float, bool, int, int, str]]:
    """Reads top-level sample tuples from XML JTL without double-counting nested subresults."""
    rows: List[Tuple[str, float, bool, int, int, str]] = []
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        top_elements = [el for el in list(root) if el.tag in ("httpSample", "sample")]
        for elem in top_elements:
            try:
                elapsed = float(elem.attrib.get("t", 0))
                label = elem.attrib.get("lb", "Unknown")
                success = elem.attrib.get("s", "true").lower() == "true"
                timestamp = parse_jtl_timestamp(elem.attrib.get("ts", 0))
                bytes_recv = int(elem.attrib.get("by", 0))
                resp_code = elem.attrib.get("rc", "200")
                rows.append((label, elapsed, success, timestamp, bytes_recv, resp_code))
            except Exception:
                continue
    except Exception as e:
        print(f"⚠️ XML Parse Error: {e}", file=sys.stderr)
    return rows


def parse_csv_jtl(
    filepath: str,
    warmup_sec: float = 0.0,
    cooldown_sec: float = 0.0,
) -> Tuple[Dict[str, SamplerStats], SamplerStats]:
    """Parses standard comma/tab delimited JTL CSV file."""
    return _aggregate_samples(_read_csv_jtl_rows(filepath), warmup_sec=warmup_sec, cooldown_sec=cooldown_sec)


def parse_xml_jtl(
    filepath: str,
    warmup_sec: float = 0.0,
    cooldown_sec: float = 0.0,
) -> Tuple[Dict[str, SamplerStats], SamplerStats]:
    """Parses XML JTL file (<testResults> / top-level <httpSample> / <sample>)."""
    return _aggregate_samples(_read_xml_jtl_rows(filepath), warmup_sec=warmup_sec, cooldown_sec=cooldown_sec)


def parse_jtl(
    filepath: str,
    warmup_sec: float = 0.0,
    cooldown_sec: float = 0.0,
) -> Tuple[Dict[str, SamplerStats], SamplerStats]:
    """Detects format and parses JTL file with optional steady-state windowing."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"JTL file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        head = f.read(256).strip()

    if head.startswith("<?xml") or head.startswith("<testResults"):
        return parse_xml_jtl(filepath, warmup_sec=warmup_sec, cooldown_sec=cooldown_sec)
    return parse_csv_jtl(filepath, warmup_sec=warmup_sec, cooldown_sec=cooldown_sec)


def evaluate_sla(
    agg_stats: Dict[str, Any],
    sla_p95: Optional[float] = 500.0,
    sla_p99: Optional[float] = None,
    sla_avg: Optional[float] = None,
    max_error_rate: Optional[float] = 1.0
) -> Tuple[bool, List[str]]:
    """Evaluates computed aggregate metrics against SLA limits."""
    violations: List[str] = []

    if sla_p95 is not None and agg_stats["p95_ms"] > sla_p95:
        violations.append(f"P95 Latency SLA Breached: {agg_stats['p95_ms']}ms > {sla_p95}ms")

    if sla_p99 is not None and agg_stats["p99_ms"] > sla_p99:
        violations.append(f"P99 Latency SLA Breached: {agg_stats['p99_ms']}ms > {sla_p99}ms")

    if sla_avg is not None and agg_stats["avg_ms"] > sla_avg:
        violations.append(f"Average Latency SLA Breached: {agg_stats['avg_ms']}ms > {sla_avg}ms")

    if max_error_rate is not None and agg_stats["error_rate_pct"] > max_error_rate:
        violations.append(f"Error Rate SLA Breached: {agg_stats['error_rate_pct']}% > {max_error_rate}%")

    passed = (len(violations) == 0)
    return passed, violations


def evaluate_tiered_sampler_sla(
    per_sampler_data: List[Dict[str, Any]],
    tiered_rules: Optional[Dict[str, float]] = None,
    max_error_rate: float = 1.0,
) -> Tuple[bool, List[str]]:
    """Enforces tiered per-sampler P95 & error-rate budgets (Read / Search / Write)."""
    rules = {
        "read_p95_ms": 200.0,
        "search_p95_ms": 500.0,
        "write_p95_ms": 1000.0,
        "critical_write_error_rate_pct": 0.1,
    }
    if tiered_rules:
        rules.update({k: float(v) for k, v in tiered_rules.items()})

    violations: List[str] = []
    for row in per_sampler_data:
        label = str(row.get("label", ""))
        low = label.lower()
        p95 = float(row.get("p95_ms", 0.0))
        err_pct = float(row.get("error_rate_pct", 0.0))

        is_write = any(m in low for m in ("[post]", "[put]", "[patch]", "[delete]", "post ", "put ", "patch ", "delete ", "checkout", "payment", "auth", "login"))
        is_search = any(k in low for k in ("search", "filter", "query", "report", "export", "analytics"))
        is_critical = any(k in low for k in ("checkout", "payment", "auth", "login"))

        if is_write:
            p95_budget = rules["write_p95_ms"]
            tier_name = "Write/Transaction"
            err_budget = rules["critical_write_error_rate_pct"] if is_critical else max_error_rate
        elif is_search:
            p95_budget = rules["search_p95_ms"]
            tier_name = "Search/Filter"
            err_budget = max_error_rate
        else:
            p95_budget = rules["read_p95_ms"]
            tier_name = "Read/Lookup"
            err_budget = min(max_error_rate, 0.5)

        if p95 > p95_budget:
            violations.append(f"[{tier_name}] {label} P95 SLA Breached: {p95}ms > {p95_budget}ms")
        if err_pct > err_budget:
            violations.append(f"[{tier_name}] {label} Error Rate SLA Breached: {err_pct}% > {err_budget}%")

    return (len(violations) == 0), violations


def format_table(per_sampler_data: List[Dict[str, Any]], agg_data: Dict[str, Any]) -> str:
    """Formats metrics into a clean CLI table."""
    headers = ["Sampler Label", "Samples", "Errors (%)", "Avg (ms)", "Min", "Max", "P90", "P95", "P99", "TPS"]
    col_w = [30, 9, 12, 10, 8, 8, 8, 8, 8, 10]

    lines = []
    header_str = " | ".join(h.ljust(col_w[i]) for i, h in enumerate(headers))
    sep_str = "-+-".join("-" * col_w[i] for i in range(len(headers)))

    lines.append(header_str)
    lines.append(sep_str)

    all_rows = list(per_sampler_data) + [agg_data]
    for row in all_rows:
        label = row["label"]
        if len(label) > 28:
            label = label[:25] + "..."
        err_str = f"{row['errors']} ({row['error_rate_pct']}%)"

        row_str = " | ".join([
            label.ljust(col_w[0]),
            str(row["samples"]).rjust(col_w[1]),
            err_str.rjust(col_w[2]),
            f"{row['avg_ms']:.1f}".rjust(col_w[3]),
            f"{row['min_ms']:.0f}".rjust(col_w[4]),
            f"{row['max_ms']:.0f}".rjust(col_w[5]),
            f"{row['p90_ms']:.1f}".rjust(col_w[6]),
            f"{row['p95_ms']:.1f}".rjust(col_w[7]),
            f"{row['p99_ms']:.1f}".rjust(col_w[8]),
            f"{row['throughput_tps']:.1f}".rjust(col_w[9]),
        ])
        if row == agg_data:
            lines.append(sep_str)
        lines.append(row_str)

    return "\n".join(lines)


def generate_markdown_report(
    jtl_file: str,
    per_sampler_data: List[Dict[str, Any]],
    agg_data: Dict[str, Any],
    passed: bool,
    violations: List[str],
    sla_info: Dict[str, Any]
) -> str:
    """Generates GitHub / GitLab Markdown report for Pull Request annotations."""
    status_badge = "✅ **PASSED**" if passed else "❌ **FAILED (SLA BREACHED)**"

    lines = [
        "# 🚀 Apache JMeter Performance & Load Test Report",
        "",
        f"- **Source Result File:** `{os.path.basename(jtl_file)}`",
        f"- **Quality Gate Status:** {status_badge}",
        f"- **Total Virtual Requests:** `{agg_data['samples']:,}`",
        f"- **Total Errors:** `{agg_data['errors']}` ({agg_data['error_rate_pct']}%)",
        f"- **Average Latency:** `{agg_data['avg_ms']} ms`",
        f"- **95th Percentile (P95):** `{agg_data['p95_ms']} ms`",
        f"- **Throughput:** `{agg_data['throughput_tps']} req/sec`",
        "",
    ]

    if violations:
        lines.extend([
            "### ⚠️ SLA Violations Detected",
            "",
        ])
        for v in violations:
            lines.append(f"- 🔴 `{v}`")
        lines.append("")

    lines.extend([
        "### 📊 Detailed Sampler Breakdown",
        "",
        "| Sampler Label | Samples | Errors | Error % | Avg (ms) | Min (ms) | Max (ms) | P90 (ms) | P95 (ms) | P99 (ms) | TPS |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ])

    for row in per_sampler_data:
        lines.append(
            f"| `{row['label']}` | {row['samples']:,} | {row['errors']} | {row['error_rate_pct']}% | "
            f"{row['avg_ms']} | {row['min_ms']} | {row['max_ms']} | {row['p90_ms']} | "
            f"**{row['p95_ms']}** | {row['p99_ms']} | {row['throughput_tps']} |"
        )

    # Aggregate row
    lines.append(
        f"| **TOTAL AGGREGATE** | **{agg_data['samples']:,}** | **{agg_data['errors']}** | **{agg_data['error_rate_pct']}%** | "
        f"**{agg_data['avg_ms']}** | **{agg_data['min_ms']}** | **{agg_data['max_ms']}** | **{agg_data['p90_ms']}** | "
        f"**{agg_data['p95_ms']}** | **{agg_data['p99_ms']}** | **{agg_data['throughput_tps']}** |"
    )

    lines.extend([
        "",
        "---",
        "*Report auto-generated by Synapse-Hub `jtl_analyzer.py` - Enterprise Performance Quality Gate.*"
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Apache JMeter JTL Results Analyzer & CI/CD SLA Quality Gatekeeper."
    )
    parser.add_argument("jtl_file", nargs="?", help="Path to JMeter results file (.jtl or .csv).")
    parser.add_argument("--sla-p95", type=float, default=500.0, help="P95 Latency threshold in ms (fails if exceeded). Default: 500.0ms.")
    parser.add_argument("--sla-p99", type=float, default=None, help="P99 Latency threshold in ms (fails if exceeded).")
    parser.add_argument("--sla-avg", type=float, default=None, help="Average Latency threshold in ms (fails if exceeded).")
    parser.add_argument("--max-error-rate", type=float, default=1.0, help="Maximum allowed error rate percentage (e.g. 1.0 = 1%%). Default: 1.0%%.")
    parser.add_argument("--markdown", "-m", help="Output path for Markdown summary report.")
    parser.add_argument("--json", "-j", help="Output path for JSON summary metrics.")
    parser.add_argument("--telemetry", help="Path to server telemetry CSV (timestamp, cpu_pct, memory_pct, db_pool_pct) for Full-Stack APM correlation.")
    parser.add_argument("--warmup-sec", type=float, default=0.0, help="Exclude initial N seconds of warm-up traffic from SLA evaluation.")
    parser.add_argument("--cooldown-sec", type=float, default=0.0, help="Exclude trailing N seconds of cool-down drainage from SLA evaluation.")
    parser.add_argument("--tiered-sla", action="store_true", help="Enforce tiered per-sampler SLAs (Read<=200ms, Search<=500ms, Write<=1000ms).")
    parser.add_argument("--sample", action="store_true", help="Generate and analyze a mock JTL dataset for verification.")

    args = parser.parse_args()

    # Handle sample verification mode
    if args.sample or not args.jtl_file:
        import tempfile
        temp_jtl = os.path.join(tempfile.gettempdir(), "sample_jmeter_run.jtl")
        with open(temp_jtl, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timeStamp", "elapsed", "label", "responseCode", "responseMessage", "threadName", "dataType", "success", "failureMessage", "bytes", "sentBytes", "grpThreads", "allThreads", "URL", "Latency", "IdleTime", "Connect"])

            # Generate 200 synthetic rows
            import time
            base_time = int(time.time() * 1000)
            for i in range(150):
                writer.writerow([base_time + (i * 100), 120 + (i % 50), "[GET] /api/v1/catalogs", "200", "OK", "Thread 1-1", "text", "true", "", 1024, 256, 10, 10, "http://api.local/catalogs", 115, 0, 15])
            for i in range(45):
                writer.writerow([base_time + (i * 100), 280 + (i % 80), "[POST] /api/v1/orders", "201", "Created", "Thread 1-2", "text", "true", "", 2048, 512, 10, 10, "http://api.local/orders", 270, 0, 20])
            for i in range(5):
                writer.writerow([base_time + (i * 100), 1500, "[POST] /api/v1/orders", "500", "Internal Error", "Thread 1-2", "text", "false", "DB Timeout", 512, 512, 10, 10, "http://api.local/orders", 1490, 0, 25])

        args.jtl_file = temp_jtl
        print(f"🔬 [SAMPLE MODE] Generated synthetic benchmark JTL: {temp_jtl}")

    per_sampler_raw, agg_raw = parse_jtl(
        args.jtl_file,
        warmup_sec=args.warmup_sec,
        cooldown_sec=args.cooldown_sec,
    )
    if not per_sampler_raw:
        print(f"⚠️ No sample records found in {args.jtl_file}", file=sys.stderr)
        sys.exit(0)

    per_sampler_data = [stats.compute() for stats in per_sampler_raw.values()]
    agg_data = agg_raw.compute()

    passed, violations = evaluate_sla(
        agg_data,
        sla_p95=args.sla_p95,
        sla_p99=args.sla_p99,
        sla_avg=args.sla_avg,
        max_error_rate=args.max_error_rate
    )
    if args.tiered_sla:
        tiered_ok, tiered_viols = evaluate_tiered_sampler_sla(
            per_sampler_data,
            max_error_rate=float(args.max_error_rate or 1.0),
        )
        if not tiered_ok:
            passed = False
            violations.extend(tiered_viols)

    print("\n" + "=" * 90)
    print("  APACHE JMETER PERFORMANCE RESULTS MATRIX (CI/CD QUALITY GATE)")
    print("=" * 90)
    print(format_table(per_sampler_data, agg_data))
    print("=" * 90)

    # Print SLA Verdict
    print("\n🎯 [QUALITY GATE SLA VERDICT]")
    if passed:
        print("✅ ALL PERFORMANCE SLAs PASSED! Ready for deployment/merge.")
    else:
        print("❌ PERFORMANCE SLA BREACHED:")
        for v in violations:
            print(f"   🔴 {v}")

    # Optional Telemetry Correlation
    telemetry_analysis = None
    if args.telemetry and os.path.exists(args.telemetry):
        from telemetry_correlator import parse_jtl_time_series, parse_server_metrics, run_correlation_analysis
        jtl_buckets = parse_jtl_time_series(args.jtl_file, bucket_sec=5)
        server_series = parse_server_metrics(args.telemetry, bucket_sec=5)
        telemetry_analysis = run_correlation_analysis(jtl_buckets, server_series)
        print("\n" + "=" * 90)
        print("  FULL-STACK APM & SERVER TELEMETRY CORRELATION (RCA)")
        print("=" * 90)
        for k, v in telemetry_analysis["correlations"].items():
            print(f"  • {k.replace('_', ' ').title():<25} : {v:+0.3f}")
        for c in telemetry_analysis["root_causes"]:
            print(f"  [{c['severity']}] {c['component']}: {c['description']}")
            print(f"    👉 Recommendation: {c['recommendation']}")

    # Export Markdown
    if args.markdown:
        md_content = generate_markdown_report(
            args.jtl_file, per_sampler_data, agg_data, passed, violations, vars(args)
        )
        if telemetry_analysis:
            from telemetry_correlator import format_rca_markdown
            md_content += "\n\n" + format_rca_markdown(telemetry_analysis)
        os.makedirs(os.path.dirname(os.path.abspath(args.markdown)) or ".", exist_ok=True)
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"📄 Markdown Report exported: {args.markdown}")

    # Export JSON
    if args.json:
        export_payload = {
            "source_jtl": os.path.abspath(args.jtl_file),
            "passed": passed,
            "violations": violations,
            "aggregate": agg_data,
            "samplers": per_sampler_data,
            "telemetry_correlation": telemetry_analysis
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.json)) or ".", exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(export_payload, f, indent=2)
        print(f"📊 JSON Metrics exported: {args.json}")

    # Exit code enforcement
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
