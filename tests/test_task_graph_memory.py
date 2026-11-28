#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""4-Scenario Verification Battery for M1: TaskGraphMemory & project_state bridge."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


def test_task_graph_transitive_ready_positive(tmp_path: Path) -> None:
    """Positive: A blocks B blocks C -> closing A unblocks B while C stays blocked."""
    from tools.core.task_graph_memory import TaskGraphMemory

    db_path = tmp_path / ".synapse" / "task_graph.db"
    mem = TaskGraphMemory(db_path=db_path)
    try:
        a = mem.add_task("T-A", "Bootstrap schema", complexity_score=3, verification_criteria=["pytest -q"])
        b = mem.add_task("T-B", "Build engine", complexity_score=7)
        c = mem.add_task("T-C", "Wire CLI", complexity_score=4)
        assert a.row_version == 1
        assert b.complexity_score == 7

        mem.add_edge("T-A", "T-B", "blocks")
        mem.add_edge("T-B", "T-C", "blocks")
        mem.add_edge("T-C", "T-A", "related")  # non-blocking edge allowed

        ready_initial = mem.get_ready_tasks()
        assert [t.task_id for t in ready_initial] == ["T-A"]

        node_b = mem.get_task("T-B")
        assert node_b is not None
        assert node_b.is_blocked is True
        assert node_b.blocking_ids == ("T-A",)

        closed_a = mem.update_status("T-A", "done", expected_version=a.row_version)
        assert closed_a.status == "done"
        assert closed_a.row_version == 2

        ready_after_a = mem.get_ready_tasks()
        assert [t.task_id for t in ready_after_a] == ["T-B"]
        node_c = mem.get_task("T-C")
        assert node_c is not None and node_c.is_blocked is True

        mem.update_status("T-B", "done", expected_version=b.row_version)
        ready_after_b = mem.get_ready_tasks()
        assert [t.task_id for t in ready_after_b] == ["T-C"]

        snap_path = tmp_path / ".synapse" / "task_graph_snapshot.jsonl"
        exported = mem.export_jsonl_snapshot(snap_path)
        assert exported == 3
        lines = snap_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3
        assert json.loads(lines[0])["task_id"] in {"T-A", "T-B", "T-C"}
    finally:
        mem.close()


def test_task_graph_cycle_and_cas_conflict_negative(tmp_path: Path) -> None:
    """Negative: blocking cycle rejected; stale row_version CAS and foreign lease rejected."""
    from tools.core.task_graph_memory import LeaseConflictError, StaleRevisionError, TaskGraphMemory

    db_path = tmp_path / ".synapse" / "task_graph.db"
    mem = TaskGraphMemory(db_path=db_path)
    try:
        t1 = mem.add_task("T-1", "Node 1")
        mem.add_task("T-2", "Node 2")
        mem.add_task("T-3", "Node 3")
        mem.add_edge("T-1", "T-2", "blocks")
        mem.add_edge("T-2", "T-3", "blocks")

        with pytest.raises(ValueError, match="cycle"):
            mem.add_edge("T-3", "T-1", "blocks")

        with pytest.raises(ValueError, match="Invalid edge_type"):
            mem.add_edge("T-1", "T-2", "unknown_edge")  # type: ignore[arg-type]

        # Lease claiming and conflict
        claimed = mem.claim_task("T-1", owner="agent-alpha", ttl_sec=60.0)
        assert claimed.lease_owner == "agent-alpha"
        assert claimed.status == "in_progress"
        assert claimed.row_version == t1.row_version + 1

        with pytest.raises(LeaseConflictError):
            mem.claim_task("T-1", owner="agent-beta", ttl_sec=60.0)

        # Stale row_version CAS rejection
        with pytest.raises(StaleRevisionError):
            mem.update_status("T-1", "done", expected_version=t1.row_version)
    finally:
        mem.close()


def test_task_graph_boundary_empty_lease_expiry_and_bridge(tmp_path: Path) -> None:
    """Boundary: empty graph, complexity clamping/validation, expired lease reclaim, and project_state bridge."""
    from tools.core import project_state
    from tools.core.task_graph_memory import TaskGraphMemory

    db_path = tmp_path / ".synapse" / "task_graph.db"
    mem = TaskGraphMemory(db_path=db_path)
    try:
        assert mem.get_ready_tasks() == []
        assert mem.get_task("MISSING") is None

        with pytest.raises(ValueError, match="task_id"):
            mem.add_task("", "Empty ID")
        with pytest.raises(ValueError, match="complexity_score"):
            mem.add_task("T-BAD", "Bad score", complexity_score=11)

        mem.add_task("T-EXP", "Expiring lease task", complexity_score=8)
        mem.claim_task("T-EXP", owner="agent-1", ttl_sec=0.01, now_ts=1000.0)
        reclaimed = mem.reclaim_expired_leases(now_ts=1001.0)
        assert reclaimed == ["T-EXP"]

        node = mem.get_task("T-EXP")
        assert node is not None
        assert node.lease_owner is None
        assert node.status == "open"

        # Bridge into project_state.export_stateless_working_block
        project_state.init_state(str(tmp_path), goal="Verify graph bridge")
        block = project_state.export_stateless_working_block(str(tmp_path))
        assert "T-EXP" in block
        assert "Graph Ready" in block
    finally:
        mem.close()


def test_task_graph_cli_json_flags(tmp_path: Path) -> None:
    """CLI Contract: add, edge, ready, and snapshot commands with --json return exit 0."""
    db_path = tmp_path / ".synapse" / "task_graph.db"
    script = Path(__file__).resolve().parents[1] / "tools" / "core" / "task_graph_memory.py"

    r1 = subprocess.run(
        [sys.executable, str(script), "--db", str(db_path), "add", "--id", "M1", "--title", "Graph", "--complexity", "5", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r1.returncode == 0, r1.stderr
    p1 = json.loads(r1.stdout)
    assert p1["task_id"] == "M1"
    assert p1["complexity_score"] == 5

    r2 = subprocess.run(
        [sys.executable, str(script), "--db", str(db_path), "ready", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r2.returncode == 0, r2.stderr
    p2 = json.loads(r2.stdout)
    assert p2["ready_count"] == 1
    assert p2["tasks"][0]["task_id"] == "M1"


def test_task_graph_mutation_hardening_guards(tmp_path: Path) -> None:
    """Mutation hardening: covers DTO defaults/immutability, SQLite PRAGMAs, close, heartbeat, self-cycle, boundaries, and CLI."""
    import sqlite3
    from dataclasses import FrozenInstanceError
    from tools.core.task_graph_memory import LeaseConflictError, TaskGraphMemory, TaskNodeDTO, main

    assert TaskNodeDTO("d1", "Default", "open", 3, 1).is_blocked is False

    db_path = tmp_path / ".synapse" / "tg_hard.db"
    mem = TaskGraphMemory(db_path=db_path)
    assert mem._conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert mem._conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    assert mem._conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    try:
        t1 = mem.add_task("N1", "Root task", complexity_score=1)
        t2 = mem.add_task("N2", "Max task", complexity_score=10)
        assert t1.complexity_score == 1 and t2.complexity_score == 10
        assert t1.to_dict()["task_id"] == "N1"

        with pytest.raises(FrozenInstanceError):
            t1.status = "done"  # type: ignore[misc]

        with pytest.raises(ValueError, match="title"):
            mem.add_task("N3", "   ")
        with pytest.raises(ValueError, match="complexity_score"):
            mem.add_task("N3", "Zero score", complexity_score=0)
        with pytest.raises(ValueError, match="status"):
            mem.add_task("N3", "Bad status", status="bogus")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="cycle"):
            mem.add_edge("N1", "N1", "blocks")
        with pytest.raises(ValueError, match="must exist"):
            mem.add_edge("N1", "NOPE", "blocks")

        # Claim, heartbeat, foreign heartbeat rejection, same-owner reclaim, non-expired reclaim noop
        with pytest.raises(ValueError, match="owner"):
            mem.claim_task("N1", owner="   ", ttl_sec=10.0)
        with pytest.raises(ValueError, match="ttl_sec"):
            mem.claim_task("N1", owner="a1", ttl_sec=0.0)
        with pytest.raises(KeyError):
            mem.claim_task("MISSING", owner="a1", ttl_sec=10.0)

        c1 = mem.claim_task("N1", owner="agent-a", ttl_sec=10.0, now_ts=100.0)
        assert c1.lease_expires_at == pytest.approx(110.0)
        hb = mem.heartbeat("N1", owner="agent-a", ttl_sec=50.0, now_ts=105.0)
        assert hb.lease_expires_at == pytest.approx(155.0)
        with pytest.raises(LeaseConflictError):
            mem.heartbeat("N1", owner="agent-b", ttl_sec=50.0, now_ts=105.0)
        assert mem.reclaim_expired_leases(now_ts=154.0) == []
        assert mem.reclaim_expired_leases(now_ts=155.0) == ["N1"]

        # Update status keeps lease when in_progress and rejects unknown task / status
        with pytest.raises(KeyError):
            mem.update_status("NOPE", "done")
        with pytest.raises(ValueError):
            mem.update_status("N1", "invalid")  # type: ignore[arg-type]

        # Snapshot archive & listing
        sid = mem.archive_plan_snapshot("slug-1", "Done", {"ok": True})
        assert sid >= 1
        snaps = mem.list_archived_snapshots(limit=5)
        assert len(snaps) == 1 and snaps[0]["summary"] == "Done"
    finally:
        mem.close()

    with pytest.raises(sqlite3.ProgrammingError):
        mem._conn.execute("SELECT 1")

    # CLI direct main() coverage
    assert main(["--db", str(db_path), "edge", "--from", "N1", "--to", "N2", "--type", "blocks", "--json"]) == 0
    assert main(["--db", str(db_path), "status", "--id", "N1", "--state", "done", "--json"]) == 0
    assert main(["--db", str(db_path), "snapshot", "--out", str(tmp_path / "snap.jsonl"), "--json"]) == 0
    assert main(["--db", str(db_path), "edge", "--from", "N2", "--to", "N1", "--type", "blocks", "--json"]) == 1
    assert main(["--db", str(db_path)]) == 1
