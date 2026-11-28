#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""smolagents-inspired Safe AST Code-as-Action Local Python Executor.

Interprets a strict allowlisted subset of Python AST nodes (zero raw eval/exec),
blocks all dunder/private attribute access and format-string escapes, enforces
authorized imports, operation caps, and wall-clock timeouts, and supports
stateful multi-step CodeActionSession with injected Hub tool callables.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass, field
import importlib
import json
import operator
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

AUTHORIZED_IMPORTS: Tuple[str, ...] = (
    "math",
    "json",
    "re",
    "statistics",
    "datetime",
    "collections",
    "itertools",
)

FORBIDDEN_ATTRS: Tuple[str, ...] = ("format", "format_map")

_BIN_OPS: Dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS: Dict[type, Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Not: operator.not_,
}

_CMP_OPS: Dict[type, Callable[[Any, Any], bool]] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
}


class SandboxSecurityError(RuntimeError):
    """Raised when a code-action snippet attempts a forbidden operation or escape."""


class OperationLimitError(RuntimeError):
    """Raised when execution exceeds max_operations or wall-clock timeout."""


class _FinalAnswerSignal(Exception):
    def __init__(self, value: Any) -> None:
        super().__init__("final_answer")
        self.value = value


class _BreakSignal(Exception):
    pass


class _ContinueSignal(Exception):
    pass


@dataclass(frozen=True)
class CodeActionResultDTO:
    success: bool
    final_answer: Optional[str]
    stdout: str
    operations_executed: int
    elapsed_ms: float
    exported_vars: Dict[str, str] = field(default_factory=dict)
    error_type: Optional[str] = None
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SafeASTPythonExecutor:
    """Zero-eval AST allowlist interpreter for safe Code-as-Action execution."""

    def __init__(
        self,
        tools: Optional[Dict[str, Callable[..., Any]]] = None,
        authorized_imports: Sequence[str] = AUTHORIZED_IMPORTS,
        max_operations: int = 10000,
        timeout_sec: float = 2.0,
        max_output_chars: int = 8192,
    ) -> None:
        if max_operations <= 0:
            raise ValueError("max_operations must be positive.")
        if timeout_sec <= 0.0:
            raise ValueError("timeout_sec must be positive.")
        self.tools = dict(tools or {})
        self.authorized_imports = set(authorized_imports)
        self.max_operations = int(max_operations)
        self.timeout_sec = float(timeout_sec)
        self.max_output_chars = int(max_output_chars)

    def _safe_getattr(self, obj: Any, attr: str) -> Any:
        if attr.startswith("_") or attr.endswith("_") or attr in FORBIDDEN_ATTRS:
            raise SandboxSecurityError(f"Access to forbidden attribute '{attr}' is blocked.")
        return getattr(obj, attr)

    def _build_env(
        self,
        state: Dict[str, Any],
        stdout_buf: List[str],
    ) -> Dict[str, Any]:
        def _safe_print(*args: Any, **kwargs: Any) -> None:
            sep = str(kwargs.get("sep", " "))
            end = str(kwargs.get("end", "\n"))
            chunk = sep.join(str(a) for a in args) + end
            current_len = sum(len(s) for s in stdout_buf)
            if current_len < self.max_output_chars:
                stdout_buf.append(chunk[: self.max_output_chars - current_len])

        def _final_answer(val: Any) -> None:
            raise _FinalAnswerSignal(val)

        builtins_map: Dict[str, Any] = {
            "len": len,
            "sum": sum,
            "min": min,
            "max": max,
            "sorted": sorted,
            "range": range,
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "abs": abs,
            "round": round,
            "enumerate": enumerate,
            "zip": zip,
            "any": any,
            "all": all,
            "print": _safe_print,
            "final_answer": _final_answer,
        }
        env: Dict[str, Any] = {}
        env.update(builtins_map)
        env.update(self.tools)
        env.update(state)
        return env

    def _eval(
        self,
        node: ast.AST,
        env: Dict[str, Any],
        counter: List[int],
        deadline: float,
    ) -> Any:
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            if node.id.startswith("_"):
                raise SandboxSecurityError(f"Access to private/dunder name '{node.id}' is blocked.")
            if node.id not in env:
                raise SandboxSecurityError(f"Name '{node.id}' is not defined or not permitted.")
            return env[node.id]

        counter[0] += 1
        if counter[0] > self.max_operations:
            raise OperationLimitError(f"Exceeded max_operations ({self.max_operations}).")
        if time.monotonic() > deadline:
            raise OperationLimitError(f"Exceeded timeout_sec ({self.timeout_sec}s).")

        if isinstance(node, ast.List):
            return [self._eval(elt, env, counter, deadline) for elt in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self._eval(elt, env, counter, deadline) for elt in node.elts)

        if isinstance(node, ast.Set):
            return {self._eval(elt, env, counter, deadline) for elt in node.elts}

        if isinstance(node, ast.Dict):
            return {
                self._eval(k, env, counter, deadline): self._eval(v, env, counter, deadline)
                for k, v in zip(node.keys, node.values)
                if k is not None
            }

        if isinstance(node, ast.JoinedStr):
            return "".join(str(self._eval(val, env, counter, deadline)) for val in node.values)

        if isinstance(node, ast.FormattedValue):
            val = self._eval(node.value, env, counter, deadline)
            if node.format_spec is not None:
                spec = str(self._eval(node.format_spec, env, counter, deadline))
                return format(val, spec)
            return str(val)

        if isinstance(node, ast.BinOp):
            op_fn = _BIN_OPS.get(type(node.op))
            if op_fn is None:
                raise SandboxSecurityError(f"Binary operator '{type(node.op).__name__}' is not allowed.")
            return op_fn(
                self._eval(node.left, env, counter, deadline),
                self._eval(node.right, env, counter, deadline),
            )

        if isinstance(node, ast.UnaryOp):
            op_fn = _UNARY_OPS.get(type(node.op))
            if op_fn is None:
                raise SandboxSecurityError(f"Unary operator '{type(node.op).__name__}' is not allowed.")
            return op_fn(self._eval(node.operand, env, counter, deadline))

        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                res: Any = True
                for val_node in node.values:
                    res = self._eval(val_node, env, counter, deadline)
                    if not res:
                        return res
                return res
            if isinstance(node.op, ast.Or):
                res = False
                for val_node in node.values:
                    res = self._eval(val_node, env, counter, deadline)
                    if res:
                        return res
                return res
            raise SandboxSecurityError(f"Boolean operator '{type(node.op).__name__}' is not allowed.")

        if isinstance(node, ast.Compare):
            left = self._eval(node.left, env, counter, deadline)
            for op, comp in zip(node.ops, node.comparators):
                op_fn = _CMP_OPS.get(type(op))
                if op_fn is None:
                    raise SandboxSecurityError(f"Comparison operator '{type(op).__name__}' is not allowed.")
                right = self._eval(comp, env, counter, deadline)
                if not op_fn(left, right):
                    return False
                left = right
            return True

        if isinstance(node, ast.IfExp):
            cond = self._eval(node.test, env, counter, deadline)
            return self._eval(node.body if cond else node.orelse, env, counter, deadline)

        if isinstance(node, ast.Subscript):
            target = self._eval(node.value, env, counter, deadline)
            if isinstance(node.slice, ast.Slice):
                low = self._eval(node.slice.lower, env, counter, deadline) if node.slice.lower else None
                up = self._eval(node.slice.upper, env, counter, deadline) if node.slice.upper else None
                step = self._eval(node.slice.step, env, counter, deadline) if node.slice.step else None
                return target[slice(low, up, step)]
            key = self._eval(node.slice, env, counter, deadline)
            return target[key]

        if isinstance(node, ast.Attribute):
            obj = self._eval(node.value, env, counter, deadline)
            return self._safe_getattr(obj, node.attr)

        if isinstance(node, ast.Call):
            fn = self._eval(node.func, env, counter, deadline)
            if not callable(fn):
                raise SandboxSecurityError("Attempted to invoke non-callable object.")
            args = [self._eval(a, env, counter, deadline) for a in node.args]
            kwargs = {kw.arg: self._eval(kw.value, env, counter, deadline) for kw in node.keywords if kw.arg}
            return fn(*args, **kwargs)

        if isinstance(node, ast.ListComp):
            return self._eval_listcomp(node, env, counter, deadline)

        raise SandboxSecurityError(f"AST expression '{type(node).__name__}' is not permitted in sandbox.")

    def _eval_listcomp(
        self,
        node: ast.ListComp,
        env: Dict[str, Any],
        counter: List[int],
        deadline: float,
    ) -> List[Any]:
        results: List[Any] = []

        def _recurse(gen_idx: int, local_env: Dict[str, Any]) -> None:
            if gen_idx == len(node.generators):
                results.append(self._eval(node.elt, local_env, counter, deadline))
                return
            gen = node.generators[gen_idx]
            iterable = self._eval(gen.iter, local_env, counter, deadline)
            for item in iterable:
                step_env = dict(local_env)
                self._assign_target(gen.target, item, step_env)
                if all(self._eval(cond, step_env, counter, deadline) for cond in gen.ifs):
                    _recurse(gen_idx + 1, step_env)

        _recurse(0, env)
        return results

    def _assign_target(self, target: ast.AST, value: Any, env: Dict[str, Any]) -> None:
        if isinstance(target, ast.Name):
            if target.id.startswith("_"):
                raise SandboxSecurityError(f"Cannot assign to private/dunder name '{target.id}'.")
            env[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)):
            vals = list(value)
            if len(vals) != len(target.elts):
                raise ValueError("Unpacking length mismatch.")
            for t_elt, v_elt in zip(target.elts, vals):
                self._assign_target(t_elt, v_elt, env)
        else:
            raise SandboxSecurityError(f"Unsupported assignment target '{type(target).__name__}'.")

    def _exec_stmt(
        self,
        stmt: ast.stmt,
        env: Dict[str, Any],
        counter: List[int],
        deadline: float,
    ) -> None:
        counter[0] += 1
        if counter[0] > self.max_operations:
            raise OperationLimitError(f"Exceeded max_operations ({self.max_operations}).")
        if time.monotonic() > deadline:
            raise OperationLimitError(f"Exceeded timeout_sec ({self.timeout_sec}s).")

        if isinstance(stmt, ast.Pass):
            return
        if isinstance(stmt, ast.Break):
            raise _BreakSignal()
        if isinstance(stmt, ast.Continue):
            raise _ContinueSignal()
        if isinstance(stmt, ast.Expr):
            self._eval(stmt.value, env, counter, deadline)
            return
        if isinstance(stmt, ast.Assign):
            val = self._eval(stmt.value, env, counter, deadline)
            for target in stmt.targets:
                self._assign_target(target, val, env)
            return
        if isinstance(stmt, ast.AugAssign):
            if not isinstance(stmt.target, ast.Name):
                raise SandboxSecurityError("Augmented assignment only supported on variable names.")
            cur = self._eval(stmt.target, env, counter, deadline)
            rhs = self._eval(stmt.value, env, counter, deadline)
            op_fn = _BIN_OPS.get(type(stmt.op))
            if op_fn is None:
                raise SandboxSecurityError(f"Unsupported augmented operator '{type(stmt.op).__name__}'.")
            self._assign_target(stmt.target, op_fn(cur, rhs), env)
            return
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                root_mod = alias.name.split(".")[0]
                if root_mod not in self.authorized_imports:
                    raise SandboxSecurityError(f"Import of unauthorized module '{alias.name}' is blocked.")
                mod = importlib.import_module(alias.name)
                env[alias.asname or root_mod] = mod
            return
        if isinstance(stmt, ast.ImportFrom):
            root_mod = (stmt.module or "").split(".")[0]
            if root_mod not in self.authorized_imports:
                raise SandboxSecurityError(f"Import from unauthorized module '{stmt.module}' is blocked.")
            mod = importlib.import_module(stmt.module or "")
            for alias in stmt.names:
                if alias.name == "*" or alias.name.startswith("_"):
                    raise SandboxSecurityError(f"Forbidden from-import symbol '{alias.name}'.")
                env[alias.asname or alias.name] = self._safe_getattr(mod, alias.name)
            return
        if isinstance(stmt, ast.If):
            branch = stmt.body if self._eval(stmt.test, env, counter, deadline) else stmt.orelse
            for sub in branch:
                self._exec_stmt(sub, env, counter, deadline)
            return
        if isinstance(stmt, ast.For):
            iterable = self._eval(stmt.iter, env, counter, deadline)
            for item in iterable:
                self._assign_target(stmt.target, item, env)
                try:
                    for sub in stmt.body:
                        self._exec_stmt(sub, env, counter, deadline)
                except _ContinueSignal:
                    continue
                except _BreakSignal:
                    break
            return
        if isinstance(stmt, ast.While):
            while self._eval(stmt.test, env, counter, deadline):
                try:
                    for sub in stmt.body:
                        self._exec_stmt(sub, env, counter, deadline)
                except _ContinueSignal:
                    continue
                except _BreakSignal:
                    break
            return

        raise SandboxSecurityError(f"AST statement '{type(stmt).__name__}' is not permitted in sandbox.")

    def execute(self, code: str, state: Optional[Dict[str, Any]] = None) -> CodeActionResultDTO:
        """Executes Python code in the AST sandbox; raises SandboxSecurityError / OperationLimitError on violations."""
        t0 = time.monotonic()
        if not isinstance(code, str) or not code.strip():
            return CodeActionResultDTO(
                success=True,
                final_answer=None,
                stdout="",
                operations_executed=0,
                elapsed_ms=0.0,
                exported_vars={},
            )

        tree = ast.parse(code)
        stdout_buf: List[str] = []
        session_state = state if state is not None else {}
        env = self._build_env(session_state, stdout_buf)
        initial_keys = set(env.keys()) - set(session_state.keys())
        counter = [0]
        deadline = t0 + self.timeout_sec
        final_ans: Optional[str] = None

        try:
            for stmt in tree.body:
                self._exec_stmt(stmt, env, counter, deadline)
        except _FinalAnswerSignal as sig:
            final_ans = None if sig.value is None else str(sig.value)

        exported: Dict[str, str] = {}
        for k, v in env.items():
            if k not in initial_keys and not callable(v) and not hasattr(v, "__file__"):
                session_state[k] = v
                exported[k] = repr(v)[:200]

        elapsed_ms = round((time.monotonic() - t0) * 1000.0, 3)
        return CodeActionResultDTO(
            success=True,
            final_answer=final_ans,
            stdout="".join(stdout_buf),
            operations_executed=counter[0],
            elapsed_ms=elapsed_ms,
            exported_vars=exported,
        )

    def execute_safe(self, code: str, state: Optional[Dict[str, Any]] = None) -> CodeActionResultDTO:
        """Executes code and captures exceptions into a failed CodeActionResultDTO instead of raising."""
        t0 = time.monotonic()
        try:
            return self.execute(code, state=state)
        except Exception as exc:
            return CodeActionResultDTO(
                success=False,
                final_answer=None,
                stdout="",
                operations_executed=0,
                elapsed_ms=round((time.monotonic() - t0) * 1000.0, 3),
                exported_vars={},
                error_type=type(exc).__name__,
                error_message=str(exc),
            )


class CodeActionSession:
    """Stateful multi-step CodeAgent session preserving variables across code steps."""

    def __init__(
        self,
        tools: Optional[Dict[str, Callable[..., Any]]] = None,
        authorized_imports: Sequence[str] = AUTHORIZED_IMPORTS,
        max_operations: int = 10000,
        timeout_sec: float = 2.0,
    ) -> None:
        self.executor = SafeASTPythonExecutor(
            tools=tools,
            authorized_imports=authorized_imports,
            max_operations=max_operations,
            timeout_sec=timeout_sec,
        )
        self.state: Dict[str, Any] = {}

    def run_step(self, code: str) -> CodeActionResultDTO:
        return self.executor.execute(code, state=self.state)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Synapse Hub Safe AST Code-as-Action Python Executor")
    parser.add_argument("--code", required=True, help="Python code snippet to run in AST sandbox")
    parser.add_argument("--max-ops", type=int, default=10000)
    parser.add_argument("--timeout-sec", type=float, default=2.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    executor = SafeASTPythonExecutor(max_operations=args.max_ops, timeout_sec=args.timeout_sec)
    res = executor.execute_safe(args.code)
    if args.json:
        print(json.dumps(res.to_dict(), indent=2))
    else:
        print(res.to_dict())
    return 0 if res.success else 1


if __name__ == "__main__":
    sys.exit(main())
