# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""Unit tests for tools/micro_mutator.py (Dynamic AST Micro-Mutation Sentinel & Test Impact Integration)."""

import os
import sys
import tempfile
import shutil
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from micro_mutator import (
    generate_mutants_for_code,
    evaluate_mutants_statically,
    resolve_scoped_test_cmd,
    evaluate_target,
    evaluate_mutants_dynamically
)
from test_impact import get_impacted_test_files


def test_syntactic_mutant_generation_operators():
    code = """
def check_status(is_active: bool, count: int) -> bool:
    if is_active == True and count >= 10:
        return True
    return False
"""
    mutants = generate_mutants_for_code(code, file_path="sample.py")
    descriptions = [m["description"] for m in mutants]

    # Verify key mutation operator families
    assert any("Equality Inversion" in d for d in descriptions)
    assert any("Relational Inversion" in d or "Boundary Shift" in d for d in descriptions)
    assert any("Boolean Inversion" in d or "Return Value Inversion" in d for d in descriptions)


def test_action_statement_deletion_mutant():
    code = """
def test_login(page):
    page.click('#login-btn')
    page.fill('#user', 'admin')
    assert page.isVisible('#dashboard')
"""
    mutants = generate_mutants_for_code(code, file_path="test_ui.py")
    descriptions = [m["description"] for m in mutants]
    assert any("Statement Deletion" in d for d in descriptions)


def test_resolve_scoped_test_cmd_templates():
    # Test with {test_files} placeholder
    cmd1, impacted1 = resolve_scoped_test_cmd("pytest {test_files} -v", "tests/test_fsm_enforcer.py", repo_root=ROOT_DIR)
    assert "pytest" in cmd1
    assert "tests/test_fsm_enforcer.py" in cmd1
    assert "-v" in cmd1
    assert "tests/test_fsm_enforcer.py" in impacted1

    # Test with {tests} placeholder
    cmd2, impacted2 = resolve_scoped_test_cmd("npm test -- {tests}", "tests/test_fsm_enforcer.py", repo_root=ROOT_DIR)
    assert "npm test --" in cmd2
    assert "tests/test_fsm_enforcer.py" in cmd2

    # Test with default append behavior
    cmd3, impacted3 = resolve_scoped_test_cmd("pytest -q", "tests/test_fsm_enforcer.py", repo_root=ROOT_DIR)
    assert cmd3.startswith("pytest -q")
    assert "tests/test_fsm_enforcer.py" in cmd3


def test_get_impacted_test_files_direct_test():
    impacted = get_impacted_test_files(["tests/test_fsm_enforcer.py"], repo_root=ROOT_DIR)
    assert len(impacted) >= 1
    assert "tests/test_fsm_enforcer.py" in impacted


def test_dynamic_mutation_execution_and_clean_restoration():
    """Verifies that dynamic mutant evaluation executes runner, kills mutant, and restores code intact."""
    tmp_dir = tempfile.mkdtemp()
    try:
        sample_file = os.path.join(tmp_dir, "test_sample.py")
        original_code = """
def add(a, b):
    return a + b

def test_add():
    assert add(2, 3) == 5
"""
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(original_code)

        # Run dynamic evaluation with scoped test command
        cache_dir = os.path.join(tmp_dir, ".pytest_cache")
        report = evaluate_target(
            sample_file,
            min_score=80.0,
            scoped_test_cmd=f'"{sys.executable}" -m pytest "{sample_file}" -q -o cache_dir="{cache_dir}" -o rootdir="{tmp_dir}" -p no:cacheprovider'
        )

        assert report["mode"] == "DYNAMIC_SCOPED"
        assert report["total_mutants"] >= 1
        # Mutation (+ -> -) causes add(2, 3) to equal -1 != 5, killing mutant in pytest
        assert report["killed"] >= 1
        assert report["runtime_mutation_kill_score"] >= 80.0
        assert report["passed"] is True

        # Verify disk file is 100% restored to original pristine code
        with open(sample_file, "r", encoding="utf-8") as f:
            restored_code = f.read()
        assert restored_code == original_code

        # Verify backup file was cleaned up
        assert not os.path.exists(sample_file + ".synapse_mutator_bak")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_dynamic_mutation_zero_impact_fast_path():
    """Verifies that scoped_test_cmd with zero impacted tests marks mutants survived without wasting test runs."""
    tmp_dir = tempfile.mkdtemp()
    try:
        sample_file = os.path.join(tmp_dir, "standalone_util.py")
        code = "def is_positive(x: int) -> bool:\n    return x > 0\n"
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(code)

        report = evaluate_target(
            sample_file,
            scoped_test_cmd="pytest {test_files} -q"
        )
        assert report["mode"] == "DYNAMIC_SCOPED"
        assert report["total_mutants"] >= 1
        assert report["killed"] == 0
        assert report["survived"] == report["total_mutants"]
        assert report["mutation_score"] == 0.0
        assert all("No impacted test cases identified" in m.get("reason", "") for m in report["mutants"])
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_invalid_syntax_mutants_discarded_from_score():
    """Verifies that mutants producing invalid Python syntax are excluded from the score denominator."""
    mutants = [
        {"id": "MUT-1", "mutated_code": "def valid(): return False\n", "status": "SURVIVED"},
        {"id": "MUT-2", "mutated_code": "def invalid(: return", "status": "SURVIVED"}
    ]
    # Dynamic evaluation on sample
    tmp_dir = tempfile.mkdtemp()
    try:
        sample_file = os.path.join(tmp_dir, "test_foo.py")
        original = "def valid(): return True\n"
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(original)

        cmd = f'"{sys.executable}" -c "import sys; sys.path.insert(0, r\'{tmp_dir}\'); import test_foo; assert test_foo.valid() is True"'
        eval_mutants, score = evaluate_mutants_dynamically(
            sample_file, original, mutants, cmd
        )
        # MUT-2 should be marked INVALID_SYNTAX
        invalid_m = [m for m in eval_mutants if m["status"] == "INVALID_SYNTAX"]
        assert len(invalid_m) == 1
        # MUT-1 was killed by failing assertion (valid() == False)
        killed_m = [m for m in eval_mutants if m["status"] == "KILLED"]
        assert len(killed_m) == 1
        # Score is 100% because 1 of 1 valid mutant was killed (invalid was discarded)
        assert score == 100.0
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

