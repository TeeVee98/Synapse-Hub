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
