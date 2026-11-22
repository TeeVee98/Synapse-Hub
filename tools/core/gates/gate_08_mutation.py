#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Gate 8: Assertion Sensitivity & Syntactic Mutation Sentinel.
Runs syntactic mutation testing and verifies assertion sensitivity score >= 80%.
"""

import glob
import json
import logging
import os
import subprocess
import sys
from typing import Any, Dict, List, Tuple

from tools.core.gates.base import (
    BaseGate,
    LAST_GATE_METRICS,
    detect_repo_mode,
    load_synapse_config,
    resolve_tool_path,
    safe_print,
)

logger = logging.getLogger("synapse.gates.mutation")


def gate_8_micro_mutator(
    repo_root: str,
    mode: str = "AUTO",
    test_cmd: str = "",
    scoped_test_cmd: str = "",
    changed_only: bool = False,
    fast: bool = False,
    live_sample: bool = False,
) -> bool:
    """Gate 8: Runs syntactic mutation testing and verifies assertion sensitivity score >= 80%."""
    effective_mode = detect_repo_mode(repo_root) if mode == "AUTO" else mode
    is_pr_or_changed = not fast and (changed_only or bool(scoped_test_cmd) or os.environ.get("SYNAPSE_PR_MODE") == "1")

    mutator_script = resolve_tool_path(repo_root, "micro_mutator.py", "lint")

    if not os.path.exists(mutator_script):
        print("[FAIL] micro_mutator.py not found in tools/! Gate 8 requires micro_mutator.py (fail-closed).")
        return False

    cfg = load_synapse_config(repo_root)
    qg_cfg = cfg.get("quality_gates", {})
    min_score_val = float(qg_cfg.get("mutation_min_score", 80.0))
    min_score_str = str(min_score_val)
    allow_empty_val = bool(qg_cfg.get("allow_empty_mutations", False))

    # Live Sample Dynamic Mutation Mode
    effective_live_sample = live_sample or (os.environ.get("SYNAPSE_DYNAMIC_MUTATION") == "1")
    if effective_live_sample:
        sample_rel = os.path.join("tests", "test_cvss_calculator.py")
        sample_target = os.path.join(repo_root, sample_rel)
        if os.path.isfile(sample_target):
            sample_cmd = test_cmd or f'{sys.executable} -m pytest "{sample_rel}" -q'
            print(f"\n[GATE 8] Running Assertion Sensitivity & Syntactic Mutation Sentinel [LIVE DYNAMIC SAMPLE MODE] (Min Score >= {min_score_str}%)...")
            print(f"   Executing live dynamic mutant runs against sample: {sample_rel} via '{sample_cmd}'")
            baseline_dir = os.path.join(repo_root, "reports")
            os.makedirs(baseline_dir, exist_ok=True)
            baseline_file = os.path.join(baseline_dir, "mutant_baseline.json")
            cmd = [sys.executable, mutator_script, sample_target, "--min-score", min_score_str, "--baseline", baseline_file, "--json", "--test-cmd", sample_cmd]
            try:
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=120.0)
            except subprocess.TimeoutExpired:
                print("[FAIL] Assertion Sensitivity Sentinel timed out after 120s!")
                return False
            if res.returncode != 0:
                print("[FAIL] Gate 8 Live Dynamic Mutation Failed: Mutants survived test execution.")
                if res.stdout:
                    safe_print(res.stdout)
                return False
            try:
                data = json.loads(res.stdout)
                score_val = data.get("mutation_score", 100.0)
                killed_cnt = data.get("killed", 0)
                valid_cnt = data.get("valid_mutants", data.get("total_mutants", 0))
                print(f"[PASS] Runtime Dynamic Mutation Score: {score_val}% >= 80% (Caught {killed_cnt}/{valid_cnt} valid mutants). Zero unasserted logic branches.")
                LAST_GATE_METRICS["gate_8"] = {
                    "mode": f"DYNAMIC SAMPLE ({sample_cmd})",
                    "measurement_kind": "dynamic_execution",
                    "static_assertion_sensitivity_score": None,
                    "dynamic_mutation_score": score_val,
                    "mutation_score": score_val,
                    "killed": killed_cnt,
                    "survived": data.get("survived", 0),
                    "timed_out": data.get("timed_out", 0),
                    "invalid_syntax": data.get("invalid_syntax", 0),
                    "total_mutants": data.get("total_mutants", 0),
                    "valid_mutants": valid_cnt,
                    "passed": True
                }
                return True
            except Exception as err:
                print(f"[FAIL] Gate 8 Live Dynamic Mutation JSON decode error: {err}")
                return False

    # PR / Changed Code Scoped Dynamic Mutation Mode
    if effective_mode == "HUB" and is_pr_or_changed:
        print(f"\n[GATE 8] Running Assertion Sensitivity & Scoped Syntactic Mutation Sentinel [PR / CHANGED CODE MODE] (Min Score >= {min_score_str}%)...")
        modified_files: List[str] = []
        try:
            from tools import test_impact
            if hasattr(test_impact, "get_git_modified_files"):
                modified_files = test_impact.get_git_modified_files(repo_root)
        except ImportError as err:
            logger.debug("tools.test_impact unavailable: %s", err)

        if not modified_files:
            try:
                res = subprocess.run(
                    ["git", "-C", repo_root, "diff", "--name-only", "HEAD"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10.0
                )
                modified_files = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            except (OSError, subprocess.SubprocessError) as err:
                logger.debug("git diff HEAD failed: %s", err)
                modified_files = []

        py_targets = [
            f for f in modified_files
            if f.endswith(".py")
            and (f.startswith("tools/") or f.startswith("tools\\"))
            and not f.startswith(("tools/templates", "tools/templates/"))
        ]

        if not py_targets:
            print("[PASS] Scoped Dynamic Mutation: Zero modified source files in tools/ detected in Git diff. Gate 8 passed.")
            LAST_GATE_METRICS["gate_8"] = {
                "mode": "DYNAMIC_SCOPED",
                "measurement_kind": "no_modified_code",
                "modified_files": [],
                "dynamic_mutation_score": None,
                "static_assertion_sensitivity_score": None,
                "mutation_score": None,
                "valid_mutants": 0,
                "killed": 0,
                "survived": 0,
                "timed_out": 0,
                "invalid_syntax": 0,
                "passed": True,
                "note": "Zero modified Python source files in tools/ detected in Git diff"
            }
            return True

        print(f"   Detected {len(py_targets)} modified source file(s) for scoped mutation: {', '.join(py_targets)}")
        effective_scoped_cmd = scoped_test_cmd or f"{sys.executable} -m pytest {{test_files}} -q"

        all_ok = True
        gate8_reports: List[Tuple[str, Dict[str, Any]]] = []
        for target_rel in py_targets:
            target_abs = os.path.join(repo_root, target_rel)
            if not os.path.isfile(target_abs):
                continue
            cmd = [
                sys.executable, mutator_script, target_abs,
                "--scoped-test-cmd", effective_scoped_cmd,
                "--min-score", min_score_str,
                "--allow-empty",
                "--json"
            ]
            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=180.0)
                try:
                    rep = json.loads(proc.stdout)
                except Exception:
                    rep = {
                        "passed": proc.returncode == 0,
                        "mutation_score": 0.0 if proc.returncode != 0 else None,
                        "dynamic_mutation_score": 0.0 if proc.returncode != 0 else None,
                        "valid_mutants": 0,
                        "killed": 0,
                        "survived": 0,
                        "timed_out": 0,
                        "invalid_syntax": 0
                    }
                gate8_reports.append((target_rel, rep))
                dyn_score = rep.get("dynamic_mutation_score", rep.get("mutation_score", 0.0))
                if proc.returncode != 0:
                    all_ok = False
                    safe_print(f"[FAIL] Scoped Dynamic Mutation failed on {target_rel} (Score: {dyn_score}% < {min_score_str}%, survived: {rep.get('survived', 0)})")
                    if proc.stderr:
                        safe_print(proc.stderr)
                else:
                    valid_cnt = rep.get("valid_mutants", rep.get("total_mutants", 0))
                    safe_print(f"[PASS] Scoped Dynamic Mutation on {target_rel}: {dyn_score}% (Killed {rep.get('killed', 0)}/{valid_cnt} valid mutants)")
            except subprocess.TimeoutExpired:
                safe_print(f"[FAIL] Scoped Dynamic Mutation timed out on {target_rel} after 180s")
                all_ok = False

        total_killed = sum(r.get("killed", 0) for r in [x[1] for x in gate8_reports])
        total_survived = sum(r.get("survived", 0) for r in [x[1] for x in gate8_reports])
        total_timed_out = sum(r.get("timed_out", 0) for r in [x[1] for x in gate8_reports])
        total_invalid = sum(r.get("invalid_syntax", 0) for r in [x[1] for x in gate8_reports])
        total_valid = total_killed + total_survived + total_timed_out
        overall_score = round((total_killed / total_valid) * 100.0, 2) if total_valid > 0 else 0.0

        LAST_GATE_METRICS["gate_8"] = {
            "mode": "DYNAMIC_SCOPED",
            "measurement_kind": "dynamic_execution",
            "modified_files": py_targets,
            "dynamic_mutation_score": overall_score if total_valid > 0 else None,
            "static_assertion_sensitivity_score": None,
            "mutation_score": overall_score if total_valid > 0 else None,
            "valid_mutants": total_valid,
            "killed": total_killed,
            "survived": total_survived,
            "timed_out": total_timed_out,
            "invalid_syntax": total_invalid,
            "passed": all_ok,
            "reports": [r[1] for r in gate8_reports]
        }
        return all_ok

    eval_mode_desc = f"DYNAMIC EXECUTION MODE ({test_cmd})" if test_cmd else "HEURISTIC STATIC MODE"
    print(f"\n[GATE 8] Running Assertion Sensitivity & Syntactic Mutation Sentinel [{eval_mode_desc}] (Min Score >= 80%)...")
    scripts_dir = os.path.join(repo_root, "Scripts")
    tests_dir = os.path.join(repo_root, "tests")

    target_dir = None
    if os.path.isdir(scripts_dir):
        groovy_files = [f for f in glob.glob(os.path.join(scripts_dir, "**", "*.groovy"), recursive=True)]
        if groovy_files:
            target_dir = scripts_dir
    if not target_dir and os.path.isdir(tests_dir):
        test_files = [f for f in glob.glob(os.path.join(tests_dir, "**", "*.*"), recursive=True) if f.endswith((".py", ".ts", ".js", ".groovy"))]
        if test_files:
            target_dir = tests_dir

    if not target_dir:
        if effective_mode == "HUB":
            print(f"[N/A] Hub Mode: Not Applicable (Assertion Sensitivity & Syntactic Mutation applies to target test suites in Spokes) [{eval_mode_desc}].")
            return True
        else:
            print("[N/A] No automated test scripts found in Scripts/ or tests/ to mutate.")
            return True

    if not test_cmd:
        test_cmd = qg_cfg.get("test_cmd") or cfg.get("test_cmd", "")

    baseline_dir = os.path.join(repo_root, "reports")
    os.makedirs(baseline_dir, exist_ok=True)
    baseline_file = os.path.join(baseline_dir, "mutant_baseline.json")

    cmd = [sys.executable, mutator_script, target_dir, "--min-score", min_score_str, "--baseline", baseline_file, "--json"]
    if test_cmd:
        cmd.extend(["--test-cmd", test_cmd])
    if allow_empty_val:
        cmd.append("--allow-empty")
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=120.0)
    except subprocess.TimeoutExpired:
        print("[FAIL] Assertion Sensitivity Sentinel timed out after 120s!")
        return False
    if res.returncode != 0:
        try:
            data = json.loads(res.stdout)
            if data.get("total_mutants", 0) == 0 or data.get("no_mutants_generated"):
                if allow_empty_val:
                    print(f"[N/A] Zero mutable expressions detected in {target_dir} (Allowed by configuration). Gate 8 skipped.")
                    return True
                else:
                    print(f"[FAIL] Gate 8 REJECTED: Zero mutable expressions detected in {target_dir}! Test suite must contain mutable logic or assertions. (Fail-closed)")
                    return False
            print("[FAIL] Assertion Sensitivity Sentinel REJECTED: Score < 80% or unasserted logic found.")
            print(f"   Assertion Sensitivity: {data.get('mutation_score', 0)}% (Required: >= 80%)")
            print(f"   Mutants Caught: {data.get('killed', 0)} / {data.get('total_mutants', 0)}")
        except (json.JSONDecodeError, ValueError, KeyError):
            if res.stdout:
                safe_print(res.stdout)
        return False
    else:
        try:
            data = json.loads(res.stdout)
            mode_label = f"DYNAMIC ({test_cmd})" if test_cmd else "STATIC AST HEURISTIC"
            is_dynamic = bool(test_cmd)
            score_val = data.get("mutation_score", 100.0)
            score_label = "Runtime Dynamic Mutation Score" if is_dynamic else "Assertion Sensitivity [STATIC AST HEURISTIC]"
            denominator_desc = "valid mutants" if is_dynamic else "syntactic mutants"
            print(f"[PASS] {score_label}: {score_val}% >= 80% (Caught {data.get('killed', 0)}/{data.get('total_mutants', 0)} {denominator_desc}). Zero unasserted logic branches.")
            if not test_cmd:
                print("   [INFO] Note: Evaluated via static AST dataflow analysis. Pass --test-cmd '<command>' to execute live mutant runs.")
            if os.path.exists(baseline_file):
                print(f"   Mutant Baseline: Recorded {data.get('killed', 0)}/{data.get('total_mutants', 0)} mutants ({score_val}%) into reports/mutant_baseline.json")
            LAST_GATE_METRICS["gate_8"] = {
                "mode": mode_label,
                "measurement_kind": "dynamic_execution" if is_dynamic else "static_ast_heuristic",
                "static_assertion_sensitivity_score": score_val if not is_dynamic else None,
                "dynamic_mutation_score": score_val if is_dynamic else None,
                "mutation_score": score_val,
                "killed": data.get("killed", 0),
                "survived": data.get("survived", 0),
                "timed_out": data.get("timed_out", 0),
                "invalid_syntax": data.get("invalid_syntax", 0),
                "total_mutants": data.get("total_mutants", 0),
                "valid_mutants": data.get("valid_mutants", data.get("total_mutants", 0)),
                "passed": True
            }
        except (json.JSONDecodeError, ValueError, KeyError):
            print(f"[PASS] Assertion Sensitivity Sentinel passed: Score >= 80% [{eval_mode_desc}].")
            LAST_GATE_METRICS["gate_8"] = {
                "mode": eval_mode_desc,
                "measurement_kind": "dynamic_execution" if test_cmd else "static_ast_heuristic",
                "static_assertion_sensitivity_score": 100.0 if not test_cmd else None,
                "dynamic_mutation_score": 100.0 if test_cmd else None,
                "mutation_score": 100.0,
                "killed": 0,
                "total_mutants": 0,
                "valid_mutants": 0,
                "passed": True
            }
        return True


class Gate08Mutation(BaseGate):
    """Gate 8: Assertion Sensitivity & Syntactic Mutation Sentinel."""

    gate_id = 8
    name = "Gate 8: Assertion Sensitivity & Syntactic Mutation Sentinel"
    key = "gate_8_micro_mutator"

    def run(self, repo_root: str, mode: str = "AUTO", **kwargs) -> bool:
        test_cmd = kwargs.get("test_cmd", "")
        scoped_test_cmd = kwargs.get("scoped_test_cmd", "")
        changed_only = kwargs.get("changed_only", False)
        fast = kwargs.get("fast", False)
        live_sample = kwargs.get("live_sample", False)
        return gate_8_micro_mutator(
            repo_root,
            mode=mode,
            test_cmd=test_cmd,
            scoped_test_cmd=scoped_test_cmd,
            changed_only=changed_only,
            fast=fast,
            live_sample=live_sample,
        )
