#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/orchestration/plan_review_auditor.py — Zero-Trust Plan-vs-Solo Review Auditor
-----------------------------------------------------------------------------------
Independent post-code reconciliation engine that audits /solo implementation artifacts
and git diffs against /super-plan specifications:
  1. Plan Scope & Write-Set Reconciliation (missing, undeleted, unplanned files)
  2. DTO & Signature Contract Drift (missing symbols, arity break, Any widening, frozen DTO)
  3. Verification Matrix Realization (test existence + non-tautological AST assertions)
  4. /solo Forensic Provenance & Anti-Tamper (constant-time HMAC, post-Red test_tree_hash,
     mutation threshold & survivor surfacing, strict decisions.tsv audit)
  5. Beyond-the-Diff Caller Compatibility & Import Acyclicity (CallGraphIndexer + DependencyCycleSolver)
  6. Signed Unified Review Receipt (atomic temp-file + os.replace + HMAC-SHA256)

Architectural Layering Guard:
  NEVER imports solo_runner.py (relying exclusively on leaf modules solo_contracts,
  call_graph_indexer, neuro_symbolic_solver, dag_self_healer, and decision_log) so
  senior_code_review -> plan_review_auditor stays 100% acyclic with solo_runner.
"""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
import glob
import hashlib
import hmac
import json
import os
import re
import sys
import tempfile
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.context.call_graph_indexer import get_or_build_call_graph
from tools.core.decision_log import audit_decision_log
from tools.design.dag_self_healer import parse_plan_to_dag
from tools.orchestration.solo_contracts import (
    AstTautologyAnalyzer,
    _get_receipt_hmac_key,
    _verify_red_receipt_hmac,
)
from tools.reasoning.neuro_symbolic_solver import DependencyCycleSolver

MAX_CALLER_FILES = 50
HIGH_FAN_IN_THRESHOLD = 15

_EPHEMERAL_PREFIXES = (
    ".git/",
    "docs/adr/",
    "reports/",
    "scratch/",
    ".cache/",
    ".pytest_cache/",
    ".agent_memory/",
)


@dataclass(frozen=True)
class PlanReconciliationDTO:
    plan_path: str
    milestone_scope: Optional[str]
    planned_files: Tuple[str, ...]
    missing_planned_files: Tuple[str, ...]
    undeleted_files: Tuple[str, ...]
    unplanned_modified_files: Tuple[str, ...]
    drifted_contracts: Tuple[str, ...]
    missing_matrix_tests: Tuple[str, ...]
    alignment_score_pct: float
    passed: bool


@dataclass(frozen=True)
class SoloProvenanceAuditDTO:
    solo_detected: bool
    milestones_checked: Tuple[str, ...]
    valid_red_receipts: Tuple[str, ...]
    tampered_or_invalid_receipts: Tuple[str, ...]
    post_red_tampered_tests: Tuple[str, ...]
    mutation_scores: Dict[str, float]
    survived_mutant_summaries: Tuple[str, ...]
    decision_log_valid: bool
    provenance_score_pct: float
    passed: bool


@dataclass(frozen=True)
class CallerCompatibilityDTO:
    modified_symbols: Tuple[str, ...]
    broken_call_sites: Tuple[str, ...]
    import_cycles: Tuple[str, ...]
    high_fan_in_targets: Tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class UnifiedReviewReceiptDTO:
    verdict: str
    passed: bool
    target_scope: str
    files_changed: int
    must_fix_count: int
    should_fix_count: int
    nice_to_have_count: int
    plan_reconciliation: Optional[PlanReconciliationDTO]
    solo_provenance: Optional[SoloProvenanceAuditDTO]
    caller_compatibility: CallerCompatibilityDTO
    receipt_hmac: str


def _norm_rel(path: str) -> str:
    cleaned = path.replace("\\", "/").strip()
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned


def _is_test_file(rel_path: str) -> bool:
    norm = _norm_rel(rel_path).lower()
    base = os.path.basename(norm)
    return (
        norm.startswith("tests/")
        or "/tests/" in norm
        or base.startswith("test_")
        or base.endswith("_test.py")
        or ".spec." in base
        or ".test." in base
    )


def _make_finding(
    severity: str,
    code: str,
    title: str,
    file_path: str,
    line_no: int,
    what_is: str,
    problem: str,
    fix: str,
    if_skipped: str,
) -> Dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "title": title,
        "file": file_path,
        "line": str(line_no),
        "what_is": what_is,
        "problem": problem,
        "fix": fix,
        "if_skipped": if_skipped,
    }


def _extract_section(markdown: str, section_num: int) -> str:
    pattern = rf"^##\s+{section_num}\.[^\n]*\n(.*?)(?=^##\s+\d+\.|\Z)"
    match = re.search(pattern, markdown, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def _parse_section1_targets(plan_content: str) -> Tuple[List[str], List[str]]:
    """Extracts (create_or_modify_files, delete_files) from Section 1 target table file column."""
    create_or_modify: List[str] = []
    delete_files: List[str] = []
    for line in plan_content.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        action_cell = cells[0]
        path_cell = cells[1]
        is_delete = "[DELETE]" in action_cell
        is_create_mod = "[CREATE]" in action_cell or "[MODIFY]" in action_cell
        if not (is_delete or is_create_mod):
            continue
        for match in re.findall(r"`([A-Za-z0-9_.\-/\\]+\.[A-Za-z0-9]{1,8})`", path_cell):
            if match.startswith(("pytest", "python", "[")):
                continue
            norm = _norm_rel(match)
            if is_delete:
                if norm not in delete_files:
                    delete_files.append(norm)
            else:
                if norm not in create_or_modify:
                    create_or_modify.append(norm)
    return create_or_modify, delete_files


def _is_frozen_dataclass(cls_node: ast.ClassDef) -> bool:
    """Returns True if cls_node has @dataclass(frozen=True) or @dataclasses.dataclass(frozen=True)."""
    for dec in cls_node.decorator_list:
        if isinstance(dec, ast.Call):
            fn = dec.func
            if (isinstance(fn, ast.Name) and fn.id == "dataclass") or (
                isinstance(fn, ast.Attribute) and fn.attr == "dataclass"
            ):
                for kw in dec.keywords:
                    if (
                        kw.arg == "frozen"
                        and isinstance(kw.value, ast.Constant)
                        and kw.value.value is True
                    ):
                        return True
    return False


def _annotation_text(node: Optional[ast.AST]) -> str:
    if node is None:
        return ""
    return ast.unparse(node).strip()


def _extract_python_contracts(section2_text: str) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Parses Python fenced code blocks in Section 2 into planned classes and functions."""
    planned_classes: Dict[str, Dict[str, Any]] = {}
    planned_funcs: Dict[str, Dict[str, Any]] = {}

    code_blocks = re.findall(r"```python\s*\n(.*?)```", section2_text, re.DOTALL | re.IGNORECASE)
    for block in code_blocks:
        try:
            tree = ast.parse(block)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                is_frozen = _is_frozen_dataclass(node)
                fields: Dict[str, str] = {}
                for stmt in node.body:
                    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        fields[stmt.target.id] = _annotation_text(stmt.annotation)
                planned_classes[node.name] = {
                    "is_frozen": is_frozen,
                    "fields": fields,
                }
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                params = _extract_func_params(node)
                planned_funcs[node.name] = params
    return planned_classes, planned_funcs


def _extract_func_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Dict[str, Any]:
    args = node.args
    all_pos = list(args.posonlyargs) + list(args.args)
    if all_pos and all_pos[0].arg in ("self", "cls"):
        all_pos = all_pos[1:]
    kwonly = list(args.kwonlyargs)
    all_named = all_pos + kwonly

    annotations: Dict[str, str] = {a.arg: _annotation_text(a.annotation) for a in all_named}
    pos_names = [a.arg for a in all_pos]
    kwonly_names = [a.arg for a in kwonly]

    num_defaults = len(args.defaults)
    required_pos = max(0, len(all_pos) - num_defaults)
    required_kwonly = [
        a.arg for a, default in zip(kwonly, args.kw_defaults) if default is None
    ]
    accepted_kw = {a.arg for a in args.args if a.arg not in ("self", "cls")} | set(kwonly_names)

    return {
        "names": pos_names + kwonly_names,
        "pos_names": pos_names,
        "kwonly_names": kwonly_names,
        "annotations": annotations,
        "arity": len(pos_names) + len(kwonly_names),
        "required_pos": required_pos,
        "max_pos": len(pos_names),
        "required_kwonly": required_kwonly,
        "accepted_kw": accepted_kw,
        "has_vararg": args.vararg is not None,
        "has_kwarg": args.kwarg is not None,
    }


def _collect_actual_python_symbols(
    repo_root: str,
    py_files: Sequence[str],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    actual_classes: Dict[str, Dict[str, Any]] = {}
    actual_funcs: Dict[str, Dict[str, Any]] = {}

    for rel in py_files:
        abs_p = os.path.join(repo_root, rel)
        if not os.path.isfile(abs_p):
            continue
        try:
            with open(abs_p, "r", encoding="utf-8", errors="replace") as fh:
                source = fh.read()
            tree = ast.parse(source, filename=rel)
        except (OSError, SyntaxError):
            continue

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                is_frozen = _is_frozen_dataclass(node)
                fields: Dict[str, str] = {}
                for stmt in node.body:
                    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        fields[stmt.target.id] = _annotation_text(stmt.annotation)
                actual_classes[node.name] = {
                    "file": rel,
                    "line": node.lineno,
                    "is_frozen": is_frozen,
                    "fields": fields,
                }
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                info = _extract_func_params(node)
                info["file"] = rel
                info["line"] = node.lineno
                actual_funcs[node.name] = info
    return actual_classes, actual_funcs


def _function_has_real_assertion(fn_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(fn_node):
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Attribute):
                if fn.attr.startswith("assert") or fn.attr in ("raises", "warns"):
                    return True
            elif isinstance(fn, ast.Name) and fn.id in ("expect", "assert_that"):
                return True
    return False


def _audit_verification_matrix(
    repo_root: str,
    plan_content: str,
    scoped_files: Optional[Set[str]],
    findings: List[Dict[str, str]],
) -> Tuple[List[str], int]:
    """Verifies Section 4 Verification Matrix test files, -k test functions, and non-tautological assertions."""
    section4 = _extract_section(plan_content, 4)
    missing_tests: List[str] = []
    checks_count = 0

    for line in section4.splitlines():
        if "|" not in line or re.match(r"^\s*\|[\s\-:|]+\|\s*$", line):
            continue
        test_files = re.findall(r"(tests/[A-Za-z0-9_.\-/]+\.py)", line)
        if not test_files:
            continue
        k_match = re.search(r'-k\s+["\']([^"\']+)["\']', line)
        k_expr = k_match.group(1).strip() if k_match else None

        for tf in dict.fromkeys(test_files):
            norm_tf = _norm_rel(tf)
            if scoped_files is not None and norm_tf not in scoped_files:
                continue
            checks_count += 1
            abs_tf = os.path.join(repo_root, norm_tf)
            if not os.path.isfile(abs_tf):
                desc = f"{norm_tf} (missing test file)"
                missing_tests.append(desc)
                findings.append(
                    _make_finding(
                        severity="Must fix",
                        code="UNVERIFIED_MATRIX_SCENARIOS",
                        title=f"Verification Matrix test file missing: {norm_tf}",
                        file_path=norm_tf,
                        line_no=1,
                        what_is="A test suite required by Section 4 Verification Matrix does not exist.",
                        problem="Planned acceptance scenarios have zero automated verification.",
                        fix=f"Create {norm_tf} implementing the planned verification scenarios.",
                        if_skipped="Planned contract guarantees ship untested.",
                    )
                )
                continue

            try:
                source = open(abs_tf, "r", encoding="utf-8", errors="replace").read()
                tree = ast.parse(source, filename=norm_tf)
            except (OSError, SyntaxError) as exc:
                desc = f"{norm_tf} (unparseable: {exc})"
                missing_tests.append(desc)
                findings.append(
                    _make_finding(
                        severity="Must fix",
                        code="UNVERIFIED_MATRIX_SCENARIOS",
                        title=f"Verification Matrix test file has syntax error: {norm_tf}",
                        file_path=norm_tf,
                        line_no=1,
                        what_is="A test file referenced by Section 4 cannot be parsed.",
                        problem=f"Syntax/read error prevents verification: {exc}",
                        fix="Fix syntax errors in the test file and re-run pytest.",
                        if_skipped="Tests cannot execute.",
                    )
                )
                continue

            test_funcs: List[ast.FunctionDef | ast.AsyncFunctionDef] = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                    test_funcs.append(node)

            if k_expr:
                tokens = [t.strip() for t in re.split(r"\s+(?:or|and)\s+", k_expr) if t.strip() and t.strip() != "not"]
                matched_funcs = [
                    fn for fn in test_funcs if any(tok in fn.name for tok in tokens)
                ]
                if not matched_funcs:
                    desc = f"{norm_tf}::{k_expr} (missing test function)"
                    missing_tests.append(desc)
                    findings.append(
                        _make_finding(
                            severity="Must fix",
                            code="UNVERIFIED_MATRIX_SCENARIOS",
                            title=f"Planned Verification Matrix test missing: {k_expr}",
                            file_path=norm_tf,
                            line_no=1,
                            what_is=f"Section 4 requires test matching '-k {k_expr}' in {norm_tf}.",
                            problem="The planned exam scenario is missing from the test suite.",
                            fix=f"Implement a non-tautological test matching '{k_expr}' in {norm_tf}.",
                            if_skipped="A planned requirement has no regression coverage.",
                        )
                    )
                    continue
                target_funcs = matched_funcs
            else:
                target_funcs = test_funcs

            for fn in target_funcs:
                fn_src = ast.get_source_segment(source, fn) or ""
                taut_findings = AstTautologyAnalyzer().analyze_source(fn_src) if fn_src else []
                has_assert = _function_has_real_assertion(fn)
                if taut_findings or not has_assert:
                    reason = taut_findings[0][2] if taut_findings else "zero assertions in test body"
                    desc = f"{norm_tf}::{fn.name} ({reason})"
                    missing_tests.append(desc)
                    findings.append(
                        _make_finding(
                            severity="Must fix",
                            code="UNVERIFIED_MATRIX_SCENARIOS",
                            title=f"Tautological or empty Verification Matrix test: {fn.name}",
                            file_path=norm_tf,
                            line_no=fn.lineno,
                            what_is=f"Test '{fn.name}' fails non-tautological assertion verification ({reason}).",
                            problem="Tautological or empty tests create fake passes and hide real defects.",
                            fix="Replace with behavioral assertions against real production outputs.",
                            if_skipped="Fake-pass tests violate Truth Anchor invariant.",
                        )
                    )

    return missing_tests, checks_count


def _reconcile_plan(
    repo_root: str,
    changed_files: List[str],
    plan_path: str,
    milestone_id: Optional[str],
    findings: List[Dict[str, str]],
) -> PlanReconciliationDTO:
    resolved_plan = (
        plan_path
        if os.path.isabs(plan_path)
        else os.path.join(repo_root, plan_path)
    )
    if not os.path.isfile(resolved_plan):
        findings.append(
            _make_finding(
                severity="Must fix",
                code="PLAN_FILE_NOT_FOUND",
                title=f"Plan file not found: {plan_path}",
                file_path=plan_path,
                line_no=1,
                what_is="The --plan target file does not exist on disk.",
                problem="Cannot reconcile implementation against a missing Super-Plan contract.",
                fix="Provide a valid path to the implementation plan Markdown file.",
                if_skipped="Plan fidelity cannot be verified.",
            )
        )
        return PlanReconciliationDTO(
            plan_path=plan_path,
            milestone_scope=milestone_id,
            planned_files=(),
            missing_planned_files=(),
            undeleted_files=(),
            unplanned_modified_files=(),
            drifted_contracts=(),
            missing_matrix_tests=(),
            alignment_score_pct=0.0,
            passed=False,
        )

    plan_content = open(resolved_plan, "r", encoding="utf-8", errors="replace").read()
    create_mod_all, delete_all = _parse_section1_targets(plan_content)
    dag = parse_plan_to_dag(plan_content, repo_root=repo_root)

    if milestone_id and milestone_id.strip():
        ms = milestone_id.strip()
        node = dag.nodes.get(ms)
        ws = [_norm_rel(w) for w in node.write_set] if node else []
        planned_files = list(dict.fromkeys(ws))
        delete_targets = [f for f in delete_all if f in planned_files]
        create_mod_targets = [f for f in planned_files if f not in delete_targets]
        scoped_set: Optional[Set[str]] = set(planned_files)
    else:
        combined: List[str] = list(create_mod_all) + [f for f in delete_all if f not in create_mod_all]
        for node in dag.nodes.values():
            for w in node.write_set:
                nw = _norm_rel(w)
                if nw and nw not in combined:
                    combined.append(nw)
        planned_files = combined
        delete_targets = list(delete_all)
        create_mod_targets = [f for f in planned_files if f not in delete_targets]
        scoped_set = None

    missing_planned: List[str] = []
    for f in create_mod_targets:
        if not os.path.exists(os.path.join(repo_root, f)):
            missing_planned.append(f)
            findings.append(
                _make_finding(
                    severity="Must fix",
                    code="UNIMPLEMENTED_PLANNED_FILES",
                    title=f"Planned file missing on disk: {f}",
                    file_path=f,
                    line_no=1,
                    what_is=f"File '{f}' is declared as [CREATE]/[MODIFY] in the plan but missing on disk.",
                    problem="Implementation is incomplete relative to the approved Super-Plan write set.",
                    fix=f"Implement '{f}' or update the plan before requesting review.",
                    if_skipped="Deliverable is missing planned artifacts.",
                )
            )

    undeleted: List[str] = []
    for f in delete_targets:
        if os.path.exists(os.path.join(repo_root, f)):
            undeleted.append(f)
            findings.append(
                _make_finding(
                    severity="Must fix",
                    code="UNDELETED_PLANNED_FILES",
                    title=f"Planned [DELETE] file still exists: {f}",
                    file_path=f,
                    line_no=1,
                    what_is=f"File '{f}' is marked [DELETE] in the plan but still exists on disk.",
                    problem="Stale code remains active and violates the cleanup contract.",
                    fix=f"Remove '{f}' and verify no callers still import it.",
                    if_skipped="Dead legacy files accumulate and risk accidental imports.",
                )
            )

    plan_rel = _norm_rel(os.path.relpath(resolved_plan, repo_root))
    planned_set = set(planned_files)
    unplanned: List[str] = []
    for cf in changed_files:
        ncf = _norm_rel(cf)
        if not ncf or ncf in planned_set or ncf == plan_rel or ncf.endswith("implementation_plan.md"):
            continue
        if ncf.startswith(_EPHEMERAL_PREFIXES) or os.path.basename(ncf) in ("decisions.tsv", "decisions.tsv.lock"):
            continue
        if ncf not in unplanned:
            unplanned.append(ncf)
            findings.append(
                _make_finding(
                    severity="Should fix",
                    code="UNPLANNED_SCOPE_CREEP",
                    title=f"Unplanned file modified outside plan write set: {ncf}",
                    file_path=ncf,
                    line_no=1,
                    what_is=f"Changed file '{ncf}' is not listed in the plan's target files or milestone write set.",
                    problem="Out-of-scope edits expand blast radius without architectural review.",
                    fix=f"Revert '{ncf}' if unrelated, or document it in the plan.",
                    if_skipped="Unreviewed scope creep bypasses plan blast-radius guards.",
                )
            )

    # Layer 2: Section 2 DTO & Signature Contract Drift
    section2 = _extract_section(plan_content, 2)
    planned_classes, planned_funcs = _extract_python_contracts(section2)
    planned_py_sources = [f for f in create_mod_targets if f.endswith(".py") and not _is_test_file(f)]
    drifted_contracts: List[str] = []
    has_must_fix_drift = False
    contract_checks = 0

    if planned_py_sources and (planned_classes or planned_funcs):
        actual_classes, actual_funcs = _collect_actual_python_symbols(repo_root, planned_py_sources)
        for cls_name, spec in planned_classes.items():
            contract_checks += 1
            actual = actual_classes.get(cls_name)
            if actual is None:
                msg = f"Missing planned class/DTO '{cls_name}'"
                drifted_contracts.append(msg)
                has_must_fix_drift = True
                findings.append(
                    _make_finding(
                        severity="Must fix",
                        code="CONTRACT_SIGNATURE_DRIFT",
                        title=msg,
                        file_path=planned_py_sources[0],
                        line_no=1,
                        what_is=f"Section 2 defines '{cls_name}' but it was not found in planned Python sources.",
                        problem="Missing planned DTO breaks downstream consumers and typed manifests.",
                        fix=f"Define '{cls_name}' matching Section 2's typed contract.",
                        if_skipped="Interface contract mismatch will cause runtime AttributeError/ImportError.",
                    )
                )
                continue

            if spec["is_frozen"] and not actual["is_frozen"]:
                msg = f"DTO '{cls_name}' missing @dataclass(frozen=True)"
                drifted_contracts.append(msg)
                findings.append(
                    _make_finding(
                        severity="Should fix",
                        code="UNFROZEN_DTO_CONTRACT",
                        title=msg,
                        file_path=actual["file"],
                        line_no=actual["line"],
                        what_is=f"'{cls_name}' was planned as @dataclass(frozen=True) but is mutable on disk.",
                        problem="Mutable DTOs allow accidental state mutation across audit boundaries.",
                        fix=f"Decorate '{cls_name}' with @dataclass(frozen=True).",
                        if_skipped="Immutability invariant from Section 2 is violated.",
                    )
                )

            for fname, planned_ann in spec["fields"].items():
                actual_ann = actual["fields"].get(fname)
                if actual_ann is None:
                    msg = f"DTO '{cls_name}' missing field '{fname}'"
                    drifted_contracts.append(msg)
                    has_must_fix_drift = True
                    findings.append(
                        _make_finding(
                            severity="Must fix",
                            code="CONTRACT_SIGNATURE_DRIFT",
                            title=msg,
                            file_path=actual["file"],
                            line_no=actual["line"],
                            what_is=f"Field '{fname}' planned on '{cls_name}' is missing.",
                            problem="Missing DTO field breaks callers expecting the typed interface.",
                            fix=f"Add field '{fname}: {planned_ann}' to '{cls_name}'.",
                            if_skipped="AttributeError at downstream read sites.",
                        )
                    )
                elif planned_ann and planned_ann != "Any" and actual_ann == "Any":
                    msg = f"DTO '{cls_name}.{fname}' type widened from '{planned_ann}' to 'Any'"
                    drifted_contracts.append(msg)
                    has_must_fix_drift = True
                    findings.append(
                        _make_finding(
                            severity="Must fix",
                            code="CONTRACT_SIGNATURE_DRIFT",
                            title=msg,
                            file_path=actual["file"],
                            line_no=actual["line"],
                            what_is=f"Typed field '{cls_name}.{fname}' was weakened to bare 'Any'.",
                            problem="Widening concrete DTO types to Any erases static type safety.",
                            fix=f"Restore explicit type annotation '{planned_ann}' on '{cls_name}.{fname}'.",
                            if_skipped="Type regressions slip past static verification.",
                        )
                    )

        for fn_name, spec in planned_funcs.items():
            contract_checks += 1
            actual = actual_funcs.get(fn_name)
            if actual is None:
                msg = f"Missing planned function '{fn_name}'"
                drifted_contracts.append(msg)
                has_must_fix_drift = True
                findings.append(
                    _make_finding(
                        severity="Must fix",
                        code="CONTRACT_SIGNATURE_DRIFT",
                        title=msg,
                        file_path=planned_py_sources[0],
                        line_no=1,
                        what_is=f"Section 2 defines function '{fn_name}' but it is missing on disk.",
                        problem="Missing planned function breaks consumers and tests.",
                        fix=f"Implement '{fn_name}({', '.join(spec['names'])})' per Section 2.",
                        if_skipped="Downstream imports will fail.",
                    )
                )
                continue

            if actual["arity"] != spec["arity"] or actual["names"] != spec["names"]:
                msg = (
                    f"Function '{fn_name}' signature drift: planned ({', '.join(spec['names'])}), "
                    f"got ({', '.join(actual['names'])})"
                )
                drifted_contracts.append(msg)
                has_must_fix_drift = True
                findings.append(
                    _make_finding(
                        severity="Must fix",
                        code="CONTRACT_SIGNATURE_DRIFT",
                        title=msg,
                        file_path=actual["file"],
                        line_no=actual["line"],
                        what_is=f"Function '{fn_name}' parameter names/arity diverged from Section 2.",
                        problem="Signature drift causes TypeError in callers adhering to the plan contract.",
                        fix=f"Align '{fn_name}' parameters with Section 2: ({', '.join(spec['names'])}).",
                        if_skipped="Callers relying on positional/keyword contract will crash.",
                    )
                )
            else:
                for pname, planned_ann in spec["annotations"].items():
                    actual_ann = actual["annotations"].get(pname, "")
                    if planned_ann and planned_ann != "Any" and actual_ann == "Any":
                        msg = f"Function '{fn_name}' param '{pname}' widened from '{planned_ann}' to 'Any'"
                        drifted_contracts.append(msg)
                        has_must_fix_drift = True
                        findings.append(
                            _make_finding(
                                severity="Must fix",
                                code="CONTRACT_SIGNATURE_DRIFT",
                                title=msg,
                                file_path=actual["file"],
                                line_no=actual["line"],
                                what_is=f"Parameter '{pname}' in '{fn_name}' was weakened to bare 'Any'.",
                                problem="Widening parameter annotations to Any undermines contract safety.",
                                fix=f"Restore type '{planned_ann}' on parameter '{pname}'.",
                                if_skipped="Invalid argument types pass unchecked.",
                            )
                        )

    # Layer 3: Section 4 Verification Matrix Realization
    missing_matrix, matrix_checks = _audit_verification_matrix(
        repo_root=repo_root,
        plan_content=plan_content,
        scoped_files=scoped_set,
        findings=findings,
    )

    total_checks = len(planned_files) + contract_checks + matrix_checks
    weighted_failures = (
        len(missing_planned)
        + len(undeleted)
        + len(drifted_contracts)
        + len(missing_matrix)
        + 0.5 * len(unplanned)
    )
    if total_checks == 0:
        alignment_pct = 100.0 if weighted_failures == 0 else 0.0
    else:
        alignment_pct = round(max(0.0, (1.0 - weighted_failures / total_checks) * 100.0), 1)

    passed = not (missing_planned or undeleted or missing_matrix or has_must_fix_drift)
    return PlanReconciliationDTO(
        plan_path=plan_path,
        milestone_scope=milestone_id,
        planned_files=tuple(planned_files),
        missing_planned_files=tuple(missing_planned),
        undeleted_files=tuple(undeleted),
        unplanned_modified_files=tuple(unplanned),
        drifted_contracts=tuple(drifted_contracts),
        missing_matrix_tests=tuple(missing_matrix),
        alignment_score_pct=alignment_pct,
        passed=passed,
    )


def _compute_live_test_tree_hash(
    repo_root: str,
    recorded_files: Dict[str, str],
    executed_tests: Sequence[str],
) -> Tuple[str, List[str]]:
    """Recomputes SHA-256 hashes of Red-certified test files and returns (tree_hash, tampered_paths)."""
    target_rels = sorted(recorded_files.keys()) if recorded_files else sorted(_norm_rel(t) for t in executed_tests if t)
    live_hashes: Dict[str, str] = {}
    tampered: List[str] = []

    for rel in target_rels:
        norm_rel = _norm_rel(rel)
        abs_p = os.path.join(repo_root, norm_rel)
        if not os.path.isfile(abs_p):
            tampered.append(norm_rel)
            continue
        try:
            with open(abs_p, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            live_hashes[rel] = digest
            if rel in recorded_files and not hmac.compare_digest(recorded_files[rel], digest):
                tampered.append(norm_rel)
        except OSError:
            tampered.append(norm_rel)

    if live_hashes:
        tree_body = "".join(f"{k}:{live_hashes[k]}\n" for k in sorted(live_hashes.keys()))
        tree_hash = hashlib.sha256(tree_body.encode("utf-8")).hexdigest()
    else:
        tree_hash = ""
    return tree_hash, tampered


def _extract_survived_mutants(payload: Dict[str, Any], label: str) -> List[str]:
    summaries: List[str] = []
    details = payload.get("target_details")
    if isinstance(details, dict):
        for target_file, t_info in details.items():
            if not isinstance(t_info, dict):
                continue
            for key in ("survived_mutants", "survivors"):
                items = t_info.get(key)
                if isinstance(items, list):
                    for m in items:
                        if isinstance(m, dict):
                            ln = m.get("line", "?")
                            op = m.get("operator", m.get("mutation", "mutant"))
                            desc = m.get("description", "")
                            summaries.append(f"[{label}] {target_file}:{ln} ({op}) {desc}".strip())
                        elif m:
                            summaries.append(f"[{label}] {target_file}: {m}")
    return summaries


def _audit_solo_provenance(
    repo_root: str,
    milestone_id: Optional[str],
    strict_solo: bool,
    findings: List[Dict[str, str]],
    planned_files: Optional[Set[str]] = None,
    changed_files: Optional[Sequence[str]] = None,
) -> Optional[SoloProvenanceAuditDTO]:
    solo_dir = os.path.join(repo_root, "reports", "solo_receipts")
    red_files: List[str] = []
    mut_files: List[str] = []

    legacy_red = os.path.join(repo_root, "reports", "tdd_red_receipt.json")
    legacy_mut = os.path.join(repo_root, "reports", "tdd_mutation_receipt.json")
    has_milestone = bool(milestone_id and milestone_id.strip())
    has_legacy_standalone = (not has_milestone) and (not planned_files) and (
        os.path.isfile(legacy_red) or os.path.isfile(legacy_mut)
    )

    if os.path.isdir(solo_dir) and not has_legacy_standalone:
        if has_milestone:
            safe_ms = re.sub(r"[^A-Za-z0-9_\-]", "_", str(milestone_id).strip())
            r_cand = os.path.join(solo_dir, f"{safe_ms}_red.json")
            m_cand = os.path.join(solo_dir, f"{safe_ms}_mutation.json")
            if os.path.isfile(r_cand):
                red_files.append(r_cand)
            if os.path.isfile(m_cand):
                mut_files.append(m_cand)
        else:
            red_files.extend(sorted(glob.glob(os.path.join(solo_dir, "*_red.json"))))
            mut_files.extend(sorted(glob.glob(os.path.join(solo_dir, "*_mutation.json"))))

    if not has_milestone:
        if os.path.isfile(legacy_red):
            red_files.append(legacy_red)
        if os.path.isfile(legacy_mut):
            mut_files.append(legacy_mut)

    changed_scope: Optional[Set[str]] = (
        {_norm_rel(str(cf)) for cf in changed_files if _norm_rel(str(cf))}
        if changed_files
        else None
    )
    scope_files: Optional[Set[str]] = (
        planned_files
        if planned_files
        else (changed_scope if (not has_milestone and not has_legacy_standalone) else None)
    )

    decisions_path = os.path.join(repo_root, "decisions.tsv")
    has_decisions = os.path.isfile(decisions_path)
    solo_detected = bool(red_files or mut_files or has_decisions)

    if not solo_detected:
        if not strict_solo:
            return None
        findings.append(
            _make_finding(
                severity="Must fix",
                code="MISSING_SOLO_RECEIPTS",
                title="Missing /solo forensic receipts under --strict-solo",
                file_path="reports/solo_receipts/",
                line_no=1,
                what_is="No /solo Red/Mutation receipts or decisions.tsv were found.",
                problem="--strict-solo requires cryptographically signed Red and Mutation evidence.",
                fix="Run agent-qa solo --red/--green/--mutation before requesting /review.",
                if_skipped="Unverified code bypasses /solo TDD and mutation gates.",
            )
        )
        return SoloProvenanceAuditDTO(
            solo_detected=False,
            milestones_checked=(),
            valid_red_receipts=(),
            tampered_or_invalid_receipts=(),
            post_red_tampered_tests=(),
            mutation_scores={},
            survived_mutant_summaries=(),
            decision_log_valid=False,
            provenance_score_pct=0.0,
            passed=False,
        )

    hmac_key = _get_receipt_hmac_key(repo_root)
    hub_fallback_key = (
        _get_receipt_hmac_key(_REPO_ROOT)
        if os.path.abspath(repo_root) != os.path.abspath(_REPO_ROOT)
        else None
    )
    milestones_checked: List[str] = []
    valid_reds: List[str] = []
    tampered_receipts: List[str] = []
    post_red_tampered: List[str] = []
    mutation_scores: Dict[str, float] = {}
    survived_summaries: List[str] = []
    total_checks = 0
    failed_checks = 0

    for rf in red_files:
        rel_rf = _norm_rel(os.path.relpath(rf, repo_root))
        try:
            with open(rf, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            if not isinstance(payload, dict):
                raise ValueError("Receipt JSON root must be an object.")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            total_checks += 1
            failed_checks += 1
            tampered_receipts.append(rel_rf)
            findings.append(
                _make_finding(
                    severity="Must fix",
                    code="CORRUPT_SOLO_RECEIPT",
                    title=f"Corrupt or unreadable /solo Red receipt: {rel_rf}",
                    file_path=rel_rf,
                    line_no=1,
                    what_is=f"Failed to parse JSON receipt '{rel_rf}': {exc}",
                    problem="Corrupted forensic receipt cannot be cryptographically verified.",
                    fix="Re-certify the milestone Red phase via agent-qa solo --red.",
                    if_skipped="TDD provenance cannot be trusted.",
                )
            )
            continue

        # Skip historical milestone receipts unrelated to the active plan or diff scope
        exec_tests_raw = payload.get("executed_tests") if isinstance(payload.get("executed_tests"), list) else []
        if scope_files and exec_tests_raw:
            norm_exec = {_norm_rel(str(t)) for t in exec_tests_raw}
            if not (norm_exec & scope_files):
                continue

        total_checks += 1
        ms_label = str(payload.get("milestone_id") or os.path.basename(rf).replace("_red.json", ""))
        if ms_label and ms_label not in milestones_checked:
            milestones_checked.append(ms_label)

        hmac_ok = _verify_red_receipt_hmac(payload, key=hmac_key) or (
            hub_fallback_key is not None and _verify_red_receipt_hmac(payload, key=hub_fallback_key)
        )
        if not hmac_ok:
            failed_checks += 1
            tampered_receipts.append(rel_rf)
            findings.append(
                _make_finding(
                    severity="Must fix",
                    code="TAMPERED_RED_RECEIPT",
                    title=f"Invalid or tampered Red receipt HMAC: {rel_rf}",
                    file_path=rel_rf,
                    line_no=1,
                    what_is=f"Constant-time HMAC-SHA256 verification failed on '{rel_rf}'.",
                    problem="The Red receipt was forged, altered manually, or signed with an unknown key.",
                    fix="Re-run agent-qa solo --red to generate an authentic signed receipt.",
                    if_skipped="Forged Red-phase proof undermines zero-trust auditing.",
                )
            )
            continue

        expected_tree = str(payload.get("test_tree_hash") or "")
        recorded_files = payload.get("test_files") if isinstance(payload.get("test_files"), dict) else {}
        executed_tests = exec_tests_raw
        if expected_tree or recorded_files:
            live_tree, tampered_paths = _compute_live_test_tree_hash(repo_root, recorded_files, executed_tests)
            tree_mismatch = bool(expected_tree) and not hmac.compare_digest(expected_tree, live_tree)
            if tampered_paths or tree_mismatch:
                failed_checks += 1
                flagged = tampered_paths or [_norm_rel(str(t)) for t in executed_tests] or [rel_rf]
                for tp in flagged:
                    if tp not in post_red_tampered:
                        post_red_tampered.append(tp)
                findings.append(
                    _make_finding(
                        severity="Must fix",
                        code="TEST_DRIFT_AFTER_RED",
                        title=f"Test file modified after Red certification ({ms_label}): {', '.join(flagged)}",
                        file_path=flagged[0],
                        line_no=1,
                        what_is=f"SHA-256 test_tree_hash drifted from signed Red receipt '{rel_rf}'.",
                        problem="Editing or weakening tests after --red without --recertify-red invalidates TDD proof.",
                        fix=f"Restore original Red assertions or re-certify via agent-qa solo --red --milestone {ms_label} --recertify-red.",
                        if_skipped="Weakened assertions could mask real implementation defects.",
                    )
                )
                continue

        valid_reds.append(rel_rf)

    for mf in mut_files:
        rel_mf = _norm_rel(os.path.relpath(mf, repo_root))
        try:
            with open(mf, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            if not isinstance(payload, dict):
                raise ValueError("Mutation receipt JSON root must be an object.")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            total_checks += 1
            failed_checks += 1
            tampered_receipts.append(rel_mf)
            findings.append(
                _make_finding(
                    severity="Must fix",
                    code="CORRUPT_SOLO_RECEIPT",
                    title=f"Corrupt /solo Mutation receipt: {rel_mf}",
                    file_path=rel_mf,
                    line_no=1,
                    what_is=f"Failed to parse mutation receipt '{rel_mf}': {exc}",
                    problem="Corrupted mutation receipt cannot verify assertion sensitivity.",
                    fix="Re-run agent-qa solo --mutation for this milestone.",
                    if_skipped="Mutation testing gate is bypassed.",
                )
            )
            continue

        ms_label = os.path.basename(mf).replace("_mutation.json", "").replace("tdd_mutation_receipt.json", "global")
        targets_eval = payload.get("targets_evaluated") if isinstance(payload.get("targets_evaluated"), list) else []
        if scope_files and targets_eval:
            norm_targets = {_norm_rel(str(t)) for t in targets_eval}
            if not (norm_targets & scope_files) and ms_label not in milestones_checked:
                continue

        total_checks += 1
        if ms_label and ms_label not in milestones_checked:
            milestones_checked.append(ms_label)

        status = str(payload.get("status", ""))
        score = float(payload.get("mutation_score", 0.0) or 0.0)
        threshold = float(payload.get("required_threshold", 80.0) or 80.0)
        passed_flag = bool(payload.get("passed", False))
        mutation_scores[ms_label] = score
        survived_summaries.extend(_extract_survived_mutants(payload, ms_label))

        if status != "AST_CONTRACT_VERIFIED" and (not passed_flag or score < threshold):
            failed_checks += 1
            findings.append(
                _make_finding(
                    severity="Must fix",
                    code="MUTATION_THRESHOLD_FAILED",
                    title=f"Mutation score below threshold for {ms_label}: {score:.1f}% < {threshold:.1f}%",
                    file_path=rel_mf,
                    line_no=1,
                    what_is=f"Mutation receipt '{rel_mf}' reported {score:.1f}% (required >= {threshold:.1f}%).",
                    problem="Weak test assertions allow injected code mutants to survive.",
                    fix="Add stronger assertions killing survived mutants and re-run --mutation.",
                    if_skipped="Regressions can slip through under-specified tests.",
                )
            )

    decision_log_valid = True
    if has_decisions:
        total_checks += 1
        d_report = audit_decision_log(decisions_path, strict=True)
        decision_log_valid = bool(d_report.get("valid", False))
        if not decision_log_valid:
            failed_checks += 1
            issues_str = "; ".join(d_report.get("issues", [])[:3])
            findings.append(
                _make_finding(
                    severity="Must fix" if strict_solo else "Should fix",
                    code="INVALID_DECISION_LOG",
                    title="Strict decisions.tsv audit failed",
                    file_path="decisions.tsv",
                    line_no=1,
                    what_is=f"decisions.tsv failed strict 6-column integrity check: {issues_str}",
                    problem="Incomplete decision trail weakens auditability of engineering choices.",
                    fix="Ensure all rows in decisions.tsv have non-empty ts/phase/decision/why/evidence/result.",
                    if_skipped="Execution rationale cannot be reconstructed during incident triage.",
                )
            )
    if strict_solo and not valid_reds:
        red_failure_codes = {
            "TAMPERED_RED_RECEIPT",
            "CORRUPT_SOLO_RECEIPT",
            "TEST_DRIFT_AFTER_RED",
            "MISSING_SOLO_RECEIPTS",
        }
        if not any(f.get("code") in red_failure_codes for f in findings):
            failed_checks += 1
            findings.append(
                _make_finding(
                    severity="Must fix",
                    code="MISSING_SOLO_RECEIPTS",
                    title="Missing valid signed /solo Red receipt under --strict-solo",
                    file_path="reports/solo_receipts/" if has_milestone else "reports/tdd_red_receipt.json",
                    line_no=1,
                    what_is="No valid signed Red receipt matched the active /solo review scope.",
                    problem="--strict-solo requires an authentic, untampered Red receipt for the current changes.",
                    fix=(
                        f"Run agent-qa solo --red --milestone {milestone_id} before requesting /review."
                        if has_milestone
                        else "Run agent-qa solo --red --test-cmd '<cmd>' (or pass --milestone <ID>) before requesting /review."
                    ),
                    if_skipped="Unverified code bypasses /solo TDD Red-First gates.",
                )
            )

    provenance_pct = (
        round(max(0.0, (1.0 - failed_checks / max(total_checks, 1)) * 100.0), 1)
        if total_checks > 0
        else 100.0
    )
    overall_ok = (
        not tampered_receipts
        and not post_red_tampered
        and failed_checks == 0
        and (not strict_solo or bool(valid_reds))
    )
    return SoloProvenanceAuditDTO(
        solo_detected=True,
        milestones_checked=tuple(milestones_checked),
        valid_red_receipts=tuple(valid_reds),
        tampered_or_invalid_receipts=tuple(tampered_receipts),
        post_red_tampered_tests=tuple(post_red_tampered),
        mutation_scores=mutation_scores,
        survived_mutant_summaries=tuple(survived_summaries),
        decision_log_valid=decision_log_valid,
        provenance_score_pct=provenance_pct,
        passed=overall_ok,
    )


def _extract_removed_def_signatures(diff_text: str) -> Dict[str, Dict[str, List[str]]]:
    """Extracts removed Python function parameter lists per file from unified diff."""
    removed_by_file: Dict[str, Dict[str, List[str]]] = {}
    current_file: Optional[str] = None
    file_re = re.compile(r"^diff --git a/(.+) b/(.+)$")
    def_re = re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(([^)]*)\)")

    for line in diff_text.splitlines():
        fm = file_re.match(line)
        if fm:
            current_file = _norm_rel(fm.group(2))
            continue
        if not current_file or not current_file.endswith(".py"):
            continue
        if line.startswith("-") and not line.startswith("---"):
            m_def = def_re.match(line[1:])
            if m_def:
                fn_name = m_def.group(1)
                raw_params = m_def.group(2)
                param_names = [
                    p.strip().lstrip("*").split(":")[0].split("=")[0].strip()
                    for p in raw_params.split(",")
                    if p.strip()
                ]
                param_names = [p for p in param_names if p and p not in ("self", "cls")]
                removed_by_file.setdefault(current_file, {})[fn_name] = param_names
    return removed_by_file


def _resolve_local_import_target(repo_root: str, src_rel: str, module_name: str, level: int = 0) -> Optional[str]:
    """Resolves a Python import module name to a local .py relative path under repo_root if present."""
    src_dir = os.path.dirname(src_rel)
    if level > 0:
        base_parts = [p for p in src_dir.split("/") if p]
        up = max(0, level - 1)
        if up > len(base_parts):
            return None
        prefix_parts = base_parts[: len(base_parts) - up]
        mod_parts = [p for p in (module_name or "").split(".") if p]
        candidates_parts = [prefix_parts + mod_parts]
    else:
        mod_parts = [p for p in (module_name or "").split(".") if p]
        if not mod_parts:
            return None
        candidates_parts = [mod_parts]
        if src_dir:
            candidates_parts.append([p for p in src_dir.split("/") if p] + mod_parts)

    for parts in candidates_parts:
        if not parts:
            continue
        rel_py = "/".join(parts) + ".py"
        if os.path.isfile(os.path.join(repo_root, rel_py)):
            return _norm_rel(rel_py)
    return None


def _extract_local_imports(repo_root: str, rel_path: str) -> List[str]:
    abs_p = os.path.join(repo_root, rel_path)
    if not os.path.isfile(abs_p):
        return []
    try:
        tree = ast.parse(open(abs_p, "r", encoding="utf-8", errors="replace").read(), filename=rel_path)
    except (OSError, SyntaxError):
        return []

    targets: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved = _resolve_local_import_target(repo_root, rel_path, alias.name, level=0)
                if resolved and resolved != rel_path and resolved not in targets:
                    targets.append(resolved)
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_local_import_target(repo_root, rel_path, node.module or "", level=node.level)
            if resolved and resolved != rel_path and resolved not in targets:
                targets.append(resolved)
            else:
                for alias in node.names:
                    sub_mod = f"{node.module}.{alias.name}" if node.module else alias.name
                    sub_res = _resolve_local_import_target(repo_root, rel_path, sub_mod, level=node.level)
                    if sub_res and sub_res != rel_path and sub_res not in targets:
                        targets.append(sub_res)
    return targets


def _check_call_against_spec(call: ast.Call, spec: Dict[str, Any]) -> Optional[str]:
    has_starred = any(isinstance(arg, ast.Starred) for arg in call.args)
    has_kw_unpack = any(kw.arg is None for kw in call.keywords)
    kw_names = [kw.arg for kw in call.keywords if kw.arg is not None]

    if not spec["has_kwarg"]:
        for kw in kw_names:
            if kw not in spec["accepted_kw"]:
                return f"unexpected keyword argument '{kw}'"

    if not has_starred and not spec["has_vararg"]:
        pos_count = len(call.args)
        if pos_count > spec["max_pos"]:
            return f"passes {pos_count} positional arg(s), max accepted is {spec['max_pos']}"
        if not has_kw_unpack:
            pos_supplied_by_kw = sum(1 for kw in kw_names if kw in spec["pos_names"])
            if pos_count + pos_supplied_by_kw < spec["required_pos"]:
                return f"passes {pos_count + pos_supplied_by_kw} arg(s), requires at least {spec['required_pos']}"

    if not has_kw_unpack:
        for req_kw in spec["required_kwonly"]:
            if req_kw not in kw_names:
                return f"missing required keyword-only argument '{req_kw}'"
    return None


def _audit_callers_and_cycles(
    repo_root: str,
    changed_files: List[str],
    diff_text: str,
    findings: List[Dict[str, str]],
) -> CallerCompatibilityDTO:
    py_changed = [_norm_rel(f) for f in changed_files if _norm_rel(f).endswith(".py")]
    modified_symbols: List[str] = []
    broken_call_sites: List[str] = []
    import_cycles: List[str] = []
    high_fan_in_targets: List[str] = []
    syntax_failed = False

    if not py_changed:
        return CallerCompatibilityDTO(
            modified_symbols=(),
            broken_call_sites=(),
            import_cycles=(),
            high_fan_in_targets=(),
            passed=True,
        )

    # 1. Parse live AST of changed Python files (explicit SyntaxError finding, never crash)
    live_funcs_by_file: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for rel in py_changed:
        abs_p = os.path.join(repo_root, rel)
        if not os.path.isfile(abs_p):
            continue
        try:
            source = open(abs_p, "r", encoding="utf-8", errors="replace").read()
            tree = ast.parse(source, filename=rel)
        except SyntaxError as exc:
            syntax_failed = True
            findings.append(
                _make_finding(
                    severity="Must fix",
                    code="SYNTAX_ERROR",
                    title=f"Python syntax error in {rel}",
                    file_path=rel,
                    line_no=exc.lineno or 1,
                    what_is=f"File '{rel}' failed ast.parse: {exc.msg}",
                    problem="Syntax errors break module imports and crash execution.",
                    fix="Fix the syntax error and re-run pytest.",
                    if_skipped="Code cannot compile or execute.",
                )
            )
            continue
        except OSError:
            continue

        file_funcs: Dict[str, Dict[str, Any]] = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                file_funcs[node.name] = _extract_func_params(node)
        live_funcs_by_file[rel] = file_funcs

    # 2. Identify changed function signatures via removed diff def lines vs live AST
    removed_defs = _extract_removed_def_signatures(diff_text)
    changed_sigs_by_file: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for rel, old_map in removed_defs.items():
        live_map = live_funcs_by_file.get(rel, {})
        for fn_name, old_params in old_map.items():
            live_spec = live_map.get(fn_name)
            if live_spec is not None and live_spec["names"] != old_params:
                changed_sigs_by_file.setdefault(rel, {})[fn_name] = live_spec
                if fn_name not in modified_symbols:
                    modified_symbols.append(fn_name)

    # 3. CallGraphIndexer lookup for downstream callers & high Fan-In alerts
    has_test_change = any(_is_test_file(f) for f in changed_files)
    graph = get_or_build_call_graph(repo_root)

    checked_callers = 0
    for rel in py_changed:
        if _is_test_file(rel):
            continue
        fan_in = graph.get_fan_in(rel)
        if fan_in >= HIGH_FAN_IN_THRESHOLD:
            high_fan_in_targets.append(f"{rel} (fan_in={fan_in})")
            if not has_test_change:
                findings.append(
                    _make_finding(
                        severity="Should fix",
                        code="HIGH_FAN_IN_TARGET",
                        title=f"High fan-in module modified without caller test coverage: {rel} (fan_in={fan_in})",
                        file_path=rel,
                        line_no=1,
                        what_is=f"'{rel}' is referenced by {fan_in} downstream files but no tests were updated.",
                        problem="High fan-in edits carry elevated blast-radius regression risk.",
                        fix="Add or run caller regression tests covering modified symbols.",
                        if_skipped="Downstream consumers may break silently.",
                    )
                )

        sig_map = changed_sigs_by_file.get(rel)
        if not sig_map:
            continue

        dependents = graph.get_dependents(rel)
        for dep in dependents:
            dep_rel = _norm_rel(dep)
            if dep_rel == rel or not dep_rel.endswith(".py"):
                continue
            if checked_callers >= MAX_CALLER_FILES:
                break
            checked_callers += 1
            abs_dep = os.path.join(repo_root, dep_rel)
            if not os.path.isfile(abs_dep):
                continue
            try:
                dep_tree = ast.parse(open(abs_dep, "r", encoding="utf-8", errors="replace").read(), filename=dep_rel)
            except (OSError, SyntaxError):
                continue

            for node in ast.walk(dep_tree):
                if not isinstance(node, ast.Call):
                    continue
                callee_name: Optional[str] = None
                if isinstance(node.func, ast.Name):
                    callee_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    callee_name = node.func.attr
                if callee_name and callee_name in sig_map:
                    err = _check_call_against_spec(node, sig_map[callee_name])
                    if err:
                        site = f"{dep_rel}:{node.lineno} -> {callee_name}() ({err})"
                        if site not in broken_call_sites:
                            broken_call_sites.append(site)
                            findings.append(
                                _make_finding(
                                    severity="Must fix",
                                    code="BROKEN_DOWNSTREAM_CALLER",
                                    title=f"Broken downstream caller at {dep_rel}:{node.lineno} calling {callee_name}()",
                                    file_path=dep_rel,
                                    line_no=node.lineno,
                                    what_is=f"Call to modified symbol '{callee_name}' fails new signature: {err}.",
                                    problem="Downstream caller outside the current diff will raise TypeError at runtime.",
                                    fix=f"Update call site at {dep_rel}:{node.lineno} or preserve backward-compatible parameter defaults.",
                                    if_skipped="Production caller will crash with TypeError.",
                                )
                            )

    # 4. Import Acyclicity check (BFS depth <= 2 from changed .py files)
    edges: List[List[str]] = []
    seen_edges: Set[Tuple[str, str]] = set()
    frontier: List[Tuple[str, int]] = [(rel, 0) for rel in py_changed]
    visited: Set[str] = set()
    while frontier:
        curr, depth = frontier.pop(0)
        if curr in visited or depth > 2:
            continue
        visited.add(curr)
        for target in _extract_local_imports(repo_root, curr):
            edge = (curr, target)
            if edge not in seen_edges:
                seen_edges.add(edge)
                edges.append([curr, target])
            if target not in visited and depth < 2:
                frontier.append((target, depth + 1))

    if edges:
        cycle_sol = DependencyCycleSolver.solve(edges)
        if cycle_sol.has_cycle:
            for cyc in cycle_sol.cycles_found:
                cyc_str = " -> ".join(cyc)
                if cyc_str not in import_cycles:
                    import_cycles.append(cyc_str)
                    findings.append(
                        _make_finding(
                            severity="Must fix",
                            code="CIRCULAR_IMPORT_DETECTED",
                            title=f"Circular import cycle detected: {cyc_str}",
                            file_path=cyc[0] if cyc else py_changed[0],
                            line_no=1,
                            what_is=f"Module dependency cycle found across touched files: {cyc_str}.",
                            problem="Circular imports trigger ImportError or partial module initialization at runtime.",
                            fix="Extract shared contracts/DTOs into a leaf module so dependencies remain strictly one-way.",
                            if_skipped="Module import order becomes fragile and fails unpredictably.",
                        )
                    )

    passed = not syntax_failed and not broken_call_sites and not import_cycles
    return CallerCompatibilityDTO(
        modified_symbols=tuple(modified_symbols),
        broken_call_sites=tuple(broken_call_sites),
        import_cycles=tuple(import_cycles),
        high_fan_in_targets=tuple(high_fan_in_targets),
        passed=passed,
    )


def audit_plan_and_solo_execution(
    repo_root: str,
    changed_files: List[str],
    diff_text: str,
    plan_path: Optional[str] = None,
    milestone_id: Optional[str] = None,
    strict_solo: bool = False,
) -> Tuple[Optional[PlanReconciliationDTO], Optional[SoloProvenanceAuditDTO], CallerCompatibilityDTO, List[Dict[str, str]]]:
    """Reconciles git diff & disk state against /super-plan contracts, /solo HMAC receipts, and CallGraph callers."""
    abs_root = os.path.abspath(repo_root)
    findings: List[Dict[str, str]] = []

    plan_dto: Optional[PlanReconciliationDTO] = None
    if plan_path and str(plan_path).strip():
        plan_dto = _reconcile_plan(
            repo_root=abs_root,
            changed_files=changed_files,
            plan_path=str(plan_path).strip(),
            milestone_id=milestone_id,
            findings=findings,
        )

    planned_set = set(plan_dto.planned_files) if plan_dto and plan_dto.planned_files else None
    solo_dto = _audit_solo_provenance(
        repo_root=abs_root,
        milestone_id=milestone_id,
        strict_solo=strict_solo,
        findings=findings,
        planned_files=planned_set,
        changed_files=changed_files,
    )

    caller_dto = _audit_callers_and_cycles(
        repo_root=abs_root,
        changed_files=changed_files,
        diff_text=diff_text,
        findings=findings,
    )

    return plan_dto, solo_dto, caller_dto, findings


def _extract_severity(finding: Any) -> str:
    if isinstance(finding, dict):
        return str(finding.get("severity", ""))
    return str(getattr(finding, "severity", ""))


def compute_review_verdict(findings: Sequence[Any], strict: bool = False) -> Tuple[str, bool, int]:
    """Returns (verdict, passed, exit_code) with strict escalation on Should fix items."""
    must_count = sum(1 for f in findings if _extract_severity(f) == "Must fix")
    should_count = sum(1 for f in findings if _extract_severity(f) == "Should fix")
    nice_count = sum(1 for f in findings if _extract_severity(f) == "Nice to have")

    if must_count > 0 or (strict and should_count > 0):
        return "CHANGES_REQUESTED", False, 1
    if should_count > 0 or nice_count > 0:
        return "APPROVED_WITH_NOTES", True, 0
    return "APPROVED", True, 0


def compute_review_receipt_hmac(payload: Dict[str, Any], key: Optional[bytes] = None) -> str:
    """Computes canonical HMAC-SHA256 over security-critical UnifiedReviewReceiptDTO fields."""
    secret = key if key is not None else _get_receipt_hmac_key()
    canonical = {
        "verdict": payload.get("verdict"),
        "passed": payload.get("passed"),
        "target_scope": payload.get("target_scope"),
        "files_changed": payload.get("files_changed"),
        "must_fix_count": payload.get("must_fix_count"),
        "should_fix_count": payload.get("should_fix_count"),
        "nice_to_have_count": payload.get("nice_to_have_count"),
        "plan_reconciliation": payload.get("plan_reconciliation"),
        "solo_provenance": payload.get("solo_provenance"),
        "caller_compatibility": payload.get("caller_compatibility"),
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret, raw, hashlib.sha256).hexdigest()


def verify_review_receipt_hmac(payload: Dict[str, Any], key: Optional[bytes] = None) -> bool:
    """Verifies code_review_receipt.json HMAC using constant-time comparison."""
    actual = payload.get("receipt_hmac")
    if not isinstance(actual, str) or len(actual) != 64:
        return False
    expected = compute_review_receipt_hmac(payload, key=key)
    return hmac.compare_digest(expected, actual)


def _atomic_write_json(path: str, payload: Dict[str, Any]) -> None:
    abs_path = os.path.abspath(path)
    parent = os.path.dirname(abs_path)
    os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".review_receipt_", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp_path, abs_path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:  # synapse-ignore: SWALLOWED_EXCEPTION
                pass
        raise


def sign_and_write_review_receipt(
    receipt_path: str,
    repo_root: str,
    verdict: str,
    passed: bool,
    target_scope: str,
    files_changed: int,
    must_fix_count: int,
    should_fix_count: int,
    nice_to_have_count: int,
    plan_reconciliation: Optional[PlanReconciliationDTO],
    solo_provenance: Optional[SoloProvenanceAuditDTO],
    caller_compatibility: CallerCompatibilityDTO,
) -> UnifiedReviewReceiptDTO:
    """Signs UnifiedReviewReceiptDTO with HMAC-SHA256 and atomically writes receipt_path."""
    payload: Dict[str, Any] = {
        "verdict": verdict,
        "passed": passed,
        "target_scope": target_scope,
        "files_changed": files_changed,
        "must_fix_count": must_fix_count,
        "should_fix_count": should_fix_count,
        "nice_to_have_count": nice_to_have_count,
        "plan_reconciliation": asdict(plan_reconciliation) if plan_reconciliation else None,
        "solo_provenance": asdict(solo_provenance) if solo_provenance else None,
        "caller_compatibility": asdict(caller_compatibility),
    }
    key = _get_receipt_hmac_key(repo_root)
    sig = compute_review_receipt_hmac(payload, key=key)
    payload["receipt_hmac"] = sig
    _atomic_write_json(receipt_path, payload)

    return UnifiedReviewReceiptDTO(
        verdict=verdict,
        passed=passed,
        target_scope=target_scope,
        files_changed=files_changed,
        must_fix_count=must_fix_count,
        should_fix_count=should_fix_count,
        nice_to_have_count=nice_to_have_count,
        plan_reconciliation=plan_reconciliation,
        solo_provenance=solo_provenance,
        caller_compatibility=caller_compatibility,
        receipt_hmac=sig,
    )
