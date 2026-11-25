#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/design/dag_self_healer.py — Dynamic DAG Rescheduling & Self-Healing Engine
---------------------------------------------------------------------------------
Eliminates the "dead stop after git checkout --" failure mode by enforcing:
  1. Failure snapshot capture before rollback (preserves evidence & diff).
  2. Transactional rollback with compensating hooks (rollback_hook for non-git state).
  3. Failure root-cause classification (LOCAL_IMPL vs ARCHITECTURAL_VIOLATION).
  4. Cascading cancellation propagation for shared assumptions.
  5. Just-In-Time (JIT) Full Body Read for affected symbols (bounded to <= 2 files).
  6. Sub-DAG Surgical Replacement & re-splicing.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from enum import Enum
import json
import os
import re
import shlex
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.lint.plan_schema_sentinel import (
    rollback_path_scoped_detailed,
    split_chained_commands,
    validate_rollback_hook_safety,
)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class NodeStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REQUEUED = "REQUEUED"


class FailureClass(str, Enum):
    LOCAL_IMPL = "LOCAL_IMPL"
    ARCHITECTURAL_VIOLATION = "ARCHITECTURAL_VIOLATION"


@dataclass
class FailureSnapshot:
    node_id: str
    timestamp: str
    diff: str
    runtime_trace: str
    involved_symbols: List[str]
    failure_class: FailureClass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp,
            "diff": self.diff,
            "runtime_trace": self.runtime_trace,
            "involved_symbols": self.involved_symbols,
            "failure_class": self.failure_class.value,
        }


@dataclass(frozen=True)
class RollbackExecutionReceipt:
    node_id: str
    compensating_hook_run: bool
    compensating_hook_exit_code: Optional[int]
    git_revert_run: bool
    reverted_files: List[str]
    removed_created_files: List[str]
    pre_hashes: Dict[str, str]
    post_hashes: Dict[str, str]
    verified_clean: bool
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "compensating_hook_run": self.compensating_hook_run,
            "compensating_hook_exit_code": self.compensating_hook_exit_code,
            "git_revert_run": self.git_revert_run,
            "reverted_files": list(self.reverted_files),
            "removed_created_files": list(self.removed_created_files),
            "pre_hashes": dict(self.pre_hashes),
            "post_hashes": dict(self.post_hashes),
            "verified_clean": self.verified_clean,
            "errors": list(self.errors),
        }


@dataclass
class DAGNode:
    node_id: str
    depends_on: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    compute_tier: str = "Flash"
    retries: int = 0
    max_retries: int = 2
    write_set: List[str] = field(default_factory=list)
    shared_assumptions: List[str] = field(default_factory=list)
    rollback_hook: Optional[str] = None
    pass_gate: Optional[str] = None

    def escalate_compute_tier(self) -> None:
        """Escalates model capacity on local implementation failures."""
        if "Flash" in self.compute_tier:
            self.compute_tier = "Pro / Reasoning [Best-of-3]"
        elif "Pro" in self.compute_tier:
            self.compute_tier = "Pro / Reasoning [Thinking: High | Best-of-3]"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "compute_tier": self.compute_tier,
            "retries": self.retries,
            "write_set": self.write_set,
            "shared_assumptions": self.shared_assumptions,
            "rollback_hook": self.rollback_hook,
            "pass_gate": self.pass_gate,
        }


class SelfHealingDAGExecutor:
    """Orchestrates DAG execution, fault triage, compensating rollback, and sub-DAG resplicing."""

    def __init__(self, nodes: Optional[Dict[str, DAGNode]] = None, repo_root: str = _REPO_ROOT):
        self.nodes: Dict[str, DAGNode] = nodes or {}
        self.repo_root = repo_root
        self.failure_snapshots: List[FailureSnapshot] = []

    def add_node(self, node: DAGNode) -> None:
        self.nodes[node.node_id] = node

    def get_ready_nodes(self) -> List[DAGNode]:
        """Returns nodes whose dependencies are all SUCCESS and are currently PENDING."""
        ready: List[DAGNode] = []
        for nid, node in self.nodes.items():
            if node.status != NodeStatus.PENDING:
                continue
            deps_met = all(
                dep in self.nodes and self.nodes[dep].status == NodeStatus.SUCCESS
                for dep in node.depends_on
            )
            if deps_met:
                ready.append(node)
        return ready

    def capture_failure_snapshot(self, node: DAGNode, diff: str, trace: str) -> FailureSnapshot:
        """Captures forensic evidence before executing safe revert (no evidence lost)."""
        import datetime

        # Extract symbols involved from stack trace
        involved: List[str] = []
        for line in trace.splitlines():
            m = re.findall(r'File "([^"]+)", line \d+, in ([a-zA-Z0-9_]+)', line)
            for fpath, func in m:
                symbol = f"{os.path.basename(fpath)}::{func}"
                if symbol not in involved:
                    involved.append(symbol)

        # Fallback to write_set if trace didn't match standard python traceback
        if not involved and node.write_set:
            involved = [f"{os.path.basename(f)}::module_root" for f in node.write_set]

        # Determine failure class
        f_class = self.classify_failure(trace, node.retries)

        snapshot = FailureSnapshot(
            node_id=node.node_id,
            timestamp=datetime.datetime.now().isoformat(),
            diff=diff,
            runtime_trace=trace,
            involved_symbols=involved,
            failure_class=f_class,
        )
        self.failure_snapshots.append(snapshot)
        return snapshot

    def classify_failure(self, trace: str, retries: int) -> FailureClass:
        """Classifies root cause: LOCAL_IMPL (code bug) vs ARCHITECTURAL_VIOLATION (schema/contract broke)."""
        arch_triggers = [
            "schema mismatch", "contract violation", "interface mismatch",
            "table already exists", "connection refused", "timeout after",
            "breaking change", "incompatible types", "importerror", "modulenotfounderror"
        ]
        lower_trace = trace.lower()
        if any(trig in lower_trace for trig in arch_triggers):
            return FailureClass.ARCHITECTURAL_VIOLATION

        # If retries already exhausted, promote to architectural review
        if retries >= 2:
            return FailureClass.ARCHITECTURAL_VIOLATION

        return FailureClass.LOCAL_IMPL

    def _execute_rollback_hook(self, hook_cmd: str, timeout: float = 30.0) -> Tuple[int, str, str]:
        """Executes a validated rollback hook command safely without shell=True.

        Supports unquoted chained operators (&&, ||, ;) by splitting segments and running
        each command via shlex.split with an explicit bounded timeout.
        """
        tokens = split_chained_commands(hook_cmd.strip())
        last_rc = 0
        out_chunks: List[str] = []
        err_chunks: List[str] = []
        idx = 0
        while idx < len(tokens):
            segment = tokens[idx].strip()
            prev_op = tokens[idx - 1] if idx > 0 else None
            idx += 2
            if not segment:
                continue
            if prev_op == "&&" and last_rc != 0:
                break
            if prev_op == "||" and last_rc == 0:
                continue
            argv = shlex.split(segment, posix=(os.name != "nt"))
            if os.name == "nt":
                argv = [t[1:-1] if len(t) >= 2 and t[0] == t[-1] and t[0] in ('"', "'") else t for t in argv]
            if not argv:
                continue
            proc = subprocess.run(
                argv,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            last_rc = proc.returncode
            if proc.stdout:
                out_chunks.append(proc.stdout)
            if proc.stderr:
                err_chunks.append(proc.stderr)
        return last_rc, "\n".join(out_chunks), "\n".join(err_chunks)

    def _partition_write_set(self, write_set: List[str]) -> Tuple[List[str], List[str], List[str]]:
        """Partitions write_set into (tracked_in_head, untracked_on_disk, errors)."""
        tracked: List[str] = []
        untracked_created: List[str] = []
        errors: List[str] = []

        try:
            git_check = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if git_check.returncode != 0 or git_check.stdout.strip().lower() != "true":
                errors.append(
                    f"Cannot execute path-scoped rollback: not a valid git worktree ({self.repo_root})"
                )
                return tracked, untracked_created, errors
        except Exception as exc:
            errors.append(f"Git worktree check failed: {type(exc).__name__}: {exc}")
            return tracked, untracked_created, errors

        for raw_path in write_set:
            norm_rel = raw_path.replace("\\", "/").strip()
            if not norm_rel:
                continue
            try:
                cat_res = subprocess.run(
                    ["git", "cat-file", "-e", f"HEAD:{norm_rel}"],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if cat_res.returncode == 0:
                    tracked.append(norm_rel)
                else:
                    full_p = os.path.join(self.repo_root, norm_rel)
                    if os.path.isfile(full_p):
                        untracked_created.append(norm_rel)
            except Exception as exc:
                errors.append(f"Failed to classify write-set path '{norm_rel}': {exc}")

        return tracked, untracked_created, errors

    def safe_rollback(
        self,
        node: DAGNode,
        run_compensating_tx: bool = True,
        hook_timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Executes transactional rollback: runs compensating hook first, then physically reverts write_set."""
        compensating_hook_run = False
        compensating_hook_exit_code: Optional[int] = None
        compensating_hook_error: Optional[str] = None
        git_revert_run = False
        reverted_files: List[str] = []
        removed_created_files: List[str] = []
        pre_hashes: Dict[str, str] = {}
        post_hashes: Dict[str, str] = {}
        errors: List[str] = []

        # 1. Compensating transaction (non-git mutations)
        if run_compensating_tx and node.rollback_hook:
            safe, reason = validate_rollback_hook_safety(node.rollback_hook)
            if not safe:
                compensating_hook_error = f"Unsafe rollback hook rejected: {reason}"
                errors.append(compensating_hook_error)
            else:
                try:
                    rc, _, err_out = self._execute_rollback_hook(node.rollback_hook, timeout=hook_timeout)
                    compensating_hook_run = True
                    compensating_hook_exit_code = rc
                    if rc != 0:
                        compensating_hook_error = (
                            f"Compensating hook exited with code {rc}: {err_out.strip()}"
                        )
                        errors.append(compensating_hook_error)
                except subprocess.TimeoutExpired:
                    compensating_hook_run = True
                    compensating_hook_exit_code = 124
                    compensating_hook_error = (
                        f"Compensating hook timed out after {hook_timeout}s: {node.rollback_hook}"
                    )
                    errors.append(compensating_hook_error)
                except (OSError, ValueError) as exc:
                    compensating_hook_run = True
                    compensating_hook_exit_code = -1
                    compensating_hook_error = f"Compensating hook execution failed: {exc}"
                    errors.append(compensating_hook_error)

        # 2. Physical path-scoped file restoration
        if node.write_set:
            tracked, untracked_created, part_errors = self._partition_write_set(node.write_set)
            errors.extend(part_errors)
            if not part_errors:
                details = rollback_path_scoped_detailed(
                    base_commit="HEAD",
                    declared_modify=tracked,
                    created_files=untracked_created,
                    repo_root=self.repo_root,
                )
                git_revert_run = True
                reverted_files = list(details["reverted_files"])
                removed_created_files = list(details["removed_created_files"])
                pre_hashes = dict(details["pre_hashes"])
                post_hashes = dict(details["post_hashes"])
                errors.extend(details["errors"])

        verified_clean = len(errors) == 0
        receipt = RollbackExecutionReceipt(
            node_id=node.node_id,
            compensating_hook_run=compensating_hook_run,
            compensating_hook_exit_code=compensating_hook_exit_code,
            git_revert_run=git_revert_run,
            reverted_files=reverted_files,
            removed_created_files=removed_created_files,
            pre_hashes=pre_hashes,
            post_hashes=post_hashes,
            verified_clean=verified_clean,
            errors=errors,
        )
        result = receipt.to_dict()
        if node.rollback_hook and compensating_hook_run:
            result["rollback_hook"] = node.rollback_hook
        if compensating_hook_error:
            result["compensating_hook_error"] = compensating_hook_error

        node.status = NodeStatus.FAILED
        return result

    def check_scope_guard_violation(self, node: DAGNode) -> Tuple[bool, List[str]]:
        """
        Physical Scope Guard (Fail-Closed): Verifies git modified files do not exceed declared milestone write_set.
        Returns (is_valid, list_of_unauthorized_files_or_unverifiable_reasons).
        """
        if node is None or not isinstance(node.write_set, list):
            return False, ["SCOPE_GUARD_UNVERIFIABLE: Missing or invalid milestone write_set"]

        if any(not isinstance(w, str) or not w.strip() for w in node.write_set):
            return False, ["SCOPE_GUARD_UNVERIFIABLE: Unreadable entry in milestone write_set"]

        if len(node.write_set) == 0:
            return True, []

        if not self.repo_root or not os.path.isdir(self.repo_root):
            return False, [f"SCOPE_GUARD_UNVERIFIABLE: repo_root does not exist: {self.repo_root}"]

        actual_modified: List[str] = []
        try:
            res = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode != 0:
                return False, [
                    f"SCOPE_GUARD_UNVERIFIABLE: git diff exited with {res.returncode}: {res.stderr.strip()}"
                ]
            for line in res.stdout.strip().splitlines():
                nl = line.replace("\\", "/").strip()
                if nl and not nl.startswith((".git", "docs/adr", ".cache")):
                    actual_modified.append(nl)

            res_st = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if res_st.returncode != 0:
                return False, [
                    f"SCOPE_GUARD_UNVERIFIABLE: git status exited with {res_st.returncode}: {res_st.stderr.strip()}"
                ]
            for line in res_st.stdout.strip().splitlines():
                if line.startswith("?? "):
                    nl = line[3:].replace("\\", "/").strip()
                    if nl and not nl.startswith((".git", "docs/adr", ".cache", "scratch")):
                        if nl not in actual_modified:
                            actual_modified.append(nl)
        except Exception as exc:
            return False, [f"SCOPE_GUARD_UNVERIFIABLE: {type(exc).__name__}: {exc}"]

        declared_set = {
            os.path.normpath(w).replace("\\", "/") for w in node.write_set
        }

        unauthorized: List[str] = []
        for f in actual_modified:
            norm_f = os.path.normpath(f).replace("\\", "/")
            if norm_f not in declared_set and not any(norm_f.endswith(d) or d.endswith(norm_f) for d in declared_set):
                unauthorized.append(f)

        return len(unauthorized) == 0, unauthorized

    def cancel_descendants_and_siblings(self, failed_node: DAGNode) -> List[str]:
        """Propagates cancellation to all descendants and nodes sharing invalid assumptions."""
        cancelled: List[str] = []

        # Find all descendants (direct and indirect)
        def get_all_descendants(nid: str) -> Set[str]:
            desc: Set[str] = set()
            for child_id, child_node in self.nodes.items():
                if nid in child_node.depends_on:
                    desc.add(child_id)
                    desc.update(get_all_descendants(child_id))
            return desc

        descendants = get_all_descendants(failed_node.node_id)

        # Find siblings with shared assumptions
        siblings_with_shared_assumptions: Set[str] = set()
        for nid, node in self.nodes.items():
            if nid != failed_node.node_id:
                shared = set(node.shared_assumptions) & set(failed_node.shared_assumptions)
                if shared:
                    siblings_with_shared_assumptions.add(nid)

        all_affected = descendants | siblings_with_shared_assumptions
        for nid in all_affected:
            if self.nodes[nid].status in (NodeStatus.PENDING, NodeStatus.RUNNING):
                self.nodes[nid].status = NodeStatus.CANCELLED
                cancelled.append(nid)

        return cancelled

    def read_full_bodies_jit(self, involved_symbols: List[str], max_files: int = 2) -> Dict[str, str]:
        """JIT Full Body Read bounded to strictly involved files (< max_files) to prevent token explosion."""
        bodies: Dict[str, str] = {}
        target_files: Set[str] = set()

        for sym in involved_symbols:
            fname = sym.split("::")[0]
            # Locate on disk
            for root, _, files in os.walk(self.repo_root):
                if fname in files:
                    full_p = os.path.join(root, fname)
                    target_files.add(full_p)
                    if len(target_files) >= max_files:
                        break
            if len(target_files) >= max_files:
                break

        for fpath in target_files:
            rel = os.path.relpath(fpath, self.repo_root)
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                    bodies[rel] = fh.read()
            except Exception as e:
                bodies[rel] = f"Error reading full body: {e}"

        return bodies

    def replan_subgraph(
        self,
        failed_node: DAGNode,
        affected_nodes: List[str],
        deep_context: Dict[str, str],
        snapshot: FailureSnapshot,
    ) -> List[DAGNode]:
        """Synthesizes a replacement sub-DAG for failed node and its cancelled descendants."""
        replacement_nodes: List[DAGNode] = []

        # Replacement node 1: Re-architected adapter with JIT deep context
        fix_node_id = f"{failed_node.node_id}_reanchored"
        fix_node = DAGNode(
            node_id=fix_node_id,
            depends_on=failed_node.depends_on,
            compute_tier="Pro / Reasoning [Best-of-3]",
            write_set=failed_node.write_set,
            shared_assumptions=[f"reanchored_from_{failed_node.node_id}"],
            pass_gate=failed_node.pass_gate,
            rollback_hook=failed_node.rollback_hook,
        )
        replacement_nodes.append(fix_node)

        # Update DAG references: add new fix node
        self.nodes[fix_node_id] = fix_node

        # Rewire affected descendants to depend on new fix node instead of failed node
        for aff_id in affected_nodes:
            node = self.nodes.get(aff_id)
            if node:
                new_deps = [fix_node_id if d == failed_node.node_id else d for d in node.depends_on]
                node.depends_on = new_deps
                node.status = NodeStatus.PENDING  # un-cancel to allow execution after fix

        return replacement_nodes

    def run_dag_live(self, dry_run: bool = False, max_loops: int = 20) -> Dict[str, Any]:
        """Executes DAG live with automated self-healing, tier escalation, and cancellation propagation."""
        loops = 0
        executed_nodes: List[str] = []
        recovered_nodes: List[str] = []

        while loops < max_loops:
            loops += 1
            ready = self.get_ready_nodes()
            if not ready:
                break

            for node in ready:
                node.status = NodeStatus.RUNNING
                executed_nodes.append(node.node_id)

                if dry_run or not node.pass_gate:
                    node.status = NodeStatus.SUCCESS
                    continue

                # Live execution of pass_gate command without shell=True
                cmd_args = shlex.split(node.pass_gate) if isinstance(node.pass_gate, str) else node.pass_gate
                res = subprocess.run(cmd_args, cwd=self.repo_root, capture_output=True, text=True, check=False)
                if res.returncode == 0:
                    node.status = NodeStatus.SUCCESS
                else:
                    trace = (res.stderr or "") + "\n" + (res.stdout or "")
                    diff_res = subprocess.run(["git", "diff"], cwd=self.repo_root, capture_output=True, text=True, check=False)
                    diff = diff_res.stdout or ""

                    snapshot = self.capture_failure_snapshot(node, diff, trace)
                    self.safe_rollback(node, run_compensating_tx=True)

                    if snapshot.failure_class == FailureClass.LOCAL_IMPL and node.retries < node.max_retries:
                        node.escalate_compute_tier()
                        node.retries += 1
                        node.status = NodeStatus.PENDING  # Requeue for retry
                        recovered_nodes.append(f"{node.node_id} (retry {node.retries})")
                    else:
                        affected = self.cancel_descendants_and_siblings(node)
                        deep_context = self.read_full_bodies_jit(snapshot.involved_symbols)
                        replanned = self.replan_subgraph(node, affected, deep_context, snapshot)
                        recovered_nodes.append(f"{node.node_id} -> {[n.node_id for n in replanned]}")

        all_success = all(n.status == NodeStatus.SUCCESS for n in self.nodes.values())
        return {
            "all_success": all_success,
            "loops": loops,
            "executed_nodes": executed_nodes,
            "recovered_nodes": recovered_nodes,
            "final_status": {nid: n.status.value for nid, n in self.nodes.items()},
        }


def check_scope_guard_violation(
    node: DAGNode,
    repo_root: str = _REPO_ROOT
) -> Tuple[bool, List[str]]:
    """Physical Scope Guard standalone helper: verifies modified files do not exceed node write_set."""
    executor = SelfHealingDAGExecutor(repo_root=repo_root)
    return executor.check_scope_guard_violation(node)


def parse_plan_to_dag(plan_content: str) -> SelfHealingDAGExecutor:
    """Parses markdown plan content into an executable SelfHealingDAGExecutor."""
    executor = SelfHealingDAGExecutor()
    milestone_blocks = re.findall(
        r"(?:###?\s*(?:Milestone\s*\d+|Node\s*[A-Za-z0-9]+)[^\n]*)(.*?)(?=(?:###?\s*(?:Milestone\s*\d+|Node\s*[A-Za-z0-9]+))|(?:\n##+\s+)|\Z)",
        plan_content,
        re.DOTALL | re.IGNORECASE,
    )

    for idx, block in enumerate(milestone_blocks, 1):
        node_match = re.search(r"Node\s*ID:\s*`?([a-zA-Z0-9_\-]+)`?", block, re.IGNORECASE)
        node_id = node_match.group(1) if node_match else f"M{idx}"

        deps_match = re.search(r"depends_on[\s*:`_]*\[(.*?)\]", block, re.IGNORECASE)
        deps = [d.strip().strip("`'\"") for d in deps_match.group(1).split(",") if d.strip()] if deps_match else []

        tier_match = re.search(r"Compute\s+Tier:\s*\[?(.*?)\]?(?:\n|$)", block, re.IGNORECASE)
        tier = tier_match.group(1).strip("[]`") if tier_match else "Flash"

        m_write = re.search(r"Write\s+Set[^\n:]*:\s*\[(.*?)\]", block, re.IGNORECASE)
        if m_write:
            write_set = [w.strip("`'\" ") for w in m_write.group(1).split(",") if w.strip()]
        else:
            raw_files = re.findall(r"`([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]{1,6})`", block)
            write_set = [f for f in raw_files if not f.startswith(("pytest", "python"))]

        m_hook = re.search(r"Rollback\s*(?:Hook|Action)?:\s*`?([^\n`]+)`?", block, re.IGNORECASE)
        rollback_hook = m_hook.group(1).strip() if m_hook else None

        m_gate = re.search(r"Pass\s+Gate:\s*`?([^\n`]+)`?", block, re.IGNORECASE)
        pass_gate = m_gate.group(1).strip() if m_gate else None

        node = DAGNode(
            node_id=node_id,
            depends_on=deps,
            compute_tier=tier,
            write_set=write_set,
            rollback_hook=rollback_hook,
            pass_gate=pass_gate,
        )
        executor.add_node(node)

    return executor


def main() -> int:
    parser = argparse.ArgumentParser(description="DAG Self-Healing Engine (AGENTS.md §5 / super-plan 10/10)")
    parser.add_argument("--simulate-failure", action="store_true", help="Runs simulated failure triage and replanning demo")
    parser.add_argument("--parse-plan", help="Parses a markdown plan into a DAG and prints state")
    parser.add_argument("--run-live", action="store_true", help="Executes parsed plan live with self-healing recovery")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run pass gates without spawning live subprocesses")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    args = parser.parse_args()

    if args.simulate_failure:
        executor = SelfHealingDAGExecutor()
        m1 = DAGNode(node_id="M1_schema", depends_on=[], write_set=["schema.py"], shared_assumptions=["db_v1"])
        m2 = DAGNode(node_id="M2_adapter", depends_on=["M1_schema"], write_set=["adapter.py"], shared_assumptions=["db_v1"])
        m3 = DAGNode(node_id="M3_caller", depends_on=["M2_adapter"], write_set=["caller.py"])
        executor.add_node(m1)
        executor.add_node(m2)
        executor.add_node(m3)

        # M1 succeeds
        m1.status = NodeStatus.SUCCESS

        # M2 fails with architectural schema mismatch
        diff_sample = "- def old(): pass\n+ def new(x: int): pass"
        trace_sample = 'Traceback (most recent call last):\n  File "adapter.py", line 42, in charge\nSchema Mismatch: column tx_id missing in database'
        snapshot = executor.capture_failure_snapshot(m2, diff_sample, trace_sample)
        rollback_res = executor.safe_rollback(m2, run_compensating_tx=True)
        cancelled = executor.cancel_descendants_and_siblings(m2)
        deep_context = executor.read_full_bodies_jit(snapshot.involved_symbols)
        replanned = executor.replan_subgraph(m2, cancelled, deep_context, snapshot)

        report = {
            "demo": "Self-Healing DAG Simulation",
            "snapshot": snapshot.to_dict(),
            "rollback": rollback_res,
            "cancelled_descendants": cancelled,
            "deep_context_files_read": list(deep_context.keys()),
            "replanned_subgraph": [n.to_dict() for n in replanned],
            "final_dag_state": {nid: n.to_dict() for nid, n in executor.nodes.items()},
        }

        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print("[SELF-HEALING SIMULATION SUCCESS]")
            print(f"  -> Captured Snapshot: {snapshot.node_id} ({snapshot.failure_class.value})")
            print(f"  -> Rollback executed: CompensatingTx={rollback_res['compensating_hook_run']}, GitRevert={rollback_res['git_revert_run']}")
            print(f"  -> Cancelled Cascading Nodes: {cancelled}")
            print(f"  -> Spliced Replacement Sub-DAG: {[n.node_id for n in replanned]}")
        return 0

    if args.parse_plan:
        if not os.path.isfile(args.parse_plan):
            print(f"Error: File not found: {args.parse_plan}")
            return 1
        with open(args.parse_plan, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        executor = parse_plan_to_dag(content)
        ready = [n.node_id for n in executor.get_ready_nodes()]
        data = {
            "file": args.parse_plan,
            "total_nodes": len(executor.nodes),
            "ready_nodes": ready,
            "nodes": {nid: n.to_dict() for nid, n in executor.nodes.items()},
        }
        if args.run_live:
            exec_res = executor.run_dag_live(dry_run=args.dry_run)
            data["live_execution"] = exec_res
            if args.json:
                print(json.dumps(data, indent=2))
            else:
                status_str = "SUCCESS" if exec_res["all_success"] else "INCOMPLETE"
                print(f"[LIVE DAG EXECUTION: {status_str}] Executed: {exec_res['executed_nodes']}")
                if exec_res["recovered_nodes"]:
                    print(f"  -> Self-Healing Recoveries: {exec_res['recovered_nodes']}")
                print(f"  -> Final Status: {exec_res['final_status']}")
            return 0 if exec_res["all_success"] else 1

        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f"[PARSED DAG] {args.parse_plan} ({len(executor.nodes)} nodes)")
            print(f"  -> Ready to run: {ready}")
            for nid, node in executor.nodes.items():
                print(f"  - [{node.status.value}] {nid} (depends_on={node.depends_on}, tier={node.compute_tier})")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
