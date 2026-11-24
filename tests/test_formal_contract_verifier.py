# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Tests for Formal Contract Verifier (SMT/IDL/DPLL Invariant Engine)
Validates function pre/post-conditions, symbolic bounds checking,
and deterministic counter-example extraction.
"""

import os
import sys
import tempfile

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_TESTS_DIR)
_TOOLS_DIR = os.path.join(_REPO_ROOT, "tools")
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.reasoning.formal_contract_verifier import (
    FormalContractVerifier,
    FunctionContract,
    ContractVerificationResult,
)


def test_extract_contracts_from_docstrings():
    code = '''
def withdraw(balance: int, amount: int) -> int:
    """
    Withdraw amount from balance.
    Requires: balance >= 0 and amount > 0 and balance >= amount
    Ensures: result >= 0
    Invariant: balance >= 0
    """
    return balance - amount
'''
    contracts = FormalContractVerifier.extract_contracts_from_source(code)
    assert len(contracts) == 1
    c = contracts[0]
    assert c.function_name == "withdraw"
    assert "balance >= 0" in c.requires
    assert "amount > 0" in c.requires
    assert "result >= 0" in c.ensures
    assert "balance >= 0" in c.invariants


def test_verify_valid_contract_holds():
    contract = FunctionContract(
        function_name="transfer",
        parameters=["balance", "amount"],
        requires=["balance >= 0", "amount > 0", "balance >= amount"],
        ensures=["result >= 0"],
        invariants=["result <= balance"],
    )

    # Implemented function
    def transfer(balance, amount):
        return balance - amount

    res: ContractVerificationResult = FormalContractVerifier.verify_function_contract(
        contract=contract,
        func=transfer,
    )

    assert res.is_verified is True
    assert res.counterexample is None
    assert len(res.violations) == 0
    assert 0.0 <= res.duration_ms < 1000.0


def test_extract_contracts_single_condition_only():
    # Tests that functions with ONLY Requires or ONLY Ensures are properly extracted
    code = '''
def only_req(x: int) -> int:
    """Requires: x > 0"""
    return x

def only_ens(y: int) -> int:
    """Ensures: result > 0"""
    return y + 1

def only_inv(z: int) -> int:
    """Invariant: z >= 0"""
    return z
'''
    contracts = FormalContractVerifier.extract_contracts_from_source(code)
    assert len(contracts) == 3
    names = [c.function_name for c in contracts]
    assert "only_req" in names
    assert "only_ens" in names
    assert "only_inv" in names


def test_eval_predicate_syntax_error_returns_false():
    # Division by zero or syntax error in predicate must return False
    res1 = FormalContractVerifier._eval_predicate("1 / 0 == 0", {})
    assert res1 is False

    res2 = FormalContractVerifier._eval_predicate("invalid syntax &&&", {})
    assert res2 is False


def test_verify_invalid_contract_extracts_counterexample():
    # Flawed function allows negative result when balance < amount
    contract = FunctionContract(
        function_name="flawed_withdraw",
        parameters=["balance", "amount"],
        requires=["balance >= 0", "amount > 0"],
        ensures=["result >= 0"],
        invariants=["result >= 0"],
    )

    def flawed_withdraw(balance, amount):
        return balance - amount

    res = FormalContractVerifier.verify_function_contract(
        contract=contract,
        func=flawed_withdraw,
    )

    assert res.is_verified is False
    assert res.counterexample is not None
    # Counterexample should expose balance < amount
    ce = res.counterexample
    assert "balance" in ce and "amount" in ce
    assert ce["balance"] < ce["amount"]
    assert len(res.violations) >= 1


def test_module_contract_verification_file():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write('''
def safe_deposit(balance: int, amount: int) -> int:
    """
    Requires: balance >= 0 and amount > 0
    Ensures: result > balance
    """
    return balance + amount

def flawed_transfer(balance: int, amount: int) -> int:
    """
    Requires: balance >= 0 and amount > 0
    Ensures: result >= 0
    """
    return balance - amount
''')
        tmp_file = f.name

    try:
        report = FormalContractVerifier.verify_module_contracts(tmp_file)
        assert report["total_functions"] == 2
        assert report["verified_count"] == 1
        assert report["failed_count"] == 1
        assert report["status"] == "CONTRACT_VIOLATION_DETECTED"
    finally:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)


def test_rce_predicate_escape_blocked():
    """Adversarial Red Test: dunder/subclasses sandbox escape must be rejected without eval."""
    malicious_predicates = [
        "().__class__.__base__.__subclasses__() != []",
        "__import__('os').system('echo pwned') == 0",
        "(lambda: 1)() == 1",
        "x.__class__ is int",
    ]
    for pred in malicious_predicates:
        res = FormalContractVerifier.evaluate_ast_predicate_safe(pred, {"x": 1})
        assert res.is_safe is False
        assert res.evaluated is False
        assert res.value is False
        assert FormalContractVerifier._eval_predicate(pred, {"x": 1}) is False


def test_module_verification_blocks_top_level_side_effects():
    """Adversarial Red Test: verify_module_contracts must NEVER exec() module top-level code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sentinel_file = os.path.join(tmpdir, "rce_pwned.txt")
        mod_file = os.path.join(tmpdir, "evil_mod.py")
        with open(mod_file, "w", encoding="utf-8") as f:
            f.write(
                f"import pathlib\n"
                f"pathlib.Path({sentinel_file!r}).write_text('PWNED', encoding='utf-8')\n\n"
                f"def safe_add(a: int, b: int) -> int:\n"
                f'    """\n'
                f"    Requires: a >= 0 and b >= 0\n"
                f"    Ensures: result >= a\n"
                f'    """\n'
                f"    return a + b\n"
            )

        report = FormalContractVerifier.verify_module_contracts(mod_file)
        assert not os.path.exists(sentinel_file), "CRITICAL RCE: top-level module code was executed!"
        assert report["total_functions"] == 1
        assert report["verified_count"] == 1
        assert report["status"] == "ALL_CONTRACTS_VERIFIED"


def test_zero_arg_and_three_arg_contracts():
    """Boundary Test: 0-arg functions must not pass vacuously and 3-arg functions must not TypeError."""
    # 0-arg flawed contract must be caught
    zero_contract = FunctionContract(
        function_name="bad_zero",
        parameters=[],
        requires=[],
        ensures=["result > 0"],
    )
    res_zero = FormalContractVerifier.verify_function_contract(
        contract=zero_contract,
        func=lambda: -5,
    )
    assert res_zero.is_verified is False
    assert res_zero.counterexample == {}

    # 3-arg valid contract must evaluate all 3 args without TypeError
    three_contract = FunctionContract(
        function_name="sum_three",
        parameters=["a", "b", "c"],
        requires=["a >= 0", "b >= 0", "c >= 0"],
        ensures=["result >= a"],
    )
    res_three = FormalContractVerifier.verify_function_contract(
        contract=three_contract,
        func=lambda a, b, c: a + b + c,
    )
    assert res_three.is_verified is True
    assert len(res_three.violations) == 0


def test_safe_ast_predicate_operators_and_immutability():
    """Mutation-hardening tests for UnaryOp, Pow bounds, single-sided dunders, BoolOp, and frozen DTO."""
    import dataclasses
    import pytest

    # 1. DTO immutability (frozen=True)
    dto = FormalContractVerifier.evaluate_ast_predicate_safe("x > 0", {"x": 5})
    assert dto.evaluated is True and dto.value is True and dto.is_safe is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        dto.value = False  # type: ignore[misc]

    # 2. Single-sided dunder name must still be rejected as unsafe
    res_prefix = FormalContractVerifier.evaluate_ast_predicate_safe("__secret == 1", {"__secret": 1})
    assert res_prefix.is_safe is False and res_prefix.evaluated is False
    res_suffix = FormalContractVerifier.evaluate_ast_predicate_safe("secret__ == 1", {"secret__": 1})
    assert res_suffix.is_safe is False and res_suffix.evaluated is False

    # 3. Unary operators (-, +, not) and binary Pow bounds
    assert FormalContractVerifier._eval_predicate("-x == -5", {"x": 5}) is True
    assert FormalContractVerifier._eval_predicate("not (x < 0)", {"x": 5}) is True
    assert FormalContractVerifier._eval_predicate("2 ** 3 == 8", {}) is True
    res_huge_pow = FormalContractVerifier.evaluate_ast_predicate_safe("2 ** 20 > 0", {})
    assert res_huge_pow.evaluated is False and res_huge_pow.value is False

    # 4. BoolOp (and/or), IfExp, container membership, and whitelisted pure funcs
    assert FormalContractVerifier._eval_predicate("a > 0 and b > 0", {"a": 1, "b": 2}) is True
    assert FormalContractVerifier._eval_predicate("a > 0 and b > 0", {"a": 1, "b": -1}) is False
    assert FormalContractVerifier._eval_predicate("a > 10 or b > 0", {"a": 1, "b": 2}) is True
    assert FormalContractVerifier._eval_predicate("a > 10 or b > 10", {"a": 1, "b": 2}) is False
    assert FormalContractVerifier._eval_predicate("(1 if x > 0 else -1) == 1", {"x": 3}) is True
    assert FormalContractVerifier._eval_predicate("x in [1, 2, 3] and abs(-x) == 2", {"x": 2}) is True
    assert FormalContractVerifier._eval_predicate("len((1, 2)) == 2", {}) is True
    assert FormalContractVerifier._eval_predicate("0 <= x < 10 and x in {1, 2} and x in {2: 'ok'}", {"x": 2}) is True
    assert FormalContractVerifier._eval_predicate("0 <= x < 10", {"x": 15}) is False
    # Keyword args in pure func calls & oversized AST expressions must be rejected as unsafe
    res_kw = FormalContractVerifier.evaluate_ast_predicate_safe("abs(x=-1) == 1", {})
    assert res_kw.is_safe is False and res_kw.evaluated is False
    huge_expr = " + ".join(["1"] * 40) + " > 0"
    res_huge = FormalContractVerifier.evaluate_ast_predicate_safe(huge_expr, {})
    assert res_huge.is_safe is False and res_huge.evaluated is False

    # 5. Verify HAS_Z3 matches actual environment probe & unknown variable returns evaluated=False, is_safe=True
    import importlib.util
    from tools.reasoning import formal_contract_verifier as fcv
    assert fcv.HAS_Z3 is (importlib.util.find_spec("z3") is not None)
    res_missing = FormalContractVerifier.evaluate_ast_predicate_safe("missing_var > 0", {})
    assert res_missing.evaluated is False and res_missing.is_safe is True
    # False-branch IfExp
    assert FormalContractVerifier._eval_predicate("(1 if x > 0 else -1) == -1", {"x": -2}) is True
