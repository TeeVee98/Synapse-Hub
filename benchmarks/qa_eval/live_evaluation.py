#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Held-Out Live Model Evaluation Harness
--------------------------------------
Scores recorded live model runs against a frozen held-out QA dataset with
real provider usage, costs, latency p95, fallback traces, human-reviewed
verdicts, and comparable completeness checks.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple


_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from benchmarks.qa_eval.eval_runner import bootstrap_ci, percentile  # noqa: E402


@dataclass(frozen=True)
class ContentAddressedEvalDTO:
    dataset_digest: str
    rubric_digest: str
    category_breakdown: Dict[str, Dict[str, float]]


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def compute_rubric_digest(rubric: Optional[Dict[str, Any]]) -> str:
    """Computes canonical SHA-256 digest over a structured rubric payload."""
    return hashlib.sha256(_canonical_json(rubric or {}).encode("utf-8")).hexdigest()


def compute_dataset_digest(
    task_ids_or_tasks: Sequence[Any],
    rubric: Optional[Dict[str, Any]] = None,
) -> str:
    """Computes canonical SHA-256 digest over structured tasks + rubric, or legacy task_ids."""
    items = list(task_ids_or_tasks)
    if any(isinstance(item, dict) for item in items):
        normalized = sorted(
            (
                {
                    "task_id": str(item.get("task_id", "")),
                    "category": str(item.get("category", "")),
                    "prompt": str(item.get("prompt", "")),
                    "expected_criteria": item.get("expected_criteria"),
                }
                for item in items
                if isinstance(item, dict)
            ),
            key=lambda row: row["task_id"],
        )
        payload: Dict[str, Any] = {"tasks": normalized}
        if rubric is not None:
            payload["rubric"] = rubric
        return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()

    sorted_ids = sorted(str(t) for t in items)
    if rubric is not None:
        return hashlib.sha256(_canonical_json({"task_ids": sorted_ids, "rubric": rubric}).encode("utf-8")).hexdigest()
    canonical = json.dumps(sorted_ids, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _is_finite_non_neg(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        num = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(num) and num >= 0.0


def _inspect_slot_record(
    rec: Optional[Dict[str, Any]],
    dataset_digest: str,
    missing_reasons: Dict[str, int],
) -> Tuple[bool, float, Optional[float], Optional[float], bool, bool]:
    """Validates one expected (task_id, run_index) slot record without masking missing fields."""
    if rec is None:
        missing_reasons["missing_run"] = missing_reasons.get("missing_run", 0) + 1
        return False, 0.0, None, None, False, False

    reasons: List[str] = []
    if str(rec.get("dataset_digest") or "") != dataset_digest:
        reasons.append("dataset_digest_mismatch")
    if not _is_finite_non_neg(rec.get("latency_ms")):
        reasons.append("invalid_latency_ms")
    if not _is_finite_non_neg(rec.get("cost_usd")):
        reasons.append("invalid_cost_usd")
    verdict = str(rec.get("human_verdict") or "").strip().lower()
    if verdict not in ("pass", "fail"):
        reasons.append("missing_human_verdict")
    if str(rec.get("status") or "").strip().lower() != "completed":
        reasons.append("incomplete_status")

    for r in reasons:
        missing_reasons[r] = missing_reasons.get(r, 0) + 1

    latency = float(rec["latency_ms"]) if _is_finite_non_neg(rec.get("latency_ms")) else None
    cost = float(rec["cost_usd"]) if _is_finite_non_neg(rec.get("cost_usd")) else None
    fb_triggered = bool(rec.get("fallback_triggered"))
    fb_ok = bool(rec.get("fallback_succeeded")) if fb_triggered else False
    slot_complete = len(reasons) == 0
    outcome = 1.0 if (slot_complete and verdict == "pass") else 0.0
    return slot_complete, outcome, latency, cost, fb_triggered, fb_ok


def _build_category_breakdown(
    cat_buckets: Dict[str, Dict[str, List[float]]],
) -> Dict[str, Dict[str, Any]]:
    """Computes per-category success rate, cost-per-success, and latency p95 rollups."""
    breakdown: Dict[str, Dict[str, Any]] = {}
    for cat in sorted(cat_buckets):
        bucket = cat_buckets[cat]
        cat_outcomes = bucket["outcomes"]
        cat_costs = bucket["costs"]
        cat_lats = bucket["latencies"]
        denom = len(cat_outcomes)
        succ = int(sum(cat_outcomes))
        cost_total = round(sum(cat_costs), 6)
        breakdown[cat] = {
            "successes": succ,
            "denominator": denom,
            "success_rate": round(succ / denom, 4),
            "cost_usd_total": cost_total,
            "cost_per_success_usd": round(cost_total / succ, 6) if succ else None,
            "latency_p95_ms": percentile(cat_lats, 95.0) if cat_lats else None,
        }
    return breakdown


def _score_single_model(
    expected_slots: Sequence[Tuple[str, int]],
    model_records: Sequence[Dict[str, Any]],
    dataset_digest: str,
    budget_usd: Optional[float],
    task_categories: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Computes scorecard metrics for one model over the exact held-out task/run grid."""
    slot_map: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for rec in model_records:
        key = (str(rec.get("task_id") or ""), int(rec.get("run_index") or 1))
        if key not in slot_map:
            slot_map[key] = rec

    missing_reasons: Dict[str, int] = {}
    outcomes: List[float] = []
    latencies: List[float] = []
    costs: List[float] = []
    cat_buckets: Dict[str, Dict[str, List[float]]] = {}
    complete_valid = 0
    fb_attempts = 0
    fb_successes = 0

    for slot in expected_slots:
        complete, outcome, lat, cost, fb_trig, fb_ok = _inspect_slot_record(
            slot_map.get(slot), dataset_digest, missing_reasons
        )
        outcomes.append(outcome)
        if complete:
            complete_valid += 1
        if lat is not None:
            latencies.append(lat)
        if cost is not None:
            costs.append(cost)
        if fb_trig:
            fb_attempts += 1
            if fb_ok:
                fb_successes += 1
        cat = task_categories.get(slot[0]) if task_categories else None
        if cat is not None:
            bucket = cat_buckets.setdefault(cat, {"outcomes": [], "costs": [], "latencies": []})
            bucket["outcomes"].append(outcome)
            if cost is not None:
                bucket["costs"].append(cost)
            if lat is not None:
                bucket["latencies"].append(lat)

    expected_total = len(expected_slots)
    successes = int(sum(outcomes))
    success_rate = round(successes / expected_total, 4) if expected_total > 0 else 0.0
    ci_low, ci_high = bootstrap_ci(outcomes)
    cost_usd_total = round(sum(costs), 6)
    cost_per_success = round(cost_usd_total / successes, 6) if successes > 0 else None
    latency_p95 = percentile(latencies, 95.0) if latencies else None
    fb_rate = round(fb_successes / fb_attempts, 4) if fb_attempts > 0 else None
    missing_count = expected_total - complete_valid
    budget_exceeded = bool(budget_usd is not None and cost_usd_total > float(budget_usd))

    return {
        "successes": successes,
        "denominator": expected_total,
        "success_rate": success_rate,
        "uncertainty_ci95": [ci_low, ci_high],
        "cost_usd_total": cost_usd_total,
        "cost_per_success_usd": cost_per_success,
        "latency_p95_ms": latency_p95,
        "fallback_attempts": fb_attempts,
        "fallback_successes": fb_successes,
        "fallback_success_rate": fb_rate,
        "missing_count": missing_count,
        "missing_reasons": missing_reasons,
        "budget_exceeded": budget_exceeded,
        "category_breakdown": _build_category_breakdown(cat_buckets),
        "complete": missing_count == 0 and expected_total > 0 and not budget_exceeded,
    }


def evaluate_live_runs(
    dataset_manifest: Dict[str, Any],
    records: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Scores recorded multi-run model receipts with denominator, uncertainty, cost, p95, and missing data."""
    raw_tasks = dataset_manifest.get("tasks")
    tasks = [t for t in raw_tasks if isinstance(t, dict)] if isinstance(raw_tasks, list) else []
    raw_rubric = dataset_manifest.get("rubric")
    rubric = raw_rubric if isinstance(raw_rubric, dict) else None

    if dataset_manifest.get("task_ids"):
        task_ids = [str(t) for t in dataset_manifest["task_ids"]]
    else:
        task_ids = [str(t.get("task_id") or "") for t in tasks if t.get("task_id")]

    task_categories: Dict[str, str] = {
        str(t["task_id"]): str(t.get("category") or "uncategorized").strip().lower()
        for t in tasks
        if t.get("task_id")
    }
    expected_runs = max(1, int(dataset_manifest.get("expected_runs_per_model") or 1))
    computed_digest = compute_dataset_digest(tasks if tasks else task_ids, rubric=rubric)
    declared_digest = str(dataset_manifest.get("dataset_digest") or "")
    dataset_digest = computed_digest
    raw_budget = dataset_manifest.get("budget_usd")
    budget_usd = float(raw_budget) if raw_budget is not None else None

    blockers: List[str] = []
    if declared_digest and declared_digest != computed_digest:
        blockers.append("manifest_digest_mismatch")
    if not dataset_manifest.get("budget_approved"):
        blockers.append("budget_not_approved")
    if not dataset_manifest.get("rubric_approved"):
        blockers.append("rubric_not_approved")

    by_model: Dict[str, List[Dict[str, Any]]] = {}
    for rec in records:
        mid = str(rec.get("model_id") or "").strip()
        if mid:
            by_model.setdefault(mid, []).append(rec)

    expected_slots = [(tid, run_idx) for run_idx in range(1, expected_runs + 1) for tid in task_ids]
    models_summary: Dict[str, Dict[str, Any]] = {
        mid: _score_single_model(expected_slots, by_model[mid], dataset_digest, budget_usd, task_categories=task_categories)
        for mid in sorted(by_model)
    }

    ranking_eligible = (
        not blockers
        and len(models_summary) >= 2
        and all(entry["complete"] for entry in models_summary.values())
    )
    rankings: List[Dict[str, Any]] = []
    if ranking_eligible:
        ordered = sorted(
            models_summary.items(),
            key=lambda kv: (
                -kv[1]["successes"],
                kv[1]["cost_usd_total"],
                kv[1]["latency_p95_ms"] if kv[1]["latency_p95_ms"] is not None else 0.0,
                kv[0],
            ),
        )
        rankings = [
            {
                "rank": idx,
                "model_id": mid,
                "successes": stats["successes"],
                "denominator": stats["denominator"],
                "cost_usd_total": stats["cost_usd_total"],
                "latency_p95_ms": stats["latency_p95_ms"],
            }
            for idx, (mid, stats) in enumerate(ordered, start=1)
        ]

    passed = (
        not blockers
        and bool(models_summary)
        and all(entry["complete"] for entry in models_summary.values())
    )
    eval_dto = ContentAddressedEvalDTO(
        dataset_digest=dataset_digest,
        rubric_digest=compute_rubric_digest(rubric),
        category_breakdown={
            mid: {
                cat: float(cstats["success_rate"])
                for cat, cstats in mstats["category_breakdown"].items()
            }
            for mid, mstats in models_summary.items()
        },
    )
    payload: Dict[str, Any] = {
        "dataset_id": str(dataset_manifest.get("dataset_id") or ""),
        "dataset_digest": eval_dto.dataset_digest,
        "rubric_digest": eval_dto.rubric_digest,
        "rubric_revision": str(dataset_manifest.get("rubric_revision") or ""),
        "passed": passed,
        "ranking_eligible": ranking_eligible,
        "blockers": blockers,
        "models": models_summary,
        "rankings": rankings,
    }
    digest_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["receipt_sha256"] = hashlib.sha256(digest_bytes).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entrypoint for scoring frozen held-out live model evaluation receipts."""
    parser = argparse.ArgumentParser(description="Score held-out live model evaluation receipts.")
    parser.add_argument("--dataset", required=True, help="Path to frozen held-out dataset manifest JSON.")
    parser.add_argument("--records", required=True, help="Path to imported model execution receipts JSON.")
    parser.add_argument("--require-comparable", action="store_true", help="Fail unless >= 2 models have comparable complete runs.")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary to stdout.")
    args = parser.parse_args(argv)

    with open(args.dataset, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    with open(args.records, "r", encoding="utf-8") as fh:
        records = json.load(fh)

    report = evaluate_live_runs(manifest, records)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Dataset={report['dataset_id']} passed={report['passed']} ranking_eligible={report['ranking_eligible']}")

    ok = report["ranking_eligible"] if args.require_comparable else report["passed"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
