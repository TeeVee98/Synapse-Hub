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
import stat
import subprocess
import sys
import unicodedata
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
    milestone_id: Optional[str] = None
    recertified_from_hmac: Optional[str] = None


@dataclass(frozen=True)
class ScopedRedReceiptDTO:
    """Milestone-scoped Red certification receipt with recertification lineage."""

    milestone_id: str
    status: str
    certified_at: str
    commit_hash: str
    normalized_cmd: str
    test_tree_hash: str
    failure_sha256: str
    ttl_seconds: int
    recertified_from_hmac: Optional[str]
    receipt_hmac: str


def resolve_red_receipt_path(
    repo_root: str,
    milestone_id: Optional[str] = None,
    explicit_path: Optional[str] = None,
    plan_slug: Optional[str] = None,
) -> str:
    """Resolves milestone- and optional plan-slug-scoped Red receipt path with legacy global fallback."""
    if explicit_path and str(explicit_path).strip():
        p = str(explicit_path).strip()
        return p if os.path.isabs(p) else os.path.join(repo_root, p)
    if milestone_id and str(milestone_id).strip():
        safe_id = re.sub(r"[^A-Za-z0-9_\-]", "_", str(milestone_id).strip())
        if plan_slug and str(plan_slug).strip():
            safe_slug = re.sub(r"[^A-Za-z0-9_\-]", "_", str(plan_slug).strip())
            return os.path.join(repo_root, "reports", "solo_receipts", f"{safe_slug}__{safe_id}_red.json")
        return os.path.join(repo_root, "reports", "solo_receipts", f"{safe_id}_red.json")
    return os.path.join(repo_root, "reports", "tdd_red_receipt.json")


def build_plan_slug(task_text: str, max_len: int = 48) -> str:
    """Normalizes task text into a collision-safe ASCII slug for .synapse/plans/<slug>.md."""
    raw = str(task_text or "").strip()
    if not raw:
        return "plan"
    raw = raw.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFKD", raw)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    if not slug:
        return "plan"
    limit = max(8, int(max_len))
    if len(slug) > limit:
        slug = slug[:limit].rstrip("-")
    return slug or "plan"


def resolve_slugged_plan_path(
    task_text: str,
    repo_root: str,
    explicit_path: Optional[str] = None,
    auto_unique: bool = True,
) -> str:
    """Resolves a collision-free plan path under .synapse/plans/<slug>.md unless explicit_path is given."""
    if explicit_path and str(explicit_path).strip() and str(explicit_path).strip().lower() != "auto":
        p = str(explicit_path).strip()
        return p if os.path.isabs(p) else os.path.join(repo_root, p)

    plans_dir = os.path.join(repo_root, ".synapse", "plans")
    slug = build_plan_slug(task_text)
    candidate = os.path.join(plans_dir, f"{slug}.md")
    if not auto_unique or not os.path.exists(candidate):
        return candidate

    counter = 2
    while True:
        numbered = os.path.join(plans_dir, f"{slug}-{counter}.md")
        if not os.path.exists(numbered):
            return numbered
        counter += 1


def resolve_active_plan_path(
    repo_root: str,
    explicit_path: Optional[str] = None,
) -> Optional[str]:
    """Resolves the active implementation plan: explicit -> SYNAPSE_ACTIVE_PLAN -> root -> latest .synapse/plans/*.md."""
    if explicit_path and str(explicit_path).strip():
        p = str(explicit_path).strip()
        cand = p if os.path.isabs(p) else os.path.join(repo_root, p)
        return cand if os.path.isfile(cand) else None

    env_plan = os.environ.get("SYNAPSE_ACTIVE_PLAN", "").strip()
    if env_plan:
        cand = env_plan if os.path.isabs(env_plan) else os.path.join(repo_root, env_plan)
        if os.path.isfile(cand):
            return cand

    root_plan = os.path.join(repo_root, "implementation_plan.md")
    if os.path.isfile(root_plan):
        return root_plan

    plans_dir = os.path.join(repo_root, ".synapse", "plans")
    if not os.path.isdir(plans_dir):
        return None
    md_files = [
        os.path.join(plans_dir, name)
        for name in os.listdir(plans_dir)
        if name.endswith(".md") and os.path.isfile(os.path.join(plans_dir, name))
    ]
    if not md_files:
        return None
    md_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return md_files[0]


def _run_git_status_porcelain(repo_root: str) -> List[str]:
    """Returns git status --porcelain lines outside .synapse/, or [] if repo_root is not a git repo."""
    if not repo_root or not os.path.isdir(repo_root):
        return []
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if res.returncode != 0:
        return []
    lines: List[str] = []
    for raw in res.stdout.splitlines():
        if not raw.strip():
            continue
        rel = raw[3:].strip().replace("\\", "/")
        if rel.startswith(".synapse/"):
            continue
        lines.append(raw)
    return lines


def inspect_workspace_concurrency(repo_root: str, task: str = "") -> Dict[str, Any]:
    """Detects concurrent plans or uncommitted edits and suggests isolated plan/worktree targets."""
    slug = build_plan_slug(task)
    suggested_abs = resolve_slugged_plan_path(task, repo_root, auto_unique=True)
    suggested_rel = os.path.relpath(suggested_abs, repo_root).replace("\\", "/")

    active_plans: List[str] = []
    if os.path.isdir(repo_root):
        root_plan = os.path.join(repo_root, "implementation_plan.md")
        if os.path.isfile(root_plan):
            active_plans.append("implementation_plan.md")
        plans_dir = os.path.join(repo_root, ".synapse", "plans")
        if os.path.isdir(plans_dir):
            for name in sorted(os.listdir(plans_dir)):
                full = os.path.join(plans_dir, name)
                if name.endswith(".md") and os.path.isfile(full):
                    active_plans.append(f".synapse/plans/{name}")

    dirty_lines = _run_git_status_porcelain(repo_root)
    is_concurrent = bool(active_plans or dirty_lines)
    return {
        "concurrency_status": "CONCURRENT_SESSION_DETECTED" if is_concurrent else "CLEAN",
        "active_plans": active_plans,
        "dirty_files_count": len(dirty_lines),
        "suggested_plan_path": suggested_rel,
        "recommended_worktree_cmd": f"agent-qa worktree create --agent-id {slug}",
    }


def _parse_positive_int(raw: Any) -> Optional[int]:
    """Parses a strictly positive integer from int or numeric text without swallowing exceptions."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw > 0 else None
    text = str(raw).strip()
    if text.startswith("+"):
        text = text[1:]
    if text.isdigit():
        val = int(text)
        return val if val > 0 else None
    return None


def resolve_red_receipt_ttl(
    ttl_seconds: Optional[int] = None,
    default_ttl: int = 900,
) -> int:
    """Resolves positive Red receipt TTL from explicit argument, env var, or default."""
    parsed = _parse_positive_int(ttl_seconds)
    if parsed is not None:
        return parsed
    parsed_env = _parse_positive_int(os.environ.get("SYNAPSE_RED_RECEIPT_TTL_SEC", ""))
    if parsed_env is not None:
        return parsed_env
    return max(1, int(default_ttl))


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


def _resolve_hmac_key_path(repo_root: Optional[str] = None) -> str:
    base_root = repo_root or _REPO_ROOT
    git_dir = os.path.join(base_root, ".git")
    if os.path.isdir(git_dir):
        return os.path.join(git_dir, "synapse_receipt_hmac.key")
    return os.path.join(os.path.expanduser("~"), ".synapse_receipt_hmac.key")


def get_receipt_hmac_key_readonly(repo_root: Optional[str] = None) -> Optional[bytes]:
    """Returns an existing HMAC signing key without writing or creating files on disk."""
    env_key = os.environ.get("SYNAPSE_RECEIPT_HMAC_KEY", "").strip()
    if env_key:
        return env_key.encode("utf-8")

    key_path = _resolve_hmac_key_path(repo_root)
    if not os.path.isfile(key_path):
        return None
    try:
        with open(key_path, "r", encoding="utf-8") as fh:
            existing = fh.read().strip()
        return existing.encode("utf-8") if existing else None
    except OSError as exc:
        sys.stderr.write(f"[solo_runner] Notice: could not read HMAC key file {key_path}: {exc}\n")
        return None


def _get_receipt_hmac_key(repo_root: Optional[str] = None) -> bytes:
    """Returns the local HMAC signing secret for Red receipts (env override or .git key file)."""
    existing = get_receipt_hmac_key_readonly(repo_root)
    if existing is not None:
        return existing

    key_path = _resolve_hmac_key_path(repo_root)
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
    canonical: Dict[str, Any] = {
        "status": payload.get("status"),
        "certified_at": payload.get("certified_at"),
        "commit_hash": payload.get("commit_hash"),
        "normalized_cmd": payload.get("normalized_cmd"),
        "executed_tests": list(payload.get("executed_tests") or []),
        "test_tree_hash": payload.get("test_tree_hash"),
        "failure_sha256": payload.get("failure_sha256"),
        "ttl_seconds": payload.get("ttl_seconds"),
    }
    if payload.get("milestone_id") is not None:
        canonical["milestone_id"] = payload.get("milestone_id")
    if payload.get("recertified_from_hmac") is not None:
        canonical["recertified_from_hmac"] = payload.get("recertified_from_hmac")
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret, raw, hashlib.sha256).hexdigest()


def _verify_red_receipt_hmac(payload: Dict[str, Any], key: Optional[bytes] = None) -> bool:
    """Verifies Red receipt HMAC using constant-time comparison."""
    actual = payload.get("receipt_hmac")
    if not isinstance(actual, str) or len(actual) != 64:
        return False
    expected = compute_red_receipt_hmac(payload, key=key)
    return hmac.compare_digest(expected, actual)


def compute_mutation_receipt_hmac(
    payload: Dict[str, Any],
    key: Optional[bytes] = None,
    repo_root: Optional[str] = None,
) -> str:
    """Computes canonical HMAC-SHA256 over security-critical mutation receipt fields."""
    secret = key if key is not None else _get_receipt_hmac_key(repo_root)
    canonical: Dict[str, Any] = {
        "status": payload.get("status"),
        "passed": bool(payload.get("passed", False)),
        "mutation_score": float(payload.get("mutation_score", 0.0) or 0.0),
        "required_threshold": float(payload.get("required_threshold", 80.0) or 80.0),
        "total_generated": int(payload.get("total_generated", payload.get("total_mutants", 0)) or 0),
        "killed": int(payload.get("killed", 0) or 0),
        "survived": int(payload.get("survived", 0) or 0),
        "targets_evaluated": sorted(str(t) for t in (payload.get("targets_evaluated") or [])),
    }
    if payload.get("milestone_id") is not None:
        canonical["milestone_id"] = payload.get("milestone_id")
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret, raw, hashlib.sha256).hexdigest()


def verify_mutation_receipt_hmac(
    payload: Dict[str, Any],
    key: Optional[bytes] = None,
    repo_root: Optional[str] = None,
) -> bool:
    """Verifies mutation receipt HMAC using constant-time comparison without creating keys on disk."""
    actual = payload.get("receipt_hmac")
    if not isinstance(actual, str) or len(actual) != 64:
        return False
    secret = key if key is not None else get_receipt_hmac_key_readonly(repo_root)
    if secret is None:
        return False
    expected = compute_mutation_receipt_hmac(payload, key=secret, repo_root=repo_root)
    return hmac.compare_digest(expected, actual)


def recertify_red_receipt_payload(
    previous_payload: Optional[Dict[str, Any]],
    new_payload: Dict[str, Any],
    key: Optional[bytes] = None,
) -> Dict[str, Any]:
    """Produces a newly signed Red receipt cryptographically chained to the prior receipt HMAC."""
    signed = dict(new_payload)
    if previous_payload is not None and previous_payload.get("receipt_hmac"):
        if not _verify_red_receipt_hmac(previous_payload, key=key):
            raise ValueError("Cannot recertify from tampered prior Red receipt (HMAC verification failed).")
        signed["recertified_from_hmac"] = str(previous_payload["receipt_hmac"])
    signed["receipt_hmac"] = compute_red_receipt_hmac(signed, key=key)
    return signed


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

    def __init__(self, flag_true_tautologies: bool = False) -> None:
        self.flag_true_tautologies = flag_true_tautologies
        self.findings: List[Tuple[int, str, str]] = []
        self.scope_constants: Dict[str, Any] = {}
        self._except_depth = 0

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

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._except_depth += 1
        try:
            self.generic_visit(node)
        finally:
            self._except_depth -= 1

    def visit_Assert(self, node: ast.Assert) -> None:
        ok, val = self._eval_constant_expr(node.test)
        if ok and not val:
            stmt_str = ast.unparse(node).strip() if hasattr(ast, "unparse") else "assert <tautology>"
            reason = f"AST Constant-Propagation: assertion evaluates statically to False ({stmt_str})"
            self.findings.append((getattr(node, "lineno", 0), stmt_str, reason))
        elif self.flag_true_tautologies and ok and val and self._except_depth == 0:
            stmt_str = ast.unparse(node).strip() if hasattr(ast, "unparse") else "assert <tautology>"
            reason = f"AST Constant-Propagation: assertion evaluates statically to True ({stmt_str})"
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
            resolved_fail_file = fail_file
            if not os.path.isfile(resolved_fail_file):
                for tok in split_cmd_portable(test_cmd):
                    cand = tok.strip('"\'')
                    if cand.endswith(".py") and os.path.isfile(cand) and os.path.basename(cand) == os.path.basename(fail_file):
                        resolved_fail_file = cand
                        break
            if os.path.isfile(resolved_fail_file):
                try:
                    with open(resolved_fail_file, "r", encoding="utf-8", errors="replace") as f:
                        file_code = f.read()
                    ast_findings = AstTautologyAnalyzer().analyze_source(file_code)
                    for finding_line, _, reason in ast_findings:
                        if abs(finding_line - fail_line) <= 2:
                            return True, f"Tautological Red Violation: {reason} at {resolved_fail_file}:{finding_line}."
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


def classify_test_failure(exit_code: int, output: str, adapter_name: str = "base") -> Tuple[str, bool, str]:
    """Classifies a failed test execution to distinguish genuine business assertion failures from environment/syntax crashes."""
    if exit_code == 0:
        return "PASS", False, "Test passed cleanly; no failure detected."

    if exit_code == 127 or "COMMAND_NOT_FOUND" in output or "command not found" in output.lower():
        return "COMMAND_NOT_FOUND", False, "Test binary or command not found on system PATH."

    if exit_code == 124 or "TIMEOUT_ERROR" in output:
        return "TIMEOUT", False, "Test execution exceeded timeout limit."

    if adapter_name == "pytest" or "pytest" in output.lower():
        if exit_code == 2:
            if "SyntaxError" in output:
                return "SYNTAX_ERROR", False, "SyntaxError in test file or imported module prevented test execution."
            if "ImportError" in output or "ModuleNotFoundError" in output:
                return "IMPORT_ERROR", False, "ImportError or missing module prevented test execution."
            return "INTERRUPTED_OR_USAGE_ERROR", False, f"Pytest exit code 2: usage or collection error: {output[:150]}"
        elif exit_code == 5:
            return "NO_TESTS_COLLECTED", False, "No tests collected by pytest."
        elif exit_code in (3, 4):
            return "INTERNAL_PYTEST_ERROR", False, f"Pytest internal or usage error (code {exit_code})."

    if "SyntaxError:" in output:
        return "SYNTAX_ERROR", False, "SyntaxError detected in test execution output."
    if "ModuleNotFoundError:" in output or "Cannot find module" in output:
        return "IMPORT_ERROR", False, "Missing dependency or module not found."

    env_markers = (
        "ECONNREFUSED", "Connection refused", "Address already in use",
        "Target closed", "browserType.launch: Executable doesn't exist",
        "Execution exception: [Errno",
    )
    if any(em.lower() in output.lower() for em in env_markers):
        return "ENVIRONMENT_ERROR", False, "Environmental infrastructure crash rather than business assertion failure."

    assertion_markers = (
        "AssertionError", "Failed: ", "expect(", "toBeVisible", "toEqual",
        "assert ", "assertFalse", "assertTrue", "assertEqual", "assertIn",
        "FAILED tests/", "FAILURE", "Expected:", "Received:",
    )
    if any(am in output for am in assertion_markers) or exit_code == 1:
        return "ASSERTION_FAILURE", True, "Genuine business assertion failure detected."

    return "UNKNOWN_FAILURE", False, f"Unclassified failure with exit code {exit_code}."


class ReadOnlyTestGuard:
    """
    DEPRECATED AS A SECURITY BOUNDARY (P0.3):
    Context manager that temporarily sets OS-level read-only permissions (0o444 / chmod a-w)
    on test files. Use WorktreeSandbox or DockerSandbox for real isolation.
    """

    DEPRECATED_SECURITY_BOUNDARY: bool = True

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


def calculate_composite_fitness_score(
    mutation_score: float,
    net_lines: int,
    green_passed: bool = True,
    max_loc_budget: int = 50,
) -> float:
    """Calculates a bounded composite fitness score in [0.0, 100.0] (80% mutation, 20% LOC efficiency)."""
    if not green_passed:
        return 0.0

    bounded_mut = max(0.0, min(100.0, float(mutation_score)))
    bounded_lines = max(0, int(net_lines))
    loc_eff = 100.0 * (max_loc_budget / (max_loc_budget + max(0, bounded_lines - 1)))
    raw_score = (bounded_mut * 0.80) + (loc_eff * 0.20)
    return round(max(0.0, min(100.0, raw_score)), 2)


def compute_pareto_front(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ranks tournament candidates by Pareto dominance (maximize mutation_score, minimize net_lines_changed)."""
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
    """Selects tournament winner using Pareto dominance and Anti-Goodhart composite fitness."""
    if not candidates:
        return None
    green_cands = [c for c in candidates if c.get("green_passed")]
    if not green_cands:
        return None

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
