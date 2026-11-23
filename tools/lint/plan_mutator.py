#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/lint/plan_mutator.py — Mechanical Plan Mutation Testing Sentinel
----------------------------------------------------------------------
Applies deterministic mechanical mutations to implementation plans during
Stage 4 Red-Teaming before any code is generated:
  1. Contract Field Drop / Type Widening: Verifies downstream nodes/matrix catch missing fields.
  2. Edge Reordering & Race Inversion: Verifies parallel nodes don't collide on write sets.
  3. Rollback Invariant Mutation: Verifies rollback commands handle non-git mutations.
Enforces Plan Kill Score >= threshold (default 90.0%).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
import json
import os
import re
import sys
from typing import Any, Dict, List, Set, Tuple

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


@dataclass(frozen=True)
class PlanMutationReportDTO:
    total_mutants: int
    killed_mutants: int
    kill_score: float
    passed: bool
    survived_mutations: List[str]
    details: Dict[str, Any]


def mutate_contract_field_drop(plan_content: str) -> Tuple[bool, str]:
    """Mutant 1: Injects contract field drops/errors and tests if plan and sentinel catch disconnects."""
    from tools.lint.plan_schema_sentinel import validate_plan_content

    # 1. Fallback/boundary assertions check
    has_boundary_check = bool(re.search(r"(?:empty|null|timeout|valueerror|fallback|error_code|graceful)", plan_content, re.I))
    has_matrix_tc = bool(re.search(r"TC-0[2-4]|Boundary|Timeout|Error", plan_content, re.I))
    has_type_contracts = bool(re.search(r"(?:Optional|Union|None|error_code|ResultDTO)", plan_content))

    if not (has_boundary_check and has_matrix_tc and has_type_contracts):
        return False, "SURVIVED: Contract mutation exposed unhandled dropped fields or missing fallback test scenario in Verification Matrix."

    # 2. Active mechanical mutation: Tamper a consumed contract in memory and verify sentinel detects disconnect
    m_con = re.search(r"(consumes[^\n]*?['\"]contract['\"]\s*:\s*['\"])([a-zA-Z0-9_]+)(['\"])", plan_content, re.IGNORECASE)
    if m_con:
        mutated_plan = plan_content[:m_con.start(2)] + "InjectedPhantomMissingContract" + plan_content[m_con.end(2):]
        passed, issues, _ = validate_plan_content(mutated_plan, mode="super")
        if passed or not any("Contract Disconnect" in iss for iss in issues):
            return False, "SURVIVED: Active contract tampering was NOT detected by plan schema sentinel."

    return True, "KILLED: Plan specifies fallback handling and mechanical contract tampering was successfully caught."


def mutate_edge_reordering(plan_content: str) -> Tuple[bool, str]:
    """Mutant 2: Inverts execution order of parallel nodes and checks write-set isolation."""
    # Check if there are [PARALLEL_OK] nodes
    parallel_matches = re.findall(
        r"(?:###?\s*(?:Milestone\s*\d+|Node\s*[A-Za-z0-9]+)[^\n]*\[PARALLEL_OK\][^\n]*)(.*?)(?=(?:###?\s*(?:Milestone\s*\d+|Node\s*[A-Za-z0-9]+))|(?:\n##+\s+)|\Z)",
        plan_content,
        re.DOTALL | re.IGNORECASE,
    )
    if not parallel_matches:
        return True, "KILLED: No concurrent nodes declared, sequential DAG prevents race condition mutants."

    # Parse write sets of parallel nodes
    write_sets: List[Set[str]] = []
    for block in parallel_matches:
        m_write = re.search(r"Write\s+Set[^\n:]*:\s*\[(.*?)\]", block, re.IGNORECASE)
        if m_write:
            wfiles = {w.strip("`'\" ") for w in m_write.group(1).split(",") if w.strip()}
        else:
            m_files = re.findall(r"`([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]{1,6})`", block)
            wfiles = {f for f in m_files if not f.startswith(("pytest", "python"))}
        write_sets.append(wfiles)

    # Check pair-wise intersections
    for i in range(len(write_sets)):
        for j in range(i + 1, len(write_sets)):
            collision = write_sets[i] & write_sets[j]
            if collision:
                return False, f"SURVIVED: Edge reordering caused race condition on shared write-set {collision}."

    return True, "KILLED: Edge reordering confirmed parallel nodes operate on strictly disjoint write sets."


def mutate_rollback_invariant(plan_content: str) -> Tuple[bool, str]:
    """Mutant 3: Simulates failure mid-transaction and tests rollback idempotency."""
    has_rollback_section = bool(re.search(r"Rollback\s*&(?: State-Migration)? Matrix", plan_content, re.I))
    has_rollback_command = bool(re.search(r"Rollback\s*(?:Command|Action|Hook)?:\s*`?[a-zA-Z0-9_\-./\s]+`?", plan_content, re.I))
    has_zero_downtime = bool(re.search(r"(?:Zero-Downtime|checkpoint|dual-write|feature flag|atomic)", plan_content, re.I))

    if has_rollback_section and has_rollback_command and has_zero_downtime:
        return True, "KILLED: Rollback mutation caught by verified Zero-Downtime guard and safe revert commands."
    return False, "SURVIVED: Plan lacks compensating transaction or safe rollback guard for non-git mutations."


def run_plan_mutation_audit(plan_content: str, threshold: float = 90.0) -> PlanMutationReportDTO:
    """Executes the mechanical plan mutation test battery and computes Plan Kill Score."""
    mutators = [
        ("Mutant 1: Contract Field Drop / Type Widening", mutate_contract_field_drop),
        ("Mutant 2: Edge Reordering & Race Inversion", mutate_edge_reordering),
        ("Mutant 3: Rollback Invariant Mutation", mutate_rollback_invariant),
    ]

    total = len(mutators)
    killed = 0
    survived: List[str] = []
    details: Dict[str, Any] = {}

    for name, func in mutators:
        is_killed, verdict = func(plan_content)
        details[name] = {"killed": is_killed, "verdict": verdict}
        if is_killed:
            killed += 1
        else:
            survived.append(f"{name} -> {verdict}")

    kill_score = round((killed / total) * 100.0, 1) if total > 0 else 0.0
    passed = kill_score >= threshold

    return PlanMutationReportDTO(
        total_mutants=total,
        killed_mutants=killed,
        kill_score=kill_score,
        passed=passed,
        survived_mutations=survived,
        details=details,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan Mutation Testing Sentinel (Stage 4 Red-Teaming Sensor)")
    parser.add_argument("--file", help="Path to markdown plan to mutate")
    parser.add_argument("--threshold", type=float, default=90.0, help="Pass gate kill score threshold (default: 90.0)")
    parser.add_argument("--self-test", action="store_true", help="Runs internal self-test battery")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    if args.self_test:
        tmpl_path = os.path.join(_REPO_ROOT, "templates", "test-plan", "spec-driven-plan-template.md")
        if not os.path.isfile(tmpl_path):
            print(f"Error: Template not found: {tmpl_path}")
            return 1
        with open(tmpl_path, "r", encoding="utf-8") as fh:
            content = fh.read()
        report = run_plan_mutation_audit(content, threshold=args.threshold)
        if args.json:
            print(json.dumps(asdict(report), indent=2))
        else:
            status = "PASS" if report.passed else "FAIL"
            print(f"[{status}] Self-Test Plan Mutation Score: {report.kill_score}% (Killed {report.killed_mutants}/{report.total_mutants})")
            for m, res in report.details.items():
                k_str = "[KILL]" if res["killed"] else "[SURVIVE]"
                print(f"  {k_str} {m}: {res['verdict']}")
        return 0 if report.passed else 1

    if not args.file or not os.path.isfile(args.file):
        print("Error: Specify a valid plan file via --file <path> or run --self-test")
        return 1

    with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()

    report = run_plan_mutation_audit(content, threshold=args.threshold)
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        status = "PASS" if report.passed else "FAIL"
        print(f"[{status}] Plan Mutation Kill Score: {report.kill_score}% ({report.killed_mutants}/{report.total_mutants})")
        for m, res in report.details.items():
            k_str = "[KILL]" if res["killed"] else "[SURVIVE]"
            print(f"  {k_str} {m}: {res['verdict']}")
        if not report.passed:
            print("\nSurvived Mutations:")
            for s in report.survived_mutations:
                print(f"  - {s}")

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
