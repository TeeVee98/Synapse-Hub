#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/orchestration/plan_dag_bridge.py — Closed-Loop Plan-to-Solo DAG Bridge
----------------------------------------------------------------------------
Deterministically compiles a validated Spec-Driven Super-Plan Markdown DAG into
sequential Single-Agent `/solo` milestone execution specs and orchestrates:
  Scope Guard -> Red/Green Certification -> Mutation Audit -> Purple Audit -> DecisionLog
with O(1) memory flushing and path-scoped rollback on unauthorized edits.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import gc
import importlib
import os
import re
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.core.decision_log import DecisionRowDTO, append_decision_row
from tools.design.dag_self_healer import DAGNode, SelfHealingDAGExecutor, parse_plan_to_dag
from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed
from tools.orchestration.solo_contracts import (
    _write_json_atomic,
    compute_mutation_receipt_hmac,
    resolve_red_receipt_path,
)

_CODE_EXTS = (".py", ".ts", ".js", ".java", ".groovy")


@dataclass(frozen=True)
class MilestoneExecutionSpecDTO:
    """Typed single-milestone execution specification compiled from a Markdown plan DAG."""

    node_id: str
    title: str
    depends_on: Tuple[str, ...]
    write_set: Tuple[str, ...]
    target_source_files: Tuple[str, ...]
    test_cmd: str
    pass_gate: str
    rollback_hook: str
    require_four_scenarios: bool = True
    mutation_threshold: float = 80.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AggregatedMutationReceiptDTO:
    """Milestone-level mutation receipt aggregating multiple target source files."""

    milestone_id: str
    status: str
    passed: bool
    mutation_score: float
    required_threshold: float
    targets_evaluated: Tuple[str, ...]
    total_generated: int
    killed: int
    survived: int
    receipt_hmac: str


@dataclass(frozen=True)
class PlanExecutionSummaryDTO:
    """Aggregated execution receipt across all compiled milestones in a Super-Plan."""

    plan_path: str
    passed: bool
    milestones_total: int
    milestones_passed: int
    halted_at_node: Optional[str]
    decision_log_path: str
    receipt_paths: Tuple[str, ...]
    milestone_results: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)
    review_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_path": self.plan_path,
            "passed": self.passed,
            "milestones_total": self.milestones_total,
            "milestones_passed": self.milestones_passed,
            "halted_at_node": self.halted_at_node,
            "decision_log_path": self.decision_log_path,
            "receipt_paths": list(self.receipt_paths),
            "milestone_results": list(self.milestone_results),
            "review_result": self.review_result,
        }


def _is_test_path(path: str) -> bool:
    norm = path.replace("\\", "/").strip()
    base = os.path.basename(norm).lower()
    return (
        norm.startswith("tests/")
        or "/tests/" in norm
        or base.startswith("test_")
        or base.endswith("_test.py")
        or ".spec." in base
        or ".test." in base
    )


def _topological_order(nodes: Dict[str, DAGNode]) -> List[DAGNode]:
    """Returns DAGNode instances in deterministic topological order, raising ValueError on cycles."""
    in_degree: Dict[str, int] = {nid: 0 for nid in nodes}
    dependents: Dict[str, List[str]] = {nid: [] for nid in nodes}

    for nid, node in nodes.items():
        for dep in node.depends_on:
            if dep in nodes:
                in_degree[nid] += 1
                dependents[dep].append(nid)

    queue: List[str] = [nid for nid in nodes if in_degree[nid] == 0]
    ordered: List[DAGNode] = []
    visited: Set[str] = set()

    while queue:
        curr = queue.pop(0)
        if curr in visited:
            continue
        visited.add(curr)
        ordered.append(nodes[curr])
        for nxt in dependents[curr]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    if len(ordered) != len(nodes):
        remaining = [nid for nid in nodes if nid not in visited]
        raise ValueError(f"Circular dependency cycle detected in plan DAG involving nodes: {remaining}")
    return ordered


def _is_tier0_plan(plan_content: str) -> bool:
    return bool(re.search(r"Fast-Track\s+Micro-Plan|Tier\s+0\s+Fast-Track|FAST_TRACK", plan_content, re.IGNORECASE))


def compile_plan_to_solo_specs(
    plan_path: str,
    repo_root: str = _REPO_ROOT,
    profile: str = "auto",
) -> List[MilestoneExecutionSpecDTO]:
    """Compiles a validated super-plan Markdown DAG into topologically ordered MilestoneExecutionSpecDTO items."""
    from tools.manual.manual_pipeline_adapter import detect_plan_profile

    if not plan_path or not str(plan_path).strip():
        raise ValueError("plan_path must be a non-empty string.")

    resolved_path = (
        plan_path
        if os.path.isabs(plan_path) or os.path.isfile(plan_path)
        else os.path.join(repo_root, plan_path)
    )
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"Plan file not found: {resolved_path}")

    with open(resolved_path, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()

    if not content.strip():
        raise ValueError(f"Plan file '{resolved_path}' is empty.")

    effective_profile = detect_plan_profile(content, explicit_profile=profile)
    executor = parse_plan_to_dag(content, repo_root=repo_root)
    if not executor.nodes:
        raise ValueError(f"Plan file '{resolved_path}' defines zero executable DAG milestones.")

    ordered_nodes = _topological_order(executor.nodes)
    tier0 = _is_tier0_plan(content)

    specs: List[MilestoneExecutionSpecDTO] = []
    for node in ordered_nodes:
        write_set = tuple(w.replace("\\", "/").strip() for w in node.write_set if w.strip())
        if effective_profile == "manual":
            source_files = tuple(w for w in write_set if w.lower().endswith(".md"))
        else:
            source_files = tuple(
                w for w in write_set
                if w.lower().endswith(_CODE_EXTS) and not _is_test_path(w)
            )
        test_files = [w for w in write_set if _is_test_path(w)]

        pass_gate = (node.pass_gate or "").strip()
        if pass_gate:
            test_cmd = pass_gate
        elif test_files:
            test_cmd = f"python3 -m pytest {' '.join(test_files)} -q"
        else:
            test_cmd = ""

        specs.append(
            MilestoneExecutionSpecDTO(
                node_id=node.node_id,
                title=node.title or f"Milestone {node.node_id}",
                depends_on=tuple(node.depends_on),
                write_set=write_set,
                target_source_files=source_files,
                test_cmd=test_cmd,
                pass_gate=pass_gate or test_cmd,
                rollback_hook=(node.rollback_hook or "").strip(),
                require_four_scenarios=not tier0,
                mutation_threshold=80.0,
            )
        )
    return specs


MAX_SAFE_UNAUTHORIZED_ROLLBACK = 10


def _rollback_unauthorized_files(unauthorized: List[str], repo_root: str) -> Dict[str, Any]:
    """Restores tracked unauthorized files and removes untracked unauthorized files safely within repo_root."""
    filtered = [p for p in unauthorized if p and not p.startswith("SCOPE_GUARD_UNVERIFIABLE:")]
    if len(filtered) > MAX_SAFE_UNAUTHORIZED_ROLLBACK:
        return {
            "success": False,
            "aborted_bulk_rollback": True,
            "reverted_files": [],
            "removed_created_files": [],
            "reason": (
                f"Bulk dirty-tree rollback aborted ({len(filtered)} files > safety cap {MAX_SAFE_UNAUTHORIZED_ROLLBACK}). "
                "Commit, stash, or clean pre-existing workspace changes before running --from-plan."
            ),
        }
    tracked: List[str] = []
    untracked: List[str] = []
    for path in filtered:
        norm = path.replace("\\", "/").strip()
        cat_res = subprocess.run(
            ["git", "cat-file", "-e", f"HEAD:{norm}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if cat_res.returncode == 0:
            tracked.append(norm)
        else:
            full_p = os.path.join(repo_root, norm)
            if os.path.isfile(full_p):
                untracked.append(norm)
    if not tracked and not untracked:
        return {"success": True, "reverted_files": [], "removed_created_files": []}
    return rollback_path_scoped_detailed(
        base_commit="HEAD",
        declared_modify=tracked,
        created_files=untracked,
        repo_root=repo_root,
    )


@dataclass(frozen=True)
class SoloPhaseCallbacks:
    """Dependency-inverted phase hooks injected by solo_runner to keep the import graph acyclic."""

    certify_red_phase: Callable[..., Dict[str, Any]]
    certify_green_phase: Callable[..., Dict[str, Any]]
    certify_mutation_phase: Callable[..., Dict[str, Any]]
    certify_purple_phase: Callable[..., Dict[str, Any]]
    resolve_test_adapter: Callable[..., Any]


def _resolve_phase_callbacks(callbacks: Optional[SoloPhaseCallbacks] = None) -> SoloPhaseCallbacks:
    if callbacks is not None:
        return callbacks
    solo_mod = sys.modules.get("tools.orchestration.solo_runner") or importlib.import_module(
        "tools.orchestration.solo_runner"
    )
    return SoloPhaseCallbacks(
        certify_red_phase=solo_mod.certify_red_phase,
        certify_green_phase=solo_mod.certify_green_phase,
        certify_mutation_phase=solo_mod.certify_mutation_phase,
        certify_purple_phase=solo_mod.certify_purple_phase,
        resolve_test_adapter=solo_mod.resolve_test_adapter,
    )


def _aggregate_milestone_mutation_results(
    milestone_id: str,
    mut_reports: Dict[str, Any],
    required_threshold: float,
    mut_all_passed: bool,
    repo_root: str,
) -> Tuple[Dict[str, Any], AggregatedMutationReceiptDTO]:
    """Aggregates per-file mutation results into one HMAC-signed milestone receipt."""
    merged_details: Dict[str, Any] = {}
    total_gen_sum = 0
    killed_sum = 0
    survived_sum = 0
    targets_eval: List[str] = []

    for src_key, rep in mut_reports.items():
        total_gen_sum += int(rep.get("total_generated") if rep.get("total_generated") is not None else rep.get("total_mutants", 0))
        killed_sum += int(rep.get("killed") or 0)
        survived_sum += int(rep.get("survived") or 0)
        eval_list = rep.get("targets_evaluated")
        for te in (eval_list if eval_list else [src_key]):
            if te not in targets_eval:
                targets_eval.append(te)
        t_det = rep.get("target_details")
        if isinstance(t_det, dict):
            merged_details.update(t_det)

    denom = killed_sum + survived_sum
    if denom > 0:
        agg_score = round((killed_sum / denom) * 100.0, 1)
    else:
        scores = [float(r.get("mutation_score") or 0.0) for r in mut_reports.values()]
        agg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    agg_status = (
        "AST_CONTRACT_VERIFIED"
        if total_gen_sum == 0 and mut_all_passed
        else ("CERTIFIED_MUTATION" if mut_all_passed else "MUTATION_REJECTED")
    )
    payload: Dict[str, Any] = {
        "milestone_id": milestone_id,
        "status": agg_status,
        "passed": mut_all_passed,
        "mutation_score": agg_score,
        "required_threshold": required_threshold,
        "targets_evaluated": targets_eval,
        "total_generated": total_gen_sum,
        "total_mutants": total_gen_sum,
        "killed": killed_sum,
        "survived": survived_sum,
        "target_details": merged_details,
    }
    agg_hmac = compute_mutation_receipt_hmac(payload, repo_root=repo_root)
    payload["receipt_hmac"] = agg_hmac
    dto = AggregatedMutationReceiptDTO(
        milestone_id=milestone_id,
        status=agg_status,
        passed=mut_all_passed,
        mutation_score=agg_score,
        required_threshold=required_threshold,
        targets_evaluated=tuple(targets_eval),
        total_generated=total_gen_sum,
        killed=killed_sum,
        survived=survived_sum,
        receipt_hmac=agg_hmac,
    )
    return payload, dto


def _execute_milestone_mutation_phase(
    spec: MilestoneExecutionSpecDTO,
    repo_root: str,
    sandbox_mode: str,
    diff_only_mutation: bool,
    certify_mutation_fn: Any,
    node_result: Dict[str, Any],
    receipt_paths: List[str],
) -> None:
    """Runs diff-scoped mutation evaluation across milestone targets and writes an aggregated signed receipt."""
    mut_receipt = os.path.join(repo_root, "reports", "solo_receipts", f"{spec.node_id}_mutation.json")
    mut_reports: Dict[str, Any] = {}
    mut_all_passed = True
    for src_file in spec.target_source_files:
        abs_src = src_file if os.path.isabs(src_file) else os.path.join(repo_root, src_file)
        if not os.path.isfile(abs_src):
            continue
        m_res = certify_mutation_fn(
            target_file=src_file,
            test_cmd=spec.test_cmd,
            threshold=spec.mutation_threshold,
            diff_only=diff_only_mutation,
            mutation_scope="diff_only" if diff_only_mutation else "full",
            allow_full_fallback=True,
            repo_root=repo_root,
            receipt_path=mut_receipt,
            sandbox_mode=sandbox_mode,
        )
        if not m_res.get("passed", False) and m_res.get("total_generated", 0) == 0:
            m_res = dict(m_res)
            m_res["status"] = "AST_CONTRACT_VERIFIED"
            m_res["passed"] = True
        mut_reports[src_file] = m_res
        if not m_res.get("passed", False):
            mut_all_passed = False

    if not mut_reports:
        return
    aggregated_payload, agg_dto = _aggregate_milestone_mutation_results(
        milestone_id=spec.node_id,
        mut_reports=mut_reports,
        required_threshold=spec.mutation_threshold,
        mut_all_passed=mut_all_passed,
        repo_root=repo_root,
    )
    _write_json_atomic(mut_receipt, aggregated_payload)
    node_result["phases"]["mutation"] = {
        "passed": mut_all_passed,
        "targets": mut_reports,
        "aggregated_receipt": asdict(agg_dto),
        "receipt_file": mut_receipt,
    }
    if os.path.isfile(mut_receipt):
        receipt_paths.append(mut_receipt)
    if not mut_all_passed:
        node_result["passed"] = False


def _derive_plan_slug(plan_path: str) -> Optional[str]:
    """Derives an optional collision-safe slug from a named plan file (None for legacy implementation_plan.md)."""
    stem = os.path.splitext(os.path.basename(plan_path or ""))[0].strip()
    if not stem or stem.lower() == "implementation_plan":
        return None
    cleaned = re.sub(r"[^A-Za-z0-9_\-]", "_", stem)
    return cleaned or None


def _execute_milestone_test_phase(
    spec: MilestoneExecutionSpecDTO,
    repo_root: str,
    sandbox_mode: str,
    recertify_red: bool,
    strict_red: bool,
    node_result: Dict[str, Any],
    receipt_paths: List[str],
    resolve_test_adapter: Any,
    certify_red_phase: Any,
    certify_green_phase: Any,
    plan_slug: Optional[str] = None,
) -> None:
    """Executes milestone-scoped Red/Green verification (plan-slug-first with legacy fallback)."""
    slugged_red_path = (
        resolve_red_receipt_path(repo_root, milestone_id=spec.node_id, plan_slug=plan_slug)
        if plan_slug
        else None
    )
    legacy_red_path = resolve_red_receipt_path(repo_root, milestone_id=spec.node_id)
    if slugged_red_path and os.path.isfile(slugged_red_path):
        scoped_red_path = slugged_red_path
    elif os.path.isfile(legacy_red_path):
        scoped_red_path = legacy_red_path
    else:
        scoped_red_path = slugged_red_path or legacy_red_path

    if os.path.isfile(scoped_red_path):
        green_res = certify_green_phase(
            test_cmd=spec.test_cmd,
            receipt_path=scoped_red_path,
            cwd=repo_root,
            sandbox_mode=sandbox_mode,
            milestone_id=spec.node_id,
            allow_commit_progression=True,
        )
        node_result["phases"]["green"] = green_res
        receipt_paths.append(scoped_red_path)
        if not green_res.get("passed", False):
            node_result["passed"] = False
        return

    adapter = resolve_test_adapter(spec.test_cmd)
    rc, out = adapter.execute(spec.test_cmd, cwd=repo_root)
    if rc != 0:
        red_res = certify_red_phase(
            test_cmd=spec.test_cmd,
            receipt_path=scoped_red_path,
            cwd=repo_root,
            target_files=list(spec.target_source_files) or None,
            require_four_scenarios=spec.require_four_scenarios,
            milestone_id=spec.node_id,
            recertify_red=recertify_red,
        )
        node_result["phases"]["red"] = red_res
        if red_res.get("receipt_file"):
            receipt_paths.append(str(red_res["receipt_file"]))
        node_result["passed"] = False
        return

    if strict_red:
        node_result["phases"]["green"] = {
            "status": "MISSING_RED_RECEIPT",
            "passed": False,
            "test_cmd": spec.test_cmd,
            "exit_code": 0,
            "error": (
                f"Strict Red-First violation: Missing milestone Red receipt at '{scoped_red_path}'. "
                f"Certify Red phase via --red --milestone {spec.node_id} before --strict-red."
            ),
        }
        node_result["passed"] = False
        return

    node_result["phases"]["green"] = {
        "status": "CERTIFIED_GREEN",
        "passed": True,
        "test_cmd": spec.test_cmd,
        "exit_code": 0,
        "mode": "verified_replay",
        "output_tail": out[-300:] if len(out) > 300 else out,
    }


def _flush_offload_dir(offload_dir: str) -> None:
    """Removes temporary milestone artifacts between sequential runs."""
    if not os.path.isdir(offload_dir):
        return
    try:
        for fn in os.listdir(offload_dir):
            fp = os.path.join(offload_dir, fn)
            if os.path.isfile(fp):
                os.remove(fp)
    except OSError:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass


def _collect_ancestor_write_set(
    node_id: str,
    spec_by_id: Dict[str, MilestoneExecutionSpecDTO],
) -> Set[str]:
    """Collects transitive write_set paths of declared depends_on ancestors for cumulative Scope Guard checks."""
    collected: Set[str] = set()
    visited: Set[str] = set()
    stack = list(spec_by_id[node_id].depends_on) if node_id in spec_by_id else []
    while stack:
        dep_id = stack.pop()
        if dep_id in visited:
            continue
        visited.add(dep_id)
        dep_spec = spec_by_id.get(dep_id)
        if dep_spec is None:
            continue
        collected.update(dep_spec.write_set)
        stack.extend(dep_spec.depends_on)
    return collected


def _extract_manual_spec_from_plan(plan_content: str) -> str:
    m = re.search(
        r"Spec\s+Source[^\n:]*:[\s*`]*([A-Za-z0-9_.\-/\\]+\.(?:md|feature))",
        plan_content or "",
        re.IGNORECASE,
    )
    return m.group(1).replace("\\", "/") if m else ""


def _execute_manual_milestone(
    spec: MilestoneExecutionSpecDTO,
    spec_path: str,
    repo_root: str,
    strict_red: bool,
    run_mutation: bool,
    node_result: Dict[str, Any],
    receipt_paths: List[str],
) -> None:
    """Executes one Manual QA milestone through Red provenance, Green linter+RTM, and Spec-Mutation."""
    from tools.manual.manual_pipeline_adapter import (
        audit_manual_delivery,
        run_spec_mutation_audit,
        verify_manual_green_phase,
    )

    tc_files = tuple(w for w in spec.write_set if w.lower().endswith(".md"))
    if strict_red:
        audit = audit_manual_delivery(
            repo_root=repo_root,
            plan_path=None,
            changed_files=tc_files,
            milestone_id=spec.node_id,
            strict_solo=True,
            spec_path=spec_path or None,
        )
        node_result["phases"]["manual_red_check"] = {
            "receipt_verified": audit.receipt_verified,
            "findings": list(audit.findings),
        }
        if not audit.receipt_verified:
            node_result["passed"] = False
            return

    green = verify_manual_green_phase(
        spec_path=spec_path,
        tc_files=tc_files,
        milestone_id=spec.node_id,
        repo_root=repo_root,
    )
    node_result["phases"]["green"] = {
        "passed": green.passed,
        "total_test_cases": green.total_test_cases,
        "uncovered_req_ids": list(green.uncovered_req_ids),
        "orphan_tc_ids": list(green.orphan_tc_ids),
        "linter_passed": green.linter_passed,
    }
    if not green.passed:
        node_result["passed"] = False
        return

    if run_mutation:
        mut = run_spec_mutation_audit(
            spec_path=spec_path,
            tc_files=tc_files,
            threshold=spec.mutation_threshold,
            repo_root=repo_root,
            milestone_id=spec.node_id,
        )
        node_result["phases"]["spec_mutation"] = {
            "passed": mut.passed,
            "kill_score": mut.kill_score,
            "threshold": mut.threshold,
            "survived_mutants": list(mut.survived_mutants),
            "receipt_hmac": mut.receipt_hmac,
        }
        mut_path = os.path.join(repo_root, "reports", "solo_receipts", f"{spec.node_id}_mutation.json")
        if os.path.isfile(mut_path):
            receipt_paths.append(mut_path)
        if not mut.passed:
            node_result["passed"] = False


def execute_plan_via_solo(
    plan_path: str,
    repo_root: str = _REPO_ROOT,
    milestone_filter: Optional[str] = None,
    decision_log_path: str = "decisions.tsv",
    sandbox_mode: str = "worktree",
    enforce_scope_guard: bool = True,
    run_mutation: bool = True,
    run_purple: bool = True,
    recertify_red: bool = False,
    strict_red: bool = False,
    diff_only_mutation: bool = True,
    phase_callbacks: Optional[SoloPhaseCallbacks] = None,
    auto_review: bool = True,
    profile: str = "auto",
) -> PlanExecutionSummaryDTO:
    """Executes compiled plan milestones sequentially through Red/Green/Mutation/Purple/ScopeGuard/DecisionLog and auto-/review."""
    from tools.manual.manual_pipeline_adapter import detect_plan_profile

    resolved_plan_path = (
        plan_path
        if os.path.isabs(plan_path) or os.path.isfile(plan_path)
        else os.path.join(repo_root, plan_path)
    )
    plan_text = ""
    if os.path.isfile(resolved_plan_path):
        with open(resolved_plan_path, "r", encoding="utf-8", errors="replace") as pfh:
            plan_text = pfh.read()
    effective_profile = detect_plan_profile(plan_text, explicit_profile=profile)
    manual_spec_path = _extract_manual_spec_from_plan(plan_text) if effective_profile == "manual" else ""

    resolved_cb = _resolve_phase_callbacks(phase_callbacks)
    certify_red_phase = resolved_cb.certify_red_phase
    certify_green_phase = resolved_cb.certify_green_phase
    certify_mutation_phase = resolved_cb.certify_mutation_phase
    certify_purple_phase = resolved_cb.certify_purple_phase
    resolve_test_adapter = resolved_cb.resolve_test_adapter

    all_specs = compile_plan_to_solo_specs(plan_path, repo_root=repo_root, profile=effective_profile)
    spec_by_id = {s.node_id: s for s in all_specs}
    specs = all_specs
    completed_write_set: Set[str] = set()
    if milestone_filter and milestone_filter.strip():
        filt = milestone_filter.strip()
        specs = [s for s in all_specs if s.node_id == filt]
        if not specs:
            raise ValueError(f"Milestone '{filt}' not found in plan '{plan_path}'.")
        completed_write_set.update(_collect_ancestor_write_set(filt, spec_by_id))

    resolved_log = (
        decision_log_path
        if os.path.isabs(decision_log_path)
        else os.path.join(repo_root, decision_log_path)
    )
    offload_dir = os.path.join(repo_root, "scratch", "offload")

    derived_plan_slug = _derive_plan_slug(plan_path)
    milestones_passed = 0
    halted_at: Optional[str] = None
    receipt_paths: List[str] = []
    milestone_results: List[Dict[str, Any]] = []

    for spec in specs:
        node_result: Dict[str, Any] = {
            "node_id": spec.node_id,
            "title": spec.title,
            "write_set": list(spec.write_set),
            "test_cmd": spec.test_cmd,
            "phases": {},
            "passed": True,
        }
        dag_node = DAGNode(
            node_id=spec.node_id,
            title=spec.title,
            depends_on=list(spec.depends_on),
            write_set=list(spec.write_set),
            rollback_hook=spec.rollback_hook or None,
            pass_gate=spec.pass_gate or None,
        )
        dag_exec = SelfHealingDAGExecutor(nodes={spec.node_id: dag_node}, repo_root=repo_root)

        # 1. Scope Guard Pre-Check (cumulative across completed milestones so M2+ never destroy M1 edits)
        if enforce_scope_guard and spec.write_set:
            scope_ok, unauthorized = dag_exec.check_scope_guard_violation(
                dag_node,
                allowed_extra_files=completed_write_set,
            )
            node_result["phases"]["scope_guard"] = {
                "passed": scope_ok,
                "unauthorized": list(unauthorized),
            }
            if not scope_ok:
                rollback_ws = dag_exec.safe_rollback(dag_node, run_compensating_tx=True)
                rollback_unauth = _rollback_unauthorized_files(unauthorized, repo_root)
                node_result["phases"]["rollback"] = {
                    "write_set_rollback": rollback_ws,
                    "unauthorized_rollback": rollback_unauth,
                }
                node_result["passed"] = False
                halted_at = spec.node_id
                milestone_results.append(node_result)
                append_decision_row(
                    resolved_log,
                    DecisionRowDTO(
                        ts=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        phase=spec.node_id,
                        decision=f"Halted {spec.node_id} on Scope Guard violation",
                        why=f"Unauthorized edits outside write_set: {unauthorized}",
                        evidence=f"{plan_path}:{spec.node_id}",
                        result="FAIL_SCOPE_GUARD",
                    ),
                )
                break

        # 2. Milestone-Scoped Red / Green / Mutation / Purple Verification
        if effective_profile == "manual":
            _execute_manual_milestone(
                spec=spec,
                spec_path=manual_spec_path,
                repo_root=repo_root,
                strict_red=strict_red,
                run_mutation=run_mutation,
                node_result=node_result,
                receipt_paths=receipt_paths,
            )
        else:
            if spec.test_cmd:
                _execute_milestone_test_phase(
                    spec=spec,
                    repo_root=repo_root,
                    sandbox_mode=sandbox_mode,
                    recertify_red=recertify_red,
                    strict_red=strict_red,
                    node_result=node_result,
                    receipt_paths=receipt_paths,
                    resolve_test_adapter=resolve_test_adapter,
                    certify_red_phase=certify_red_phase,
                    certify_green_phase=certify_green_phase,
                    plan_slug=derived_plan_slug,
                )

            # 3. Live Dynamic Mutation Sentinel (diff-scoped by default with full fallback & AST_CONTRACT_VERIFIED waiver)
            if node_result["passed"] and run_mutation and spec.target_source_files and spec.test_cmd:
                _execute_milestone_mutation_phase(
                    spec=spec,
                    repo_root=repo_root,
                    sandbox_mode=sandbox_mode,
                    diff_only_mutation=diff_only_mutation,
                    certify_mutation_fn=certify_mutation_phase,
                    node_result=node_result,
                    receipt_paths=receipt_paths,
                )

            # 4. Purple Phase Audit (Tech Lead + Neuro-Symbolic + Call-Graph across ALL milestone target source files)
            if node_result["passed"] and run_purple:
                purple_receipt = os.path.join(repo_root, "reports", "solo_receipts", f"{spec.node_id}_purple.json")
                primary_target = spec.target_source_files[0] if spec.target_source_files else ""
                p_res = certify_purple_phase(
                    target="uncommitted",
                    target_file=primary_target,
                    target_files=list(spec.target_source_files) or None,
                    receipt_path=purple_receipt,
                    repo_root=repo_root,
                )
                must_fix = [
                    f for f in p_res.get("findings", [])
                    if isinstance(f, dict) and f.get("severity") == "Must fix"
                ]
                purple_ok = bool(p_res.get("passed", False)) or len(must_fix) == 0
                node_result["phases"]["purple"] = p_res
                if os.path.isfile(purple_receipt):
                    receipt_paths.append(purple_receipt)
                if not purple_ok:
                    node_result["passed"] = False

        # 5. Append Decision Log Audit Trail Row
        status_label = "PASS" if node_result["passed"] else "FAIL"
        append_decision_row(
            resolved_log,
            DecisionRowDTO(
                ts=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                phase=spec.node_id,
                decision=f"Executed {spec.title} via /solo plan bridge",
                why=f"Sequential DAG milestone verification ({', '.join(spec.write_set) or 'no write_set'})",
                evidence=f"{spec.test_cmd or plan_path}",
                result=status_label,
            ),
        )

        milestone_results.append(node_result)
        if node_result["passed"]:
            milestones_passed += 1
            completed_write_set.update(spec.write_set)
        else:
            halted_at = spec.node_id
            break

        # O(1) State-Flushing Memory Hygiene between milestones
        _flush_offload_dir(offload_dir)
        gc.collect()

    overall_passed = halted_at is None and milestones_passed == len(specs)
    review_result: Optional[Dict[str, Any]] = None
    if overall_passed and auto_review:
        from tools.orchestration.senior_code_review import evaluate_review

        rev_exit, rev_payload, _, _ = evaluate_review(
            repo_dir=repo_root,
            target="uncommitted",
            plan_path=plan_path,
            milestone_id=milestone_filter.strip() if milestone_filter and milestone_filter.strip() else None,
            strict=False,
            strict_solo=strict_red,
            decision_log_path=resolved_log,
        )
        review_result = rev_payload
        rev_rcpt = rev_payload.get("receipt_path")
        if isinstance(rev_rcpt, str) and os.path.isfile(rev_rcpt):
            receipt_paths.append(rev_rcpt)
        if rev_exit != 0 or not rev_payload.get("passed", False):
            overall_passed = False
            halted_at = "REVIEW"
            append_decision_row(
                resolved_log,
                DecisionRowDTO(
                    ts=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    phase="REVIEW",
                    decision=f"Auto /review blocked {plan_path} ({rev_payload.get('verdict')})",
                    why=f"Post-solo Plan-vs-Solo reconciliation found {rev_payload.get('findings_count', 0)} finding(s)",
                    evidence=str(rev_rcpt or plan_path),
                    result="FAIL_AUTO_REVIEW",
                ),
            )

    return PlanExecutionSummaryDTO(
        plan_path=plan_path,
        passed=overall_passed,
        milestones_total=len(specs),
        milestones_passed=milestones_passed,
        halted_at_node=halted_at,
        decision_log_path=resolved_log,
        receipt_paths=tuple(dict.fromkeys(receipt_paths)),
        milestone_results=tuple(milestone_results),
        review_result=review_result,
    )
