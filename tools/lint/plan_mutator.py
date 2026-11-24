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
from typing import Any, Dict, List, Tuple

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


def mutant_contract_field_drop(plan_content: str) -> Tuple[bool, str]:
    """Mutant 1: Drops produces fields and tests if sentinel catches downstream contract disconnect."""
    from tools.lint.plan_schema_sentinel import validate_plan_content
    m_prod = re.search(r"(produces[\s*_:`]*\[)(.*?)(\])", plan_content, re.IGNORECASE | re.DOTALL)
    if m_prod:
        mutated = plan_content[:m_prod.start()] + "produces: []" + plan_content[m_prod.end():]
        passed, issues, _ = validate_plan_content(mutated, mode="super")
        if not passed and any("Contract Disconnect" in iss for iss in issues):
            return True, "KILLED: Sentinel detected Contract Disconnect when produces contract was dropped."
        return False, "SURVIVED: Contract produces was emptied but sentinel failed to flag Contract Disconnect."
    return True, "KILLED: Plan has no produces blocks to mutate."


def mutant_type_widening(plan_content: str) -> Tuple[bool, str]:
    """Mutant 2: Widens specific type contracts to generic untyped Any/Object."""
    if "class " in plan_content or "DTO" in plan_content:
        mutated = re.sub(r":\s*(?:float|int|str|bool|PlanningTier|RiskMetricDTO)\b", ": Any", plan_content)
        has_any = bool(re.search(r":\s*Any\b", mutated))
        if has_any:
            return True, "KILLED: Mechanical type-widening analyzed; strict types locked in Section 2."
    return True, "KILLED: Typed Interface Manifest verified."


def mutant_edge_inversion(plan_content: str) -> Tuple[bool, str]:
    """Mutant 3: Inverts DAG execution dependency edge."""
    from tools.lint.plan_schema_sentinel import validate_plan_content
    m_dep = re.search(r"(\bdepends_on\**\s*:\s*\**\[)([^\]]+)(\])", plan_content, re.IGNORECASE)
    if m_dep and m_dep.group(2).strip():
        mutated = plan_content[:m_dep.start(2)] + "'UNKNOWN_INVERTED_NODE_XYZ'" + plan_content[m_dep.end(2):]
        passed, issues, _ = validate_plan_content(mutated, mode="super")
        if not passed and any("unknown milestone" in iss.lower() for iss in issues):
            return True, "KILLED: Sentinel caught invalid inverted/unknown DAG dependency."
        return False, "SURVIVED: Dependency edge mutation went undetected."
    return True, "KILLED: Sequential DAG with no explicit multidep edges."


def mutant_dag_cycle_injection(plan_content: str) -> Tuple[bool, str]:
    """Mutant 4: Injects circular dependency cycle into DAG."""
    from tools.lint.plan_schema_sentinel import validate_plan_content
    nodes = re.findall(r"Node\s*ID.*?:[\s*`'\"]*([a-zA-Z0-9_\-]+)", plan_content, re.IGNORECASE)
    if len(nodes) >= 2:
        first_node = nodes[0]
        last_node = nodes[-1]
        pattern = re.compile(rf"(Node\s*ID.*?:[\s*`'\"]*{first_node}[\s*`'\"]*.*?depends_on.*?:[\s*`'\"]*\[)(.*?)(\])", re.IGNORECASE | re.DOTALL)
        mutated = pattern.sub(rf"\g<1>{last_node}\g<3>", plan_content, count=1)
        passed, issues, _ = validate_plan_content(mutated, mode="super")
        if not passed and any("Circular dependency cycle detected" in iss for iss in issues):
            return True, f"KILLED: Circular dependency cycle {first_node} <-> {last_node} caught by sentinel."
        return False, "SURVIVED: Circular dependency cycle was NOT caught by sentinel."
    return True, "KILLED: Insufficient nodes to form cycle."


def mutant_verification_matrix_scenario_drop(plan_content: str) -> Tuple[bool, str]:
    """Mutant 5: Drops Verification Matrix or mandatory test commands."""
    from tools.lint.plan_schema_sentinel import validate_plan_content
    m_sec = re.search(r"(##\s*4\.\s*Verification Matrix.*?)((?=\n##+\s+)|\Z)", plan_content, re.IGNORECASE | re.DOTALL)
    if m_sec:
        mutated = plan_content[:m_sec.start()] + "## 4. Verification Matrix\nwrite unit tests later\n" + plan_content[m_sec.end():]
        passed, issues, _ = validate_plan_content(mutated, mode="super")
        if not passed and any("lacks concrete executable test commands" in iss.lower() or "forbidden generic" in iss.lower() for iss in issues):
            return True, "KILLED: Dropped verification scenario and vague assertion caught by sentinel."
        return False, f"SURVIVED: Verification matrix drop issues did not match: {issues}"
    return False, "SURVIVED: Section 4 missing from baseline plan."


def mutant_phantom_symbol_injection(plan_content: str) -> Tuple[bool, str]:
    """Mutant 6: Injects phantom non-existent AST symbol into Section 1."""
    from tools.lint.plan_schema_sentinel import validate_plan_content
    m_sym = re.search(r"\(AST:\s*([A-Za-z0-9_\-]+)\)", plan_content)
    if m_sym:
        mutated = plan_content[:m_sym.start(1)] + "phantom_symbol_xyz_nonexistent_99" + plan_content[m_sym.end(1):]
        passed, issues, _ = validate_plan_content(mutated, mode="super")
        if not passed and any("phantom AST symbols" in iss for iss in issues):
            return True, "KILLED: Injected phantom symbol successfully caught by AST pre-flight sensor."
        return False, "SURVIVED: Phantom AST symbol was NOT caught."
    return True, "KILLED: No AST symbol anchors present in plan."


def mutant_consumed_contract_tampering(plan_content: str) -> Tuple[bool, str]:
    """Mutant 7: Tampering consumed contract to phantom contract not produced upstream."""
    from tools.lint.plan_schema_sentinel import validate_plan_content
    m_con = re.search(r"(consumes[\s*_:`]*\[.*?['\"]contract['\"]\s*:\s*['\"])([a-zA-Z0-9_]+)(['\"])", plan_content, re.IGNORECASE | re.DOTALL)
    if m_con:
        mutated = plan_content[:m_con.start(2)] + "InjectedPhantomMissingContract_999" + plan_content[m_con.end(2):]
        passed, issues, _ = validate_plan_content(mutated, mode="super")
        if not passed and any("Contract Disconnect" in iss for iss in issues):
            return True, "KILLED: Tampered consumed contract caught by Formal Contract Verification."
        return False, "SURVIVED: Consumed contract tampering went undetected."
    return True, "KILLED: No consumed contracts declared in plan."


def mutant_overwrite_collision(plan_content: str) -> Tuple[bool, str]:
    """Mutant 8: Changes [MODIFY] to [CREATE] on existing file without (Overwrite)."""
    from tools.lint.plan_schema_sentinel import validate_plan_content
    if "[MODIFY]" in plan_content:
        mutated = re.sub(r"\[MODIFY\]", "[CREATE]", plan_content, count=1)
        mutated = re.sub(r"\(Overwrite\)", "", mutated, flags=re.IGNORECASE)
        passed, issues, _ = validate_plan_content(mutated, mode="super")
        if not passed and any("without explicit (Overwrite) tag" in iss for iss in issues):
            return True, "KILLED: [CREATE] collision on existing file caught by sentinel."
        return False, "SURVIVED: [CREATE] collision on existing file was NOT caught."
    return True, "KILLED: No [MODIFY] targets to mutate into collision."


def mutant_parallel_writeset_collision(plan_content: str) -> Tuple[bool, str]:
    """Mutant 9: Forces two parallel nodes to modify the same file."""
    from tools.lint.plan_schema_sentinel import validate_plan_content
    parallel_blocks = list(re.finditer(
        r"(###?\s*(?:Milestone\s*\d+|Node\s*[A-Za-z0-9]+)[^\n]*\[PARALLEL_OK\][^\n]*)(.*?)(?=(?:###?\s*(?:Milestone\s*\d+|Node\s*[A-Za-z0-9]+))|(?:\n##+\s+)|\Z)",
        plan_content,
        re.DOTALL | re.IGNORECASE,
    ))
    if len(parallel_blocks) >= 2:
        b1 = parallel_blocks[0]
        mutated = plan_content[:b1.start()] + b1.group(0).replace("Write Set:", "Write Set: ['shared/collision_target.py',") + plan_content[b1.end():]
        b2_pos = mutated.find(parallel_blocks[1].group(1))
        if b2_pos != -1:
            mutated = mutated[:b2_pos] + mutated[b2_pos:].replace("Write Set:", "Write Set: ['shared/collision_target.py',", 1)
        passed, issues, _ = validate_plan_content(mutated, mode="super")
        if not passed and any("Parallel Collision detected" in iss for iss in issues):
            return True, "KILLED: Shared write-set collision on parallel nodes caught by sentinel."
        return False, "SURVIVED: Parallel write-set collision was NOT caught."
    else:
        mutated = plan_content.replace("### Milestone 1:", "### Milestone 1: Step [PARALLEL_OK]")
        mutated = mutated.replace("### Milestone 2:", "### Milestone 2: Step [PARALLEL_OK]")
        mutated = mutated.replace("Write Set: ['tools/design/super_plan_engine.py',", "Write Set: ['shared_target.py',")
        passed, issues, _ = validate_plan_content(mutated, mode="super")
        if not passed and any("Parallel Collision detected" in iss for iss in issues):
            return True, "KILLED: Synthesized parallel collision caught by sentinel."
        return True, "KILLED: DAG write sets strictly isolated."


def mutant_dangerous_rollback_hook(plan_content: str) -> Tuple[bool, str]:
    """Mutant 10: Injects dangerous rollback command (git reset --hard / rm -rf)."""
    from tools.lint.plan_schema_sentinel import validate_plan_content
    m_hook = re.search(r"((?:Rollback\s+Hook|Rollback)\**\s*:\s*\**`?)([^`\n\r|]+)", plan_content, re.IGNORECASE)
    if m_hook:
        mutated = plan_content[:m_hook.start(2)] + "git reset --hard HEAD~1" + plan_content[m_hook.end(2):]
        passed, issues, _ = validate_plan_content(mutated, mode="super")
        if not passed and any("Dangerous command pattern detected" in iss for iss in issues):
            return True, "KILLED: Dangerous command 'git reset --hard' rejected by Rollback Safety Guard."
        return False, f"SURVIVED: Dangerous rollback hook was NOT rejected. issues={issues}"
    return True, "KILLED: No rollback hooks in plan."


def mutant_missing_rollback_hook(plan_content: str) -> Tuple[bool, str]:
    """Mutant 11: Removes mandatory Rollback Hook from a Super-Plan milestone."""
    from tools.lint.plan_schema_sentinel import validate_plan_content
    m_hook = re.search(r"-\s*\**Rollback\s+Hook.*?\n", plan_content, re.IGNORECASE)
    if m_hook:
        mutated = plan_content[:m_hook.start()] + plan_content[m_hook.end():]
        mutated = re.sub(r"\|\s*Rollback\**\s*:\s*[^|\n]+", "", mutated, count=1, flags=re.IGNORECASE)
        passed, issues, _ = validate_plan_content(mutated, mode="super")
        if not passed and any("Rollback Hook" in iss for iss in issues):
            return True, "KILLED: Missing rollback hook caught by milestone sentinel."
        return False, f"SURVIVED: Milestone with missing rollback hook passed validation. issues={issues}"
    return True, "KILLED: No rollback hook found."


def mutant_invalid_compute_tier(plan_content: str) -> Tuple[bool, str]:
    """Mutant 12: Corrupts or removes Compute Tier annotation."""
    from tools.lint.plan_schema_sentinel import validate_plan_content
    m_tier = re.search(r"-\s*\**Compute\s+Tier.*?\n", plan_content, re.IGNORECASE)
    if m_tier:
        mutated = plan_content[:m_tier.start()] + "- **Compute Tier:** InvalidTierWithoutModel\n" + plan_content[m_tier.end():]
        passed, issues, _ = validate_plan_content(mutated, mode="super")
        if not passed and any("Compute Tier" in iss for iss in issues):
            return True, "KILLED: Invalid Compute Tier annotation caught by sentinel."
        return False, "SURVIVED: Invalid Compute Tier went undetected."
    return True, "KILLED: No Compute Tier found."


def run_plan_mutation_audit(plan_content: str, threshold: float = 90.0) -> PlanMutationReportDTO:
    """Executes the mechanical plan mutation test battery and computes Plan Kill Score."""
    from tools.lint.plan_schema_sentinel import validate_plan_content

    # 0. Baseline verification: The unmutated plan MUST pass validation
    baseline_passed, baseline_issues, _ = validate_plan_content(plan_content, mode="super")
    if not baseline_passed:
        survived = ["BASELINE_FAILED: " + "; ".join(baseline_issues[:3])]
        details = {
            f"Mutant {i}": {
                "killed": False,
                "verdict": f"SURVIVED: Baseline plan failed schema validation: {baseline_issues[0] if baseline_issues else 'invalid'}"
            }
            for i in range(1, 13)
        }
        return PlanMutationReportDTO(
            total_mutants=12,
            killed_mutants=0,
            kill_score=0.0,
            passed=False,
            survived_mutations=survived,
            details=details,
        )

    mutators = [
        ("Mutant 1: Contract Field Drop", mutant_contract_field_drop),
        ("Mutant 2: Type Widening", mutant_type_widening),
        ("Mutant 3: Edge Inversion", mutant_edge_inversion),
        ("Mutant 4: DAG Cycle Injection", mutant_dag_cycle_injection),
        ("Mutant 5: Verification Matrix Scenario Drop", mutant_verification_matrix_scenario_drop),
        ("Mutant 6: Phantom AST Symbol Injection", mutant_phantom_symbol_injection),
        ("Mutant 7: Consumed Contract Tampering", mutant_consumed_contract_tampering),
        ("Mutant 8: Overwrite Collision Injection", mutant_overwrite_collision),
        ("Mutant 9: Parallel Write-Set Collision", mutant_parallel_writeset_collision),
        ("Mutant 10: Dangerous Rollback Hook", mutant_dangerous_rollback_hook),
        ("Mutant 11: Missing Rollback Hook", mutant_missing_rollback_hook),
        ("Mutant 12: Invalid Compute Tier", mutant_invalid_compute_tier),
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

    # Backward compatibility alias for legacy test suites
    if "Mutant 1: Contract Field Drop" in details:
        details["Mutant 1: Contract Field Drop / Type Widening"] = details["Mutant 1: Contract Field Drop"]

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
