#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_tier11_suffix_speculative.py — Test Suite for Tier 11 Suffix Speculative Decoder
-----------------------------------------------------------------------------------------
Enforces 4-Scenario Testing: Positive, Negative, Boundary, and CLI invocation.
"""

import json
import subprocess
import sys
import unittest
from tools.runtime.suffix_speculative_decoder import (
    RepoSpeculativeEngine,
    SimpleTokenizer,
    SuffixAutomatonIndex,
    run_benchmark,
)


class TestTier11SuffixSpeculative(unittest.TestCase):
    """Test Suite for Tier 11 Suffix Speculative Decoding Engine."""

    def setUp(self) -> None:
        self.index = SuffixAutomatonIndex(min_ngram=2, max_ngram=12)
        self.sample_code = (
            "import { test, expect } from '@playwright/test';\n"
            "test('sample test', async ({ page }) => {\n"
            "    await page.goto('/login');\n"
            "    await page.fill('#username', 'admin');\n"
            "    await page.fill('#password', 'secret');\n"
            "    await page.click('button[type=\"submit\"]');\n"
            "});\n"
        )
        self.index.index_text("sample.ts", self.sample_code)

    # 1. Positive Scenario
    def test_positive_speculative_match(self) -> None:
        prefix = "await page.fill('#username', 'admin');\n    await page."
        draft = self.index.lookup_continuation(prefix, speculate_len=8)
        self.assertIsNotNone(draft)
        assert draft is not None
        self.assertIn("fill", draft.speculated_text)
        self.assertGreaterEqual(draft.token_count, 1)
        self.assertGreaterEqual(draft.confidence, 0.60)

        # Verification Oracle
        ground_truth = "fill('#password', 'secret');\n    await page."
        verif = RepoSpeculativeEngine.verify_draft(draft, ground_truth)
        self.assertGreaterEqual(verif.accepted_count, 1)
        self.assertGreaterEqual(verif.speedup_ratio, 1.0)

    # 2. Negative Scenario
    def test_negative_no_match(self) -> None:
        prefix = "completely_unknown_token_sequence_xyz_12345"
        draft = self.index.lookup_continuation(prefix)
        self.assertIsNone(draft)

        # Mismatched verification
        if draft:
            verif = RepoSpeculativeEngine.verify_draft(draft, "totally different code")
            self.assertEqual(verif.accepted_count, 0)

    # 3. Boundary Scenario
    def test_boundary_empty_and_null(self) -> None:
        # Empty string
        self.assertIsNone(self.index.lookup_continuation(""))
        self.assertIsNone(self.index.lookup_continuation("   \n\t  "))
        # 1-char token
        self.assertIsNone(self.index.lookup_continuation("a"))

        # Empty tokenizer
        self.assertEqual(SimpleTokenizer.tokenize(""), [])
        self.assertEqual(SimpleTokenizer.detokenize([]), "")

    # 4. CLI & Gate Scenario
    def test_cli_and_gate_execution(self) -> None:
        bench = run_benchmark()
        self.assertEqual(bench["status"], "PASS")
        self.assertLess(bench["lookup_time_ms"], 50.0)

        # Subprocess CLI run
        proc = subprocess.run(
            [sys.executable, "tools/runtime/suffix_speculative_decoder.py", "--benchmark", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["status"], "PASS")

        # Subprocess Gate run
        gate_proc = subprocess.run(
            [sys.executable, "tools/runtime/suffix_speculative_decoder.py", "--gate"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS]", gate_proc.stdout)


if __name__ == "__main__":
    unittest.main()
