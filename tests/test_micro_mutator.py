# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for tools/micro_mutator.py (Dynamic AST Micro-Mutation Sentinel & Test Impact Integration)."""

import os
import sys
import tempfile
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from micro_mutator import (
    generate_mutants_for_code,
    resolve_scoped_test_cmd,
    evaluate_target,
    evaluate_mutants_dynamically
)
from test_impact import get_impacted_test_files
from tools.lint.equivalent_mutant_filter import EquivalentMutantDetector


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
        report = evaluate_target(
            sample_file,
            min_score=80.0,
            scoped_test_cmd=f'"{sys.executable}" -B -m pytest "{sample_file}" -q --rootdir "{tmp_dir}" -p no:cacheprovider'
        )

        assert report["mode"] == "DYNAMIC_SCOPED"
        assert report["total_mutants"] >= 1
        # Mutation (+ -> -) causes add(2, 3) to equal -1 != 5, killing mutant in pytest
        assert report["killed"] >= 1, f"Expected killed >= 1, got report: {report}"
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


def test_equivalent_mutant_dead_code_detection():
    """Milestone 3: Detects mutants inside unreachable dead-code blocks as Equivalent Mutants."""
    dead_code = """
def compute_val(x: int) -> int:
    return x * 2
    y = x + 10  # Dead code!
    return y
"""
    unreachable = EquivalentMutantDetector.find_unreachable_lines(dead_code)
    # Lines 4 and 5 (after return) must be detected as dead code
    assert 4 in unreachable
    assert 5 in unreachable

    mutant = {
        "id": "MUT-EQ-1",
        "line": 4,
        "original_snippet": "y = x + 10",
        "mutated_snippet": "y = x - 10",
    }
    is_eq, reason = EquivalentMutantDetector.is_equivalent(dead_code, "", mutant)
    assert is_eq is True
    assert "dead-code" in reason.lower() or "unreachable" in reason.lower()


def test_equivalent_mutant_commutative_swap():
    """Milestone 3: Detects commutative and symmetric argument permutations as Equivalent Mutants."""
    mutant = {
        "id": "MUT-EQ-2",
        "line": 2,
        "original_snippet": "return max(a, b)",
        "mutated_snippet": "return max(b, a)",
    }
    is_eq, reason = EquivalentMutantDetector.is_equivalent("def f(a, b): return max(a, b)", "", mutant)
    assert is_eq is True
    assert "commutative" in reason.lower() or "symmetric" in reason.lower()


def test_equivalent_mutant_boolean_dpll_equivalence():
    """Milestone 3: Detects redundant boolean identities via DPLL logic as Equivalent Mutants."""
    mutant_true = {
        "id": "MUT-EQ-3",
        "line": 2,
        "original_snippet": "if active and True:",
        "mutated_snippet": "if active:",
    }
    is_eq, reason = EquivalentMutantDetector.is_equivalent("if active and True:\n    pass", "", mutant_true)
    assert is_eq is True
    assert "boolean" in reason.lower() or "dpll" in reason.lower() or "logical" in reason.lower()


def test_equivalent_mutants_excluded_from_score_denominator():
    """Milestone 3: Proven Equivalent Mutants are discarded from denominator to reflect true sensitivity."""
    dead_code = """
def run_action(flag: bool) -> bool:
    if flag:
        return True
    return False
    unreachable_var = 100
"""
    mutants = [
        # Mutant 1: Real fault injection (killed by test)
        {
            "id": "MUT-REAL",
            "line": 4,
            "original_snippet": "return True",
            "mutated_snippet": "return False",
            "mutated_code": dead_code.replace("return True", "return False"),
            "status": "SURVIVED",
        },
        # Mutant 2: Equivalent fault injection in dead code (cannot be killed)
        {
            "id": "MUT-EQUIV",
            "line": 6,
            "original_snippet": "unreachable_var = 100",
            "mutated_snippet": "unreachable_var = 200",
            "mutated_code": dead_code.replace("unreachable_var = 100", "unreachable_var = 200"),
            "status": "SURVIVED",
        },
    ]

    tmp_dir = tempfile.mkdtemp()
    try:
        sample_file = os.path.join(tmp_dir, "test_action.py")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(dead_code)

        cmd = f'"{sys.executable}" -c "import sys; sys.path.insert(0, r\'{tmp_dir}\'); import test_action; assert test_action.run_action(True) is True"'
        eval_mutants, score = evaluate_mutants_dynamically(
            sample_file, dead_code, mutants, cmd, filter_equivalent=True
        )

        eq_m = [m for m in eval_mutants if m["status"] == "EQUIVALENT"]
        assert len(eq_m) == 1
        killed_m = [m for m in eval_mutants if m["status"] == "KILLED"]
        assert len(killed_m) == 1
        # Score is 100% because 1 of 1 non-equivalent mutant was killed!
        assert score == 100.0
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_dynamic_mutation_never_touches_working_tree_file():
    """Regression (P1-8): Working-tree file must remain 100% read-only & untouched during dynamic mutation."""
    tmp_dir = tempfile.mkdtemp()
    sample_file = os.path.join(tmp_dir, "test_readonly_target.py")
    try:
        original_code = "def multiply(a, b):\n    return a * b\n\ndef test_mul():\n    assert multiply(3, 4) == 12\n"
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(original_code)

        # Lock file read-only (0o444): any in-place write attempt will raise PermissionError
        os.chmod(sample_file, 0o444)
        st_before = os.stat(sample_file)

        report = evaluate_target(
            sample_file,
            min_score=80.0,
            scoped_test_cmd=f'"{sys.executable}" -B -m pytest "{sample_file}" -q --rootdir "{tmp_dir}" -p no:cacheprovider',
        )

        st_after = os.stat(sample_file)
        assert st_after.st_mtime_ns == st_before.st_mtime_ns
        assert st_after.st_ino == st_before.st_ino
        assert not os.path.exists(sample_file + ".synapse_mutator_bak")
        assert report["killed"] >= 1
        assert report["passed"] is True
    finally:
        if os.path.exists(sample_file):
            os.chmod(sample_file, 0o644)
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_backtick_and_hash_selector_in_quotes_and_comments():
    """Regression: JS/TS backtick literals and '#' selectors are handled without false comment truncation."""
    from micro_mutator import is_inside_quotes, is_inside_comment

    line = "expect(page.locator(`#submit-btn`)).toBeVisible();"
    hash_pos = line.index("#submit-btn")
    to_be_pos = line.index("toBeVisible")
    assert is_inside_quotes(line, hash_pos) is True
    assert is_inside_comment(line, to_be_pos, file_ext=".ts") is False
    assert is_inside_comment("x = 1  # py comment", 12, file_ext=".py") is True

