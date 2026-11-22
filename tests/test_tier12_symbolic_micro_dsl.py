#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_tier12_symbolic_micro_dsl.py — Test Suite for Tier 12 Symbolic Micro-DSL Compiler
--------------------------------------------------------------------------------------------
Enforces 4-Scenario Testing: Positive, Negative, Boundary, and CLI invocation.
"""

import json
import subprocess
import sys
import unittest
from tools.context.symbolic_micro_dsl import MicroDSLCompiler, run_benchmark


class TestTier12SymbolicMicroDSL(unittest.TestCase):
    """Test Suite for Tier 12 Symbolic Micro-DSL Compiler."""

    # 1. Positive Scenario
    def test_positive_round_trip(self) -> None:
        natural = (
            "Please inspect the implementation in tests/auth/login.spec.ts around lines 1 to 30. "
            "Ensure that it strictly follows the Clean POM architecture and uses dynamic waiting "
            "without any static sleep or hardcoded timeouts. Run the verification test suite."
        )
        encoded = MicroDSLCompiler.encode(natural, target_files=["tests/auth/login.spec.ts:L1-30"])
        self.assertIn("CTX[tests/auth/login.spec.ts:L1-30]", encoded)
        self.assertIn("INV[CleanPOM,!sleep]", encoded)
        self.assertIn("ACT[TEST]", encoded)

        # Validation
        valid, errors = MicroDSLCompiler.validate(encoded)
        self.assertTrue(valid)
        self.assertEqual(errors, [])

        # Decoding
        decoded = MicroDSLCompiler.decode(encoded)
        self.assertTrue(decoded.valid)
        self.assertIn("tests/auth/login.spec.ts:L1-30", decoded.contexts)
        self.assertIn("CleanPOM", decoded.invariants)
        self.assertIn("!sleep", decoded.invariants)

        # Compression Metrics
        metrics = MicroDSLCompiler.calculate_compression(natural, encoded)
        self.assertGreaterEqual(metrics.token_reduction_pct, 40.0)

    def test_balanced_brackets_and_bare_directives(self) -> None:
        # Exact syntax from specification: nested types, pipe in actions, bare assignments
        dsl = "CTX[auth.ts:L12-45] | INV[!mutate(user_id), ret:Result<T,E>] | ACT[PATCH|TEST] | MAX_STEP=2"
        decoded = MicroDSLCompiler.decode(dsl)
        self.assertTrue(decoded.valid)
        self.assertEqual(decoded.contexts, ["auth.ts:L12-45"])
        self.assertEqual(decoded.invariants, ["!mutate(user_id)", "ret:Result<T,E>"])
        self.assertEqual(decoded.actions, ["PATCH", "TEST"])
        self.assertEqual(decoded.budget.get("max_steps"), 2)

    # 2. Negative Scenario
    def test_negative_invalid_dsl(self) -> None:
        invalid_dsl = "INVALID_SYNTAX_WITHOUT_BLOCKS"
        valid, errors = MicroDSLCompiler.validate(invalid_dsl)
        self.assertFalse(valid)
        self.assertGreater(len(errors), 0)

        # Malformed integer in budget
        malformed_budget = "CTX[a.py] | INV[CleanPOM] | BUDGET[max=invalid,think=zero]"
        decoded = MicroDSLCompiler.decode(malformed_budget)
        self.assertFalse(decoded.valid)
        self.assertTrue(any("Invalid integer" in err for err in decoded.errors))

    # 3. Boundary Scenario
    def test_boundary_empty_and_minimal(self) -> None:
        # Empty string
        decoded = MicroDSLCompiler.decode("")
        self.assertFalse(decoded.valid)
        self.assertIn("empty", decoded.errors[0].lower())

        # Whitespace
        decoded_ws = MicroDSLCompiler.decode("   \n\t  ")
        self.assertFalse(decoded_ws.valid)

        # Minimal encoding
        minimal_encoded = MicroDSLCompiler.encode("")
        self.assertIn("INV[CleanPOM]", minimal_encoded)
        self.assertIn("ACT[VERIFY]", minimal_encoded)

        # Entropy computation on empty
        entropy = MicroDSLCompiler._compute_entropy("")
        self.assertEqual(entropy, 0.0)

    # 4. CLI & Gate Scenario
    def test_cli_and_gate_execution(self) -> None:
        bench = run_benchmark()
        self.assertEqual(bench["status"], "PASS")

        # Subprocess CLI run
        proc = subprocess.run(
            [sys.executable, "tools/context/symbolic_micro_dsl.py", "--benchmark", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "PASS")

        # Subprocess Gate run
        gate_proc = subprocess.run(
            [sys.executable, "tools/context/symbolic_micro_dsl.py", "--gate"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS]", gate_proc.stdout)


if __name__ == "__main__":
    unittest.main()
