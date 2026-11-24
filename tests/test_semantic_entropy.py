#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_semantic_entropy.py — 4-Scenario Unit Test Battery for SemanticEntropyEngine (R3)
---------------------------------------------------------------------------------------------
Validates:
  - Scenario 1 (Positive): Consensus convergence (0.0 entropy), divergence confabulation (1.0 entropy),
    AST code structural isomorphism, bi-directional entailment, unit normalization, threshold governance.
  - Scenario 2 (Negative): Non-existent files, malformed JSON, invalid out-of-bounds thresholds,
    missing CLI arguments, whitespace/empty hypotheses.
  - Scenario 3 (Boundary): Empty hypothesis list, single hypothesis, exact threshold equality,
    extreme thresholds (0.0 and 1.0), 2-element consensus vs divergence.
  - Scenario 4 (CLI Flags): Full CLI matrix (--hypotheses-file, --prompt, --samples, --threshold,
    --epistemic-search, --output, --json).

TRUTH ANCHOR: Zero fake passes, zero swallowed exceptions, zero static sleeps.
"""

import sys
import json
import subprocess
from pathlib import Path


from tools.reasoning.semantic_entropy import (
    SemanticEntropyEngine,
    SemanticClusterer
)

PYTHON_EXECUTABLE = sys.executable
SEMANTIC_ENTROPY_SCRIPT = str(
    Path(__file__).resolve().parent.parent / "tools" / "reasoning" / "semantic_entropy.py"
)


class TestSemanticEntropyPositive:
    """Scenario 1: Positive verification of clustering, entropy calculations, and epistemic locks."""

    def test_consensus_hypotheses_low_entropy(self) -> None:
        """Verifies that semantically equivalent hypotheses yield 0.0 entropy and grant write permissions."""
        engine = SemanticEntropyEngine()
        hypotheses = [
            "Default timeout is 5000ms configured in BasePage.",
            "Default timeout is 5 seconds configured in BasePage.",
            "BasePage default timeout is 5000ms.",
            "BasePage default timeout is 5s."
        ]

        res = engine.evaluate_hypotheses(hypotheses, threshold=0.50)

        assert res["status"] == "PASS"
        assert res["cluster_count"] == 1
        assert res["clusters_count"] == 1
        assert res["raw_entropy"] == 0.0
        assert res["normalized_entropy"] == 0.0
        assert res["semantic_entropy"] == 0.0
        assert res["uncertainty_status"] == "CONFIDENT_LOW_ENTROPY"
        assert res["code_write_permission"] is True
        assert res["epistemic_search_required"] is False
        assert len(res["epistemic_search_plan"]) == 0
        assert res["total_hypotheses_evaluated"] == 4

    def test_divergent_hypotheses_high_entropy(self) -> None:
        """Verifies that completely divergent hypotheses yield max entropy and enforce epistemic lock."""
        engine = SemanticEntropyEngine()
        hypotheses = [
            "Architecture follows monolithic synchronous orchestrator pattern.",
            "Architecture employs event-driven Kafka stream consumers.",
            "Architecture uses microservices with gRPC communication mesh.",
            "Architecture is serverless AWS Lambda functions triggered by S3."
        ]

        res = engine.evaluate_hypotheses(hypotheses, threshold=0.50)

        assert res["status"] == "PASS"
        assert res["cluster_count"] == 4
        assert res["normalized_entropy"] == 1.0
        assert res["raw_entropy"] == 2.0
        assert res["semantic_entropy"] == 1.0
        assert res["uncertainty_status"] == "HIGH_ENTROPY_CONFABULATION_RISK"
        assert res["code_write_permission"] is False
        assert res["epistemic_search_required"] is True
        assert len(res["epistemic_search_plan"]) == 4

        # Validate structured plan directives
        steps = [p["step"] for p in res["epistemic_search_plan"]]
        assert steps == [1, 2, 3, 4]
        actions = [p["action"] for p in res["epistemic_search_plan"]]
        assert "HALT_SPECULATIVE_WRITING" in actions
        assert "READ_SOURCE_CODE" in actions

    def test_ast_code_equivalence_clustering(self) -> None:
        """Verifies that Python code snippets are clustered by AST structure regardless of var renames or docstrings."""
        code_1 = (
            "def calculate_tax(subtotal, rate):\n"
            "    \"\"\"Calculates sales tax.\"\"\"\n"
            "    return subtotal * rate"
        )
        code_2 = (
            "def calculate_tax(x, y):\n"
            "    return x * y"
        )
        code_3 = (
            "def calculate_tax(subtotal, rate):\n"
            "    return subtotal + rate"
        )

        clusters = SemanticClusterer.cluster([code_1, code_2, code_3])

        assert len(clusters) == 2
        # code_1 and code_2 are AST equivalent (multiplication)
        assert len(clusters[0]) == 2
        assert code_1 in clusters[0]
        assert code_2 in clusters[0]
        # code_3 uses addition, distinct cluster
        assert len(clusters[1]) == 1
        assert code_3 in clusters[1]

    def test_bidirectional_entailment_and_unit_normalization(self) -> None:
        """Verifies unit normalization (e.g. 5000ms vs 5s) correctly bridges semantic equivalence."""
        h1 = "Execution timeout is set to 5000ms in config."
        h2 = "Execution timeout is set to 5 seconds in config."
        h3 = "Execution timeout is set to 30000ms in config."

        clusters = SemanticClusterer.cluster([h1, h2, h3])

        assert len(clusters) == 2
        assert len(clusters[0]) == 2
        assert h1 in clusters[0]
        assert h2 in clusters[0]
        assert h3 in clusters[1]

    def test_polarity_contradiction_separation(self) -> None:
        """Verifies that affirmative and negated statements never cluster together."""
        h_affirmative_1 = "The authentication handshake completed successfully."
        h_affirmative_2 = "The authentication handshake succeeded."
        h_negated_1 = "The authentication handshake failed."
        h_negated_2 = "The authentication handshake did not succeed."

        clusters = SemanticClusterer.cluster([
            h_affirmative_1,
            h_affirmative_2,
            h_negated_1,
            h_negated_2
        ])

        # Affirmatives must not be grouped with negated
        for cluster in clusters:
            has_affirm = any(c in (h_affirmative_1, h_affirmative_2) for c in cluster)
            has_neg = any(c in (h_negated_1, h_negated_2) for c in cluster)
            assert not (has_affirm and has_neg), "Contradictory polarities clustered together"

    def test_threshold_governance(self) -> None:
        """Verifies that threshold strictly dictates write lockout for identical distributions."""
        engine = SemanticEntropyEngine()
        # 4 hypotheses forming 2 equal clusters of 2 -> H = 1.0, max_H = 2.0 -> SE = 0.50
        hypotheses = [
            "Default timeout is 5000ms in BasePage.",
            "Default timeout is 5 seconds in BasePage.",
            "Timeout is 30000ms in Playwright config.",
            "Timeout is 30s in Playwright config."
        ]

        # Case A: threshold 0.60 -> 0.50 <= 0.60 -> PASS / CONFIDENT
        res_a = engine.evaluate_hypotheses(hypotheses, threshold=0.60)
        assert res_a["normalized_entropy"] == 0.5
        assert res_a["uncertainty_status"] == "CONFIDENT_LOW_ENTROPY"
        assert res_a["code_write_permission"] is True
        assert res_a["epistemic_search_required"] is False

        # Case B: threshold 0.40 -> 0.50 > 0.40 -> LOCKOUT
        res_b = engine.evaluate_hypotheses(hypotheses, threshold=0.40)
        assert res_b["normalized_entropy"] == 0.5
        assert res_b["uncertainty_status"] == "HIGH_ENTROPY_CONFABULATION_RISK"
        assert res_b["code_write_permission"] is False
        assert res_b["epistemic_search_required"] is True

    def test_generate_candidate_hypotheses(self) -> None:
        """Verifies synthetic candidate generation for prompt evaluation."""
        engine = SemanticEntropyEngine()

        candidates_timeout = engine.generate_candidate_hypotheses("What is the timeout?", count=4)
        assert len(candidates_timeout) == 4
        assert any("timeout" in c.lower() for c in candidates_timeout)

        candidates_return = engine.generate_candidate_hypotheses("What is the return type of foo?", count=3)
        assert len(candidates_return) == 3
        assert any("return" in c.lower() for c in candidates_return)


class TestSemanticEntropyNegative:
    """Scenario 2: Negative verification of file errors, malformed data, and bad arguments."""

    def test_nonexistent_hypotheses_file(self) -> None:
        """Verifies non-existent file path terminates with exit code 1 and descriptive error."""
        cmd = [PYTHON_EXECUTABLE, SEMANTIC_ENTROPY_SCRIPT, "--hypotheses-file", "nonexistent_hypo_file.json"]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        assert proc.returncode == 1
        assert "not found" in proc.stderr.lower()

    def test_malformed_json_hypotheses_file(self, tmp_path: Path) -> None:
        """Verifies corrupted JSON syntax produces exit code 1 and error diagnostic."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{ this is broken json", encoding="utf-8")

        cmd = [PYTHON_EXECUTABLE, SEMANTIC_ENTROPY_SCRIPT, "--hypotheses-file", str(bad_file)]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        assert proc.returncode == 1
        assert "failed to read" in proc.stderr.lower() or "error" in proc.stderr.lower()

    def test_invalid_threshold_out_of_bounds(self) -> None:
        """Verifies out-of-range threshold values (< 0.0 or > 1.0) exit with code 1."""
        cmd_neg = [
            PYTHON_EXECUTABLE, SEMANTIC_ENTROPY_SCRIPT,
            "--prompt", "test query",
            "--threshold", "-0.1"
        ]
        proc_neg = subprocess.run(cmd_neg, capture_output=True, text=True)
        assert proc_neg.returncode == 1
        assert "between 0.0 and 1.0" in proc_neg.stderr

        cmd_high = [
            PYTHON_EXECUTABLE, SEMANTIC_ENTROPY_SCRIPT,
            "--prompt", "test query",
            "--threshold", "1.5"
        ]
        proc_high = subprocess.run(cmd_high, capture_output=True, text=True)
        assert proc_high.returncode == 1
        assert "between 0.0 and 1.0" in proc_high.stderr

    def test_missing_cli_arguments(self) -> None:
        """Verifies invocation without prompt or hypotheses file exits with code 1."""
        cmd = [PYTHON_EXECUTABLE, SEMANTIC_ENTROPY_SCRIPT]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        assert proc.returncode == 1
        assert "must provide either --prompt or --hypotheses-file" in proc.stderr.lower()

    def test_whitespace_and_empty_string_hypotheses(self) -> None:
        """Verifies graceful handling of empty or blank candidate strings."""
        engine = SemanticEntropyEngine()
        hypotheses = ["", "   ", "\t\n", "Actual content"]

        res = engine.evaluate_hypotheses(hypotheses, threshold=0.50)

        assert res["status"] == "PASS"
        assert res["total_hypotheses_evaluated"] == 4
        assert res["cluster_count"] >= 1


class TestSemanticEntropyBoundary:
    """Scenario 3: Boundary verification for 0-count, 1-count, exact equality, and extreme thresholds."""

    def test_empty_hypotheses_list(self) -> None:
        """Verifies empty hypothesis array yields 0.0 entropy and default low-entropy state."""
        engine = SemanticEntropyEngine()
        res = engine.evaluate_hypotheses([], threshold=0.50)

        assert res["cluster_count"] == 0
        assert res["clusters_count"] == 0
        assert res["clusters"] == []
        assert res["semantic_entropy"] == 0.0
        assert res["raw_entropy"] == 0.0
        assert res["normalized_entropy"] == 0.0
        assert res["uncertainty_status"] == "CONFIDENT_LOW_ENTROPY"
        assert res["code_write_permission"] is True
        assert res["epistemic_search_required"] is False
        assert res["epistemic_search_plan"] == []

    def test_single_hypothesis(self) -> None:
        """Verifies single hypothesis yields 0.0 normalized entropy without DivisionByZero."""
        engine = SemanticEntropyEngine()
        res = engine.evaluate_hypotheses(["Unique hypothesis"], threshold=0.50)

        assert res["cluster_count"] == 1
        assert res["total_hypotheses_evaluated"] == 1
        assert res["semantic_entropy"] == 0.0
        assert res["normalized_entropy"] == 0.0
        assert res["uncertainty_status"] == "CONFIDENT_LOW_ENTROPY"
        assert res["code_write_permission"] is True
        assert res["epistemic_search_required"] is False

    def test_two_identical_hypotheses(self) -> None:
        """Verifies two identical hypotheses collapse to 1 cluster with 0.0 entropy."""
        engine = SemanticEntropyEngine()
        res = engine.evaluate_hypotheses(["Target is Alpha", "Target is Alpha"])

        assert res["cluster_count"] == 1
        assert res["normalized_entropy"] == 0.0
        assert res["uncertainty_status"] == "CONFIDENT_LOW_ENTROPY"

    def test_two_distinct_hypotheses(self) -> None:
        """Verifies two completely distinct hypotheses yield 1.0 normalized entropy (H = 1.0, max_H = 1.0)."""
        engine = SemanticEntropyEngine()
        res = engine.evaluate_hypotheses(["Option Alpha", "Option Beta"], threshold=0.50)

        assert res["cluster_count"] == 2
        assert res["raw_entropy"] == 1.0
        assert res["normalized_entropy"] == 1.0
        assert res["uncertainty_status"] == "HIGH_ENTROPY_CONFABULATION_RISK"
        assert res["code_write_permission"] is False

    def test_exact_threshold_boundary(self) -> None:
        """Verifies boundary condition: SE == threshold must NOT trigger lockout (> comparison)."""
        engine = SemanticEntropyEngine()
        # 4 items with 2 clusters of 2 -> normalized_entropy = 0.50
        hypotheses = [
            "Default timeout is 5000ms.",
            "Default timeout is 5s.",
            "Timeout is 30000ms.",
            "Timeout is 30s."
        ]

        # threshold = 0.50 -> 0.50 > 0.50 is False
        res = engine.evaluate_hypotheses(hypotheses, threshold=0.50)
        assert res["normalized_entropy"] == 0.5
        assert res["code_write_permission"] is True
        assert res["epistemic_search_required"] is False
        assert res["uncertainty_status"] == "CONFIDENT_LOW_ENTROPY"

    def test_extreme_thresholds_zero_and_one(self) -> None:
        """Verifies behavior at extreme thresholds 0.0 and 1.0."""
        engine = SemanticEntropyEngine()
        hypotheses = ["A", "B"]  # SE = 1.0

        # At threshold 0.0: any non-zero entropy triggers lockout
        res_zero = engine.evaluate_hypotheses(hypotheses, threshold=0.0)
        assert res_zero["uncertainty_status"] == "HIGH_ENTROPY_CONFABULATION_RISK"
        assert res_zero["code_write_permission"] is False

        # At threshold 1.0: SE must exceed 1.0 to trigger lockout, which is bounded at 1.0
        res_one = engine.evaluate_hypotheses(hypotheses, threshold=1.0)
        assert res_one["uncertainty_status"] == "CONFIDENT_LOW_ENTROPY"
        assert res_one["code_write_permission"] is True


class TestSemanticEntropyCLIFlags:
    """Scenario 4: Verification of all CLI flags and operational combinations."""

    def test_cli_hypotheses_file_json_flag(self, tmp_path: Path) -> None:
        """Verifies CLI execution with --hypotheses-file and --json flag."""
        sample_file = tmp_path / "hypotheses.json"
        sample_data = {
            "hypotheses": [
                "Default timeout is 5000ms in BasePage.",
                "Default timeout is 5 seconds in BasePage."
            ]
        }
        sample_file.write_text(json.dumps(sample_data), encoding="utf-8")

        cmd = [
            PYTHON_EXECUTABLE, SEMANTIC_ENTROPY_SCRIPT,
            "--hypotheses-file", str(sample_file),
            "--threshold", "0.50",
            "--json"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        assert proc.returncode == 0
        parsed = json.loads(proc.stdout)
        assert parsed["status"] == "PASS"
        assert parsed["cluster_count"] == 1
        assert parsed["normalized_entropy"] == 0.0
        assert parsed["code_write_permission"] is True

    def test_cli_prompt_and_samples_flags(self) -> None:
        """Verifies CLI execution with --prompt, --samples, and --json."""
        cmd = [
            PYTHON_EXECUTABLE, SEMANTIC_ENTROPY_SCRIPT,
            "--prompt", "What is the timeout configuration in BasePage?",
            "--samples", "4",
            "--threshold", "0.50",
            "--json"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        assert proc.returncode == 0
        parsed = json.loads(proc.stdout)
        assert parsed["status"] == "PASS"
        assert parsed["total_hypotheses_evaluated"] == 4
        assert "normalized_entropy" in parsed
        assert "cluster_distribution" in parsed

    def test_cli_output_file_flag(self, tmp_path: Path) -> None:
        """Verifies CLI execution with --output saves results correctly to disk."""
        out_file = tmp_path / "results" / "entropy_out.json"

        cmd = [
            PYTHON_EXECUTABLE, SEMANTIC_ENTROPY_SCRIPT,
            "--prompt", "consensus timeout in BasePage",
            "--output", str(out_file),
            "--json"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        assert proc.returncode == 0
        assert out_file.exists()
        saved = json.loads(out_file.read_text(encoding="utf-8"))
        assert saved["status"] == "PASS"
        assert saved["uncertainty_status"] == "CONFIDENT_LOW_ENTROPY"

    def test_cli_epistemic_search_flag(self) -> None:
        """Verifies CLI execution with --epistemic-search produces textual directives."""
        cmd = [
            PYTHON_EXECUTABLE, SEMANTIC_ENTROPY_SCRIPT,
            "--prompt", "ambiguous architecture patterns",
            "--epistemic-search"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        assert proc.returncode == 0
        assert "SEMANTIC ENTROPY & EPISTEMIC SEARCH ENGINE" in proc.stdout
        assert "Epistemic Search Mandate" in proc.stdout
        assert "HALT_SPECULATIVE_WRITING" in proc.stdout

    def test_cli_custom_threshold_flag(self) -> None:
        """Verifies CLI respects custom --threshold parameter."""
        cmd = [
            PYTHON_EXECUTABLE, SEMANTIC_ENTROPY_SCRIPT,
            "--prompt", "ambiguous architecture patterns",
            "--threshold", "0.85",
            "--json"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        assert proc.returncode == 0
        parsed = json.loads(proc.stdout)
        assert parsed["threshold"] == 0.85


class TestSemanticEntropyASTAndStemmingSensors:
    """Rigorous sensor tests for AST normalization, code equivalence, and morphological stemming."""

    def test_ast_normalization_dunders_and_docstrings(self):
        from tools.reasoning.semantic_entropy import SemanticClusterer

        # 1. Function with docstring vs function without docstring
        code_sync_doc = "def calculate(a, b):\n    '''Docstring summary.'''\n    return a + b"
        code_sync_nodoc = "def compute(x, y):\n    return x + y"
        assert SemanticClusterer._ast_equivalent(code_sync_doc, code_sync_nodoc) is True

        # 2. AsyncFunction with docstring vs without docstring
        code_async_doc = "async def fetch_data(url, timeout):\n    '''Fetch data asynchronously.'''\n    await client.get(url)\n    return True"
        code_async_nodoc = "async def load(endpoint, limit):\n    await client.get(endpoint)\n    return True"
        assert SemanticClusterer._ast_equivalent(code_async_doc, code_async_nodoc) is True

        # 3. None / Invalid code syntax comparison
        assert SemanticClusterer._ast_equivalent("def broken(: pass", "def valid(): pass") is False
        assert SemanticClusterer._ast_equivalent("def valid(): pass", "def broken(: pass") is False
        assert SemanticClusterer._ast_equivalent("def broken1(: pass", "def broken2(: pass") is False

        # 4. Inverting AST comparison (different operator)
        code_diff = "def calculate(a, b):\n    return a - b"
        assert SemanticClusterer._ast_equivalent(code_sync_doc, code_diff) is False

    def test_async_function_without_docstring_no_attribute_error(self):
        """M1 Bugfix: visit_AsyncFunctionDef handles non-docstring bodies (pass, assignment, numeric expr)."""
        # Minimal async def with pass (previously crashed with AttributeError on Pass.value)
        assert SemanticClusterer._ast_equivalent(
            "async def f():\n    pass",
            "async def g():\n    pass",
        ) is True

        # Async def starting with assignment (x = 1)
        assert SemanticClusterer._ast_equivalent(
            "async def f():\n    x = 1\n    return x",
            "async def g():\n    y = 1\n    return y",
        ) is True

        # Async def with docstring only normalizes to pass
        assert SemanticClusterer._ast_equivalent(
            "async def f():\n    '''Only docstring.'''",
            "async def g():\n    pass",
        ) is True

        # Async def with non-string constant expression must NOT be stripped as a docstring
        assert SemanticClusterer._ast_equivalent(
            "async def f():\n    123\n    return 1",
            "async def g():\n    return 1",
        ) is False

    def test_morphological_stemming_boundaries(self):
        from tools.reasoning.semantic_entropy import SemanticClusterer

        # Success / succeed
        assert SemanticClusterer._stem_token("success") == "success"
        assert SemanticClusterer._stem_token("successful") == "success"
        assert SemanticClusterer._stem_token("succeed") == "success"
        assert SemanticClusterer._stem_token("succeeded") == "success"

        # -ies rule (len > 4) -> 'cries' becomes 'cry'
        assert SemanticClusterer._stem_token("cries") == "cry"
        # -ies len <= 4 falls through to -s rule: 'dies' becomes 'die'
        assert SemanticClusterer._stem_token("dies") == "die"
        # -s rule boundary: len <= 3 remains unchanged ('is', 'as')
        assert SemanticClusterer._stem_token("is") == "is"
        assert SemanticClusterer._stem_token("as") == "as"

        # -ing rule (len > 5)
        assert SemanticClusterer._stem_token("running") == "runn"
        assert SemanticClusterer._stem_token("testing") == "test"
        assert SemanticClusterer._stem_token("ring") == "ring"  # len 4 -> unchanged
        assert SemanticClusterer._stem_token("wing") == "wing"  # len 4 -> unchanged

        # -ed rule (len > 4)
        assert SemanticClusterer._stem_token("passed") == "pass"
        assert SemanticClusterer._stem_token("loaded") == "load"
        assert SemanticClusterer._stem_token("red") == "red"    # len 3 -> unchanged
        assert SemanticClusterer._stem_token("bed") == "bed"    # len 3 -> unchanged
