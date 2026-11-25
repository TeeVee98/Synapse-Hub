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
    SCRIPT_DIR,
    get_git_commit_sha,
    load_synapse_config,
    set_gate_metric,
)

logger = logging.getLogger("synapse.gates.perf")


def _is_synthetic_cpu_artifact(filepath: str) -> bool:
    """Detects synthetic local://benchmark CPU microbenchmark files masquerading as HTTP load artifacts."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
            head = fh.read(4096)
        return "local://benchmark" in head or "LOCAL_CPU_JSON_SERIALIZE" in head
    except OSError:
        return False


def _load_baseline_p95(perf_dirs: List[str]) -> float:
    """Loads optional baseline P95 latency (ms) from baseline_summary.json if present."""
    for pdir in perf_dirs:
        bpath = os.path.join(pdir, "baseline_summary.json")
        if os.path.isfile(bpath):
            try:
                with open(bpath, "r", encoding="utf-8") as bf:
                    bdata = json.load(bf)
                if isinstance(bdata, dict) and "p95_ms" in bdata:
                    return float(bdata["p95_ms"])
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
    return 0.0


def evaluate_baseline_regression(
    current_p95: float,
    baseline_p95: float,
    max_regression_pct: float,
) -> tuple[bool, float]:
    """Returns (within_budget, regression_delta_pct) comparing current_p95 against baseline_p95."""
    if baseline_p95 <= 0.0:
        return True, 0.0
    delta_pct = ((current_p95 - baseline_p95) / baseline_p95) * 100.0
    return delta_pct <= max_regression_pct, round(delta_pct, 2)


def gate_10_performance_sla(repo_root: str, mode: str = "AUTO") -> bool:
    """Gate 10: Performance & SLA Sentinel: Ingests perf test results (.jtl, k6_summary.json) and enforces SLA thresholds."""
    print("\n[GATE 10] Running Performance & SLA Sentinel...")
    raw_perf_dirs = [
        os.path.join(repo_root, "reports", "perf"),
        os.path.join(repo_root, "reports"),
        os.path.join(repo_root, "Reports", "perf"),
        os.path.join(repo_root, "Reports"),
        os.path.join(repo_root, ".synapse", "perf"),
    ]
    perf_dirs: List[str] = []
    for pdir in raw_perf_dirs:
        if os.path.exists(pdir) and not any(os.path.samefile(pdir, existing) for existing in perf_dirs):
            perf_dirs.append(pdir)

    raw_jtl: List[str] = []
    raw_k6: List[str] = []
    for pdir in perf_dirs:
        raw_jtl.extend(glob.glob(os.path.join(pdir, "*.jtl")))
        raw_jtl.extend(glob.glob(os.path.join(pdir, "*_results.csv")))
        raw_k6.extend(glob.glob(os.path.join(pdir, "*k6*.json")))
        raw_k6.extend(glob.glob(os.path.join(pdir, "summary.json")))

    raw_mode = (mode or "AUTO").upper()
    effective_mode = raw_mode
    if effective_mode == "AUTO":
        from tools.core.gates.base import detect_repo_mode
        effective_mode = detect_repo_mode(repo_root).upper()
    is_hub_mode = effective_mode == "HUB"

    synthetic_detected = [p for p in (raw_jtl + raw_k6) if _is_synthetic_cpu_artifact(p)]
    if synthetic_detected and raw_mode == "CLIENT":
        print(
            f"[FAIL] Gate 10 Performance Sentinel REJECTED: Synthetic CPU microbenchmark artifact "
            f"({os.path.basename(synthetic_detected[0])}) is prohibited in {effective_mode} mode."
        )
        return False

    # Exclude synthetic local://benchmark artifacts in HUB mode so Hub never claims fake 1ms HTTP SLA passes
    if is_hub_mode:
        jtl_candidates = [p for p in raw_jtl if not _is_synthetic_cpu_artifact(p)]
        k6_candidates = [p for p in raw_k6 if not _is_synthetic_cpu_artifact(p)]
    else:
        jtl_candidates = raw_jtl
        k6_candidates = raw_k6

    cfg = load_synapse_config(repo_root)
    perf_top_cfg = cfg.get("performance", {})
    perf_cfg = perf_top_cfg.get("sla", {})
    sla_p95 = perf_cfg.get("p95_ms", 500.0)
    sla_p99 = perf_cfg.get("p99_ms", 1000.0)
    max_error_rate = perf_cfg.get("max_error_rate_pct", 1.0)
    raw_reg_pct = perf_cfg.get("max_p95_regression_pct")
    if raw_reg_pct is None:
        raw_reg_pct = perf_top_cfg.get("max_p95_regression_pct", 15.0)
    max_p95_regression_pct = float(raw_reg_pct)
    baseline_p95 = _load_baseline_p95(perf_dirs)
    warmup_sec = float(perf_cfg.get("warmup_sec") or perf_top_cfg.get("warmup_sec") or 0.0)
    cooldown_sec = float(perf_cfg.get("cooldown_sec") or perf_top_cfg.get("cooldown_sec") or 0.0)
    tiered_sla = bool(perf_cfg.get("tiered_sla") or perf_top_cfg.get("tiered_sla") or False)
    tiered_rules = perf_cfg.get("tiered_rules") or perf_top_cfg.get("tiered_rules")

    fresh_benchmark_run = False

    # Check for companion metadata file or k6 metadata
    meta: Dict[str, Any] = {}
    meta_candidates = [
        os.path.join(repo_root, "reports", "perf", "perf_metadata.json"),
        os.path.join(repo_root, "reports", "perf_metadata.json"),
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

    effective_mode = (mode or "AUTO").upper()
    if effective_mode == "AUTO":
        from tools.core.gates.base import detect_repo_mode
        effective_mode = detect_repo_mode(repo_root).upper()
    is_hub_mode = effective_mode == "HUB"

    explicit_require_fresh_false = (
        perf_top_cfg.get("require_fresh") is False
        or perf_cfg.get("require_fresh") is False
    )
    if is_stale or require_fresh or (not jtl_candidates and not k6_candidates):
        if is_hub_mode:
            auto_bench = bool(cfg.get("performance", {}).get("auto_benchmark_fallback", False))
        else:
            auto_bench = bool(cfg.get("performance", {}).get("client_auto_benchmark_fallback", False))

        if auto_bench and not (require_fresh and not cfg.get("performance", {}).get("allow_auto_bench_on_require_fresh", True)):
            trigger_reason = f"Stale artifact detected ({staleness_reason})" if is_stale else ("Fresh benchmark required" if require_fresh else "No existing perf run found")
            print(f"[GATE 10] [HUB CLI MICROBENCHMARK] {trigger_reason}. Triggering local CPU microbenchmark runner...")
            try:
                try:
                    from tools.perf.benchmark_perf_runner import run_benchmark
                except ImportError:
                    sys.path.insert(0, os.path.join(repo_root, "tools"))
                    from perf.benchmark_perf_runner import run_benchmark
                out_dir = os.path.join(repo_root, "reports", "perf")
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
        elif not jtl_candidates and not k6_candidates and is_hub_mode and not require_fresh:
            skip_metrics = {
                "status": "SKIPPED_NO_LOAD_ARTIFACT",
                "execution_mode": "SKIPPED_NO_LOAD_ARTIFACT",
                "evaluation_type": "NO_LOAD_ARTIFACT",
                "is_fresh_measurement": False,
                "is_stale": False,
                "staleness_reason": None,
                "generated_at": None,
                "commit": get_git_commit_sha(repo_root),
                "command": "N/A",
                "fixture_environment": {},
                "passed": True,
                "sla_p95_ms": sla_p95,
                "max_error_rate_pct": max_error_rate,
                "max_p95_regression_pct": max_p95_regression_pct,
                "warmup_sec": warmup_sec,
                "cooldown_sec": cooldown_sec,
                "tiered_sla": tiered_sla,
                "evaluated_artifacts": [],
            }
            set_gate_metric("gate_10", skip_metrics)
            print("[SKIPPED] Hub Mode: No real HTTP load test artifact in reports/perf/ (synthetic CPU masquerade disabled).")
            return True
        elif is_stale and not explicit_require_fresh_false and not is_hub_mode:
            print(f"[FAIL] Gate 10 Performance Sentinel REJECTED: {staleness_reason} (Client/Target mode requires fresh load test artifacts; synthetic CPU fallback disabled).")
            return False
        elif require_fresh:
            print(f"[FAIL] Gate 10 Performance Sentinel REJECTED: {staleness_reason or 'Fresh benchmark required but not generated.'} (Stale artifact not accepted as new measurement)")
            return False
        elif not jtl_candidates and not k6_candidates:
            print(f"[FAIL] Gate 10 Performance Sentinel REJECTED: No active perf runs found in reports/perf/ for mode={effective_mode} (Fail-closed).")
            return False

    parse_jtl = evaluate_sla = evaluate_tiered_sampler_sla = None
    if jtl_candidates:
        try:
            try:
                from tools.perf.jtl_analyzer import parse_jtl, evaluate_sla, evaluate_tiered_sampler_sla
            except ImportError:
                if SCRIPT_DIR not in sys.path:
                    sys.path.insert(0, SCRIPT_DIR)
                from jtl_analyzer import parse_jtl, evaluate_sla, evaluate_tiered_sampler_sla
        except Exception as e:
            print(f"[FAIL] Gate 10 Performance Sentinel REJECTED: jtl_analyzer unavailable ({e}) (Fail-closed).")
            return False

    all_passed = True
    observed_max_reg_delta = 0.0

    # 1. Evaluate Apache JMeter JTL / CSV results
    for jtl_path in jtl_candidates:
        rel_path = os.path.relpath(jtl_path, repo_root)
        try:
            per_sampler, agg_raw = parse_jtl(
                jtl_path, warmup_sec=warmup_sec, cooldown_sec=cooldown_sec
            )
            if not per_sampler:
                all_passed = False
                print(f"[FAIL] Empty or unparseable JTL artifact: {rel_path}")
                continue
            agg_stats = agg_raw.compute()
            passed, violations = evaluate_sla(
                agg_stats,
                sla_p95=sla_p95,
                sla_p99=sla_p99,
                max_error_rate=max_error_rate
            )
            reg_ok, reg_delta = evaluate_baseline_regression(
                float(agg_stats.get("p95_ms", 0.0)),
                baseline_p95,
                max_p95_regression_pct,
            )
            observed_max_reg_delta = max(observed_max_reg_delta, reg_delta)
            if not reg_ok:
                passed = False
                violations.append(
                    f"P95 Regression Delta Breached: +{reg_delta:.1f}% > +{max_p95_regression_pct:.1f}% vs baseline ({agg_stats.get('p95_ms', 0.0)}ms vs {baseline_p95}ms)"
                )
            if tiered_sla:
                tiered_ok, tiered_viols = evaluate_tiered_sampler_sla(
                    [s.compute() for s in per_sampler.values()],
                    tiered_rules=tiered_rules,
                    max_error_rate=float(max_error_rate),
                )
                if not tiered_ok:
                    passed = False
                    violations.extend(tiered_viols)
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
            all_passed = False
            print(f"[FAIL] Failed to parse JTL {rel_path}: {e}")

    # 2. Evaluate k6 summary export JSON
    for k6_path in k6_candidates:
        rel_path = os.path.relpath(k6_path, repo_root)
        try:
            with open(k6_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            metrics = data.get("metrics", {})
            dur = metrics.get("http_req_duration", {}).get("values", {})
            p95 = float(dur.get("p(95)", 0.0))
            err_rate = float(metrics.get("http_req_failed", {}).get("values", {}).get("rate", 0.0)) * 100.0

            violations = []
            if p95 > sla_p95:
                violations.append(f"P95 Latency SLA Breached: {p95:.1f}ms > {sla_p95}ms")
            if err_rate > max_error_rate:
                violations.append(f"Error Rate SLA Breached: {err_rate:.2f}% > {max_error_rate}%")
            reg_ok, reg_delta = evaluate_baseline_regression(p95, baseline_p95, max_p95_regression_pct)
            observed_max_reg_delta = max(observed_max_reg_delta, reg_delta)
            if not reg_ok:
                violations.append(
                    f"P95 Regression Delta Breached: +{reg_delta:.1f}% > +{max_p95_regression_pct:.1f}% vs baseline ({p95:.1f}ms vs {baseline_p95:.1f}ms)"
                )

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
            all_passed = False
            print(f"[FAIL] Failed to parse k6 summary {rel_path}: {e}")

    sample_path = (k6_candidates or jtl_candidates)[0] if (k6_candidates or jtl_candidates) else None
    mtime_epoch = os.path.getmtime(sample_path) if sample_path and os.path.exists(sample_path) else None
    default_gen_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime_epoch)) if mtime_epoch else None

    final_metrics = {
        "status": "PASS" if all_passed else "FAIL",
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
        "max_p95_regression_pct": max_p95_regression_pct,
        "regression_delta_pct": observed_max_reg_delta,
        "warmup_sec": warmup_sec,
        "cooldown_sec": cooldown_sec,
        "tiered_sla": tiered_sla,
        "evaluated_artifacts": [os.path.relpath(p, repo_root) for p in jtl_candidates + k6_candidates],
    }
    set_gate_metric("gate_10", final_metrics)

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
