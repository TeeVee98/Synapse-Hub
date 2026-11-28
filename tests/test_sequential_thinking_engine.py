#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""4-Scenario Verification Battery for M2: SequentialThinking, ToT Beam Pruner, Ulysses & OODA."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


def test_sequential_thinking_revision_branching_and_tot_beam_positive() -> None:
    """Positive: record thoughts, revise, branch, and beam-prune candidates by score."""
    from tools.reasoning.sequential_thinking_engine import (
        SequentialThinkingSession,
        beam_prune_branches,
    )

    sess = SequentialThinkingSession(session_id="sess-1")
    s1 = sess.record_thought(1, 3, "Analyze root cause in login handler", next_thought_needed=True)
    assert s1.thought_number == 1
    assert s1.is_revision is False

    s2 = sess.record_thought(
        2, 3, "Revise: failure is in token refresh, not login", next_thought_needed=True,
        is_revision=True, revises_thought=1,
    )
    assert s2.is_revision is True
    assert s2.revises_thought == 1

    s3 = sess.record_thought(
        3, 3, "Explore retry-backoff branch", next_thought_needed=False,
        branch_from_thought=2, branch_id="branch-retry",
    )
    assert s3.branch_id == "branch-retry"
    assert "branch-retry" in sess.branches

    pruned = beam_prune_branches(
        candidates=[
            {"id": "A", "proposal": "Rewrite auth", "votes": [0.3, 0.4]},
            {"id": "B", "proposal": "Patch token refresh lock", "votes": [0.9, 0.95]},
            {"id": "C", "proposal": "Disable cache", "votes": [0.6, 0.65]},
        ],
        beam_width=2,
    )
    assert [c["id"] for c in pruned] == ["B", "C"]
    assert pruned[0]["beam_score"] == pytest.approx(0.925)

    md = sess.export_markdown()
    assert "sess-1" in md
    assert "branch-retry" in md


def test_sequential_and_ooda_negative_validation() -> None:
    """Negative: invalid revision target, oversized thought, and OODA advance without enough evidence."""
    from tools.reasoning.sequential_thinking_engine import (
        OODALoopSession,
        SequentialThinkingSession,
    )

    sess = SequentialThinkingSession(session_id="neg-1", max_thought_chars=40)
    with pytest.raises(ValueError, match="max_thought_chars"):
        sess.record_thought(1, 2, "x" * 60, next_thought_needed=True)

    with pytest.raises(ValueError, match="revises_thought"):
        sess.record_thought(1, 2, "rev", next_thought_needed=True, is_revision=True, revises_thought=99)

    ooda = OODALoopSession(session_id="ooda-1", min_evidence=2)
    res_blocked = ooda.advance(evidence=["single log line"], hypothesis="stale cache")
    assert res_blocked["advanced"] is False
    assert res_blocked["phase"] == "observe"
    assert "min_evidence" in res_blocked["reason"]


def test_ulysses_and_ooda_boundaries() -> None:
    """Boundary: Ulysses escalates at max_iterations or time budget; OODA advances at exact min_evidence."""
    from tools.reasoning.sequential_thinking_engine import (
        OODALoopSession,
        UlyssesProtocolSession,
        beam_prune_branches,
    )

    assert beam_prune_branches([], beam_width=2) == []

    # Ulysses aligned with Invariant 13 (max_iterations=2)
    ulysses = UlyssesProtocolSession(session_id="u-1", max_iterations=2, time_budget_sec=30.0)
    g1 = ulysses.step(phase="execute", elapsed_sec=5.0, summary="Attempt 1")
    assert g1.must_escalate is False
    assert g1.iteration == 1

    g2 = ulysses.step(phase="execute", elapsed_sec=10.0, summary="Attempt 2")
    assert g2.must_escalate is True
    assert g2.phase == "escalate"
    assert "iteration" in g2.reason.lower()

    # Time budget boundary
    u_time = UlyssesProtocolSession(session_id="u-2", max_iterations=5, time_budget_sec=10.0)
    gt = u_time.step(phase="execute", elapsed_sec=12.5, summary="Slow run")
    assert gt.must_escalate is True
    assert "time" in gt.reason.lower()

    # OODA boundary exact min_evidence == 2
    ooda = OODALoopSession(session_id="ooda-b", min_evidence=2)
    r1 = ooda.advance(evidence=["e1", "e2"], hypothesis="race in worker")
    assert r1["advanced"] is True
    assert r1["phase"] == "orient"
    assert "race in worker" in r1["active_hypotheses"]


def test_sequential_thinking_cli_json_flags() -> None:
    """CLI Contract: think, ulysses, and beam subcommands emit valid JSON with exit 0."""
    script = Path(__file__).resolve().parents[1] / "tools" / "reasoning" / "sequential_thinking_engine.py"

    r1 = subprocess.run(
        [sys.executable, str(script), "think", "--thought", "Check boundary", "--number", "1", "--total", "2", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r1.returncode == 0, r1.stderr
    p1 = json.loads(r1.stdout)
    assert p1["thought_number"] == 1
    assert p1["content"] == "Check boundary"

    r2 = subprocess.run(
        [sys.executable, str(script), "ulysses", "--iteration", "2", "--max-iterations", "2", "--elapsed", "5.0", "--budget", "30.0", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r2.returncode == 0, r2.stderr
    p2 = json.loads(r2.stdout)
    assert p2["must_escalate"] is True


def test_sequential_thinking_mutation_hardening() -> None:
    """Mutation hardening: DTO immutability, era reset, exact boundaries, full OODA cycle, and beam/CLI paths."""
    from dataclasses import FrozenInstanceError
    from tools.reasoning.sequential_thinking_engine import (
        OODALoopSession,
        SequentialThinkingSession,
        UlyssesProtocolSession,
        beam_prune_branches,
        main,
    )

    with pytest.raises(ValueError, match="max_thought_chars"):
        SequentialThinkingSession(max_thought_chars=0)

    sess = SequentialThinkingSession(session_id="mh-1", max_thought_chars=20)
    with pytest.raises(ValueError, match="non-empty"):
        sess.record_thought(1, 1, "   ")
    with pytest.raises(ValueError, match=">= 1"):
        sess.record_thought(0, 1, "bad")
    with pytest.raises(ValueError, match=">= 1"):
        sess.record_thought(1, 0, "bad")

    step1 = sess.record_thought(2, 1, "x" * 20, next_thought_needed=False, beam_score=0.75)
    assert step1.total_thoughts == 2  # adjusted_total = max(1, 2)
    assert step1.to_dict()["beam_score"] == 0.75
    assert "score:0.750" in sess.export_markdown()
    with pytest.raises(FrozenInstanceError):
        step1.content = "mutated"  # type: ignore[misc]

    with pytest.raises(ValueError, match="branch_from_thought"):
        sess.record_thought(3, 3, "bad branch", branch_from_thought=99)

    new_era = sess.reset_era()
    assert new_era == 2 and sess.history == [] and sess.branches == {}

    # Ulysses exact boundaries & complete phase
    with pytest.raises(ValueError, match="max_iterations"):
        UlyssesProtocolSession(max_iterations=0)
    with pytest.raises(ValueError, match="time_budget_sec"):
        UlyssesProtocolSession(time_budget_sec=0.0)
    u = UlyssesProtocolSession(session_id="u-ok", max_iterations=1, time_budget_sec=10.0)
    with pytest.raises(ValueError, match="negative"):
        u.step(phase="execute", elapsed_sec=-1.0)
    res_complete = u.step(phase="complete", elapsed_sec=5.0, summary="done")
    assert res_complete.must_escalate is False and res_complete.phase == "complete"
    assert res_complete.to_dict()["iteration"] == 1
    with pytest.raises(FrozenInstanceError):
        res_complete.must_escalate = True  # type: ignore[misc]

    # Exact time boundary == time_budget_sec triggers escalate
    u_exact = UlyssesProtocolSession(session_id="u-ex", max_iterations=5, time_budget_sec=10.0)
    assert u_exact.step(phase="execute", elapsed_sec=10.0).must_escalate is True

    # OODA full 4-phase cycle wraparound & validation
    with pytest.raises(ValueError, match="min_evidence"):
        OODALoopSession(min_evidence=0)
    ooda = OODALoopSession(session_id="o-full", min_evidence=1)
    assert ooda.advance(["e1"], "h1")["phase"] == "orient"
    assert ooda.advance([], "h1")["phase"] == "decide"
    assert ooda.advance([])["phase"] == "act"
    wrap = ooda.advance([])
    assert wrap["phase"] == "observe" and wrap["cycle"] == 2
    assert len(wrap["active_hypotheses"]) == 1

    # Beam score fallback & beam_width validation
    with pytest.raises(ValueError, match="beam_width"):
        beam_prune_branches([{"id": "A", "score": 1.0}], beam_width=0)
    out = beam_prune_branches([{"id": "A", "score": 0.2}, {"id": "B", "score": 0.8}], beam_width=1)
    assert len(out) == 1 and out[0]["id"] == "B" and out[0]["beam_score"] == 0.8

    # Direct CLI main() branches
    assert main(["beam", "--candidates-json", '[{"id":"X","score":0.9}]', "--width", "1", "--json"]) == 0
    assert main(["beam", "--candidates-json", "not-json", "--json"]) == 1
    assert main([]) == 1

