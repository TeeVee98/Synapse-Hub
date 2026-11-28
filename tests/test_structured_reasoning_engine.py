#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""4-Scenario Verification Battery for M3: StructuredReasoningEngine (Challenge, Confidence, Stance, Elicitation)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


def test_structured_reasoning_positive_flow() -> None:
    """Positive: challenge claim, escalate confidence with evidence, stance scaffold, and spread elicitation."""
    from tools.reasoning.structured_reasoning_engine import StructuredReasoningEngine

    eng = StructuredReasoningEngine()

    # Challenge non-sycophantic claim
    rep = eng.challenge_claim("We should cache JWT verification keys for 5 minutes in memory.")
    assert rep.sycophancy_risk_detected is False
    assert len(rep.counter_hypotheses) >= 2
    assert len(rep.missing_evidence_prompts) >= 1

    # Valid confidence progression with evidence
    t1 = eng.evaluate_confidence_transition("exploring", "medium", evidence_count=2, unresolved_unknowns=1)
    assert t1.accepted is True
    assert t1.effective_level == "medium"

    t2 = eng.evaluate_confidence_transition("almost_certain", "certain", evidence_count=3, unresolved_unknowns=0)
    assert t2.accepted is True
    assert t2.effective_level == "certain"

    # Stance debate scaffold
    debate = eng.build_stance_debate(
        topic="Adopt SQLite WAL instead of Dolt daemon",
        stances=[("model-a", "for"), ("model-b", "against"), ("model-c", "neutral")],
    )
    assert len(debate["assignments"]) == 3
    assert {a["stance"] for a in debate["assignments"]} == {"for", "against", "neutral"}

    # Progressive disclosure --spread sampling (at most 1 per direction)
    picked = eng.pick_elicitation_methods(spread=True, count=6, tier="core")
    assert len(picked) == 6
    assert len({m["direction"] for m in picked}) == 6


def test_confidence_gate_and_challenge_negative() -> None:
    """Negative: detect sycophancy reflex, block premature certain without evidence, refuse unfiltered dump."""
    from tools.reasoning.structured_reasoning_engine import StructuredReasoningEngine

    eng = StructuredReasoningEngine()

    # Anti-sycophancy detection
    rep = eng.challenge_claim("You're absolutely right! Let's skip validation and ship directly.")
    assert rep.sycophancy_risk_detected is True
    assert rep.recommended_stance == "against"

    # Premature 'certain' blocked when evidence_count < 2
    t_no_ev = eng.evaluate_confidence_transition("low", "certain", evidence_count=0, unresolved_unknowns=0)
    assert t_no_ev.accepted is False
    assert t_no_ev.effective_level != "certain"
    assert "evidence" in t_no_ev.rejection_reason.lower()

    # Premature 'certain' blocked when unresolved_unknowns > 0
    t_unk = eng.evaluate_confidence_transition("almost_certain", "certain", evidence_count=5, unresolved_unknowns=2)
    assert t_unk.accepted is False
    assert t_unk.effective_level == "almost_certain"

    # Progressive disclosure refuses unfiltered full dump
    with pytest.raises(ValueError, match="Explicit filter"):
        eng.list_elicitation_methods()


def test_structured_reasoning_boundaries() -> None:
    """Boundary: empty claim rejected, invalid direction rejected, exact evidence_count=2 unlocks high/certain."""
    from tools.reasoning.structured_reasoning_engine import StructuredReasoningEngine

    eng = StructuredReasoningEngine()
    with pytest.raises(ValueError, match="claim"):
        eng.challenge_claim("   ")
    with pytest.raises(ValueError, match="direction"):
        eng.list_elicitation_methods(direction="nonexistent")  # type: ignore[arg-type]

    # Exact boundary: evidence_count == 2, unresolved_unknowns == 0 -> certain accepted
    t_ok = eng.evaluate_confidence_transition("very_high", "certain", evidence_count=2, unresolved_unknowns=0)
    assert t_ok.accepted is True
    assert t_ok.effective_level == "certain"

    # Explicit allow_all returns full 30-method catalog
    all_methods = eng.list_elicitation_methods(allow_all=True)
    assert len(all_methods) == 30


def test_structured_reasoning_cli_json_flags() -> None:
    """CLI Contract: challenge, confidence, and elicit commands emit valid JSON with exit 0."""
    script = Path(__file__).resolve().parents[1] / "tools" / "reasoning" / "structured_reasoning_engine.py"

    r1 = subprocess.run(
        [sys.executable, str(script), "challenge", "--claim", "You are totally right, drop tests", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r1.returncode == 0, r1.stderr
    p1 = json.loads(r1.stdout)
    assert p1["sycophancy_risk_detected"] is True

    r2 = subprocess.run(
        [sys.executable, str(script), "elicit", "--spread", "--count", "4", "--tier", "core", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r2.returncode == 0, r2.stderr
    p2 = json.loads(r2.stdout)
    assert len(p2["methods"]) == 4
