# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""4-scenario verification suite for M7: Agno /improve Ratchet, CAMEL Critic/CoT & Letta Core Compaction."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.core.qa_memory_os import CoreCompactionReceiptDTO, QAMemoryOS
from tools.orchestration.self_improve_harness import (
    CriticRubricEvaluator,
    EvalCaseDTO,
    EvalRegressionSuite,
    EvalSuiteResultDTO,
    SelfImproveHarness,
    SelfImprovingTraceLoop,
    WorkforceFailureEscalator,
    main as improve_main,
)


def test_improve_ratchet_and_core_compaction(tmp_path: Path) -> None:
    """Positive + Negative scenario: /improve regression ratchet, Critic veto, CoT refine, Workforce escalation, Letta core compaction."""
    cases = [
        EvalCaseDTO("c1", "login", "PASS_LOGIN"),
        EvalCaseDTO("c2", "checkout", "PASS_CHECKOUT"),
        EvalCaseDTO("c3", "refund", "PASS_REFUND"),
        EvalCaseDTO("c4", "logout", "PASS_LOGOUT"),
        EvalCaseDTO("c5", "audit", "PASS_AUDIT"),
    ]
    with pytest.raises(FrozenInstanceError):
        cases[0].case_id = "mut"  # type: ignore[misc]

    suite = EvalRegressionSuite("qa_skills_regression", cases)
    critic = CriticRubricEvaluator(weights={"correctness": 0.6, "safety": 0.4}, veto_threshold=0.75)
    harness = SelfImproveHarness(suite=suite, critic=critic)

    def baseline_solver(inp: str) -> str:
        return f"PASS_{inp.upper()}" if inp != "audit" else "FAIL"

    def better_solver(inp: str) -> str:
        return f"PASS_{inp.upper()}"

    def regressed_solver(inp: str) -> str:
        return "PASS_LOGIN" if inp == "login" else "FAIL"

    # 1. Positive: candidate improves pass rate (0.8 -> 1.0) and passes critic -> accepted
    acc = harness.evaluate_candidate(
        baseline_solver=baseline_solver,
        candidate_solver=better_solver,
        critic_scores={"correctness": 0.95, "safety": 0.90},
    )
    assert isinstance(acc, EvalSuiteResultDTO)
    assert acc.verdict == "accepted"
    assert acc.baseline_pass_rate == 0.8
    assert acc.pass_rate == 1.0
    assert acc.passed_cases == 5
    assert acc.failed_cases == 0
    assert acc.critic_score >= 0.9
    with pytest.raises(FrozenInstanceError):
        acc.verdict = "rejected_critic"  # type: ignore[misc]

    # 2. Negative: candidate regresses pass rate -> rejected_regression
    reg = harness.evaluate_candidate(
        baseline_solver=better_solver,
        candidate_solver=regressed_solver,
        critic_scores={"correctness": 0.95, "safety": 0.95},
    )
    assert reg.verdict == "rejected_regression"
    assert reg.pass_rate < reg.baseline_pass_rate

    # 3. Negative: candidate improves pass rate but critic vetoes -> rejected_critic
    vetoed = harness.evaluate_candidate(
        baseline_solver=baseline_solver,
        candidate_solver=better_solver,
        critic_scores={"correctness": 0.5, "safety": 0.5},
    )
    assert vetoed.verdict == "rejected_critic"

    # 4. Boundary: identical pass rate -> no_improvement
    same = harness.evaluate_candidate(
        baseline_solver=better_solver,
        candidate_solver=better_solver,
        critic_scores={"correctness": 0.9, "safety": 0.9},
    )
    assert same.verdict == "no_improvement"

    # 5. CAMEL SelfImprovingTraceLoop (CoT rejection/refinement)
    cot_loop = SelfImprovingTraceLoop(max_rounds=3, min_reward=0.85)
    refined = cot_loop.refine(
        initial_trace="Step 1: guess locator",
        reward_fn=lambda tr: 0.92 if "VERIFY_AOM" in tr else 0.40,
        improve_fn=lambda tr, r: tr + (" -> VERIFY_AOM" if r >= 2 else " -> check dom"),
    )
    assert refined["converged"] is True
    assert refined["rounds"] == 2
    assert refined["best_reward"] == 0.92

    # 6. CAMEL Workforce failure escalation policy (retry -> replan -> decompose)
    esc = WorkforceFailureEscalator()
    assert esc.decide_action(attempt=1, max_retries=2) == "retry"
    assert esc.decide_action(attempt=2, max_retries=2) == "replan"
    assert esc.decide_action(attempt=3, max_retries=2) == "decompose"

    # 7. Letta/Agno self-editing core memory + lossless archival overflow compaction
    with QAMemoryOS(db_path=str(tmp_path / "letta_mem.db")) as mem:
        mem.set_core("persona", {"notes": "alpha beta gamma " + ("x" * 300)})
        edited = mem.edit_core_block("persona", field="notes", old_text="alpha", new_text="ALPHA_V2")
        assert edited["notes"].startswith("ALPHA_V2 beta")

        receipt = mem.compact_core_block("persona", budget_bytes=120, project_hash="proj1")
        assert isinstance(receipt, CoreCompactionReceiptDTO)
        assert receipt.compacted is True
        assert receipt.bytes_before > 120
        assert receipt.bytes_after <= 120
        assert receipt.archived_entry_id is not None
        with pytest.raises(FrozenInstanceError):
            receipt.compacted = False  # type: ignore[misc]

        # Original full content preserved losslessly in archival tier
        archived = mem.query_archival(query="core_compaction:persona", domain="core_compaction", project_hash="proj1")
        assert len(archived) >= 1
        assert "ALPHA_V2" in str(archived[0]["action"])

        # Already within budget -> no-op compaction
        noop = mem.compact_core_block("persona", budget_bytes=500, project_hash="proj1")
        assert noop.compacted is False
        assert noop.archived_entry_id is None


def test_self_improve_and_compaction_negative_and_boundary(tmp_path: Path) -> None:
    """Negative & Boundary scenarios: empty suite, invalid weights/thresholds, invalid compaction budget, missing block."""
    with pytest.raises(ValueError, match="suite_name"):
        EvalRegressionSuite("   ", [])
    with pytest.raises(ValueError, match="weights"):
        CriticRubricEvaluator(weights={})
    with pytest.raises(ValueError, match="veto_threshold"):
        CriticRubricEvaluator(weights={"a": 1.0}, veto_threshold=1.5)
    with pytest.raises(ValueError, match="max_rounds"):
        SelfImprovingTraceLoop(max_rounds=0)

    # Empty suite boundary
    empty_suite = EvalRegressionSuite("empty", [])
    res = empty_suite.run(lambda s: s)
    assert res["total_cases"] == 0
    assert res["pass_rate"] == 0.0

    # SelfImprovingTraceLoop non-convergent boundary
    loop = SelfImprovingTraceLoop(max_rounds=2, min_reward=0.95)
    out = loop.refine("seed", reward_fn=lambda _t: 0.3, improve_fn=lambda t, r: f"{t}_{r}")
    assert out["converged"] is False
    assert out["rounds"] == 2

    # QAMemoryOS negative guards
    with QAMemoryOS(db_path=str(tmp_path / "neg_mem.db")) as mem:
        with pytest.raises(KeyError):
            mem.edit_core_block("missing_block", field="notes", old_text="a", new_text="b")
        with pytest.raises(ValueError, match="budget_bytes"):
            mem.compact_core_block("missing_block", budget_bytes=10)
        with pytest.raises(KeyError):
            mem.compact_core_block("missing_block", budget_bytes=100)


def test_self_improve_cli_json_contract(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI scenario: run --demo --json in-process and subprocess."""
    assert improve_main(["--demo", "--json"]) == 0
    in_proc = json.loads(capsys.readouterr().out)
    assert in_proc["status"] == "ok"
    assert in_proc["result"]["verdict"] == "accepted"

    assert improve_main([]) == 1

    worktree_root = Path(__file__).resolve().parents[1]
    script = str(worktree_root / "tools" / "orchestration" / "self_improve_harness.py")
    r = subprocess.run([sys.executable, script, "--demo", "--json"], capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr
    sub_data = json.loads(r.stdout)
    assert sub_data["result"]["pass_rate"] == 1.0
