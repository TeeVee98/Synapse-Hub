#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_token_engineering_and_benchmark.py — Token Engineering & Benchmark Reporting Suite
----------------------------------------------------------------------------------------------
Verifies:
  1. Provider Usage Ingestion & Adapter Isolation:
     - Real provider responses (Google, OpenAI, Anthropic, Antigravity) are parsed strictly.
     - Refuses to interpolate or fabricate fake numbers when usage is absent.
     - Mock provider usage is NEVER mixed or conflated with static/synthetic estimators.
  2. Fallback Heuristic Exactness Status:
     - Heuristic polyglot mode always declares is_exact: False.
  3. Clean JSON Benchmark Output:
     - Subprocess output from `benchmark_swarm_context.py --json` is parsed by a single `json.load`.
     - Schema strictly declares measurement_kind, measurement_source, commit, version, fixture_hash.
  4. Reporting Disclosures:
     - Track 1 is explicitly declared as synthetic micro-workloads.
     - Track 2 is declared as static filesystem workspace inspection.
     - Avoided disk bytes is declared as disk I/O footprint, NOT context tokens or billed savings.
  5. Scientific Honesty & Paired Reduction:
     - Only claims verified live provider reduction when BOTH runs are provider_observed.
  6. Context Decomposition:
     - Statically estimated skill payloads are separated from overall provider input tokens,
       isolating external host system prompts and tool schemas.
"""

import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.core.provider_usage_adapter import (
    ProviderUsageRecord,
    TokenMeasurementRecord,
    serialize_provider_usage,
    parse_provider_usage,
    create_unobserved_provider_record,
    decompose_prompt_context,
    compare_paired_provider_runs,
)
from tools.core.token_estimator import (
    get_estimator_info,
    calculate_hydration_payload,
)
from tools.core.rules_router import route_rules
from tools.context.benchmark_swarm_context import (
    run_benchmark,
    format_markdown_report,
)


class TestProviderUsageAdapter(unittest.TestCase):
    """Verifies strict parsing and boundary enforcement for live provider usage."""

    def test_parse_google_genai_usage_metadata(self):
        """Parses Google GenAI response with prompt_token_count and candidates_token_count."""
        resp = {
            "model": "gemini-1.5-pro",
            "usage_metadata": {
                "prompt_token_count": 1420,
                "candidates_token_count": 310,
                "cached_content_token_count": 600,
                "total_token_count": 1730,
            }
        }
        record = parse_provider_usage(resp, provider_hint="google")
        self.assertIsInstance(record, ProviderUsageRecord)
        self.assertEqual(record.measurement_kind, "provider_observed")
        self.assertEqual(record.provider, "google")
        self.assertEqual(record.model, "gemini-1.5-pro")
        self.assertEqual(record.provider_reported_input_tokens, 1420)
        self.assertEqual(record.provider_reported_output_tokens, 310)
        self.assertEqual(record.provider_cached_tokens, 600)
        self.assertEqual(record.total_provider_tokens, 1730)

    def test_parse_openai_usage(self):
        """Parses OpenAI chat completion usage with prompt_tokens and cached tokens."""
        resp = {
            "model": "gpt-4o",
            "usage": {
                "prompt_tokens": 2100,
                "completion_tokens": 450,
                "total_tokens": 2550,
                "prompt_tokens_details": {
                    "cached_tokens": 1024,
                }
            }
        }
        record = parse_provider_usage(resp)
        self.assertEqual(record.measurement_kind, "provider_observed")
        self.assertEqual(record.provider, "openai")
        self.assertEqual(record.model, "gpt-4o")
        self.assertEqual(record.provider_reported_input_tokens, 2100)
        self.assertEqual(record.provider_reported_output_tokens, 450)
        self.assertEqual(record.provider_cached_tokens, 1024)
        self.assertEqual(record.total_provider_tokens, 2550)

    def test_parse_anthropic_usage(self):
        """Parses Anthropic Messages usage with input_tokens and cache_read_input_tokens."""
        resp = {
            "model": "claude-3-5-sonnet-20241022",
            "usage": {
                "input_tokens": 3200,
                "output_tokens": 800,
                "cache_read_input_tokens": 1500,
            }
        }
        record = parse_provider_usage(resp)
        self.assertEqual(record.measurement_kind, "provider_observed")
        self.assertEqual(record.provider, "anthropic")
        self.assertEqual(record.provider_reported_input_tokens, 3200)
        self.assertEqual(record.provider_reported_output_tokens, 800)
        self.assertEqual(record.provider_cached_tokens, 1500)
        self.assertEqual(record.total_provider_tokens, 4000)

    def test_parse_antigravity_transcript_usage(self):
        """Parses Antigravity transcript turn step dictionary."""
        resp = {
            "provider": "antigravity",
            "model": "gemini-1.5-flash",
            "input_tokens": 950,
            "output_tokens": 180,
            "cache_read_tokens": 400,
        }
        record = parse_provider_usage(resp)
        self.assertEqual(record.measurement_kind, "provider_observed")
        self.assertEqual(record.provider_reported_input_tokens, 950)
        self.assertEqual(record.provider_reported_output_tokens, 180)
        self.assertEqual(record.provider_cached_tokens, 400)
        self.assertEqual(record.total_provider_tokens, 1530)

    def test_refuse_fabrication_when_usage_missing(self):
        """Raises ValueError and refuses to interpolate fake numbers when usage payload is missing."""
        invalid_resp = {"content": "Hello, world!", "status": "200 OK"}
        with self.assertRaises(ValueError) as ctx:
            parse_provider_usage(invalid_resp)
        self.assertIn("refuses to fabricate", str(ctx.exception))

    def test_create_unobserved_provider_record(self):
        """Unobserved provider records must strictly declare None for all provider token fields."""
        unobs = create_unobserved_provider_record(measurement_kind="static_estimate")
        self.assertEqual(unobs["measurement_kind"], "static_estimate")
        self.assertFalse(unobs["provider_observed"])
        self.assertIsNone(unobs["provider"])
        self.assertIsNone(unobs["model"])
        self.assertIsNone(unobs["provider_reported_input_tokens"])
        self.assertIsNone(unobs["provider_reported_output_tokens"])
        self.assertIsNone(unobs["provider_cached_tokens"])
        self.assertIsNone(unobs["total_provider_tokens"])
        self.assertTrue(bool(unobs["timestamp"]))
        self.assertTrue(bool(unobs["commit"]))

    def test_provider_usage_record_post_init_rejects_synthetic(self):
        """ProviderUsageRecord rejects non-provider_observed measurement_kind via __post_init__."""
        with self.assertRaises(ValueError) as ctx:
            ProviderUsageRecord(
                provider="openai",
                model="gpt-4o",
                measurement_kind="synthetic_estimate",
                provider_reported_input_tokens=100,
                provider_reported_output_tokens=50,
                provider_cached_tokens=None,
                total_provider_tokens=150,
                timestamp="2026-11-15T00:00:00Z",
                version="4.2.0",
                commit="abc1234",
                raw_usage={},
            )
        self.assertIn("requires measurement_kind == 'provider_observed'", str(ctx.exception))

    def test_serialize_provider_usage_rejects_synthetic_estimate(self):
        """serialize_provider_usage refuses to serialize synthetic estimates into provider usage."""
        record = TokenMeasurementRecord(
            measurement_kind="synthetic_estimate",
            token_count=200,
            model_name="claude-3-5-sonnet",
            encoding="cl100k_base",
            is_fallback=True,
            commit_sha="a" * 40,
            input_hash="b" * 64,
            timestamp=1700000000.0,
        )
        with self.assertRaises(ValueError) as ctx:
            serialize_provider_usage(record)
        self.assertIn("Cannot serialize non-provider-observed", str(ctx.exception))

    def test_serialize_provider_usage_accepts_provider_observed(self):
        """serialize_provider_usage accepts provider_observed measurement records."""
        record = TokenMeasurementRecord(
            measurement_kind="provider_observed",
            token_count=350,
            model_name="claude-3-5-sonnet",
            encoding="cl100k_base",
            is_fallback=False,
            commit_sha="a" * 40,
            input_hash="b" * 64,
            timestamp=1700000000.0,
        )
        data = serialize_provider_usage(record)
        self.assertEqual(data["measurement_kind"], "provider_observed")
        self.assertEqual(data["provider_reported_input_tokens"], 350)

    def test_calculate_hydration_payload_provenance_metadata(self):
        """calculate_hydration_payload outputs comprehensive provenance metadata."""
        payload = calculate_hydration_payload(
            REPO_ROOT,
            rules=["clean-pom-architecture.md"],
            skills=["clean-pom-crafter"],
        )
        self.assertIn("commit_sha", payload)
        self.assertIn("timestamp", payload)
        self.assertIn("input_hash", payload)
        self.assertIn("is_fallback", payload)
        self.assertIn("encoding", payload)
        self.assertEqual(len(payload["input_hash"]), 64)

    def test_rules_router_token_metrics_carries_provenance(self):
        """rules_router route_rules token_metrics carries comprehensive provenance metadata."""
        res = route_rules(REPO_ROOT, minimal=True)
        metrics = res.get("token_metrics", {})
        self.assertIn("commit_sha", metrics)
        self.assertIn("timestamp", metrics)
        self.assertIn("input_hash", metrics)
        self.assertIn("is_fallback", metrics)
        self.assertIn("encoding", metrics)


class TestContextDecomposition(unittest.TestCase):
    """Verifies separation of statically estimated skill payloads from live provider input tokens."""

    def test_decompose_prompt_context_isolates_external_wrapper(self):
        """Skill payload estimate is subtracted from total provider input tokens."""
        record = ProviderUsageRecord(
            provider="mock_provider",
            model="mock_model",
            measurement_kind="provider_observed",
            provider_reported_input_tokens=5000,
            provider_reported_output_tokens=600,
            provider_cached_tokens=1000,
            total_provider_tokens=5600,
            timestamp="2026-11-15T00:00:00Z",
            version="1.0.0",
            commit="testcommit",
            raw_usage={},
        )

        skill_tokens = 1800
        rule_tokens = 500

        decomposed = decompose_prompt_context(record, skill_payload_tokens=skill_tokens, rule_payload_tokens=rule_tokens)

        self.assertEqual(decomposed["measurement_kind"], "provider_observed_with_decomposition")
        self.assertEqual(decomposed["provider_reported_input_tokens"], 5000)
        self.assertEqual(decomposed["skill_payload_static_estimated_tokens"], 1800)
        self.assertEqual(decomposed["rule_payload_static_estimated_tokens"], 500)
        self.assertEqual(decomposed["total_managed_static_tokens"], 2300)
        # External system prompt and tool schema wrapper = 5000 - 2300 = 2700
        self.assertEqual(decomposed["external_system_prompt_and_wrapper_tokens"], 2700)
        self.assertEqual(decomposed["managed_payload_ratio_pct"], 46.0)
        self.assertIn("disclaimer", decomposed)


class TestPairedProviderVerification(unittest.TestCase):
    """Verifies that live reduction claims are strictly guarded by paired provider tests."""

    def test_paired_provider_runs_reduction_verified(self):
        """Both baseline and optimized runs from provider_observed produce verified reduction."""
        baseline = ProviderUsageRecord(
            provider="mock",
            model="mock-v1",
            measurement_kind="provider_observed",
            provider_reported_input_tokens=10000,
            provider_reported_output_tokens=1000,
            provider_cached_tokens=0,
            total_provider_tokens=11000,
            timestamp="2026-11-15T00:00:00Z",
            version="1.0.0",
            commit="testcommit",
            raw_usage={},
        )
        optimized = ProviderUsageRecord(
            provider="mock",
            model="mock-v1",
            measurement_kind="provider_observed",
            provider_reported_input_tokens=4000,
            provider_reported_output_tokens=600,
            provider_cached_tokens=0,
            total_provider_tokens=4600,
            timestamp="2026-11-15T00:01:00Z",
            version="1.0.0",
            commit="testcommit",
            raw_usage={},
        )

        comp = compare_paired_provider_runs(baseline, optimized)
        self.assertTrue(comp["verified_provider_savings"])
        self.assertEqual(comp["measurement_kind"], "paired_provider_observed")
        self.assertEqual(comp["input_tokens_saved"], 6000)
        self.assertEqual(comp["output_tokens_saved"], 400)
        self.assertEqual(comp["net_tokens_saved"], 6400)
        self.assertAlmostEqual(comp["reduction_pct"], 58.18, places=1)

    def test_refuse_paired_comparison_when_not_provider_observed(self):
        """Refuses to verify live savings if non-provider record is passed."""
        with self.assertRaises(TypeError):
            compare_paired_provider_runs({"input": 100}, {"input": 50})  # type: ignore


class TestFallbackHeuristicExactness(unittest.TestCase):
    """Verifies that fallback heuristic mode always declares is_exact: False."""

    def test_fallback_heuristic_declared_not_exact(self):
        """Simulating absence of tiktoken must return is_exact: False and engine: heuristic_polyglot."""
        with patch("tools.core.token_estimator._TIKTOKEN_ENCODER", None):
            info = get_estimator_info()
            self.assertFalse(info["is_exact"], "Fallback heuristic must never claim to be exact BPE!")
            self.assertEqual(info["engine"], "heuristic_polyglot")


class TestBenchmarkJsonStdoutAndDisclosures(unittest.TestCase):
    """Verifies benchmark CLI output cleanliness and report disclosures."""

    def test_benchmark_cli_json_stdout_single_load(self):
        """Executing benchmark_swarm_context.py --json emits valid JSON parseable with single json.load."""
        cmd = [sys.executable, os.path.join(REPO_ROOT, "tools", "context", "benchmark_swarm_context.py"), "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # stdout must be parseable with json.loads alone
        raw_stdout = proc.stdout.strip()
        data = json.loads(raw_stdout)

        # Verify top-level schema
        self.assertEqual(data["measurement_kind"], "dual_track_benchmark")
        self.assertIn("tokenizer_engine", data)
        self.assertIn("encoding", data)
        self.assertIn("is_exact", data)
        self.assertIn("version", data)
        self.assertIn("commit", data)
        self.assertFalse(data["provider_observed"])
        self.assertIsNone(data["provider_reported_input_tokens"])

        # Verify Track 1 synthetic schema
        syn = data["synthetic_track"]
        self.assertEqual(syn["measurement_kind"], "synthetic")
        self.assertEqual(syn["measurement_source"], "synthetic_micro_workloads_suite")
        self.assertFalse(syn["provider_observed"])
        self.assertIsNone(syn["provider_reported_input_tokens"])
        self.assertGreater(len(syn["scenarios"]), 0)
        for scn in syn["scenarios"]:
            self.assertEqual(scn["measurement_kind"], "synthetic")
            self.assertTrue(bool(scn["fixture_hash"]))
            self.assertIsNone(scn["provider_reported_input_tokens"])

        # Verify Track 2 empirical schema
        emp = data["empirical_track"]
        self.assertEqual(emp["measurement_kind"], "static_estimate")
        self.assertEqual(emp["measurement_source"], "disk_workspace_inspection")
        self.assertFalse(emp["provider_observed"])
        for p in emp["results"]:
            self.assertEqual(p["measurement_kind"], "static_estimate")
            self.assertIn("avoided_disk_bytes", p)
            self.assertIsNone(p["provider_reported_input_tokens"])

    def test_markdown_report_discloses_io_vs_tokens_and_synthetic_scope(self):
        """Markdown report must state Avoided Disk Read is disk I/O, not context tokens or billing savings."""
        bench = run_benchmark()
        md = format_markdown_report(bench)

        # Check scientific disclosures
        self.assertIn("Track 1: Deterministic Micro-Workload Benchmark (Synthetic)", md)
        self.assertIn("Track 2: Empirical Reference Suites Benchmark (Static Workspace Inspection)", md)
        self.assertIn("Avoided Disk Read (I/O)", md)
        self.assertIn("measures filesystem file size bytes not read from storage", md)
        self.assertIn("strictly distinguished from context tokens", md)
        self.assertIn("Offline estimates do not represent live LLM provider billing usage", md)


if __name__ == "__main__":
    unittest.main()
