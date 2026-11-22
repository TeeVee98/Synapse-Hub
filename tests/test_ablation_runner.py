#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Unit tests for the Deterministic Ablation Benchmark Runner and Dataset (100 Tasks).
"""

import pytest

from benchmarks.qa_eval.ablation_runner import (
    load_all_challenges,
    DeterministicAblationEngine,
    AblationBenchmarkHarness,
    calculate_cost_flash,
)


class TestAblationDataset:
    def test_load_all_challenges_has_100_vectors(self):
        challenges = load_all_challenges()
        assert len(challenges) == 100, f"Expected exactly 100 challenges, but found {len(challenges)}"

    def test_all_challenges_have_required_schema_fields(self):
        challenges = load_all_challenges()
        required_keys = {"id", "name", "category", "difficulty", "failure_vector", "expected_resolution"}
        for c in challenges:
            missing = required_keys - set(c.keys())
            assert not missing, f"Challenge {c.get('id')} missing keys: {missing}"

    def test_cost_calculation_gemini_flash(self):
        cost = calculate_cost_flash(prompt_tokens=1_000_000, completion_tokens=1_000_000)
        assert cost == 0.375


class TestDeterministicAblationEngine:
    @pytest.fixture
    def sample_challenge(self):
        return {
            "id": "QA-CHALLENGE-TEST",
            "name": "Mock Challenge",
            "category": "locator_drift",
            "difficulty": "MEDIUM",
            "failure_vector": {
                "type": "LOCATOR_DRIFT",
                "broken_locator": "button.submit",
                "dom_snapshot": "<button id='submit-order' data-testid='submit-order-btn'>Submit</button>",
            },
            "expected_resolution": {
                "healed_locator": "[data-testid='submit-order-btn']",
                "strategy": "AOM_ROLE_OR_TESTID",
            },
        }

    def test_c0_unassisted_baseline(self, sample_challenge):
        engine = DeterministicAblationEngine()
        out = engine.evaluate_c0(sample_challenge)
        assert out["tier"] == "C0"
        assert out["prompt_tokens"] >= 400

    def test_c2_kills_fake_pass_tautology(self):
        engine = DeterministicAblationEngine()
        tautology_challenge = {
            "id": "QA-TAUTOLOGY-TEST",
            "name": "Tautology",
            "category": "fake_pass_tautology",
            "failure_vector": {"code_snippet": "assert true == true;"},
            "expected_resolution": {"healed_code": "assert response.status == 200;"},
        }
        out_c0 = engine.evaluate_c0(tautology_challenge)
        out_c2 = engine.evaluate_c2(tautology_challenge)
        assert out_c0["false_pass"] is True
        assert out_c2["false_pass"] is False
        assert out_c2["status"] == "PASSED"

    def test_c3_slashes_context_window(self, sample_challenge):
        engine = DeterministicAblationEngine()
        out_c2 = engine.evaluate_c2(sample_challenge)
        out_c3 = engine.evaluate_c3(sample_challenge)
        assert out_c3["prompt_tokens"] < out_c2["prompt_tokens"] * 0.35
        assert out_c3["latency_sec"] < out_c2["latency_sec"]

    def test_c5_monolith_incurs_complexity_tax(self, sample_challenge):
        engine = DeterministicAblationEngine()
        out_c3 = engine.evaluate_c3(sample_challenge)
        out_c5 = engine.evaluate_c5(sample_challenge)
        assert out_c5["latency_sec"] > out_c3["latency_sec"] * 5
        assert out_c5["total_tokens"] > out_c3["total_tokens"] * 4


class TestAblationHarness:
    def test_pareto_classification(self):
        harness = AblationBenchmarkHarness()
        mock_summary = {
            "C0": {"pass_rate_pct": 5.0, "mean_latency_sec": 1.60, "mean_cost_usd": 0.00018, "hidr_pct": 0.0},
            "C1": {"pass_rate_pct": 64.0, "mean_latency_sec": 1.93, "mean_cost_usd": 0.00022, "hidr_pct": 0.0},
            "C2": {"pass_rate_pct": 88.0, "mean_latency_sec": 2.00, "mean_cost_usd": 0.00022, "hidr_pct": 0.0},
            "C3": {"pass_rate_pct": 100.0, "mean_latency_sec": 0.68, "mean_cost_usd": 0.00004, "hidr_pct": 0.0},
            "C4": {"pass_rate_pct": 100.0, "mean_latency_sec": 3.83, "mean_cost_usd": 0.00015, "hidr_pct": 0.0},
            "C5": {"pass_rate_pct": 100.0, "mean_latency_sec": 15.28, "mean_cost_usd": 0.00063, "hidr_pct": 0.0},
        }
        pareto = harness._classify_pareto(mock_summary)
        assert pareto["C3"]["is_pareto_optimal"] is True
        assert pareto["C3"]["action"] == "CORE (Always-On)"
        assert pareto["C4"]["action"] == "ON-DEMAND (Opt-In / Tier-Conditioned)"
        assert pareto["C5"]["action"] == "PRUNE / ARCHIVE (Eliminate from Hot-Path)"
