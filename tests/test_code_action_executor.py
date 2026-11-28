# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""4-scenario verification suite for M3: smolagents SafeASTPythonExecutor."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.runtime.code_action_executor import (
    AUTHORIZED_IMPORTS,
    CodeActionResultDTO,
    CodeActionSession,
    OperationLimitError,
    SafeASTPythonExecutor,
    SandboxSecurityError,
)


def test_ast_sandbox_security_and_composition() -> None:
    """Positive + Security Negative scenario: safe multi-step tool composition vs sandbox escapes."""
    def fetch_scores(module: str) -> list[int]:
        return [80, 90, 100] if module == "auth" else [50, 60]

    def format_badge(name: str, avg: float) -> str:
        return f"{name}:{avg:.1f}"

    session = CodeActionSession(
        tools={"fetch_scores": fetch_scores, "format_badge": format_badge},
        max_operations=500,
        timeout_sec=2.0,
    )

    # Step 1: authorized import + tool call + loop + state persistence
    step1 = session.run_step(
        """
import math
import statistics
scores = fetch_scores("auth")
avg_val = statistics.mean(scores)
root_val = math.isqrt(int(avg_val))
print("computed", avg_val)
"""
    )
    assert isinstance(step1, CodeActionResultDTO)
    assert step1.success is True
    assert step1.final_answer is None
    assert "computed 90" in step1.stdout
    assert step1.operations_executed > 0
    assert step1.elapsed_ms >= 0.0
    assert session.state["avg_val"] == 90
    assert session.state["root_val"] == 9

    with pytest.raises(FrozenInstanceError):
        step1.success = False  # type: ignore[misc]

    # Step 2: reuse persisted state + final_answer short-circuit
    step2 = session.run_step(
        """
badge = format_badge("auth", avg_val)
final_answer(badge)
x_never_reached = 999
"""
    )
    assert step2.success is True
    assert step2.final_answer == "auth:90.0"
    assert "x_never_reached" not in session.state

    # Security Negative tests: every escape vector must fail with SandboxSecurityError or OperationLimitError
    executor = SafeASTPythonExecutor(max_operations=200, timeout_sec=1.0)

    with pytest.raises(SandboxSecurityError):
        executor.execute("().__class__.__subclasses__()")

    with pytest.raises(SandboxSecurityError):
        executor.execute("import os\nos.listdir('.')")

    with pytest.raises(SandboxSecurityError):
        executor.execute("__import__('os')")

    with pytest.raises(SandboxSecurityError):
        executor.execute("'{0.__class__}'.format(1)")

    with pytest.raises(SandboxSecurityError):
        executor.execute("open('/etc/passwd').read()")

    with pytest.raises(OperationLimitError):
        executor.execute("i = 0\nwhile True:\n    i += 1")


def test_ast_sandbox_negative_and_boundary() -> None:
    """Negative & Boundary scenarios: constructor limits, empty script, comprehensions, syntax error, op-limit edge."""
    assert "math" in AUTHORIZED_IMPORTS
    assert "os" not in AUTHORIZED_IMPORTS

    with pytest.raises(ValueError, match="max_operations"):
        SafeASTPythonExecutor(max_operations=0)
    with pytest.raises(ValueError, match="timeout_sec"):
        SafeASTPythonExecutor(timeout_sec=0.0)

    executor = SafeASTPythonExecutor(max_operations=50, timeout_sec=1.0)

    # Empty script boundary
    empty_res = executor.execute("   ")
    assert empty_res.success is True
    assert empty_res.final_answer is None
    assert empty_res.operations_executed == 0

    # List comprehension, dict/subscript, if/else, boolean ops
    comp_res = executor.execute(
        """
nums = [x * 2 for x in range(5) if x % 2 == 0]
d = {"a": nums[0], "b": nums[-1]}
res = d["b"] if len(nums) == 3 and not False else 0
final_answer(str(res))
"""
    )
    assert comp_res.success is True
    assert comp_res.final_answer == "8"

    # Syntax error returns failed DTO cleanly when strict=False or raises on execute_safe
    bad = executor.execute_safe("def broken(:\n    pass")
    assert bad.success is False
    assert bad.error_type == "SyntaxError"
    assert bad.error_message != ""

    # Forbidden underscore attribute on dict/object (including single leading underscore)
    with pytest.raises(SandboxSecurityError):
        executor.execute("x = {}\nx.__doc__")

    class _Box:
        _secret = "hidden"

    with pytest.raises(SandboxSecurityError):
        SafeASTPythonExecutor(tools={"box": lambda: _Box()}).execute("box()._secret")

    # Bounded stdout truncation and formatted f-string
    bounded = SafeASTPythonExecutor(max_output_chars=10)
    b_res = bounded.execute("print('123456')\nprint('abcdef')\nfinal_answer(f'{3.14159:.2f}')")
    assert len(b_res.stdout) == 10
    assert b_res.final_answer == "3.14"

    # Regression tests for DoS bombs (Pow, sequence Mult, range) & C-builtin module filtering
    safe_pow = executor.execute("a = 2 ** 3\nb = 2000000 ** 2\nfinal_answer(f'{a}:{b}')")
    assert safe_pow.final_answer == "8:4000000000000"
    with pytest.raises(OperationLimitError):
        executor.execute("2 ** 5000")
    with pytest.raises(OperationLimitError):
        executor.execute("2000000 ** 4")
    with pytest.raises(OperationLimitError):
        executor.execute("'a' * 200000")
    with pytest.raises(OperationLimitError):
        executor.execute("200000 * ['x']")
    with pytest.raises(OperationLimitError):
        executor.execute("range(1000000)")

    zero_mult = SafeASTPythonExecutor().execute(
        "big = ('a' * 60000) + ('b' * 60000)\nz1 = big * 0\nz2 = 0 * big\nfinal_answer(f'{len(z1)}:{len(z2)}')"
    )
    assert zero_mult.final_answer == "0:0"

    c_mod_state: dict[str, object] = {}
    c_mod_res = SafeASTPythonExecutor().execute("import itertools\nitems = list(itertools.islice([1, 2, 3], 2))", state=c_mod_state)
    assert c_mod_res.success is True
    assert "itertools" not in c_mod_state
    assert "itertools" not in c_mod_res.exported_vars
    assert c_mod_state["items"] == [1, 2]


def test_ast_sandbox_cli_json_contract() -> None:
    """CLI scenario: execute safe Python snippet via --code --json."""
    worktree_root = Path(__file__).resolve().parents[1]
    script = str(worktree_root / "tools" / "runtime" / "code_action_executor.py")
    r = subprocess.run(
        [
            sys.executable,
            script,
            "--code",
            "vals = [1, 2, 3, 4]\nfinal_answer(str(sum(vals)))",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["success"] is True
    assert data["final_answer"] == "10"
