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
import subprocess
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
    get_receipt_hmac_key_readonly,
    verify_mutation_receipt_hmac,
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


def _inspect_py_class_def(node: ast.ClassDef, rel: str = "") -> Dict[str, Any]:
    """Extracts dataclass immutability, typed fields, and methods from a ClassDef AST node."""
    is_frozen = _is_frozen_dataclass(node)
    fields: Dict[str, str] = {}
    methods: Dict[str, Dict[str, Any]] = {}
    for stmt in node.body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            fields[stmt.target.id] = _annotation_text(stmt.annotation)
            continue
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            m_info = _extract_func_params(stmt)
            if rel:
                m_info["file"] = rel
                m_info["line"] = stmt.lineno
            methods[stmt.name] = m_info
    info: Dict[str, Any] = {
        "is_frozen": is_frozen,
        "fields": fields,
        "methods": methods,
    }
    if rel:
        info["file"] = rel
        info["line"] = node.lineno
    return info


def _extract_python_contracts(section2_text: str) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Parses Python fenced code blocks in Section 2 into planned classes (with methods) and functions."""
    planned_classes: Dict[str, Dict[str, Any]] = {}
    planned_funcs: Dict[str, Dict[str, Any]] = {}

    code_blocks = re.findall(r"```(?:python|py)\s*\n(.*?)```", section2_text, re.DOTALL | re.IGNORECASE)
    for block in code_blocks:
        try:
            tree = ast.parse(block)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                planned_classes[node.name] = _inspect_py_class_def(node)
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                planned_funcs[node.name] = _extract_func_params(node)
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
        "returns": _annotation_text(node.returns),
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
                cls_info = _inspect_py_class_def(node, rel=rel)
                actual_classes[f"{rel}::{node.name}"] = cls_info
                if node.name not in actual_classes:
                    actual_classes[node.name] = cls_info
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                info = _extract_func_params(node)
                info["file"] = rel
                info["line"] = node.lineno
                actual_funcs[f"{rel}::{node.name}"] = info
                if node.name not in actual_funcs:
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


def _match_k_expression(
    k_expr: str,
    test_funcs: Sequence[ast.FunctionDef | ast.AsyncFunctionDef],
    class_map: Dict[int, str],
) -> Tuple[List[ast.FunctionDef | ast.AsyncFunctionDef], List[str]]:
    """Evaluates pytest -k expressions supporting AND/OR clauses and TestCase class names."""
    cleaned = k_expr.strip().strip("()")
    or_groups = [g.strip() for g in re.split(r"\s+or\s+", cleaned) if g.strip()]
    matched_ids: Set[int] = set()
    matched_funcs: List[ast.FunctionDef | ast.AsyncFunctionDef] = []
    missing_tokens: List[str] = []

    def _matches_tok(fn: ast.FunctionDef | ast.AsyncFunctionDef, tok: str) -> bool:
        cls_name = class_map.get(id(fn), "")
        return tok in fn.name or (cls_name and tok in cls_name)

    for grp in or_groups:
        and_tokens = [
            t.strip().strip("()")
            for t in re.split(r"\s+and\s+", grp)
            if t.strip() and not t.strip().startswith("not ")
        ]
        if not and_tokens:
            continue
        grp_missing: List[str] = []
        grp_matched: List[ast.FunctionDef | ast.AsyncFunctionDef] = []
        for tok in and_tokens:
            hits = [fn for fn in test_funcs if _matches_tok(fn, tok)]
            if not hits:
                grp_missing.append(tok)
            else:
                grp_matched.extend(hits)
        for fn in grp_matched:
            if id(fn) not in matched_ids:
                matched_ids.add(id(fn))
                matched_funcs.append(fn)
        if grp_missing:
            missing_tokens.extend(grp_missing)

    if matched_funcs and len(or_groups) > 1:
        # In an OR expression, if at least one branch satisfied all its AND clauses, report no missing tokens
        missing_tokens = []
    return matched_funcs, list(dict.fromkeys(missing_tokens))


def _collect_py_test_functions(
    tree: ast.AST,
) -> Tuple[List[ast.FunctionDef | ast.AsyncFunctionDef], Dict[int, str]]:
    """Collects top-level and TestCase-nested test_* functions alongside class_map."""
    test_funcs: List[ast.FunctionDef | ast.AsyncFunctionDef] = []
    class_map: Dict[int, str] = {}
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            test_funcs.append(node)
            continue
        if not isinstance(node, ast.ClassDef):
            continue
        for sub in node.body:
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name.startswith("test_"):
                test_funcs.append(sub)
                class_map[id(sub)] = node.name
    return test_funcs, class_map


def _audit_matrix_py_file(
    repo_root: str,
    norm_tf: str,
    k_expr: Optional[str],
    missing_tests: List[str],
    findings: List[Dict[str, str]],
) -> None:
    """Verifies existence, -k match, and non-tautological assertions for one Verification Matrix test file."""
    abs_tf = os.path.join(repo_root, norm_tf)
    if not os.path.isfile(abs_tf):
        missing_tests.append(f"{norm_tf} (missing test file)")
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
        return

    try:
        source = open(abs_tf, "r", encoding="utf-8", errors="replace").read()
        tree = ast.parse(source, filename=norm_tf)
    except (OSError, SyntaxError) as exc:
        missing_tests.append(f"{norm_tf} (unparseable: {exc})")
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
        return

    test_funcs, class_map = _collect_py_test_functions(tree)
    target_funcs = test_funcs
    if k_expr:
        matched_funcs, missing_toks = _match_k_expression(k_expr, test_funcs, class_map)
        if missing_toks or not matched_funcs:
            miss_label = ", ".join(missing_toks) if missing_toks else k_expr
            missing_tests.append(f"{norm_tf}::{miss_label} (missing test function)")
            findings.append(
                _make_finding(
                    severity="Must fix",
                    code="UNVERIFIED_MATRIX_SCENARIOS",
                    title=f"Planned Verification Matrix test missing: {miss_label}",
                    file_path=norm_tf,
                    line_no=1,
                    what_is=f"Section 4 requires test matching '-k {k_expr}' in {norm_tf}.",
                    problem="The planned exam scenario is missing from the test suite.",
                    fix=f"Implement a non-tautological test matching '{miss_label}' in {norm_tf}.",
                    if_skipped="A planned requirement has no regression coverage.",
                )
            )
        target_funcs = matched_funcs

    for fn in target_funcs:
        fn_src = ast.get_source_segment(source, fn) or ""
        taut_findings = AstTautologyAnalyzer(flag_true_tautologies=True).analyze_source(fn_src) if fn_src else []
        if taut_findings or not _function_has_real_assertion(fn):
            reason = taut_findings[0][2] if taut_findings else "zero assertions in test body"
            missing_tests.append(f"{norm_tf}::{fn.name} ({reason})")
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


def _audit_verification_matrix(
    repo_root: str,
    plan_content: str,
    scoped_files: Optional[Set[str]],
    findings: List[Dict[str, str]],
) -> Tuple[List[str], int]:
    """Verifies Section 4 Verification Matrix test files (Python & JS/TS), -k expressions, and non-tautological assertions."""
    section4 = _extract_section(plan_content, 4)
    missing_tests: List[str] = []
    checks_count = 0
    js_test_re = re.compile(r"([A-Za-z0-9_.\-/]+\.(?:spec|test)\.(?:ts|js|tsx|jsx))")
    py_test_re = re.compile(r"((?:tests/[A-Za-z0-9_.\-/]+|test_[A-Za-z0-9_.\-/]+)\.py)")

    for line in section4.splitlines():
        if "|" not in line or re.match(r"^\s*\|[\s\-:|]+\|\s*$", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        cmd_targets = [
            c for c in reversed(cells)
            if (py_test_re.search(c) or js_test_re.search(c))
            and re.search(r"\b(?:pytest|python3?|npx|npm|jest|vitest)\b", c, re.IGNORECASE)
        ]
        scan_target = cmd_targets[0] if cmd_targets else line
        py_files = py_test_re.findall(scan_target)
        js_files = js_test_re.findall(scan_target)
        if not py_files and not js_files:
            continue
        k_match = re.search(r'-k\s+["\']([^"\']+)["\']', scan_target)
        k_expr = k_match.group(1).strip() if k_match else None

        for jf in dict.fromkeys(js_files):
            norm_jf = _norm_rel(jf)
            if scoped_files is not None and norm_jf not in scoped_files:
                continue
            checks_count += 1
            abs_jf = os.path.join(repo_root, norm_jf)
            if not os.path.isfile(abs_jf):
                desc = f"{norm_jf} (missing spec file)"
                missing_tests.append(desc)
                findings.append(
                    _make_finding(
                        severity="Must fix",
                        code="UNVERIFIED_MATRIX_SCENARIOS",
                        title=f"Verification Matrix spec file missing: {norm_jf}",
                        file_path=norm_jf,
                        line_no=1,
                        what_is="A JS/TS test spec required by Section 4 Verification Matrix does not exist.",
                        problem="Planned acceptance scenarios have zero automated verification.",
                        fix=f"Create {norm_jf} implementing the planned verification scenarios.",
                        if_skipped="Planned contract guarantees ship untested.",
                    )
                )

        for tf in dict.fromkeys(py_files):
            norm_tf = _norm_rel(tf)
            if scoped_files is not None and norm_tf not in scoped_files:
                continue
            checks_count += 1
            _audit_matrix_py_file(repo_root, norm_tf, k_expr, missing_tests, findings)

    return missing_tests, checks_count


def _reconcile_class_fields_and_methods(
    cls_name: str,
    spec: Dict[str, Any],
    actual: Dict[str, Any],
    drifted_contracts: List[str],
    findings: List[Dict[str, str]],
    compare_func_fn: Any,
) -> Tuple[bool, int]:
    """Validates frozen status, typed DTO fields, and methods on one planned class; returns (must_fix, method_checks)."""
    has_must_fix = False
    method_checks = 0
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
            has_must_fix = True
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
            continue
        if planned_ann and planned_ann != "Any" and actual_ann == "Any":
            msg = f"DTO '{cls_name}.{fname}' type widened from '{planned_ann}' to 'Any'"
            drifted_contracts.append(msg)
            has_must_fix = True
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

    for m_name, m_spec in spec.get("methods", {}).items():
        method_checks += 1
        actual_m = actual.get("methods", {}).get(m_name)
        if actual_m is None:
            msg = f"Missing planned method '{cls_name}.{m_name}'"
            drifted_contracts.append(msg)
            has_must_fix = True
            findings.append(
                _make_finding(
                    severity="Must fix",
                    code="CONTRACT_SIGNATURE_DRIFT",
                    title=msg,
                    file_path=actual["file"],
                    line_no=actual["line"],
                    what_is=f"Section 2 defines method '{cls_name}.{m_name}' but it is missing on disk.",
                    problem="Missing class method breaks consumers adhering to Section 2.",
                    fix=f"Implement '{m_name}' on '{cls_name}' per Section 2.",
                    if_skipped="AttributeError at runtime.",
                )
            )
            continue
        compare_func_fn(f"Method '{cls_name}.{m_name}'", m_spec, actual_m)
    return has_must_fix, method_checks


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
    is_milestone_scoped = bool(milestone_id and milestone_id.strip() and len(dag.nodes) > 1)
    milestone_block_text = ""
    if is_milestone_scoped:
        ms_key = milestone_id.strip()
        m_blk = re.search(
            rf"(###?\s*[^\n]*\b{re.escape(ms_key)}\b.*?)(?=(?:###?\s*(?:Milestone\s*\d+|Node\s*[A-Za-z0-9]+))|(?:\n##+\s+)|\Z)",
            plan_content,
            re.DOTALL | re.IGNORECASE,
        )
        milestone_block_text = m_blk.group(1) if m_blk else ""

    def _compare_func_contract(
        label: str,
        spec: Dict[str, Any],
        actual: Dict[str, Any],
    ) -> None:
        nonlocal has_must_fix_drift
        if actual["arity"] != spec["arity"] or actual["names"] != spec["names"]:
            msg = (
                f"{label} signature drift: planned ({', '.join(spec['names'])}), "
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
                    what_is=f"{label} parameter names/arity diverged from Section 2.",
                    problem="Signature drift causes TypeError in callers adhering to the plan contract.",
                    fix=f"Align {label} parameters with Section 2: ({', '.join(spec['names'])}).",
                    if_skipped="Callers relying on positional/keyword contract will crash.",
                )
            )
            return

        for pname, planned_ann in spec["annotations"].items():
            actual_ann = actual["annotations"].get(pname, "")
            if planned_ann and planned_ann != "Any" and actual_ann == "Any":
                msg = f"{label} param '{pname}' widened from '{planned_ann}' to 'Any'"
                drifted_contracts.append(msg)
                has_must_fix_drift = True
                findings.append(
                    _make_finding(
                        severity="Must fix",
                        code="CONTRACT_SIGNATURE_DRIFT",
                        title=msg,
                        file_path=actual["file"],
                        line_no=actual["line"],
                        what_is=f"Parameter '{pname}' in {label} was weakened to bare 'Any'.",
                        problem="Widening parameter annotations to Any undermines contract safety.",
                        fix=f"Restore type '{planned_ann}' on parameter '{pname}'.",
                        if_skipped="Invalid argument types pass unchecked.",
                    )
                )

        planned_ret = spec.get("returns", "")
        actual_ret = actual.get("returns", "")
        if planned_ret and planned_ret != "Any" and actual_ret == "Any":
            msg = f"{label} return type widened from '{planned_ret}' to 'Any'"
            drifted_contracts.append(msg)
            has_must_fix_drift = True
            findings.append(
                _make_finding(
                    severity="Must fix",
                    code="CONTRACT_SIGNATURE_DRIFT",
                    title=msg,
                    file_path=actual["file"],
                    line_no=actual["line"],
                    what_is=f"Return annotation of {label} was weakened to bare 'Any'.",
                    problem="Widening return types to Any breaks static type contracts.",
                    fix=f"Restore return type '{planned_ret}' on {label}.",
                    if_skipped="Downstream callers receive untyped values.",
                )
            )

    if planned_py_sources and (planned_classes or planned_funcs):
        actual_classes, actual_funcs = _collect_actual_python_symbols(repo_root, planned_py_sources)
        for cls_name, spec in planned_classes.items():
            actual = actual_classes.get(cls_name)
            if actual is None and is_milestone_scoped and cls_name not in milestone_block_text:
                continue
            contract_checks += 1
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

            cls_must_fix, m_checks = _reconcile_class_fields_and_methods(
                cls_name=cls_name,
                spec=spec,
                actual=actual,
                drifted_contracts=drifted_contracts,
                findings=findings,
                compare_func_fn=_compare_func_contract,
            )
            contract_checks += m_checks
            if cls_must_fix:
                has_must_fix_drift = True

        for fn_name, spec in planned_funcs.items():
            actual = actual_funcs.get(fn_name)
            if actual is None and is_milestone_scoped and fn_name not in milestone_block_text:
                continue
            contract_checks += 1
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

            _compare_func_contract(f"Function '{fn_name}'", spec, actual)

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


_MUTATION_CODE_EXTS = (".py", ".ts", ".js", ".java", ".groovy")


def _verify_red_receipt_payload(
    repo_root: str,
    rel_rf: str,
    payload: Dict[str, Any],
    hmac_key: Optional[bytes],
    hub_fallback_key: Optional[bytes],
    ms_label: str,
    executed_tests: List[Any],
    tampered_receipts: List[str],
    post_red_tampered: List[str],
    findings: List[Dict[str, str]],
) -> bool:
    """Verifies HMAC, CERTIFIED_RED status, and SHA-256 test_tree_hash for one Red receipt."""
    hmac_ok = (hmac_key is not None and _verify_red_receipt_hmac(payload, key=hmac_key)) or (
        hub_fallback_key is not None and _verify_red_receipt_hmac(payload, key=hub_fallback_key)
    )
    if not hmac_ok:
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
        return False

    red_status = str(payload.get("status") or "")
    expected_tree = str(payload.get("test_tree_hash") or "")
    recorded_files = payload.get("test_files") if isinstance(payload.get("test_files"), dict) else {}
    if red_status != "CERTIFIED_RED" or not expected_tree:
        tampered_receipts.append(rel_rf)
        findings.append(
            _make_finding(
                severity="Must fix",
                code="INVALID_RED_RECEIPT",
                title=f"Invalid Red receipt status or missing test_tree_hash: {rel_rf}",
                file_path=rel_rf,
                line_no=1,
                what_is=f"Red receipt '{rel_rf}' has status='{red_status}' and test_tree_hash='{expected_tree}'.",
                problem="Red receipts without CERTIFIED_RED status and SHA-256 test_tree_hash cannot certify TDD.",
                fix="Re-run agent-qa solo --red to generate a valid CERTIFIED_RED receipt.",
                if_skipped="Unverified or failed Red states could mask missing TDD coverage.",
            )
        )
        return False

    live_tree, tampered_paths = _compute_live_test_tree_hash(repo_root, recorded_files, executed_tests)
    tree_mismatch = not hmac.compare_digest(expected_tree, live_tree)
    if tampered_paths or tree_mismatch:
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
        return False
    return True


def _audit_solo_provenance(
    repo_root: str,
    milestone_id: Optional[str],
    strict_solo: bool,
    findings: List[Dict[str, str]],
    planned_files: Optional[Set[str]] = None,
    changed_files: Optional[Sequence[str]] = None,
    has_plan: bool = False,
    require_mutation_receipt: bool = True,
    decision_log_path: Optional[str] = None,
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

    decisions_path = (
        decision_log_path
        if (decision_log_path and os.path.isabs(decision_log_path))
        else os.path.join(repo_root, decision_log_path or "decisions.tsv")
    )
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

    hmac_key = get_receipt_hmac_key_readonly(repo_root)
    hub_fallback_key = (
        get_receipt_hmac_key_readonly(_REPO_ROOT)
        if os.path.abspath(repo_root) != os.path.abspath(_REPO_ROOT)
        else None
    )
    milestones_checked: List[str] = []
    valid_reds: List[str] = []
    valid_muts: List[str] = []
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

        if not _verify_red_receipt_payload(
            repo_root=repo_root,
            rel_rf=rel_rf,
            payload=payload,
            hmac_key=hmac_key,
            hub_fallback_key=hub_fallback_key,
            ms_label=ms_label,
            executed_tests=exec_tests_raw,
            tampered_receipts=tampered_receipts,
            post_red_tampered=post_red_tampered,
            findings=findings,
        ):
            failed_checks += 1
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

        if "receipt_hmac" in payload:
            mut_hmac_ok = (
                hmac_key is not None and verify_mutation_receipt_hmac(payload, key=hmac_key, repo_root=repo_root)
            ) or (
                hub_fallback_key is not None
                and verify_mutation_receipt_hmac(payload, key=hub_fallback_key, repo_root=repo_root)
            )
            if not mut_hmac_ok:
                failed_checks += 1
                tampered_receipts.append(rel_mf)
                findings.append(
                    _make_finding(
                        severity="Must fix",
                        code="TAMPERED_MUTATION_RECEIPT",
                        title=f"Invalid or tampered Mutation receipt HMAC: {rel_mf}",
                        file_path=rel_mf,
                        line_no=1,
                        what_is=f"Constant-time HMAC-SHA256 verification failed on '{rel_mf}'.",
                        problem="The Mutation receipt was altered manually or signed with an unknown key.",
                        fix="Re-run agent-qa solo --mutation to generate an authentic signed receipt.",
                        if_skipped="Forged mutation scores hide weak test assertions.",
                    )
                )
                continue

        status = str(payload.get("status", ""))
        score = float(payload.get("mutation_score", 0.0) or 0.0)
        threshold = float(payload.get("required_threshold", 80.0) or 80.0)
        total_gen = int(payload.get("total_generated", payload.get("total_mutants", 0)) or 0)
        passed_flag = bool(payload.get("passed", False))
        mutation_scores[ms_label] = score
        survived_summaries.extend(_extract_survived_mutants(payload, ms_label))

        valid_ast_waiver = status == "AST_CONTRACT_VERIFIED" and total_gen == 0
        if not valid_ast_waiver and (not passed_flag or score < threshold):
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
        else:
            valid_muts.append(rel_mf)

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
    elif strict_solo and has_plan:
        total_checks += 1
        failed_checks += 1
        decision_log_valid = False
        findings.append(
            _make_finding(
                severity="Must fix",
                code="MISSING_DECISION_LOG",
                title="Missing decisions.tsv audit trail under --plan --strict-solo",
                file_path="decisions.tsv",
                line_no=1,
                what_is="Plan-driven --strict-solo review requires decisions.tsv, but none exists on disk.",
                problem="Without decisions.tsv, milestone execution rationale and verification gates are unrecorded.",
                fix="Execute the plan via agent-qa solo --from-plan or log milestone decisions in decisions.tsv.",
                if_skipped="Audit trail cannot be reconstructed for plan execution.",
            )
        )

    if strict_solo and not valid_reds:
        red_failure_codes = {
            "TAMPERED_RED_RECEIPT",
            "INVALID_RED_RECEIPT",
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

    if strict_solo and require_mutation_receipt and not valid_muts:
        mut_failure_codes = {
            "MUTATION_THRESHOLD_FAILED",
            "TAMPERED_MUTATION_RECEIPT",
            "CORRUPT_SOLO_RECEIPT",
            "MISSING_SOLO_RECEIPTS",
            "MISSING_MUTATION_RECEIPT",
        }
        active_sources = [
            f
            for f in (scope_files or changed_scope or ())
            if f.endswith(_MUTATION_CODE_EXTS) and not _is_test_file(f)
        ]
        if active_sources and not any(f.get("code") in mut_failure_codes for f in findings):
            failed_checks += 1
            findings.append(
                _make_finding(
                    severity="Must fix",
                    code="MISSING_MUTATION_RECEIPT",
                    title="Missing valid /solo Mutation receipt under --strict-solo",
                    file_path="reports/solo_receipts/" if has_milestone else "reports/tdd_mutation_receipt.json",
                    line_no=1,
                    what_is="Non-test source changes lack a matching Mutation receipt under --strict-solo.",
                    problem="--strict-solo requires live mutation verification (>= 80%) on changed source files.",
                    fix="Run agent-qa solo --mutation --target <source.py> --test-cmd '<cmd>' before /review.",
                    if_skipped="Weak assertions in tests remain undetected.",
                )
            )

    provenance_pct = (
        round(max(0.0, (1.0 - failed_checks / max(total_checks, 1)) * 100.0), 1)
        if total_checks > 0
        else 100.0
    )
    mut_required_missing = any(f.get("code") == "MISSING_MUTATION_RECEIPT" for f in findings)
    overall_ok = (
        not tampered_receipts
        and not post_red_tampered
        and failed_checks == 0
        and not mut_required_missing
        and decision_log_valid
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


def _parse_def_header_params(header_lines: List[str]) -> Optional[Tuple[str, List[str]]]:
    """Parses a single-line or multi-line Python def header into (fn_name, param_names)."""
    raw_src = "\n".join(header_lines).strip()
    if ":" not in raw_src:
        raw_src = raw_src.rstrip() + ":"
    try:
        tree = ast.parse(raw_src + "\n    pass")
    except SyntaxError:
        m = re.match(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\((.*)\)", " ".join(header_lines), re.DOTALL)
        if not m:
            return None
        fn_name = m.group(1)
        params = [
            p.strip().lstrip("*").split(":")[0].split("=")[0].strip()
            for p in m.group(2).split(",")
            if p.strip()
        ]
        return fn_name, [p for p in params if p and p not in ("self", "cls")]

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            info = _extract_func_params(node)
            return node.name, info["names"]
    return None


def _extract_removed_def_signatures(
    diff_text: str,
    repo_root: Optional[str] = None,
) -> Dict[str, Dict[str, List[str]]]:
    """Extracts prior Python function parameter lists from git HEAD and multi-line diff headers."""
    removed_by_file: Dict[str, Dict[str, List[str]]] = {}
    current_file: Optional[str] = None
    file_re = re.compile(r'^diff --git (?:"a/.+?"|a/\S+) ("b/.+?"|b/\S+)$')
    def_start_re = re.compile(r"^\s*(?:async\s+)?def\s+[A-Za-z_]\w*\s*\(")

    # 1. Multi-line paren-balanced parser across diff hunks (handles synthetic & live diffs)
    collecting = False
    has_removed_line = False
    buf: List[str] = []
    paren_depth = 0

    def _flush_buf() -> None:
        nonlocal collecting, has_removed_line, buf, paren_depth
        if collecting and has_removed_line and current_file and buf:
            parsed = _parse_def_header_params(buf)
            if parsed:
                fn_name, pnames = parsed
                removed_by_file.setdefault(current_file, {})[fn_name] = pnames
        collecting = False
        has_removed_line = False
        buf = []
        paren_depth = 0

    for line in diff_text.splitlines():
        fm = file_re.match(line)
        if fm:
            _flush_buf()
            raw_b = fm.group(1).strip()
            if len(raw_b) >= 2 and raw_b.startswith('"') and raw_b.endswith('"'):
                raw_b = raw_b[1:-1]
            current_file = _norm_rel(raw_b[2:] if raw_b.startswith("b/") else raw_b)
            continue
        if not current_file or not current_file.endswith(".py"):
            continue
        if line.startswith("@@"):
            _flush_buf()
            continue
        if line.startswith("+") and not line.startswith("+++"):
            # Added lines belong to the new signature, not the old one
            continue
        if line.startswith("\\"):
            continue
        if line.startswith("---"):
            continue

        is_removed = line.startswith("-")
        code = line[1:] if is_removed or line.startswith(" ") else line

        if not collecting:
            if def_start_re.match(code):
                collecting = True
                has_removed_line = is_removed
                buf = [code.lstrip()]
                paren_depth = code.count("(") - code.count(")")
                if paren_depth <= 0 and ")" in code:
                    _flush_buf()
        else:
            if is_removed:
                has_removed_line = True
            buf.append(code.strip())
            paren_depth += code.count("(") - code.count(")")
            if paren_depth <= 0:
                _flush_buf()
    _flush_buf()

    # 2. Enrich from git HEAD AST when available (handles edits that didn't touch the def line directly)
    if repo_root and os.path.isdir(os.path.join(repo_root, ".git")):
        for rel, def_map in removed_by_file.items():
            _enrich_removed_defs_from_git_head(repo_root, rel, def_map)
    return removed_by_file


def _enrich_removed_defs_from_git_head(
    repo_root: str,
    rel: str,
    def_map: Dict[str, List[str]],
) -> None:
    """Updates parsed removed signatures using AST parameter lists from git HEAD:<rel> when available."""
    try:
        res = subprocess.run(
            ["git", "show", f"HEAD:{rel}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=5.0,
        )
        if res.returncode != 0 or not res.stdout:
            return
        tree = ast.parse(res.stdout, filename=rel)
    except (OSError, SyntaxError, subprocess.SubprocessError):
        return
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in def_map:
            def_map[node.name] = _extract_func_params(node)["names"]


def _resolve_local_import_target(repo_root: str, src_rel: str, module_name: str, level: int = 0) -> Optional[str]:
    """Resolves a Python import module name to a local .py or __init__.py relative path under repo_root."""
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
        rel_init = "/".join(parts + ["__init__.py"])
        if os.path.isfile(os.path.join(repo_root, rel_init)):
            return _norm_rel(rel_init)
    return None


def _is_optional_import_try(node: ast.AST) -> bool:
    """Returns True if an ast.Try handles ImportError/ModuleNotFoundError/Exception around optional imports."""
    if not isinstance(node, ast.Try):
        return False
    for handler in node.handlers:
        if handler.type is None:
            return True
        if isinstance(handler.type, ast.Name) and handler.type.id in ("ImportError", "ModuleNotFoundError", "Exception"):
            return True
        if isinstance(handler.type, ast.Tuple):
            for elt in handler.type.elts:
                if isinstance(elt, ast.Name) and elt.id in ("ImportError", "ModuleNotFoundError", "Exception"):
                    return True
    return False


def _extract_local_imports(repo_root: str, rel_path: str) -> List[str]:
    abs_p = os.path.join(repo_root, rel_path)
    if not os.path.isfile(abs_p):
        return []
    try:
        tree = ast.parse(open(abs_p, "r", encoding="utf-8", errors="replace").read(), filename=rel_path)
    except (OSError, SyntaxError):
        return []

    targets: List[str] = []

    def _visit(node: ast.AST) -> None:
        if _is_optional_import_try(node):
            return
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved = _resolve_local_import_target(repo_root, rel_path, alias.name, level=0)
                if resolved and resolved != rel_path and resolved not in targets:
                    targets.append(resolved)
            return
        if isinstance(node, ast.ImportFrom):
            resolved = _resolve_local_import_target(repo_root, rel_path, node.module or "", level=node.level)
            if resolved and resolved != rel_path and resolved not in targets:
                targets.append(resolved)
            else:
                for alias in node.names:
                    sub_mod = f"{node.module}.{alias.name}" if node.module else alias.name
                    sub_res = _resolve_local_import_target(repo_root, rel_path, sub_mod, level=node.level)
                    if sub_res and sub_res != rel_path and sub_res not in targets:
                        targets.append(sub_res)
            return
        for child in ast.iter_child_nodes(node):
            _visit(child)

    _visit(tree)
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


def _collect_import_from_bindings(
    repo_root: str,
    dep_rel: str,
    node: ast.ImportFrom,
    norm_target: str,
    sym_names: Set[str],
    mod_aliases: Set[str],
) -> bool:
    """Collects imported symbols/aliases for one ImportFrom node; returns True on wildcard import."""
    resolved = _resolve_local_import_target(repo_root, dep_rel, node.module or "", level=node.level)
    if resolved == norm_target:
        wildcard = False
        for alias in node.names:
            if alias.name == "*":
                wildcard = True
            else:
                sym_names.add(alias.asname or alias.name)
        return wildcard

    for alias in node.names:
        sub_mod = f"{node.module}.{alias.name}" if node.module else alias.name
        if _resolve_local_import_target(repo_root, dep_rel, sub_mod, level=node.level) == norm_target:
            mod_aliases.add(alias.asname or alias.name)
    return False


def _collect_imported_bindings_for_target(
    repo_root: str,
    dep_rel: str,
    dep_tree: ast.AST,
    target_rel: str,
) -> Tuple[Set[str], Set[str], bool]:
    """Returns (imported_symbol_names, imported_module_aliases, imports_star_or_module) for target_rel."""
    sym_names: Set[str] = set()
    mod_aliases: Set[str] = set()
    wildcard = False
    norm_target = _norm_rel(target_rel)

    for node in ast.walk(dep_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _resolve_local_import_target(repo_root, dep_rel, alias.name, level=0) == norm_target:
                    mod_aliases.add(alias.asname or alias.name)
            continue
        if isinstance(node, ast.ImportFrom):
            if _collect_import_from_bindings(repo_root, dep_rel, node, norm_target, sym_names, mod_aliases):
                wildcard = True
    return sym_names, mod_aliases, wildcard


def _scan_dependent_caller_ast(
    repo_root: str,
    dep_rel: str,
    target_rel: str,
    sig_map: Dict[str, Dict[str, Any]],
    broken_call_sites: List[str],
    findings: List[Dict[str, str]],
) -> None:
    """Scans one downstream Python file's AST for broken call sites targeting sig_map."""
    abs_dep = os.path.join(repo_root, dep_rel)
    if not os.path.isfile(abs_dep):
        return
    try:
        dep_tree = ast.parse(open(abs_dep, "r", encoding="utf-8", errors="replace").read(), filename=dep_rel)
    except (OSError, SyntaxError):
        return

    imported_syms, mod_aliases, has_wildcard = _collect_imported_bindings_for_target(
        repo_root, dep_rel, dep_tree, target_rel
    )
    has_binding_info = bool(imported_syms or mod_aliases or has_wildcard)
    for node in ast.walk(dep_tree):
        if not isinstance(node, ast.Call):
            continue
        callee_name: Optional[str] = None
        if isinstance(node.func, ast.Name):
            if has_binding_info and not has_wildcard and node.func.id not in imported_syms:
                continue
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            recv = ast.unparse(node.func.value) if hasattr(ast, "unparse") else ""
            if has_binding_info and recv not in mod_aliases:
                continue
            if not has_binding_info and isinstance(node.func.value, ast.Call):
                continue
            callee_name = node.func.attr
        if not callee_name or callee_name not in sig_map:
            continue
        err = _check_call_against_spec(node, sig_map[callee_name])
        if not err:
            continue
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
    removed_defs = _extract_removed_def_signatures(diff_text, repo_root=repo_root)
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
    caller_scan_truncated = False
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
                caller_scan_truncated = True
                break
            checked_callers += 1
            _scan_dependent_caller_ast(repo_root, dep_rel, rel, sig_map, broken_call_sites, findings)

    if caller_scan_truncated:
        findings.append(
            _make_finding(
                severity="Nice to have",
                code="CALLER_SCAN_TRUNCATED",
                title=f"Downstream caller scan capped at {MAX_CALLER_FILES} files",
                file_path=py_changed[0],
                line_no=1,
                what_is=f"Caller AST check stopped after {MAX_CALLER_FILES} dependent files.",
                problem="Additional downstream callers beyond the cap were not inspected.",
                fix="Run full test suite across downstream packages to verify remaining callers.",
                if_skipped="Callers past the scan cap might require manual verification.",
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
    require_mutation_receipt: bool = True,
    decision_log_path: Optional[str] = None,
) -> Tuple[Optional[PlanReconciliationDTO], Optional[SoloProvenanceAuditDTO], CallerCompatibilityDTO, List[Dict[str, str]]]:
    """Reconciles git diff & disk state against /super-plan contracts, /solo HMAC receipts, and CallGraph callers."""
    abs_root = os.path.abspath(repo_root)
    findings: List[Dict[str, str]] = []

    plan_dto: Optional[PlanReconciliationDTO] = None
    has_plan = bool(plan_path and str(plan_path).strip())
    if has_plan:
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
        has_plan=has_plan,
        require_mutation_receipt=require_mutation_receipt,
        decision_log_path=decision_log_path,
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
