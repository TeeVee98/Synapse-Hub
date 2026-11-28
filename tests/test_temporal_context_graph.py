# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""4-scenario verification suite for M1: TemporalContextGraph & AssociativeMemory bridge."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from tools.reasoning.associative_memory import AssociativeMemory
from tools.reasoning.temporal_context_graph import (
    BiTemporalEdgeDTO,
    CommunitySummaryDTO,
    EpisodeRecordDTO,
    TemporalContextGraph,
    _format_utc,
    _parse_iso_strict,
)


def test_bitemporal_invalidation_and_communities(tmp_path: Path) -> None:
    """Positive scenario: episode provenance, contradiction invalidation, as_of queries, communities, bridge."""
    db_path = str(tmp_path / "temporal.db")
    with TemporalContextGraph(db_path=db_path) as graph:
        ep1 = graph.add_episode(
            source="deploy_log",
            content="auth_service uses token_v1",
            reference_time="2026-01-10T00:00:00Z",
            facts=[("auth_service", "uses_protocol", "token_v1", "Auth uses token_v1")],
        )
        assert isinstance(ep1, EpisodeRecordDTO)
        assert ep1.source == "deploy_log"
        assert "auth_service" in ep1.entity_ids
        assert "token_v1" in ep1.entity_ids

        ep2 = graph.add_episode(
            source="deploy_log",
            content="auth_service upgraded to token_v2",
            reference_time="2026-02-10T00:00:00Z",
            facts=[("auth_service", "uses_protocol", "token_v2", "Auth upgraded to token_v2")],
        )
        assert ep2.episode_id != ep1.episode_id

        # Historical fact must be invalidated non-destructively (not deleted)
        all_edges = graph.list_edges(include_invalid=True)
        assert len(all_edges) == 2
        v1_edge = next(e for e in all_edges if e.target_id == "token_v1")
        v2_edge = next(e for e in all_edges if e.target_id == "token_v2")
        assert isinstance(v1_edge, BiTemporalEdgeDTO)
        assert v1_edge.invalid_at == "2026-02-10T00:00:00+00:00"
        assert v1_edge.expired_at is not None
        assert v1_edge.episode_ids == (ep1.episode_id,)
        assert v2_edge.invalid_at is None
        assert v2_edge.expired_at is None
        assert v2_edge.episode_ids == (ep2.episode_id,)

        # Point-in-time as_of queries
        res_t1 = graph.query_as_of(
            query="auth_service",
            as_of="2026-01-15T00:00:00Z",
            mode="local",
        )
        assert len(res_t1["edges"]) == 1
        assert res_t1["edges"][0]["target_id"] == "token_v1"

        res_t2 = graph.query_as_of(
            query="auth_service",
            as_of="2026-02-15T00:00:00Z",
            mode="local",
        )
        assert len(res_t2["edges"]) == 1
        assert res_t2["edges"][0]["target_id"] == "token_v2"

        # Add a second disconnected cluster for GraphRAG community detection
        graph.add_episode(
            source="billing_spec",
            content="checkout_api calls payment_gateway and invoice_db",
            reference_time="2026-02-11T00:00:00Z",
            facts=[
                ("checkout_api", "calls", "payment_gateway", "Checkout calls payment"),
                ("payment_gateway", "writes", "invoice_db", "Payment writes invoice"),
            ],
        )
        communities = graph.rebuild_communities(as_of="2026-02-15T00:00:00Z")
        assert len(communities) == 2
        assert all(isinstance(c, CommunitySummaryDTO) for c in communities)
        member_sets = [set(c.member_ids) for c in communities]
        assert {"auth_service", "token_v2"} in member_sets
        assert {"checkout_api", "payment_gateway", "invoice_db"} in member_sets
        assert all(c.modularity_weight > 0.0 for c in communities)

        global_res = graph.query_as_of(query="payment", as_of="2026-02-15T00:00:00Z", mode="global")
        assert global_res["mode"] == "global"
        assert len(global_res["communities"]) >= 1
        assert "payment_gateway" in global_res["communities"][0]["summary_text"]

        hybrid_res = graph.query_as_of(query="auth_service", as_of="2026-02-15T00:00:00Z", mode="hybrid")
        assert hybrid_res["mode"] == "hybrid"
        assert len(hybrid_res["edges"]) == 1
        assert len(hybrid_res["communities"]) >= 1

        # AssociativeMemory optional bridge
        with AssociativeMemory(db_path=str(tmp_path / "assoc.db")) as assoc:
            assoc.record_node("locator_login", "locator", {"role": "button"})
            assoc.record_node("login_page", "page", {"path": "pages/login.py"})
            assoc.record_association("locator_login", "login_page", "belongs_to", weight=0.9)
            sync_report = assoc.sync_to_temporal_graph(graph, reference_time="2026-03-01T00:00:00Z")
            assert sync_report["synced_edges"] == 1
            assert sync_report["episode_id"].startswith("ep_")

        post_sync = graph.query_as_of(query="locator_login", as_of="2026-03-02T00:00:00Z", mode="local")
        assert any(e["target_id"] == "login_page" for e in post_sync["edges"])


def test_bitemporal_negative_validation(tmp_path: Path) -> None:
    """Negative scenario: rejects invalid timestamps, empty sources, malformed facts, unknown modes."""
    with TemporalContextGraph(db_path=str(tmp_path / "neg.db")) as graph:
        with pytest.raises(ValueError, match="source"):
            graph.add_episode(source="   ", content="x", reference_time="2026-01-01T00:00:00Z", facts=[])

        with pytest.raises(ValueError, match="ISO-8601"):
            graph.add_episode(source="log", content="x", reference_time="not-a-date", facts=[])

        with pytest.raises(ValueError, match="entity"):
            graph.add_episode(
                source="log",
                content="bad fact",
                reference_time="2026-01-01T00:00:00Z",
                facts=[("", "uses", "v1", "empty source")],
            )

        with pytest.raises(ValueError, match="mode"):
            graph.query_as_of(query="x", as_of="2026-01-01T00:00:00Z", mode="invalid_mode")  # type: ignore[arg-type]


def test_bitemporal_boundary_intervals_and_empty_graph(tmp_path: Path) -> None:
    """Boundary scenario: half-open [valid_at, invalid_at) boundaries and empty/singleton graphs."""
    with TemporalContextGraph(db_path=str(tmp_path / "bound.db")) as graph:
        # Empty graph
        assert graph.rebuild_communities() == []
        empty_res = graph.query_as_of(query="anything", as_of="2026-01-01T00:00:00Z", mode="hybrid")
        assert empty_res["edges"] == []
        assert empty_res["communities"] == []

        # Exact boundary [valid_at, invalid_at)
        graph.add_episode(
            source="s1",
            content="e1",
            reference_time="2026-05-01T00:00:00Z",
            facts=[("svc", "tier", "bronze", "Initial tier")],
        )
        graph.add_episode(
            source="s2",
            content="e2",
            reference_time="2026-05-10T00:00:00Z",
            facts=[("svc", "tier", "gold", "Upgraded tier")],
        )

        # Before first valid_at -> empty
        before = graph.query_as_of(query="svc", as_of="2026-04-30T23:59:59Z", mode="local")
        assert before["edges"] == []

        # Exactly at valid_at of first fact -> bronze visible
        at_t1 = graph.query_as_of(query="svc", as_of="2026-05-01T00:00:00Z", mode="local")
        assert [e["target_id"] for e in at_t1["edges"]] == ["bronze"]

        # Exactly at invalid_at of bronze (== valid_at of gold) -> only gold visible
        at_t2 = graph.query_as_of(query="svc", as_of="2026-05-10T00:00:00Z", mode="local")
        assert [e["target_id"] for e in at_t2["edges"]] == ["gold"]

        # Re-asserting the identical target does not duplicate or self-invalidate
        graph.add_episode(
            source="s3",
            content="e3",
            reference_time="2026-05-11T00:00:00Z",
            facts=[("svc", "tier", "gold", "Confirmed tier")],
        )
        at_t3 = graph.query_as_of(query="svc", as_of="2026-05-12T00:00:00Z", mode="local")
        assert len(at_t3["edges"]) == 1
        assert at_t3["edges"][0]["target_id"] == "gold"
        assert len(at_t3["edges"][0]["episode_ids"]) == 2


def test_bitemporal_cli_json_contract(tmp_path: Path) -> None:
    """CLI scenario: add-episode, communities, query, and stats with --json."""
    db_file = tmp_path / "cli_temporal.db"
    worktree_root = Path(__file__).resolve().parents[1]
    script = str(worktree_root / "tools" / "reasoning" / "temporal_context_graph.py")

    facts_json = json.dumps([["api_v1", "depends_on", "db_primary", "API depends on primary DB"]])
    r1 = subprocess.run(
        [
            sys.executable,
            script,
            "--db-path",
            str(db_file),
            "add-episode",
            "--source",
            "ci_run",
            "--content",
            "Recorded API dependency",
            "--reference-time",
            "2026-06-01T00:00:00Z",
            "--facts-json",
            facts_json,
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r1.returncode == 0, r1.stderr
    p1 = json.loads(r1.stdout)
    assert p1["status"] == "ok"
    assert p1["episode"]["source"] == "ci_run"

    r2 = subprocess.run(
        [
            sys.executable,
            script,
            "--db-path",
            str(db_file),
            "communities",
            "--as-of",
            "2026-06-02T00:00:00Z",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r2.returncode == 0, r2.stderr
    p2 = json.loads(r2.stdout)
    assert p2["community_count"] == 1

    r3 = subprocess.run(
        [
            sys.executable,
            script,
            "--db-path",
            str(db_file),
            "query",
            "--query",
            "api_v1",
            "--as-of",
            "2026-06-02T00:00:00Z",
            "--mode",
            "hybrid",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r3.returncode == 0, r3.stderr
    p3 = json.loads(r3.stdout)
    assert len(p3["edges"]) == 1
    assert p3["edges"][0]["target_id"] == "db_primary"


def test_bitemporal_pragmas_timezones_and_dto_immutability(tmp_path: Path) -> None:
    """Hardening scenario: verifies SQLite WAL/timeout/FK pragmas, timezone normalization, and frozen DTOs."""
    from datetime import datetime, timedelta, timezone

    # Empty/whitespace & non-string timestamp rejection
    with pytest.raises(ValueError, match="non-empty"):
        _parse_iso_strict("   ")
    with pytest.raises(ValueError, match="non-empty"):
        _parse_iso_strict(None)  # type: ignore[arg-type]

    # Naive datetime gets UTC; non-UTC offset converts cleanly to UTC (kills tzinfo is/is-not mutants)
    naive_dt = _parse_iso_strict("2026-01-10T05:00:00")
    assert naive_dt.tzinfo == timezone.utc
    assert naive_dt.hour == 5
    offset_dt = _parse_iso_strict("2026-01-10T07:00:00+02:00")
    assert offset_dt.tzinfo == timezone.utc
    assert offset_dt.hour == 5

    # _format_utc handles both naive and offset datetimes properly
    assert _format_utc(datetime(2026, 1, 10, 5, 0, 0)) == "2026-01-10T05:00:00+00:00"
    plus2 = timezone(timedelta(hours=2))
    assert _format_utc(datetime(2026, 1, 10, 7, 0, 0, tzinfo=plus2)) == "2026-01-10T05:00:00+00:00"

    # File-backed DB enforces WAL, busy_timeout=5000, synchronous=NORMAL(1), foreign_keys=ON(1)
    db_file = str(tmp_path / "pragmas.db")
    with TemporalContextGraph(db_path=db_file) as g:
        assert g._is_memory is False
        assert g.conn.execute("PRAGMA journal_mode;").fetchone()[0].lower() == "wal"
        assert int(g.conn.execute("PRAGMA busy_timeout;").fetchone()[0]) == 5000
        assert int(g.conn.execute("PRAGMA synchronous;").fetchone()[0]) == 1
        assert int(g.conn.execute("PRAGMA foreign_keys;").fetchone()[0]) == 1

        ep = g.add_episode("src", "c", "2026-01-01T00:00:00Z", [("a", "rel", "b", "fact")])
        edge = g.list_edges()[0]
        comm = g.rebuild_communities("2026-01-02T00:00:00Z")[0]

        with pytest.raises(FrozenInstanceError):
            ep.source = "mutated"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            edge.fact = "mutated"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            comm.summary_text = "mutated"  # type: ignore[misc]

    # Memory DB and auto_wal=False modes
    with TemporalContextGraph(db_path=":memory:", auto_wal=True) as mem_g:
        assert mem_g._is_memory is True
        assert mem_g.conn.execute("PRAGMA journal_mode;").fetchone()[0].lower() == "memory"

    no_wal_file = str(tmp_path / "nowal.db")
    with TemporalContextGraph(db_path=no_wal_file, auto_wal=False) as nw_g:
        assert nw_g.conn.execute("PRAGMA journal_mode;").fetchone()[0].lower() != "wal"
