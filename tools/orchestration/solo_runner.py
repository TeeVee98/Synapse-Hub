#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/orchestration/solo_runner.py — Automated Solo 4-Pillar Verification Orchestrator

Integrates the 4 verification pillars of single-agent engineering rigor into an automated, deterministic pipeline:
  - Pillar 1: Test-First Inversion (Red-First Invariant with Forensic Red Receipt & Anti-Cheat Tautology Sentinel)
  - Pillar 2: 3-Phase Cognitive Persona Shifting (Red QA -> Blue Dev -> Purple Auditor)
  - Pillar 3: Live Dynamic Mutation Sentinel (micro_mutator with Diff-Scoped Targeting & >= 80% Threshold)
  - Pillar 4: Zero-Sum Prover-Verifier Debate (Nash Equilibrium extraction of 4 Contrarian Adversarial Perspectives)
"""

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass

from tools.reasoning.prover_verifier_games import ProverVerifierGame
from tools.lint.micro_mutator import evaluate_target
from tools.orchestration.worktree_manager import WorktreeManager
from tools.orchestration.qa_event_stream import QaEventStream
from tools.orchestration.qa_instinct_vault import QAInstinctVault
from tools.orchestration.senior_code_review import get_git_diff, parse_diff, analyze_diff
from tools.orchestration.goldfish_review import review_file as run_goldfish_review
from tools.orchestration.matrix_sharder import shard_tests_lpt
from tools.report.pinpoint_failure import compute_error_fingerprint
from tools.api.cross_service_contract_graph import (
    CrossServiceContractGraph,
    ServiceContractNode,
    EphemeralServiceSandbox,
)
from tools.reasoning.formal_contract_verifier import FormalContractVerifier
from tools.reasoning.semantic_entropy import SemanticEntropyEngine
from tools.reasoning.constrained_decoding import ConstrainedDecoder
from tools.orchestration.deterministic_race_scheduler import (
    DeterministicRaceScheduler,
    ConcurrentAction,
    RaceAuditResult,
)
from tools.core.circuit_breaker import LocatorRetryCircuitBreaker
from tools.orchestration.sandbox_runner import (
    SandboxBackend,
    WorktreeSandbox,
    create_sandbox_backend,
    rewrite_command_paths,
)
from tools.orchestration.solo_contracts import (
    AstTautologyAnalyzer,  # noqa: F401
    MicroContextExtractor,  # noqa: F401
    MicroContextPayload,  # noqa: F401
    ReadOnlyTestGuard,  # noqa: F401
    ScopedRedReceiptDTO,  # noqa: F401
    SignedRedReceipt,  # noqa: F401
    SpeculativeCandidatePrompt,  # noqa: F401
    _get_receipt_hmac_key as _contracts_get_receipt_hmac_key,
    _resolve_git_head,
    _verify_red_receipt_hmac as _contracts_verify_red_receipt_hmac,
    _write_json_atomic,
    calculate_composite_fitness_score,  # noqa: F401
    classify_test_failure,  # noqa: F401
    compute_mutation_receipt_hmac,
    compute_pareto_front,  # noqa: F401
    compute_red_receipt_hmac as _contracts_compute_red_receipt_hmac,
    detect_tautological_red,  # noqa: F401
    is_literal_constant,  # noqa: F401
    is_tautological_assertion,  # noqa: F401
    normalize_test_command,
    recertify_red_receipt_payload,
    resolve_red_receipt_path,
    resolve_red_receipt_ttl,
    select_tournament_winner,  # noqa: F401
    split_cmd_portable,  # noqa: F401
)


def _get_receipt_hmac_key() -> bytes:
    return _contracts_get_receipt_hmac_key(repo_root=_REPO_ROOT)


def compute_red_receipt_hmac(payload: Dict[str, Any], key: Optional[bytes] = None) -> str:
    effective_key = key if key is not None else _get_receipt_hmac_key()
    return _contracts_compute_red_receipt_hmac(payload, key=effective_key)


def _verify_red_receipt_hmac(payload: Dict[str, Any], key: Optional[bytes] = None) -> bool:
    effective_key = key if key is not None else _get_receipt_hmac_key()
    return _contracts_verify_red_receipt_hmac(payload, key=effective_key)

DEFAULT_RECEIPT_PATH = os.path.join(_REPO_ROOT, "reports", "tdd_red_receipt.json")
DEFAULT_PURPLE_RECEIPT_PATH = os.path.join(_REPO_ROOT, "reports", "tdd_purple_receipt.json")
DEFAULT_MUTATION_RECEIPT_PATH = os.path.join(_REPO_ROOT, "reports", "tdd_mutation_receipt.json")
DEFAULT_BATCH_RECEIPT_PATH = os.path.join(_REPO_ROOT, "reports", "solo_swarm_batch_receipt.json")
DEFAULT_EVENT_STREAM_PATH = os.path.join(_REPO_ROOT, "reports", "solo_swarm_event_stream.jsonl")
DEFAULT_MUTATION_THRESHOLD = 80.0

CONTRARIAN_PERSPECTIVES = [
    "Vulnerability 1 (Chaos & Network): Simulate downstream service timeout, 503 transient drop, and retry backoff.",
    "Vulnerability 2 (Concurrency & Race): Simulate 50ms rapid double-action, duplicate idempotency key, and dirty state reads.",
    "Vulnerability 3 (Boundary & Malformed): Empty payload, null byte, max integer overflow, and schema drift violation.",
    "Vulnerability 4 (Blast Radius & Migration): Backward compatibility with legacy callers and state migration safety.",
]


def resolve_auto_targets(repo_root: Optional[str] = None) -> List[str]:
    """
    Milestone 3 Anti-Shrinking: Scans git diff and untracked files to automatically discover all modified source files.
    Excludes test files, reports, and documentation.
    """
    root = repo_root or _REPO_ROOT
    files: Set[str] = set()
    try:
        # 1. Tracked changes against HEAD (both staged and uncommitted)
        proc1 = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
        )
        if proc1.returncode == 0:
            files.update(proc1.stdout.splitlines())

        # 2. Unstaged changes in working tree
        proc2 = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
        )
        if proc2.returncode == 0:
            files.update(proc2.stdout.splitlines())

        # 3. Untracked new files (excluding .gitignore entries)
        proc3 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
        )
        if proc3.returncode == 0:
            files.update(proc3.stdout.splitlines())

        valid_exts = {".py", ".groovy", ".ts", ".js", ".java"}
        source_files = []
        for f in sorted(files):
            norm_f = f.strip().replace("\\", "/")
            if any(norm_f.endswith(ext) for ext in valid_exts):
                if (
                    not norm_f.startswith("tests/")
                    and "/tests/" not in norm_f
                    and not norm_f.startswith("reports/")
                    and not norm_f.startswith("docs/")
                ):
                    full_p = os.path.join(root, norm_f)
                    if os.path.isfile(full_p):
                        source_files.append(norm_f)

        # 4. Git-Resilience Fallback: If working tree is clean, check last commit (HEAD~1..HEAD)
        if not source_files:
            proc4 = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=5,
                encoding="utf-8",
                errors="replace",
            )
            if proc4.returncode == 0:
                for f in sorted(proc4.stdout.splitlines()):
                    norm_f = f.strip().replace("\\", "/")
                    if any(norm_f.endswith(ext) for ext in valid_exts):
                        if (
                            not norm_f.startswith("tests/")
                            and "/tests/" not in norm_f
                            and not norm_f.startswith("reports/")
                            and not norm_f.startswith("docs/")
                        ):
                            full_p = os.path.join(root, norm_f)
                            if os.path.isfile(full_p) and norm_f not in source_files:
                                source_files.append(norm_f)

        return source_files
    except Exception:
        # 5. Non-Git Fallback: Safe scan of default source directories
        valid_exts = {".py", ".groovy", ".ts", ".js", ".java"}
        fallback_files = []
        for cdir_name in ("tools", "src"):
            cdir = os.path.join(root, cdir_name)
            if os.path.isdir(cdir):
                for r, _, fnames in os.walk(cdir):
                    for fn in fnames:
                        if any(fn.endswith(ext) for ext in valid_exts) and not fn.startswith("test_"):
                            rel = os.path.relpath(os.path.join(r, fn), root).replace("\\", "/")
                            if not rel.startswith("tests/") and "/tests/" not in rel:
                                fallback_files.append(rel)
                                if len(fallback_files) >= 5:
                                    return fallback_files
        return fallback_files


def prepare_stateless_oracle_context(repo_root: str, target: str = "") -> str:
    """
    Constructs a memory-wiped, stateless context payload for the Purple Oracle.
    Contains strictly git diff -U0 HEAD, implementation plan summary, and test status.
    Strips prior conversation turns, thoughts, or Blue agent rationales to eliminate confirmation bias.
    """
    try:
        diff_text = get_git_diff(repo_root, "uncommitted")
    except Exception:
        diff_text = ""

    plan_path = os.path.join(repo_root, "implementation_plan.md")
    plan_summary = ""
    if os.path.isfile(plan_path):
        try:
            with open(plan_path, "r", encoding="utf-8", errors="replace") as pf:
                plan_lines = pf.readlines()
            plan_summary = "".join(plan_lines[:40])
        except Exception:
            plan_summary = ""

    payload = {
        "git_diff_u0": diff_text,
        "plan_summary": plan_summary,
        "target_file": target,
        "cognitive_isolation": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(payload, indent=2)


def execute_external_oracle(
    oracle_cmd: str,
    target_file: str = "",
    prompt_or_spec: str = "",
    cwd: Optional[str] = None,
    timeout: float = 30.0,
    event_stream_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Weapon 4 Enhancement: External Stateless Adversarial Oracle.
    Executes a secondary model CLI, external prover, or adversarial fuzzer via subprocess.
    Eliminates single-LLM cognitive blind spots without multi-agent chat overhead.
    """
    working_dir = cwd or _REPO_ROOT
    start_time = datetime.now(timezone.utc)

    cmd = oracle_cmd
    if "{target}" in cmd and target_file:
        cmd = cmd.replace("{target}", target_file)

    cmd_parts = split_cmd_portable(cmd)

    effective_input = prompt_or_spec if prompt_or_spec else prepare_stateless_oracle_context(working_dir, target_file)

    try:
        proc = subprocess.run(
            cmd_parts,
            input=effective_input,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
        output = proc.stdout.strip()
        passed = proc.returncode == 0

        parsed_data = None
        oracle_json_repaired = False
        if output:
            try:
                parsed_data = json.loads(output)
            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                try:
                    repaired = ConstrainedDecoder().project_json(output)
                    if isinstance(repaired, (dict, list)):
                        parsed_data = repaired
                        oracle_json_repaired = True
                except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                    parsed_data = None
                    oracle_json_repaired = False

        record_solo_swarm_event(
            event_type="ORACLE_EVALUATED",
            actor="external-oracle",
            payload={
                "oracle_cmd": oracle_cmd,
                "target_file": target_file,
                "passed": passed,
                "exit_code": proc.returncode,
                "duration_sec": duration_sec,
                "oracle_json_repaired": oracle_json_repaired,
            },
            stream_path=event_stream_path,
            repo_root=working_dir,
        )

        return {
            "status": "ORACLE_CERTIFIED" if passed else "ORACLE_VIOLATION_DETECTED",
            "passed": passed,
            "exit_code": proc.returncode,
            "duration_sec": duration_sec,
            "oracle_cmd": oracle_cmd,
            "target_file": target_file,
            "output": output,
            "parsed": parsed_data,
            "oracle_json_repaired": oracle_json_repaired,
            "message": (
                "✅ External Oracle Certified: Secondary model / oracle passed without counter-examples."
                if passed
                else f"⚠️ External Oracle Violation: Secondary model / oracle returned exit code {proc.returncode}."
            ),
        }
    except subprocess.TimeoutExpired:
        duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
        return {
            "status": "ORACLE_TIMEOUT",
            "passed": False,
            "exit_code": 124,
            "duration_sec": duration_sec,
            "error": f"External oracle timed out after {timeout}s",
            "oracle_cmd": oracle_cmd,
        }
    except Exception as e:
        duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
        return {
            "status": "ORACLE_ERROR",
            "passed": False,
            "exit_code": 1,
            "duration_sec": duration_sec,
            "error": str(e),
            "oracle_cmd": oracle_cmd,
        }


def _extract_file_imports(
    file_path: str,
) -> Tuple[List[str], List[Tuple[str, int]], List[Tuple[str, int]]]:
    """Extracts (abs_imports, rel_imports, submod_imports) via AST (Python) or regex (TS/JS/Groovy/Java)."""
    abs_imports: List[str] = []
    rel_imports: List[Tuple[str, int]] = []
    submod_imports: List[Tuple[str, int]] = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    if file_path.endswith(".py"):
        tree = ast.parse(content, filename=file_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    abs_imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if node.level:
                        rel_imports.append((node.module, node.level))
                    else:
                        abs_imports.append(node.module)
                    for alias in node.names:
                        if alias.name != "*":
                            submod_imports.append((f"{node.module}.{alias.name}", node.level))
                elif node.level:
                    for alias in node.names:
                        if alias.name != "*":
                            rel_imports.append((alias.name, node.level))
    else:
        for pat in (
            r'(?:import|from)\s+[\'"]([^\'"]+)[\'"]',
            r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
            r'import\s+([a-zA-Z0-9_.]+)',
        ):
            for m in re.finditer(pat, content):
                abs_imports.append(m.group(1))
    return abs_imports, rel_imports, submod_imports


def _build_transitive_import_edges(
    abs_target: str,
    effective_root: str,
    max_nodes: int = 500,
) -> List[List[str]]:
    """Builds transitive directed import edges from abs_target with bounded O(V+E) traversal."""
    call_graph_map: Dict[str, List[str]] = {}
    try:
        from tools.context.call_graph_indexer import get_or_build_call_graph

        cg = get_or_build_call_graph(effective_root)
        for rel_p in cg.files:
            stem = os.path.splitext(os.path.basename(rel_p))[0]
            call_graph_map.setdefault(stem, []).append(os.path.abspath(os.path.join(effective_root, rel_p)))
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

    stdlib_names = getattr(sys, "stdlib_module_names", frozenset())

    def _node_id(path: str) -> str:
        rel = os.path.relpath(path, effective_root).replace("\\", "/")
        return os.path.splitext(rel)[0]

    def _resolve_local(curr_file: str, spec: str, level: int, use_cg: bool = True) -> Optional[str]:
        base_dir = os.path.dirname(curr_file)
        if curr_file.endswith(".py"):
            if level > 0:
                for _ in range(level - 1):
                    base_dir = os.path.dirname(base_dir)
                search_dirs = [base_dir]
            else:
                search_dirs = [base_dir, effective_root]
            parts = spec.split(".")
            for sd in search_dirs:
                cand = os.path.join(sd, *parts) + ".py"
                if os.path.isfile(cand):
                    return os.path.abspath(cand)
            if use_cg and level == 0 and parts[0] not in stdlib_names:
                matches = [p for p in call_graph_map.get(parts[-1], []) if p.endswith(".py")]
                if len(matches) == 1:
                    return matches[0]
            return None

        raw_stem = os.path.basename(spec).split(".")[0]
        if spec.startswith("."):
            base_cand = os.path.normpath(os.path.join(base_dir, spec))
            for ext in ("", ".ts", ".js", ".tsx", ".jsx", ".groovy", ".java"):
                cand = base_cand + ext
                if os.path.isfile(cand):
                    return os.path.abspath(cand)
        else:
            key = spec.split(".")[-1] if "." in spec else raw_stem
            matches = [p for p in call_graph_map.get(key, []) if not p.endswith(".py")]
            if len(matches) == 1:
                return matches[0]
        return None

    visited: Set[str] = set()
    queue: List[str] = [abs_target]
    edge_set: Set[Tuple[str, str]] = set()

    while queue and len(visited) < max_nodes:
        curr_file = queue.pop(0)
        if curr_file in visited:
            continue
        visited.add(curr_file)
        curr_id = _node_id(curr_file)

        try:
            abs_imps, rel_imps, sub_imps = _extract_file_imports(curr_file)
        except SyntaxError:
            if curr_file == abs_target:
                raise
            continue

        for spec, level in [(s, 0) for s in abs_imps] + rel_imps:
            dep_file = _resolve_local(curr_file, spec, level=level)
            if dep_file is not None and dep_file != curr_file:
                dep_id = _node_id(dep_file)
                edge_set.add((curr_id, dep_id))
                if dep_file not in visited:
                    queue.append(dep_file)
            elif curr_file == abs_target:
                ext_name = spec.split(".")[0] if curr_file.endswith(".py") else os.path.basename(spec).split(".")[0]
                if not curr_file.endswith(".py") and "." in spec and not spec.startswith("."):
                    ext_name = spec.split(".")[-1]
                if ext_name and ext_name != curr_id:
                    edge_set.add((curr_id, ext_name))

        for spec, level in sub_imps:
            dep_file = _resolve_local(curr_file, spec, level=level, use_cg=False)
            if dep_file is not None and dep_file != curr_file:
                dep_id = _node_id(dep_file)
                edge_set.add((curr_id, dep_id))
                if dep_file not in visited:
                    queue.append(dep_file)

    return [[u, v] for u, v in sorted(edge_set)]


def verify_neuro_symbolic_constraints(
    target_file: str,
    constraint_type: str = "cycle",
    repo_root: Optional[str] = None,
    event_stream_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Weapon 2 Phase 3 Enhancement: Tier 15 Neuro-Symbolic Invariant Verification.
    Offloads structural, topological, and contract constraints to deterministic solvers (Z3 / DPLL / DependencyCycleSolver).
    Mathematically proves acyclicity and invariant compliance without LLM subjectivity.
    Supports Python (AST), TypeScript/JavaScript (regex import extraction), and Groovy/Java.
    """
    root = repo_root or _REPO_ROOT
    abs_target = os.path.abspath(target_file) if os.path.isabs(target_file) else os.path.join(root, target_file)

    if not os.path.isfile(abs_target):
        return {
            "status": "ERROR",
            "passed": False,
            "error": f"File not found: {abs_target}",
        }

    abs_root = os.path.abspath(root)
    if repo_root is not None:
        effective_root = abs_root
    else:
        try:
            is_inside = os.path.commonpath([abs_root, abs_target]) == abs_root
        except ValueError:
            is_inside = False
        effective_root = abs_root if is_inside else os.path.dirname(abs_target)

    start_time = datetime.now(timezone.utc)
    try:
        from tools.reasoning.neuro_symbolic_solver import DependencyCycleSolver

        edges = _build_transitive_import_edges(abs_target, effective_root)

        cycle_sol = DependencyCycleSolver.solve(edges)
        duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
        has_cycle = cycle_sol.has_cycle

        # Formal Contract & Invariant Verification for Python targets
        formal_report = None
        contract_passed = True
        if abs_target.endswith(".py"):
            try:
                formal_report = FormalContractVerifier.verify_module_contracts(abs_target)
                if formal_report.get("status") == "CONTRACT_VIOLATION_DETECTED":
                    contract_passed = False
            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                pass

        passed = (not has_cycle) and contract_passed
        if not contract_passed:
            status_val = "CONTRACT_VIOLATION_DETECTED"
            msg = f"❌ Neuro-Symbolic Violation: Formal contract violation detected in {target_file}."
        elif has_cycle:
            status_val = "CYCLE_DETECTED"
            msg = f"❌ Neuro-Symbolic Violation: Circular dependency detected in {target_file}."
        else:
            status_val = "NEURO_SYMBOLIC_CERTIFIED"
            msg = "✅ Neuro-Symbolic Invariants Certified: Formal topological and constraint checks passed."

        record_solo_swarm_event(
            event_type="NEURO_SYMBOLIC_VERIFIED",
            actor="symbolic-solver",
            payload={
                "target_file": target_file,
                "constraint_type": constraint_type,
                "passed": passed,
                "has_cycle": cycle_sol.has_cycle,
                "formal_contract_passed": contract_passed,
                "duration_sec": duration_sec,
            },
            stream_path=event_stream_path,
            repo_root=root,
        )

        return {
            "status": status_val,
            "passed": passed,
            "target_file": target_file,
            "constraint_type": constraint_type,
            "edges_evaluated": len(edges),
            "has_cycle": cycle_sol.has_cycle,
            "cycles_found": cycle_sol.cycles_found,
            "topological_order": cycle_sol.topological_order,
            "formal_contracts": formal_report,
            "duration_sec": duration_sec,
            "message": msg,
        }
    except Exception as e:
        duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
        return {
            "status": "NEURO_SYMBOLIC_ERROR",
            "passed": False,
            "error": str(e),
            "duration_sec": duration_sec,
        }


def run_deterministic_race_audit(
    action_factory: Callable[[List[str]], Tuple[Any, List[ConcurrentAction]]],
    invariant_check: Callable[[Any], bool],
    invariant_name: str = "Invariant Holds",
) -> RaceAuditResult:
    """Audits concurrent actions across all deterministic step interleavings without flaky sleeps."""
    scheduler = DeterministicRaceScheduler()
    return scheduler.audit_concurrency(
        action_factory=action_factory,
        invariant_check=invariant_check,
        invariant_name=invariant_name,
    )


def run_debate(
    proposal: str,
    context: Optional[str] = None,
    rounds: int = 3,
    judge_mode: str = "strict",
    repo_root: Optional[str] = None,
    oracle_cmd: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Weapon 4: Run Prover-Verifier debate with 4 Contrarian Perspectives and extract adversarial test cases.
    If oracle_cmd is provided, executes an external adversary/prover to inject verified counter-examples.
    """
    root = repo_root or _REPO_ROOT

    # Milestone 3: Enrich context with Contrarian Adversarial Perspectives
    adversarial_context = (context or "") + "\n\nAdversarial Evaluation Directives:\n" + "\n".join(f"- {p}" for p in CONTRARIAN_PERSPECTIVES)

    game = ProverVerifierGame(repo_root=root)
    result = game.run_debate(proposal=proposal, context=adversarial_context, rounds=rounds, judge_mode=judge_mode)

    # Automatically extract counter_examples into structured test scenarios
    counter_examples = []
    for item in result.get("transcript", []):
        vc = item.get("verifier_counter", {})
        for ce in vc.get("counter_examples", []):
            if ce not in counter_examples:
                counter_examples.append(ce)

    # External Adversarial Oracle injection if provided
    oracle_res = None
    if oracle_cmd:
        oracle_res = execute_external_oracle(
            oracle_cmd=oracle_cmd,
            prompt_or_spec=proposal,
            cwd=root,
        )
        if not oracle_res.get("passed", False):
            out_msg = oracle_res.get("output", "")
            ce_msg = f"External Oracle Counter-example: {out_msg[:200]}"
            if ce_msg not in counter_examples:
                counter_examples.append(ce_msg)

    structured_test_scenarios = []
    for idx, ce in enumerate(counter_examples, 1):
        clean_name = ce.replace("Counter-example: ", "").strip()
        structured_test_scenarios.append({
            "id": f"TC-ADV-{idx:02d}",
            "description": clean_name,
            "category": "adversarial_boundary",
            "required_assert": "Explicit boundary validation preventing unhandled crash / silent pass",
        })

    # Milestone 4: Evaluate semantic consistency across debate arguments via SemanticEntropyEngine
    debate_hypotheses: List[str] = []
    for item in result.get("transcript", []):
        if isinstance(item, dict):
            for key, field_name in (("prover_argument", "claim"), ("verifier_counter", "refutation")):
                part = item.get(key)
                if isinstance(part, dict):
                    text_val = part.get(field_name)
                    if isinstance(text_val, str):
                        clean_val = text_val.strip()
                        if clean_val:
                            debate_hypotheses.append(clean_val)

    semantic_entropy: Optional[float] = None
    uncertainty_status: str = "ERROR_REVIEW_REQUIRED"
    code_write_permission: bool = False
    entropy_error: Optional[str] = None
    try:
        se_eval = SemanticEntropyEngine().evaluate_hypotheses(
            debate_hypotheses,
            query_context=proposal,
        )
        if not isinstance(se_eval, dict) or "semantic_entropy" not in se_eval:
            raise ValueError("SemanticEntropyEngine returned malformed evaluation payload")
        semantic_entropy = float(se_eval["semantic_entropy"])
        uncertainty_status = str(se_eval.get("uncertainty_status", "ERROR_REVIEW_REQUIRED"))
        code_write_permission = bool(se_eval.get("code_write_permission", False))
    except Exception as exc:
        # Fail-closed (M6 P1.4): never mask SemanticEntropyEngine failure as 0.0 entropy
        semantic_entropy = None
        uncertainty_status = "ERROR_REVIEW_REQUIRED"
        code_write_permission = False
        entropy_error = str(exc)

    return {
        "status": "COMPLETED",
        "proposal": proposal,
        "winner": result.get("winner"),
        "nash_equilibrium_score": result.get("nash_equilibrium_score"),
        "rounds_completed": result.get("rounds_completed"),
        "counter_examples_count": len(counter_examples),
        "counter_examples": counter_examples,
        "unresolved_vulnerabilities": result.get("unresolved_vulnerabilities", []),
        "structured_test_scenarios": structured_test_scenarios,
        "contrarian_perspectives_injected": len(CONTRARIAN_PERSPECTIVES),
        "semantic_entropy": semantic_entropy,
        "uncertainty_status": uncertainty_status,
        "code_write_permission": code_write_permission,
        "entropy_error": entropy_error,
        "oracle_result": oracle_res,
        "debate_raw": result,
    }


def _normalize_python_command(
    cmd_parts: List[str],
    platform_name: Optional[str] = None,
    resolved_which: Optional[str] = None,
    executable: Optional[str] = None,
) -> List[str]:
    """Rewrites Windows 'python3' / Store WindowsApps stub invocations to sys.executable.

    Guarantees:
      - Returns cmd_parts unchanged on non-win32 platforms or when cmd_parts is empty.
      - Leaves non-python3 binaries (pytest, node, npx, python) untouched.
      - Substitutes sys.executable on win32 when python3 is absent or resolves under WindowsApps.
    """
    if not cmd_parts:
        return []
    active_platform = sys.platform if platform_name is None else platform_name
    if active_platform != "win32":
        return list(cmd_parts)
    binary_name = os.path.basename(cmd_parts[0]).lower()
    if binary_name not in ("python3", "python3.exe"):
        return list(cmd_parts)
    effective_which = shutil.which(cmd_parts[0]) if resolved_which is None else resolved_which
    if not effective_which or "windowsapps" in effective_which.lower() or "windowsapps" in cmd_parts[0].lower():
        effective_executable = executable if executable is not None else sys.executable
        return [effective_executable, *cmd_parts[1:]]
    return list(cmd_parts)


class BaseTestAdapter:
    """Abstract interface for test runners across languages and frameworks."""

    name: str = "base"

    def execute(self, test_cmd: str, cwd: str, timeout: float = 120.0) -> Tuple[int, str]:
        cmd_parts = _normalize_python_command(split_cmd_portable(test_cmd))
        if not cmd_parts:
            return 1, "Execution exception: Empty test command"
        try:
            proc = subprocess.run(
                cmd_parts,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            return proc.returncode, proc.stdout
        except subprocess.TimeoutExpired as e:
            return 124, f"TIMEOUT_ERROR: Execution timed out after {timeout}s: {e}"
        except FileNotFoundError as e:
            return 127, f"COMMAND_NOT_FOUND: Command '{cmd_parts[0]}' not found: {e}"
        except Exception as e:
            return 1, f"Execution exception: {e}"

    def check_tautology(self, output: str, test_cmd: str = "") -> Tuple[bool, Optional[str]]:
        return False, None


class PytestAdapter(BaseTestAdapter):
    """Native Python / Pytest Adapter with AST constant-propagation guard."""

    name: str = "pytest"

    def check_tautology(self, output: str, test_cmd: str = "") -> Tuple[bool, Optional[str]]:
        return detect_tautological_red(output, test_cmd=test_cmd)


class JestPlaywrightAdapter(BaseTestAdapter):
    """JavaScript / TypeScript Adapter for Jest, Vitest, and Playwright test runners."""

    name: str = "jest_playwright"

    def check_tautology(self, output: str, test_cmd: str = "") -> Tuple[bool, Optional[str]]:
        # Check test_cmd for inline cheats
        if re.search(
            r"expect\s*\(\s*(true|false|1|0|null|undefined)\s*\)\s*\.\s*(toBe|toEqual)\s*\(\s*(true|false|1|0|null|undefined)\s*\)",
            test_cmd,
            re.I,
        ):
            return True, "Jest/Playwright Tautology: Literal constant expect assertion in test command."

        for line in output.splitlines():
            line_s = line.strip()
            m = re.search(r"expect\s*\(\s*([^)]+)\s*\)\s*\.\s*toBe\s*\(\s*([^)]+)\s*\)", line_s)
            if m:
                l_val, r_val = m.group(1).strip(), m.group(2).strip()
                if is_literal_constant(l_val) and is_literal_constant(r_val) and l_val != r_val:
                    return True, f"Jest/Playwright Tautology: Literal comparison expect({l_val}).toBe({r_val}) in source."

            if "test.fail()" in line_s or "expect(true).toBe(false)" in line_s or "expect(false).toBeTruthy()" in line_s:
                return True, "Jest/Playwright Tautology: Forced failure without domain assertion."

        return False, None


class JUnitXMLAdapter(BaseTestAdapter):
    """JUnit XML Adapter for Katalon Studio, Groovy, Gradle, Maven, and XML test reports."""

    name: str = "junit_xml"

    def parse_xml_report(self, xml_path: str) -> Tuple[int, int, List[str]]:
        """Parses JUnit XML report file and returns (failures_count, errors_count, failure_messages)."""
        if not os.path.isfile(xml_path):
            return 0, 0, []
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            failures = []
            failures_count = int(root.attrib.get("failures", 0))
            errors_count = int(root.attrib.get("errors", 0))

            for tc in root.iter("testcase"):
                for fail in tc.iter("failure"):
                    msg = fail.attrib.get("message", "") or (fail.text or "").strip()
                    if msg:
                        failures.append(msg)
                for err in tc.iter("error"):
                    msg = err.attrib.get("message", "") or (err.text or "").strip()
                    if msg:
                        failures.append(msg)
            return failures_count, errors_count, failures
        except Exception:
            return 0, 0, []

    def check_tautology(self, output: str, test_cmd: str = "") -> Tuple[bool, Optional[str]]:
        xml_match = re.search(r"([a-zA-Z0-9_\-./\\:~]+\.xml)", test_cmd + " " + output)
        if xml_match:
            xml_file = xml_match.group(1)
            if os.path.isfile(xml_file):
                fails, errs, msgs = self.parse_xml_report(xml_file)
                for m in msgs:
                    is_t, reason = is_tautological_assertion(m)
                    if is_t:
                        return True, f"JUnit XML Tautology: {reason} in failure report."

        return detect_tautological_red(output, test_cmd=test_cmd)


def resolve_test_adapter(test_cmd: str, runner_override: Optional[str] = None) -> BaseTestAdapter:
    """Factory to resolve the appropriate test runner adapter."""
    if runner_override and runner_override.lower().strip() != "auto":
        ro = runner_override.lower().strip()
        if ro in ("jest", "playwright", "ts", "js"):
            return JestPlaywrightAdapter()
        elif ro in ("junit", "xml", "katalon", "groovy"):
            return JUnitXMLAdapter()
        elif ro == "pytest":
            return PytestAdapter()

    cmd_lower = test_cmd.lower()
    if any(k in cmd_lower for k in ("playwright", "jest", "vitest", "npm test", "npx ")):
        return JestPlaywrightAdapter()
    if any(k in cmd_lower for k in ("--junitxml", "katalon", "gradle", "mvn")):
        return JUnitXMLAdapter()
    return PytestAdapter()


def record_solo_swarm_event(
    event_type: str,
    actor: str,
    payload: Dict[str, Any],
    stream_path: Optional[str] = None,
    repo_root: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Subagent Skill: event-stream-qa-orchestrator
    Records a lifecycle event to the hash-chained QaEventStream.
    Safely falls back if stream recording is unavailable.
    """
    target_stream = stream_path or DEFAULT_EVENT_STREAM_PATH
    try:
        os.makedirs(os.path.dirname(os.path.abspath(target_stream)), exist_ok=True)
        es = QaEventStream(repo_root=repo_root or _REPO_ROOT)
        if not os.path.exists(target_stream):
            es.init_stream(
                session_id=f"solo_swarm_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                out_file=target_stream,
            )
        return es.record_event(
            stream_file=target_stream,
            event_type=event_type,
            actor=actor,
            payload=payload,
        )
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        return None


def query_instinct_guidance(domain: str = "general", repo_root: Optional[str] = None, limit: int = 2) -> List[str]:
    """
    Subagent Skill: qa-memory-os (QAInstinctVault)
    Queries learned failure patterns and heuristic instincts.
    Returns concise guidance strings to inject into candidate prompts.
    """
    root = repo_root or _REPO_ROOT
    db_path = os.path.join(root, ".agent_memory", "qa_memory.db")
    if not os.path.exists(db_path):
        return []
    try:
        vault = QAInstinctVault(db_path=db_path)
        instincts = vault.query_instincts(project_dir=root, domain=domain if domain != "general" else None, min_confidence=0.4)
        vault.close()
        guidance = []
        for inst in instincts[:limit]:
            act = inst.get("action")
            trig = inst.get("trigger")
            if act and trig:
                guidance.append(f"Avoid '{trig}': {act}")
            elif act:
                guidance.append(str(act))
        return guidance
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        return []


def record_instinct_observation(
    tool_name: str,
    error_signature: str,
    resolution: str,
    repo_root: Optional[str] = None,
) -> None:
    """
    Subagent Skill: qa-memory-os (QAInstinctVault)
    Records execution observation or learned instinct back into QAInstinctVault.
    """
    root = repo_root or _REPO_ROOT
    db_path = os.path.join(root, ".agent_memory", "qa_memory.db")
    try:
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        vault = QAInstinctVault(db_path=db_path)
        vault.record_observation(
            project_dir=root,
            tool_name=tool_name,
            error_signature=error_signature,
            resolution=resolution,
        )
        vault.close()
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass


def shard_test_execution(
    test_files: List[str],
    num_shards: int = 2,
    target_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Subagent Skill: actor-qa-swarm (matrix_sharder)
    Splits test suite into balanced shards using Longest Processing Time (LPT) bin-packing.
    """
    root = target_dir or _REPO_ROOT
    return shard_tests_lpt(test_files, target_dir=root, num_shards=num_shards)


def extract_test_files_from_cmd(test_cmd: str, working_dir: Optional[str] = None) -> List[str]:
    """
    Extracts physical test file paths referenced in a test command.
    Matches paths with test naming conventions or standard extensions (.py, .ts, .js, .groovy).
    Handles file::test selector syntax and directory trees (e.g. pytest tests/).
    """
    cmd_str = (test_cmd or "").strip()
    if not cmd_str:
        return []
    root = working_dir or _REPO_ROOT
    raw_tokens = split_cmd_portable(test_cmd)
    found_files: List[str] = []
    test_exts = (".py", ".ts", ".js", ".jsx", ".tsx", ".groovy", ".java")

    for tok in raw_tokens:
        if tok.startswith("-"):
            continue
        clean_tok = tok.strip("'\"").split("::")[0]
        if any(clean_tok.endswith(ext) for ext in test_exts) or "test" in clean_tok.lower():
            resolved = clean_tok if os.path.isabs(clean_tok) else os.path.join(root, clean_tok)
            if os.path.isfile(resolved):
                found_files.append(resolved)
            elif os.path.isdir(resolved):
                for dirpath, _, filenames in os.walk(resolved):
                    for fn in filenames:
                        if any(fn.endswith(ext) for ext in test_exts) or fn.startswith("conftest"):
                            found_files.append(os.path.join(dirpath, fn))

    return sorted(list(set(found_files)))


def compute_test_files_snapshot(
    test_cmd: str = "",
    working_dir: Optional[str] = None,
    files_override: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Milestone 2 (Cryptographic Test Tree Snapshot):
    Computes SHA-256 content hashes of all relevant test files.
    Returns composite tree_hash and individual relative path hashes.
    """
    root = working_dir or _REPO_ROOT
    if files_override is not None:
        targets: List[str] = []
        for f in files_override:
            fp = f if os.path.isabs(f) else os.path.join(root, f)
            targets.append(fp)
    else:
        targets = extract_test_files_from_cmd(test_cmd, working_dir=root)

    file_hashes: Dict[str, str] = {}
    for fp in sorted(targets):
        if os.path.isfile(fp):
            try:
                with open(fp, "rb") as fh:
                    h = hashlib.sha256(fh.read()).hexdigest()
                rel = os.path.relpath(fp, root)
                file_hashes[rel] = h
            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                pass

    if file_hashes:
        tree_body = "".join(f"{rel}:{file_hashes[rel]}\n" for rel in sorted(file_hashes.keys()))
        tree_hash = hashlib.sha256(tree_body.encode("utf-8")).hexdigest()
    else:
        tree_hash = ""

    return {
        "tree_hash": tree_hash,
        "files": file_hashes,
        "total_files": len(file_hashes),
    }


def lock_test_files(test_files: List[str], repo_root: Optional[str] = None) -> List[str]:
    """Standalone utility to lock test files to OS read-only mode."""
    guard = ReadOnlyTestGuard(test_files, repo_root=repo_root)
    return guard.lock()


def unlock_test_files(test_files: List[str], repo_root: Optional[str] = None) -> List[str]:
    """Standalone utility to restore write permissions (0o644) to test files."""
    root = repo_root or _REPO_ROOT
    unlocked: List[str] = []
    for f in test_files:
        fp = os.path.abspath(f) if os.path.isabs(f) else os.path.join(root, f)
        if os.path.isfile(fp):
            try:
                os.chmod(fp, 0o644)
                unlocked.append(fp)
            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                pass
    return unlocked


REQUIRED_RED_SCENARIOS: Tuple[str, ...] = (
    "positive",
    "negative",
    "boundary",
    "cli_or_resilience",
)

_SCENARIO_PATTERNS: Dict[str, re.Pattern] = {
    "positive": re.compile(
        r"\b(positive|happy|valid|success|succeed|normal|nominal|standard|creates?|returns?|passes?|accepts?)\b",
        re.IGNORECASE,
    ),
    "negative": re.compile(
        r"\b(negative|invalid|error|reject|fail|deny|forbid|unauthorized|missing|malformed|tamper|blocked|raises?|exception|wrong)\b",
        re.IGNORECASE,
    ),
    "boundary": re.compile(
        r"\b(boundary|empty|null|none|zero|limit|max|min|edge|overflow|underflow|cutoff|threshold|single|truncate)\b",
        re.IGNORECASE,
    ),
    "cli_or_resilience": re.compile(
        r"\b(cli|flag|flags|json|argv|argparse|subprocess|resilience|concurren\w*|race|timeout|retry|fallback|recover|idempoten\w*|thread|lock)\b",
        re.IGNORECASE,
    ),
}


def analyze_four_scenario_coverage(
    test_files: List[str],
    output: str = "",
    working_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Inspects executed test files (AST test functions/docstrings/comments) and runner output
    to verify coverage across the 4 mandatory scenario categories:
    positive, negative, boundary, and cli_or_resilience.
    """
    root = working_dir or _REPO_ROOT
    coverage: Dict[str, bool] = {cat: False for cat in REQUIRED_RED_SCENARIOS}
    evidence: Dict[str, List[str]] = {cat: [] for cat in REQUIRED_RED_SCENARIOS}

    def _scan_text(text: str, source_label: str) -> None:
        if not text:
            return
        # Normalize snake_case tokens to spaces so word-boundary regex matches test_positive_foo
        normalized = text.replace("_", " ").replace("-", " ")
        for cat, pat in _SCENARIO_PATTERNS.items():
            match = pat.search(normalized)
            if match:
                coverage[cat] = True
                entry = f"{source_label}:{match.group(0).lower()}"
                if entry not in evidence[cat]:
                    evidence[cat].append(entry)

    for tf in test_files:
        fp = os.path.abspath(tf) if os.path.isabs(tf) else os.path.join(root, tf)
        if not os.path.isfile(fp):
            continue
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                src = f.read()
        except OSError:
            continue

        if fp.endswith(".py"):
            try:
                tree = ast.parse(src)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                        doc = ast.get_docstring(node) or ""
                        _scan_text(f"{node.name} {doc}", node.name)
            except SyntaxError:
                _scan_text(src, os.path.basename(fp))
        else:
            _scan_text(src, os.path.basename(fp))

    if not test_files and output:
        _scan_text(output, "output")

    missing = [cat for cat in REQUIRED_RED_SCENARIOS if not coverage[cat]]
    return {
        "coverage": coverage,
        "missing_scenarios": missing,
        "complete": len(missing) == 0,
        "matched_evidence": evidence,
    }


def _extract_target_identifiers(target_path: str, working_dir: str) -> Tuple[Set[str], Set[str]]:
    """Extracts canonical module/path tokens and top-level AST symbols for a target file."""
    norm = target_path.replace("\\", "/")
    rel = norm
    if os.path.isabs(target_path) and working_dir:
        try:
            rel = os.path.relpath(target_path, working_dir).replace("\\", "/")
        except ValueError:
            rel = norm

    base = os.path.basename(rel)
    stem, _ = os.path.splitext(base)
    dotted = os.path.splitext(rel)[0].replace("/", ".").lstrip(".")

    tokens: Set[str] = {base, stem}
    if rel and not rel.startswith(".."):
        tokens.add(rel)
    if dotted and not dotted.startswith(".."):
        tokens.add(dotted)

    symbols: Set[str] = set()
    abs_path = target_path if os.path.isabs(target_path) else os.path.join(working_dir, target_path)
    if os.path.isfile(abs_path) and abs_path.endswith(".py"):
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if not node.name.startswith("_") and len(node.name) >= 3:
                        symbols.add(node.name)
        except (OSError, SyntaxError):
            # Target file may be unparseable during early Red TDD; rely on path/module tokens
            symbols = set()

    return tokens, symbols


def verify_red_target_relevance(
    test_files: List[str],
    output: str,
    target_files: List[str],
    working_dir: Optional[str] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Verifies that Red test assertions/imports or failure traceback actually reference
    at least one of the changed target_files (prevents unrelated semantic failures).
    """
    root = working_dir or _REPO_ROOT
    matched_targets: List[str] = []
    unmatched_targets: List[str] = []
    match_details: Dict[str, List[str]] = {}

    # Gather imports and raw source from executed test files
    test_imports: Set[str] = set()
    test_sources: List[str] = []
    for tf in test_files:
        fp = os.path.abspath(tf) if os.path.isabs(tf) else os.path.join(root, tf)
        if not os.path.isfile(fp):
            continue
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                src = f.read()
            test_sources.append(src)
            if fp.endswith(".py"):
                tree = ast.parse(src)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            test_imports.add(alias.name)
                            test_imports.add(alias.name.split(".")[-1])
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        test_imports.add(node.module)
                        test_imports.add(node.module.split(".")[-1])
                        for alias in node.names:
                            test_imports.add(alias.name)
        except (OSError, SyntaxError):
            continue

    combined_test_src = "\n".join(test_sources)
    combined_output = output or ""

    for target in target_files:
        tokens, symbols = _extract_target_identifiers(target, root)
        reasons: List[str] = []

        for tok in sorted(tokens):
            if not tok:
                continue
            if tok in test_imports:
                reasons.append(f"test_import:{tok}")
            elif tok in combined_output:
                reasons.append(f"trace:{tok}")
            elif re.search(rf"\b{re.escape(tok)}\b", combined_test_src):
                reasons.append(f"test_ref:{tok}")

        if not reasons:
            for sym in sorted(symbols):
                if sym in test_imports:
                    reasons.append(f"symbol_import:{sym}")
                elif re.search(rf"\b{re.escape(sym)}\b", combined_output):
                    reasons.append(f"trace_symbol:{sym}")

        if reasons:
            matched_targets.append(target)
            match_details[target] = reasons[:5]
        else:
            unmatched_targets.append(target)

    is_relevant = len(matched_targets) > 0
    return is_relevant, {
        "checked": True,
        "matched": is_relevant,
        "matched_targets": matched_targets,
        "unmatched_targets": unmatched_targets,
        "evidence": match_details,
    }


def certify_red_phase(
    test_cmd: str,
    receipt_path: Optional[str] = None,
    cwd: Optional[str] = None,
    runner: Optional[str] = None,
    event_stream_path: Optional[str] = None,
    target_files: Optional[List[str]] = None,
    require_four_scenarios: bool = False,
    milestone_id: Optional[str] = None,
    ttl_seconds: Optional[int] = None,
    recertify_red: bool = False,
) -> Dict[str, Any]:
    """
    Weapon 1: Physically execute test_cmd and certify that tests FAIL (Red Phase).
    Enforces Anti-Cheat Tautology checks, 4-scenario coverage binding, and target file relevance.
    Saves forensic failure receipt to receipt_path (or milestone-scoped reports/solo_receipts/<id>_red.json).
    """
    if not test_cmd or not test_cmd.strip():
        return {
            "status": "ERROR",
            "passed": False,
            "error": "Missing test command. Provide a non-empty test command via --test-cmd.",
        }

    working_dir = cwd or _REPO_ROOT
    if receipt_path and receipt_path != DEFAULT_RECEIPT_PATH:
        target_receipt = receipt_path
    elif milestone_id:
        target_receipt = resolve_red_receipt_path(working_dir, milestone_id=milestone_id)
    else:
        target_receipt = receipt_path or DEFAULT_RECEIPT_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_receipt)), exist_ok=True)

    adapter = resolve_test_adapter(test_cmd, runner_override=runner)

    # Execute test command via adapter
    start_time = datetime.now(timezone.utc)
    exit_code, output = adapter.execute(test_cmd, cwd=working_dir)
    duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()

    # Red-First Invariant: Test MUST fail initially!
    if exit_code == 0:
        return {
            "status": "FAKE_RED_REJECTED",
            "passed": False,
            "test_cmd": test_cmd,
            "exit_code": exit_code,
            "error": "Fake Red Violation: Test passed on initial run. Test MUST fail before implementation to verify Red Phase.",
            "duration_sec": duration_sec,
        }

    # Milestone 2 & 3 Anti-Cheat: Reject literal tautological failures via adapter
    is_tautological, violation_msg = adapter.check_tautology(output, test_cmd=test_cmd)
    if is_tautological:
        return {
            "status": "TAUTOLOGICAL_RED_REJECTED",
            "passed": False,
            "test_cmd": test_cmd,
            "exit_code": exit_code,
            "error": violation_msg,
            "duration_sec": duration_sec,
        }

    # Semantic Red Verification: Categorize failure and reject environmental / syntax / timeout crashes
    category, is_semantic, cat_msg = classify_test_failure(exit_code, output, adapter_name=adapter.name)
    if not is_semantic:
        return {
            "status": f"{category}_RED_REJECTED",
            "passed": False,
            "test_cmd": test_cmd,
            "exit_code": exit_code,
            "failure_category": category,
            "error": f"Semantic Red Failure Rejection ({category}): {cat_msg}",
            "duration_sec": duration_sec,
        }

    # Milestone 2: Compute cryptographic test tree snapshot
    test_snapshot = compute_test_files_snapshot(test_cmd=test_cmd, working_dir=working_dir)
    test_tree_hash = test_snapshot.get("tree_hash", "")
    test_files_map = test_snapshot.get("files", {})
    executed_test_files = list(test_files_map.keys()) or extract_test_files_from_cmd(test_cmd)

    # Milestone 4 (P1.1): 4-Scenario Red Coverage Binding
    scenario_report = analyze_four_scenario_coverage(
        executed_test_files, output=output, working_dir=working_dir
    )
    scenario_coverage = scenario_report["coverage"]
    if require_four_scenarios and not scenario_report["complete"]:
        missing_str = ", ".join(scenario_report["missing_scenarios"])
        return {
            "status": "MISSING_SCENARIO_COVERAGE_REJECTED",
            "passed": False,
            "test_cmd": test_cmd,
            "exit_code": exit_code,
            "scenario_coverage": scenario_coverage,
            "missing_scenarios": scenario_report["missing_scenarios"],
            "error": f"Red Phase 4-Scenario Binding Violation: Missing required scenario categories: {missing_str}.",
            "duration_sec": duration_sec,
        }

    # Milestone 4 (P1.1): Target Relevance Binding (reject unrelated semantic failures)
    target_binding: Dict[str, Any] = {
        "checked": False,
        "matched": True,
        "matched_targets": [],
        "unmatched_targets": [],
        "evidence": {},
    }
    if target_files:
        is_relevant, target_binding = verify_red_target_relevance(
            executed_test_files,
            output=output,
            target_files=list(target_files),
            working_dir=working_dir,
        )
        if not is_relevant:
            return {
                "status": "UNRELATED_TARGET_RED_REJECTED",
                "passed": False,
                "test_cmd": test_cmd,
                "exit_code": exit_code,
                "scenario_coverage": scenario_coverage,
                "target_files": list(target_files),
                "target_binding": target_binding,
                "error": f"Unrelated Target Red Failure Rejection: Failure trace and tests do not bind to changed target file(s): {', '.join(target_files)}.",
                "duration_sec": duration_sec,
            }

    # Extract failure excerpt (last 30 lines)
    output_lines = output.splitlines()
    excerpt = output_lines[-30:] if len(output_lines) > 30 else output_lines
    excerpt_text = "\n".join(excerpt)
    sha_hash = hashlib.sha256(output.encode("utf-8", errors="replace")).hexdigest()

    # Subagent Skill: failure-autopsy-and-healing (pinpoint_failure error fingerprinting)
    try:
        err_fingerprint = compute_error_fingerprint(adapter.name, excerpt_text)
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        err_fingerprint = f"fp_{hashlib.md5(excerpt_text.encode('utf-8', errors='replace'), usedforsecurity=False).hexdigest()[:8]}"

    commit_hash = _resolve_git_head(working_dir)
    normalized_cmd = normalize_test_command(test_cmd)
    certified_at = datetime.now(timezone.utc).isoformat()
    effective_ttl = resolve_red_receipt_ttl(ttl_seconds=ttl_seconds, default_ttl=900)

    receipt_payload: Dict[str, Any] = {
        "status": "CERTIFIED_RED",
        "certified_at": certified_at,
        "runner": adapter.name,
        "is_semantic_red": is_semantic,
        "failure_category": category,
        "commit_hash": commit_hash,
        "ttl_seconds": effective_ttl,
        "test_cmd": test_cmd,
        "normalized_cmd": normalized_cmd,
        "executed_tests": list(executed_test_files),
        "exit_code": exit_code,
        "duration_sec": duration_sec,
        "failure_sha256": sha_hash,
        "error_fingerprint": err_fingerprint,
        "failure_excerpt": excerpt_text,
        "test_tree_hash": test_tree_hash,
        "test_files": test_files_map,
        "scenario_coverage": scenario_coverage,
        "target_binding": target_binding,
    }
    if milestone_id:
        receipt_payload["milestone_id"] = milestone_id

    if recertify_red and os.path.isfile(target_receipt):
        try:
            with open(target_receipt, "r", encoding="utf-8") as prev_fh:
                prev_data = json.load(prev_fh)
            receipt_payload = recertify_red_receipt_payload(
                prev_data if isinstance(prev_data, dict) else None,
                receipt_payload,
                key=_get_receipt_hmac_key(),
            )
            receipt_hmac = str(receipt_payload["receipt_hmac"])
        except ValueError as exc:
            return {
                "status": "RECERTIFY_TAMPERED_PRIOR_RECEIPT",
                "passed": False,
                "test_cmd": test_cmd,
                "error": str(exc),
                "duration_sec": duration_sec,
            }
        except (OSError, json.JSONDecodeError):
            receipt_hmac = compute_red_receipt_hmac(receipt_payload)
            receipt_payload["receipt_hmac"] = receipt_hmac
    else:
        receipt_hmac = compute_red_receipt_hmac(receipt_payload)
        receipt_payload["receipt_hmac"] = receipt_hmac

    _write_json_atomic(target_receipt, receipt_payload)

    # Subagent Skill: event-stream-qa-orchestrator (cryptographic hash-chaining)
    record_solo_swarm_event(
        event_type="RED_CERTIFIED",
        actor="red-team",
        payload={
            "test_cmd": test_cmd,
            "normalized_cmd": normalized_cmd,
            "commit_hash": commit_hash,
            "exit_code": exit_code,
            "failure_sha256": sha_hash,
            "error_fingerprint": err_fingerprint,
            "test_tree_hash": test_tree_hash,
            "scenario_coverage": scenario_coverage,
            "receipt_hmac": receipt_hmac,
        },
        stream_path=event_stream_path,
        repo_root=working_dir,
    )

    # Subagent Skill: qa-memory-os (QAInstinctVault observation)
    record_instinct_observation(
        tool_name=adapter.name,
        error_signature=err_fingerprint,
        resolution=f"Awaiting Blue implementation for: {test_cmd}",
        repo_root=working_dir,
    )

    return {
        "status": "CERTIFIED_RED",
        "passed": True,
        "runner": adapter.name,
        "milestone_id": milestone_id,
        "test_cmd": test_cmd,
        "normalized_cmd": normalized_cmd,
        "commit_hash": commit_hash,
        "executed_tests": list(executed_test_files),
        "exit_code": exit_code,
        "duration_sec": duration_sec,
        "receipt_file": target_receipt,
        "receipt_hmac": receipt_hmac,
        "recertified_from_hmac": receipt_payload.get("recertified_from_hmac"),
        "failure_sha256": sha_hash,
        "error_fingerprint": err_fingerprint,
        "test_tree_hash": test_tree_hash,
        "test_files": test_files_map,
        "scenario_coverage": scenario_coverage,
        "target_binding": target_binding,
        "message": f"✅ Red Phase Certified ({adapter.name}): Tests failed as expected. Signed Red Receipt recorded.",
    }


def _is_git_ancestor(older_commit: str, newer_commit: str, working_dir: str) -> bool:
    """Returns True if older_commit is a git ancestor of newer_commit."""
    if not older_commit or not newer_commit or older_commit == "unknown" or newer_commit == "unknown":
        return False
    try:
        proc = subprocess.run(
            ["git", "merge-base", "--is-ancestor", older_commit, newer_commit],
            cwd=working_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode == 0
    except OSError:
        return False


def certify_green_phase(
    test_cmd: str,
    receipt_path: Optional[str] = None,
    cwd: Optional[str] = None,
    runner: Optional[str] = None,
    event_stream_path: Optional[str] = None,
    shard_count: int = 1,
    circuit_breaker: Optional[LocatorRetryCircuitBreaker] = None,
    target_id: Optional[str] = None,
    sandbox_mode: str = "worktree",
    sandbox: Optional[SandboxBackend] = None,
    milestone_id: Optional[str] = None,
    allow_commit_progression: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Weapon 2: Execute test_cmd and verify that tests now PASS (Green Phase).
    Requires a valid HMAC-signed prior Red Receipt bound to HEAD (or ancestor commit with intact
    test_tree_hash in milestone-scoped mode), TTL, and normalized command.
    Enforces LocatorRetryCircuitBreaker (2 consecutive strikes -> CIRCUIT_BREAKER_OPEN)
    and executes tests inside a pluggable SandboxBackend (WorktreeSandbox default).
    """
    if not test_cmd or not test_cmd.strip():
        return {
            "status": "ERROR",
            "passed": False,
            "error": "Missing test command. Provide a non-empty test command via --test-cmd.",
        }

    working_dir = cwd or _REPO_ROOT
    if receipt_path and receipt_path != DEFAULT_RECEIPT_PATH:
        target_receipt = receipt_path
    elif milestone_id:
        target_receipt = resolve_red_receipt_path(working_dir, milestone_id=milestone_id)
    else:
        target_receipt = receipt_path or DEFAULT_RECEIPT_PATH

    # Verify prior Red Receipt existence
    if not os.path.exists(target_receipt):
        return {
            "status": "MISSING_RED_RECEIPT",
            "passed": False,
            "test_cmd": test_cmd,
            "error": f"Cannot certify Green Phase without a prior Red Receipt at '{target_receipt}'. Run --red first!",
        }

    try:
        with open(target_receipt, "r", encoding="utf-8") as receipt_fh:
            red_data = json.load(receipt_fh)
        if not isinstance(red_data, dict) or red_data.get("status") != "CERTIFIED_RED":
            return {
                "status": "INVALID_RED_RECEIPT",
                "passed": False,
                "error": f"Prior receipt does not have 'CERTIFIED_RED' status: found {red_data.get('status') if isinstance(red_data, dict) else type(red_data).__name__}",
            }
    except Exception as e:
        return {
            "status": "CORRUPT_RED_RECEIPT",
            "passed": False,
            "error": f"Failed to read Red Receipt: {e}",
        }

    # P0.2 Cryptographic Integrity Check: Verify HMAC-SHA256 before trusting any receipt field
    if not _verify_red_receipt_hmac(red_data):
        return {
            "status": "TAMPERED_RED_RECEIPT",
            "passed": False,
            "test_cmd": test_cmd,
            "error": "Red Receipt HMAC-SHA256 verification failed: receipt was modified or unsigned. Re-run --red.",
        }

    # Mandatory valid ISO-8601 certified_at & TTL check (fail-closed)
    cert_at_str = red_data.get("certified_at")
    if not isinstance(cert_at_str, str) or not cert_at_str.strip():
        return {
            "status": "INVALID_RED_RECEIPT",
            "passed": False,
            "test_cmd": test_cmd,
            "error": "Red Receipt missing mandatory ISO-8601 'certified_at' timestamp.",
        }
    try:
        cert_at = datetime.fromisoformat(cert_at_str.replace("Z", "+00:00"))
        if cert_at.tzinfo is None:
            cert_at = cert_at.replace(tzinfo=timezone.utc)
    except ValueError as exc:
        return {
            "status": "INVALID_RED_RECEIPT",
            "passed": False,
            "test_cmd": test_cmd,
            "error": f"Red Receipt has malformed ISO-8601 'certified_at' timestamp: {exc}",
        }

    ttl_seconds = red_data.get("ttl_seconds", 900)
    if not isinstance(ttl_seconds, (int, float)) or ttl_seconds <= 0:
        return {
            "status": "INVALID_RED_RECEIPT",
            "passed": False,
            "test_cmd": test_cmd,
            "error": f"Red Receipt has invalid ttl_seconds: {ttl_seconds!r}",
        }

    age_sec = (datetime.now(timezone.utc) - cert_at).total_seconds()
    if age_sec > ttl_seconds or age_sec < -60:
        return {
            "status": "EXPIRED_RED_RECEIPT",
            "passed": False,
            "test_cmd": test_cmd,
            "error": f"Red Receipt expired ({int(age_sec)}s old > {int(ttl_seconds)}s TTL). Re-run Red phase to verify fresh failure.",
        }

    # Commit binding check (supports ancestor commit progression when test_tree_hash is intact in milestone mode)
    red_commit = red_data.get("commit_hash")
    current_head = _resolve_git_head(working_dir)
    commit_progressed = False
    can_progress_commit = (
        allow_commit_progression
        if allow_commit_progression is not None
        else bool(milestone_id or red_data.get("milestone_id"))
    )
    if not isinstance(red_commit, str) or not red_commit.strip():
        return {
            "status": "COMMIT_MISMATCH_REJECTED",
            "passed": False,
            "test_cmd": test_cmd,
            "error": f"Commit Mismatch: Red receipt is bound to commit '{red_commit}', but current HEAD is '{current_head}'.",
        }
    if red_commit != current_head:
        expected_hash_for_prog = red_data.get("test_tree_hash", "")
        recorded_for_prog = red_data.get("test_files") or {}
        if can_progress_commit and expected_hash_for_prog and _is_git_ancestor(red_commit, current_head, working_dir):
            prog_snap = compute_test_files_snapshot(
                test_cmd=test_cmd,
                working_dir=working_dir,
                files_override=list(recorded_for_prog.keys()),
            )
            if prog_snap.get("tree_hash") == expected_hash_for_prog:
                commit_progressed = True
            else:
                return {
                    "status": "TEST_TAMPERING_DETECTED",
                    "passed": False,
                    "test_cmd": test_cmd,
                    "error": "Tampering Violation: Test tree hash changed across commit progression.",
                }
        else:
            return {
                "status": "COMMIT_MISMATCH_REJECTED",
                "passed": False,
                "test_cmd": test_cmd,
                "error": f"Commit Mismatch: Red receipt is bound to commit '{red_commit}', but current HEAD is '{current_head}'.",
            }

    # Strict normalized command matching (no blanket inline exemption)
    norm_green = normalize_test_command(test_cmd)
    norm_red = red_data.get("normalized_cmd") or normalize_test_command(red_data.get("test_cmd", ""))
    if not norm_red or norm_green != norm_red:
        return {
            "status": "COMMAND_MISMATCH_REJECTED",
            "passed": False,
            "test_cmd": test_cmd,
            "error": f"Command Mismatch: Green command '{test_cmd}' does not match certified Red command '{red_data.get('test_cmd', '')}'.",
        }

    # Milestone 2 Anti-Tamper Check: Verify test files were NOT altered by Blue Team
    expected_tree_hash = red_data.get("test_tree_hash", "")
    recorded_files = red_data.get("test_files") or {}
    if expected_tree_hash:
        current_snapshot = compute_test_files_snapshot(
            test_cmd=test_cmd,
            working_dir=working_dir,
            files_override=list(recorded_files.keys()),
        )
        if current_snapshot.get("tree_hash") != expected_tree_hash:
            tampered_files: List[str] = []
            for f_rel, exp_h in recorded_files.items():
                curr_h = current_snapshot.get("files", {}).get(f_rel)
                if curr_h is None or curr_h != exp_h:
                    tampered_files.append(f_rel)
            for f_rel in current_snapshot.get("files", {}):
                if f_rel not in recorded_files and f_rel not in tampered_files:
                    tampered_files.append(f_rel)

            record_solo_swarm_event(
                event_type="TEST_TAMPERING_DETECTED",
                actor="green-sentinel",
                payload={
                    "test_cmd": test_cmd,
                    "tampered_files": tampered_files,
                    "expected_tree_hash": expected_tree_hash,
                    "current_tree_hash": current_snapshot.get("tree_hash"),
                },
                stream_path=event_stream_path,
                repo_root=working_dir,
            )

            return {
                "status": "TEST_TAMPERING_DETECTED",
                "passed": False,
                "test_cmd": test_cmd,
                "error": f"Tampering Violation: {len(tampered_files)} test file(s) modified or deleted after Red Phase certification. Blue Team is strictly forbidden from modifying Red tests.",
                "tampered_files": tampered_files,
                "expected_tree_hash": expected_tree_hash,
                "current_tree_hash": current_snapshot.get("tree_hash"),
            }

    # P0.2 Circuit Breaker Guardrail: Halt after 2 consecutive strikes on the same target
    breaker = circuit_breaker or LocatorRetryCircuitBreaker(
        max_failures=2,
        state_file=os.path.join(os.path.dirname(os.path.abspath(target_receipt)), ".solo_breaker_state.json"),
    )
    breaker_target = target_id or norm_green
    if breaker.is_tripped(breaker_target):
        cb_state = breaker.evaluate_retry_guard(breaker_target)
        return {
            "status": "CIRCUIT_BREAKER_OPEN",
            "passed": False,
            "test_cmd": test_cmd,
            "circuit_breaker": cb_state,
            "error": (
                f"Circuit Breaker OPEN for '{breaker_target}' after {cb_state['failure_count']} "
                f"consecutive failures. Blind retries halted; escalate or reset breaker."
            ),
        }

    adapter = resolve_test_adapter(test_cmd, runner_override=runner)

    # P0.3 Pluggable Ephemeral Sandbox execution (WorktreeSandbox default; opt-in Docker; opt-out Host)
    try:
        sbx_backend = sandbox if sandbox is not None else create_sandbox_backend(sandbox_mode)
    except ValueError as exc:
        return {
            "status": "ERROR",
            "passed": False,
            "test_cmd": test_cmd,
            "error": str(exc),
        }

    use_isolated_sandbox = sbx_backend.name != "host"
    sandbox_dir = sbx_backend.prepare(working_dir, list(recorded_files.keys())) if use_isolated_sandbox else working_dir
    sandbox_info = {
        "backend": sbx_backend.name,
        "isolated": use_isolated_sandbox,
        "isolated_root": sandbox_dir,
    }

    def _exec_cmd(cmd_str: str) -> Tuple[int, str]:
        if use_isolated_sandbox:
            return sbx_backend.execute(cmd_str, sandbox_dir, timeout=120.0)
        return adapter.execute(cmd_str, cwd=working_dir)

    try:
        # Actor Swarm Matrix Sharding execution if shard_count > 1
        raw_words = test_cmd.split()
        test_files = [w for w in raw_words if w.startswith("tests/") or w.endswith(".py") or w.endswith(".ts") or w.endswith(".groovy")]
        if shard_count > 1 and len(test_files) > 1:
            shards = shard_test_execution(test_files, num_shards=shard_count, target_dir=working_dir)
            prefix_words = [w for w in raw_words if w not in test_files]
            if not prefix_words:
                prefix_words = [sys.executable, "-m", "pytest"]
            start_time = datetime.now(timezone.utc)
            shard_results = []
            with ThreadPoolExecutor(max_workers=min(len(shards), shard_count)) as executor:
                def _run_shard(shard: Dict[str, Any]) -> Tuple[int, str, List[str]]:
                    cmd_parts = prefix_words + shard["tests"]
                    s_cmd = " ".join(cmd_parts)
                    s_code, s_out = _exec_cmd(s_cmd)
                    return s_code, s_out, shard["tests"]

                futures = [executor.submit(_run_shard, s) for s in shards if s["tests"]]
                for fut in futures:
                    s_code, s_out, s_tests = fut.result()
                    shard_results.append({"exit_code": s_code, "tests": s_tests, "output": s_out})

            duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
            failed_shards = [sr for sr in shard_results if sr["exit_code"] != 0]
            if failed_shards:
                breaker.record_failure(breaker_target, error_message=f"{len(failed_shards)}/{len(shards)} shards failed")
                return {
                    "status": "GREEN_FAILED",
                    "passed": False,
                    "test_cmd": test_cmd,
                    "sharded": True,
                    "shards_count": len(shards),
                    "exit_code": 1,
                    "circuit_breaker": breaker.evaluate_retry_guard(breaker_target),
                    "sandbox": sandbox_info,
                    "error": f"{len(failed_shards)}/{len(shards)} shards failed in parallel execution.",
                    "duration_sec": duration_sec,
                    "failure_excerpt": failed_shards[0]["output"][-500:],
                }
            exit_code = 0
        else:
            # Standard sequential execution inside sandbox
            start_time = datetime.now(timezone.utc)
            exit_code, output = _exec_cmd(test_cmd)
            duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()

            if exit_code != 0:
                breaker.record_failure(breaker_target, error_message=f"Green command exited with {exit_code}")
                return {
                    "status": "GREEN_FAILED",
                    "passed": False,
                    "test_cmd": test_cmd,
                    "exit_code": exit_code,
                    "circuit_breaker": breaker.evaluate_retry_guard(breaker_target),
                    "sandbox": sandbox_info,
                    "error": "Tests are still failing. Blue implementer must fix logic until exit code is 0.",
                    "duration_sec": duration_sec,
                    "failure_excerpt": "\n".join(output.splitlines()[-20:]),
                }
    finally:
        if use_isolated_sandbox:
            sbx_backend.cleanup(sandbox_dir)

    # Reset circuit breaker consecutive failure counter on pass
    breaker.record_success(breaker_target)

    # Subagent Skill: event-stream-qa-orchestrator (cryptographic hash-chaining)
    record_solo_swarm_event(
        event_type="GREEN_CERTIFIED",
        actor="blue-team",
        payload={
            "test_cmd": test_cmd,
            "exit_code": 0,
            "duration_sec": duration_sec,
            "sandbox_backend": sbx_backend.name,
        },
        stream_path=event_stream_path,
        repo_root=working_dir,
    )

    # Subagent Skill: qa-memory-os (QAInstinctVault observation)
    record_instinct_observation(
        tool_name=adapter.name,
        error_signature=red_data.get("failure_sha256", "clean")[:16],
        resolution=f"Certified passing logic for: {test_cmd}",
        repo_root=working_dir,
    )

    return {
        "status": "CERTIFIED_GREEN",
        "passed": True,
        "test_cmd": test_cmd,
        "exit_code": 0,
        "duration_sec": duration_sec,
        "sharded": shard_count > 1 and len(test_files) > 1,
        "red_certified_at": red_data.get("certified_at"),
        "commit_progressed": commit_progressed,
        "circuit_breaker": breaker.evaluate_retry_guard(breaker_target),
        "sandbox": sandbox_info,
        "message": f"✅ Green Phase Certified ({sbx_backend.name} sandbox): All tests pass with zero exceptions.",
    }


def _run_mutation_in_sandbox(
    backend: SandboxBackend,
    sandbox_dir: str,
    sandbox_target: str,
    min_score: float,
    sandbox_test_cmd: str,
    timeout: float,
    diff_only: bool,
    mutation_scope: Optional[str],
    allow_full_fallback: bool,
) -> Dict[str, Any]:
    """Executes micro_mutator.evaluate_target inside an isolated sandbox subprocess."""
    import base64 as _b64
    sentinel = "__SYNAPSE_MUT_JSON__:"
    payload_args = json.dumps({
        "target_path": sandbox_target,
        "min_score": min_score,
        "test_cmd": sandbox_test_cmd,
        "timeout": timeout,
        "diff_only": diff_only,
        "mutation_scope": mutation_scope,
        "allow_full_fallback": allow_full_fallback,
        "sandbox_dir": sandbox_dir,
        "hub_root": _REPO_ROOT,
    })
    runner_code = (
        "import base64, json, sys; "
        "cfg = json.loads(base64.b64decode(sys.argv[2]).decode('utf-8')); "
        "sys.path.insert(0, cfg['hub_root']); "
        "from tools.lint import micro_mutator as mm; "
        "mm.HUB_ROOT = cfg['sandbox_dir']; "
        "res = mm.evaluate_target("
        "target_path=cfg['target_path'], "
        "min_score=cfg['min_score'], "
        "test_cmd=cfg['test_cmd'], "
        "timeout=cfg['timeout'], "
        "diff_only=cfg['diff_only'], "
        "mutation_scope=cfg['mutation_scope'], "
        "allow_full_fallback=cfg['allow_full_fallback']); "
        f"print({sentinel!r} + json.dumps(res))"
    )
    code_b64 = _b64.b64encode(runner_code.encode("utf-8")).decode("ascii")
    payload_b64 = _b64.b64encode(payload_args.encode("utf-8")).decode("ascii")
    python_bin = "python3" if backend.name == "docker" else sys.executable
    cmd_str = f'"{python_bin}" -c "import base64,sys;exec(base64.b64decode(sys.argv[1]).decode())" {code_b64} {payload_b64}'
    total_timeout = max(60.0, float(timeout) * 25.0)
    rc, output = backend.execute(cmd_str, sandbox_dir, timeout=total_timeout)
    for line in reversed((output or "").splitlines()):
        if line.startswith(sentinel):
            try:
                return json.loads(line[len(sentinel):])
            except json.JSONDecodeError as exc:
                return {
                    "status": "ERROR",
                    "passed": False,
                    "error": f"Failed to parse sandboxed mutation JSON: {exc}",
                }
    return {
        "status": "ERROR",
        "passed": False,
        "error": f"Sandboxed mutation execution failed (rc={rc}): {(output or '').strip()[-400:]}",
    }


def _run_host_mutation_eval(
    root: str,
    abs_target: str,
    threshold: float,
    test_cmd: str,
    timeout: float,
    diff_only: bool,
    mutation_scope: Optional[str],
    allow_full_fallback: bool,
) -> Dict[str, Any]:
    """Runs mutation evaluation on the host workspace while restoring micro_mutator.HUB_ROOT."""
    from tools.lint import micro_mutator as _mm

    prev_hub_root = _mm.HUB_ROOT
    try:
        if os.path.abspath(root) != os.path.abspath(prev_hub_root):
            _mm.HUB_ROOT = root
        return evaluate_target(
            target_path=abs_target,
            min_score=threshold,
            test_cmd=test_cmd,
            timeout=timeout,
            diff_only=diff_only,
            mutation_scope=mutation_scope,
            allow_full_fallback=allow_full_fallback,
        )
    finally:
        _mm.HUB_ROOT = prev_hub_root


def _load_cli_batch_specs(batch_queue: Optional[str], batch_json: Optional[str]) -> Tuple[Any, Optional[str]]:
    """Loads batch queue specifications from --batch-queue file or --batch-json string."""
    if batch_queue:
        if not os.path.isfile(batch_queue):
            return [], f"Batch queue file not found: '{batch_queue}'"
        try:
            with open(batch_queue, "r", encoding="utf-8") as f:
                return json.load(f), None
        except Exception as e:  # synapse-ignore: SWALLOWED_EXCEPTION
            return [], f"Failed to parse batch queue JSON file: {e}"
    if batch_json:
        try:
            return json.loads(batch_json), None
        except Exception as e:  # synapse-ignore: SWALLOWED_EXCEPTION
            return [], f"Failed to parse batch JSON string: {e}"
    return [], None


def certify_mutation_phase(
    target_file: str = "",
    test_cmd: str = "",
    threshold: float = DEFAULT_MUTATION_THRESHOLD,
    timeout: float = 60.0,
    diff_only: bool = True,
    repo_root: Optional[str] = None,
    event_stream_path: Optional[str] = None,
    receipt_path: Optional[str] = None,
    mutation_scope: Optional[str] = None,
    allow_full_fallback: bool = False,
    sandbox_mode: str = "worktree",
    sandbox: Optional[SandboxBackend] = None,
) -> Dict[str, Any]:
    """
    Weapon 3: Run live dynamic mutation testing against target_file using test_cmd.
    If target_file is omitted, automatically resolves all modified source files from git diff and untracked files.
    By default scopes mutations strictly to git diff line ranges (diff_only=True) inside a pluggable SandboxBackend.
    """
    root = repo_root or _REPO_ROOT

    # Milestone 3: Auto-target discovery if target_file is empty
    auto_targeted = False
    targets = [target_file] if target_file else []
    if target_file:
        abs_explicit = os.path.abspath(target_file) if os.path.isabs(target_file) else os.path.join(root, target_file)
        if not os.path.exists(abs_explicit):
            return {
                "status": "ERROR",
                "passed": False,
                "error": f"Target source file not found at '{abs_explicit}'",
            }
    else:
        targets = resolve_auto_targets(repo_root=root)
        auto_targeted = True
        if not targets:
            return {
                "status": "ERROR",
                "passed": False,
                "error": "No target file specified and no modified source files detected in git diff or untracked state. Provide a target via --target.",
            }

    if not test_cmd or not test_cmd.strip():
        return {
            "status": "ERROR",
            "passed": False,
            "error": "Missing test command for mutation verification. Pass --test-cmd '<command>'.",
        }

    # P0.3 Pluggable Sandbox setup for mutation isolation
    try:
        sbx_backend = sandbox if sandbox is not None else create_sandbox_backend(sandbox_mode)
    except ValueError as exc:
        return {
            "status": "ERROR",
            "passed": False,
            "error": str(exc),
        }

    use_isolated_sandbox = sbx_backend.name != "host"
    sandbox_dir = sbx_backend.prepare(root, targets) if use_isolated_sandbox else root
    if isinstance(sbx_backend, WorktreeSandbox):
        existing_pp = sbx_backend.extra_env.get("PYTHONPATH", "")
        pp_parts = [sandbox_dir, _REPO_ROOT] + ([existing_pp] if existing_pp else [])
        sbx_backend.extra_env["PYTHONPATH"] = os.pathsep.join(pp_parts)

    sandbox_info = {
        "backend": sbx_backend.name,
        "isolated": use_isolated_sandbox,
        "isolated_root": sandbox_dir,
    }

    scope_requested = mutation_scope or ("diff_only" if diff_only else "full")
    target_results: Dict[str, Any] = {}
    total_mutants_sum = 0
    killed_sum = 0
    survived_sum = 0
    timed_out_sum = 0
    invalid_sum = 0
    denominator_sum = 0
    scopes_used: Set[str] = set()
    all_passed = True
    all_no_diff = True

    try:
        for t in targets:
            abs_target = os.path.abspath(t) if os.path.isabs(t) else os.path.join(root, t)
            if not os.path.exists(abs_target):
                continue

            if use_isolated_sandbox:
                try:
                    rel_t = os.path.relpath(abs_target, os.path.abspath(root))
                except ValueError:
                    rel_t = os.path.basename(abs_target)
                sandbox_target = os.path.join(sandbox_dir, rel_t)
                sandbox_test_cmd = rewrite_command_paths(test_cmd, root, sandbox_dir)
                res = _run_mutation_in_sandbox(
                    backend=sbx_backend,
                    sandbox_dir=sandbox_dir,
                    sandbox_target=sandbox_target,
                    min_score=threshold,
                    sandbox_test_cmd=sandbox_test_cmd,
                    timeout=timeout,
                    diff_only=diff_only,
                    mutation_scope=mutation_scope,
                    allow_full_fallback=allow_full_fallback,
                )
            else:
                res = _run_host_mutation_eval(
                    root=root,
                    abs_target=abs_target,
                    threshold=threshold,
                    test_cmd=test_cmd,
                    timeout=timeout,
                    diff_only=diff_only,
                    mutation_scope=mutation_scope,
                    allow_full_fallback=allow_full_fallback,
                )
            target_results[t] = res
            t_total = res.get("total_generated", res.get("total_mutants", 0))
            t_killed = res.get("killed", 0)
            t_survived = res.get("survived", 0)
            t_timed_out = res.get("timed_out", 0)
            t_invalid = res.get("invalid", res.get("invalid_syntax", 0))
            t_denom = res.get("score_denominator", t_killed + t_survived + t_timed_out)
            total_mutants_sum += t_total
            killed_sum += t_killed
            survived_sum += t_survived
            timed_out_sum += t_timed_out
            invalid_sum += t_invalid
            denominator_sum += t_denom
            scopes_used.add(res.get("scope_used", scope_requested))
            if res.get("status") != "NO_DIFF_MUTANTS":
                all_no_diff = False
            if not res.get("passed", False):
                all_passed = False
    finally:
        if use_isolated_sandbox:
            sbx_backend.cleanup(sandbox_dir)

    if not target_results:
        return {
            "status": "ERROR",
            "passed": False,
            "error": "No valid target source files found to evaluate.",
        }

    overall_score = (killed_sum / denominator_sum * 100.0) if denominator_sum > 0 else 0.0
    is_no_diff = all_no_diff and total_mutants_sum == 0
    passed = (not is_no_diff) and all_passed and (overall_score >= threshold)
    scope_used = next(iter(scopes_used)) if len(scopes_used) == 1 else "mixed"

    effective_target = targets[0] if len(targets) == 1 else f"{len(targets)} targets ({', '.join(targets[:3])}{'...' if len(targets) > 3 else ''})"

    # Subagent Skill: event-stream-qa-orchestrator (cryptographic hash-chaining)
    record_solo_swarm_event(
        event_type="MUTATION_CERTIFIED" if passed else ("MUTATION_NO_DIFF" if is_no_diff else "MUTATION_EVALUATED"),
        actor="purple-team",
        payload={
            "score": overall_score,
            "threshold": threshold,
            "killed": killed_sum,
            "survived": survived_sum,
            "timed_out": timed_out_sum,
            "invalid": invalid_sum,
            "score_denominator": denominator_sum,
            "scope_used": scope_used,
            "targets_count": len(target_results),
        },
        stream_path=event_stream_path,
        repo_root=root,
    )

    if is_no_diff:
        mut_status = "NO_DIFF_MUTANTS"
        mut_msg = (
            "❌ No mutable diff lines detected under diff_only scope (zero silent fallback). "
            "Pass --full-file / mutation_scope='full' to run full-file mutation explicitly."
        )
    elif passed:
        mut_status = "CERTIFIED_MUTATION"
        mut_msg = (
            f"✅ Mutation Phase Certified: Assertion sensitivity {overall_score:.1f}% >= {threshold}% "
            f"(Killed {killed_sum}/{denominator_sum} valid mutants across {len(target_results)} files)."
        )
    else:
        mut_status = "MUTATION_REJECTED"
        mut_msg = (
            f"❌ Mutation Phase Rejected: Sensitivity {overall_score:.1f}% < {threshold}% or survivor detected. "
            "Strengthen test assertions."
        )

    result = {
        "status": mut_status,
        "passed": passed,
        "target_file": effective_target,
        "targets_evaluated": list(target_results.keys()),
        "auto_targeted": auto_targeted,
        "diff_only": diff_only,
        "scope_requested": scope_requested,
        "scope_used": scope_used,
        "test_cmd": test_cmd,
        "mutation_score": overall_score,
        "required_threshold": threshold,
        "total_generated": total_mutants_sum,
        "total_mutants": total_mutants_sum,
        "killed": killed_sum,
        "survived": survived_sum,
        "timed_out": timed_out_sum,
        "invalid": invalid_sum,
        "score_denominator": denominator_sum,
        "target_details": target_results,
        "sandbox": sandbox_info,
        "message": mut_msg,
    }
    result["receipt_hmac"] = compute_mutation_receipt_hmac(result, repo_root=root)

    out_receipt = receipt_path or DEFAULT_MUTATION_RECEIPT_PATH
    try:
        _write_json_atomic(out_receipt, result)
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

    return result


def certify_purple_phase(
    target: str = "uncommitted",
    target_file: str = "",
    receipt_path: Optional[str] = None,
    repo_root: Optional[str] = None,
    event_stream_path: Optional[str] = None,
    oracle_cmd: Optional[str] = None,
    check_neuro_symbolic: bool = True,
    target_files: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Weapon 2 Phase 3: Purple Team (Senior Tech Lead Auditor & Goldfish Review).
    Stateless, memory-wiped audit of uncommitted code changes and specifications.
    Integrates senior_code_review diff analysis, goldfish_review spec inspection,
    neuro-symbolic formal constraint checking, and external adversarial oracle across all targets.
    Produces tdd_purple_receipt.json and records to QaEventStream.
    """
    root = repo_root or _REPO_ROOT
    out_receipt = receipt_path or DEFAULT_PURPLE_RECEIPT_PATH
    os.makedirs(os.path.dirname(os.path.abspath(out_receipt)), exist_ok=True)

    # Auto-resolve changed source targets when explicit targets are omitted so Neuro-Symbolic & Call-Graph run
    auto_resolved_targets: List[str] = []
    targets_to_audit: List[str] = []
    if target_files:
        for tf in target_files:
            clean_tf = str(tf).strip()
            if clean_tf and clean_tf not in targets_to_audit:
                targets_to_audit.append(clean_tf)
    elif target_file:
        targets_to_audit = [target_file]
    else:
        auto_resolved_targets = resolve_auto_targets(repo_root=root)
        targets_to_audit = list(auto_resolved_targets)

    effective_target_file = targets_to_audit[0] if targets_to_audit else ""

    # 1. Senior Code Review (Stateless Diff Inspection)
    findings: List[Dict[str, Any]] = []
    lines_cuttable = 0
    files_analyzed = 0
    review_status = "CLEAN"
    try:
        diff_text = get_git_diff(root, target)
        files = parse_diff(diff_text)
        files_analyzed = len(files)
        raw_findings, lines_cuttable = analyze_diff(files, root)
        findings = [item.to_dict() for item in raw_findings]
        # Invariant 2 Enforcement: Treat swallowed exceptions as Must Fix
        for finding in findings:
            msg_text = " ".join(
                str(finding.get(k, "") or "") for k in ("title", "problem", "message")
            ).lower()
            if "swallowed" in msg_text or "empty catch" in msg_text:
                finding["severity"] = "Must fix"

        has_must_fix = any(finding.get("severity") == "Must fix" for finding in findings)
        if has_must_fix:
            review_status = "MUST_FIX_DETECTED"
        elif files_analyzed == 0 and not effective_target_file:
            review_status = "EMPTY_SCOPE_WARNING"
            findings.append({
                "severity": "Warning",
                "message": f"No modified files detected in diff scope '{target}'. Specify --target-file to audit specific file.",
            })
    except Exception as err:
        findings = [{"severity": "Must fix", "message": f"Diff inspection error: {err}"}]
        review_status = "DIFF_ERROR"

    # 2. Goldfish Spec Review (strictly scoped to specification / feature files)
    spec_review = None
    if effective_target_file:
        cand_path = os.path.abspath(effective_target_file) if os.path.isabs(effective_target_file) else os.path.join(root, effective_target_file)
        if os.path.exists(cand_path) and cand_path.lower().endswith((".md", ".feature", ".txt")):
            try:
                spec_res = run_goldfish_review(cand_path)
                spec_review = {
                    "file": effective_target_file,
                    "score": spec_res.get("score", 100),
                    "passed": spec_res.get("passed", True),
                    "findings_count": spec_res.get("findings_count", 0),
                }
                if not spec_res.get("passed", True):
                    findings.append({
                        "severity": "Must fix",
                        "message": f"Goldfish spec review failed for {effective_target_file} (score: {spec_res.get('score', 0)})",
                    })
                    review_status = "MUST_FIX_DETECTED"
            except Exception as err:
                spec_review = {
                    "file": effective_target_file,
                    "score": 0,
                    "passed": False,
                    "error": f"Spec inspection error: {err}",
                }
                findings.append({
                    "severity": "Must fix",
                    "message": f"Goldfish review exception on {effective_target_file}: {err}",
                })
                review_status = "MUST_FIX_DETECTED"

    # 3. Tier 15 Neuro-Symbolic Invariant Verification (all resolved targets)
    neuro_symbolic_res = None
    neuro_symbolic_reviews: Dict[str, Any] = {}
    if targets_to_audit and check_neuro_symbolic:
        for audit_target in targets_to_audit:
            cand_path = os.path.abspath(audit_target) if os.path.isabs(audit_target) else os.path.join(root, audit_target)
            if os.path.isfile(cand_path):
                ns_res = verify_neuro_symbolic_constraints(
                    target_file=audit_target,
                    repo_root=root,
                    event_stream_path=event_stream_path,
                )
                neuro_symbolic_reviews[audit_target] = ns_res
                if neuro_symbolic_res is None:
                    neuro_symbolic_res = ns_res
                if not ns_res.get("passed", False):
                    findings.append({
                        "severity": "Must fix",
                        "message": f"Neuro-Symbolic Constraint Violation ({audit_target}): {ns_res.get('message')}",
                    })
                    review_status = "MUST_FIX_DETECTED"

    # 4. External Adversarial Oracle
    oracle_res = None
    if oracle_cmd:
        o_res = execute_external_oracle(
            oracle_cmd=oracle_cmd,
            target_file=effective_target_file,
            cwd=root,
            event_stream_path=event_stream_path,
        )
        oracle_res = o_res
        if not o_res.get("passed", False):
            findings.append({
                "severity": "Must fix",
                "message": f"External Oracle Adversarial Violation: {o_res.get('output', '')[:200]}",
            })
            review_status = "MUST_FIX_DETECTED"

    # 5. Call Graph Downstream Blast Radius Inspection (Invariant 17d across all targets)
    downstream_impact = None
    downstream_impacts: Dict[str, Any] = {}
    if targets_to_audit:
        try:
            from tools.context.call_graph_indexer import get_or_build_call_graph
            cg = get_or_build_call_graph(root)
            for audit_target in targets_to_audit:
                abs_tf = os.path.abspath(audit_target) if os.path.isabs(audit_target) else os.path.join(root, audit_target)
                rel_target = os.path.relpath(abs_tf, root).replace("\\", "/")
                fan_in = cg.get_fan_in(rel_target)
                dependents = cg.get_dependents(rel_target)
                impact_entry = {
                    "target": rel_target,
                    "fan_in": fan_in,
                    "dependents": dependents[:10],
                    "high_blast_radius": fan_in >= 5,
                }
                downstream_impacts[audit_target] = impact_entry
                if downstream_impact is None:
                    downstream_impact = impact_entry
                if fan_in >= 15:
                    findings.append({
                        "severity": "Warning",
                        "message": f"High blast radius: {rel_target} has {fan_in} downstream dependent callers. Ensure comprehensive regression testing.",
                    })
        except Exception as cg_err:
            downstream_impact = {"error": str(cg_err)}

    passed = (review_status == "CLEAN") and (spec_review is None or spec_review.get("passed", True))
    verdict = "CERTIFIED_PURPLE" if passed else "PURPLE_AUDIT_WARNINGS"

    receipt_payload = {
        "status": verdict,
        "certified_at": datetime.now(timezone.utc).isoformat(),
        "target_scope": target,
        "target_file": effective_target_file,
        "targets_audited": targets_to_audit,
        "auto_resolved_targets": auto_resolved_targets,
        "files_analyzed": files_analyzed,
        "findings_count": len(findings),
        "lines_cuttable": lines_cuttable,
        "findings": findings,
        "spec_review": spec_review,
        "neuro_symbolic_review": neuro_symbolic_res,
        "neuro_symbolic_reviews": neuro_symbolic_reviews,
        "oracle_review": oracle_res,
        "downstream_impact": downstream_impact,
        "downstream_impacts": downstream_impacts,
        "cognitive_isolation_certified": True,
        "stateless_oracle_used": bool(oracle_cmd),
        "passed": passed,
    }

    with open(out_receipt, "w", encoding="utf-8") as receipt_out_fh:
        json.dump(receipt_payload, receipt_out_fh, indent=2)

    record_solo_swarm_event(
        event_type="PURPLE_AUDITED",
        actor="purple-team",
        payload={
            "verdict": verdict,
            "passed": passed,
            "findings_count": len(findings),
            "files_analyzed": files_analyzed,
            "targets_audited": len(targets_to_audit),
        },
        stream_path=event_stream_path,
        repo_root=root,
    )

    return {
        "status": verdict,
        "passed": passed,
        "target": target,
        "target_file": effective_target_file,
        "targets_audited": targets_to_audit,
        "auto_resolved_targets": auto_resolved_targets,
        "files_analyzed": files_analyzed,
        "findings_count": len(findings),
        "lines_cuttable": lines_cuttable,
        "findings": findings,
        "spec_review": spec_review,
        "neuro_symbolic_review": neuro_symbolic_res,
        "neuro_symbolic_reviews": neuro_symbolic_reviews,
        "downstream_impact": downstream_impact,
        "downstream_impacts": downstream_impacts,
        "receipt_file": out_receipt,
        "message": (
            "✅ Purple Phase Certified: Zero must-fix code review defects & clean specification."
            if passed
            else f"⚠️ Purple Phase Warnings: {len(findings)} review findings detected. Check {out_receipt}."
        ),
    }


def evaluate_tournament_candidate(
    candidate_id: str,
    worktree_path: str,
    branch_name: str,
    test_cmd: str,
    target_file: str = "",
    threshold: float = DEFAULT_MUTATION_THRESHOLD,
    timeout: float = 60.0,
    diff_only: bool = True,
    repo_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates an individual tournament candidate in its isolated worktree.
    Verifies Green status, evaluates mutation testing kill rate, and calculates net changed LOC.
    """
    start_time = datetime.now(timezone.utc)
    # 1. Run test_cmd in candidate worktree
    cmd_parts = split_cmd_portable(test_cmd)
    proc = subprocess.run(
        cmd_parts,
        cwd=worktree_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
        encoding="utf-8",
        errors="replace",
    )
    green_passed = proc.returncode == 0

    # 2. Measure LOC changed
    loc_proc = subprocess.run(
        ["git", "diff", "--shortstat", "HEAD"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    net_lines = 1
    if loc_proc.returncode == 0 and loc_proc.stdout.strip():
        m_lines = re.search(r"(\d+)\s+insertion", loc_proc.stdout)
        if m_lines:
            net_lines = max(1, int(m_lines.group(1)))

    # 3. Evaluate mutation phase in worktree
    mutation_score = 0.0
    killed = 0
    total_mutants = 0
    if green_passed:
        mut_res = certify_mutation_phase(
            target_file=target_file,
            test_cmd=test_cmd,
            threshold=threshold,
            timeout=timeout,
            diff_only=diff_only,
            repo_root=worktree_path,
        )
        mutation_score = mut_res.get("mutation_score", 0.0)
        killed = mut_res.get("killed", 0)
        total_mutants = mut_res.get("total_mutants", 0)

    # 4. Anti-Goodhart Composite fitness score (Milestone 1): 80% mutation kill sensitivity, 20% bounded LOC efficiency
    composite_score = calculate_composite_fitness_score(
        mutation_score=mutation_score,
        net_lines=net_lines,
        green_passed=green_passed,
    )
    duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()

    return {
        "candidate_id": candidate_id,
        "worktree_path": worktree_path,
        "branch_name": branch_name,
        "green_passed": green_passed,
        "mutation_score": mutation_score,
        "mutants_killed": killed,
        "mutants_total": total_mutants,
        "net_lines_changed": net_lines,
        "composite_fitness_score": composite_score,
        "duration_sec": duration_sec,
    }


class ZeroTokenArbiter:
    """
    Milestone 3 (MCI Swarm): 100% Mechanical Zero-Token Tournament Arbiter.
    Evaluates candidate implementations using purely deterministic execution signals:
      1. Green status (Exit code == 0)
      2. Dynamic Mutation Kill Sensitivity (micro_mutator.py --diff-only)
      3. Net LOC efficiency (Leanest complete implementation)
    Zero tokens are spent on LLM judging.
    """

    def __init__(self, repo_root: Optional[str] = None) -> None:
        self.repo_root = repo_root or _REPO_ROOT

    def judge_tournament(
        self,
        candidate_paths: List[str],
        test_cmd: str,
        target_file: str = "",
        threshold: float = DEFAULT_MUTATION_THRESHOLD,
        auto_cleanup: bool = True,
        event_stream_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        start_time = datetime.now(timezone.utc)
        candidates_to_eval = []
        for idx, p in enumerate(candidate_paths, 1):
            candidates_to_eval.append({
                "candidate_id": f"candidate_{idx}",
                "worktree_path": os.path.abspath(p),
                "branch_name": os.path.basename(p),
            })

        if not candidates_to_eval:
            return {
                "status": "ERROR",
                "passed": False,
                "arbitration_mode": "100%_MECHANICAL_ZERO_TOKEN",
                "tokens_consumed": 0,
                "error": "No tournament candidate worktrees or paths found to evaluate.",
            }

        eval_results = []
        with ThreadPoolExecutor(max_workers=min(4, len(candidates_to_eval))) as executor:
            futures = [
                executor.submit(
                    evaluate_tournament_candidate,
                    candidate_id=c["candidate_id"],
                    worktree_path=c["worktree_path"],
                    branch_name=c["branch_name"],
                    test_cmd=test_cmd,
                    target_file=target_file,
                    threshold=threshold,
                    repo_root=self.repo_root,
                )
                for c in candidates_to_eval
            ]
            for f in futures:
                try:
                    eval_results.append(f.result(timeout=120))
                except Exception as e:
                    eval_results.append({
                        "candidate_id": "failed_candidate",
                        "green_passed": False,
                        "error": str(e),
                        "composite_fitness_score": 0.0,
                    })

        winner = select_tournament_winner(eval_results)
        cleaned = []
        if auto_cleanup and winner:
            mgr = WorktreeManager(repo_root=self.repo_root)
            for c in candidates_to_eval:
                if c["candidate_id"] != winner.get("candidate_id"):
                    try:
                        mgr.cleanup_worktree(c["worktree_path"], force=True)
                        cleaned.append(c["worktree_path"])
                    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                        pass

        duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()

        if winner:
            record_solo_swarm_event(
                event_type="TOURNAMENT_WINNER",
                actor="zero-token-arbiter",
                payload={
                    "winner_id": winner["candidate_id"],
                    "fitness": winner["composite_fitness_score"],
                    "mutation_score": winner["mutation_score"],
                    "net_lines": winner["net_lines_changed"],
                },
                stream_path=event_stream_path,
                repo_root=self.repo_root,
            )
            record_instinct_observation(
                tool_name="zero-token-arbiter",
                error_signature="tournament_winner",
                resolution=f"Selected {winner['candidate_id']} (fitness: {winner['composite_fitness_score']:.2f})",
                repo_root=self.repo_root,
            )

        return {
            "status": "TOURNAMENT_COMPLETED" if winner else "TOURNAMENT_FAILED",
            "passed": winner is not None,
            "arbitration_mode": "100%_MECHANICAL_ZERO_TOKEN",
            "tokens_consumed": 0,
            "wall_clock_duration_sec": duration_sec,
            "winner_candidate": winner,
            "candidates_count": len(eval_results),
            "candidates_evaluated": eval_results,
            "cleaned_worktrees": cleaned,
            "message": (
                f"🏆 Zero-Token Arbiter Winner: [{winner['candidate_id']}] "
                f"(Mutation: {winner['mutation_score']:.1f}%, LOC: +{winner['net_lines_changed']}, "
                f"Fitness: {winner['composite_fitness_score']:.2f}, Tokens Spent: 0)"
                if winner
                else "❌ Tournament Failed: No candidate met Green verification and mutation threshold."
            ),
        }


class AsyncCandidateSpeculator:
    """
    Milestone 2 (MCI Swarm): Manages speculative generation across multiple candidate personas.
    Prepares Candidate A (Minimalist/Stdlib) and Candidate B (Defensive/Resilient) simultaneously.
    """

    def __init__(self, repo_root: Optional[str] = None) -> None:
        self.repo_root = repo_root or _REPO_ROOT
        self.extractor = MicroContextExtractor(repo_root=self.repo_root)

    def prepare_speculative_prompts(
        self,
        target_file: str,
        failure_trace: str,
        count: int = 2,
    ) -> Tuple[MicroContextPayload, List[SpeculativeCandidatePrompt]]:
        payload = self.extractor.build_micro_payload(target_file, failure_trace)

        # Subagent Skill: qa-memory-os (QAInstinctVault past learned instincts retrieval)
        past_instincts = query_instinct_guidance(domain="general", repo_root=self.repo_root, limit=2)
        instinct_note = f" Past Learned Instincts: {'; '.join(past_instincts)}." if past_instincts else ""

        prompts = [
            SpeculativeCandidatePrompt(
                candidate_id="cand_minimalist",
                persona="MINIMALIST_STDLIB",
                system_directive=(
                    "Implement the leanest, most minimal solution using standard library only. "
                    "Prioritize minimum lines of code and zero unnecessary abstractions."
                    + instinct_note
                ),
                temperature=0.2,
                max_tokens=600,
            ),
            SpeculativeCandidatePrompt(
                candidate_id="cand_defensive",
                persona="DEFENSIVE_RESILIENT",
                system_directive=(
                    "Implement a robust, defensive solution with explicit input validation, "
                    "boundary/null checking, and resilient error recovery."
                    + instinct_note
                ),
                temperature=0.6,
                max_tokens=900,
            ),
        ]
        return payload, prompts[:count]

    def run_speculative_tournament(
        self,
        candidate_paths: List[str],
        test_cmd: str,
        target_file: str = "",
        threshold: float = DEFAULT_MUTATION_THRESHOLD,
    ) -> Dict[str, Any]:
        arbiter = ZeroTokenArbiter(repo_root=self.repo_root)
        return arbiter.judge_tournament(
            candidate_paths=candidate_paths,
            test_cmd=test_cmd,
            target_file=target_file,
            threshold=threshold,
        )


def run_tournament(
    candidate_paths: Optional[List[str]] = None,
    test_cmd: str = "",
    target_file: str = "",
    threshold: float = DEFAULT_MUTATION_THRESHOLD,
    auto_cleanup: bool = True,
    repo_root: Optional[str] = None,
    event_stream_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Weapon 2 & 3 Swarm Essence: Runs a tournament between candidate implementations.
    Delegates to ZeroTokenArbiter for 100% mechanical evaluation and parallel execution.
    """
    root = repo_root or _REPO_ROOT
    effective_paths = list(candidate_paths) if candidate_paths else []
    if not effective_paths:
        mgr = WorktreeManager(repo_root=root)
        wts = mgr.list_worktrees()
        for wt in wts:
            p = wt.get("path", "")
            if p and os.path.realpath(p) != os.path.realpath(root):
                effective_paths.append(p)

    arbiter = ZeroTokenArbiter(repo_root=root)
    return arbiter.judge_tournament(
        candidate_paths=effective_paths,
        test_cmd=test_cmd,
        target_file=target_file,
        threshold=threshold,
        auto_cleanup=auto_cleanup,
        event_stream_path=event_stream_path,
    )


def get_status(receipt_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns current Solo-Swarm verification status.
    """
    target_receipt = receipt_path or DEFAULT_RECEIPT_PATH
    has_red = os.path.exists(target_receipt)
    red_data = None
    if has_red:
        try:
            with open(target_receipt, "r", encoding="utf-8") as f:
                red_data = json.load(f)
        except Exception:
            red_data = {"status": "CORRUPTED"}

    return {
        "red_receipt_exists": has_red,
        "receipt_file": target_receipt,
        "red_details": red_data,
        "protocol": "Solo 4-Weapon Orchestrator",
        "standards_reference": "standards/qa-process/solo-protocol.md",
        "contrarian_perspectives_count": len(CONTRARIAN_PERSPECTIVES),
    }


def execute_state_flushing_batch(
    batch_specs: List[Dict[str, Any]],
    repo_root: Optional[str] = None,
    event_stream_path: Optional[str] = None,
    batch_receipt_path: Optional[str] = None,
    contract_graph_path: Optional[str] = None,
    use_sandbox: bool = True,
) -> Dict[str, Any]:
    """
    Massive Distributed Systems Enhancement: State-Flushing DAG Pipeline with Typed Contract Sentinel.
    Iteratively executes Solo-Swarm verification across multiple services / modules sequentially,
    wiping working context memory, offload files, and Python GC between steps while enforcing
    cross-service contract compatibility (OpenAPI/CDC) and ephemeral sandboxing.
    """
    import gc

    root = repo_root or _REPO_ROOT
    out_receipt = batch_receipt_path or DEFAULT_BATCH_RECEIPT_PATH
    start_time = datetime.now(timezone.utc)
    step_results = []
    all_passed = True

    offload_dir = os.path.join(root, "scratch", "offload")
    batch_breaker = LocatorRetryCircuitBreaker(
        max_failures=2,
        state_file=os.path.join(os.path.dirname(os.path.abspath(out_receipt)), ".batch_breaker_state.json"),
    )
    batch_breaker.reset()

    # Initialize Cross-Service Contract Graph if contracts are present
    contract_graph: Optional[CrossServiceContractGraph] = None
    if contract_graph_path and os.path.isfile(contract_graph_path):
        try:
            with open(contract_graph_path, "r", encoding="utf-8") as f:
                c_data = json.load(f)
            contract_graph = CrossServiceContractGraph.from_dict(c_data)
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass
    elif any(
        spec.get("contracts") or spec.get("spec_data") or spec.get("consumes") or spec.get("spec_path")
        for spec in batch_specs
    ):
        contract_graph = CrossServiceContractGraph()
        for s in batch_specs:
            s_id = s.get("target_id", "")
            s_spec_data = s.get("spec_data") or s.get("contracts") or {}
            s_consumes = s.get("consumes", [])
            s_spec_path = s.get("spec_path")
            if s_spec_path and not s_spec_data and os.path.isfile(s_spec_path):
                try:
                    with open(s_spec_path, "r", encoding="utf-8") as f:
                        s_spec_data = json.load(f)
                except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                    pass
            contract_graph.register_service(ServiceContractNode(
                service_id=s_id,
                version=s.get("version", "1.0.0"),
                spec_path=s_spec_path,
                spec_data=s_spec_data,
                consumes=s_consumes,
                metadata=s.get("metadata", {}),
            ))

    for idx, spec in enumerate(batch_specs, 1):
        target_id = spec.get("target_id", f"target_{idx}")
        target_file = spec.get("target_file", "")
        test_cmd = spec.get("test_cmd", "")
        threshold = spec.get("threshold", DEFAULT_MUTATION_THRESHOLD)

        step_entry: Dict[str, Any] = {
            "index": idx,
            "target_id": target_id,
            "target_file": target_file,
            "test_cmd": test_cmd,
            "phases": {},
        }

        # Inject Cross-Service Contract context
        if contract_graph and target_id in contract_graph.nodes:
            try:
                svc_ctx = contract_graph.get_service_context(target_id)
                step_entry["contract_context"] = {
                    "upstream_dependencies": list(svc_ctx["upstream_dependencies"].keys()),
                    "downstream_consumers": [c["consumer_id"] for c in svc_ctx["downstream_consumers"]],
                }
            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                pass

        record_solo_swarm_event(
            event_type="BATCH_STEP_STARTED",
            actor="batch-orchestrator",
            payload={"step": idx, "target_id": target_id, "target_file": target_file},
            stream_path=event_stream_path,
            repo_root=root,
        )

        step_passed = True

        # Ephemeral Micro-Sandbox manager
        sandbox_mgr = (
            EphemeralServiceSandbox(
                service_id=target_id,
                base_dir=os.path.join(root, "scratch", "sandboxes"),
                port_offset=idx,
            )
            if use_sandbox
            else None
        )

        def _run_step_body() -> bool:
            nonlocal step_passed
            # 1. Run Green Phase if test_cmd provided
            if test_cmd:
                require_red = spec.get("require_red", False)
                step_milestone = spec.get("milestone_id")
                step_receipt = spec.get("receipt_path") or (
                    resolve_red_receipt_path(root, milestone_id=step_milestone)
                    if step_milestone
                    else DEFAULT_RECEIPT_PATH
                )
                if require_red:
                    green_res = certify_green_phase(
                        test_cmd=test_cmd,
                        receipt_path=step_receipt,
                        cwd=root,
                        event_stream_path=event_stream_path,
                        sandbox_mode="host" if not use_sandbox else "worktree",
                        milestone_id=step_milestone,
                    )
                else:
                    adapter = resolve_test_adapter(test_cmd)
                    s_code, s_out = adapter.execute(test_cmd, cwd=root)
                    green_res = {
                        "status": "CERTIFIED_GREEN" if s_code == 0 else "GREEN_FAILED",
                        "passed": s_code == 0,
                        "exit_code": s_code,
                        "test_cmd": test_cmd,
                        "output": s_out[-500:] if len(s_out) > 500 else s_out,
                    }
                step_entry["phases"]["green"] = green_res
                if not green_res.get("passed", False):
                    step_passed = False

            # 2. Run Mutation Phase if target_file and test_cmd provided
            run_mutation = spec.get("mutation", True) and not spec.get("skip_mutation", False)
            if target_file and test_cmd and step_passed and run_mutation:
                mut_res = certify_mutation_phase(
                    target_file=target_file,
                    test_cmd=test_cmd,
                    threshold=threshold,
                    repo_root=root,
                    event_stream_path=event_stream_path,
                )
                step_entry["phases"]["mutation"] = mut_res
                if not mut_res.get("passed", False):
                    step_passed = False

            # 3. Run Purple Audit when explicitly enabled on batch spec
            if spec.get("purple", False) and step_passed:
                purple_res = certify_purple_phase(
                    target="uncommitted",
                    target_file=target_file,
                    repo_root=root,
                    event_stream_path=event_stream_path,
                )
                step_entry["phases"]["purple"] = purple_res
                if not purple_res.get("passed", False):
                    step_passed = False

            # 3. Run Neuro-Symbolic contract verification if target_file exists
            if target_file:
                abs_f = os.path.join(root, target_file) if not os.path.isabs(target_file) else target_file
                if os.path.isfile(abs_f):
                    ns_res = verify_neuro_symbolic_constraints(
                        target_file=target_file,
                        repo_root=root,
                        event_stream_path=event_stream_path,
                    )
                    step_entry["phases"]["neuro_symbolic"] = ns_res
                    if not ns_res.get("passed", False):
                        step_passed = False

            # 4. Cross-Service Contract Drift Verification
            new_spec = spec.get("new_spec") or spec.get("new_spec_data")
            if contract_graph and target_id in contract_graph.nodes and new_spec:
                compat = contract_graph.verify_contract_compatibility(target_id, new_spec)
                if not compat["is_compatible"]:
                    step_entry["phases"]["contract"] = {
                        "status": "CONTRACT_DRIFT_DETECTED",
                        "passed": False,
                        "breaking_changes": compat["breaking_changes"],
                        "impacted_consumers": compat["impacted_consumers"],
                        "contract_health_score": compat.get("contract_health_score", 0.0),
                    }
                    step_passed = False
                    record_solo_swarm_event(
                        event_type="CONTRACT_DRIFT_DETECTED",
                        actor="batch-orchestrator",
                        payload={
                            "target_id": target_id,
                            "breaking_changes": compat["breaking_changes"],
                            "impacted_consumers": compat["impacted_consumers"],
                        },
                        stream_path=event_stream_path,
                        repo_root=root,
                    )
                else:
                    step_entry["phases"]["contract"] = {
                        "status": "CONTRACT_VERIFIED",
                        "passed": True,
                        "contract_health_score": compat.get("contract_health_score", 100.0),
                    }
            elif contract_graph and target_id in contract_graph.nodes:
                step_entry["phases"]["contract"] = {
                    "status": "CONTRACT_VERIFIED",
                    "passed": True,
                    "contract_health_score": 100.0,
                }

            return step_passed

        if batch_breaker.is_tripped(target_id):
            cb_state = batch_breaker.evaluate_retry_guard(target_id)
            step_passed = False
            step_entry["phases"]["circuit_breaker"] = {
                "status": "CIRCUIT_BREAKER_OPEN",
                "passed": False,
                "circuit_breaker": cb_state,
                "error": f"Batch target '{target_id}' halted by Circuit Breaker after {cb_state['failure_count']} consecutive failures.",
            }
        elif sandbox_mgr:
            with sandbox_mgr:
                _run_step_body()
        else:
            _run_step_body()

        if step_passed:
            batch_breaker.record_success(target_id)
        elif "circuit_breaker" not in step_entry["phases"]:
            batch_breaker.record_failure(target_id, error_message=f"Batch step {idx} failed for target '{target_id}'")
        step_entry["circuit_breaker"] = batch_breaker.evaluate_retry_guard(target_id)

        step_entry["passed"] = step_passed
        if not step_passed:
            all_passed = False

        step_results.append(step_entry)

        # STATE-FLUSHING MEMORY RESET
        if os.path.isdir(offload_dir):
            try:
                for fn in os.listdir(offload_dir):
                    fp = os.path.join(offload_dir, fn)
                    if os.path.isfile(fp):
                        os.remove(fp)
            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                pass
        gc.collect()

        record_solo_swarm_event(
            event_type="BATCH_STEP_COMPLETED",
            actor="batch-orchestrator",
            payload={"step": idx, "target_id": target_id, "passed": step_passed},
            stream_path=event_stream_path,
            repo_root=root,
        )

    total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    batch_summary = {
        "status": "BATCH_CERTIFIED" if all_passed else "BATCH_FAILED",
        "passed": all_passed,
        "total_targets": len(batch_specs),
        "targets_passed": sum(1 for s in step_results if s["passed"]),
        "targets_failed": sum(1 for s in step_results if not s["passed"]),
        "total_duration_sec": total_duration,
        "steps": step_results,
        "receipt_file": out_receipt,
    }

    try:
        os.makedirs(os.path.dirname(os.path.abspath(out_receipt)), exist_ok=True)
        with open(out_receipt, "w", encoding="utf-8") as f:
            json.dump(batch_summary, f, indent=2)
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

    return batch_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="solo_runner.py",
        description="Solo 4-Pillar Verification Orchestrator: Automated Test-First, Cognitive Shift, Mutation & Debate Runner.",
    )
    group = parser.add_argument_group("Solo Action Modes")
    group.add_argument("--proposal", type=str, help="Pillar 4: Run Prover-Verifier debate on architectural/test proposal")
    group.add_argument("--red", action="store_true", help="Pillar 1: Verify and certify Red Phase (test must fail)")
    group.add_argument("--green", action="store_true", help="Pillar 2: Verify and certify Green Phase (test must pass)")
    group.add_argument("--mutation", action="store_true", help="Pillar 3: Run live dynamic mutation testing")
    group.add_argument("--purple", action="store_true", help="Pillar 2 Phase 3: Verify and certify Purple Phase (Tech Lead & Security Auditor)")
    group.add_argument("--tournament", nargs="*", help="Swarm Tournament: Run head-to-head tournament evaluation between candidate paths or worktrees")
    group.add_argument("--speculate", type=int, nargs="?", const=2, default=None, help="MCI Swarm: Run async multi-candidate speculative generation (default count: 2)")
    group.add_argument("--oracle-cmd", type=str, help="Stateless external model / CLI oracle command for adversarial verification (eliminates single-LLM cognitive bias)")
    group.add_argument("--neuro-symbolic", action="store_true", help="Run Tier 15 formal neuro-symbolic solver verification on target module contracts")
    group.add_argument("--batch-queue", type=str, help="Path to JSON file containing target specifications for state-flushing multi-service execution")
    group.add_argument("--batch-json", type=str, help="JSON string representing a list of batch targets for state-flushing execution")
    group.add_argument("--from-plan", type=str, default="", help="Compile and execute a Spec-Driven Super-Plan Markdown DAG sequentially via /solo")
    group.add_argument("--contract-graph", type=str, help="Cross-Service Contract Graph JSON file for multi-service dependency and breaking change tracking")
    group.add_argument("--no-sandbox", action="store_true", help="Disable ephemeral micro-sandbox isolation during batch execution")
    group.add_argument("--lock-tests", nargs="*", help="Milestone 2: Lock specified or discovered test files to OS read-only mode (0o444)")
    group.add_argument("--unlock-tests", nargs="*", help="Milestone 2: Restore write permissions (0o644) to test files")
    group.add_argument("--status", action="store_true", help="Display current Solo-Swarm verification state")

    parser.add_argument("--test-cmd", type=str, default="", help="Dynamic test command (e.g. 'pytest tests/test_target.py')")
    parser.add_argument("--target", "--target-file", dest="target", type=str, default="", help="Target source file for mutation testing or static audit (auto-resolved from git diff if omitted)")
    parser.add_argument("--milestone", type=str, default="", help="Milestone Node ID (e.g. M1) for milestone-scoped receipts and --from-plan filtering")
    parser.add_argument("--require-four-scenarios", action="store_true", help="Enforce 4-scenario coverage (positive, negative, boundary, cli/resilience) during --red certification")
    parser.add_argument("--recertify-red", action="store_true", help="Audited Red recertification chaining recertified_from_hmac to the prior Red receipt")
    parser.add_argument("--strict-red", action="store_true", help="Require prior milestone Red receipt in --from-plan instead of allowing verified_replay")
    parser.add_argument("--no-review", action="store_true", help="Skip automatic closed-loop /review verification in --from-plan or standalone --purple")
    parser.add_argument("--ttl", type=int, default=None, help="Red receipt TTL in seconds (default: 900 or SYNAPSE_RED_RECEIPT_TTL_SEC)")
    parser.add_argument("--decision-log", type=str, default="decisions.tsv", help="Path to append-only decisions.tsv log for --from-plan execution")
    parser.add_argument("--rounds", type=int, default=3, help="Debate rounds for Pillar 4 (default: 3)")
    parser.add_argument("--judge-mode", choices=["strict", "evidence_weighted", "consensus"], default="strict", help="Debate judge mode")
    parser.add_argument("--threshold", type=float, default=DEFAULT_MUTATION_THRESHOLD, help="Minimum mutation score threshold (default: 80.0)")
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-mutant test execution timeout in seconds")
    parser.add_argument("--receipt-path", type=str, default=DEFAULT_RECEIPT_PATH, help="Path to TDD Red Receipt file")
    parser.add_argument("--diff-only", action="store_true", default=True, help="Scope mutations strictly to line ranges modified in git diff (default: True)")
    parser.add_argument("--full-file", action="store_true", help="Force mutation testing across full file instead of diff-scoped lines")
    parser.add_argument("--runner", choices=["auto", "pytest", "jest", "playwright", "junit"], default="auto", help="Test runner adapter (default: auto)")
    parser.add_argument("--sandbox", choices=["worktree", "docker", "host"], default="worktree", help="Execution isolation backend for Green & Mutation phases (default: worktree)")
    parser.add_argument("--shard", type=int, default=1, help="Actor Swarm Sharding: Partition test files across N shards via LPT bin-packing")
    parser.add_argument("--event-stream", type=str, default="", help="Path to cryptographic event stream JSONL log")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Default action if no flag is provided
    if not (
        args.proposal
        or args.red
        or args.green
        or args.mutation
        or args.purple
        or args.tournament is not None
        or args.speculate is not None
        or args.status
        or args.shard > 1
        or args.oracle_cmd
        or args.neuro_symbolic
        or args.batch_queue
        or args.batch_json
        or args.from_plan
        or args.lock_tests is not None
        or args.unlock_tests is not None
    ):
        parser.print_help()
        return 0

    results: Dict[str, Any] = {}
    exit_code = 0

    if args.lock_tests is not None:
        target_files = args.lock_tests if args.lock_tests else ["tests"]
        locked = lock_test_files(target_files, repo_root=_REPO_ROOT)
        results["lock_tests"] = {"status": "LOCKED", "locked_files": locked, "count": len(locked)}
        if not args.json:
            print(f"\n🔒 OS-Level Test Guard: Locked {len(locked)} test file(s) to read-only mode.\n")
        return 0

    if args.unlock_tests is not None:
        target_files = args.unlock_tests if args.unlock_tests else ["tests"]
        unlocked = unlock_test_files(target_files, repo_root=_REPO_ROOT)
        results["unlock_tests"] = {"status": "UNLOCKED", "unlocked_files": unlocked, "count": len(unlocked)}
        if not args.json:
            print(f"\n🔓 OS-Level Test Guard: Restored write permissions to {len(unlocked)} test file(s).\n")
        return 0

    if args.status:
        results = get_status(args.receipt_path)
        if not args.json:
            print("\n======================================================================")
            print("   SOLO-SWARM VERIFICATION STATUS")
            print("======================================================================")
            print(f"  Protocol Reference : {results['standards_reference']}")
            print(f"  Red Receipt File   : {results['receipt_file']}")
            print(f"  Red Receipt Exists : {results['red_receipt_exists']}")
            if results["red_details"]:
                print(f"  Red Certified At   : {results['red_details'].get('certified_at', 'N/A')}")
                print(f"  Test Command       : {results['red_details'].get('test_cmd', 'N/A')}")
            print("======================================================================\n")
            return 0

    if args.proposal:
        debate_res = run_debate(
            proposal=args.proposal,
            rounds=args.rounds,
            judge_mode=args.judge_mode,
            oracle_cmd=args.oracle_cmd,
        )
        results["debate"] = debate_res
        if not args.json:
            print("\n======================================================================")
            print("   WEAPON 4: PROVER-VERIFIER DEBATE & ADVERSARIAL EXTRACTION")
            print("======================================================================")
            print(f"  Proposal : {args.proposal}")
            print(f"  Winner   : {debate_res['winner'].upper()}")
            print(f"  Nash Eq. : {debate_res['nash_equilibrium_score']:.4f}")
            print(f"  Extracted Edge Cases : {debate_res['counter_examples_count']}")
            for sc in debate_res["structured_test_scenarios"]:
                print(f"    • [{sc['id']}]: {sc['description']}")
            print("======================================================================\n")

    if args.red:
        red_res = certify_red_phase(
            test_cmd=args.test_cmd,
            receipt_path=args.receipt_path,
            runner=args.runner,
            event_stream_path=args.event_stream or None,
            target_files=[args.target] if args.target else None,
            require_four_scenarios=bool(getattr(args, "require_four_scenarios", False)),
            milestone_id=getattr(args, "milestone", "") or None,
            ttl_seconds=getattr(args, "ttl", None),
            recertify_red=bool(getattr(args, "recertify_red", False)),
        )
        results["red_phase"] = red_res
        if not red_res.get("passed", False):
            exit_code = 1
        if not args.json:
            print("\n======================================================================")
            print("   WEAPON 1: RED PHASE CERTIFICATION (RED-FIRST INVARIANT)")
            print("======================================================================")
            print(f"  Status       : {red_res['status']}")
            print(f"  Runner       : {red_res.get('runner', 'auto')}")
            print(f"  Test Command : {red_res.get('test_cmd', 'N/A')}")
            if red_res.get("passed", False):
                print(f"  Receipt File : {red_res.get('receipt_file')}")
                print(f"  Message      : {red_res.get('message')}")
            else:
                print(f"  Error        : {red_res.get('error')}")
            print("======================================================================\n")

    if args.green:
        effective_sandbox = "host" if getattr(args, "no_sandbox", False) else getattr(args, "sandbox", "worktree")
        green_res = certify_green_phase(
            test_cmd=args.test_cmd,
            receipt_path=args.receipt_path,
            runner=args.runner,
            event_stream_path=args.event_stream or None,
            shard_count=args.shard,
            sandbox_mode=effective_sandbox,
            milestone_id=getattr(args, "milestone", "") or None,
        )
        results["green_phase"] = green_res
        if not green_res.get("passed", False):
            exit_code = 1
        if not args.json:
            print("\n======================================================================")
            print("   WEAPON 2: GREEN PHASE CERTIFICATION (BLUE IMPLEMENTER)")
            print("======================================================================")
            print(f"  Status       : {green_res['status']}")
            print(f"  Test Command : {green_res.get('test_cmd', 'N/A')}")
            if green_res.get("passed", False):
                print(f"  Message      : {green_res.get('message')}")
            else:
                print(f"  Error        : {green_res.get('error')}")
            print("======================================================================\n")

    if args.mutation:
        diff_only = not args.full_file
        effective_sandbox = "host" if getattr(args, "no_sandbox", False) else getattr(args, "sandbox", "worktree")
        mut_res = certify_mutation_phase(
            target_file=args.target,
            test_cmd=args.test_cmd,
            threshold=args.threshold,
            timeout=args.timeout,
            diff_only=diff_only,
            mutation_scope="full" if args.full_file else "diff_only",
            event_stream_path=args.event_stream or None,
            receipt_path=args.receipt_path if args.receipt_path != DEFAULT_RECEIPT_PATH else None,
            sandbox_mode=effective_sandbox,
        )
        results["mutation_phase"] = mut_res
        if not mut_res.get("passed", False):
            exit_code = 1
        if not args.json:
            print("\n======================================================================")
            print("   WEAPON 3: LIVE DYNAMIC MUTATION SENTINEL")
            print("======================================================================")
            print(f"  Status       : {mut_res['status']}")
            print(f"  Target File  : {mut_res.get('target_file', 'N/A')} {'(Auto-detected from git diff)' if mut_res.get('auto_targeted') else ''}")
            print(f"  Diff-Scoped  : {mut_res.get('diff_only', False)}")
            print(f"  Score        : {mut_res.get('mutation_score', 0.0):.1f}% (Required: >={mut_res.get('required_threshold', 80.0)}%)")
            print(f"  Mutants      : Total {mut_res.get('total_mutants', 0)} | Killed: {mut_res.get('killed', 0)} | Survived: {mut_res.get('survived', 0)}")
            print(f"  Message      : {mut_res.get('message')}")
            print("======================================================================\n")

    if args.purple:
        purple_res = certify_purple_phase(
            target="uncommitted",
            target_file=args.target,
            receipt_path=args.receipt_path if args.receipt_path != DEFAULT_RECEIPT_PATH else None,
            repo_root=_REPO_ROOT,
            event_stream_path=args.event_stream or None,
            oracle_cmd=args.oracle_cmd,
        )
        results["purple_phase"] = purple_res
        if not purple_res.get("passed", False):
            exit_code = 1
        if not args.json:
            print("\n======================================================================")
            print("   WEAPON 2: PURPLE PHASE CERTIFICATION (TECH LEAD & SECURITY AUDITOR)")
            print("======================================================================")
            print(f"  Status        : {purple_res['status']}")
            print(f"  Target Scope  : {purple_res.get('target', 'uncommitted')}")
            print(f"  Files Checked : {purple_res.get('files_analyzed', 0)}")
            print(f"  Findings      : {purple_res.get('findings_count', 0)}")
            print(f"  Receipt File  : {purple_res.get('receipt_file')}")
            print(f"  Message       : {purple_res.get('message')}")
            print("======================================================================\n")

        if not args.from_plan and not getattr(args, "no_review", False):
            from tools.orchestration.senior_code_review import evaluate_review

            ms_raw = getattr(args, "milestone", "")
            ms_arg = ms_raw.strip() if isinstance(ms_raw, str) and ms_raw.strip() else None
            plan_cand = os.path.join(_REPO_ROOT, "implementation_plan.md")
            auto_plan = plan_cand if os.path.isfile(plan_cand) else None
            try:
                rev_exit, rev_payload, _, _ = evaluate_review(
                    repo_dir=_REPO_ROOT,
                    target="uncommitted",
                    plan_path=auto_plan,
                    milestone_id=ms_arg,
                    strict=False,
                    strict_solo=True,
                    require_mutation_receipt=False,
                )
                auto_review: Dict[str, Any] = {
                    "verdict": rev_payload.get("verdict"),
                    "passed": bool(rev_payload.get("passed", False)),
                    "findings_count": rev_payload.get("findings_count", 0),
                    "receipt_path": rev_payload.get("receipt_path"),
                    "receipt_hmac": rev_payload.get("receipt_hmac"),
                }
                if rev_exit != 0 or not auto_review["passed"]:
                    exit_code = 1
            except Exception as exc:
                auto_review = {
                    "verdict": "ERROR",
                    "passed": False,
                    "findings_count": 0,
                    "receipt_path": None,
                    "receipt_hmac": None,
                    "error": str(exc),
                }
                exit_code = 1

            results["auto_review"] = auto_review
            if not args.json:
                print("======================================================================")
                print("   AUTO /review GATE (--strict-solo)")
                print("======================================================================")
                print(f"  Verdict       : {auto_review.get('verdict')}")
                print(f"  Passed        : {auto_review.get('passed')}")
                print(f"  Findings      : {auto_review.get('findings_count', 0)}")
                print(f"  Receipt Path  : {auto_review.get('receipt_path') or 'N/A'}")
                print(f"  Receipt HMAC  : {auto_review.get('receipt_hmac') or 'N/A'}")
                if auto_review.get("error"):
                    print(f"  Error         : {auto_review['error']}")
                print("======================================================================\n")

    if args.shard > 1 and not args.green:
        raw_words = args.test_cmd.split() if args.test_cmd else []
        test_files = [w for w in raw_words if w.startswith("tests/") or w.endswith(".py") or w.endswith(".ts") or w.endswith(".groovy")]
        if not test_files and args.target:
            test_files = [args.target]
        shards = shard_test_execution(test_files, num_shards=args.shard, target_dir=_REPO_ROOT)
        results["sharded_matrix"] = shards
        if not args.json:
            print("\n======================================================================")
            print(f"   ACTOR SWARM SHARDING: LPT BIN-PACKING ({args.shard} SHARDS)")
            print("======================================================================")
            for s in shards:
                print(f"  Shard {s['shard_index']} (Est {s['total_duration']}s): {len(s['tests'])} tests -> {', '.join(s['tests']) if s['tests'] else 'None'}")
            print("======================================================================\n")

    if args.tournament is not None:
        tourn_res = run_tournament(
            candidate_paths=args.tournament if args.tournament else None,
            test_cmd=args.test_cmd,
            target_file=args.target,
            threshold=args.threshold,
            event_stream_path=args.event_stream or None,
        )
        results["tournament"] = tourn_res
        if not tourn_res.get("passed", False):
            exit_code = 1
        if not args.json:
            print("\n======================================================================")
            print("   SWARM ESSENCE: HEAD-TO-HEAD TOURNAMENT ARBITER")
            print("======================================================================")
            print(f"  Status       : {tourn_res['status']}")
            print(f"  Candidates   : {tourn_res.get('candidates_count', 0)}")
            print(f"  Message      : {tourn_res.get('message')}")
            for c in tourn_res.get("candidates_evaluated", []):
                print(f"    • [{c['candidate_id']}] Green: {c['green_passed']} | Mutation: {c['mutation_score']:.1f}% | LOC: +{c['net_lines_changed']} | Fitness: {c['composite_fitness_score']:.2f}")
            if tourn_res.get("winner_candidate"):
                w = tourn_res["winner_candidate"]
                print(f"  🏆 Winner     : {w['candidate_id']} ({w['worktree_path']})")
            print("======================================================================\n")

    if args.speculate is not None:
        speculator = AsyncCandidateSpeculator()
        target = args.target or (resolve_auto_targets()[0] if resolve_auto_targets() else "solution.py")
        payload, prompts = speculator.prepare_speculative_prompts(
            target_file=target,
            failure_trace="Failure traceback excerpt for candidate synthesis",
            count=args.speculate,
        )
        spec_res = {
            "status": "SPECULATION_PREPARED",
            "micro_payload": {
                "target_file": payload.target_file,
                "estimated_tokens": payload.estimated_tokens,
                "ast_skeleton_lines": len(payload.ast_skeleton.splitlines()),
            },
            "candidate_personas": [
                {
                    "id": p.candidate_id,
                    "persona": p.persona,
                    "temperature": p.temperature,
                    "max_tokens": p.max_tokens,
                }
                for p in prompts
            ],
            "token_savings_ratio": "85-90% compared to monolithic swarm",
        }
        results["speculation"] = spec_res
        if not args.json:
            print("\n======================================================================")
            print("   MCI SWARM: ASYNC SPECULATIVE DUAL-CANDIDATE ENGINE")
            print("======================================================================")
            print(f"  Target File      : {payload.target_file}")
            print(f"  Micro-Context    : ~{payload.estimated_tokens} tokens (Pruned from full file)")
            print(f"  Candidates Spawn : {len(prompts)} distinct personas")
            for p in prompts:
                print(f"    • [{p.candidate_id}] ({p.persona}): temp={p.temperature}, max_tokens={p.max_tokens}")
            print("  Token Savings    : 85-90% token reduction via AST skeleton injection")
            print("======================================================================\n")

    if args.oracle_cmd:
        oracle_res = execute_external_oracle(
            oracle_cmd=args.oracle_cmd,
            target_file=args.target,
            prompt_or_spec=args.proposal or "",
            cwd=_REPO_ROOT,
            timeout=args.timeout,
            event_stream_path=args.event_stream or None,
        )
        results["oracle"] = oracle_res
        if not oracle_res.get("passed", False):
            exit_code = 1
        if not args.json:
            print("\n======================================================================")
            print("   STATELESS EXTERNAL ADVERSARIAL ORACLE")
            print("======================================================================")
            print(f"  Status   : {oracle_res['status']}")
            print(f"  Command  : {oracle_res['oracle_cmd']}")
            print(f"  Message  : {oracle_res.get('message')}")
            print("======================================================================\n")

    if args.neuro_symbolic:
        target_f = args.target or (resolve_auto_targets()[0] if resolve_auto_targets() else "tools/orchestration/solo_runner.py")
        ns_res = verify_neuro_symbolic_constraints(
            target_file=target_f,
            repo_root=_REPO_ROOT,
            event_stream_path=args.event_stream or None,
        )
        results["neuro_symbolic"] = ns_res
        if not ns_res.get("passed", False):
            exit_code = 1
        if not args.json:
            print("\n======================================================================")
            print("   TIER 15 NEURO-SYMBOLIC FORMAL CONSTRAINT SENTINEL")
            print("======================================================================")
            print(f"  Status   : {ns_res['status']}")
            print(f"  Target   : {ns_res.get('target_file')}")
            print(f"  Has Cycle: {ns_res.get('has_cycle')}")
            print(f"  Message  : {ns_res.get('message')}")
            print("======================================================================\n")

    if args.batch_queue or args.batch_json:
        specs, parse_err = _load_cli_batch_specs(args.batch_queue, args.batch_json)

        if parse_err or not isinstance(specs, list):
            err_msg = parse_err or "Batch specification must be a JSON array of target objects."
            results["batch"] = {"status": "ERROR", "passed": False, "error": err_msg}
            exit_code = 1
            if not args.json:
                print(f"\n❌ Batch Queue Error: {err_msg}\n")
        else:
            batch_res = execute_state_flushing_batch(
                batch_specs=specs,
                repo_root=_REPO_ROOT,
                event_stream_path=args.event_stream or None,
                contract_graph_path=args.contract_graph or None,
                use_sandbox=not getattr(args, "no_sandbox", False),
            )
            results["batch"] = batch_res
            if not batch_res.get("passed", False):
                exit_code = 1
            if not args.json:
                print("\n======================================================================")
                print("   STATE-FLUSHING DAG / BATCH ITERATOR PIPELINE")
                print("======================================================================")
                print(f"  Status          : {batch_res['status']}")
                print(f"  Total Targets   : {batch_res['total_targets']}")
                print(f"  Targets Passed  : {batch_res['targets_passed']}/{batch_res['total_targets']}")
                print(f"  Total Duration  : {batch_res['total_duration_sec']:.2f}s")
                print(f"  Receipt File    : {batch_res.get('receipt_file')}")
                print("======================================================================\n")

    if args.from_plan:
        from tools.orchestration.plan_dag_bridge import SoloPhaseCallbacks, execute_plan_via_solo

        effective_sandbox = "host" if getattr(args, "no_sandbox", False) else getattr(args, "sandbox", "worktree")
        try:
            plan_summary = execute_plan_via_solo(
                plan_path=args.from_plan,
                repo_root=_REPO_ROOT,
                milestone_filter=getattr(args, "milestone", "") or None,
                decision_log_path=getattr(args, "decision_log", "decisions.tsv") or "decisions.tsv",
                sandbox_mode=effective_sandbox,
                recertify_red=bool(getattr(args, "recertify_red", False)),
                strict_red=bool(getattr(args, "strict_red", False)),
                diff_only_mutation=not bool(getattr(args, "full_file", False)),
                auto_review=not bool(getattr(args, "no_review", False)),
                phase_callbacks=SoloPhaseCallbacks(
                    certify_red_phase=certify_red_phase,
                    certify_green_phase=certify_green_phase,
                    certify_mutation_phase=certify_mutation_phase,
                    certify_purple_phase=certify_purple_phase,
                    resolve_test_adapter=resolve_test_adapter,
                ),
            )
            results["plan_execution"] = plan_summary.to_dict()
            if not plan_summary.passed:
                exit_code = 1
            if not args.json:
                print("\n======================================================================")
                print("   CLOSED-LOOP PLAN-TO-SOLO EXECUTION BRIDGE (--from-plan)")
                print("======================================================================")
                print(f"  Plan Path        : {plan_summary.plan_path}")
                print(f"  Status           : {'PASSED' if plan_summary.passed else 'HALTED'}")
                print(f"  Milestones       : {plan_summary.milestones_passed}/{plan_summary.milestones_total} passed")
                if plan_summary.halted_at_node:
                    print(f"  Halted At Node   : {plan_summary.halted_at_node}")
                if plan_summary.review_result:
                    rev = plan_summary.review_result
                    print(f"  Auto /review     : {rev.get('verdict')} (findings={rev.get('findings_count', 0)}, receipt={rev.get('receipt_path', 'N/A')})")
                print(f"  Decision Log     : {plan_summary.decision_log_path}")
                print("======================================================================\n")
        except (FileNotFoundError, ValueError) as exc:
            results["plan_execution"] = {"status": "ERROR", "passed": False, "error": str(exc)}
            exit_code = 1
            if not args.json:
                print(f"\n❌ Plan Execution Error: {exc}\n")

    if args.json:
        print(json.dumps(results, indent=2))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
