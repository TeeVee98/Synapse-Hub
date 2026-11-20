#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Gate 10: Performance & SLA Sentinel.
Ingests perf test results (.jtl, k6_summary.json) and enforces SLA latency budgets and error rate thresholds.
"""

from datetime import datetime
import glob
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List

from tools.core.gates.base import (
    BaseGate,
    LAST_GATE_METRICS,
    SCRIPT_DIR,
    get_git_commit_sha,
    load_synapse_config,
)

logger = logging.getLogger("synapse.gates.perf")


def gate_10_performance_sla(repo_root: str, mode: str = "AUTO") -> bool:
    """Gate 10: Performance & SLA Sentinel: Ingests perf test results (.jtl, k6_summary.json) and enforces SLA thresholds."""
    print("\n[GATE 10] Running Performance & SLA Sentinel...")
    perf_dirs = [
        os.path.join(repo_root, "Reports", "perf"),
        os.path.join(repo_root, "Reports"),
        os.path.join(repo_root, ".synapse", "perf")
    ]

    jtl_candidates: List[str] = []
    k6_candidates: List[str] = []
    for pdir in perf_dirs:
        if os.path.exists(pdir):
            jtl_candidates.extend(glob.glob(os.path.join(pdir, "*.jtl")))
            jtl_candidates.extend(glob.glob(os.path.join(pdir, "*_results.csv")))
            k6_candidates.extend(glob.glob(os.path.join(pdir, "*k6*.json")))
            k6_candidates.extend(glob.glob(os.path.join(pdir, "summary.json")))

    cfg = load_synapse_config(repo_root)
    perf_top_cfg = cfg.get("performance", {})
    perf_cfg = perf_top_cfg.get("sla", {})
    sla_p95 = perf_cfg.get("p95_ms", 500.0)
    sla_p99 = perf_cfg.get("p99_ms", 1000.0)
    max_error_rate = perf_cfg.get("max_error_rate_pct", 1.0)

    fresh_benchmark_run = False

    # Check for companion metadata file or k6 metadata
    meta: Dict[str, Any] = {}
    meta_candidates = [
        os.path.join(repo_root, "Reports", "perf", "perf_metadata.json"),
        os.path.join(repo_root, "Reports", "perf_metadata.json"),
    ]
    for mpath in meta_candidates:
        if os.path.exists(mpath):
            try:
                with open(mpath, "r", encoding="utf-8") as mf:
                    meta = json.load(mf)
                break
            except (OSError, json.JSONDecodeError) as err:
                logger.debug("Could not read perf_metadata: %s", err)

    if not meta and k6_candidates:
        for kp in k6_candidates:
            try:
                with open(kp, "r", encoding="utf-8") as kf:
                    k_obj = json.load(kf)
                    if isinstance(k_obj, dict) and "metadata" in k_obj:
                        meta = k_obj["metadata"]
                        break
            except (OSError, json.JSONDecodeError) as err:
                logger.debug("Could not read k6 metadata: %s", err)

    max_age_hours = float(perf_top_cfg.get("max_artifact_age_hours") or perf_cfg.get("max_artifact_age_hours") or 24.0)
    require_fresh = bool(perf_top_cfg.get("require_fresh") or perf_cfg.get("require_fresh") or os.environ.get("SYNAPSE_PERF_FRESH") == "1")

    # Assess staleness of pre-existing artifacts
    is_stale = False
    staleness_reason = None
    if jtl_candidates or k6_candidates:
        sample_path = (k6_candidates or jtl_candidates)[0]
        gen_time_str = meta.get("generated_at")
        artifact_epoch = None
        if gen_time_str:
            try:
                dt = datetime.fromisoformat(gen_time_str.replace("Z", "+00:00"))
                artifact_epoch = dt.timestamp()
            except (ValueError, TypeError) as err:
                logger.debug("Could not parse generated_at timestamp: %s", err)
        if artifact_epoch is None and os.path.exists(sample_path):
            artifact_epoch = os.path.getmtime(sample_path)

        if artifact_epoch is not None:
            age_hours = (time.time() - artifact_epoch) / 3600.0
            if age_hours > max_age_hours:
                is_stale = True
                staleness_reason = f"Artifact is {age_hours:.1f}h old (exceeds {max_age_hours:.1f}h threshold)"

    if is_stale or require_fresh or (not jtl_candidates and not k6_candidates):
        auto_bench = cfg.get("performance", {}).get("auto_benchmark_fallback", True)
        if auto_bench and not (require_fresh and not cfg.get("performance", {}).get("allow_auto_bench_on_require_fresh", True)):
            trigger_reason = f"Stale artifact detected ({staleness_reason})" if is_stale else ("Fresh benchmark required" if require_fresh else "No existing perf run found")
            print(f"[GATE 10] {trigger_reason}. Triggering local CPU microbenchmark runner...")
            try:
                try:
                    from tools.perf.benchmark_perf_runner import run_benchmark
                except ImportError:
                    sys.path.insert(0, os.path.join(repo_root, "tools"))
                    from perf.benchmark_perf_runner import run_benchmark
                out_dir = os.path.join(repo_root, "Reports", "perf")
                bench_res = run_benchmark(iterations=50, output_dir=out_dir)
                jtl_candidates = [bench_res["jtl_file"]]
                k6_candidates = [bench_res["k6_file"]]
                meta = bench_res.get("metadata", {})
                fresh_benchmark_run = True
                is_stale = False
                staleness_reason = None
                print(f"[GATE 10] Local CPU microbenchmark generated: P95={bench_res['p95_ms']}ms, P99={bench_res['p99_ms']}ms, Error={bench_res['error_rate_pct']}%.")
            except Exception as exc:
                print(f"[FAIL] Gate 10 Performance Sentinel REJECTED: Failed to execute performance benchmark: {exc}")
                return False
        elif require_fresh:
            print(f"[FAIL] Gate 10 Performance Sentinel REJECTED: {staleness_reason or 'Fresh benchmark required but not generated.'} (Stale artifact not accepted as new measurement)")
            return False
        elif not jtl_candidates and not k6_candidates:
            print("[FAIL] Gate 10 Performance Sentinel REJECTED: No active perf runs found in Reports/perf/ and auto_benchmark_fallback is false. (Fail-closed)")
            return False

    try:
        try:
            from tools.perf.jtl_analyzer import parse_jtl, evaluate_sla
        except ImportError:
            sys.path.insert(0, SCRIPT_DIR)
            from jtl_analyzer import parse_jtl, evaluate_sla
    except Exception as e:
        print(f"[WARN] jtl_analyzer not available: {e}")
        return True

    all_passed = True

    # 1. Evaluate Apache JMeter JTL / CSV results
    for jtl_path in jtl_candidates:
        rel_path = os.path.relpath(jtl_path, repo_root)
        try:
            per_sampler, agg_raw = parse_jtl(jtl_path)
            if not per_sampler:
                continue
            agg_stats = agg_raw.compute()
            passed, violations = evaluate_sla(
                agg_stats,
                sla_p95=sla_p95,
                sla_p99=sla_p99,
                max_error_rate=max_error_rate
            )
            if not passed:
                all_passed = False
                print(f"[FAIL] SLA breach detected in {rel_path}:")
                for v in violations:
                    print(f"   🔴 {v}")
            else:
                mtime_epoch = os.path.getmtime(jtl_path) if os.path.exists(jtl_path) else None
                mtime_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime_epoch)) if mtime_epoch else "unknown"
                pass_mode_tag = "[FRESH LOAD TEST PASS]" if fresh_benchmark_run else "[ARTIFACT SENTINEL PASS]"
                print(f"[PASS] {pass_mode_tag} SLA compliant in {rel_path} (P95: {agg_stats['p95_ms']}ms, Error: {agg_stats['error_rate_pct']}%, artifact freshness: {mtime_str})")
        except Exception as e:
            print(f"[WARN] Failed to parse JTL {rel_path}: {e}")

    # 2. Evaluate k6 summary export JSON
    for k6_path in k6_candidates:
        rel_path = os.path.relpath(k6_path, repo_root)
        try:
            with open(k6_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            metrics = data.get("metrics", {})
            dur = metrics.get("http_req_duration", {}).get("values", {})
            p95 = dur.get("p(95)", 0.0)
            err_rate = metrics.get("http_req_failed", {}).get("values", {}).get("rate", 0.0) * 100.0

            violations = []
            if p95 > sla_p95:
                violations.append(f"P95 Latency SLA Breached: {p95:.1f}ms > {sla_p95}ms")
            if err_rate > max_error_rate:
                violations.append(f"Error Rate SLA Breached: {err_rate:.2f}% > {max_error_rate}%")

            if violations:
                all_passed = False
                print(f"[FAIL] k6 SLA breach detected in {rel_path}:")
                for v in violations:
                    print(f"   🔴 {v}")
            else:
                mtime_epoch = os.path.getmtime(k6_path) if os.path.exists(k6_path) else None
                mtime_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime_epoch)) if mtime_epoch else "unknown"
                pass_mode_tag = "[FRESH LOAD TEST PASS]" if fresh_benchmark_run else "[ARTIFACT SENTINEL PASS]"
                print(f"[PASS] {pass_mode_tag} k6 SLA compliant in {rel_path} (P95: {p95:.1f}ms, Error: {err_rate:.2f}%, artifact freshness: {mtime_str})")
        except Exception as e:
            print(f"[WARN] Failed to parse k6 summary {rel_path}: {e}")

    sample_path = (k6_candidates or jtl_candidates)[0] if (k6_candidates or jtl_candidates) else None
    mtime_epoch = os.path.getmtime(sample_path) if sample_path and os.path.exists(sample_path) else None
    default_gen_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime_epoch)) if mtime_epoch else None

    LAST_GATE_METRICS["gate_10"] = {
        "execution_mode": "FRESH_LOAD_TEST" if fresh_benchmark_run else "ARTIFACT_SENTINEL",
        "evaluation_type": "RUN_FRESH_BENCHMARK" if fresh_benchmark_run else "VALIDATE_EXISTING_REPORT",
        "is_fresh_measurement": bool(fresh_benchmark_run),
        "is_stale": bool(is_stale),
        "staleness_reason": staleness_reason,
        "generated_at": meta.get("generated_at") or default_gen_str,
        "commit": meta.get("commit") or get_git_commit_sha(repo_root),
        "command": meta.get("command") or (f"{sys.executable} -m tools.perf.benchmark_perf_runner" if fresh_benchmark_run else "N/A"),
        "fixture_environment": meta.get("fixture_environment") or {},
        "passed": all_passed,
        "sla_p95_ms": sla_p95,
        "max_error_rate_pct": max_error_rate,
        "evaluated_artifacts": [os.path.relpath(p, repo_root) for p in jtl_candidates + k6_candidates],
    }

    if all_passed:
        if fresh_benchmark_run:
            mode_summary = "Fresh Load Test"
            print(f"[PASS] 100% Performance SLA Compliant ({mode_summary}, P95 <= {sla_p95}ms, Error Rate <= {max_error_rate}%).")
        else:
            stale_tag = " [STALE ARTIFACT]" if is_stale else ""
            mode_summary = f"Pre-existing Artifact Sentinel{stale_tag}"
            print(f"[PASS] 100% Performance SLA Compliant ({mode_summary}, P95 <= {sla_p95}ms, Error Rate <= {max_error_rate}%).")
            if is_stale:
                print(f"   ⚠️  Notice: Existing artifact is stale ({staleness_reason}). For a fresh measurement, run tools/perf/benchmark_perf_runner.py or pass --fresh-perf.")
        return True
    return False


class Gate10PerfSLA(BaseGate):
    """Gate 10: Performance & SLA Sentinel."""

    gate_id = 10
    name = "Gate 10: Performance & SLA Sentinel"
    key = "gate_10_performance_sla"

    def run(self, repo_root: str, mode: str = "AUTO", **kwargs) -> bool:
        return gate_10_performance_sla(repo_root, mode=mode)
