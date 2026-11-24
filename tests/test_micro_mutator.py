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


# ==============================================================================
# Milestone 4 (P1.1 & P1.2): 4-Scenario Red Binding & Explicit Mutation Scope
# ==============================================================================

def _init_temp_git_repo(tmp_dir: str, filename: str, content: str) -> str:
    """Helper to initialize an isolated git repository with one committed source file."""
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@synapse.local"], cwd=tmp_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Synapse Tester"], cwd=tmp_dir, check=True, capture_output=True)
    file_path = os.path.join(tmp_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    subprocess.run(["git", "add", filename], cwd=tmp_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=tmp_dir, check=True, capture_output=True)
    return file_path


def test_m4_diff_only_empty_diff_emits_no_diff_mutants_without_fallback():
    """Boundary (TC-07): diff_only=True with clean git diff MUST emit NO_DIFF_MUTANTS with zero silent full-file fallback."""
    from dataclasses import FrozenInstanceError
    import pytest
    from micro_mutator import ScopedMutationReceipt

    receipt = ScopedMutationReceipt(
        target="pricing.py",
        scope_requested="diff_only",
        scope_used="diff_only",
        total_generated=0,
        killed=0,
        survived=0,
        timed_out=0,
        invalid=0,
        score_denominator=0,
        score=0.0,
        passed=False,
        mutants=[],
    )
    with pytest.raises(FrozenInstanceError):
        receipt.score = 99.0  # type: ignore[misc]

    tmp_dir = tempfile.mkdtemp()
    try:
        code = "def calc_discount(price: int) -> int:\n    if price >= 100:\n        return price - 10\n    return price\n"
        sample_file = _init_temp_git_repo(tmp_dir, "pricing.py", code)

        report = evaluate_target(sample_file, diff_only=True)
        assert report["status"] == "NO_DIFF_MUTANTS"
        assert report["scope_requested"] == "diff_only"
        assert report["scope_used"] == "diff_only"
        assert report["total_generated"] == 0
        assert report["total_mutants"] == 0
        assert report["score_denominator"] == 0
        assert report["score"] == 0.0
        assert report["mutation_score"] == 0.0
        assert report["equivalent"] == 0
        assert report["inconclusive"] == 0
        assert report["passed"] is False
        assert report["mutants"] == []

        # Explicit mutation_scope='diff_only' overrides diff_only=False
        report_scope = evaluate_target(sample_file, diff_only=False, mutation_scope="diff_only")
        assert report_scope["status"] == "NO_DIFF_MUTANTS"
        assert report_scope["scope_requested"] == "diff_only"
        assert report_scope["scope_used"] == "diff_only"
        assert report_scope["score"] == 0.0
        assert report_scope["passed"] is False

        # Real mutable line edit in diff_only mode MUST generate diff-scoped mutants (not NO_DIFF_MUTANTS)
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write("def calc_discount(price: int) -> int:\n    if price >= 200:\n        return price - 10\n    return price\n")
        report_edited = evaluate_target(sample_file, diff_only=True)
        assert report_edited["status"] in ("PASSED", "FAILED")
        assert report_edited["no_diff_mutants"] is False
        assert report_edited["scope_used"] == "diff_only"
        assert report_edited["total_generated"] >= 1
        assert report_edited["equivalent"] == 0
        assert report_edited["inconclusive"] == 0

        # Non-git directory with diff_only=True must fail closed (NO_DIFF_MUTANTS)
        non_git_dir = tempfile.mkdtemp()
        try:
            non_git_file = os.path.join(non_git_dir, "plain.py")
            with open(non_git_file, "w", encoding="utf-8") as f:
                f.write(code)
            ng_report = evaluate_target(non_git_file, diff_only=True)
            assert ng_report["status"] == "NO_DIFF_MUTANTS"
            assert ng_report["total_generated"] == 0
        finally:
            shutil.rmtree(non_git_dir, ignore_errors=True)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_m4_diff_only_comment_only_diff_emits_no_diff_mutants():
    """Boundary (TC-07): diff_only=True with comment-only edit MUST emit NO_DIFF_MUTANTS without falling back."""
    tmp_dir = tempfile.mkdtemp()
    try:
        code = "# pricing module\ndef is_valid(x: int) -> bool:\n    return x > 0\n"
        sample_file = _init_temp_git_repo(tmp_dir, "validator.py", code)

        with open(sample_file, "w", encoding="utf-8") as f:
            f.write("# pricing module updated comment only\ndef is_valid(x: int) -> bool:\n    return x > 0\n")

        report = evaluate_target(sample_file, diff_only=True)
        assert report["status"] == "NO_DIFF_MUTANTS"
        assert report["scope_requested"] == "diff_only"
        assert report["scope_used"] == "diff_only"
        assert report["total_generated"] == 0
        assert report["passed"] is False
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_m4_explicit_full_mutation_scope_and_opt_in_fallback():
    """Positive (TC-07): Explicit mutation_scope='full' and allow_full_fallback=True produce full ledger & denominator."""
    tmp_dir = tempfile.mkdtemp()
    try:
        code = "def check_limit(n: int) -> bool:\n    if n >= 5:\n        return True\n    return False\n"
        sample_file = _init_temp_git_repo(tmp_dir, "limiter.py", code)

        full_report = evaluate_target(sample_file, diff_only=True, mutation_scope="full")
        assert full_report["scope_requested"] == "full"
        assert full_report["scope_used"] == "full"
        assert full_report["total_generated"] >= 2
        assert full_report["score_denominator"] == full_report["total_generated"]
        assert full_report["equivalent"] == 0
        assert full_report["inconclusive"] == 0
        assert "invalid" in full_report
        assert "timed_out" in full_report
        assert isinstance(full_report["mutants"], list) and len(full_report["mutants"]) == full_report["total_generated"]

        # Static run with strong assertions passes in STATIC mode (kills DYNAMIC/STATIC inversion mutant)
        static_pass_file = os.path.join(tmp_dir, "test_static_pass.py")
        with open(static_pass_file, "w", encoding="utf-8") as f:
            f.write(
                "def test_check():\n"
                "    val = 10\n"
                "    if val >= 5:\n"
                "        assert val == 10\n"
            )
        static_report = evaluate_target(static_pass_file, min_score=50.0, mutation_scope="full")
        assert static_report["mode"] == "STATIC"
        assert static_report["passed"] is True
        assert static_report["status"] == "PASSED"
        assert static_report["equivalent"] == 0
        assert static_report["inconclusive"] == 0

        fb_report = evaluate_target(sample_file, diff_only=True, allow_full_fallback=True)
        assert fb_report["scope_requested"] == "diff_only"
        assert fb_report["scope_used"] == "full_fallback"
        assert fb_report["total_generated"] >= 2
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_m4_invalid_mutation_scope_raises_value_error():
    """Negative: Unsupported mutation_scope fails closed with ValueError."""
    import pytest

    tmp_dir = tempfile.mkdtemp()
    try:
        sample_file = os.path.join(tmp_dir, "mod.py")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write("def f(x):\n    return x > 1\n")
        with pytest.raises(ValueError, match="Unsupported mutation_scope"):
            evaluate_target(sample_file, mutation_scope="invalid_scope")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_m4_cli_mutation_scope_flag_and_json_receipt():
    """CLI (TC-07): micro_mutator CLI enforces --diff-only NO_DIFF_MUTANTS and honors --mutation-scope full."""
    import json
    import subprocess

    tmp_dir = tempfile.mkdtemp()
    try:
        code = "def clamp(val: int) -> int:\n    return val if val >= 0 else 0\n"
        sample_file = _init_temp_git_repo(tmp_dir, "clamp.py", code)
        script_path = os.path.join(ROOT_DIR, "tools", "lint", "micro_mutator.py")

        proc_diff = subprocess.run(
            [sys.executable, script_path, sample_file, "--diff-only", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc_diff.returncode == 1
        data_diff = json.loads(proc_diff.stdout)
        assert data_diff["status"] == "NO_DIFF_MUTANTS"
        assert data_diff["scope_used"] == "diff_only"
        assert data_diff["total_generated"] == 0

        proc_full = subprocess.run(
            [sys.executable, script_path, sample_file, "--mutation-scope", "full", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        data_full = json.loads(proc_full.stdout)
        assert data_full["scope_requested"] == "full"
        assert data_full["scope_used"] == "full"
        assert data_full["total_generated"] >= 1
        assert data_full["score_denominator"] >= 1
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_m4_red_phase_four_scenario_and_target_binding():
    """Positive & Negative (TC-06): certify_red_phase enforces 4-scenario coverage and target file relevance."""
    import json
    from tools.orchestration.solo_runner import certify_red_phase, certify_mutation_phase

    tmp_dir = tempfile.mkdtemp()
    try:
        target_mod = _init_temp_git_repo(
            tmp_dir,
            "billing_engine.py",
            "def compute_total(amount: int) -> int:\n    return amount * 2\n",
        )
        unrelated_mod = os.path.join(tmp_dir, "unrelated_util.py")
        with open(unrelated_mod, "w", encoding="utf-8") as f:
            f.write("def get_flag() -> bool:\n    return False\n")

        # 1. Negative: Missing 4-scenario coverage rejected
        incomplete_test = os.path.join(tmp_dir, "test_incomplete.py")
        with open(incomplete_test, "w", encoding="utf-8") as f:
            f.write(
                "import billing_engine\n"
                "def test_positive_total():\n"
                "    assert billing_engine.compute_total(10) == 100\n"
            )
        receipt_incomplete = os.path.join(tmp_dir, "red_incomplete.json")
        res_inc = certify_red_phase(
            test_cmd=f'"{sys.executable}" -m pytest "{incomplete_test}"',
            receipt_path=receipt_incomplete,
            cwd=tmp_dir,
            target_files=[target_mod],
            require_four_scenarios=True,
        )
        assert res_inc["status"] == "MISSING_SCENARIO_COVERAGE_REJECTED"
        assert res_inc["passed"] is False
        assert "negative" in res_inc["missing_scenarios"]
        assert "boundary" in res_inc["missing_scenarios"]
        assert "cli_or_resilience" in res_inc["missing_scenarios"]
        assert not os.path.exists(receipt_incomplete)

        # 2. Negative: Unrelated target failure rejected even with 4 scenarios
        unrelated_test = os.path.join(tmp_dir, "test_unrelated.py")
        with open(unrelated_test, "w", encoding="utf-8") as f:
            f.write(
                "import unrelated_util\n"
                "def test_positive_flag():\n"
                "    assert unrelated_util.get_flag() is True\n"
                "def test_negative_invalid_input():\n"
                "    assert unrelated_util.get_flag() is False\n"
                "def test_boundary_empty_case():\n"
                "    assert unrelated_util.get_flag() is False\n"
                "def test_cli_resilience_timeout():\n"
                "    assert unrelated_util.get_flag() is False\n"
            )
        receipt_unrelated = os.path.join(tmp_dir, "red_unrelated.json")
        res_unrel = certify_red_phase(
            test_cmd=f'"{sys.executable}" -m pytest "{unrelated_test}"',
            receipt_path=receipt_unrelated,
            cwd=tmp_dir,
            target_files=[target_mod],
            require_four_scenarios=True,
        )
        assert res_unrel["status"] == "UNRELATED_TARGET_RED_REJECTED"
        assert res_unrel["passed"] is False
        assert not os.path.exists(receipt_unrelated)

        # 3. Positive: Full 4-scenario test suite bound to target_mod passes Red certification
        complete_test = os.path.join(tmp_dir, "test_billing_complete.py")
        with open(complete_test, "w", encoding="utf-8") as f:
            f.write(
                "import billing_engine\n"
                "def test_positive_compute_total():\n"
                "    assert billing_engine.compute_total(10) == 100\n"
                "def test_negative_invalid_amount():\n"
                "    assert billing_engine.compute_total(-1) == -2\n"
                "def test_boundary_zero_amount():\n"
                "    assert billing_engine.compute_total(0) == 0\n"
                "def test_cli_json_resilience():\n"
                "    assert billing_engine.compute_total(1) == 2\n"
            )
        receipt_ok = os.path.join(tmp_dir, "red_ok.json")
        res_ok = certify_red_phase(
            test_cmd=f'"{sys.executable}" -m pytest "{complete_test}"',
            receipt_path=receipt_ok,
            cwd=tmp_dir,
            target_files=[target_mod],
            require_four_scenarios=True,
        )
        assert res_ok["status"] == "CERTIFIED_RED"
        assert res_ok["passed"] is True
        assert all(res_ok["scenario_coverage"].values())
        assert res_ok["target_binding"]["matched"] is True
        assert os.path.exists(receipt_ok)
        with open(receipt_ok, "r", encoding="utf-8") as rf:
            receipt_json = json.load(rf)
        assert all(receipt_json["scenario_coverage"].values())

        # 4. Boundary: certify_mutation_phase propagates NO_DIFF_MUTANTS without fallback
        mut_res = certify_mutation_phase(
            target_file=target_mod,
            test_cmd=f'"{sys.executable}" -m pytest "{complete_test}"',
            diff_only=True,
            repo_root=tmp_dir,
            receipt_path=os.path.join(tmp_dir, "mut_receipt.json"),
        )
        assert mut_res["status"] == "NO_DIFF_MUTANTS"
        assert mut_res["passed"] is False
        assert mut_res["scope_used"] == "diff_only"
        assert mut_res["score_denominator"] == 0
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


