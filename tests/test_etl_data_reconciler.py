#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

from tools.contrib.etl_data_reconciler import (
    evaluate_iso_25012_quality,
    reconcile_etl_datasets,
    compute_row_hash,
)


def test_compute_row_hash():
    row_a = {"id": "1", "name": "Alice", "balance": "100"}
    row_b = {"name": "Alice", "balance": "100", "id": "1"}  # Different key order
    assert compute_row_hash(row_a) == compute_row_hash(row_b)

    row_c = {"id": "1", "name": "Alice", "balance": "200"}
    assert compute_row_hash(row_a) != compute_row_hash(row_c)


def test_iso_25012_quality_clean():
    clean_rows = [
        {"id": 1, "username": "alice", "status": "ACTIVE", "created_at": "2026-11-17T08:00:00Z"},
        {"id": 2, "username": "bob", "status": "PENDING", "created_at": "2026-11-17T08:30:00Z"},
    ]
    schema = {"id": {"type": "int"}, "status": {"enum": ["ACTIVE", "PENDING"]}}
    res = evaluate_iso_25012_quality(clean_rows, schema_spec=schema, max_freshness_hours=48.0)
    assert res["overall_score"] >= 90.0
    assert res["verdict"] == "PASS"
    assert res["characteristics"]["completeness"]["null_cells"] == 0
    assert res["characteristics"]["consistency"]["duplicate_rows"] == 0


def test_iso_25012_quality_with_nulls_and_duplicates():
    flawed_rows = [
        {"id": 1, "name": "Alice", "email": None},  # Null cell
        {"id": 1, "name": "Alice", "email": None},  # Duplicate row
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
    ]
    res = evaluate_iso_25012_quality(flawed_rows)
    assert res["characteristics"]["completeness"]["null_cells"] >= 1
    assert res["characteristics"]["consistency"]["duplicate_rows"] >= 1
    assert res["overall_score"] < 95.0


def test_dama_dmbok_reconcile_clean():
    source = [
        {"id": "ORD_1", "amount": 100.0, "status": "PAID"},
        {"id": "ORD_2", "amount": 250.0, "status": "PAID"},
    ]
    target = [
        {"id": "ORD_1", "amount": 100.0, "status": "PAID"},
        {"id": "ORD_2", "amount": 250.0, "status": "PAID"},
    ]
    res = reconcile_etl_datasets(source, target, primary_key="id", numeric_columns=["amount"])
    assert res["is_reconciled"] is True
    assert res["row_counts"]["variance"] == 0
    assert res["key_deltas"]["dropped_in_target_count"] == 0
    assert res["key_deltas"]["ghost_in_target_count"] == 0
    assert res["data_mutations"]["mutated_records_count"] == 0
    assert res["numeric_aggregation_parity"]["amount"]["is_balanced"] is True


def test_dama_dmbok_reconcile_with_dropped_and_mutated():
    source = [
        {"id": "ORD_1", "amount": 100.0, "status": "PAID"},
        {"id": "ORD_2", "amount": 250.0, "status": "PAID"},
        {"id": "ORD_3", "amount": 500.0, "status": "PENDING"},
    ]
    # ORD_2 has mutated amount, ORD_3 is dropped, ORD_4 is ghost
    target = [
        {"id": "ORD_1", "amount": 100.0, "status": "PAID"},
        {"id": "ORD_2", "amount": 240.0, "status": "PAID"},
        {"id": "ORD_4", "amount": 80.0, "status": "COMPLETED"},
    ]
    res = reconcile_etl_datasets(source, target, primary_key="id", numeric_columns=["amount"])
    assert res["is_reconciled"] is False
    assert res["key_deltas"]["dropped_in_target_count"] == 1
    assert "ORD_3" in res["key_deltas"]["dropped_sample"]
    assert res["key_deltas"]["ghost_in_target_count"] == 1
    assert "ORD_4" in res["key_deltas"]["ghost_sample"]
    assert res["data_mutations"]["mutated_records_count"] == 1
    assert res["numeric_aggregation_parity"]["amount"]["is_balanced"] is False
