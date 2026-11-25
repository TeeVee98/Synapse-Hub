#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tools/telemetry_correlator.py — Full-Stack APM & Server Telemetry Performance Correlator
---------------------------------------------------------------------------------------
Correlates Client-Side perceived response times (from JMeter .jtl) with Server-Side
infrastructure metrics (Prometheus Node Exporter, PerfMon, CloudWatch, Datadog),
performs Pearson correlation analysis, isolates resource bottlenecks, and generates
an automated Root Cause Analysis (RCA) diagnostic report for Senior Performance QCs.

Capabilities:
  1. Multi-Dimensional Correlation:
     - Client Latency (P95/P99 ms) vs Server CPU Utilization (%)
     - Client Latency vs Server Memory Utilization (%) / JVM GC Pauses
     - Client Latency vs Database Connection Pool Saturation
     - Client Latency vs Network I/O & Disk Write IOPS
  2. Root Cause Attribution Engine:
     - Detects CPU saturation (CPU > 85% correlating with latency spikes)
     - Detects Memory leak / JVM Stop-the-world GC pauses (RAM > 90%)
     - Detects Database connection starvation (DB Pool = Max)
     - Detects Network / Gateway / Downstream third-party bottleneck
  3. CI/CD Artifacts:
     - Visual ANSI Correlation Matrix
     - GitHub / GitLab Markdown RCA report with actionable tuning recommendations
     - Structured JSON diagnostic export.

Usage:
  python tools/telemetry_correlator.py --jtl results.jtl --server-metrics server.csv
  python tools/telemetry_correlator.py --sample --markdown rca_report.md
  agent-qa correlate-telemetry --jtl results.jtl --server-metrics server.csv
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
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple

try:
    from tools.perf.jtl_analyzer import parse_jtl_timestamp
except ImportError:
    from perf.jtl_analyzer import parse_jtl_timestamp

# Enforce UTF-8 stdout encoding for Windows/macOS/Linux console compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def calculate_pearson_correlation(x: List[float], y: List[float]) -> float:
    """Calculates Pearson correlation coefficient between two numeric series."""
    n = min(len(x), len(y))
    if n < 2:
        return 0.0

    x = x[:n]
    y = y[:n]

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    denom_x = sum((x[i] - mean_x) ** 2 for i in range(n))
    denom_y = sum((y[i] - mean_y) ** 2 for i in range(n))

    if denom_x <= 0 or denom_y <= 0:
        return 0.0

    return numerator / math.sqrt(denom_x * denom_y)


def parse_jtl_time_series(jtl_path: str, bucket_sec: int = 5) -> Dict[int, List[float]]:
    """Buckets JMeter elapsed times by N-second time windows (supports CSV, TSV, and XML JTL)."""
    buckets: Dict[int, List[float]] = {}
    with open(jtl_path, "r", encoding="utf-8", errors="replace") as f:
        head = f.read(256).strip()

    if head.startswith("<?xml") or head.startswith("<testResults"):
        try:
            root = ET.parse(jtl_path).getroot()
            for elem in list(root):
                if elem.tag not in ("httpSample", "sample"):
                    continue
                try:
                    ts_ms = parse_jtl_timestamp(elem.attrib.get("ts", 0))
                    elapsed = float(elem.attrib.get("t", 0))
                    sec_bucket = (ts_ms // 1000 // bucket_sec) * bucket_sec
                    buckets.setdefault(sec_bucket, []).append(elapsed)
                except Exception:
                    continue
        except ET.ParseError:
            return buckets
        return buckets

    with open(jtl_path, "r", encoding="utf-8", errors="replace") as f:
        first_line = f.readline()
        if not first_line:
            return buckets
        delimiter = "\t" if "\t" in first_line else ","
        f.seek(0)
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            try:
                ts_ms = parse_jtl_timestamp(row.get("timeStamp") or row.get("Timestamp") or row.get("t") or 0)
                elapsed = float(row.get("elapsed") or row.get("Elapsed") or row.get("time") or 0)
                sec_bucket = (ts_ms // 1000 // bucket_sec) * bucket_sec
                buckets.setdefault(sec_bucket, []).append(elapsed)
            except Exception:
                continue
    return buckets


def parse_server_metrics(metrics_path: str, bucket_sec: int = 5) -> Dict[str, Dict[int, float]]:
    """
    Parses server telemetry CSV (timestamp/time, cpu_pct, memory_pct, db_pool_pct, disk_iops).
    """
    series: Dict[str, Dict[int, float]] = {
        "cpu_pct": {},
        "memory_pct": {},
        "db_pool_pct": {},
        "disk_iops": {}
    }

    with open(metrics_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Timestamp can be unix epoch in seconds or milliseconds
                raw_ts = float(row.get("timestamp") or row.get("time") or row.get("epoch") or 0)
                ts_sec = int(raw_ts if raw_ts < 1e11 else raw_ts / 1000)
                bucket = (ts_sec // bucket_sec) * bucket_sec

                if "cpu" in row or "cpu_pct" in row:
                    series["cpu_pct"][bucket] = float(row.get("cpu_pct") or row.get("cpu") or 0)
                if "memory" in row or "memory_pct" in row or "mem_pct" in row:
                    series["memory_pct"][bucket] = float(row.get("memory_pct") or row.get("memory") or 0)
                if "db_pool" in row or "db_pool_pct" in row or "db_connections" in row:
                    series["db_pool_pct"][bucket] = float(row.get("db_pool_pct") or row.get("db_pool") or 0)
                if "disk_iops" in row or "disk" in row or "iops" in row:
                    series["disk_iops"][bucket] = float(row.get("disk_iops") or row.get("disk") or 0)
            except Exception:
                continue

    return series


def fetch_prometheus_metrics(
    prometheus_url: str,
    start_epoch: int,
    end_epoch: int,
    bucket_sec: int = 5,
    queries: Optional[Dict[str, str]] = None,
    timeout_sec: float = 5.0,
) -> Dict[str, Dict[int, float]]:
    """Queries Prometheus HTTP /api/v1/query_range and buckets results for correlation."""
    series: Dict[str, Dict[int, float]] = {
        "cpu_pct": {},
        "memory_pct": {},
        "db_pool_pct": {},
        "disk_iops": {},
    }
    promql_map = queries or {
        "cpu_pct": '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)',
        "memory_pct": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
        "db_pool_pct": "100 * (hikaricp_connections_active / clamp_min(hikaricp_connections_max, 1))",
        "disk_iops": "sum(rate(node_disk_reads_completed_total[1m]) + rate(node_disk_writes_completed_total[1m]))",
    }
    base = prometheus_url.rstrip("/")
    for metric_key, expr in promql_map.items():
        if metric_key not in series:
            series[metric_key] = {}
        params = urllib.parse.urlencode({
            "query": expr,
            "start": int(start_epoch),
            "end": int(end_epoch),
            "step": f"{int(bucket_sec)}s",
        })
        url = f"{base}/api/v1/query_range?{params}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        for result_item in payload.get("data", {}).get("result", []):
            for ts_raw, val_raw in result_item.get("values", []):
                try:
                    bucket = (int(float(ts_raw)) // bucket_sec) * bucket_sec
                    series[metric_key][bucket] = float(val_raw)
                except (ValueError, TypeError):
                    continue
    return series


def build_otel_payload(
    analysis: Dict[str, Any],
    service_name: str = "synapse-backend-under-test",
) -> Dict[str, Any]:
    """Builds an OTLP-compliant ResourceMetrics JSON payload from correlation analysis."""
    summary = analysis.get("metrics_summary", {})
    return {
        "resourceMetrics": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": service_name}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": "synapse-correlator"}},
                    ]
                },
                "scopeMetrics": [
                    {
                        "scope": {"name": "synapse.telemetry.correlator", "version": "1.0.0"},
                        "metrics": [
                            {
                                "name": "http.server.request.duration",
                                "unit": "ms",
                                "gauge": {"dataPoints": [{"asDouble": float(summary.get("max_p95_ms", 0.0))}]},
                            },
                            {
                                "name": "system.cpu.utilization",
                                "unit": "1",
                                "gauge": {"dataPoints": [{"asDouble": round(float(summary.get("max_cpu_pct", 0.0)) / 100.0, 4)}]},
                            },
                            {
                                "name": "system.memory.utilization",
                                "unit": "1",
                                "gauge": {"dataPoints": [{"asDouble": round(float(summary.get("max_memory_pct", 0.0)) / 100.0, 4)}]},
                            },
                        ],
                    }
                ],
            }
        ]
    }


def push_otlp_metrics(
    endpoint: str,
    payload: Dict[str, Any],
    timeout_sec: float = 5.0,
) -> Tuple[bool, str]:
    """Pushes OTLP ResourceMetrics JSON to an OpenTelemetry HTTP collector endpoint."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            status = getattr(resp, "status", 200)
            return (200 <= int(status) < 300), f"HTTP {status}"
    except Exception as exc:
        return False, str(exc)


def _best_lag_correlation(
    sorted_buckets: List[int],
    p95_series: List[float],
    metric_map: Dict[int, float],
    bucket_sec: int,
    max_lag_buckets: int,
) -> Tuple[float, int]:
    """Computes highest positive Pearson correlation across +/- max_lag_buckets for clock-skew resilience."""
    best_r = calculate_pearson_correlation(
        p95_series, [metric_map.get(b, 0.0) for b in sorted_buckets]
    )
    best_lag = 0
    if max_lag_buckets <= 0:
        return best_r, best_lag

    for lag in range(-max_lag_buckets, max_lag_buckets + 1):
        if lag == 0:
            continue
        shifted = [metric_map.get(b + (lag * bucket_sec)) for b in sorted_buckets]
        paired_x = [p95_series[i] for i, val in enumerate(shifted) if val is not None]
        paired_y = [float(val) for val in shifted if val is not None]
        if len(paired_x) < 2:
            continue
        r = calculate_pearson_correlation(paired_x, paired_y)
        if r > best_r:
            best_r = r
            best_lag = lag
    return best_r, best_lag


def run_correlation_analysis(
    jtl_buckets: Dict[int, List[float]],
    server_series: Dict[str, Dict[int, float]],
    bucket_sec: int = 5,
    max_lag_buckets: int = 2,
) -> Dict[str, Any]:
    """Aligns time series and evaluates synchronous + lag-compensated Pearson correlation & Root Cause."""
    sorted_buckets = sorted(jtl_buckets.keys())
    if not sorted_buckets:
        return {"status": "NO_DATA", "correlations": {}, "lag_compensated_correlations": {}, "root_causes": []}

    # Calculate P95 per bucket
    p95_series: List[float] = []
    aligned_cpu: List[float] = []
    aligned_mem: List[float] = []
    aligned_db: List[float] = []
    aligned_disk: List[float] = []

    for b in sorted_buckets:
        values = sorted(jtl_buckets[b])
        p95 = values[int(len(values) * 0.95)] if values else 0.0
        p95_series.append(p95)

        aligned_cpu.append(server_series["cpu_pct"].get(b, 0.0))
        aligned_mem.append(server_series["memory_pct"].get(b, 0.0))
        aligned_db.append(server_series["db_pool_pct"].get(b, 0.0))
        aligned_disk.append(server_series["disk_iops"].get(b, 0.0))

    corr_cpu = calculate_pearson_correlation(p95_series, aligned_cpu)
    corr_mem = calculate_pearson_correlation(p95_series, aligned_mem)
    corr_db = calculate_pearson_correlation(p95_series, aligned_db)
    corr_disk = calculate_pearson_correlation(p95_series, aligned_disk)

    best_cpu_r, best_cpu_lag = _best_lag_correlation(sorted_buckets, p95_series, server_series["cpu_pct"], bucket_sec, max_lag_buckets)
    best_mem_r, best_mem_lag = _best_lag_correlation(sorted_buckets, p95_series, server_series["memory_pct"], bucket_sec, max_lag_buckets)
    best_db_r, best_db_lag = _best_lag_correlation(sorted_buckets, p95_series, server_series["db_pool_pct"], bucket_sec, max_lag_buckets)
    best_disk_r, best_disk_lag = _best_lag_correlation(sorted_buckets, p95_series, server_series["disk_iops"], bucket_sec, max_lag_buckets)

    max_cpu = max(server_series["cpu_pct"].values()) if server_series["cpu_pct"] else 0.0
    max_mem = max(server_series["memory_pct"].values()) if server_series["memory_pct"] else 0.0
    max_db = max(server_series["db_pool_pct"].values()) if server_series["db_pool_pct"] else 0.0
    max_p95 = max(p95_series) if p95_series else 0.0

    root_causes: List[Dict[str, str]] = []

    if best_cpu_r >= 0.65 and max_cpu > 80:
        lag_note = f" (lag-adjusted {best_cpu_lag * bucket_sec:+d}s)" if best_cpu_lag != 0 else ""
        root_causes.append({
            "component": "Server CPU Compute",
            "severity": "CRITICAL",
            "correlation": f"{best_cpu_r:.2f}",
            "description": f"Strong positive correlation ({best_cpu_r:.2f}{lag_note}) with peak CPU reaching {max_cpu:.1f}%. Compute capacity is saturated under peak load.",
            "recommendation": "Profile hot methods/threads with async-profiler. Consider CPU thread pool tuning or vertical/horizontal pod autoscaling (HPA)."
        })

    if best_db_r >= 0.65 and max_db > 85:
        lag_note = f" (lag-adjusted {best_db_lag * bucket_sec:+d}s)" if best_db_lag != 0 else ""
        root_causes.append({
            "component": "Database Connection Pool",
            "severity": "CRITICAL",
            "correlation": f"{best_db_r:.2f}",
            "description": f"Strong positive correlation ({best_db_r:.2f}{lag_note}) with DB Connection Pool reaching {max_db:.1f}% capacity. Threads are blocked waiting for pooled DB connections.",
            "recommendation": "Increase HikariCP / Tomcat maxPoolSize. Audit slow SQL queries holding connections open or enable connection leak detection."
        })

    if best_mem_r >= 0.60 and max_mem > 85:
        lag_note = f" (lag-adjusted {best_mem_lag * bucket_sec:+d}s)" if best_mem_lag != 0 else ""
        root_causes.append({
            "component": "Server Memory / JVM Heap",
            "severity": "HIGH",
            "correlation": f"{best_mem_r:.2f}",
            "description": f"Memory saturation reached {max_mem:.1f}% with correlation ({best_mem_r:.2f}{lag_note}). Probable GC pause (Stop-The-World) throttling throughput.",
            "recommendation": "Inspect GC logs (-Xlog:gc*). Tune JVM garbage collection flags (G1GC / ZGC) or adjust heap headroom (-Xmx)."
        })

    if not root_causes:
        if max_p95 > 1000 and max_cpu < 50 and max_db < 50:
            root_causes.append({
                "component": "Downstream Network / External Dependency",
                "severity": "MEDIUM",
                "correlation": "N/A",
                "description": f"Latency spiked to {max_p95:.1f}ms while Server CPU ({max_cpu:.1f}%) and DB Pool ({max_db:.1f}%) remained relaxed.",
                "recommendation": "Audit external 3rd-party HTTP gateways, microservice RPC timeouts, or lock contention in synchronized code blocks."
            })
        else:
            root_causes.append({
                "component": "System Health Normal",
                "severity": "INFO",
                "correlation": "N/A",
                "description": "Server hardware resources scale stably within acceptable performance boundaries.",
                "recommendation": "Maintain current infrastructure capacity parameters."
            })

    return {
        "status": "COMPLETED",
        "sample_points": len(sorted_buckets),
        "metrics_summary": {
            "max_p95_ms": round(max_p95, 2),
            "max_cpu_pct": round(max_cpu, 2),
            "max_memory_pct": round(max_mem, 2),
            "max_db_pool_pct": round(max_db, 2),
        },
        "correlations": {
            "cpu_correlation": round(corr_cpu, 3),
            "memory_correlation": round(corr_mem, 3),
            "db_pool_correlation": round(corr_db, 3),
            "disk_correlation": round(corr_disk, 3)
        },
        "lag_compensated_correlations": {
            "cpu_correlation": {"r": round(best_cpu_r, 3), "lag_sec": best_cpu_lag * bucket_sec},
            "memory_correlation": {"r": round(best_mem_r, 3), "lag_sec": best_mem_lag * bucket_sec},
            "db_pool_correlation": {"r": round(best_db_r, 3), "lag_sec": best_db_lag * bucket_sec},
            "disk_correlation": {"r": round(best_disk_r, 3), "lag_sec": best_disk_lag * bucket_sec},
        },
        "otel_metrics": {
            "http.server.request.duration.p95_ms": round(max_p95, 2),
            "system.cpu.utilization_ratio": round(max_cpu / 100.0, 4),
            "system.memory.utilization_ratio": round(max_mem / 100.0, 4),
            "system.db_pool.utilization_ratio": round(max_db / 100.0, 4),
        },
        "root_causes": root_causes
    }


def format_rca_markdown(analysis: Dict[str, Any]) -> str:
    """Generates GitHub / GitLab Markdown RCA report."""
    summary = analysis["metrics_summary"]
    corrs = analysis["correlations"]
    causes = analysis["root_causes"]

    lines = [
        "# 🔬 Full-Stack Performance Telemetry Correlation & RCA Report",
        "",
        "### 📊 Telemetry Metrics Summary",
        f"- **Max Client P95 Latency:** `{summary['max_p95_ms']} ms`",
        f"- **Peak Server CPU Utilization:** `{summary['max_cpu_pct']}%`",
        f"- **Peak Memory Consumption:** `{summary['max_memory_pct']}%`",
        f"- **Peak Database Pool Usage:** `{summary['max_db_pool_pct']}%`",
        "",
        "### 🔗 Pearson Correlation Matrix (Client Latency vs Server Telemetry)",
        "| Server Metric | Pearson Coefficient ($r$) | Impact Level | Interpretation |",
        "| :--- | :---: | :---: | :--- |",
        f"| **CPU Utilization** | `{corrs['cpu_correlation']}` | {'🔴 HIGH' if corrs['cpu_correlation'] > 0.6 else '🟢 LOW'} | Latency tracks CPU load directly |",
        f"| **Database Pool** | `{corrs['db_pool_correlation']}` | {'🔴 HIGH' if corrs['db_pool_correlation'] > 0.6 else '🟢 LOW'} | Connection pool saturation bottleneck |",
        f"| **Memory / JVM** | `{corrs['memory_correlation']}` | {'🟠 MEDIUM' if corrs['memory_correlation'] > 0.5 else '🟢 LOW'} | Possible GC pause or memory pressure |",
        f"| **Disk I/O** | `{corrs['disk_correlation']}` | {'🟠 MEDIUM' if corrs['disk_correlation'] > 0.5 else '🟢 LOW'} | Storage latency / write queueing |",
        "",
        "### 🎯 Root Cause Attribution & Engineering Action Items",
        ""
    ]

    for c in causes:
        badge = "🔴 CRITICAL" if c["severity"] == "CRITICAL" else ("🟠 HIGH" if c["severity"] == "HIGH" else "🔵 INFO")
        lines.extend([
            f"#### [{badge}] {c['component']}",
            f"- **Observation:** {c['description']}",
            f"- **Actionable Tuning:** {c['recommendation']}",
            ""
        ])

    lines.extend([
        "---",
        "*Report auto-generated by Synapse-Hub `telemetry_correlator.py` - Enterprise Observability Suite.*"
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Full-Stack APM & Server Telemetry Performance Correlator (Senior QC Performance Suite)."
    )
    parser.add_argument("--jtl", help="Path to JMeter results file (.jtl).")
    parser.add_argument("--server-metrics", "-s", help="Path to Server Telemetry CSV (timestamp, cpu_pct, memory_pct, db_pool_pct).")
    parser.add_argument("--prometheus-url", help="Live Prometheus base URL (e.g. http://localhost:9090) for query_range telemetry ingestion.")
    parser.add_argument("--markdown", "-m", help="Path to export Markdown RCA report.")
    parser.add_argument("--json", "-j", help="Path to export structured JSON diagnostics.")
    parser.add_argument("--otel", action="store_true", help="Export OpenTelemetry ResourceMetrics payload format to stdout.")
    parser.add_argument("--otlp-endpoint", help="OpenTelemetry OTLP/HTTP metrics endpoint (e.g. http://localhost:4318/v1/metrics).")
    parser.add_argument("--sample", action="store_true", help="Generate synthetic client & server telemetry dataset for verification.")

    args = parser.parse_args()

    if args.sample or not args.jtl or (not args.server_metrics and not args.prometheus_url):
        import tempfile
        import time
        temp_dir = tempfile.gettempdir()
        temp_jtl = os.path.join(temp_dir, "sample_corr_jmeter.jtl")
        temp_srv = os.path.join(temp_dir, "sample_corr_server.csv")

        base_ts = int(time.time() * 1000)
        # Create synthetic correlated dataset: CPU and Latency spike together in the middle
        with open(temp_jtl, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timeStamp", "elapsed", "label", "responseCode", "success"])
            for sec in range(60):
                # Spike between sec 20 and 40
                is_spike = 20 <= sec <= 40
                elapsed = 150 + (1200 if is_spike else 0) + (sec % 10)
                for _ in range(10):
                    w.writerow([base_ts + (sec * 1000), elapsed, "[POST] /api/v1/checkout", "200", "true"])

        with open(temp_srv, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "cpu_pct", "memory_pct", "db_pool_pct", "disk_iops"])
            for sec in range(60):
                is_spike = 20 <= sec <= 40
                cpu = 25.0 + (65.0 if is_spike else 5.0) + (sec % 3)
                mem = 60.0 + (sec * 0.2)
                db = 30.0 + (60.0 if is_spike else 0.0)
                w.writerow([int(base_ts / 1000) + sec, cpu, mem, db, 120])

        args.jtl = temp_jtl
        args.server_metrics = temp_srv
        print(f"🔬 [SAMPLE MODE] Generated synthetic correlated dataset in {temp_dir}")

    jtl_buckets = parse_jtl_time_series(args.jtl, bucket_sec=5)
    if args.prometheus_url and jtl_buckets:
        sorted_b = sorted(jtl_buckets.keys())
        server_series = fetch_prometheus_metrics(
            args.prometheus_url,
            start_epoch=sorted_b[0],
            end_epoch=sorted_b[-1] + 5,
            bucket_sec=5,
        )
    else:
        server_series = parse_server_metrics(args.server_metrics, bucket_sec=5)

    analysis = run_correlation_analysis(jtl_buckets, server_series)

    print("\n" + "=" * 80)
    print("  FULL-STACK APM & SERVER TELEMETRY CORRELATION ENGINE (RCA MATRIX)")
    print("=" * 80)
    print(f"Sample Windows Evaluated : {analysis['sample_points']} time slices (5s interval)")
    print(f"Peak Client P95 Latency : {analysis['metrics_summary']['max_p95_ms']} ms")
    print(f"Peak Server CPU          : {analysis['metrics_summary']['max_cpu_pct']}%")
    print(f"Peak Database Pool       : {analysis['metrics_summary']['max_db_pool_pct']}%")
    print("-" * 80)
    print("Pearson Correlation Coefficients (r):")
    for k, v in analysis["correlations"].items():
        print(f"  • {k.replace('_', ' ').title():<25} : {v:+0.3f}")
    print("-" * 80)
    print("🎯 Root Cause Analysis (RCA):")
    for c in analysis["root_causes"]:
        print(f"  [{c['severity']}] {c['component']}: {c['description']}")
        print(f"    👉 Recommendation: {c['recommendation']}")
    print("=" * 80 + "\n")

    if args.otel or args.otlp_endpoint:
        otel_metrics = build_otel_payload(analysis)
        if args.otlp_endpoint:
            ok, detail = push_otlp_metrics(args.otlp_endpoint, otel_metrics)
            print(f"{'✅' if ok else '❌'} [OTLP PUSH] {args.otlp_endpoint} -> {detail}")
        if args.otel:
            print(json.dumps(otel_metrics, indent=2))
            return

    if args.markdown:
        md = format_rca_markdown(analysis)
        os.makedirs(os.path.dirname(os.path.abspath(args.markdown)) or ".", exist_ok=True)
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"📄 Markdown RCA Report exported: {args.markdown}")

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)) or ".", exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2)
        print(f"📊 JSON Diagnostics exported: {args.json}")


if __name__ == "__main__":
    main()
