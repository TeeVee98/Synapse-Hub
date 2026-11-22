#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_associative_memory.py — 4-Scenario Test Suite for Associative Graph Memory (M5 / R5)
---------------------------------------------------------------------------------------------
Comprehensive tests covering:
  1. TestAssociativeMemoryPositive : Core logic, graph creation, queries, decay, consolidation, stats.
  2. TestAssociativeMemoryNegative : Missing entities, bad JSON, NaN weights, invalid subcommands.
  3. TestAssociativeMemoryBoundary : Zero weights, extreme half-life, empty graph, future timestamps.
  4. TestAssociativeMemoryCLIFlags : CLI options (--json, --output, --db-path, all subcommands).
"""

import json
import math
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

from tools.reasoning.associative_memory import (
    AssociativeMemory,
    main as cli_main,
)


class TestAssociativeMemoryPositive:
    """Positive scenario tests verifying core associative memory capabilities."""

    def test_record_node_and_retrieval(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test_nodes.db")
        with AssociativeMemory(db_path=db_path) as mem:
            mem.record_node(
                entity_id="module:checkout",
                entity_type="module",
                attributes={"owner": "payments", "tier": 1},
            )
            node = mem.get_node("module:checkout")
            assert node is not None
            assert node["entity_id"] == "module:checkout"
            assert node["entity_type"] == "module"
            assert node["attributes"]["owner"] == "payments"
            assert node["attributes"]["tier"] == 1
            assert node["access_count"] == 1
            assert node["status"] == "active"

            # Updating node merges attributes and increments access count
            mem.record_node(
                entity_id="module:checkout",
                entity_type="module",
                attributes={"version": "2.4.0"},
            )
            updated_node = mem.get_node("module:checkout")
            assert updated_node is not None
            assert updated_node["attributes"]["owner"] == "payments"
            assert updated_node["attributes"]["version"] == "2.4.0"
            assert updated_node["access_count"] == 2

    def test_record_and_query_associations(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test_assoc.db")
        with AssociativeMemory(db_path=db_path) as mem:
            mem.record_association(
                source_id="defect:ERR-409",
                target_id="module:checkout",
                relation="violates",
                weight=0.90,
            )
            mem.record_association(
                source_id="test:tc_checkout",
                target_id="module:checkout",
                relation="verifies",
                weight=0.75,
            )
            mem.record_association(
                source_id="defect:ERR-500",
                target_id="module:checkout",
                relation="violates",
                weight=0.30,
            )

            # Query all associations for module:checkout
            results = mem.query_associations("module:checkout", min_weight=0.50, limit=10)
            assert len(results) == 2
            # Check descending weight ordering
            assert results[0]["weight"] == 0.90
            assert results[0]["neighbor_id"] == "defect:ERR-409"
            assert results[1]["weight"] == 0.75
            assert results[1]["neighbor_id"] == "test:tc_checkout"

            # Access count on target module should have increased
            mod = mem.get_node("module:checkout")
            assert mod is not None
            assert mod["access_count"] >= 2

    def test_continuous_temporal_decay_mathematical_precision(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test_decay.db")
        with AssociativeMemory(db_path=db_path) as mem:
            t0 = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
            mem.record_association(
                source_id="defect:slow_query",
                target_id="module:database",
                relation="affects",
                weight=1.0,
                timestamp=t0,
            )

            # 7 days elapsed with half_life_days=7.0 -> weight should be exactly 0.50
            t_after_7d = t0 + timedelta(days=7.0)
            decayed_count = mem.apply_time_decay(half_life_days=7.0, current_time=t_after_7d)
            assert decayed_count == 1

            assoc = mem.query_associations("module:database", min_weight=0.0)
            assert len(assoc) == 1
            calculated_weight = assoc[0]["weight"]
            assert math.isclose(calculated_weight, 0.50, rel_tol=1e-4)

            # Another 7 days (14 days total) -> weight should be 0.25
            t_after_14d = t_after_7d + timedelta(days=7.0)
            mem.apply_time_decay(half_life_days=7.0, current_time=t_after_14d)
            assoc_14d = mem.query_associations("module:database", min_weight=0.0)
            assert math.isclose(assoc_14d[0]["weight"], 0.25, rel_tol=1e-4)

    def test_sleep_consolidation_clusters_defects_and_archives_granular_nodes(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test_consolidate.db")
        with AssociativeMemory(db_path=db_path) as mem:
            t0 = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
            # Record 3 recurring defects violating module:auth
            for i in range(1, 4):
                defect_id = f"defect:auth_bypass_0{i}"
                mem.record_node(
                    entity_id=defect_id,
                    entity_type="defect",
                    attributes={"code": f"SEC-00{i}", "detail": f"Auth token bypass case {i}"},
                    status="active",
                    timestamp=t0,
                )
                mem.record_association(
                    source_id=defect_id,
                    target_id="module:auth",
                    relation="violates",
                    weight=0.90,
                    timestamp=t0,
                )

            # Run sleep consolidation with min_cooccurrence=2
            t_sleep = t0 + timedelta(days=1.0)
            summary = mem.sleep_consolidate(
                prune_threshold=0.15,
                generalize_min_cooccurrence=2,
                current_time=t_sleep,
            )

            assert summary["decayed_count"] == 3
            assert len(summary["consolidated_principles"]) == 1
            principle = summary["consolidated_principles"][0]
            assert principle["principle_id"] == "rule:consolidated:auth"
            assert principle["target_id"] == "module:auth"
            assert principle["subsumed_defects_count"] == 3

            # Check that generalized principle node exists and is active
            p_node = mem.get_node("rule:consolidated:auth")
            assert p_node is not None
            assert p_node["entity_type"] == "rule"
            assert p_node["status"] == "active"
            assert p_node["attributes"]["is_generalized"] is True

            # Check that granular defect nodes are now archived
            for i in range(1, 4):
                d_node = mem.get_node(f"defect:auth_bypass_0{i}")
                assert d_node is not None
                assert d_node["status"] == "archived"

            # Check associations on consolidated principle
            p_assocs = mem.query_associations("rule:consolidated:auth")
            relations = {a["relation"] for a in p_assocs}
            assert "guards" in relations
            assert "subsumed_by" in relations

    def test_get_stats_and_dict_serialization(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test_stats.db")
        with AssociativeMemory(db_path=db_path) as mem:
            mem.record_node("module:core", "module", {"critical": True})
            mem.record_node("rule:no_eval", "rule", {"severity": "critical"})
            mem.record_association("rule:no_eval", "module:core", "guards", weight=0.85)

            stats = mem.get_stats()
            assert stats["total_nodes"] == 2
            assert stats["active_nodes"] == 2
            assert stats["total_edges"] == 1
            assert stats["avg_weight"] == 0.85
            assert stats["node_types"]["module"] == 1
            assert stats["node_types"]["rule"] == 1
            assert stats["relations"]["guards"] == 1

            # Test to_dict and from_dict
            serialized = mem.to_dict()
            assert len(serialized["nodes"]) == 2
            assert len(serialized["edges"]) == 1

        # Restore into another memory instance
        db2_path = str(tmp_path / "test_stats2.db")
        with AssociativeMemory(db_path=db2_path) as mem2:
            mem2.from_dict(serialized)
            stats2 = mem2.get_stats()
            assert stats2["total_nodes"] == 2
            assert stats2["total_edges"] == 1
            assert stats2["avg_weight"] == 0.85


class TestAssociativeMemoryNegative:
    """Negative scenario tests verifying error resilience and input validation."""

    def test_invalid_node_recording_inputs_raise_value_error(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test_neg.db")
        with AssociativeMemory(db_path=db_path) as mem:
            with pytest.raises(ValueError, match="entity_id must be a non-empty string"):
                mem.record_node("", "module")

            with pytest.raises(ValueError, match="entity_type must be a non-empty string"):
                mem.record_node("module:test", "")

    def test_invalid_association_inputs_raise_value_error(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test_neg2.db")
        with AssociativeMemory(db_path=db_path) as mem:
            with pytest.raises(ValueError, match="source_id must be a non-empty string"):
                mem.record_association("", "module:test", "rel")

            with pytest.raises(ValueError, match="target_id must be a non-empty string"):
                mem.record_association("source:test", "", "rel")

            with pytest.raises(ValueError, match="relation must be a non-empty string"):
                mem.record_association("source:test", "target:test", "")

            with pytest.raises(ValueError, match="weight must be a finite float"):
                mem.record_association("s", "t", "r", weight=float("nan"))

            with pytest.raises(ValueError, match="weight must be a finite float"):
                mem.record_association("s", "t", "r", weight=float("inf"))

    def test_querying_nonexistent_or_empty_entity_returns_empty_list(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test_neg3.db")
        with AssociativeMemory(db_path=db_path) as mem:
            res1 = mem.query_associations("non_existent_entity_12345")
            assert res1 == []

            res2 = mem.query_associations("")
            assert res2 == []

    def test_invalid_decay_parameters_raise_value_error(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test_neg4.db")
        with AssociativeMemory(db_path=db_path) as mem:
            with pytest.raises(ValueError, match="half_life_days must be strictly positive"):
                mem.apply_time_decay(half_life_days=0.0)

            with pytest.raises(ValueError, match="half_life_days must be strictly positive"):
                mem.apply_time_decay(half_life_days=-5.0)

            with pytest.raises(ValueError, match="decay_lambda must be non-negative"):
                mem.apply_time_decay(decay_lambda=-0.1)

    def test_cli_handles_invalid_subcommand_cleanly(self) -> None:
        exit_code = cli_main(["invalid_command_xyz", "--json"])
        assert exit_code != 0


class TestAssociativeMemoryBoundary:
    """Boundary conditions tests (zero weight, extreme half-life, empty graphs, clock skew)."""

    def test_zero_weight_edge(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test_bound_zero.db")
        with AssociativeMemory(db_path=db_path) as mem:
            mem.record_association("src:zero", "tgt:zero", "rel", weight=0.0)
            res = mem.query_associations("src:zero", min_weight=0.0)
            assert len(res) == 1
            assert res[0]["weight"] == 0.0

            # Pruning threshold above 0.0 should prune it immediately
            summary = mem.sleep_consolidate(prune_threshold=0.01)
            assert summary["pruned_count"] >= 1
            res_after = mem.query_associations("src:zero", min_weight=0.0)
            assert len(res_after) == 0

    def test_extreme_half_life_values(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test_bound_hl.db")
        with AssociativeMemory(db_path=db_path) as mem:
            t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            mem.record_association("node:a", "node:b", "rel", weight=1.0, timestamp=t0)

            # Very large half-life: 1,000,000 days -> virtually zero decay in 10 days
            t1 = t0 + timedelta(days=10.0)
            mem.apply_time_decay(half_life_days=1000000.0, current_time=t1)
            res_large_hl = mem.query_associations("node:a", min_weight=0.0)
            assert math.isclose(res_large_hl[0]["weight"], 1.0, rel_tol=1e-3)

            # Micro half-life: 0.0001 days (~8.6 seconds) -> completely decays in 1 hour
            t2 = t1 + timedelta(hours=1.0)
            mem.apply_time_decay(half_life_days=0.0001, current_time=t2)
            res_micro_hl = mem.query_associations("node:a", min_weight=0.0)
            assert res_micro_hl[0]["weight"] < 1e-10

    def test_empty_graph_operations(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test_bound_empty.db")
        with AssociativeMemory(db_path=db_path) as mem:
            # Query on empty graph
            assert mem.query_associations("anything") == []

            # Decay on empty graph
            assert mem.apply_time_decay() == 0

            # Sleep consolidate on empty graph
            summary = mem.sleep_consolidate()
            assert summary["nodes_count"] == 0
            assert summary["edges_count"] == 0
            assert summary["decayed_count"] == 0
            assert summary["pruned_count"] == 0
            assert summary["consolidated_principles"] == []

            # Stats on empty graph
            stats = mem.get_stats()
            assert stats["total_nodes"] == 0
            assert stats["total_edges"] == 0
            assert stats["avg_weight"] == 0.0

    def test_single_node_graph_without_edges(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test_bound_single.db")
        with AssociativeMemory(db_path=db_path) as mem:
            mem.record_node("orphan:concept", "concept")
            node = mem.get_node("orphan:concept")
            assert node is not None
            assert node["entity_id"] == "orphan:concept"

            assocs = mem.query_associations("orphan:concept")
            assert assocs == []

            stats = mem.get_stats()
            assert stats["total_nodes"] == 1
            assert stats["total_edges"] == 0

    def test_future_timestamp_clock_skew_does_not_grow_weight(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test_bound_future.db")
        with AssociativeMemory(db_path=db_path) as mem:
            future_t = datetime(2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            mem.record_association("src:future", "tgt:future", "rel", weight=0.80, timestamp=future_t)

            # Evaluation at an earlier timestamp (clock skew)
            current_t = datetime(2026, 11, 22, 0, 0, 0, tzinfo=timezone.utc)
            decayed = mem.apply_time_decay(half_life_days=7.0, current_time=current_t)
            assert decayed == 0

            assoc = mem.query_associations("src:future")
            # Weight must not increase
            assert assoc[0]["weight"] == 0.80

    def test_high_cooccurrence_threshold_prevents_premature_generalization(self, tmp_path: Path) -> None:
        db_path = str(tmp_path / "test_bound_thresh.db")
        with AssociativeMemory(db_path=db_path) as mem:
            # Only 1 defect recorded
            mem.record_node("defect:single_flaky", "defect", status="active")
            mem.record_association("defect:single_flaky", "module:cart", "violates", weight=0.90)

            # Consolidate with min_cooccurrence=5
            summary = mem.sleep_consolidate(generalize_min_cooccurrence=5)
            # Threshold 5 not reached by 1 defect -> no principle created
            assert summary["consolidated_principles"] == []
            assert mem.get_node("rule:consolidated:cart") is None


class TestAssociativeMemoryCLIFlags:
    """CLI flag and subcommand integration tests."""

    def test_cli_record_and_query_json(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        db_path = str(tmp_path / "cli_test.db")
        # 1. Record node
        code1 = cli_main([
            "--db-path", db_path,
            "record",
            "--entity", "module:order",
            "--type", "module",
            "--attributes", '{"team": "e-commerce"}',
            "--json",
        ])
        assert code1 == 0
        captured1 = capsys.readouterr()
        data1 = json.loads(captured1.out)
        assert data1["status"] == "ok"
        assert data1["entity_id"] == "module:order"

        # 2. Record association
        code2 = cli_main([
            "--db-path", db_path,
            "record",
            "--source", "defect:timeout",
            "--target", "module:order",
            "--relation", "impacts",
            "--weight", "0.88",
            "--json",
        ])
        assert code2 == 0
        captured2 = capsys.readouterr()
        data2 = json.loads(captured2.out)
        assert data2["status"] == "ok"
        assert data2["weight"] == 0.88

        # 3. Query associations
        code3 = cli_main([
            "--db-path", db_path,
            "query",
            "--entity", "module:order",
            "--min-weight", "0.50",
            "--limit", "5",
            "--json",
        ])
        assert code3 == 0
        captured3 = capsys.readouterr()
        data3 = json.loads(captured3.out)
        assert data3["status"] == "ok"
        assert data3["associations_count"] == 1
        assert data3["associations"][0]["relation"] == "impacts"

    def test_cli_decay_and_stats(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        db_path = str(tmp_path / "cli_decay.db")
        cli_main([
            "--db-path", db_path,
            "record",
            "--source", "rule:timeout_guard",
            "--target", "module:net",
            "--relation", "guards",
            "--weight", "1.0",
            "--json",
        ])
        capsys.readouterr()

        # Decay
        code_decay = cli_main([
            "--db-path", db_path,
            "decay",
            "--half-life-days", "14.0",
            "--json",
        ])
        assert code_decay == 0
        captured_decay = capsys.readouterr()
        data_decay = json.loads(captured_decay.out)
        assert data_decay["status"] == "ok"
        assert data_decay["half_life_days"] == 14.0

        # Stats
        code_stats = cli_main([
            "--db-path", db_path,
            "stats",
            "--json",
        ])
        assert code_stats == 0
        captured_stats = capsys.readouterr()
        data_stats = json.loads(captured_stats.out)
        assert data_stats["status"] == "ok"
        assert data_stats["total_nodes"] == 2
        assert data_stats["total_edges"] == 1

    def test_cli_consolidate_and_output_file(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        db_path = str(tmp_path / "cli_consolidate.db")
        out_file = str(tmp_path / "output_summary.json")

        # Insert 2 defects
        for i in (1, 2):
            cli_main([
                "--db-path", db_path,
                "record",
                "--entity", f"defect:bug_0{i}",
                "--type", "defect",
                "--json",
            ])
            cli_main([
                "--db-path", db_path,
                "record",
                "--source", f"defect:bug_0{i}",
                "--target", "module:billing",
                "--relation", "violates",
                "--weight", "0.95",
                "--json",
            ])
        capsys.readouterr()

        # Consolidate with output file
        code_cons = cli_main([
            "--db-path", db_path,
            "--output", out_file,
            "consolidate",
            "--prune-threshold", "0.20",
            "--min-cooccurrence", "2",
            "--json",
        ])
        assert code_cons == 0
        captured_cons = capsys.readouterr()
        data_cons = json.loads(captured_cons.out)
        assert data_cons["status"] == "ok"
        assert len(data_cons["consolidated_principles"]) == 1

        # Verify output file content
        assert os.path.exists(out_file)
        with open(out_file, "r", encoding="utf-8") as fp:
            file_data = json.load(fp)
            assert file_data["status"] == "ok"
            assert file_data["consolidated_principles"][0]["principle_id"] == "rule:consolidated:billing"

    def test_cli_error_handling_emits_json_when_requested(self, capsys: pytest.CaptureFixture) -> None:
        # Invalid attributes JSON
        code = cli_main([
            "--db-path", ":memory:",
            "record",
            "--entity", "test_entity",
            "--attributes", "{bad_json",
            "--json",
        ])
        assert code != 0
        captured = capsys.readouterr()
        err_data = json.loads(captured.out)
        assert err_data["status"] == "error"
        assert "Invalid JSON string in --attributes" in err_data["error"]


class TestAssociativeMemoryPragmaAndDateTimeSensors:
    """Rigorous sensor tests for SQLite WAL pragmas, datetime parsing, and entity validation."""

    def test_sqlite_pragmas_on_disk_and_wal_control(self, tmp_path: Path):
        from tools.reasoning.associative_memory import AssociativeMemory

        # 1. On-disk database with default auto_wal=True (auto_wal argument omitted)
        db_file = tmp_path / "nested_dir" / "wal_test.db"
        with AssociativeMemory(db_path=str(db_file)) as mem:
            assert os.path.exists(tmp_path / "nested_dir")
            jm = mem.conn.execute("PRAGMA journal_mode;").fetchone()[0]
            assert jm.upper() == "WAL"

            sync = mem.conn.execute("PRAGMA synchronous;").fetchone()[0]
            assert sync in (1, "NORMAL", "normal")

            fk = mem.conn.execute("PRAGMA foreign_keys;").fetchone()[0]
            assert fk == 1

        # 2. On-disk database with auto_wal=False
        db_nowal = tmp_path / "nowal_test.db"
        with AssociativeMemory(db_path=str(db_nowal), auto_wal=False) as mem_nowal:
            jm_no = mem_nowal.conn.execute("PRAGMA journal_mode;").fetchone()[0]
            assert jm_no.upper() != "WAL"

        # 3. In-memory database :memory: does not use WAL
        with AssociativeMemory(db_path=":memory:", auto_wal=True) as mem_mem:
            jm_mem = mem_mem.conn.execute("PRAGMA journal_mode;").fetchone()[0]
            assert jm_mem.upper() != "WAL"

    def test_iso_datetime_parsing_tzinfo_handling(self):
        from datetime import datetime, timezone
        from tools.reasoning.associative_memory import _parse_iso_datetime, _format_iso_datetime

        # 1. None and non-string inputs return current UTC
        dt_none = _parse_iso_datetime(None)
        assert dt_none.tzinfo == timezone.utc

        dt_bad_type = _parse_iso_datetime(12345)  # type: ignore
        assert dt_bad_type.tzinfo == timezone.utc

        # 2. Naive ISO string without offset gets UTC assigned directly (hour preserved as 12 UTC)
        dt_naive = _parse_iso_datetime("2026-01-01T12:00:00")
        assert dt_naive.tzinfo == timezone.utc
        assert dt_naive.hour == 12

        # 3. Formatter with naive datetime assigns UTC without shift
        naive_dt = datetime(2026, 1, 1, 12, 0, 0)
        formatted = _format_iso_datetime(naive_dt)
        assert "2026-01-01T12:00:00+00:00" in formatted

    def test_infer_entity_type_and_record_node_validation(self):
        from tools.reasoning.associative_memory import AssociativeMemory

        # Test _infer_entity_type on non-string (int) and empty string
        assert AssociativeMemory._infer_entity_type(12345) == "concept"  # type: ignore
        assert AssociativeMemory._infer_entity_type(None) == "concept"   # type: ignore
        assert AssociativeMemory._infer_entity_type("") == "concept"
        assert AssociativeMemory._infer_entity_type("module:auth") == "module"

        with AssociativeMemory(db_path=":memory:") as mem:
            # Non-string entity_id
            with pytest.raises(ValueError, match="entity_id must be a non-empty string"):
                mem.record_node(123, "module")  # type: ignore

            # Non-string entity_type
            with pytest.raises(ValueError, match="entity_type must be a non-empty string"):
                mem.record_node("valid_id", 456)  # type: ignore
