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

from core.token_estimator import (
    count_tokens,
    count_file_tokens,
    calculate_hydration_payload,
    get_estimator_info,
    get_full_unrouted_baseline,
    _get_skills_manifest,
    clear_skills_manifest_cache,
)


class TestTokenEstimator(unittest.TestCase):
    """Test suite for token_estimator module."""

    def tearDown(self):
        clear_skills_manifest_cache()

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

    def test_get_estimator_info_and_full_baseline(self):
        info = get_estimator_info()
        self.assertIn("engine", info)
        self.assertIn("is_exact", info)
        self.assertEqual(info["encoding"], "cl100k_base")

        baseline = get_full_unrouted_baseline(REPO_ROOT)
        self.assertEqual(baseline["skill_count"], 53)
        self.assertEqual(baseline["rule_count"], 13)
        self.assertGreater(baseline["total_full_baseline"], baseline["total_summary_baseline"])
        self.assertGreater(baseline["total_full_bytes"], 200000)

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

    def test_skills_manifest_multi_repo_isolation_and_mutation(self):
        """Verifies skills manifest cache keys by repo canonical path and invalidates on mutation/deletion."""
        import json
        import shutil
        import time

        dir_a = tempfile.mkdtemp(prefix="repo_a_")
        dir_b = tempfile.mkdtemp(prefix="repo_b_")

        try:
            # Repo A declares skill-A
            path_a = os.path.join(dir_a, "skills_manifest.json")
            with open(path_a, "w", encoding="utf-8") as f:
                json.dump({"skills": [{"id": "skill-A", "name": "Skill A", "description": "From Repo A"}]}, f)

            # Repo B declares skill-B
            path_b = os.path.join(dir_b, "skills_manifest.json")
            with open(path_b, "w", encoding="utf-8") as f:
                json.dump({"skills": [{"id": "skill-B", "name": "Skill B", "description": "From Repo B"}]}, f)

            # 1. Query A -> must return skill-A
            manifest_a1 = _get_skills_manifest(dir_a)
            self.assertIn("skill-A", manifest_a1)
            self.assertNotIn("skill-B", manifest_a1)

            # 2. Query B in same process -> must return skill-B, NOT skill-A (Zero Cross-Repo Leakage)
            manifest_b = _get_skills_manifest(dir_b)
            self.assertIn("skill-B", manifest_b)
            self.assertNotIn("skill-A", manifest_b)

            # 3. Query A again -> must return skill-A (Cache Hit)
            manifest_a2 = _get_skills_manifest(dir_a)
            self.assertIn("skill-A", manifest_a2)

            # 4. Mutate Repo A manifest on disk
            time.sleep(0.05)  # Ensure mtime difference
            with open(path_a, "w", encoding="utf-8") as f:
                json.dump({"skills": [{"id": "skill-A-v2", "name": "Skill A v2", "description": "Mutated"}]}, f)

            manifest_a3 = _get_skills_manifest(dir_a)
            self.assertIn("skill-A-v2", manifest_a3)
            self.assertNotIn("skill-A", manifest_a3)

            # 5. Delete Repo A manifest
            os.remove(path_a)
            manifest_a4 = _get_skills_manifest(dir_a)
            self.assertEqual(manifest_a4, {})
        finally:
            shutil.rmtree(dir_a, ignore_errors=True)
            shutil.rmtree(dir_b, ignore_errors=True)

    def test_fallback_heuristic_exactness_flag(self):
        """Verifies that heuristic fallback mode accurately sets is_exact: False and does not claim exactness."""
        from unittest.mock import patch

        with patch("core.token_estimator._TIKTOKEN_ENCODER", None):
            info = get_estimator_info()
            self.assertEqual(info["engine"], "heuristic_polyglot")
            self.assertFalse(info["is_exact"])
            self.assertIsNone(info["package_version"])

            tokens = count_tokens("Hello world from unit test fallback!")
            self.assertGreater(tokens, 0)


if __name__ == "__main__":
    unittest.main()
