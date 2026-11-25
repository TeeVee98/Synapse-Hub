#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_audit_skills_and_kv_sentinel.py — 4-Scenario Regression Suite for Audit Remediation
-----------------------------------------------------------------------------------------------
Covers:
  - M1: Hermetic skill isolation (surgical-coding-principles AS3 == 0) & skills-lock.json parity.
  - M2: KV-Cache Sentinel --check-latest / --strict CLI & check_latest_telemetry() contract.
  - M2: Normalized transcript token denominator (input_tokens + cache_read_tokens) in audit_transcript_file().
  - Scenarios: Positive, Negative, Boundary, Concurrency, and CLI Flags (--json, --strict, --transcript).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import tools.core.kv_cache_sentinel as kv_sentinel
from tools.core.skill_canonical_digest import validate_lockfile_integrity
from tools.core.skillspector import scan_target


def _write_history(repo_root: str, payload_text: str) -> str:
    telemetry_dir = os.path.join(repo_root, ".synapse", "telemetry")
    os.makedirs(telemetry_dir, exist_ok=True)
    history_path = os.path.join(telemetry_dir, "kv_cache_history.json")
    with open(history_path, "w", encoding="utf-8") as fh:
        fh.write(payload_text)
    return history_path


def _write_config(repo_root: str, min_pct: float) -> str:
    cfg_path = os.path.join(repo_root, "synapse.config.json")
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "telemetry": {
                    "min_kv_cache_hit_rate_pct": min_pct,
                    "alert_on_cache_miss": True,
                }
            },
            fh,
        )
    return cfg_path


def _run_cli(argv: list[str]) -> tuple[int, str]:
    old_argv = sys.argv
    buf = io.StringIO()
    sys.argv = ["kv_cache_sentinel.py", *argv]
    try:
        with redirect_stdout(buf):
            code = kv_sentinel.main()
    finally:
        sys.argv = old_argv
    return code, buf.getvalue()


class TestAuditSkillsAndKVSentinel(unittest.TestCase):
    """4-scenario regression suite for hermetic skills and KV-cache sentinel contracts."""

    def test_positive_skillspector_zero_findings_and_lockfile_integrity(self):
        """Positive: surgical-coding-principles passes SkillSpector with 0 findings and lockfile matches."""
        skill_dir = os.path.join(REPO_ROOT, "skills", "08-code-quality", "surgical-coding-principles")
        report = scan_target(skill_dir)
        self.assertEqual(report.risk_score, 0)
        self.assertEqual(len(report.findings), 0)
        self.assertEqual(report.severity.value, "LOW")

        ok, msg = validate_lockfile_integrity(REPO_ROOT, enforce_content_hash=True)
        self.assertTrue(ok, msg)
        self.assertIn("57/57 skills verified", msg)

    def test_positive_check_latest_passing_record_and_cli_json(self):
        """Positive: --check-latest evaluates passing 90.0% telemetry record and exits 0."""
        with tempfile.TemporaryDirectory() as td:
            _write_history(
                td,
                json.dumps(
                    [
                        {
                            "timestamp": "2026-11-25T10:00:00+00:00",
                            "provider": "anthropic",
                            "model": "claude-sonnet",
                            "input_tokens": 10000,
                            "cached_tokens": 9000,
                        }
                    ]
                ),
            )

            verdict = kv_sentinel.check_latest_telemetry(repo_root=td)
            self.assertIsInstance(verdict, kv_sentinel.LatestKVCacheVerdictDTO)
            with self.assertRaises((FrozenInstanceError, AttributeError)):
                verdict.status = "MUTATED"  # type: ignore[misc]
            self.assertEqual(verdict.status, "EVALUATED")
            self.assertEqual(verdict.timestamp, "2026-11-25T10:00:00+00:00")
            self.assertEqual(verdict.provider, "anthropic")
            self.assertEqual(verdict.model, "claude-sonnet")
            self.assertEqual(verdict.input_tokens, 10000)
            self.assertEqual(verdict.cached_tokens, 9000)
            self.assertEqual(verdict.cache_hit_rate_pct, 90.0)
            self.assertEqual(verdict.min_required_pct, 85.0)
            self.assertTrue(verdict.passed)
            self.assertFalse(verdict.alert_triggered)

            code_json, out_json = _run_cli(["--check-latest", "--repo-root", td, "--json"])
            self.assertEqual(code_json, 0)
            parsed = json.loads(out_json)
            self.assertEqual(parsed["status"], "EVALUATED")
            self.assertEqual(parsed["cache_hit_rate_pct"], 90.0)
            self.assertTrue(parsed["passed"])
            self.assertFalse(parsed["alert_triggered"])

            code_txt, out_txt = _run_cli(["--check-latest", "--repo-root", td])
            self.assertEqual(code_txt, 0)
            self.assertIn("90.0%", out_txt)
            self.assertIn("PASS", out_txt)

    def test_positive_audit_transcript_normalizes_total_input_tokens(self):
        """Positive: audit_transcript_file sums uncached input_tokens + cache_read_tokens."""
        with tempfile.TemporaryDirectory() as td:
            transcript_path = os.path.join(td, "transcript.jsonl")
            with open(transcript_path, "w", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "input_tokens": 2514,
                            "cache_read_tokens": 54206,
                            "model": "gemini-4-hydrogen",
                        }
                    )
                    + "\n"
                )
                fh.write(
                    json.dumps(
                        {
                            "input_tokens": 1000,
                            "cache_read_input_tokens": 9000,
                            "model": "claude-sonnet",
                        }
                    )
                    + "\n"
                )

            audits = kv_sentinel.audit_transcript_file(transcript_path, repo_root=td)
            self.assertEqual(len(audits), 2)
            self.assertEqual(audits[0].input_tokens, 56720)
            self.assertEqual(audits[0].cached_tokens, 54206)
            self.assertEqual(audits[0].cache_hit_rate_pct, 95.57)
            self.assertLessEqual(audits[0].cache_hit_rate_pct, 100.0)
            self.assertTrue(audits[0].passed)
            self.assertEqual(audits[0].provider, "antigravity")
            self.assertEqual(audits[0].model, "gemini-4-hydrogen")

            self.assertEqual(audits[1].input_tokens, 10000)
            self.assertEqual(audits[1].cached_tokens, 9000)
            self.assertEqual(audits[1].cache_hit_rate_pct, 90.0)

            code, out = _run_cli(["--transcript", transcript_path, "--repo-root", td, "--json"])
            self.assertEqual(code, 0)
            cli_items = json.loads(out)
            self.assertEqual(len(cli_items), 2)
            self.assertEqual(cli_items[0]["cache_hit_rate_pct"], 95.57)

            compat = kv_sentinel.evaluate_cache_hit_rate(input_tokens=4000, cached_tokens=3600, min_pct=85.0)
            self.assertEqual(compat.cache_hit_rate_pct, 90.0)
            self.assertTrue(compat.passed)

    def test_negative_check_latest_sla_breach_exits_one(self):
        """Negative: 75.0% hit rate triggers SLA breach alert and exit code 1."""
        with tempfile.TemporaryDirectory() as td:
            _write_history(
                td,
                json.dumps(
                    [
                        {
                            "timestamp": "2026-11-25T10:00:00+00:00",
                            "provider": "anthropic",
                            "model": "claude-sonnet",
                            "input_tokens": 10000,
                            "cached_tokens": 9000,
                        },
                        {
                            "timestamp": "2026-11-25T10:05:00+00:00",
                            "provider": "openai",
                            "model": "gpt-5",
                            "input_tokens": 4000,
                            "cached_tokens": 3000,
                        },
                    ]
                ),
            )

            verdict = kv_sentinel.check_latest_telemetry(repo_root=td)
            self.assertEqual(verdict.status, "EVALUATED")
            self.assertEqual(verdict.provider, "openai")
            self.assertEqual(verdict.model, "gpt-5")
            self.assertEqual(verdict.cache_hit_rate_pct, 75.0)
            self.assertFalse(verdict.passed)
            self.assertTrue(verdict.alert_triggered)
            self.assertIn("ALERT", verdict.details)

            code_json, out_json = _run_cli(["--check-latest", "--repo-root", td, "--json"])
            self.assertEqual(code_json, 1)
            payload = json.loads(out_json)
            self.assertEqual(payload["status"], "EVALUATED")
            self.assertFalse(payload["passed"])
            self.assertTrue(payload["alert_triggered"])

            code_txt, out_txt = _run_cli(["--check-latest", "--repo-root", td])
            self.assertEqual(code_txt, 1)
            self.assertIn("ALERT", out_txt)

    def test_negative_corrupt_history_json_and_negative_tokens(self):
        """Negative: malformed JSON, non-list root, missing keys, and negative tokens fail cleanly."""
        bad_payloads = [
            "{malformed json",
            json.dumps({"not": "a list"}),
            json.dumps(["not-a-dict"]),
            json.dumps([{"provider": "anthropic"}]),
            json.dumps([{"input_tokens": True, "cached_tokens": 100}]),
            json.dumps([{"input_tokens": -100, "cached_tokens": 50}]),
            json.dumps([{"input_tokens": 100, "cached_tokens": -5}]),
        ]
        for raw_payload in bad_payloads:
            with tempfile.TemporaryDirectory() as td:
                _write_history(td, raw_payload)
                verdict = kv_sentinel.check_latest_telemetry(repo_root=td)
                self.assertEqual(verdict.status, "CORRUPT_TELEMETRY_HISTORY")
                self.assertFalse(verdict.passed)
                self.assertTrue(verdict.alert_triggered)

                code, out = _run_cli(["--check-latest", "--repo-root", td, "--json"])
                self.assertEqual(code, 1)
                parsed = json.loads(out)
                self.assertEqual(parsed["status"], "CORRUPT_TELEMETRY_HISTORY")
                self.assertFalse(parsed["passed"])
                self.assertTrue(parsed["alert_triggered"])

    def test_negative_transcript_skips_malformed_and_negative_steps(self):
        """Negative: malformed JSONL lines, booleans, and negative tokens are skipped safely."""
        with tempfile.TemporaryDirectory() as td:
            transcript_path = os.path.join(td, "transcript.jsonl")
            with open(transcript_path, "w", encoding="utf-8") as fh:
                fh.write("not valid json\n")
                fh.write("[1, 2, 3]\n")
                fh.write(json.dumps({"input_tokens": -5, "cache_read_tokens": 100}) + "\n")
                fh.write(json.dumps({"input_tokens": 100, "cache_read_tokens": -5}) + "\n")
                fh.write(json.dumps({"input_tokens": True, "cache_read_tokens": 100}) + "\n")
                fh.write(json.dumps({"input_tokens": 100, "cache_read_tokens": 900}) + "\n")

            audits = kv_sentinel.audit_transcript_file(transcript_path, repo_root=td)
            self.assertEqual(len(audits), 1)
            self.assertEqual(audits[0].input_tokens, 1000)
            self.assertEqual(audits[0].cached_tokens, 900)
            self.assertEqual(audits[0].cache_hit_rate_pct, 90.0)

    def test_boundary_missing_or_empty_history_default_vs_strict(self):
        """Boundary: missing or empty history yields NO_TELEMETRY_RECORDED (exit 0 default, 1 strict)."""
        for create_empty_list in (False, True):
            with tempfile.TemporaryDirectory() as td:
                if create_empty_list:
                    _write_history(td, "[]")

                default_verdict = kv_sentinel.check_latest_telemetry(repo_root=td)
                self.assertEqual(default_verdict.status, "NO_TELEMETRY_RECORDED")
                self.assertIsNone(default_verdict.input_tokens)
                self.assertIsNone(default_verdict.cached_tokens)
                self.assertIsNone(default_verdict.cache_hit_rate_pct)
                self.assertEqual(default_verdict.min_required_pct, 85.0)
                self.assertTrue(default_verdict.passed)
                self.assertFalse(default_verdict.alert_triggered)

                code_default, out_default = _run_cli(["--check-latest", "--repo-root", td, "--json"])
                self.assertEqual(code_default, 0)
                self.assertEqual(json.loads(out_default)["status"], "NO_TELEMETRY_RECORDED")

                strict_verdict = kv_sentinel.check_latest_telemetry(repo_root=td, strict=True)
                self.assertEqual(strict_verdict.status, "NO_TELEMETRY_RECORDED")
                self.assertFalse(strict_verdict.passed)
                self.assertTrue(strict_verdict.alert_triggered)

                code_strict, out_strict = _run_cli(
                    ["--check-latest", "--strict", "--repo-root", td, "--json"]
                )
                self.assertEqual(code_strict, 1)
                parsed_strict = json.loads(out_strict)
                self.assertEqual(parsed_strict["status"], "NO_TELEMETRY_RECORDED")
                self.assertFalse(parsed_strict["passed"])
                self.assertTrue(parsed_strict["alert_triggered"])

    def test_boundary_transcript_zero_uncached_and_exact_sla_thresholds(self):
        """Boundary: 0 uncached + 5000 cached == 100.0%, 0+0 skipped, exact 85.0% passes, 84.99% fails."""
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(kv_sentinel.audit_transcript_file(os.path.join(td, "missing.jsonl"), repo_root=td), [])

            transcript_path = os.path.join(td, "transcript.jsonl")
            with open(transcript_path, "w", encoding="utf-8") as fh:
                fh.write("\n   \n")
                fh.write(json.dumps({"input_tokens": 0, "cache_read_tokens": 0}) + "\n")
                fh.write(json.dumps({"input_tokens": 0, "cache_read_tokens": 5000}) + "\n")
                fh.write(json.dumps({"cache_read_tokens": 5000}) + "\n")
                fh.write(json.dumps({"input_tokens": 1000}) + "\n")
                fh.write(json.dumps({"input_tokens": 0, "cache_read_tokens": 1}) + "\n")
                fh.write(json.dumps({"input_tokens": 150, "cache_read_tokens": 850}) + "\n")
                fh.write(json.dumps({"input_tokens": 1501, "cache_read_tokens": 8499}) + "\n")

            audits = kv_sentinel.audit_transcript_file(transcript_path, repo_root=td)
            self.assertEqual(len(audits), 6)
            self.assertEqual(audits[0].input_tokens, 5000)
            self.assertEqual(audits[0].cache_hit_rate_pct, 100.0)
            self.assertTrue(audits[0].passed)

            self.assertEqual(audits[1].input_tokens, 5000)
            self.assertEqual(audits[1].cached_tokens, 5000)
            self.assertEqual(audits[1].cache_hit_rate_pct, 100.0)

            self.assertEqual(audits[2].input_tokens, 1000)
            self.assertEqual(audits[2].cached_tokens, 0)
            self.assertEqual(audits[2].cache_hit_rate_pct, 0.0)
            self.assertFalse(audits[2].passed)

            self.assertEqual(audits[3].input_tokens, 1)
            self.assertEqual(audits[3].cached_tokens, 1)
            self.assertEqual(audits[3].cache_hit_rate_pct, 100.0)

            self.assertEqual(audits[4].cache_hit_rate_pct, 85.0)
            self.assertTrue(audits[4].passed)

            self.assertEqual(audits[5].cache_hit_rate_pct, 84.99)
            self.assertFalse(audits[5].passed)

            _write_config(td, 92.0)
            _write_history(td, json.dumps([{"input_tokens": 10000, "cached_tokens": 9000}]))
            verdict_custom = kv_sentinel.check_latest_telemetry(repo_root=td)
            self.assertEqual(verdict_custom.min_required_pct, 92.0)
            self.assertFalse(verdict_custom.passed)
            self.assertTrue(verdict_custom.alert_triggered)

    def test_concurrency_read_only_check_latest_and_subprocess_cli(self):
        """Concurrency & CLI: parallel --check-latest calls are idempotent and non-mutating."""
        with tempfile.TemporaryDirectory() as td:
            raw_history = json.dumps(
                [
                    {
                        "timestamp": "2026-11-25T11:00:00+00:00",
                        "provider": "gemini",
                        "model": "gemini-4-hydrogen",
                        "input_tokens": 10000,
                        "cached_tokens": 9000,
                    }
                ]
            )
            history_path = _write_history(td, raw_history)

            with ThreadPoolExecutor(max_workers=8) as pool:
                verdicts = list(pool.map(lambda _: kv_sentinel.check_latest_telemetry(repo_root=td), range(8)))

            for v in verdicts:
                self.assertEqual(v.status, "EVALUATED")
                self.assertEqual(v.cache_hit_rate_pct, 90.0)
                self.assertTrue(v.passed)

            with open(history_path, "r", encoding="utf-8") as fh:
                self.assertEqual(fh.read(), raw_history)

            proc = subprocess.run(
                [
                    sys.executable,
                    os.path.join(REPO_ROOT, "tools", "core", "kv_cache_sentinel.py"),
                    "--check-latest",
                    "--repo-root",
                    td,
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["status"], "EVALUATED")


if __name__ == "__main__":
    unittest.main()
