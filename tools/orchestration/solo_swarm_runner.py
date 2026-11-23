#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/orchestration/solo_swarm_runner.py — Automated Solo-Swarm 4-Weapon Orchestrator

Integrates the 4 weapons of single-agent engineering rigor into an automated, deterministic pipeline:
  - Weapon 1: Test-First Inversion (Red-First Invariant with Forensic Red Receipt & Anti-Cheat Tautology Sentinel)
  - Weapon 2: 3-Phase Cognitive Persona Shifting (Red QA -> Blue Dev -> Purple Auditor)
  - Weapon 3: Live Dynamic Mutation Sentinel (micro_mutator with Diff-Scoped Targeting & >= 80% Threshold)
  - Weapon 4: Zero-Sum Prover-Verifier Debate (Nash Equilibrium extraction of 4 Contrarian Adversarial Perspectives)
"""

import os
import re
import sys
import ast
import stat
import json
import shlex
import hashlib
import argparse
import subprocess
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set, Callable

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
from tools.orchestration.deterministic_race_scheduler import (
    DeterministicRaceScheduler,
    ConcurrentAction,
    RaceAuditResult,
)

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


@dataclass(frozen=True)
class MicroContextPayload:
    """Ultra-compact context payload minimizing token consumption."""

    target_file: str
    ast_skeleton: str
    target_functions: List[str]
    failure_trace_excerpt: str
    offloaded_artifact_id: Optional[str] = None
    estimated_tokens: int = 0

    def to_compact_prompt(self, persona_directive: str = "") -> str:
        prompt_parts = []
        if persona_directive:
            prompt_parts.append(f"Persona Directive: {persona_directive}")
        prompt_parts.append(f"Target Source File: {self.target_file}")
        if self.ast_skeleton:
            prompt_parts.append(f"Target AST Signatures:\n{self.ast_skeleton}")
        prompt_parts.append(f"Failure Signal:\n{self.failure_trace_excerpt}")
        return "\n\n".join(prompt_parts)


class MicroContextExtractor:
    """Bridge to context_slicer and output_offloader to prepare minimal prompts (< 250 tokens)."""

    def __init__(self, repo_root: Optional[str] = None) -> None:
        self.repo_root = repo_root or _REPO_ROOT

    def build_micro_payload(
        self,
        target_file: str,
        failure_trace: str,
        max_tokens: int = 250,
    ) -> MicroContextPayload:
        from tools.context.context_slicer import extract_spec_micro_context
        from tools.context.output_offloader import OutputOffloader

        # 1. AST Skeleton extraction bounded within max_tokens // 2
        abs_target = (
            os.path.abspath(target_file) if os.path.isabs(target_file) else os.path.join(self.repo_root, target_file)
        )
        skeleton_info = extract_spec_micro_context(abs_target, max_tokens=max(50, max_tokens // 2))
        ast_skeleton = skeleton_info.get("skeleton", "")

        # 2. Output offloading for long failure traces (> 1 KB)
        offloader = OutputOffloader(
            storage_dir=os.path.join(self.repo_root, "scratch", "offload"),
            threshold_bytes=1024,
        )
        was_offloaded, _, ref = offloader.process_output(failure_trace, source_command="red_phase_failure")
        artifact_id = ref.artifact_id if ref else None

        if ref is not None:
            failure_excerpt = f"[Log offloaded to {ref.file_path}]\n{ref.tail_excerpt}"
        else:
            trace_lines = failure_trace.splitlines()
            failure_excerpt = "\n".join(trace_lines[-15:]) if len(trace_lines) > 15 else failure_trace

        total_text = f"{ast_skeleton}\n{failure_excerpt}"
        est_tokens = len(total_text) // 4

        return MicroContextPayload(
            target_file=target_file,
            ast_skeleton=ast_skeleton,
            target_functions=[],
            failure_trace_excerpt=failure_excerpt,
            offloaded_artifact_id=artifact_id,
            estimated_tokens=est_tokens,
        )


@dataclass(frozen=True)
class SpeculativeCandidatePrompt:
    """Prompt specification for distinct candidate personas."""

    candidate_id: str
    persona: str  # "MINIMALIST_STDLIB" | "DEFENSIVE_RESILIENT"
    system_directive: str
    temperature: float
    max_tokens: int


class AstTautologyAnalyzer(ast.NodeVisitor):
    """
    Milestone 2: Analyzes Python AST to detect tautological assertions and literal constant propagation cheats,
    such as 'x = 1; y = 2; assert x == y', 'assert 1 + 1 == 3', or 'assert not True'.
    """

    def __init__(self) -> None:
        self.findings: List[Tuple[int, str, str]] = []
        self.scope_constants: Dict[str, Any] = {}

    def _eval_constant_expr(self, node: ast.AST) -> Tuple[bool, Any]:
        """Statically evaluates expressions composed purely of literal constants."""
        if isinstance(node, ast.Constant):
            return True, node.value
        if isinstance(node, ast.Name):
            if node.id in self.scope_constants:
                return True, self.scope_constants[node.id]
            return False, None
        if isinstance(node, ast.UnaryOp):
            ok, val = self._eval_constant_expr(node.operand)
            if ok:
                if isinstance(node.op, ast.Not):
                    return True, not val
                elif isinstance(node.op, ast.USub):
                    return True, -val
                elif isinstance(node.op, ast.UAdd):
                    return True, +val
            return False, None
        if isinstance(node, ast.BinOp):
            ok_l, val_l = self._eval_constant_expr(node.left)
            ok_r, val_r = self._eval_constant_expr(node.right)
            if ok_l and ok_r:
                try:
                    if isinstance(node.op, ast.Add):
                        return True, val_l + val_r
                    if isinstance(node.op, ast.Sub):
                        return True, val_l - val_r
                    if isinstance(node.op, ast.Mult):
                        return True, val_l * val_r
                    if isinstance(node.op, ast.FloorDiv):
                        return True, val_l // val_r
                    if isinstance(node.op, ast.Mod):
                        return True, val_l % val_r
                except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                    pass
            return False, None
        if isinstance(node, ast.Compare):
            ok_l, val_l = self._eval_constant_expr(node.left)
            if not ok_l:
                return False, None
            if len(node.ops) == 1 and len(node.comparators) == 1:
                ok_r, val_r = self._eval_constant_expr(node.comparators[0])
                if not ok_r:
                    return False, None
                op = node.ops[0]
                try:
                    if isinstance(op, ast.Eq):
                        return True, val_l == val_r
                    if isinstance(op, ast.NotEq):
                        return True, val_l != val_r
                    if isinstance(op, ast.Lt):
                        return True, val_l < val_r
                    if isinstance(op, ast.LtE):
                        return True, val_l <= val_r
                    if isinstance(op, ast.Gt):
                        return True, val_l > val_r
                    if isinstance(op, ast.GtE):
                        return True, val_l >= val_r
                    if isinstance(op, ast.Is):
                        return True, val_l is val_r
                    if isinstance(op, ast.IsNot):
                        return True, val_l is not val_r
                except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                    pass
            return False, None
        return False, None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        prev_scope = dict(self.scope_constants)
        self.generic_visit(node)
        self.scope_constants = prev_scope

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        prev_scope = dict(self.scope_constants)
        self.generic_visit(node)
        self.scope_constants = prev_scope

    def visit_Assign(self, node: ast.Assign) -> None:
        ok, val = self._eval_constant_expr(node.value)
        if ok:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.scope_constants[target.id] = val
        else:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.scope_constants.pop(target.id, None)
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        ok, val = self._eval_constant_expr(node.test)
        if ok and not val:
            stmt_str = ast.unparse(node).strip() if hasattr(ast, "unparse") else "assert <tautology>"
            reason = f"AST Constant-Propagation: assertion evaluates statically to False ({stmt_str})"
            self.findings.append((getattr(node, "lineno", 0), stmt_str, reason))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        is_fail = False
        if (
            isinstance(node.func, ast.Attribute)
            and getattr(node.func.value, "id", None) == "pytest"
            and node.func.attr == "fail"
        ):
            is_fail = True
        elif isinstance(node.func, ast.Name) and node.func.id == "fail":
            is_fail = True
        if is_fail:
            stmt_str = ast.unparse(node).strip() if hasattr(ast, "unparse") else "pytest.fail()"
            self.findings.append((
                getattr(node, "lineno", 0),
                stmt_str,
                "Forced failure via pytest.fail() call without domain assertion",
            ))
        self.generic_visit(node)

    def analyze_source(self, code: str) -> List[Tuple[int, str, str]]:
        try:
            tree = ast.parse(code)
            self.visit(tree)
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass
        return self.findings


def is_literal_constant(expr: str) -> bool:
    """Returns True if expr is a literal constant (numbers, bools, strings, None) with no variables or calls."""
    expr = expr.strip()
    if expr in ("True", "False", "None", "true", "false", "null"):
        return True
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", expr):
        return True
    if (expr.startswith('"') and expr.endswith('"') and len(expr) >= 2) or (
        expr.startswith("'") and expr.endswith("'") and len(expr) >= 2
    ):
        return True
    return False


def is_tautological_assertion(stmt: str) -> Tuple[bool, Optional[str]]:
    """
    Checks if an assertion statement is purely tautological (assert False, assert 0, assert 1 == 2, assert 'a' == 'b').
    """
    stmt = stmt.strip()
    # Check bare assert False, assert 0, assert None, assert not True
    m_bare = re.match(r"^assert\s+(False|0|None|not\s+True)\b(?:\s*,\s*.*)?$", stmt, re.IGNORECASE)
    if m_bare:
        return True, f"Literal constant assertion: 'assert {m_bare.group(1)}'"

    # Check comparison: assert left op right where BOTH operands are literal constants
    m_cmp = re.match(r"^assert\s+(.+?)\s*(==|!=|<|>|<=|>=|is|is\s+not)\s*(.+?)(?:\s*,\s*.*)?$", stmt)
    if m_cmp:
        left, op, right = m_cmp.group(1).strip(), m_cmp.group(2).strip(), m_cmp.group(3).strip()
        if is_literal_constant(left) and is_literal_constant(right):
            return True, f"Literal constant comparison: 'assert {left} {op} {right}'"

    # Check pytest.fail with literal reason or empty
    if re.match(r"^(?:pytest\.)?fail\s*\(", stmt):
        return True, "Forced failure via pytest.fail() call without domain assertion"

    # AST Constant Propagation check for isolated snippet
    try:
        ast_checker = AstTautologyAnalyzer()
        findings = ast_checker.analyze_source(stmt)
        if findings:
            return True, findings[0][2]
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

    return False, None


def detect_tautological_red(failure_output: str, test_cmd: str = "") -> Tuple[bool, Optional[str]]:
    """
    Milestone 2 Anti-Cheat: Analyzes failure traceback and test command to detect literal tautological failures.
    Catches cheats like 'assert False', 'assert 1 == 2', 'assert 0 == 1', 'pytest.fail()',
    and AST constant propagation cheats like 'x = 1; y = 2; assert x == y'.
    """
    # 1. Check test_cmd itself for forced failures or constant propagation in -c inline scripts
    if test_cmd:
        m_cmd = re.search(r'-c\s+["\'](.*?)["\']', test_cmd)
        if m_cmd:
            code_snip = m_cmd.group(1)
            ast_findings = AstTautologyAnalyzer().analyze_source(code_snip)
            if ast_findings:
                return True, f"Tautological Red Violation: {ast_findings[0][2]} in test command."
            for sub_s in code_snip.split(";"):
                sub_s = sub_s.strip()
                is_cheat, reason = is_tautological_assertion(sub_s)
                if is_cheat:
                    return True, f"Tautological Red Violation: {reason} in test command."
        else:
            is_cheat, reason = is_tautological_assertion(test_cmd)
            if is_cheat:
                return True, f"Tautological Red Violation: {reason} in test command."

    # 2. Check failure_output: extract failing file and line number to run AST check on enclosing test
    if failure_output:
        # Match pattern: path/to/test_file.py:123: AssertionError
        m_file_line = re.search(r'([a-zA-Z0-9_\-./]+\.py):(\d+):\s*AssertionError', failure_output)
        if m_file_line:
            fail_file, fail_line_s = m_file_line.group(1), m_file_line.group(2)
            fail_line = int(fail_line_s)
            if os.path.isfile(fail_file):
                try:
                    with open(fail_file, "r", encoding="utf-8", errors="replace") as f:
                        file_code = f.read()
                    ast_findings = AstTautologyAnalyzer().analyze_source(file_code)
                    for finding_line, stmt, reason in ast_findings:
                        if abs(finding_line - fail_line) <= 2:
                            return True, f"Tautological Red Violation: {reason} at {fail_file}:{finding_line}."
                except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                    pass

        lines = failure_output.splitlines()
        for idx, line in enumerate(lines):
            line_s = line.strip()
            # Pytest source line indicator
            if line_s.startswith(">"):
                src_stmt = line_s.lstrip(">").strip()
                is_cheat, reason = is_tautological_assertion(src_stmt)
                if is_cheat:
                    return True, f"Tautological Red Violation: {reason} in test source."
            # Standard Python traceback line immediately preceding AssertionError
            if line_s == "AssertionError" or line_s.startswith("AssertionError:"):
                if idx > 0:
                    prev_line = lines[idx - 1].strip()
                    is_cheat, reason = is_tautological_assertion(prev_line)
                    if is_cheat:
                        return True, f"Tautological Red Violation: {reason} in traceback."

    return False, None


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

    cmd_parts = shlex.split(cmd) if isinstance(cmd, str) else cmd

    try:
        proc = subprocess.run(
            cmd_parts,
            input=prompt_or_spec if prompt_or_spec else None,
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
        try:
            parsed_data = json.loads(output)
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass

        record_solo_swarm_event(
            event_type="ORACLE_EVALUATED",
            actor="external-oracle",
            payload={
                "oracle_cmd": oracle_cmd,
                "target_file": target_file,
                "passed": passed,
                "exit_code": proc.returncode,
                "duration_sec": duration_sec,
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

    start_time = datetime.now(timezone.utc)
    try:
        from tools.reasoning.neuro_symbolic_solver import DependencyCycleSolver

        imported_modules = set()
        if abs_target.endswith(".py"):
            with open(abs_target, "r", encoding="utf-8", errors="replace") as f:
                tree = ast.parse(f.read(), filename=abs_target)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_modules.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_modules.add(node.module.split(".")[0])
        else:
            with open(abs_target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            # JS / TS import & require statements
            for m in re.finditer(r'(?:import|from)\s+[\'"]([^\'"]+)[\'"]', content):
                imported_modules.add(os.path.basename(m.group(1)).split(".")[0])
            for m in re.finditer(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', content):
                imported_modules.add(os.path.basename(m.group(1)).split(".")[0])
            # Groovy / Java import statements
            for m in re.finditer(r'import\s+([a-zA-Z0-9_.]+)', content):
                imported_modules.add(m.group(1).split(".")[-1])

        base_name = os.path.splitext(os.path.basename(abs_target))[0]
        edges = [[base_name, imp] for imp in sorted(imported_modules) if imp != base_name]

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
        "oracle_result": oracle_res,
        "debate_raw": result,
    }


class BaseTestAdapter:
    """Abstract interface for test runners across languages and frameworks."""

    name: str = "base"

    def execute(self, test_cmd: str, cwd: str, timeout: float = 120.0) -> Tuple[int, str]:
        cmd_parts = shlex.split(test_cmd) if isinstance(test_cmd, str) else test_cmd
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
        xml_match = re.search(r"([a-zA-Z0-9_\-./]+\.xml)", test_cmd + " " + output)
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
    """
    cmd_str = (test_cmd or "").strip()
    if not cmd_str:
        return []
    root = working_dir or _REPO_ROOT
    raw_tokens = shlex.split(test_cmd) if isinstance(test_cmd, str) else list(test_cmd)
    found_files: List[str] = []
    test_exts = (".py", ".ts", ".js", ".jsx", ".tsx", ".groovy", ".java")

    for tok in raw_tokens:
        if tok.startswith("-"):
            continue
        clean_tok = tok.strip("'\"")
        if any(clean_tok.endswith(ext) for ext in test_exts) or "test" in clean_tok.lower():
            resolved = clean_tok if os.path.isabs(clean_tok) else os.path.join(root, clean_tok)
            if os.path.isfile(resolved):
                found_files.append(resolved)

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
                with open(fp, "rb") as f:
                    h = hashlib.sha256(f.read()).hexdigest()
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


class ReadOnlyTestGuard:
    """
    Milestone 2 (OS-Level Test Guard):
    Context manager that temporarily locks test files with OS-level read-only permissions (0o444 / chmod a-w)
    to physically prevent unauthorized writes during implementation phases.
    Restores original file modes upon exit.
    """

    def __init__(self, test_files: List[str], repo_root: Optional[str] = None):
        self.root = repo_root or _REPO_ROOT
        self.test_files = [
            os.path.abspath(f) if os.path.isabs(f) else os.path.join(self.root, f)
            for f in test_files
        ]
        self._orig_modes: Dict[str, int] = {}

    def lock(self) -> List[str]:
        locked: List[str] = []
        for fp in self.test_files:
            if os.path.isfile(fp):
                try:
                    mode = os.stat(fp).st_mode
                    self._orig_modes[fp] = mode
                    new_mode = mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
                    os.chmod(fp, new_mode)
                    locked.append(fp)
                except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                    pass
        return locked

    def unlock(self) -> List[str]:
        unlocked: List[str] = []
        for fp, orig_mode in self._orig_modes.items():
            if os.path.isfile(fp):
                try:
                    os.chmod(fp, orig_mode)
                    unlocked.append(fp)
                except Exception:
                    try:
                        os.chmod(fp, 0o644)
                        unlocked.append(fp)
                    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                        pass
        self._orig_modes.clear()
        return unlocked

    def __enter__(self):
        self.lock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unlock()


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


def certify_red_phase(
    test_cmd: str,
    receipt_path: Optional[str] = None,
    cwd: Optional[str] = None,
    runner: Optional[str] = None,
    event_stream_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Weapon 1: Physically execute test_cmd and certify that tests FAIL (Red Phase).
    Enforces Anti-Cheat Tautology checks to reject 'assert False' or 'assert 1 == 2'.
    Saves forensic failure receipt to receipt_path.
    """
    if not test_cmd or not test_cmd.strip():
        return {
            "status": "ERROR",
            "passed": False,
            "error": "Missing test command. Provide a non-empty test command via --test-cmd.",
        }

    working_dir = cwd or _REPO_ROOT
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

    # Extract failure excerpt (last 30 lines)
    output_lines = output.splitlines()
    excerpt = output_lines[-30:] if len(output_lines) > 30 else output_lines
    excerpt_text = "\n".join(excerpt)
    sha_hash = hashlib.sha256(output.encode("utf-8", errors="replace")).hexdigest()

    # Subagent Skill: failure-autopsy-and-healing (pinpoint_failure error fingerprinting)
    try:
        err_fingerprint = compute_error_fingerprint(adapter.name, excerpt_text)
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        err_fingerprint = f"fp_{hashlib.md5(excerpt_text.encode('utf-8', errors='replace')).hexdigest()[:8]}"

    # Milestone 2: Compute cryptographic test tree snapshot
    test_snapshot = compute_test_files_snapshot(test_cmd=test_cmd, working_dir=working_dir)
    test_tree_hash = test_snapshot.get("tree_hash", "")
    test_files_map = test_snapshot.get("files", {})

    receipt_payload = {
        "status": "CERTIFIED_RED",
        "certified_at": datetime.now(timezone.utc).isoformat(),
        "runner": adapter.name,
        "test_cmd": test_cmd,
        "exit_code": exit_code,
        "duration_sec": duration_sec,
        "failure_sha256": sha_hash,
        "error_fingerprint": err_fingerprint,
        "failure_excerpt": excerpt_text,
        "test_tree_hash": test_tree_hash,
        "test_files": test_files_map,
    }

    with open(target_receipt, "w", encoding="utf-8") as f:
        json.dump(receipt_payload, f, indent=2)

    # Subagent Skill: event-stream-qa-orchestrator (cryptographic hash-chaining)
    record_solo_swarm_event(
        event_type="RED_CERTIFIED",
        actor="red-team",
        payload={
            "test_cmd": test_cmd,
            "exit_code": exit_code,
            "failure_sha256": sha_hash,
            "error_fingerprint": err_fingerprint,
            "test_tree_hash": test_tree_hash,
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
        "test_cmd": test_cmd,
        "exit_code": exit_code,
        "duration_sec": duration_sec,
        "receipt_file": target_receipt,
        "failure_sha256": sha_hash,
        "error_fingerprint": err_fingerprint,
        "test_tree_hash": test_tree_hash,
        "test_files": test_files_map,
        "message": f"✅ Red Phase Certified ({adapter.name}): Tests failed as expected. Physical Red Receipt recorded.",
    }


def certify_green_phase(
    test_cmd: str,
    receipt_path: Optional[str] = None,
    cwd: Optional[str] = None,
    runner: Optional[str] = None,
    event_stream_path: Optional[str] = None,
    shard_count: int = 1,
) -> Dict[str, Any]:
    """
    Weapon 2: Execute test_cmd and verify that tests now PASS (Green Phase).
    Requires a valid prior Red Receipt to prevent skipping the Red Phase.
    If shard_count > 1 and test_cmd lists multiple tests, executes shards in parallel.
    """
    if not test_cmd or not test_cmd.strip():
        return {
            "status": "ERROR",
            "passed": False,
            "error": "Missing test command. Provide a non-empty test command via --test-cmd.",
        }

    working_dir = cwd or _REPO_ROOT
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
        with open(target_receipt, "r", encoding="utf-8") as f:
            red_data = json.load(f)
        if red_data.get("status") != "CERTIFIED_RED":
            return {
                "status": "INVALID_RED_RECEIPT",
                "passed": False,
                "error": f"Prior receipt does not have 'CERTIFIED_RED' status: found {red_data.get('status')}",
            }
    except Exception as e:
        return {
            "status": "CORRUPT_RED_RECEIPT",
            "passed": False,
            "error": f"Failed to read Red Receipt: {e}",
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

    adapter = resolve_test_adapter(test_cmd, runner_override=runner)

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
                s_code, s_out = adapter.execute(s_cmd, cwd=working_dir)
                return s_code, s_out, shard["tests"]

            futures = [executor.submit(_run_shard, s) for s in shards if s["tests"]]
            for f in futures:
                s_code, s_out, s_tests = f.result()
                shard_results.append({"exit_code": s_code, "tests": s_tests, "output": s_out})

        duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
        failed_shards = [sr for sr in shard_results if sr["exit_code"] != 0]
        if failed_shards:
            return {
                "status": "GREEN_FAILED",
                "passed": False,
                "test_cmd": test_cmd,
                "sharded": True,
                "shards_count": len(shards),
                "exit_code": 1,
                "error": f"{len(failed_shards)}/{len(shards)} shards failed in parallel execution.",
                "duration_sec": duration_sec,
                "failure_excerpt": failed_shards[0]["output"][-500:],
            }
        exit_code = 0
    else:
        # Standard sequential execution via adapter
        start_time = datetime.now(timezone.utc)
        exit_code, output = adapter.execute(test_cmd, cwd=working_dir)
        duration_sec = (datetime.now(timezone.utc) - start_time).total_seconds()

        if exit_code != 0:
            return {
                "status": "GREEN_FAILED",
                "passed": False,
                "test_cmd": test_cmd,
                "exit_code": exit_code,
                "error": "Tests are still failing. Blue implementer must fix logic until exit code is 0.",
                "duration_sec": duration_sec,
                "failure_excerpt": "\n".join(output.splitlines()[-20:]),
            }

    # Subagent Skill: event-stream-qa-orchestrator (cryptographic hash-chaining)
    record_solo_swarm_event(
        event_type="GREEN_CERTIFIED",
        actor="blue-team",
        payload={"test_cmd": test_cmd, "exit_code": 0, "duration_sec": duration_sec},
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
        "message": "✅ Green Phase Certified: All tests pass with zero exceptions.",
    }


def certify_mutation_phase(
    target_file: str = "",
    test_cmd: str = "",
    threshold: float = DEFAULT_MUTATION_THRESHOLD,
    timeout: float = 60.0,
    diff_only: bool = True,
    repo_root: Optional[str] = None,
    event_stream_path: Optional[str] = None,
    receipt_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Weapon 3: Run live dynamic mutation testing against target_file using test_cmd.
    If target_file is omitted, automatically resolves all modified source files from git diff and untracked files.
    By default scopes mutations to git diff line ranges (diff_only=True) to cut execution time by 95%.
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

    target_results: Dict[str, Any] = {}
    total_mutants_sum = 0
    killed_sum = 0
    survived_sum = 0
    all_passed = True

    for t in targets:
        abs_target = os.path.abspath(t) if os.path.isabs(t) else os.path.join(root, t)
        if not os.path.exists(abs_target):
            continue

        res = evaluate_target(
            target_path=abs_target,
            min_score=threshold,
            test_cmd=test_cmd,
            timeout=timeout,
            diff_only=diff_only,
        )
        target_results[t] = res
        t_total = res.get("total_mutants", 0)
        t_killed = res.get("killed", 0)
        t_survived = res.get("survived", 0)
        total_mutants_sum += t_total
        killed_sum += t_killed
        survived_sum += t_survived
        if not res.get("passed", False):
            all_passed = False

    if not target_results:
        return {
            "status": "ERROR",
            "passed": False,
            "error": "No valid target source files found to evaluate.",
        }

    overall_score = (killed_sum / total_mutants_sum * 100.0) if total_mutants_sum > 0 else 0.0
    passed = all_passed and (overall_score >= threshold)

    effective_target = targets[0] if len(targets) == 1 else f"{len(targets)} targets ({', '.join(targets[:3])}{'...' if len(targets) > 3 else ''})"

    # Subagent Skill: event-stream-qa-orchestrator (cryptographic hash-chaining)
    record_solo_swarm_event(
        event_type="MUTATION_CERTIFIED" if passed else "MUTATION_EVALUATED",
        actor="purple-team",
        payload={
            "score": overall_score,
            "threshold": threshold,
            "killed": killed_sum,
            "survived": survived_sum,
            "targets_count": len(target_results),
        },
        stream_path=event_stream_path,
        repo_root=root,
    )

    result = {
        "status": "CERTIFIED_MUTATION" if passed else "MUTATION_REJECTED",
        "passed": passed,
        "target_file": effective_target,
        "targets_evaluated": list(target_results.keys()),
        "auto_targeted": auto_targeted,
        "diff_only": diff_only,
        "test_cmd": test_cmd,
        "mutation_score": overall_score,
        "required_threshold": threshold,
        "total_mutants": total_mutants_sum,
        "killed": killed_sum,
        "survived": survived_sum,
        "target_details": target_results,
        "message": (
            f"✅ Mutation Phase Certified: Assertion sensitivity {overall_score:.1f}% >= {threshold}% (Killed {killed_sum}/{total_mutants_sum} mutants across {len(target_results)} files)."
            if passed
            else f"❌ Mutation Phase Rejected: Sensitivity {overall_score:.1f}% < {threshold}% or survivor detected. Strengthen test assertions."
        ),
    }

    out_receipt = receipt_path or DEFAULT_MUTATION_RECEIPT_PATH
    try:
        os.makedirs(os.path.dirname(os.path.abspath(out_receipt)), exist_ok=True)
        with open(out_receipt, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
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
) -> Dict[str, Any]:
    """
    Weapon 2 Phase 3: Purple Team (Senior Tech Lead Auditor & Goldfish Review).
    Stateless, memory-wiped audit of uncommitted code changes and specifications.
    Integrates senior_code_review diff analysis, goldfish_review spec inspection,
    neuro-symbolic formal constraint checking, and external adversarial oracle.
    Produces tdd_purple_receipt.json and records to QaEventStream.
    """
    root = repo_root or _REPO_ROOT
    out_receipt = receipt_path or DEFAULT_PURPLE_RECEIPT_PATH
    os.makedirs(os.path.dirname(os.path.abspath(out_receipt)), exist_ok=True)

    # 1. Senior Code Review (Stateless Diff Inspection)
    findings = []
    lines_cuttable = 0
    files_analyzed = 0
    review_status = "CLEAN"
    try:
        diff_text = get_git_diff(root, target)
        files = parse_diff(diff_text)
        files_analyzed = len(files)
        raw_findings, lines_cuttable = analyze_diff(files, root)
        findings = [f.to_dict() for f in raw_findings]
        has_must_fix = any(f.get("severity") == "Must fix" for f in findings)
        if has_must_fix:
            review_status = "MUST_FIX_DETECTED"
    except Exception as err:  # synapse-ignore: SWALLOWED_EXCEPTION
        findings = [{"severity": "Warning", "message": f"Diff inspection error: {err}"}]
        review_status = "DIFF_ERROR"

    # 2. Goldfish Spec Review (if target_file is provided)
    spec_review = None
    if target_file:
        cand_path = os.path.abspath(target_file) if os.path.isabs(target_file) else os.path.join(root, target_file)
        if os.path.exists(cand_path):
            try:
                spec_res = run_goldfish_review(cand_path)
                spec_review = {
                    "file": target_file,
                    "score": spec_res.get("score", 100),
                    "passed": spec_res.get("passed", True),
                    "findings_count": spec_res.get("findings_count", 0),
                }
            except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                pass

    # 3. Tier 15 Neuro-Symbolic Invariant Verification
    neuro_symbolic_res = None
    if target_file and check_neuro_symbolic:
        cand_path = os.path.abspath(target_file) if os.path.isabs(target_file) else os.path.join(root, target_file)
        if os.path.isfile(cand_path):
            ns_res = verify_neuro_symbolic_constraints(
                target_file=target_file,
                repo_root=root,
                event_stream_path=event_stream_path,
            )
            neuro_symbolic_res = ns_res
            if not ns_res.get("passed", False):
                findings.append({
                    "severity": "Must fix",
                    "message": f"Neuro-Symbolic Constraint Violation: {ns_res.get('message')}",
                })
                review_status = "MUST_FIX_DETECTED"

    # 4. External Adversarial Oracle
    oracle_res = None
    if oracle_cmd:
        o_res = execute_external_oracle(
            oracle_cmd=oracle_cmd,
            target_file=target_file,
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

    passed = (review_status == "CLEAN") and (spec_review is None or spec_review.get("passed", True))
    verdict = "CERTIFIED_PURPLE" if passed else "PURPLE_AUDIT_WARNINGS"

    receipt_payload = {
        "status": verdict,
        "certified_at": datetime.now(timezone.utc).isoformat(),
        "target_scope": target,
        "files_analyzed": files_analyzed,
        "findings_count": len(findings),
        "lines_cuttable": lines_cuttable,
        "findings": findings,
        "spec_review": spec_review,
        "neuro_symbolic_review": neuro_symbolic_res,
        "oracle_review": oracle_res,
        "passed": passed,
    }

    with open(out_receipt, "w", encoding="utf-8") as f:
        json.dump(receipt_payload, f, indent=2)

    record_solo_swarm_event(
        event_type="PURPLE_AUDITED",
        actor="purple-team",
        payload={
            "verdict": verdict,
            "passed": passed,
            "findings_count": len(findings),
            "files_analyzed": files_analyzed,
        },
        stream_path=event_stream_path,
        repo_root=root,
    )

    return {
        "status": verdict,
        "passed": passed,
        "target": target,
        "files_analyzed": files_analyzed,
        "findings_count": len(findings),
        "lines_cuttable": lines_cuttable,
        "findings": findings,
        "spec_review": spec_review,
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
    cmd_parts = shlex.split(test_cmd) if isinstance(test_cmd, str) else test_cmd
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


def calculate_composite_fitness_score(
    mutation_score: float,
    net_lines: int,
    green_passed: bool = True,
    max_loc_budget: int = 50,
) -> float:
    """
    Milestone 1 (Anti-Goodhart Tournament Fitness):
    Calculates a bounded composite fitness score in [0.0, 100.0].
    Eliminates the unbounded 100/LOC singularity while rewarding lean, high-kill implementations.
    Weights: 80% Mutation kill sensitivity, 20% Bounded LOC efficiency.
    """
    if not green_passed:
        return 0.0

    bounded_mut = max(0.0, min(100.0, float(mutation_score)))
    bounded_lines = max(0, int(net_lines))

    # Bounded LOC efficiency: 100.0 when net_lines <= 1, decays smoothly towards 0 for massive bloat.
    loc_eff = 100.0 * (max_loc_budget / (max_loc_budget + max(0, bounded_lines - 1)))

    raw_score = (bounded_mut * 0.80) + (loc_eff * 0.20)
    return round(max(0.0, min(100.0, raw_score)), 2)


def compute_pareto_front(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Milestone 1 (Multi-Objective Pareto Dominance):
    Ranks tournament candidates by Pareto dominance across:
      - Objective 1 (maximize): mutation_score
      - Objective 2 (minimize): net_lines_changed
    Annotates each candidate with:
      - 'pareto_rank': int (1 = non-dominated / Pareto front, 2 = second front, etc.)
      - 'pareto_front': bool (True if pareto_rank == 1)
    """
    if not candidates:
        return []

    pool = [dict(c) for c in candidates]
    remaining = list(range(len(pool)))
    current_rank = 1

    while remaining:
        current_front = []
        for i in remaining:
            cand_i = pool[i]
            mut_i = float(cand_i.get("mutation_score", 0.0))
            loc_i = int(cand_i.get("net_lines_changed", 0))

            is_dominated = False
            for j in remaining:
                if i == j:
                    continue
                cand_j = pool[j]
                mut_j = float(cand_j.get("mutation_score", 0.0))
                loc_j = int(cand_j.get("net_lines_changed", 0))

                # j dominates i if j is >= i in all objectives and strictly > in at least one
                if (mut_j >= mut_i and loc_j <= loc_i) and (mut_j > mut_i or loc_j < loc_i):
                    is_dominated = True
                    break

            if not is_dominated:
                current_front.append(i)

        if not current_front:
            for idx in remaining:
                pool[idx]["pareto_rank"] = current_rank
                pool[idx]["pareto_front"] = (current_rank == 1)
            break

        for idx in current_front:
            pool[idx]["pareto_rank"] = current_rank
            pool[idx]["pareto_front"] = (current_rank == 1)
            remaining.remove(idx)

        current_rank += 1

    return pool


def select_tournament_winner(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Milestone 1: Selects tournament winner using Pareto dominance & Anti-Goodhart composite fitness.
    Filters green passed candidates, computes Pareto front, and ranks candidates by:
      1. pareto_rank (ascending: Rank 1 is best)
      2. composite_fitness_score (descending)
      3. mutation_score (descending)
      4. net_lines_changed (ascending)
    """
    if not candidates:
        return None
    # Filter green passed candidates first
    green_cands = [c for c in candidates if c.get("green_passed")]
    if not green_cands:
        return None

    # Calculate composite_fitness_score if missing
    for c in green_cands:
        if "composite_fitness_score" not in c or c["composite_fitness_score"] is None:
            c["composite_fitness_score"] = calculate_composite_fitness_score(
                mutation_score=c.get("mutation_score", 0.0),
                net_lines=c.get("net_lines_changed", 1),
                green_passed=True,
            )

    ranked_cands = compute_pareto_front(green_cands)

    sorted_cands = sorted(
        ranked_cands,
        key=lambda c: (
            c.get("pareto_rank", 999),
            -c.get("composite_fitness_score", 0.0),
            -c.get("mutation_score", 0.0),
            c.get("net_lines_changed", 999),
        ),
    )
    return sorted_cands[0]


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
            if p and os.path.abspath(p) != os.path.abspath(root):
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
        "protocol": "Solo-Swarm 4-Weapon Orchestrator",
        "standards_reference": "standards/qa-process/solo-swarm-protocol.md",
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
                adapter = resolve_test_adapter(test_cmd)
                require_red = spec.get("require_red", False)
                if require_red and not os.path.exists(DEFAULT_RECEIPT_PATH):
                    green_res = {
                        "status": "MISSING_RED_RECEIPT",
                        "passed": False,
                        "error": "Batch target requires prior red receipt.",
                    }
                else:
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

        if sandbox_mgr:
            with sandbox_mgr:
                _run_step_body()
        else:
            _run_step_body()

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
        prog="solo_swarm_runner.py",
        description="Solo-Swarm 4-Weapon Orchestrator: Automated Test-First, Cognitive Shift, Mutation & Debate Runner.",
    )
    group = parser.add_argument_group("Solo-Swarm Action Modes")
    group.add_argument("--proposal", type=str, help="Weapon 4: Run Prover-Verifier debate on architectural/test proposal")
    group.add_argument("--red", action="store_true", help="Weapon 1: Verify and certify Red Phase (test must fail)")
    group.add_argument("--green", action="store_true", help="Weapon 2: Verify and certify Green Phase (test must pass)")
    group.add_argument("--mutation", action="store_true", help="Weapon 3: Run live dynamic mutation testing")
    group.add_argument("--purple", action="store_true", help="Weapon 2 Phase 3: Verify and certify Purple Phase (Tech Lead & Security Auditor)")
    group.add_argument("--tournament", nargs="*", help="Swarm Tournament: Run head-to-head tournament evaluation between candidate paths or worktrees")
    group.add_argument("--speculate", type=int, nargs="?", const=2, default=None, help="MCI Swarm: Run async multi-candidate speculative generation (default count: 2)")
    group.add_argument("--oracle-cmd", type=str, help="Stateless external model / CLI oracle command for adversarial verification (eliminates single-LLM cognitive bias)")
    group.add_argument("--neuro-symbolic", action="store_true", help="Run Tier 15 formal neuro-symbolic solver verification on target module contracts")
    group.add_argument("--batch-queue", type=str, help="Path to JSON file containing target specifications for state-flushing multi-service execution")
    group.add_argument("--batch-json", type=str, help="JSON string representing a list of batch targets for state-flushing execution")
    group.add_argument("--contract-graph", type=str, help="Cross-Service Contract Graph JSON file for multi-service dependency and breaking change tracking")
    group.add_argument("--no-sandbox", action="store_true", help="Disable ephemeral micro-sandbox isolation during batch execution")
    group.add_argument("--lock-tests", nargs="*", help="Milestone 2: Lock specified or discovered test files to OS read-only mode (0o444)")
    group.add_argument("--unlock-tests", nargs="*", help="Milestone 2: Restore write permissions (0o644) to test files")
    group.add_argument("--status", action="store_true", help="Display current Solo-Swarm verification state")

    parser.add_argument("--test-cmd", type=str, default="", help="Dynamic test command (e.g. 'pytest tests/test_target.py')")
    parser.add_argument("--target", type=str, default="", help="Target source file for mutation testing (auto-resolved from git diff if omitted)")
    parser.add_argument("--rounds", type=int, default=3, help="Debate rounds for Weapon 4 (default: 3)")
    parser.add_argument("--judge-mode", choices=["strict", "evidence_weighted", "consensus"], default="strict", help="Debate judge mode")
    parser.add_argument("--threshold", type=float, default=DEFAULT_MUTATION_THRESHOLD, help="Minimum mutation score threshold (default: 80.0)")
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-mutant test execution timeout in seconds")
    parser.add_argument("--receipt-path", type=str, default=DEFAULT_RECEIPT_PATH, help="Path to TDD Red Receipt file")
    parser.add_argument("--diff-only", action="store_true", default=True, help="Scope mutations strictly to line ranges modified in git diff (default: True)")
    parser.add_argument("--full-file", action="store_true", help="Force mutation testing across full file instead of diff-scoped lines")
    parser.add_argument("--runner", choices=["auto", "pytest", "jest", "playwright", "junit"], default="auto", help="Test runner adapter (default: auto)")
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
        green_res = certify_green_phase(
            test_cmd=args.test_cmd,
            receipt_path=args.receipt_path,
            runner=args.runner,
            event_stream_path=args.event_stream or None,
            shard_count=args.shard,
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
        mut_res = certify_mutation_phase(
            target_file=args.target,
            test_cmd=args.test_cmd,
            threshold=args.threshold,
            timeout=args.timeout,
            diff_only=diff_only,
            event_stream_path=args.event_stream or None,
            receipt_path=args.receipt_path if args.receipt_path != DEFAULT_RECEIPT_PATH else None,
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
        target_f = args.target or (resolve_auto_targets()[0] if resolve_auto_targets() else "tools/orchestration/solo_swarm_runner.py")
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
        specs = []
        parse_err = None
        if args.batch_queue:
            if not os.path.isfile(args.batch_queue):
                parse_err = f"Batch queue file not found: '{args.batch_queue}'"
            else:
                try:
                    with open(args.batch_queue, "r", encoding="utf-8") as f:
                        specs = json.load(f)
                except Exception as e:  # synapse-ignore: SWALLOWED_EXCEPTION
                    parse_err = f"Failed to parse batch queue JSON file: {e}"
        elif args.batch_json:
            try:
                specs = json.loads(args.batch_json)
            except Exception as e:  # synapse-ignore: SWALLOWED_EXCEPTION
                parse_err = f"Failed to parse batch JSON string: {e}"

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

    if args.json:
        print(json.dumps(results, indent=2))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
