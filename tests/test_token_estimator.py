#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_token_estimator.py — Tests for Unified Polyglot BPE Token Estimator
"""

import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from core.token_estimator import count_tokens, count_file_tokens, calculate_hydration_payload


class TestTokenEstimator(unittest.TestCase):
    """Test suite for token_estimator module."""

    def test_count_empty_text(self):
        self.assertEqual(count_tokens(""), 0)

    def test_count_english_code(self):
        code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        tokens = count_tokens(code)
        self.assertGreater(tokens, 5)
        self.assertLess(tokens, 30)

    def test_count_vietnamese_unicode_density(self):
        en_text = "This is a clean and concise technical specification for software testing."
        vi_text = "Đây là một đặc tả kỹ thuật rõ ràng và ngắn gọn cho việc kiểm thử phần mềm."
        tokens_en = count_tokens(en_text)
        tokens_vi = count_tokens(vi_text)

        # Vietnamese with accents should consume more tokens than English equivalent
        self.assertGreater(tokens_vi, tokens_en * 0.9)

    def test_count_file_tokens(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
            f.write("# Sample Markdown Header\n\nSome body text here.\n")
            temp_path = f.name
        try:
            tokens = count_file_tokens(temp_path)
            self.assertGreater(tokens, 5)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_calculate_hydration_payload(self):
        res = calculate_hydration_payload(
            REPO_ROOT,
            rules=["communication-style.md", "author-integrity-guard.md"],
            skills=["clean-pom-crafter", "verification-before-completion"],
        )
        self.assertIn("rule_tokens", res)
        self.assertIn("skill_catalog_tokens", res)
        self.assertIn("skill_full_body_tokens", res)
        self.assertGreater(res["skill_full_body_tokens"], res["skill_catalog_tokens"])
        self.assertGreater(res["total_hydrated_tokens"], res["total_summary_tokens"])

    def test_session_telemetry_recording_and_summary(self):
        from core.telemetry import SessionTelemetryRecord, record_session_telemetry, get_telemetry_summary

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
            temp_ledger = f.name

        try:
            rec = SessionTelemetryRecord(
                session_id="test_sess_01",
                timestamp="2026-11-13T10:00:00Z",
                model="gemini-flash",
                platform="antigravity",
                task_type="failure_healing",
                stack="playwright",
                turns=3,
                input_tokens=15000,
                output_tokens=1200,
                cached_tokens=11000,
                cache_hit_ratio=0.733,
                raw_log_bytes=50000,
                distilled_log_bytes=1500,
                distillation_reduction_pct=97.0,
                test_outcome="PASS",
                bug_resolved=True,
                tokens_per_bug=16200,
                elapsed_seconds=32.5,
            )
            record_session_telemetry(rec, ledger_file=temp_ledger)
            summary = get_telemetry_summary(ledger_file=temp_ledger)

            self.assertEqual(summary["sample_size"], 1)
            self.assertEqual(summary["resolved_bugs"], 1)
            self.assertEqual(summary["median_tokens_per_bug"], 16200)
            self.assertEqual(summary["mttr_seconds"], 32.5)
            self.assertGreater(summary["avg_cache_hit_ratio"], 0.7)
            self.assertGreater(summary["avg_distillation_reduction_pct"], 90.0)
        finally:
            if os.path.exists(temp_ledger):
                os.remove(temp_ledger)


if __name__ == "__main__":
    unittest.main()
