#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/orchestration/solo_contracts.py — Forensic Receipt & AST Tautology Contracts
----------------------------------------------------------------------------------
Extracted from solo_runner.py to enforce modular single-responsibility boundaries:
  - SignedRedReceipt & HMAC-SHA256 signing / constant-time verification
  - MicroContextPayload & MicroContextExtractor (< 250 token AST slicing)
  - SpeculativeCandidatePrompt & split_cmd_portable
  - AstTautologyAnalyzer & detect_tautological_red (Anti-Cheat Red Verification)
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
import re
import secrets
import shlex
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)


@dataclass(frozen=True)
class SignedRedReceipt:
    status: str
    certified_at: str
    commit_hash: str
    normalized_cmd: str
    executed_tests: List[str]
    scenario_coverage: Dict[str, bool]
    test_tree_hash: str
    failure_sha256: str
    ttl_seconds: int
    receipt_hmac: str


def split_cmd_portable(cmd: Any) -> List[str]:
    """Portably tokenizes a CLI command string into an argument list."""
    if isinstance(cmd, (list, tuple)):
        return list(cmd)
    if not isinstance(cmd, str):
        return [str(cmd)]
    cmd_str = cmd.strip()
    if not cmd_str:
        return []

    norm_cmd = re.sub(
        r'([A-Za-z]:[\\/][^ \t"\'\r\n]+)',
        lambda m: m.group(1).replace("\\", "/"),
        cmd_str,
    )
    first_part = norm_cmd.split(None, 1)[0]
    if "\\" in first_part and not first_part.startswith(("-", '"', "'")):
        norm_first = first_part.replace("\\", "/")
        norm_cmd = norm_first + norm_cmd[len(first_part):]

    return shlex.split(norm_cmd)


def normalize_test_command(test_cmd: str) -> str:
    """Produces a deterministic canonical command string for strict Red/Green matching."""
    tokens = split_cmd_portable(test_cmd)
    if not tokens:
        return ""
    first_base = os.path.basename(tokens[0]).lower()
    if (
        tokens[0] == sys.executable
        or first_base in ("python", "python3", "python.exe", "python3.exe")
        or re.match(r"^python3\.\d+(\.exe)?$", first_base)
    ):
        tokens[0] = "python"
    return " ".join(tok.strip() for tok in tokens if tok.strip())


def _get_receipt_hmac_key(repo_root: Optional[str] = None) -> bytes:
    """Returns the local HMAC signing secret for Red receipts (env override or .git key file)."""
    env_key = os.environ.get("SYNAPSE_RECEIPT_HMAC_KEY", "").strip()
    if env_key:
        return env_key.encode("utf-8")

    base_root = repo_root or _REPO_ROOT
    git_dir = os.path.join(base_root, ".git")
    if os.path.isdir(git_dir):
        key_path = os.path.join(git_dir, "synapse_receipt_hmac.key")
    else:
        key_path = os.path.join(os.path.expanduser("~"), ".synapse_receipt_hmac.key")

    if os.path.isfile(key_path):
        try:
            with open(key_path, "r", encoding="utf-8") as fh:
                existing = fh.read().strip()
            if existing:
                return existing.encode("utf-8")
        except OSError as exc:
            sys.stderr.write(f"[solo_runner] Notice: could not read HMAC key file {key_path}: {exc}\n")

    generated = secrets.token_hex(32)
    tmp_path = f"{key_path}.tmp.{os.getpid()}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            fh.write(generated)
        try:
            os.chmod(tmp_path, 0o600)
        except OSError as exc:
            sys.stderr.write(f"[solo_runner] Notice: could not chmod HMAC key file {tmp_path}: {exc}\n")
        os.replace(tmp_path, key_path)
    except OSError as exc:
        sys.stderr.write(f"[solo_runner] Notice: could not persist HMAC key file {key_path}: {exc}\n")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError as rm_exc:
                sys.stderr.write(f"[solo_runner] Notice: could not remove temp HMAC key file {tmp_path}: {rm_exc}\n")
    return generated.encode("utf-8")


def compute_red_receipt_hmac(payload: Dict[str, Any], key: Optional[bytes] = None) -> str:
    """Computes canonical HMAC-SHA256 over security-critical Red receipt fields."""
    secret = key if key is not None else _get_receipt_hmac_key()
    canonical = {
        "status": payload.get("status"),
        "certified_at": payload.get("certified_at"),
        "commit_hash": payload.get("commit_hash"),
        "normalized_cmd": payload.get("normalized_cmd"),
        "executed_tests": list(payload.get("executed_tests") or []),
        "test_tree_hash": payload.get("test_tree_hash"),
        "failure_sha256": payload.get("failure_sha256"),
        "ttl_seconds": payload.get("ttl_seconds"),
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret, raw, hashlib.sha256).hexdigest()


def _verify_red_receipt_hmac(payload: Dict[str, Any], key: Optional[bytes] = None) -> bool:
    """Verifies Red receipt HMAC using constant-time comparison."""
    actual = payload.get("receipt_hmac")
    if not isinstance(actual, str) or len(actual) != 64:
        return False
    expected = compute_red_receipt_hmac(payload, key=key)
    return hmac.compare_digest(expected, actual)


def _resolve_git_head(working_dir: str) -> str:
    """Resolves git HEAD SHA in working_dir, returning 'unknown' outside a git repository."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except OSError as exc:
        sys.stderr.write(f"[solo_runner] Notice: could not resolve git HEAD in {working_dir}: {exc}\n")
    return "unknown"


def _write_json_atomic(path: str, payload: Dict[str, Any]) -> None:
    """Atomically writes a JSON payload to disk via temp file + os.replace."""
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    tmp_path = f"{abs_path}.tmp.{os.getpid()}.{secrets.token_hex(4)}"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    os.replace(tmp_path, abs_path)


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

        abs_target = (
            os.path.abspath(target_file) if os.path.isabs(target_file) else os.path.join(self.repo_root, target_file)
        )
        skeleton_info = extract_spec_micro_context(abs_target, max_tokens=max(50, max_tokens // 2))
        ast_skeleton = skeleton_info.get("skeleton", "")

        offloader = OutputOffloader(
            storage_dir=os.path.join(self.repo_root, "scratch", "offload"),
            threshold_bytes=1024,
        )
        _, _, ref = offloader.process_output(failure_trace, source_command="red_phase_failure")
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
    persona: str
    system_directive: str
    temperature: float
    max_tokens: int


class AstTautologyAnalyzer(ast.NodeVisitor):
    """Analyzes Python AST to detect tautological assertions and literal constant propagation cheats."""

    def __init__(self) -> None:
        self.findings: List[Tuple[int, str, str]] = []
        self.scope_constants: Dict[str, Any] = {}

    def _eval_constant_expr(self, node: ast.AST) -> Tuple[bool, Any]:
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
                if isinstance(node.op, ast.USub):
                    return True, -val
                if isinstance(node.op, ast.UAdd):
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
    """Returns True if expr is a literal constant with no variables or calls."""
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
    """Checks if an assertion statement is purely tautological."""
    stmt = stmt.strip()
    m_bare = re.match(r"^assert\s+(False|0|None|not\s+True)\b(?:\s*,\s*.*)?$", stmt, re.IGNORECASE)
    if m_bare:
        return True, f"Literal constant assertion: 'assert {m_bare.group(1)}'"

    m_cmp = re.match(r"^assert\s+(.+?)\s*(==|!=|<|>|<=|>=|is|is\s+not)\s*(.+?)(?:\s*,\s*.*)?$", stmt)
    if m_cmp:
        left, op, right = m_cmp.group(1).strip(), m_cmp.group(2).strip(), m_cmp.group(3).strip()
        if is_literal_constant(left) and is_literal_constant(right):
            return True, f"Literal constant comparison: 'assert {left} {op} {right}'"

    if re.match(r"^(?:pytest\.)?fail\s*\(", stmt):
        return True, "Forced failure via pytest.fail() call without domain assertion"

    try:
        ast_checker = AstTautologyAnalyzer()
        findings = ast_checker.analyze_source(stmt)
        if findings:
            return True, findings[0][2]
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

    return False, None


def detect_tautological_red(failure_output: str, test_cmd: str = "") -> Tuple[bool, Optional[str]]:
    """Analyzes failure traceback and test command to detect literal tautological failures."""
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

    if failure_output:
        m_file_line = re.search(r'([a-zA-Z0-9_\-./\\:]+\.py):(\d+):\s*AssertionError', failure_output)
        if m_file_line:
            fail_file, fail_line_s = m_file_line.group(1), m_file_line.group(2)
            fail_line = int(fail_line_s)
            if os.path.isfile(fail_file):
                try:
                    with open(fail_file, "r", encoding="utf-8", errors="replace") as f:
                        file_code = f.read()
                    ast_findings = AstTautologyAnalyzer().analyze_source(file_code)
                    for finding_line, _, reason in ast_findings:
                        if abs(finding_line - fail_line) <= 2:
                            return True, f"Tautological Red Violation: {reason} at {fail_file}:{finding_line}."
                except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                    pass

        lines = failure_output.splitlines()
        for idx, line in enumerate(lines):
            line_s = line.strip()
            if line_s.startswith(">"):
                src_stmt = line_s.lstrip(">").strip()
                is_cheat, reason = is_tautological_assertion(src_stmt)
                if is_cheat:
                    return True, f"Tautological Red Violation: {reason} in test source."
            if line_s == "AssertionError" or line_s.startswith("AssertionError:"):
                if idx > 0:
                    prev_line = lines[idx - 1].strip()
                    is_cheat, reason = is_tautological_assertion(prev_line)
                    if is_cheat:
                        return True, f"Tautological Red Violation: {reason} in traceback."

    return False, None
