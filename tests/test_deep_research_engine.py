# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Verify offline research expansion, evidence usefulness, and source budgeting."""

from dataclasses import FrozenInstanceError
from datetime import date
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


MODULE = "tools.context.deep_research_engine"
ROOT = Path(__file__).resolve().parents[1]
QUERY = "SQLite WAL checkpoint interval"


@pytest.fixture
def engine():
    assert importlib.util.find_spec(MODULE) is not None, "Offline research module is unavailable"
    return importlib.import_module(MODULE)


def test_deep_research_rubric_and_budget(engine):
    """Positive direct evidence outranks filler, with bounded expansion and cited learning."""
    direct = engine.EvidenceChunk("direct", "https://db.example.edu/wal", "SQLite WAL checkpoint interval defaults to 1000 pages.")
    support = engine.EvidenceChunk("support", "https://db.example.org", "SQLite WAL supports 2 checkpoint modes.")
    filler = engine.EvidenceChunk("filler", "https://research.example.gov", "A look at the SQLite WAL checkpoint interval.")
    unrelated = engine.EvidenceChunk("unrelated", "https://music.example.edu", "A microphone samples audio at 48000 Hz.")
    rubric = engine.UsefulnessRubricFilter()
    assert tuple(rubric.score(QUERY, chunk).usefulness_level for chunk in (direct, support, filler, unrelated)) == (3, 2, 1, 0)
    assert rubric.score(QUERY, direct).rubric_score == 1.0
    assert rubric.score(QUERY, unrelated).rubric_score == 0.0
    assert rubric.score("", direct).usefulness_level == 0

    visited = []

    def search(query):
        visited.append(query)
        return [filler, unrelated, support, direct]

    fence = chr(96) * 3
    payload = f"Analysis\n{fence}json\n" + '{"queries":["WAL limits","WAL metrics","discard",],}' + f"\n{fence}"
    result = engine.DeepResearchTree().research(
        QUERY, search, depth=2, breadth=2, max_context_words=200,
        expand=lambda _query, _learnings: payload,
    )
    assert visited == [QUERY, "WAL limits", "WAL metrics"]
    assert result.visited_queries == tuple(visited)
    assert result.kept_chunks == result.learnings_count == 2
    assert result.words_used == sum(len(item.learning.split()) for item in result.learnings)
    assert result.words_used <= 200
    assert result.learnings[0].citations == (direct.source_url,)
    assert result.learnings[0].learning.endswith(f"[{direct.source_url}]")
    assert result.learnings[0].depth == 1
    assert result.learnings[0].query == QUERY
    for frozen, field in ((direct, "text"), (rubric.score(QUERY, direct), "text"), (result.learnings[0], "query"), (result, "words_used")):
        with pytest.raises(FrozenInstanceError):
            setattr(frozen, field, None)


def test_negative_query_payload_and_opt_in_gateway(engine):
    extract = engine.extract_queries
    assert extract('{"queries": [{"query":"With comma, ] intact"}, {"query":null}, "  valid  ", "VALID",],}') == (
        "With comma, ] intact", "valid",
    )
    assert extract('{"followUpQuestions": ["Related query"]}') == ("Related query",)
    assert extract('["First", "Second"]') == ("First", "Second")
    assert extract("### Follow-ups\n- First path\n2. Second path") == ("First path", "Second path")
    assert extract('{"queries":null}') == ()
    assert extract("broken text with no query rows") == ()

    chunk = engine.EvidenceChunk("id", "https://example.edu", "Related text")
    calls = []
    scorer = lambda query, evidence: calls.append((query, evidence.chunk_id)) or 3
    assert engine.UsefulnessRubricFilter(gateway=scorer).score("other", chunk).usefulness_level == 0
    assert calls == []
    assert engine.UsefulnessRubricFilter(gateway=scorer, allow_gateway=True).score("other", chunk).usefulness_level == 3
    assert calls == [("other", "id")]
    with pytest.raises(ValueError, match="gateway"):
        engine.UsefulnessRubricFilter(allow_gateway=True)
    with pytest.raises(ValueError, match="0 through 3"):
        engine.UsefulnessRubricFilter(gateway=lambda _q, _e: True, allow_gateway=True).score("other", chunk)


def test_source_curator_credibility_recency_and_evidence_density(engine):
    curator = engine.SourceCurator()
    make = engine.EvidenceChunk
    stale = make("stale", "https://research.example.edu", "A verified 1 second rate.", date(2022, 1, 1))
    strong = make("strong", "https://data.example.gov", "The latency is 1 second and 50% of 200 samples.", date(2024, 1, 1))
    weak = make("weak", "https://results.example.edu", "No evidence included.", date(2024, 1, 1))
    unknown = make("unknown", "https://data.example.gov.invalid", "Measures 2 seconds.", date(2026, 1, 1))
    assert tuple(item.chunk_id for item in curator.rank([unknown, weak, stale, strong])) == ("strong", "weak", "stale", "unknown")
    assert curator.credibility_score("https://host.example.org") > curator.credibility_score("http://host.example.com")
    assert curator.credibility_score("https://user@db.example.edu") == 0.0
    assert curator.credibility_score("https://[invalid") == 0.0
    assert curator.credibility_score("file:///report") == 0.0
    assert curator.credibility_score("https://bad host.example.edu") == 0.0


def test_boundary_search_caps_budget_and_deduplication(engine):
    tree = engine.DeepResearchTree()
    calls = []
    search = lambda query: calls.append(query) or ()
    assert tree.research("root", search, depth=0).visited_queries == ()
    assert tree.research("root", search, breadth=0).visited_queries == ()
    assert tree.research("root", search, max_context_words=0).visited_queries == ()
    assert tree.research("  ", search).visited_queries == ()
    assert calls == []
    with pytest.raises(ValueError, match="non-negative"):
        tree.research("root", search, depth=-1)
    with pytest.raises(ValueError, match="queries"):
        tree.research("root", search, expand=lambda _query, _notes: None)
    calls.clear()
    result = tree.research(
        "root", search, depth=100, breadth=100,
        expand=lambda query, _notes: [query.upper(), *(f"{query}-{idx}" for idx in range(8))],
    )
    assert len(result.visited_queries) == 1 + 5 + 25 + 125
    assert len(set(result.visited_queries)) == len(calls)
    assert result.learnings == () and result.words_used == 0
    assert len(tree.research("root", search, depth=2, breadth=2).visited_queries) == 3

    evidence = engine.EvidenceChunk("one", "https://example.com", "SQLite uses 2 modes.")
    oversize = engine.EvidenceChunk("huge", "https://example.edu", "SQLite has 1 mode " + "word " * engine.MAX_CONTEXT_WORDS)
    result = tree.research("SQLite", lambda _: (oversize, evidence), depth=1, max_context_words=10**6)
    assert result.kept_chunks == 1
    assert result.words_used == 5
    assert not tree.research("SQLite", lambda _: (evidence,), depth=1, max_context_words=4).learnings
    assert tree.research("SQLite", lambda _: (evidence,), depth=1, max_context_words=5).words_used == 5


def test_cli_json_offline_research_and_invalid_null_chunk():
    args = [sys.executable, "-m", MODULE, "--json"]
    payload = {
        "query": QUERY, "depth": 1, "max_context_words": 30,
        "chunks": [{"chunk_id": "db", "source_url": "https://example.edu/db", "text": "SQLite WAL checkpoint interval defaults to 1000 pages."}],
    }
    completed = subprocess.run(args, cwd=ROOT, input=json.dumps(payload), capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["learnings_count"] == 1
    assert output["learnings"][0]["citations"] == ["https://example.edu/db"]
    invalid = subprocess.run(args, cwd=ROOT, input=json.dumps(payload | {"chunks": [None]}), capture_output=True, text=True, check=False)
    assert invalid.returncode == 2
    assert json.loads(invalid.stdout)["error"]


def test_negative_curator_rejects_bad_scheme_or_missing_host_and_scores_transport(engine):
    score = engine.SourceCurator.credibility_score
    assert score("ftp://archive.example.edu/report") == 0.0
    assert score("https:///missing-host") == 0.0
    assert score("https://source.example.org/reference") == 0.75
    assert score("https://example.com/reference") == 0.55
    assert score("http://source.example.org/reference") == 0.35
    assert score("http://source.example.gov/reference") == 0.35
