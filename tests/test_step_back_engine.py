# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for tools/reasoning/step_back_engine.py (DeepMind Step-Back & Stanford Attention Pattern)."""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from reasoning.step_back_engine import StepBackEngine


def test_step_back_question_generation_concurrency():
    engine = StepBackEngine()
    task = "Fix double-click race condition in checkout payment flow"
    questions = engine.generate_abstract_questions(task)

    assert len(questions) >= 1
    categories = [q["category"] for q in questions]
    assert "DISTRIBUTED_CONCURRENCY" in categories
    assert any("idempotent" in q["target_mental_model"].lower() or "concurren" in q["abstract_question"].lower() for q in questions)


def test_step_back_question_generation_auth_and_flakiness():
    engine = StepBackEngine()
    task = "Audit auth token refresh under network flakiness and static sleep"
    questions = engine.generate_abstract_questions(task)

    categories = [q["category"] for q in questions]
    assert "SECURITY_IDENTITY" in categories
    assert "ASYNCHRONOUS_OBSERVABILITY" in categories


def test_step_back_derive_governing_principles():
    engine = StepBackEngine()
    task = "Design high-load API stress test under connection pool saturation"
    questions = engine.generate_abstract_questions(task)
    principles = engine.derive_governing_principles(task, questions)

    assert len(principles) >= 1
    p = principles[0]
    assert "principle_name" in p
    assert "core_invariant" in p
    assert "concrete_guardrails" in p
    assert len(p["concrete_guardrails"]) >= 2


def test_step_back_attention_layout_optimization():
    engine = StepBackEngine()
    task = "Eliminate race condition in state transitions"
    long_log = "\n".join([f"Log line {i}: network event packet trace" for i in range(100)])

    res = engine.run(task_text=task, context_data=long_log)
    assert res["status"] == "SUCCESS"
    assert res["framework"].startswith("Step-Back Prompting")

    layout = res["attention_layout"]
    assert layout["attention_optimization_applied"] is True
    assert layout["primacy_anchor_char_count"] > 0
    assert layout["recency_anchor_char_count"] > 0
    assert layout["middle_zone_char_count"] > 0

    # Verify that the long log was distilled to prevent Lost in the Middle
    payload = layout["optimized_prompt_payload"]
    assert "Middle content distilled" in payload
    assert "IMMUTABLE GOVERNING INVARIANTS" in payload
    assert "IMMEDIATE EXECUTION TARGET" in payload
