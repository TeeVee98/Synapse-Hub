#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_live_evaluation.py
Validates held-out live model evaluation scoring across 2 models x 20 tasks x 3 runs,
incomplete/missing-data ranking blocks, budget/rubric approvals, boundary handling, and CLI.
"""

import json
from pathlib import Path
import subprocess
import sys


def _build_manifest_and_records(num_tasks: int = 20, runs_per_model: int = 3):
    from benchmarks.qa_eval.live_evaluation import compute_dataset_digest

    task_ids = [f"HELD-{idx:02d}" for idx in range(1, num_tasks + 1)]
    digest = compute_dataset_digest(task_ids)
    manifest = {
        "dataset_id": "qa_heldout_v1",
        "dataset_digest": digest,
        "task_ids": task_ids,
        "expected_runs_per_model": runs_per_model,
        "budget_usd": 25.0,
        "budget_approved": True,
        "rubric_approved": True,
        "rubric_revision": "rubric-v1.0",
    }

    records = []
    for model_id, base_latency, unit_cost, fail_mod in (
        ("model-alpha", 420.0, 0.12, 10),
        ("model-beta", 680.0, 0.20, 4),
    ):
        for r_idx in range(1, runs_per_model + 1):
            for t_idx, tid in enumerate(task_ids, start=1):
                global_idx = (r_idx - 1) * num_tasks + t_idx
                passed = (global_idx % fail_mod) != 0
                fb_triggered = (global_idx % 12) == 0
                records.append(
                    {
                        "model_id": model_id,
                        "task_id": tid,
                        "run_index": r_idx,
                        "dataset_digest": digest,
                        "status": "completed",
                        "prompt_tokens": 1200,
                        "completion_tokens": 400,
                        "cost_usd": unit_cost,
                        "latency_ms": base_latency + float(t_idx * 10),
                        "fallback_triggered": fb_triggered,
                        "fallback_succeeded": True if fb_triggered else None,
                        "human_verdict": "pass" if passed else "fail",
                    }
                )
    return manifest, records


def test_comparable_two_model_pilot_scoring_and_ranking():
    """Positive: 2 models x 20 tasks x 3 runs produce comparable metrics, CI, cost/success, p95, and ranking."""
    from benchmarks.qa_eval.live_evaluation import evaluate_live_runs

    manifest, records = _build_manifest_and_records(20, 3)
    report = evaluate_live_runs(manifest, records)

    assert report["passed"] is True
    assert report["ranking_eligible"] is True
    assert len(report["rankings"]) == 2
    assert report["rankings"][0]["model_id"] == "model-alpha"

    alpha = report["models"]["model-alpha"]
    assert alpha["denominator"] == 60
    assert alpha["successes"] == 54
    assert alpha["missing_count"] == 0
    assert len(alpha["uncertainty_ci95"]) == 2
    assert alpha["uncertainty_ci95"][0] <= alpha["success_rate"] <= alpha["uncertainty_ci95"][1]
    assert alpha["cost_usd_total"] == round(60 * 0.12, 6)
    assert alpha["cost_per_success_usd"] == round((60 * 0.12) / 54, 6)
    assert alpha["latency_p95_ms"] > 500.0
    assert alpha["fallback_attempts"] == 5
    assert alpha["fallback_success_rate"] == 1.0


def test_negative_missing_review_unapproved_budget_or_digest_mismatch_blocks_ranking():
    """Negative: Missing human review, missing run, unapproved budget/rubric, or bad digest block ranking."""
    from benchmarks.qa_eval.live_evaluation import evaluate_live_runs

    manifest, records = _build_manifest_and_records(20, 3)

    # 1. Drop 1 human review verdict from model-beta
    incomplete_records = [dict(r) for r in records]
    incomplete_records[-1]["human_verdict"] = None
    res_inc = evaluate_live_runs(manifest, incomplete_records)
    assert res_inc["ranking_eligible"] is False
    assert res_inc["rankings"] == []
    assert res_inc["models"]["model-beta"]["missing_count"] == 1
    assert res_inc["models"]["model-beta"]["missing_reasons"]["missing_human_verdict"] == 1

    # 2. Unapproved budget/rubric blocks overall certification
    unapproved = dict(manifest, budget_approved=False, rubric_approved=False)
    res_unapp = evaluate_live_runs(unapproved, records)
    assert res_unapp["passed"] is False
    assert res_unapp["ranking_eligible"] is False
    assert "budget_not_approved" in res_unapp["blockers"]
    assert "rubric_not_approved" in res_unapp["blockers"]

    # 3. Digest mismatch quarantined into missing data
    bad_digest_records = [dict(r) for r in records]
    bad_digest_records[0]["dataset_digest"] = "wrong-digest"
    res_digest = evaluate_live_runs(manifest, bad_digest_records)
    assert res_digest["ranking_eligible"] is False
    assert res_digest["models"]["model-alpha"]["missing_reasons"]["dataset_digest_mismatch"] == 1

    # 4. In-process dropped runs check missing_run and fallback preservation
    res_dropped = evaluate_live_runs(manifest, records[:-2])
    assert res_dropped["ranking_eligible"] is False
    assert res_dropped["models"]["model-beta"]["missing_count"] == 2
    assert res_dropped["models"]["model-beta"]["missing_reasons"]["missing_run"] == 2
    assert res_dropped["models"]["model-beta"]["fallback_attempts"] == 4
    assert res_dropped["models"]["model-beta"]["fallback_successes"] == 4


def test_boundary_zero_successes_empty_records_and_non_finite_metrics():
    """Boundary: 0 successes gives None cost_per_success; empty records and NaN latency are accounted cleanly."""
    from benchmarks.qa_eval.live_evaluation import evaluate_live_runs

    manifest, _ = _build_manifest_and_records(5, 1)
    empty_res = evaluate_live_runs(manifest, [])
    assert empty_res["passed"] is False
    assert empty_res["ranking_eligible"] is False
    assert empty_res["models"] == {}

    failing_records = [
        {
            "model_id": "m1",
            "task_id": tid,
            "run_index": 1,
            "dataset_digest": manifest["dataset_digest"],
            "status": "completed",
            "cost_usd": None if idx == 0 else ("bad" if idx == 3 else 0.5),
            "latency_ms": float("nan") if idx == 0 else (-1.0 if idx == 1 else (True if idx == 2 else 100.0)),
            "fallback_triggered": False,
            "human_verdict": "fail",
        }
        for idx, tid in enumerate(manifest["task_ids"])
    ]
    res = evaluate_live_runs(manifest, failing_records)
    m1 = res["models"]["m1"]
    assert m1["successes"] == 0
    assert m1["cost_per_success_usd"] is None
    assert m1["missing_count"] == 4
    assert m1["missing_reasons"]["invalid_latency_ms"] == 3
    assert m1["missing_reasons"]["invalid_cost_usd"] == 2
    assert res["ranking_eligible"] is False


def test_cli_live_evaluation_json_and_require_comparable_gate(tmp_path):
    """CLI: Evaluates frozen manifest + imported receipts and fails closed under --require-comparable on gaps."""
    manifest, records = _build_manifest_and_records(20, 3)
    ds_file = tmp_path / "heldout_manifest.json"
    rec_file = tmp_path / "imported_receipts.json"
    bad_rec_file = tmp_path / "incomplete_receipts.json"

    ds_file.write_text(json.dumps(manifest), encoding="utf-8")
    rec_file.write_text(json.dumps(records), encoding="utf-8")
    bad_rec_file.write_text(json.dumps(records[:-2]), encoding="utf-8")

    repo_root = Path(__file__).resolve().parent.parent
    script = str(repo_root / "benchmarks" / "qa_eval" / "live_evaluation.py")

    ok = subprocess.run(
        [sys.executable, script, "--dataset", str(ds_file), "--records", str(rec_file), "--require-comparable", "--json"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert ok.returncode == 0, ok.stderr
    ok_payload = json.loads(ok.stdout)
    assert ok_payload["ranking_eligible"] is True
    assert ok_payload["rankings"][0]["model_id"] == "model-alpha"

    fail = subprocess.run(
        [sys.executable, script, "--dataset", str(ds_file), "--records", str(bad_rec_file), "--require-comparable", "--json"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert fail.returncode != 0
    fail_payload = json.loads(fail.stdout)
    assert fail_payload["ranking_eligible"] is False
    beta = fail_payload["models"]["model-beta"]
    assert beta["missing_count"] == 2
    assert beta["missing_reasons"]["missing_run"] == 2
    assert beta["fallback_attempts"] == 4
    assert beta["fallback_successes"] == 4
