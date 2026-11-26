#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Enterprise Multi-Project DoD Verifier (One Command Quality Gate Orchestrator)."""

import argparse
import concurrent.futures
from dataclasses import dataclass
from datetime import datetime
import html as html_lib
import io
import json
import logging
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.core.gates.base import ThreadLocalStdoutProxy, set_thread_stdout

from tools.core.gates import (
    ALL_GATES, BOM_EXTENSIONS, FORBIDDEN_PATH_PATTERNS, LAST_GATE_METRICS,
    MOJIBAKE_INDICATORS, PARALLEL_STATIC_GATE_KEYS, REPO_ROOT, SCRIPT_DIR,
    BaseGate, Gate01UTF8, Gate02Portability, Gate03CleanPOM, Gate04AIDocs,
    Gate05Blacklist, Gate06Credentials, Gate07InferLinter, Gate08Mutation,
    Gate09Collisions, Gate10PerfSLA, GateResult, check_python_ast_integrity,
    detect_repo_mode, gate_0_author_integrity, gate_1_bom_check,
    gate_2_path_portability, gate_3_clean_pom, gate_4_ai_docs_lint,
    gate_5_cleanup_blacklist, gate_6_credential_security, gate_7_infer_linter,
    gate_8_micro_mutator, gate_9_skill_collision, gate_10_performance_sla,
    gate_11_token_reduction,
    get_git_commit_sha, get_scoped_git_files, has_python_sources,
    is_page_class_path, load_synapse_config, parse_pytest_metrics,
    parse_pytest_output, print_header, resolve_target_repo, resolve_tool_path,
    safe_print, verify_engine_preflight,
)

logger = logging.getLogger("synapse.verify_all")

__all__ = (
    "ALL_GATES", "BOM_EXTENSIONS", "FORBIDDEN_PATH_PATTERNS", "LAST_GATE_METRICS",
    "MOJIBAKE_INDICATORS", "PARALLEL_STATIC_GATE_KEYS", "REPO_ROOT", "SCRIPT_DIR",
    "BaseGate", "Gate01UTF8", "Gate02Portability", "Gate03CleanPOM", "Gate04AIDocs",
    "Gate05Blacklist", "Gate06Credentials", "Gate07InferLinter", "Gate08Mutation",
    "Gate09Collisions", "Gate10PerfSLA", "GateResult", "check_python_ast_integrity",
    "detect_repo_mode", "gate_0_author_integrity", "gate_1_bom_check",
    "gate_2_path_portability", "gate_3_clean_pom", "gate_4_ai_docs_lint",
    "gate_5_cleanup_blacklist", "gate_6_credential_security", "gate_7_infer_linter",
    "gate_8_micro_mutator", "gate_9_skill_collision", "gate_10_performance_sla",
    "get_git_commit_sha", "get_scoped_git_files", "has_python_sources",
    "is_page_class_path", "load_synapse_config", "parse_pytest_metrics",
    "parse_pytest_output", "print_header", "resolve_target_repo", "resolve_tool_path",
    "safe_print", "verify_engine_preflight", "format_gates_junit", "run_all_gates", "run_all_gates_detailed", "main",
    "ThreadSafeGateExecutionDTO", "execute_gate_isolated",
)


@dataclass(frozen=True)
class ThreadSafeGateExecutionDTO:
    """Isolated execution outcome for a single quality gate running inside a worker thread."""
    gate_key: str
    passed: bool
    captured_log: str
    duration_sec: float


def execute_gate_isolated(
    gate_key: str,
    gate_fn: Any,
    repo_root: str,
    mode: str,
    buffer: io.StringIO,
    gate_name: str = "",
) -> ThreadSafeGateExecutionDTO:
    """Executes a static DoD gate writing exclusively to a thread-local StringIO without mutating sys.stdout."""
    t0 = time.perf_counter()
    set_thread_stdout(buffer)
    try:
        passed = bool(gate_fn(repo_root, mode=mode))
    except Exception as exc:
        label = gate_name or gate_key
        buffer.write(f"\n[ERROR in {label}]: {exc}\n")
        passed = False
    finally:
        set_thread_stdout(None)
    return ThreadSafeGateExecutionDTO(
        gate_key=gate_key,
        passed=passed,
        captured_log=buffer.getvalue(),
        duration_sec=round(time.perf_counter() - t0, 4),
    )


def format_gates_junit(gate_results: List[Tuple[str, bool, str]], repo_root: str, gate_metrics: Optional[Dict[str, Any]] = None) -> str:
    """Formats 11 DoD Quality Gates result into JUnit XML testsuite."""
    metrics_map = gate_metrics if gate_metrics is not None else LAST_GATE_METRICS
    total, failures = len(gate_results), len([g for g in gate_results if not g[1]])
    lines = ['<?xml version="1.0" encoding="utf-8"?>', f'<testsuite name="synapse-quality-gates" tests="{total}" failures="{failures}" errors="0">']
    for name, success, reason in gate_results:
        cname, tname = "synapse.quality_gates", html_lib.escape(name.split(":")[0].strip().replace(" ", "_"), quote=True)
        g7 = metrics_map.get("gate_7", {}) if ("gate_7" in name.lower() or "static defect" in name.lower()) else None
        g8 = metrics_map.get("gate_8", {}) if ("gate_8" in name.lower() or "mutation" in name.lower() or "assertion" in name.lower()) else None
        g10 = metrics_map.get("gate_10", {}) if ("gate_10" in name.lower() or "performance" in name.lower() or "sla" in name.lower()) else None
        time_attr = f' time="{g7["duration_seconds"]:.2f}"' if (g7 and g7.get("duration_seconds")) else ""
        lines.append(f'  <testcase classname="{cname}" name="{tname}"{time_attr}>')
        if g7:
            lines.append("    <properties>")
            for k in ("status", "execution_mode", "collected", "passed", "skipped", "failed", "xfailed", "commit", "uncollected", "parent_test", "note"):
                if k in g7 and g7[k] is not None:
                    lines.append(f'      <property name="{k}" value="{html_lib.escape(str(g7[k]), quote=True)}"/>')
            lines.append("    </properties>")
            sha = html_lib.escape(str(g7.get("commit", "unknown")), quote=True)
            if g7.get("uncollected") or g7.get("status") == "PARENT_RUNNER_ACTIVE":
                lines.append(f'    <system-out>Hub regression test suite {"passed" if success else "failed"}: {html_lib.escape(str(g7.get("note", "")))} (Git commit: {sha}).</system-out>')
            else:
                summary = [f"{g7.get('passed', 0)} passed"] + [f"{g7[ek]} {ek}" for ek in ("skipped", "failed", "xfailed", "errors") if g7.get(ek, 0) > 0]
                lines.append(f'    <system-out>Hub regression test suite {"passed" if success else "failed"}: {html_lib.escape(", ".join(summary))} in {g7.get("duration_seconds", 0.0):.2f}s (Git commit: {sha}).</system-out>')
        elif g8:
            lines.append("    <properties>")
            for k in ("mode", "measurement_kind", "static_assertion_sensitivity_score", "dynamic_mutation_score", "mutation_score", "killed", "survived", "timed_out", "invalid_syntax", "total_mutants", "valid_mutants"):
                if k in g8 and g8[k] is not None:
                    lines.append(f'      <property name="{k}" value="{html_lib.escape(str(g8[k]), quote=True)}"/>')
            lines.append("    </properties>")
        elif g10:
            lines.append("    <properties>")
            for k in ("execution_mode", "evaluation_type", "is_fresh_measurement", "is_stale", "staleness_reason", "generated_at", "commit", "sla_p95_ms", "max_error_rate_pct"):
                if k in g10 and g10[k] is not None:
                    lines.append(f'      <property name="{k}" value="{html_lib.escape(str(g10[k]), quote=True)}"/>')
            lines.append("    </properties>")
        if not success:
            lines.append(f'    <failure message="Quality Gate Failed: {html_lib.escape(str(name), quote=True)}">{html_lib.escape(str(name))} failed in repository {html_lib.escape(str(repo_root))} ({html_lib.escape(str(reason))})</failure>')
        lines.append("  </testcase>")
    lines.append("</testsuite>")
    return "\n".join(lines)


def run_all_gates_detailed(repo_root: str, mode: str = "AUTO", test_cmd: str = "", scoped_test_cmd: str = "", changed_only: bool = False, output_format: str = "text", config_path: Optional[str] = None, fast: bool = False, parallel: bool = False, live_sample: bool = False, tier: Optional[str] = None, report_path: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Programmatic entrypoint returning (exit_code, result_dict) in memory for all 11 DoD Quality Gates."""
    effective_mode = detect_repo_mode(repo_root) if mode.upper() == "AUTO" else mode.upper()
    if tier:
        tier_lower = tier.lower()
        if tier_lower == "fast":
            fast = True
        elif tier_lower == "impact":
            os.environ["SYNAPSE_VERIFY_TIER"] = "impact"
        elif tier_lower == "full":
            fast = False
            os.environ["SYNAPSE_VERIFY_TIER"] = "full"

    effective_changed = changed_only or fast
    cfg = load_synapse_config(repo_root, config_path=config_path)
    gate_toggles = cfg.get("quality_gates", {}).get("gates", {})

    if output_format == "text":
        tier_label = f" TIER:{tier.upper()}" if tier else ""
        suffix = f" [{effective_mode}{tier_label} FAST MODE]" if fast else f" [{effective_mode}{tier_label} MODE]"
        print_header(f"ENTERPRISE AUTOMATION - ONE-COMMAND DoD VERIFICATION{suffix}")
        print(f"Target Repository: {repo_root}\nOperational Mode : {effective_mode}")
        if fast:
            print("Execution Speed  : FAST (Sub-3s targeted feedback loop)")
        elif tier and tier.lower() == "impact":
            print("Execution Tier   : IMPACT (Test impact-scoped feedback loop)")
        if parallel:
            print("Concurrency Mode : PARALLEL (ThreadPoolExecutor for independent static gates)")

    if not verify_engine_preflight(repo_root, mode=effective_mode, silent=True):
        if output_format == "text":
            print("\n[DoD BLOCKED] Pre-flight Engine Integrity Guard failed: Author Attribution / MIT License Violated.")
            print("   Under MIT License, original author copyright notice to 'Thế Vị (@TeeVee98)' must be preserved.")
        return 1, {
            "timestamp": datetime.now().isoformat(),
            "target": repo_root,
            "mode": effective_mode,
            "all_passed": False,
            "return_code": 1,
            "summary": {"total": 11, "passed": 0, "skipped": 0, "failed": 1},
            "gates": [],
            "error": "Pre-flight Engine Integrity Guard failed",
        }

    if effective_mode == "HUB":
        invariant_script = resolve_tool_path(repo_root, "invariant_checker.py", "lint")
        if os.path.exists(invariant_script):
            try:
                inv_res = subprocess.run(
                    [sys.executable, invariant_script, "--json"],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    timeout=15.0,
                )
                if inv_res.returncode != 0:
                    if output_format == "text":
                        print("\n[DoD BLOCKED] Pre-flight Invariant Sentinel failed: Architectural Invariants Violated.")
                        safe_print(inv_res.stdout)
                    return 1, {
                        "timestamp": datetime.now().isoformat(),
                        "target": repo_root,
                        "mode": effective_mode,
                        "all_passed": False,
                        "return_code": 1,
                        "summary": {"total": 11, "passed": 0, "skipped": 0, "failed": 1},
                        "gates": [],
                        "error": "Pre-flight Invariant Sentinel failed",
                    }
            except Exception as inv_err:
                if output_format == "text":
                    safe_print(f"[DoD BLOCKED] Invariant checker preflight failed: {inv_err}")
                return 1, {
                    "timestamp": datetime.now().isoformat(),
                    "target": repo_root,
                    "mode": effective_mode,
                    "all_passed": False,
                    "return_code": 1,
                    "summary": {"total": 11, "passed": 0, "skipped": 0, "failed": 1},
                    "gates": [],
                    "error": f"Invariant checker preflight failed: {inv_err}",
                }

    gates = [
        ("gate_1_bom_check", "Gate 1: UTF-8 No BOM", lambda r, mode: gate_1_bom_check(r, mode=mode, fast=fast)),
        ("gate_2_path_portability", "Gate 2: Path Portability", lambda r, mode: gate_2_path_portability(r, mode=mode, fast=fast)),
        ("gate_3_clean_pom", "Gate 3: Clean POM & Flat Architecture", gate_3_clean_pom),
        ("gate_4_ai_docs_lint", "Gate 4: AI Documentation Linter", gate_4_ai_docs_lint),
        ("gate_5_cleanup_blacklist", "Gate 5: Temporary Files Blacklist", gate_5_cleanup_blacklist),
        ("gate_6_credential_security", "Gate 6: Credential Security", lambda r, mode: gate_6_credential_security(r, mode=mode, fast=fast)),
        ("gate_7_infer_linter", "Gate 7: Static Defect Sentinel", lambda r, mode: gate_7_infer_linter(r, mode=mode, fast=fast)),
        ("gate_8_micro_mutator", "Gate 8: Assertion Sensitivity & Syntactic Mutation Sentinel", lambda r, mode: gate_8_micro_mutator(r, mode=mode, test_cmd=test_cmd, scoped_test_cmd=scoped_test_cmd, changed_only=effective_changed, fast=fast, live_sample=live_sample)),
        ("gate_9_skill_collision", "Gate 9: Tier-2 Skill Routing & Collision Guard", gate_9_skill_collision),
        ("gate_10_performance_sla", "Gate 10: Performance & SLA Sentinel", gate_10_performance_sla),
        ("gate_11_token_reduction", "Gate 11: Token Reduction Architecture Sentinel", lambda r, mode: gate_11_token_reduction(r, mode=mode, fast=fast)),
    ]

    all_passed, gate_results, parallel_outputs = True, [], {}
    if parallel:
        static_gates = [(gk, n, fn) for gk, n, fn in gates if gk in PARALLEL_STATIC_GATE_KEYS and gate_toggles.get(gk) is not False]
        original_stdout = sys.stdout
        proxy_stdout = ThreadLocalStdoutProxy(original_stdout)
        sys.stdout = proxy_stdout
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(static_gates), 6) or 1) as ex:
                futs = {
                    ex.submit(execute_gate_isolated, gk, fn, repo_root, effective_mode, io.StringIO(), n): gk
                    for gk, n, fn in static_gates
                }
                for fut in concurrent.futures.as_completed(futs):
                    dto = fut.result()
                    parallel_outputs[dto.gate_key] = (dto.passed, dto.captured_log)
        finally:
            sys.stdout = original_stdout

    old_stdout = sys.stdout if output_format in ("json", "junit") else None
    if old_stdout:
        sys.stdout = io.StringIO()
    try:
        for g_key, name, gate_fn in gates:
            if gate_toggles.get(g_key) is False:
                if effective_mode.lower() == "hub":
                    if not old_stdout:
                        print(f"\n[{name.split(':')[0].upper()}] Disabled via synapse.config.json (FAIL: Disabling quality gates in Hub mode violates Invariant 11)")
                    gate_results.append((name, False, "FAIL_SKIPPED_BY_CONFIG"))
                    all_passed = False
                    continue
                else:
                    if not old_stdout:
                        print(f"\n[{name.split(':')[0].upper()}] Disabled via synapse.config.json (SKIPPED)")
                    gate_results.append((name, True, "SKIPPED_BY_CONFIG"))
                    continue
            if parallel and g_key in parallel_outputs:
                success, out_text = parallel_outputs[g_key]
                if not old_stdout and out_text:
                    sys.stdout.write(out_text)
                    sys.stdout.flush()
            else:
                success = gate_fn(repo_root, mode=effective_mode)
            metric_alias = {
                "gate_7_infer_linter": "gate_7",
                "gate_8_micro_mutator": "gate_8",
                "gate_10_performance_sla": "gate_10",
                "gate_11_token_reduction": "gate_11",
            }.get(g_key, g_key)
            recorded_meta = LAST_GATE_METRICS.get(metric_alias, {})
            recorded_status = str(recorded_meta.get("status", "")) if isinstance(recorded_meta, dict) else ""
            if not success:
                tri_status = "FAIL"
            elif recorded_status in ("HEURISTIC_PASS", "SKIPPED", "SKIPPED_NO_LOAD_ARTIFACT"):
                tri_status = recorded_status
            else:
                tri_status = "PASS"
            gate_results.append((name, success, tri_status))
            if not success:
                all_passed = False
    finally:
        if old_stdout:
            sys.stdout = old_stdout

    passed_cnt = sum(1 for _, p, s in gate_results if p and s != "SKIPPED_BY_CONFIG")
    strict_passed_cnt = sum(1 for _, p, s in gate_results if p and s == "PASS")
    heuristic_cnt = sum(1 for _, p, s in gate_results if p and s == "HEURISTIC_PASS")
    skipped_cnt = sum(1 for _, _, s in gate_results if s in ("SKIPPED_BY_CONFIG", "SKIPPED", "SKIPPED_NO_LOAD_ARTIFACT"))
    config_skipped_cnt = sum(1 for _, _, s in gate_results if s == "SKIPPED_BY_CONFIG")
    failed_cnt = sum(1 for _, p, s in gate_results if not p or s.startswith("FAIL"))

    gates_json: List[Dict[str, Any]] = [{"name": g[0], "passed": g[1], "status": g[2]} for g in gate_results]
    for gj in gates_json:
        for gk, key in (("gate_7", "gate_7"), ("gate_8", "gate_8"), ("gate_10", "gate_10"), ("gate_11", "gate_11")):
            if gk in str(gj["name"]).lower() and key in LAST_GATE_METRICS:
                gj["metrics"] = LAST_GATE_METRICS[key]
    overall_ok = all_passed and failed_cnt == 0
    exit_code = 0 if overall_ok else 1
    verification_completeness = (
        "FAILED"
        if not overall_ok
        else ("PARTIAL_FAST_TIER" if fast else "FULL_DOD")
    )
    summary_dict: Dict[str, Any] = {
        "total": len(gates),
        "passed": passed_cnt,
        "strict_passed": strict_passed_cnt,
        "heuristic": heuristic_cnt,
        "skipped": skipped_cnt,
        "failed": failed_cnt,
    }
    res_doc: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(), "target": repo_root, "mode": effective_mode,
        "git_commit": get_git_commit_sha(repo_root), "all_passed": overall_ok,
        "verification_completeness": verification_completeness,
        "return_code": exit_code,
        "summary": summary_dict,
        "gates": gates_json,
    }
    for k, outk in (("gate_7", "pytest_metrics"), ("gate_8", "assertion_and_mutation_metrics"), ("gate_10", "performance_metrics"), ("gate_11", "token_reduction_metrics")):
        if k in LAST_GATE_METRICS:
            res_doc[outk] = LAST_GATE_METRICS[k]
    target_report_path = report_path or os.path.join(repo_root, "reports", "verify_all_report.json")
    try:
        os.makedirs(os.path.dirname(os.path.abspath(target_report_path)), exist_ok=True)
        with open(target_report_path, "w", encoding="utf-8") as vf:
            json.dump(res_doc, vf, indent=2)
    except (OSError, TypeError) as err:
        logger.debug("Could not persist %s: %s", target_report_path, err)

    if output_format == "json":
        print(json.dumps(res_doc, indent=2))
        return exit_code, res_doc

    if output_format == "junit":
        print(format_gates_junit(gate_results, repo_root, gate_metrics=LAST_GATE_METRICS))
        return exit_code, res_doc

    print("\n" + "=" * 70)
    if overall_ok:
        if not fast:
            try:
                from tools.core.project_state import sync_project_state_dod
                g7 = LAST_GATE_METRICS.get("gate_7", {})
                test_cnt = g7.get("passed", 0)
                sync_project_state_dod(
                    repo_root,
                    gate_status=f"{strict_passed_cnt} PASS / {heuristic_cnt} HEURISTIC / {skipped_cnt} SKIPPED",
                    test_passed=test_cnt,
                )
            except Exception as sync_err:
                logger.debug("Automatic dual-state synchronization bypassed: %s", sync_err)

            # Issue cryptographic DoD Verification Receipt ONLY on full non-fast HUB runs with real pytest execution
            if effective_mode == "HUB" and config_skipped_cnt == 0:
                try:
                    from tools.core.dod_receipt import create_receipt
                    commit_sha = get_git_commit_sha(repo_root)
                    g7 = LAST_GATE_METRICS.get("gate_7", {})
                    test_cnt = g7.get("passed", 0)
                    if commit_sha and test_cnt > 0:
                        create_receipt(
                            repo_root=repo_root,
                            commit_sha=commit_sha,
                            tests_passed=test_cnt,
                            gates_passed=passed_cnt,
                            mode=effective_mode,
                            summary=summary_dict,
                        )
                except Exception as receipt_err:
                    logger.debug("DoD receipt creation bypassed: %s", receipt_err)

        detail_parts = [f"{strict_passed_cnt} PASS"]
        if heuristic_cnt > 0:
            detail_parts.append(f"{heuristic_cnt} HEURISTIC")
        if skipped_cnt > 0:
            detail_parts.append(f"{skipped_cnt} SKIPPED")
        breakdown_str = ", ".join(detail_parts)
        if fast:
            print(f"[PARTIAL PASS - FAST TIER: {breakdown_str} | Regression Suite Not Run]")
            print("   Fast static feedback succeeded. Run full 'verify_all.py --mode hub' before CI/CD release.\n" + "=" * 70 + "\n")
        else:
            print(f"[ALL {len(gates)} QUALITY GATES VERIFIED ({breakdown_str}) - 100% DoD COMPLIANT]")
            print("   Repository is verified, secure, and ready for execution/CI/CD.\n" + "=" * 70 + "\n")
        return 0, res_doc

    # Invalidate any cached receipt on gate failure
    try:
        from tools.core.dod_receipt import invalidate_receipt
        invalidate_receipt(repo_root)
    except Exception as inv_err:
        logger.debug("DoD receipt invalidation error: %s", inv_err)

    print(f"[DoD BLOCKED] {failed_cnt} OF {len(gates)} QUALITY GATES FAILED.\n" + "=" * 70 + "\n")
    return 1, res_doc


def run_all_gates(repo_root: str, mode: str = "AUTO", test_cmd: str = "", scoped_test_cmd: str = "", changed_only: bool = False, output_format: str = "text", config_path: Optional[str] = None, fast: bool = False, parallel: bool = False, live_sample: bool = False, tier: Optional[str] = None) -> int:
    """Programmatic entrypoint to execute all 11 DoD Quality Gates with config and format support."""
    rc, _ = run_all_gates_detailed(
        repo_root,
        mode=mode,
        test_cmd=test_cmd,
        scoped_test_cmd=scoped_test_cmd,
        changed_only=changed_only,
        output_format=output_format,
        config_path=config_path,
        fast=fast,
        parallel=parallel,
        live_sample=live_sample,
        tier=tier,
    )
    return rc


def main() -> int:
    parser = argparse.ArgumentParser(description="Enterprise DoD Verification Sentinel")
    parser.add_argument("target", nargs="?", default=None, help="Target repository path to verify")
    parser.add_argument("--repo", "--path", dest="repo_path", default=None, help="Target repository path")
    parser.add_argument("--mode", choices=["auto", "hub", "target"], default="auto", help="Execution mode")
    parser.add_argument("--format", choices=["text", "json", "junit"], default="text", help="Output report format")
    parser.add_argument("--config", help="Path to synapse.config.json")
    parser.add_argument("--test-cmd", default="", help="Optional test command for Gate 8 dynamic mutation")
    parser.add_argument("--scoped-test-cmd", default="", help="Scoped dynamic test command for Gate 8")
    parser.add_argument("--changed-only", "--pr", action="store_true", dest="changed_only", help="Scope Gate 8 to git diff")
    parser.add_argument("--live-sample", "--dynamic-mutation", action="store_true", dest="live_sample", default=False, help="Run live sample dynamic mutation on representative test suite (cvss_calculator)")
    parser.add_argument("--tier", choices=["fast", "impact", "full"], default=None, help="Tiered Quality Gate execution profile: fast (<3s), impact (affected tests), full (11 Gates DoD)")
    parser.add_argument("--fast", "-f", action="store_true", default=False, help="Enable fast verification mode (<3s)")
    parser.add_argument("--parallel", "-p", action="store_true", default=False, help="Parallelize static gates")
    args = parser.parse_args()

    try:
        repo_root = resolve_target_repo(cli_target=args.target, cli_repo=args.repo_path)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1
    return run_all_gates(repo_root, mode=args.mode, test_cmd=args.test_cmd, scoped_test_cmd=args.scoped_test_cmd, changed_only=args.changed_only, output_format=args.format, config_path=args.config, fast=args.fast, parallel=args.parallel, live_sample=args.live_sample, tier=args.tier)


if __name__ == "__main__":
    sys.exit(main())
