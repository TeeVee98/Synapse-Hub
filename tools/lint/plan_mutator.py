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
  1. Contract Field Drop / Type Widening: Verifies sentinel catches dropped produces and `: Any` widening.
  2. Edge Reordering, Cycle Injection & Race Collision: Verifies DAG invariants & write-set isolation.
  3. Rollback & Compute Tier Mutations: Verifies rollback safety guard and compute tier enforcement.
Enforces non-vacuous applicable-denominator Plan Kill Score >= threshold (default 90.0%).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
import re
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

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
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

_PLACEHOLDER_PREFIXES = (
    "[",
    "path/",
    "src/modules/target_module",
    "src/target_types",
    "src/caller",
    "obsolete/",
)

_MILESTONE_BLOCK_RE = re.compile(
    r"(###?\s*(?:Milestone\s*\d+|Chặng\s*\d+|Node\s*[A-Za-z0-9]+)[^\n]*)(.*?)(?=(?:###?\s*(?:Milestone\s*\d+|Chặng\s*\d+|Node\s*[A-Za-z0-9]+))|(?:\n##+\s+)|\Z)",
    re.DOTALL | re.IGNORECASE,
)


@dataclass(frozen=True)
class PlanMutationReportDTO:
    total_mutants: int
    killed_mutants: int
    kill_score: float
    passed: bool
    survived_mutations: List[str]
    details: Dict[str, Any]
    applicable_mutants: int = 0
    not_applicable_mutants: int = 0


def mutant_contract_field_drop(plan_content: str) -> Tuple[Optional[bool], str]:
    """Mutant 1: Drops produces contract consumed downstream and verifies sentinel catches disconnect."""
    from tools.lint.plan_schema_sentinel import validate_plan_content

    consumed = set(
        re.findall(
            r"consumes[\s*_:`]*\[.*?['\"]contract['\"]\s*:\s*['\"]([a-zA-Z0-9_]+)['\"]",
            plan_content,
            re.IGNORECASE | re.DOTALL,
        )
    )
    if not consumed:
        return None, "NOT_APPLICABLE: Plan declares no downstream consumed contracts."

    for m_prod in re.finditer(r"(produces[\s*_:`]*\[)(.*?)(\])", plan_content, re.IGNORECASE | re.DOTALL):
        produced_names = set(
            re.findall(r"['\"]contract['\"]\s*:\s*['\"]([a-zA-Z0-9_]+)['\"]", m_prod.group(2))
        )
        if produced_names & consumed:
            mutated = plan_content[: m_prod.start()] + "produces: []" + plan_content[m_prod.end() :]
            passed, issues, _ = validate_plan_content(mutated, mode="super")
            if not passed and any("Contract Disconnect" in iss for iss in issues):
                return True, "KILLED: Sentinel detected Contract Disconnect when produces contract was dropped."
            return False, "SURVIVED: Contract produces was emptied but sentinel failed to flag Contract Disconnect."

    return None, "NOT_APPLICABLE: Plan has no produces blocks consumed by downstream nodes."


def mutant_type_widening(plan_content: str) -> Tuple[Optional[bool], str]:
    """Mutant 2: Widens a typed field/parameter in Section 2 to untyped `: Any` and verifies sentinel catches it."""
    from tools.lint.plan_schema_sentinel import validate_plan_content

    m_sec2 = re.search(
        r"(^##\s*(?:2[.\s]*)?(?:Data\s+Flow|Interface\s+Signatures)[^\n]*\n)(.*?)(?=^##\s+|\Z)",
        plan_content,
        re.IGNORECASE | re.DOTALL | re.MULTILINE,
    )
    if not m_sec2:
        return None, "NOT_APPLICABLE: Section 2 Data Flow / Interface Signatures missing."

    sec2_body = m_sec2.group(2)
    fence_pat = re.compile(r"(```(?:python|py|ts|typescript)?\s*\n)(.*?)(```)", re.DOTALL | re.IGNORECASE)
    type_pat = re.compile(
        r"(?<![\"'])\b([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(?:float|int|str|bool|dict|list|number|string|boolean|PlanningTier|RiskMetricDTO)\b"
    )

    for m_fence in fence_pat.finditer(sec2_body):
        code_body = m_fence.group(2)
        m_type = type_pat.search(code_body)
        if m_type:
            widened_code = (
                code_body[: m_type.start()]
                + f"{m_type.group(1)}: Any"
                + code_body[m_type.end() :]
            )
            new_sec2_body = (
                sec2_body[: m_fence.start(2)] + widened_code + sec2_body[m_fence.end(2) :]
            )
            mutated = (
                plan_content[: m_sec2.start(2)] + new_sec2_body + plan_content[m_sec2.end(2) :]
            )
            passed, issues, _ = validate_plan_content(mutated, mode="super")
            if not passed and any("Type Widening" in iss for iss in issues):
                return True, f"KILLED: Sentinel rejected widened '{m_type.group(1)}: Any' in Section 2."
            return False, f"SURVIVED: Widening '{m_type.group(1)}: Any' was NOT rejected by sentinel."

    return None, "NOT_APPLICABLE: No concrete typed fields/parameters in Section 2 fenced code blocks."


def mutant_edge_inversion(plan_content: str) -> Tuple[Optional[bool], str]:
    """Mutant 3: Replaces a DAG dependency edge with an unknown node ID."""
    from tools.lint.plan_schema_sentinel import validate_plan_content

    for m_dep in re.finditer(r"(\bdepends_on[\s*:`_]*\[)([^\]]+)(\])", plan_content, re.IGNORECASE):
        if m_dep.group(2).strip():
            mutated = (
                plan_content[: m_dep.start(2)]
                + "'UNKNOWN_INVERTED_NODE_XYZ'"
                + plan_content[m_dep.end(2) :]
            )
            passed, issues, _ = validate_plan_content(mutated, mode="super")
            if not passed and any("unknown milestone" in iss.lower() for iss in issues):
                return True, "KILLED: Sentinel caught invalid inverted/unknown DAG dependency."
            return False, "SURVIVED: Dependency edge mutation went undetected."
    return None, "NOT_APPLICABLE: Sequential DAG with no non-empty depends_on edges."


def mutant_dag_cycle_injection(plan_content: str) -> Tuple[Optional[bool], str]:
    """Mutant 4: Injects circular dependency cycle into DAG."""
    from tools.lint.plan_schema_sentinel import validate_plan_content

    nodes = re.findall(r"Node\s*ID.*?:[\s*`'\"]*([a-zA-Z0-9_\-]+)", plan_content, re.IGNORECASE)
    if len(nodes) < 2:
        return None, "NOT_APPLICABLE: Fewer than 2 DAG nodes to form a cycle."

    first_node = nodes[0]
    last_node = nodes[-1]
    pattern = re.compile(
        rf"(Node\s*ID.*?:[\s*`'\"]*{re.escape(first_node)}[\s*`'\"]*.*?depends_on[\s*:`_]*\[)(.*?)(\])",
        re.IGNORECASE | re.DOTALL,
    )
    mutated, count = pattern.subn(rf"\g<1>{last_node}\g<3>", plan_content, count=1)
    if count == 0:
        return None, "NOT_APPLICABLE: Could not locate depends_on on first DAG node."
    passed, issues, _ = validate_plan_content(mutated, mode="super")
    if not passed and any("Circular dependency cycle detected" in iss for iss in issues):
        return True, f"KILLED: Circular dependency cycle {first_node} <-> {last_node} caught by sentinel."
    return False, "SURVIVED: Circular dependency cycle was NOT caught by sentinel."


def mutant_verification_matrix_scenario_drop(plan_content: str) -> Tuple[Optional[bool], str]:
    """Mutant 5: Drops Verification Matrix or mandatory test commands."""
    from tools.lint.plan_schema_sentinel import validate_plan_content

    m_sec = re.search(
        r"(##\s*4\.\s*Verification Matrix.*?)((?=\n##+\s+)|\Z)",
        plan_content,
        re.IGNORECASE | re.DOTALL,
    )
    if not m_sec:
        return False, "SURVIVED: Section 4 missing from baseline plan."

    mutated = (
        plan_content[: m_sec.start()]
        + "## 4. Verification Matrix\nwrite unit tests later\n"
        + plan_content[m_sec.end() :]
    )
    passed, issues, _ = validate_plan_content(mutated, mode="super")
    if not passed and any(
        "lacks concrete executable test commands" in iss.lower() or "forbidden generic" in iss.lower()
        for iss in issues
    ):
        return True, "KILLED: Dropped verification scenario and vague assertion caught by sentinel."
    return False, f"SURVIVED: Verification matrix drop issues did not match: {issues}"


def mutant_phantom_symbol_injection(plan_content: str) -> Tuple[Optional[bool], str]:
    """Mutant 6: Injects phantom non-existent AST symbol into an existing Section 1 [MODIFY] target."""
    from tools.lint.plan_schema_sentinel import validate_plan_content

    action_sym_pat = re.compile(
        r"\|\s*`?\[MODIFY\]`?\s*\|\s*`?([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]{1,6})`?(?:::([A-Za-z0-9_\-./:#]+))?(?:\s*\((?:AST:\s*)?([A-Za-z0-9_\-./:#]+)\))?",
        re.IGNORECASE,
    )

    for m in action_sym_pat.finditer(plan_content):
        fpath = m.group(1)
        if fpath.startswith(_PLACEHOLDER_PREFIXES):
            continue
        if not os.path.isfile(os.path.join(_REPO_ROOT, fpath)):
            continue
        sym_group = 2 if m.group(2) else (3 if m.group(3) else 0)
        if sym_group == 0:
            continue
        raw_sym = m.group(sym_group).strip()
        if (
            raw_sym.lower() in ("new", "overwrite", "allow-overwrite", "module_root", "file_root", "unknown", "rule_body", "workflow_body")
            or re.match(r"^L\d+(-L?\d+)?$", raw_sym, re.IGNORECASE)
        ):
            continue
        mutated = (
            plan_content[: m.start(sym_group)]
            + "phantom_symbol_xyz_nonexistent_99"
            + plan_content[m.end(sym_group) :]
        )
        passed, issues, _ = validate_plan_content(mutated, mode="super")
        if not passed and any("phantom AST symbols" in iss for iss in issues):
            return True, f"KILLED: Injected phantom symbol in '{fpath}' caught by AST pre-flight sensor."
        return False, f"SURVIVED: Phantom AST symbol in '{fpath}' was NOT caught."

    return None, "NOT_APPLICABLE: No real-file AST symbol anchors in Section 1 to mutate."


def mutant_consumed_contract_tampering(plan_content: str) -> Tuple[Optional[bool], str]:
    """Mutant 7: Tampers consumed contract to phantom contract not produced upstream."""
    from tools.lint.plan_schema_sentinel import validate_plan_content

    m_con = re.search(
        r"(consumes[\s*_:`]*\[.*?['\"]contract['\"]\s*:\s*['\"])([a-zA-Z0-9_]+)(['\"])",
        plan_content,
        re.IGNORECASE | re.DOTALL,
    )
    if not m_con:
        return None, "NOT_APPLICABLE: No consumed contracts declared in plan."

    mutated = (
        plan_content[: m_con.start(2)]
        + "InjectedPhantomMissingContract_999"
        + plan_content[m_con.end(2) :]
    )
    passed, issues, _ = validate_plan_content(mutated, mode="super")
    if not passed and any("Contract Disconnect" in iss for iss in issues):
        return True, "KILLED: Tampered consumed contract caught by Formal Contract Verification."
    return False, "SURVIVED: Consumed contract tampering went undetected."


def mutant_overwrite_collision(plan_content: str) -> Tuple[Optional[bool], str]:
    """Mutant 8: Changes [MODIFY] to [CREATE] on an existing disk file without (Overwrite)."""
    from tools.lint.plan_schema_sentinel import validate_plan_content

    mod_pat = re.compile(
        r"(\|\s*`?)(\[MODIFY\])(`?\s*\|\s*`?([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]{1,6})`?)",
        re.IGNORECASE,
    )
    for m in mod_pat.finditer(plan_content):
        fpath = m.group(4)
        if fpath.startswith(_PLACEHOLDER_PREFIXES):
            continue
        if not os.path.isfile(os.path.join(_REPO_ROOT, fpath)):
            continue
        mutated = plan_content[: m.start(2)] + "[CREATE]" + plan_content[m.end(2) :]
        mutated = re.sub(r"\(Overwrite\)", "", mutated, flags=re.IGNORECASE)
        passed, issues, _ = validate_plan_content(mutated, mode="super")
        if not passed and any("without explicit (Overwrite) tag" in iss for iss in issues):
            return True, f"KILLED: [CREATE] collision on existing file '{fpath}' caught by sentinel."
        return False, f"SURVIVED: [CREATE] collision on existing file '{fpath}' was NOT caught."

    return None, "NOT_APPLICABLE: No existing-file [MODIFY] targets to mutate into collision."


def _inject_collision_writeset(block_text: str, shared_file: str = "shared/collision_target.py") -> str:
    """Replaces or inserts a Write Set containing shared_file inside a milestone block."""
    ws_pat = re.compile(r"(Write\s+Set[^\n:]*:[\s*`]*\[)(.*?)(\]`?)", re.IGNORECASE)
    if ws_pat.search(block_text):
        return ws_pat.sub(rf"\g<1>'{shared_file}'\g<3>", block_text, count=1)
    lines = block_text.splitlines(keepends=True)
    if not lines:
        return block_text
    return lines[0] + f"- Write Set: `['{shared_file}']`\n" + "".join(lines[1:])


def mutant_parallel_writeset_collision(plan_content: str) -> Tuple[Optional[bool], str]:
    """Mutant 9: Forces two independent [PARALLEL_OK] milestones to share a colliding write-set."""
    from tools.lint.plan_schema_sentinel import validate_plan_content

    blocks = list(_MILESTONE_BLOCK_RE.finditer(plan_content))
    if len(blocks) < 2:
        return None, "NOT_APPLICABLE: Fewer than 2 milestones for parallel write-set collision test."

    # Pick first two milestones; tag both [PARALLEL_OK], clear depends_on so they run concurrently,
    # and force both to write to the same colliding file path.
    b1, b2 = blocks[0], blocks[1]

    def _make_colliding(match: re.Match[str]) -> str:
        header = match.group(1)
        body = match.group(2)
        if "[PARALLEL_OK]" not in header.upper():
            header = f"{header} [PARALLEL_OK]"
        body = re.sub(
            r"(\bdepends_on[\s*:`_]*\[)[^\]]*(\])",
            r"\g<1>\g<2>",
            body,
            count=1,
            flags=re.IGNORECASE,
        )
        return _inject_collision_writeset(header + body)

    m1_text = _make_colliding(b1)
    m2_text = _make_colliding(b2)
    mutated = (
        plan_content[: b1.start()]
        + m1_text
        + plan_content[b1.end() : b2.start()]
        + m2_text
        + plan_content[b2.end() :]
    )
    passed, issues, _ = validate_plan_content(mutated, mode="super")
    if not passed and any("Parallel Collision detected" in iss for iss in issues):
        return True, "KILLED: Shared write-set collision on parallel milestones caught by sentinel."
    return False, f"SURVIVED: Parallel write-set collision was NOT caught by sentinel. issues={issues}"


def mutant_dangerous_rollback_hook(plan_content: str) -> Tuple[Optional[bool], str]:
    """Mutant 10: Injects dangerous rollback command (git reset --hard)."""
    from tools.lint.plan_schema_sentinel import validate_plan_content

    m_hook = re.search(
        r"((?:Rollback\s+Hook|Rollback)[^\w\n]*:[\s*`'\"]*)([^`\n\r|*]+)",
        plan_content,
        re.IGNORECASE,
    )
    if not m_hook:
        return None, "NOT_APPLICABLE: No rollback hooks in plan."

    mutated = (
        plan_content[: m_hook.start(2)]
        + "git reset --hard HEAD~1"
        + plan_content[m_hook.end(2) :]
    )
    passed, issues, _ = validate_plan_content(mutated, mode="super")
    if not passed and any("Dangerous command pattern detected" in iss for iss in issues):
        return True, "KILLED: Dangerous command 'git reset --hard' rejected by Rollback Safety Guard."
    return False, f"SURVIVED: Dangerous rollback hook was NOT rejected. issues={issues}"


def mutant_missing_rollback_hook(plan_content: str) -> Tuple[Optional[bool], str]:
    """Mutant 11: Removes mandatory Rollback Hook from the first Super-Plan milestone."""
    from tools.lint.plan_schema_sentinel import validate_plan_content

    blocks = list(_MILESTONE_BLOCK_RE.finditer(plan_content))
    if not blocks:
        return None, "NOT_APPLICABLE: No milestone blocks found."

    b1 = blocks[0]
    block_text = b1.group(0)
    has_rollback = bool(re.search(r"(?:Rollback\s+Hook|Rollback)[^\w\n]*:", block_text, re.IGNORECASE))
    if not has_rollback:
        return None, "NOT_APPLICABLE: First milestone has no rollback hook to remove."

    stripped_block = re.sub(r"^\s*-?\s*\**Rollback\s+Hook[^\n]*\n?", "", block_text, flags=re.IGNORECASE | re.MULTILINE)
    stripped_block = re.sub(r"\|\s*\**Rollback\**\s*:\s*[^|\n]+", "", stripped_block, flags=re.IGNORECASE)
    stripped_block = re.sub(r"^\s*-?\s*\**Rollback\**\s*:\s*[^\n]*\n?", "", stripped_block, flags=re.IGNORECASE | re.MULTILINE)

    mutated = plan_content[: b1.start()] + stripped_block + plan_content[b1.end() :]
    passed, issues, _ = validate_plan_content(mutated, mode="super")
    if not passed and any("Rollback Hook" in iss for iss in issues):
        return True, "KILLED: Missing rollback hook caught by milestone sentinel."
    return False, f"SURVIVED: Milestone with missing rollback hook passed validation. issues={issues}"


def mutant_invalid_compute_tier(plan_content: str) -> Tuple[Optional[bool], str]:
    """Mutant 12: Corrupts Compute Tier annotation on a milestone."""
    from tools.lint.plan_schema_sentinel import validate_plan_content

    m_tier = re.search(r"-\s*\**Compute\s+Tier[^\n]*\n", plan_content, re.IGNORECASE)
    if not m_tier:
        return None, "NOT_APPLICABLE: No Compute Tier annotation found."

    mutated = (
        plan_content[: m_tier.start()]
        + "- **Compute Tier:** InvalidTierWithoutModel\n"
        + plan_content[m_tier.end() :]
    )
    passed, issues, _ = validate_plan_content(mutated, mode="super")
    if not passed and any("Compute Tier" in iss for iss in issues):
        return True, "KILLED: Invalid Compute Tier annotation caught by sentinel."
    return False, "SURVIVED: Invalid Compute Tier went undetected."


def run_plan_mutation_audit(plan_content: str, threshold: float = 90.0) -> PlanMutationReportDTO:
    """Executes the mechanical 12-mutant battery and computes non-vacuous Plan Kill Score."""
    from tools.lint.plan_schema_sentinel import validate_plan_content

    # 0. Baseline verification: The unmutated plan MUST pass validation
    baseline_passed, baseline_issues, _ = validate_plan_content(plan_content, mode="super")
    if not baseline_passed:
        survived = ["BASELINE_FAILED: " + "; ".join(baseline_issues[:3])]
        details = {
            f"Mutant {i}": {
                "killed": False,
                "applicable": True,
                "status": "SURVIVED",
                "verdict": (
                    f"SURVIVED: Baseline plan failed schema validation: "
                    f"{baseline_issues[0] if baseline_issues else 'invalid'}"
                ),
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
            applicable_mutants=12,
            not_applicable_mutants=0,
        )

    mutators: List[Tuple[str, Callable[[str], Tuple[Optional[bool], str]]]] = [
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
    applicable = 0
    not_applicable = 0
    killed = 0
    survived: List[str] = []
    details: Dict[str, Any] = {}

    for name, func in mutators:
        outcome, verdict = func(plan_content)
        if outcome is None:
            not_applicable += 1
            details[name] = {
                "killed": False,
                "applicable": False,
                "status": "NOT_APPLICABLE",
                "verdict": verdict,
            }
        elif outcome is True:
            applicable += 1
            killed += 1
            details[name] = {
                "killed": True,
                "applicable": True,
                "status": "KILLED",
                "verdict": verdict,
            }
        else:
            applicable += 1
            details[name] = {
                "killed": False,
                "applicable": True,
                "status": "SURVIVED",
                "verdict": verdict,
            }
            survived.append(f"{name} -> {verdict}")

    if applicable == 0:
        kill_score = 0.0
        passed = False
        survived.append("APPLICABLE_DENOMINATOR_ZERO: No mutants were applicable to this plan.")
    else:
        kill_score = round((killed / applicable) * 100.0, 1)
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
        applicable_mutants=applicable,
        not_applicable_mutants=not_applicable,
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
            print(
                f"[{status}] Self-Test Plan Mutation Score: {report.kill_score}% "
                f"(Killed {report.killed_mutants}/{report.applicable_mutants} applicable, "
                f"{report.not_applicable_mutants} N/A)"
            )
            for m, res in report.details.items():
                st = res.get("status", "KILL" if res["killed"] else "SURVIVE")
                print(f"  [{st}] {m}: {res['verdict']}")
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
        print(
            f"[{status}] Plan Mutation Kill Score: {report.kill_score}% "
            f"({report.killed_mutants}/{report.applicable_mutants} applicable, "
            f"{report.not_applicable_mutants} N/A)"
        )
        for m, res in report.details.items():
            st = res.get("status", "KILL" if res["killed"] else "SURVIVE")
            print(f"  [{st}] {m}: {res['verdict']}")
        if not report.passed:
            print("\nSurvived Mutations:")
            for s in report.survived_mutations:
                print(f"  - {s}")

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
