#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Unit and CLI integration tests for Gemini 4 Neon and Gemini 4 Carbon support
across count_tokens.py, cli.py, and circuit_breaker.py.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

from tools.core import circuit_breaker
from tools.core import cli
from tools.core import count_tokens


class TestGemini4NeonAndCarbonSupport(unittest.TestCase):
    """Verifies pricing, auto-detection, CLI flags, and fallback registration."""

    def test_pricing_table_contains_neon_and_carbon_rates(self):
        self.assertIn("gemini-4-neon", count_tokens.PRICING_TABLE)
        self.assertIn("gemini-4-carbon", count_tokens.PRICING_TABLE)

        neon = count_tokens.PRICING_TABLE["gemini-4-neon"]
        self.assertAlmostEqual(neon["input_per_m"], 3.00)
        self.assertAlmostEqual(neon["cache_per_m"], 0.15)
        self.assertAlmostEqual(neon["output_per_m"], 15.00)
        self.assertIn("Neon", neon["name"])

        carbon = count_tokens.PRICING_TABLE["gemini-4-carbon"]
        self.assertAlmostEqual(carbon["input_per_m"], 4.00)
        self.assertAlmostEqual(carbon["cache_per_m"], 0.20)
        self.assertAlmostEqual(carbon["output_per_m"], 20.00)
        self.assertIn("Carbon", carbon["name"])

    def test_calculate_cost_positive_and_boundary(self):
        neon_cost = count_tokens.calculate_cost(1_000_000, 1_000_000, 1_000_000, "gemini-4-neon")
        self.assertAlmostEqual(neon_cost["input_cost_usd"], 3.00)
        self.assertAlmostEqual(neon_cost["cache_cost_usd"], 0.15)
        self.assertAlmostEqual(neon_cost["output_cost_usd"], 15.00)
        self.assertAlmostEqual(neon_cost["total_cost_usd"], 18.15)
        self.assertIn("Neon", neon_cost["model_name"])

        carbon_cost = count_tokens.calculate_cost(1_000_000, 1_000_000, 1_000_000, "gemini-4-carbon")
        self.assertAlmostEqual(carbon_cost["input_cost_usd"], 4.00)
        self.assertAlmostEqual(carbon_cost["cache_cost_usd"], 0.20)
        self.assertAlmostEqual(carbon_cost["output_cost_usd"], 20.00)
        self.assertAlmostEqual(carbon_cost["total_cost_usd"], 24.20)
        self.assertIn("Carbon", carbon_cost["model_name"])

        # Boundary: zero tokens
        zero_cost = count_tokens.calculate_cost(0, 0, 0, "gemini-4-neon")
        self.assertEqual(zero_cost["total_cost_usd"], 0.0)

        # Negative: unknown model falls back gracefully to DEFAULT_MODEL
        fallback_cost = count_tokens.calculate_cost(1_000_000, 0, 0, "nonexistent-model-xyz")
        default_name = count_tokens.PRICING_TABLE[count_tokens.DEFAULT_MODEL]["name"]
        self.assertEqual(fallback_cost["model_name"], default_name)

    def test_antigravity_transcript_auto_detects_neon_and_carbon(self):
        cases = [
            ("Model Selection from None to Gemini 4 Neon (Medium).", "gemini-4-neon"),
            ("Model Selection from Gemini 4 Hydrogen (High) to GEMINI 4 NEON (High).", "gemini-4-neon"),
            ("Model Selection from Gemini 4 Neon (Medium) to Gemini 4 Carbon (High).", "gemini-4-carbon"),
        ]
        for selection_line, expected_model in cases:
            with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
                entry = {
                    "type": "USER_INPUT",
                    "source": "USER_EXPLICIT",
                    "content": f"<USER_REQUEST>hello</USER_REQUEST>\n<USER_SETTINGS_CHANGE>{selection_line}</USER_SETTINGS_CHANGE>",
                }
                tmp.write(json.dumps(entry) + "\n")
                tmp_path = tmp.name
            try:
                parsed = count_tokens.AntigravityAdapter.parse_transcript(tmp_path)
                self.assertEqual(parsed["detected_model"], expected_model)
            finally:
                os.unlink(tmp_path)

    def test_antigravity_transcript_empty_and_malformed_boundary(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
            tmp.write("\nnot-valid-json\n")
            tmp_path = tmp.name
        try:
            parsed = count_tokens.AntigravityAdapter.parse_transcript(tmp_path)
            self.assertEqual(parsed["detected_model"], count_tokens.DEFAULT_MODEL)
            self.assertEqual(parsed["turns_count"], 0)
        finally:
            os.unlink(tmp_path)

    def test_circuit_breaker_default_fallback_models_include_neon_and_carbon(self):
        self.assertIn("gemini-4-neon", circuit_breaker.DEFAULT_FALLBACK_MODELS)
        self.assertIn("gemini-4-carbon", circuit_breaker.DEFAULT_FALLBACK_MODELS)

        cb = circuit_breaker.TokenCircuitBreaker()
        self.assertIn("gemini-4-neon", cb.fallback_models)
        self.assertIn("gemini-4-carbon", cb.fallback_models)

    def test_cli_tokens_parser_accepts_neon_and_carbon(self):
        parser = cli.build_parser("en")
        args_neon = parser.parse_args(["tokens", "--pricing", "gemini-4-neon", "--json"])
        self.assertEqual(args_neon.pricing, "gemini-4-neon")
        self.assertTrue(args_neon.json)

        args_carbon = parser.parse_args(["tokens", "--pricing", "gemini-4-carbon", "--json"])
        self.assertEqual(args_carbon.pricing, "gemini-4-carbon")
        self.assertTrue(args_carbon.json)

    def test_count_tokens_cli_subprocess_flags_for_neon_and_carbon(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
            entry = {
                "type": "USER_INPUT",
                "source": "USER_EXPLICIT",
                "content": "<USER_REQUEST>test cli flag</USER_REQUEST>",
            }
            tmp.write(json.dumps(entry) + "\n")
            tmp_path = tmp.name

        try:
            for model_key, expected_label in [
                ("gemini-4-neon", "Neon"),
                ("gemini-4-carbon", "Carbon"),
            ]:
                proc = subprocess.run(
                    [
                        sys.executable,
                        "tools/core/count_tokens.py",
                        "--file",
                        tmp_path,
                        "--pricing",
                        model_key,
                        "--json",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, msg=proc.stderr)
                payload = json.loads(proc.stdout)
                self.assertIn(expected_label, payload["costs"]["model_name"])
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
