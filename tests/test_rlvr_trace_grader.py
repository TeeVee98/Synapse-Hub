# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Verify deterministic RLVR rewards and bounded inference-time scaling."""

from dataclasses import FrozenInstanceError
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.reasoning.dynamic_budget_engine import DynamicBudgetEngine


MODULE = "tools.reasoning.rlvr_trace_grader"
ROOT = Path(__file__).resolve().parents[1]
TRACE = "<think>Step 1: Identify the inputs.\nStep 2: Add.\nStep 3: Verify.</think><answer>42</answer>"


@pytest.fixture
def engine():
    assert importlib.util.find_spec(MODULE) is not None, "RLVR grading module is unavailable"
    return importlib.import_module(MODULE)


def test_rlvr_rewards_grpo_and_r1_profile(engine):
    """Positive trace rewards, verification, and R1 inference safeguards."""
    grader = engine.RLVRTraceGrader()
    score = grader.grade(TRACE, expected_answer="42")
    wrong = grader.grade(TRACE, expected_answer="41")
    loop = TRACE.replace("Step 3: Verify.", "Step 1: Verify. " * 100)
    repeated = grader.grade(loop, expected_answer="42")
    assert score.format_score == score.tag_count_score == score.reasoning_steps_score == 1.0
    assert score.extracted_answer == "42"
    assert 0.5 < score.cosine_length_score <= 1.0
    assert score.repetition_penalty == score.overlong_penalty == 0.0
    assert wrong.cosine_length_score < 0.0
    assert score.composite_reward > wrong.composite_reward
    assert repeated.repetition_penalty < 0.0
    assert repeated.reasoning_steps_score == pytest.approx(2 / 3)
    assert repeated.composite_reward < score.composite_reward
    with pytest.raises(FrozenInstanceError):
        score.extracted_answer = None

    advantages = grader.compute_grpo_advantages([1.0, 2.0, 3.0])
    assert advantages == pytest.approx((-1 / 1.0001, 0.0, 1 / 1.0001))
    assert sum(advantages) == pytest.approx(0.0)
    profile = DynamicBudgetEngine.resolve_reasoning_model_profile("deepseek-ai/DeepSeek-R1", temperature=0.95)
    assert profile.model_id == "deepseek-ai/DeepSeek-R1"
    assert profile.temperature == 0.7
    assert profile.avoid_system_prompt
    assert profile.enforce_think_prefix == "<think>\n"
    assert profile.estimated_kv_cache_mb == profile.estimated_flops_per_token == 0.0
    with pytest.raises(FrozenInstanceError):
        profile.temperature = 0.6


def test_negative_trace_format_refuses_empty_reasoning_duplicate_tags_and_partial_answers(engine):
    grader = engine.RLVRTraceGrader()
    blank = grader.grade("<think>\n\n</think><answer>42</answer>", expected_answer="42")
    assert blank.format_score == 0.0
    assert blank.tag_count_score == 1.0
    assert blank.extracted_answer is None
    assert blank.cosine_length_score < 0.0
    for trace in (TRACE + " extra", "<answer>42</answer>", TRACE.replace("Add.", "<think>Add.")):
        result = grader.grade(trace, expected_answer="42")
        assert result.format_score == 0.0
        assert result.extracted_answer is None
    assert grader.tag_count_reward("<think><think></think><answer>42</answer>") == 0.75
    assert grader.reasoning_steps_reward("Step 1: One\nStep 1: One\nStep 1: One") == pytest.approx(1 / 3)
    assert grader.reasoning_steps_reward("1. Count.\n- Add.\nFinally, confirm.") == 1.0
    assert grader.cosine_scaled_length_reward(8, True, max_length=8) == 0.5
    assert grader.cosine_scaled_length_reward(20, False, max_length=8) == -0.5


def test_boundary_trace_n_grams_grpo_and_overlong_penalty(engine):
    grader = engine.RLVRTraceGrader()
    empty = grader.grade("", expected_answer="42")
    assert empty == engine.RLVRTraceScoreDTO(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert grader.compute_grpo_advantages([]) == ()
    assert grader.compute_grpo_advantages([5.0]) == (0.0,)
    assert grader.compute_grpo_advantages([5.0, 5.0]) == (0.0, 0.0)
    with pytest.raises(ValueError, match="finite"):
        grader.compute_grpo_advantages([1.0, float("nan")])
    with pytest.raises(ValueError, match="epsilon"):
        grader.compute_grpo_advantages([0.0, 1.0], epsilon=0.0)

    assert grader.ngram_repetition_penalty("Alpha beta", ngram_size=3) == 0.0
    assert grader.ngram_repetition_penalty("Alpha beta Alpha beta", ngram_size=2) == pytest.approx(-1 / 3)
    with pytest.raises(ValueError, match="ngram_size"):
        grader.ngram_repetition_penalty("word", ngram_size=0)
    assert grader.soft_overlong_penalty(6, max_length=10, soft_limit=4) == 0.0
    assert grader.soft_overlong_penalty(8, max_length=10, soft_limit=4) == -0.5
    assert grader.soft_overlong_penalty(10, max_length=10, soft_limit=4) == -1.0
    assert grader.soft_overlong_penalty(11, max_length=10, soft_limit=4) == -1.0
    with pytest.raises(ValueError):
        grader.soft_overlong_penalty(8, max_length=3, soft_limit=4)
    with pytest.raises(ValueError):
        grader.cosine_scaled_length_reward(-1, True)
    with pytest.raises(ValueError):
        grader.cosine_scaled_length_reward(0, False, max_length=0)


def test_positive_scaling_boxed_votes_and_ties(engine):
    controller = engine.InferenceScalingController()
    assert controller.extract_last_boxed(r"before \boxed{1}, then \boxed{\frac{2}{3}}") == r"\frac{2}{3}"
    assert controller.extract_last_boxed(r"\boxed{\{value\}} then \boxed{open") == r"\{value\}"
    assert controller.extract_last_boxed(r"nothing \boxed{}") is None
    assert controller.extract_last_boxed(r"escaped \\boxed{ignored}") is None
    assert controller.extract_last_boxed("no answer") is None
    ballot = controller.self_consistency_vote([r"work \boxed{42}", "17", TRACE, " ", "42"])
    assert ballot.selected_answer == "42"
    assert ballot.vote_counts == {"42": 3, "17": 1}
    assert ballot.consensus_ratio == 0.75
    assert ballot.refinement_rounds == 0
    assert not ballot.stopped_early_no_gain
    assert controller.self_consistency_vote(["z", "a"]).selected_answer == "z"
    assert controller.self_consistency_vote(["", " "]).selected_answer == ""
    assert controller.self_consistency_vote([""]).consensus_ratio == 0.0
    with pytest.raises(FrozenInstanceError):
        ballot.consensus_ratio = 1.0


def test_boundary_refinement_stops_on_equal_score_and_caps_attempts(engine):
    controller = engine.InferenceScalingController()
    candidates = iter(["stronger", "same score", "must not run"])
    scores = {"initial": 1.0, "stronger": 2.0, "same score": 2.0}
    calls = []

    def refine(previous: str, round_number: int) -> str:
        calls.append((previous, round_number))
        return next(candidates)

    result = controller.self_refinement_loop("initial", refine, scores.__getitem__, max_rounds=3)
    assert calls == [("initial", 1), ("stronger", 2)]
    assert next(candidates) == "must not run"
    assert result.selected_answer == "stronger"
    assert result.refinement_rounds == 2 and result.stopped_early_no_gain
    assert len(result.group_advantages) == 3
    assert sum(result.group_advantages) == pytest.approx(0.0)

    zero = controller.self_refinement_loop("0", lambda _previous, attempt: str(attempt), float, max_rounds=0)
    capped = controller.self_refinement_loop("0", lambda _previous, attempt: str(attempt), float, max_rounds=99)
    early = controller.self_refinement_loop("2", lambda _previous, _attempt: "1", float)
    assert (zero.selected_answer, zero.refinement_rounds, zero.stopped_early_no_gain) == ("0", 0, False)
    assert (capped.selected_answer, capped.refinement_rounds, capped.stopped_early_no_gain) == ("5", 5, False)
    assert (early.selected_answer, early.refinement_rounds, early.stopped_early_no_gain) == ("2", 1, True)
    with pytest.raises(ValueError, match="max_rounds"):
        controller.self_refinement_loop("0", refine, float, max_rounds=-1)
    with pytest.raises(ValueError, match="finite"):
        controller.self_refinement_loop("0", refine, lambda _candidate: float("inf"))


def test_boundary_model_sizing_and_non_r1_temperature():
    engine = DynamicBudgetEngine
    estimate = engine.estimate_kv_cache_and_flops(
        num_layers=2, hidden_size=8, context_tokens=16, vocab_size=32, kv_width=4,
    )
    assert estimate == (512 / 2**20, 4608.0)
    assert engine.estimate_kv_cache_and_flops(num_layers=1, hidden_size=8, context_tokens=0) == (0.0, 1536.0)
    assert engine.estimate_kv_cache_and_flops(num_layers=1, hidden_size=8, context_tokens=2) == (64 / 2**20, 1600.0)
    for fields in (
        {"num_layers": 0}, {"hidden_size": 0}, {"context_tokens": -1}, {"vocab_size": -1},
        {"kv_width": 0}, {"kv_width": 9}, {"bytes_per_value": 0},
    ):
        with pytest.raises(ValueError):
            engine.estimate_kv_cache_and_flops(**({"num_layers": 1, "hidden_size": 8, "context_tokens": 0} | fields))

    r1 = engine.resolve_reasoning_model_profile("provider/deepseek-r1-distill-qwen", 0.2, sizing=estimate)
    assert r1.temperature == 0.5 and r1.avoid_system_prompt
    assert (r1.estimated_kv_cache_mb, r1.estimated_flops_per_token) == estimate
    assert engine.resolve_reasoning_model_profile("deepseek-reasoner").temperature == 0.6
    other = engine.resolve_reasoning_model_profile("other-model", 0.95)
    assert other.temperature == 0.95
    assert not other.avoid_system_prompt and other.enforce_think_prefix == ""
    assert engine.resolve_reasoning_model_profile("other-model").temperature == 0.6
    with pytest.raises(ValueError):
        engine.resolve_reasoning_model_profile("", temperature=0.6)
    with pytest.raises(ValueError):
        engine.resolve_reasoning_model_profile("model", temperature=float("nan"))
    with pytest.raises(ValueError):
        engine.resolve_reasoning_model_profile("model", sizing=(-1.0, 0.0))


def test_cli_json_grade_and_negative_field():
    command = [sys.executable, "-m", MODULE, "--json", "--expected-answer", "42"]
    result = subprocess.run(command, cwd=ROOT, input=TRACE, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["format_score"] == 1.0 and payload["extracted_answer"] == "42"
    failed = subprocess.run(command + ["--max-length", "0"], cwd=ROOT, input=TRACE, capture_output=True, text=True, check=False)
    assert failed.returncode == 2
    assert json.loads(failed.stdout)["error"]
