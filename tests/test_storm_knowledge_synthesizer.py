# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Verify offline STORM perspectives and citation integrity."""

from dataclasses import FrozenInstanceError
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.context.deep_research_engine import ResearchLearningDTO


MODULE = "tools.design.storm_knowledge_synthesizer"
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def engine():
    assert importlib.util.find_spec(MODULE) is not None, "STORM synthesis module is unavailable"
    return importlib.import_module(MODULE)


def test_storm_mindmap_and_citation_integrity(engine):
    """Positive hierarchical organization preserves verified citation IDs."""
    knowledge = engine.KnowledgeBase("SQLite QA")
    for source_id in range(1, 5):
        knowledge.register_source(source_id, f"https://example.edu/s{source_id}")
    assert knowledge.insert_from_outline_string("# SQLite QA\n## Details\n### Storage\n## Empty\n## Operations") == 4
    knowledge.insert_information(("Details", "Storage"), "SQLite writes to the journal [1].", citation_ids=(2,))
    knowledge.insert_information(("Operations",), "Recover state [3] and validate results [4].")
    assert knowledge.reorganize() == (1, 1)
    assert knowledge.reorganize() == (0, 0)
    report = knowledge.to_report()
    assert report == knowledge.to_report()
    assert "## Details / Storage" in report
    assert "## Empty" not in report
    assert "SQLite writes to the journal [1]. [2]" in report
    assert all(f"[{source_id}] https://example.edu/s{source_id}" in report for source_id in range(1, 5))
    root, storage, ops = knowledge.to_nodes()
    assert root.title == "SQLite QA" and root.children_ids == (storage.node_id, ops.node_id)
    assert storage.path == ("SQLite QA", "Details / Storage")
    assert storage.citation_ids == (1, 2)
    assert storage.children_ids == ()
    with pytest.raises(FrozenInstanceError):
        storage.title = "Edited"

    knowledge.insert_information(("Operations",), "Unsupported [99].")
    with pytest.raises(ValueError, match=r"99"):
        knowledge.to_report()


def test_negative_outline_sources_and_inline_markers_are_rejected_atomically(engine):
    knowledge = engine.KnowledgeBase("Topic")
    with pytest.raises(ValueError, match="Duplicate"):
        knowledge.insert_from_outline_string("# Topic\n## A\n## a")
    assert tuple(item.title for item in knowledge.to_nodes()) == ("Topic",)
    with pytest.raises(ValueError, match="skips"):
        knowledge.insert_from_outline_string("# Topic\n### Unattached")
    with pytest.raises(ValueError, match="section"):
        knowledge.insert_information(("Missing",), "Unsupported.")
    for invalid_id, source in ((0, "https://example.edu"), (True, "https://example.edu"), (1, "file:///tmp/document")):
        with pytest.raises(ValueError):
            knowledge.register_source(invalid_id, source)
    knowledge.register_source(1, "https://example.edu")
    knowledge.register_source(1, "https://example.edu")
    with pytest.raises(ValueError, match="registered"):
        knowledge.register_source(1, "https://other.example.edu")
    knowledge.insert_information((), r"Literal \[99] and valid claim [1].")
    assert "valid claim [1]" in knowledge.to_report()
    knowledge.insert_information((), "Out of range [" + "9" * 35 + "].")
    with pytest.raises(ValueError, match="citation"):
        knowledge.to_report()


def test_boundary_empty_outline_and_citation_in_title(engine):
    knowledge = engine.KnowledgeBase("Root")
    assert knowledge.insert_from_outline_string("") == 0
    assert knowledge.reorganize() == (0, 0)
    assert knowledge.to_report() == "# Root\n"
    assert knowledge.to_nodes()[0].citation_ids == ()
    assert knowledge.insert_from_outline_string("## Checkpoints [2]") == 1
    assert knowledge.reorganize() == (0, 0)
    with pytest.raises(ValueError, match="2"):
        knowledge.to_report()
    knowledge.register_source(2, "https://example.edu")
    assert "## Checkpoints [2]" in knowledge.to_report()
    with pytest.raises(ValueError, match="topic"):
        engine.PersonaGenerator().generate("")


def test_positive_personas_interview_and_research_learning_bridge(engine):
    topic = "SQLite"
    sources = (
        engine.InterviewSource(1, "https://example.edu/access", "SQLite access controls protect data."),
        engine.InterviewSource(2, "https://example.edu/storage", "SQLite storage preserves state and transactions."),
        engine.InterviewSource(3, "https://example.edu/boundaries", "SQLite boundary inputs include null and empty values."),
        engine.InterviewSource(4, "https://example.edu/uptime", "SQLite reliability practices cover recovery and availability."),
    )
    personas = engine.PersonaGenerator().generate(topic)
    assert tuple(persona.name for persona in personas) == (
        "Security Auditor", "State/DB Architect", "Boundary QA", "Reliability SRE", "End-User Advocate",
    )
    assert len({persona.focus for persona in personas}) == 5
    interview = engine.SimulatedExpertInterview().conduct(topic, personas, sources)
    assert len(interview) == 5
    for turn, source in zip(interview[:4], sources, strict=True):
        assert topic in turn.question
        assert turn.citation_ids == (source.source_id,)
        assert turn.answer == f"{source.excerpt} [{source.source_id}]"
    for frozen, field in ((personas[0], "name"), (sources[0], "url"), (interview[0], "answer")):
        with pytest.raises(FrozenInstanceError):
            setattr(frozen, field, "changed")
    assert all(not turn.citation_ids for turn in engine.SimulatedExpertInterview().conduct(topic, personas, ()))

    result = engine.StormKnowledgeSynthesizer().synthesize(topic, sources)
    assert result.persona_count == 5 and result.node_count == 6
    assert result.verified_citations == 4
    assert result.turns == interview
    with pytest.raises(FrozenInstanceError):
        result.verified_citations = 0
    first = sources[0]
    learning = ResearchLearningDTO(1, topic, f"{first.excerpt} [{first.url}]", (first.url,), 3)
    bridged = engine.StormKnowledgeSynthesizer().synthesize_from_learnings(topic, [learning, learning])
    assert bridged.verified_citations == 1
    assert f"[1] {first.url}" in bridged.report
    assert f"{first.excerpt} [1]" in bridged.report


def test_cli_json_synthesizes_cited_notes_and_rejects_null_source():
    command = [sys.executable, "-m", MODULE, "--json"]
    data = {
        "topic": "SQLite", "outline": "# SQLite\n## Findings",
        "sources": [{"source_id": 1, "url": "https://example.edu", "excerpt": "SQLite limits concurrent writes."}],
    }
    result = subprocess.run(command, cwd=ROOT, input=json.dumps(data), capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["persona_count"] == 5 and payload["node_count"] == 2
    assert payload["verified_citations"] == 1
    assert "## Findings" in payload["report"]
    invalid = subprocess.run(
        command, cwd=ROOT, input=json.dumps(data | {"sources": [None]}),
        capture_output=True, text=True, check=False,
    )
    assert invalid.returncode == 2 and json.loads(invalid.stdout)["error"]
