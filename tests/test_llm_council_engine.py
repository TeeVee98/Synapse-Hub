#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""4-Scenario Verification Battery for M4: Double-Blind LLMCouncilEngine, MARS & PlanSearch."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


def test_double_blind_council_ranking_positive() -> None:
    """Positive: anonymize candidates, parse peer rankings, compute aggregate rank, and run PlanSearch."""
    from tools.orchestration.llm_council_engine import (
        CouncilCandidateDTO,
        LLMCouncilEngine,
        plansearch_combine_observations,
    )

    eng = LLMCouncilEngine(min_verification_passes=2)
    candidates = [
        CouncilCandidateDTO("gemini-4-neon", "gemini", "Use SQLite WAL with optimistic row_version."),
        CouncilCandidateDTO("claude-opus-5.5", "anthropic", "Use SQLite WAL, advisory file lock, and JSONL snapshots."),
        CouncilCandidateDTO("gpt-6.2-astra", "openai", "Use in-memory dictionary without disk sync."),
    ]
    label_map, prompt = eng.build_anonymized_ranking_prompt("Design task graph persistence", candidates)
    assert label_map == {
        "Response A": "gemini-4-neon",
        "Response B": "claude-opus-5.5",
        "Response C": "gpt-6.2-astra",
    }
    assert "gemini-4-neon" not in prompt
    assert "Response A" in prompt and "Response B" in prompt and "Response C" in prompt

    peer_reviews = [
        "Response B handles crash recovery best.\nFINAL RANKING:\n1. Response B\n2. Response A\n3. Response C",
        "Response B is most complete.\nFINAL RANKING:\n1. Response B\n2. Response A\n3. Response C",
        "Response A is lean.\nFINAL RANKING:\n1. Response A\n2. Response B\n3. Response C",
    ]
    verdict = eng.adjudicate_offline("Design task graph persistence", candidates, peer_reviews)
    assert verdict.winner_model == "claude-opus-5.5"
    assert verdict.consensus_passes == 2
    assert verdict.offline_mode is True
    assert verdict.aggregate_rankings[0][0] == "claude-opus-5.5"
    assert verdict.aggregate_rankings[0][1] == pytest.approx(1.3333, rel=1e-3)
    assert "claude-opus-5.5" in verdict.chairman_synthesis

    # PlanSearch observation-first combinations
    combos = plansearch_combine_observations(
        ["WAL avoids read blocks", "CAS prevents lost updates", "JSONL survives DB corruption"],
        max_pairs=3,
    )
    assert len(combos) == 3
    assert all(len(c["observations"]) == 2 for c in combos)


def test_double_blind_council_negative_malformed_and_insufficient() -> None:
    """Negative: malformed peer review skipped cleanly; <2 candidates rejected."""
    from tools.orchestration.llm_council_engine import CouncilCandidateDTO, LLMCouncilEngine

    eng = LLMCouncilEngine()
    with pytest.raises(ValueError, match="At least 2"):
        eng.adjudicate_offline(
            "Single candidate",
            [CouncilCandidateDTO("m1", "gemini", "only one")],
            ["FINAL RANKING:\n1. Response A"],
        )

    candidates = [
        CouncilCandidateDTO("m1", "gemini", "Option 1"),
        CouncilCandidateDTO("m2", "anthropic", "Option 2"),
    ]
    peer_reviews = [
        "Garbage output without any ranking block at all",
        "FINAL RANKING:\n1. Response B\n2. Response A",
    ]
    verdict = eng.adjudicate_offline("Pick best", candidates, peer_reviews)
    assert verdict.winner_model == "m2"
    assert verdict.consensus_passes == 1


def test_double_blind_council_boundary_tie_and_empty_observations() -> None:
    """Boundary: exact tie broken deterministically by model order; empty observations returns []."""
    from tools.orchestration.llm_council_engine import (
        CouncilCandidateDTO,
        LLMCouncilEngine,
        plansearch_combine_observations,
    )

    assert plansearch_combine_observations([]) == []
    assert plansearch_combine_observations(["single obs"])[0]["observations"] == ["single obs"]

    eng = LLMCouncilEngine()
    candidates = [
        CouncilCandidateDTO("alpha-model", "gemini", "Draft A"),
        CouncilCandidateDTO("beta-model", "openai", "Draft B"),
    ]
    peer_reviews = [
        "FINAL RANKING:\n1. Response A\n2. Response B",
        "FINAL RANKING:\n1. Response B\n2. Response A",
    ]
    verdict = eng.adjudicate_offline("Tie test", candidates, peer_reviews)
    assert verdict.aggregate_rankings[0][1] == verdict.aggregate_rankings[1][1] == pytest.approx(1.5)
    assert verdict.winner_model == "alpha-model"


def test_llm_council_cli_json_flags(tmp_path: Path) -> None:
    """CLI Contract: offline council --candidates-file --json exits 0 with structured verdict."""
    fixture = tmp_path / "council_input.json"
    fixture.write_text(
        json.dumps(
            {
                "query": "Choose test retry policy",
                "candidates": [
                    {"model_id": "m1", "provider_family": "gemini", "response_text": "Cap at 2 retries"},
                    {"model_id": "m2", "provider_family": "anthropic", "response_text": "Infinite retry loop"},
                ],
                "peer_reviews": [
                    "FINAL RANKING:\n1. Response A\n2. Response B",
                    "FINAL RANKING:\n1. Response A\n2. Response B",
                ],
            }
        ),
        encoding="utf-8",
    )
    script = Path(__file__).resolve().parents[1] / "tools" / "orchestration" / "llm_council_engine.py"
    res = subprocess.run(
        [sys.executable, str(script), "adjudicate", "--candidates-file", str(fixture), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["winner_model"] == "m1"
    assert data["consensus_passes"] == 2


def test_llm_council_mutation_hardening() -> None:
    """Mutation hardening: DTO immutability, ranking parser bleed/fallback, MARS status, PlanSearch cap & CLI."""
    from dataclasses import FrozenInstanceError
    from tools.orchestration.llm_council_engine import (
        CouncilCandidateDTO,
        LLMCouncilEngine,
        main,
        parse_ranking_from_text,
        plansearch_combine_observations,
    )

    c1 = CouncilCandidateDTO("m1", "gemini", "Draft 1")
    c2 = CouncilCandidateDTO("m2", "anthropic", "Draft 2")
    assert c1.to_dict()["model_id"] == "m1"
    with pytest.raises(FrozenInstanceError):
        c1.model_id = "tampered"  # type: ignore[misc]

    # Pre-header mentions of Response A must NOT leak when FINAL RANKING is missing or after it
    assert parse_ranking_from_text("1. Response A\n2. Response B", ["Response A", "Response B"]) == []
    assert parse_ranking_from_text("Response A is mentioned but no header exists", ["Response A", "Response B"]) == []
    assert parse_ranking_from_text("", ["Response A", "Response B"]) == []
    # Duplicate and unknown labels must be ignored in both numbered and inline modes
    dup_numbered = parse_ranking_from_text(
        "FINAL RANKING:\n1. Response B\n2. Response B\n3. Response Z\n4. Response A",
        ["Response A", "Response B"],
    )
    assert dup_numbered == ["Response B", "Response A"]
    inline_parsed = parse_ranking_from_text(
        "Response A was verbose.\nFINAL RANKING:\nResponse B beats Response B and Response Z and Response A",
        ["Response A", "Response B"],
    )
    assert inline_parsed == ["Response B", "Response A"]

    # Engine validation & MARS status labels
    with pytest.raises(ValueError, match="min_verification_passes"):
        LLMCouncilEngine(min_verification_passes=0)
    eng = LLMCouncilEngine(min_verification_passes=2)
    with pytest.raises(ValueError, match="query"):
        eng.build_anonymized_ranking_prompt("   ", [c1, c2])

    v_below = eng.adjudicate_offline("Q", [c1, c2], ["FINAL RANKING:\n1. Response B\n2. Response A"])
    assert "BELOW_MARS_THRESHOLD" in v_below.chairman_synthesis
    assert v_below.to_dict()["winner_model"] == "m2"
    with pytest.raises(FrozenInstanceError):
        v_below.winner_model = "m1"  # type: ignore[misc]

    v_ok = eng.adjudicate_offline(
        "Q",
        [c1, c2],
        [
            "FINAL RANKING:\n1. Response B\n2. Response A",
            "FINAL RANKING:\n1. Response B\n2. Response A",
        ],
    )
    assert "CONSENSUS_VERIFIED" in v_ok.chairman_synthesis
    assert v_ok.aggregate_rankings[1][1] == pytest.approx(2.0)

    # PlanSearch max_pairs truncation & whitespace filtering
    combos = plansearch_combine_observations(["obs1", "   ", "obs2", "obs3", "obs4"], max_pairs=2)
    assert len(combos) == 2
    assert combos[0]["combo_id"] == "PS-1" and combos[1]["combo_id"] == "PS-2"

    # CLI direct main() plansearch, required args, & error output assertions
    import io
    from contextlib import redirect_stdout

    with pytest.raises(SystemExit):
        main(["adjudicate"])
    with pytest.raises(SystemExit):
        main(["plansearch"])

    assert main(["plansearch", "--observation", "o1", "--observation", "o2", "--max-pairs", "1", "--json"]) == 0
    buf_json = io.StringIO()
    with redirect_stdout(buf_json):
        assert main(["adjudicate", "--candidates-file", "/nonexistent/missing.json", "--json"]) == 1
    assert json.loads(buf_json.getvalue())["ok"] is False

    buf_text = io.StringIO()
    with redirect_stdout(buf_text):
        assert main(["adjudicate", "--candidates-file", "/nonexistent/missing.json"]) == 1
    assert buf_text.getvalue().startswith("Error:")
    assert main([]) == 1

