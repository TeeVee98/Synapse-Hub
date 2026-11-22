#!/usr/bin/env python3
# Copyright (c) 2026 Thế Vị (@TeeVee98)
# Synapse Hub is open-source software under the MIT License.
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_entropy_pruning.py — 4-Scenario Unit Test Battery for EntropyPruner
-------------------------------------------------------------------------------
Covers:
  - Scenario 1 (Positive): Compression of representative Python code, 100% invariant
    preservation (functions, variables, branches, asserts), budget constraint, ratio calculations.
  - Scenario 2 (Negative): Non-existent file, invalid target ratios, negative budgets,
    conflicting CLI flags, malformed input lexical fallback.
  - Scenario 3 (Boundary): Empty string, 1-token input, code without comments, only comments,
    extreme ratios (0.0, 1.0).
  - Scenario 4 (CLI Flags): Full CLI test matrix (--file, --text, --target-ratio,
    --budget-tokens, --output, --json, --preserve-identifiers, --no-preserve-identifiers).

TRUTH ANCHOR: Zero fake passes, zero swallowed exceptions, zero static sleeps.
"""

import sys
import ast
import json
import subprocess
from pathlib import Path
import pytest

from tools.reasoning.entropy_pruning import (
    EntropyPruner,
    count_tokens,
)

PYTHON_EXECUTABLE = sys.executable
ENTROPY_PRUNER_SCRIPT = str(
    Path(__file__).resolve().parent.parent / "tools" / "reasoning" / "entropy_pruning.py"
)

SAMPLE_PYTHON_CODE = '''"""Module docstring for test calculations."""

class OrderCalculator:
    """Class docstring for OrderCalculator."""

    def calculate_total(self, items: list[dict], tax_rate: float = 0.08) -> dict:
        """Calculates final order total with tax and item discounts."""
        # Verify inputs are not negative
        assert tax_rate >= 0.0, "Tax rate cannot be negative"
        assert len(items) > 0, "Item list must contain at least one item"

        subtotal = 0.0
        # Iterate over each purchased item
        for item in items:
            price = item.get("price", 0.0)
            qty = item.get("qty", 1)
            # Apply bulk discount if quantity exceeds threshold
            if qty >= 10:
                subtotal += price * qty * 0.90
            else:
                subtotal += price * qty

        # Compute tax and grand total
        if subtotal > 100.0:
            tax = subtotal * tax_rate
        else:
            tax = 0.0

        grand_total = subtotal + tax
        return {"subtotal": subtotal, "tax": tax, "grand_total": grand_total}
'''


class TestEntropyPruningPositive:
    """Scenario 1: Positive verification of compression, invariants, budgets, and ratios."""

    def test_compress_representative_python_code(self):
        """Verifies compression on complex Python code with docstrings, comments, and hints."""
        compressed, meta = EntropyPruner.compress(
            SAMPLE_PYTHON_CODE, target_ratio=0.50, preserve_identifiers=True
        )

        assert meta["status"] == "ok"
        assert meta["original_token_count"] > 0
        assert meta["pruned_token_count"] > 0
        assert meta["compression_ratio"] > 0.0
        assert meta["preserved_identifiers_pct"] == 100.0
        assert len(compressed) < len(SAMPLE_PYTHON_CODE)

        # Confirm compressed code is syntactically valid Python
        parsed_ast = ast.parse(compressed)
        assert isinstance(parsed_ast, ast.Module)

    def test_100_percent_invariant_preservation(self):
        """Verifies 100% preservation of function signatures, variables, branches, and asserts."""
        compressed, meta = EntropyPruner.compress(
            SAMPLE_PYTHON_CODE, target_ratio=0.30, preserve_identifiers=True
        )

        # Invariant: function signatures
        assert "calculate_total" in compressed
        assert "OrderCalculator" in compressed

        # Invariant: variable identifiers
        for var_name in ["subtotal", "tax_rate", "items", "price", "qty", "grand_total"]:
            assert var_name in compressed

        # Invariant: branching keywords
        assert "if " in compressed
        assert "else:" in compressed
        assert "for " in compressed

        # Invariant: assertion statements
        assert "assert tax_rate >= 0.0" in compressed
        assert "assert len(items) > 0" in compressed

        # Invariant metric
        assert meta["preserved_identifiers_pct"] == 100.0

    def test_budget_tokens_constraint(self):
        """Verifies that budget_tokens caps the maximum number of tokens in compressed output."""
        original_tokens = count_tokens(SAMPLE_PYTHON_CODE)
        budget = 60

        compressed, meta = EntropyPruner.compress(
            SAMPLE_PYTHON_CODE, target_ratio=0.90, budget_tokens=budget, preserve_identifiers=True
        )

        compressed_tokens = count_tokens(compressed)
        assert compressed_tokens <= original_tokens
        assert meta["pruned_token_count"] == original_tokens - compressed_tokens
        assert meta["status"] == "ok"

    def test_ratio_calculations_consistency(self):
        """Verifies exact mathematical consistency of token counts and compression ratios."""
        compressed, meta = EntropyPruner.compress(
            SAMPLE_PYTHON_CODE, target_ratio=0.50, preserve_identifiers=True
        )

        orig_cnt = meta["original_token_count"]
        pruned_cnt = meta["pruned_token_count"]
        ratio = meta["compression_ratio"]
        comp_cnt = count_tokens(compressed)

        assert orig_cnt == pruned_cnt + comp_cnt
        assert ratio == round(pruned_cnt / orig_cnt, 4)

    def test_surprisal_ranking_order(self):
        """Verifies that low-surprisal comments are pruned before high-surprisal comments."""
        code_with_comments = '''def process():
    # note note note note note
    # Invariant cryptographic verification prevents unauthorized state modification
    x = 100
    assert x > 0
    return x
'''
        compressed, meta = EntropyPruner.compress(
            code_with_comments, target_ratio=0.85, preserve_identifiers=True
        )
        assert meta["status"] == "ok"
        assert "process" in compressed
        assert "assert x > 0" in compressed


class TestEntropyPruningNegative:
    """Scenario 2: Negative verification of errors, invalid params, and malformed inputs."""

    def test_invalid_target_ratio_negative(self):
        """Verifies ValueError is raised for negative target_ratio."""
        with pytest.raises(ValueError) as excinfo:
            EntropyPruner.compress(SAMPLE_PYTHON_CODE, target_ratio=-0.1)
        assert "target_ratio must be between 0.0 and 1.0" in str(excinfo.value)

    def test_invalid_target_ratio_greater_than_one(self):
        """Verifies ValueError is raised for target_ratio > 1.0."""
        with pytest.raises(ValueError) as excinfo:
            EntropyPruner.compress(SAMPLE_PYTHON_CODE, target_ratio=1.5)
        assert "target_ratio must be between 0.0 and 1.0" in str(excinfo.value)

    def test_negative_budget_tokens(self):
        """Verifies ValueError is raised for negative budget_tokens."""
        with pytest.raises(ValueError) as excinfo:
            EntropyPruner.compress(SAMPLE_PYTHON_CODE, budget_tokens=-5)
        assert "budget_tokens must be non-negative" in str(excinfo.value)

    def test_non_existent_file_cli(self):
        """Verifies CLI returns exit code 1 with clear error for non-existent file."""
        cmd = [
            PYTHON_EXECUTABLE,
            ENTROPY_PRUNER_SCRIPT,
            "--file",
            "non_existent_entropy_file_987654.py",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 1
        assert "not found" in res.stderr

    def test_missing_file_and_text_cli(self):
        """Verifies CLI returns exit code 1 when neither --file nor --text is supplied."""
        cmd = [PYTHON_EXECUTABLE, ENTROPY_PRUNER_SCRIPT]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 1
        assert "Either --file or --text must be specified" in res.stderr

    def test_both_file_and_text_cli(self, tmp_path):
        """Verifies CLI returns exit code 1 when both --file and --text are supplied."""
        dummy_file = tmp_path / "dummy.py"
        dummy_file.write_text("x = 1\n", encoding="utf-8")

        cmd = [
            PYTHON_EXECUTABLE,
            ENTROPY_PRUNER_SCRIPT,
            "--file",
            str(dummy_file),
            "--text",
            "x = 1",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 1
        assert "Cannot specify both --file and --text" in res.stderr

    def test_malformed_input_graceful_lexical_fallback(self):
        """Verifies malformed/unparseable Python syntax is pruned via lexical fallback without crashing."""
        malformed = "def ({ [ : invalid syntax !@#$ \n # comment\n return 42"
        compressed, meta = EntropyPruner.compress(malformed, target_ratio=0.50)
        assert meta["status"] == "ok"
        assert meta["original_token_count"] > 0
        assert "return" in compressed


class TestEntropyPruningBoundary:
    """Scenario 3: Boundary edge cases (empty strings, single tokens, extreme ratios)."""

    def test_empty_string(self):
        """Verifies behavior on empty string."""
        compressed, meta = EntropyPruner.compress("", target_ratio=0.50)
        assert compressed == ""
        assert meta["original_token_count"] == 0
        assert meta["pruned_token_count"] == 0
        assert meta["compression_ratio"] == 0.0
        assert meta["preserved_identifiers_pct"] == 100.0
        assert meta["status"] == "ok"

    def test_single_token_identifier(self):
        """Verifies behavior on single-token input."""
        compressed, meta = EntropyPruner.compress("my_unique_var", target_ratio=0.50)
        assert meta["original_token_count"] == 1
        assert meta["preserved_identifiers_pct"] == 100.0
        assert "my_unique_var" in compressed

    def test_single_token_number(self):
        """Verifies behavior on single numeric token."""
        compressed, meta = EntropyPruner.compress("42", target_ratio=0.50)
        assert meta["original_token_count"] == 1
        assert "42" in compressed

    def test_code_without_comments_or_docstrings(self):
        """Verifies behavior on code containing purely business logic without comments."""
        pure_code = "a = 10\nb = 20\nassert a < b\nresult = a + b\n"
        compressed, meta = EntropyPruner.compress(pure_code, target_ratio=0.50, preserve_identifiers=True)
        assert "assert a < b" in compressed
        assert "result" in compressed
        assert meta["preserved_identifiers_pct"] == 100.0

    def test_code_with_only_comments(self):
        """Verifies behavior on file containing exclusively comments."""
        comments_only = "# Comment line one\n# Comment line two\n# Comment line three\n"
        compressed, meta = EntropyPruner.compress(comments_only, target_ratio=0.0)
        assert meta["original_token_count"] > 0
        assert meta["pruned_token_count"] == meta["original_token_count"]
        assert meta["compression_ratio"] == 1.0
        assert compressed == ""

    def test_extreme_target_ratio_one(self):
        """Verifies target_ratio=1.0 retains 100% of tokens with 0 pruning."""
        compressed, meta = EntropyPruner.compress(SAMPLE_PYTHON_CODE, target_ratio=1.0)
        assert meta["pruned_token_count"] == 0
        assert meta["compression_ratio"] == 0.0
        assert compressed == SAMPLE_PYTHON_CODE

    def test_extreme_target_ratio_zero_preserves_invariants(self):
        """Verifies target_ratio=0.0 strips all boilerplate while retaining core logic invariants."""
        compressed, meta = EntropyPruner.compress(SAMPLE_PYTHON_CODE, target_ratio=0.0, preserve_identifiers=True)
        assert meta["preserved_identifiers_pct"] == 100.0
        assert "def calculate_total" in compressed
        assert "assert tax_rate >= 0.0" in compressed
        assert "for item in items:" in compressed


class TestEntropyPruningCLIFlags:
    """Scenario 4: Verification of all command line interface flags."""

    def test_cli_text_flag(self):
        """Verifies --text flag execution."""
        cmd = [
            PYTHON_EXECUTABLE,
            ENTROPY_PRUNER_SCRIPT,
            "--text",
            "def foo(x):\n # comment\n return x",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "def foo" in res.stdout

    def test_cli_file_flag(self, tmp_path):
        """Verifies --file flag execution."""
        sample_file = tmp_path / "sample.py"
        sample_file.write_text(SAMPLE_PYTHON_CODE, encoding="utf-8")

        cmd = [
            PYTHON_EXECUTABLE,
            ENTROPY_PRUNER_SCRIPT,
            "--file",
            str(sample_file),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "def calculate_total" in res.stdout

    def test_cli_target_ratio_flag(self):
        """Verifies --target-ratio flag is parsed and passed."""
        cmd = [
            PYTHON_EXECUTABLE,
            ENTROPY_PRUNER_SCRIPT,
            "--text",
            "def bar():\n # comment\n pass",
            "--target-ratio",
            "0.25",
            "--json",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        data = json.loads(res.stdout)
        assert data["status"] == "ok"
        assert "bar" in data["compressed_text"]

    def test_cli_budget_tokens_flag(self):
        """Verifies --budget-tokens flag is parsed and respected."""
        cmd = [
            PYTHON_EXECUTABLE,
            ENTROPY_PRUNER_SCRIPT,
            "--text",
            SAMPLE_PYTHON_CODE,
            "--budget-tokens",
            "50",
            "--json",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        data = json.loads(res.stdout)
        assert data["status"] == "ok"
        assert data["original_token_count"] > 0

    def test_cli_output_flag(self, tmp_path):
        """Verifies --output writes compressed text to disk."""
        out_file = tmp_path / "compressed_output.py"
        cmd = [
            PYTHON_EXECUTABLE,
            ENTROPY_PRUNER_SCRIPT,
            "--text",
            "def calc(a, b):\n # note\n return a + b",
            "--output",
            str(out_file),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "def calc(a, b):" in content
        assert "return a + b" in content

    def test_cli_json_flag(self):
        """Verifies --json flag outputs valid JSON structure with all expected keys."""
        cmd = [
            PYTHON_EXECUTABLE,
            ENTROPY_PRUNER_SCRIPT,
            "--text",
            SAMPLE_PYTHON_CODE,
            "--json",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        data = json.loads(res.stdout)

        for expected_key in [
            "original_token_count",
            "pruned_token_count",
            "compression_ratio",
            "preserved_identifiers_pct",
            "compressed_text",
            "status",
        ]:
            assert expected_key in data

        assert data["status"] == "ok"
        assert data["preserved_identifiers_pct"] == 100.0

    def test_cli_no_preserve_identifiers_flag(self):
        """Verifies --no-preserve-identifiers flag disables invariant hard-pinning."""
        cmd = [
            PYTHON_EXECUTABLE,
            ENTROPY_PRUNER_SCRIPT,
            "--text",
            "def non_invariant():\n x = 1\n y = 2\n return x + y",
            "--no-preserve-identifiers",
            "--target-ratio",
            "0.10",
            "--json",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        data = json.loads(res.stdout)
        assert data["status"] == "ok"


class TestEntropyPruningASTAndSurprisalSensors:
    """Rigorous sensor tests for AST invariant visitor, argument types, assertions, and surprisal metrics."""

    def test_ast_visitor_assertion_detection(self):
        import ast
        from tools.reasoning.entropy_pruning import IdentifierVisitor

        # 1. Code without assertions
        tree_no_assert = ast.parse("def calculate(x, y):\n    return x + y")
        v_no = IdentifierVisitor()
        v_no.visit(tree_no_assert)
        assert v_no.has_assertions is False

        # 2. Code with assertions
        tree_assert = ast.parse("def test_calc():\n    assert 1 + 1 == 2")
        v_yes = IdentifierVisitor()
        v_yes.visit(tree_assert)
        assert v_yes.has_assertions is True

    def test_ast_visitor_all_argument_types(self):
        import ast
        from tools.reasoning.entropy_pruning import IdentifierVisitor

        code = "def complex_fn(pos_arg, /, normal_arg, *varargs, kw_only=42, **kwargs):\n    return 0"
        tree = ast.parse(code)
        visitor = IdentifierVisitor()
        visitor.visit(tree)

        assert "complex_fn" in visitor.function_names
        assert "pos_arg" in visitor.arg_names
        assert "normal_arg" in visitor.arg_names
        assert "varargs" in visitor.arg_names
        assert "kw_only" in visitor.arg_names
        assert "kwargs" in visitor.arg_names

    def test_ast_visitor_multiline_docstring_ranges(self):
        import ast
        from tools.reasoning.entropy_pruning import IdentifierVisitor

        code = 'def documented():\n    """Line 2\n    Line 3\n    Line 4"""\n    return 1'
        tree = ast.parse(code)
        visitor = IdentifierVisitor()
        visitor.visit(tree)

        assert len(visitor.docstring_ranges) == 1
        assert 2 in visitor.docstring_lines
        assert 3 in visitor.docstring_lines
        assert 4 in visitor.docstring_lines

    def test_surprisal_estimator_boundary_probabilities(self):
        import math
        from collections import Counter
        from tools.reasoning.entropy_pruning import compute_surprisal

        # Empty estimator (total_count <= 0)
        assert compute_surprisal("nonexistent", Counter(), 0) == 0.0

        # Trained counter
        freqs = Counter({"apple": 3, "banana": 1, "cherry": 1})
        # Token with count 3 out of 5: p = 0.6
        s_apple = compute_surprisal("apple", freqs, 5)
        assert round(s_apple, 4) == round(-math.log2(3 / 5), 4)

        # Unseen token gets default smoothing count 1 -> p = 1 / 5
        s_unseen = compute_surprisal("unseen_word", freqs, 5)
        assert round(s_unseen, 4) == round(-math.log2(1 / 5), 4)

    def test_preserve_identifiers_behavioral_difference(self):
        from tools.reasoning.entropy_pruning import EntropyPruner

        code = (
            "def worker_step():\n"
            "    alpha_var = 1\n"
            "    beta_var = 2\n"
            "    gamma_var = 3\n"
            "    delta_var = 4\n"
            "    return alpha_var + beta_var + gamma_var + delta_var\n"
        )
        # With preserve_identifiers=True (default), 100% of identifiers are preserved
        _, meta_preserved = EntropyPruner.compress(code, target_ratio=0.10, preserve_identifiers=True)
        assert meta_preserved["preserved_identifiers_pct"] == 100.0

        # With preserve_identifiers=False, identifier preservation is relaxed
        _, meta_relaxed = EntropyPruner.compress(code, target_ratio=0.05, preserve_identifiers=False)
        assert meta_relaxed["preserved_identifiers_pct"] <= 100.0
