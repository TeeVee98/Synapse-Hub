# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Verify calibrated peer review, idea novelty, and bounded experiment repair."""

from dataclasses import FrozenInstanceError, replace
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


MODULE = "tools.orchestration.peer_review_calibrator"
ROOT = Path(__file__).resolve().parents[1]
PATTERN_IDS = {
    "zeroshot", "fewshot", "cot", "meta-prompting", "consistency", "knowledge", "prompt_chaining", "tot",
    "rag", "art", "ape", "activeprompt", "dsp", "pal", "react", "reflexion", "multimodalcot", "graph",
}


@pytest.fixture
def engine():
    assert importlib.util.find_spec(MODULE) is not None, "Peer review module is unavailable"
    return importlib.import_module(MODULE)


def _review(engine, reviewer="a", overall=8, confidence=4, decision="Accept", weaknesses=()):
    return engine.PeerReviewRubricDTO(
        reviewer, 3, 3, 3, 3, 3, 3, 3, overall, confidence, decision, weaknesses=weaknesses,
    )


def test_peer_review_novelty_and_catalog(engine, tmp_path):
    """Positive ensemble calibration, duplicate ADR detection, and catalog coverage."""
    reviewers = (
        _review(engine, "a", 8, 4, weaknesses=("No replication",)),
        _review(engine, "b", 9, 5, weaknesses=("no replication", "Missing latency log")),
        _review(engine, "c", 2, 1, "Reject", weaknesses=("No control group",)),
    )
    meta = engine.CalibratedPeerReviewer().synthesize_meta_review(reviewers)
    assert meta.reviewer_count == 3
    assert meta.mean_overall == pytest.approx(19 / 3)
    assert meta.confidence_weighted_overall == pytest.approx(7.9)
    assert meta.calibrated_decision == "Accept"
    assert meta.dissent_detected
    assert meta.key_weaknesses == ("No replication", "Missing latency log", "No control group")
    with pytest.raises(FrozenInstanceError):
        meta.dissent_detected = False
    with pytest.raises(FrozenInstanceError):
        reviewers[0].overall = 9

    adr = tmp_path / "ADR-0001-sqlite-recovery.md"
    adr.write_text("# ADR-0001: SQLite checkpoint recovery\n\n## Context\nA durable journal restores pending transactions after failure.\n\n## Decision\nUse a local store.", encoding="utf-8")
    generator = engine.NoveltyCheckedIdeaGenerator(tmp_path)
    duplicate = generator.evaluate("SQLite checkpoint recovery", "A completely different overview")
    assert not duplicate.is_novel and duplicate.max_similarity == 1.0
    assert duplicate.closest_existing_id == "ADR-0001"
    assert "similarity" in duplicate.verdict_reason.lower()
    with pytest.raises(FrozenInstanceError):
        duplicate.is_novel = True
    summary_duplicate = generator.evaluate("Retry transaction notes", "A durable journal restores pending transactions after failure.")
    assert not summary_duplicate.is_novel
    novel = generator.evaluate("Spreadsheet color palette tokenizer", "Quantize hue channels for accessible charts.")
    assert novel.is_novel and novel.max_similarity == 0.0

    catalog = engine.load_prompt_patterns()
    assert {item["id"] for item in catalog["patterns"]} == PATTERN_IDS
    assert len(catalog["patterns"]) == 18
    assert all(item["when_to_use"] and item["source_path"] for item in catalog["patterns"])
    assert len(catalog["context_engineering"]) >= 4
    assert set(catalog["risk_mitigations"]) >= {
        "direct_injection", "indirect_injection", "prompt_leaking", "delimiter_jailbreak",
        "roleplay_obfuscation", "sycophancy_bias",
    }


def test_negative_review_ranges_and_conservative_decision(engine):
    calibrator = engine.CalibratedPeerReviewer()
    review = _review(engine)
    for field in ("originality", "quality", "clarity", "significance", "soundness", "presentation", "contribution"):
        for value in (0, 5):
            with pytest.raises(ValueError, match=field):
                calibrator.calibrate(replace(review, **{field: value}))
    for values in (
        {"reviewer_id": ""}, {"overall": 0}, {"overall": 11}, {"confidence": 0},
        {"confidence": 6}, {"confidence": True}, {"decision": "Maybe"},
    ):
        with pytest.raises(ValueError):
            calibrator.calibrate(replace(review, **values))
    clamped = calibrator.calibrate(replace(review, originality=8, overall=-3, confidence=0), clamp=True)
    assert (clamped.originality, clamped.overall, clamped.confidence, clamped.decision) == (4, 1, 1, "Reject")
    assert calibrator.calibrate(replace(review, overall=6)).decision == "Reject"
    assert calibrator.calibrate(replace(review, overall=7, confidence=3)).decision == "Accept"
    assert calibrator.calibrate(replace(review, confidence=2)).decision == "Reject"
    assert calibrator.calibrate(replace(review, soundness=1)).decision == "Reject"
    assert calibrator.calibrate(replace(review, overall=10, decision="Reject")).decision == "Reject"
    assert calibrator.calibrate(replace(review, overall=10, confidence=5, quality=4)).decision == "Accept"
    for options in ({"acceptance_threshold": 0}, {"acceptance_threshold": 11}, {"minimum_confidence": 0}, {"minimum_confidence": 6}):
        with pytest.raises(ValueError):
            engine.CalibratedPeerReviewer(**options)
    with pytest.raises(ValueError, match="review"):
        calibrator.synthesize_meta_review([])
    with pytest.raises(ValueError, match="unique"):
        calibrator.synthesize_meta_review([review, review])
    undecided = calibrator.synthesize_meta_review([review, replace(review, reviewer_id="b", decision="Reject")])
    assert undecided.calibrated_decision == "Reject" and undecided.dissent_detected
    assert not calibrator.synthesize_meta_review([review]).dissent_detected


def test_boundary_novelty_empty_archive_and_invalid_title(engine, tmp_path):
    generator = engine.NoveltyCheckedIdeaGenerator(tmp_path)
    result = generator.evaluate("New idea")
    assert result.is_novel and result.max_similarity == 0.0
    assert result.closest_existing_id is None
    with pytest.raises(ValueError, match="title"):
        generator.evaluate("  ")
    with pytest.raises(ValueError):
        engine.NoveltyCheckedIdeaGenerator(tmp_path, threshold=0.0)
    with pytest.raises(ValueError):
        engine.NoveltyCheckedIdeaGenerator(tmp_path, threshold=1.1)
    with pytest.raises(ValueError):
        engine.NoveltyCheckedIdeaGenerator(tmp_path, ngram_size=0)


def test_boundary_experiment_repairs_preserve_incumbent_and_stderr(engine):
    loop = engine.ExperimentRepairLoop(5)
    calls = []
    scores = iter((0.50, 0.45, 0.85))

    def execute(attempt, previous):
        calls.append((attempt, previous))
        if attempt == 1:
            raise subprocess.CalledProcessError(1, ["experiment"], stderr="fixture unavailable")
        return next(scores), f"diagnostic {attempt}"

    result = loop.run(execute, target_score=0.80)
    assert result.status == "TARGET_REACHED"
    assert result.best_score == 0.85
    assert len(result.attempts) == 4
    assert calls[0] == (1, None) and calls[1][1] == result.attempts[0]
    assert result.attempts[0].stderr == "fixture unavailable"
    assert result.attempts[0].score is None
    assert tuple(entry.best_score for entry in result.attempts) == (None, 0.50, 0.50, 0.85)
    with pytest.raises(FrozenInstanceError):
        result.best_score = 1.0
    with pytest.raises(FrozenInstanceError):
        result.attempts[0].stderr = ""

    exhausted = engine.ExperimentRepairLoop(99).run(lambda _i, _prev: (0.3, ""), target_score=1.0)
    assert exhausted.status == "EXHAUSTED" and len(exhausted.attempts) == 5
    with pytest.raises(ValueError, match="max_runs"):
        engine.ExperimentRepairLoop(0)
    with pytest.raises(ValueError, match="finite"):
        loop.run(lambda _i, _prev: (float("nan"), ""), target_score=1.0)


def test_cli_json_catalog_and_invalid_catalog_schema(tmp_path):
    command = [sys.executable, "-m", MODULE, "--json"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["pattern_count"] == 18
    assert {entry["id"] for entry in payload["catalog"]["patterns"]} == PATTERN_IDS
    invalid = tmp_path / "broken.json"
    invalid.write_text('{"patterns":null}', encoding="utf-8")
    negative = subprocess.run(command + ["--catalog", str(invalid)], cwd=ROOT, capture_output=True, text=True, check=False)
    assert negative.returncode == 2
    assert json.loads(negative.stdout)["error"]
