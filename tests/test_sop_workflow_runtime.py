# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""4-scenario verification suite for M5: MetaGPT SOP Runtime, Agno Control-Flow/HITL & AFlow ExperiencePool."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.core.sop_schema import QASOPWorkflow, SOPStageDefinition, validate_sop_workflow
from tools.orchestration.sop_workflow_runtime import (
    ApprovalGate,
    ApprovalReceiptDTO,
    ConditionStep,
    ExperiencePool,
    ExperienceRecordDTO,
    LoopStep,
    RouterStep,
    SOPWorkflowRuntime,
    main as sop_main,
)


def _build_team_sop() -> QASOPWorkflow:
    return QASOPWorkflow(
        sop_id="qa_delivery_sop",
        version="2.0.0",
        title="MetaGPT Role-Gated QA Delivery SOP",
        description="Enforces PM -> Architect -> Engineer -> QA with HITL gate",
        initial_stage="pm_prd",
        final_stage="qa_signoff",
        stages={
            "pm_prd": SOPStageDefinition(
                stage_id="pm_prd",
                actor_role="PM",
                description="Author PRD & acceptance criteria",
                required_evidence_fields=["prd_hash", "ac_count"],
                transitions=["arch_design"],
            ),
            "arch_design": SOPStageDefinition(
                stage_id="arch_design",
                actor_role="ARCHITECT",
                description="Lock interface contracts",
                required_evidence_fields=["interface_spec"],
                transitions=["eng_impl"],
                approval_required=True,
            ),
            "eng_impl": SOPStageDefinition(
                stage_id="eng_impl",
                actor_role="ENGINEER",
                description="Implement with unit tests",
                required_evidence_fields=["pytest_exit_code"],
                transitions=["qa_signoff"],
            ),
            "qa_signoff": SOPStageDefinition(
                stage_id="qa_signoff",
                actor_role="QA",
                description="Final DoD verification",
                required_evidence_fields=["mutation_score"],
                transitions=[],
            ),
        },
    )


def test_sop_hitl_and_experience_pool() -> None:
    """Positive + Negative scenario: PM->Arch->Eng->QA evidence gate, HITL pause/resume, control-flow, UCB1."""
    wf = _build_team_sop()
    valid, errs = validate_sop_workflow(wf)
    assert valid is True, errs

    pool = ExperiencePool()
    rt = SOPWorkflowRuntime(wf, experience_pool=pool)
    assert rt.experience_pool is pool
    assert isinstance(SOPWorkflowRuntime(wf).experience_pool, ExperiencePool)
    assert rt.current_stage == "pm_prd"

    # Negative: missing required evidence blocks transition fail-closed
    blocked = rt.advance("arch_design", evidence={"prd_hash": "abc"})
    assert blocked["allowed"] is False
    assert "ac_count" in blocked["missing_evidence"]
    assert rt.current_stage == "pm_prd"

    # Positive: supply full evidence -> advances to arch_design
    step1 = rt.advance("arch_design", evidence={"prd_hash": "abc", "ac_count": 5})
    assert step1["allowed"] is True
    assert rt.current_stage == "arch_design"

    # HITL gate on arch_design (approval_required=True): pending blocks advance
    gate = ApprovalGate("gate_arch", "arch_design")
    pending = gate.request_approval("Verify interface contracts")
    assert isinstance(pending, ApprovalReceiptDTO)
    assert pending.decision == "pending"
    with pytest.raises(FrozenInstanceError):
        pending.decision = "approved"  # type: ignore[misc]

    paused = rt.advance("eng_impl", evidence={"interface_spec": "v1"}, approval_receipt=pending)
    assert paused["allowed"] is False
    assert paused["approval_status"] == "pending"
    assert rt.current_stage == "arch_design"

    # Rejected approval also fails closed
    rejected = gate.resolve("rejected", approver="lead_arch", reason="Missing rollback")
    assert rejected.decision == "rejected"
    rej_res = rt.advance("eng_impl", evidence={"interface_spec": "v1"}, approval_receipt=rejected)
    assert rej_res["allowed"] is False
    assert rej_res["approval_status"] == "rejected"

    # Approved receipt unblocks transition -> eng_impl -> qa_signoff
    approved = gate.resolve("approved", approver="lead_arch", reason="LGTM")
    res_eng = rt.advance("eng_impl", evidence={"interface_spec": "v1"}, approval_receipt=approved)
    assert res_eng["allowed"] is True
    assert rt.current_stage == "eng_impl"

    res_qa = rt.advance("qa_signoff", evidence={"pytest_exit_code": 0})
    assert res_qa["allowed"] is True
    assert rt.current_stage == "qa_signoff"
    assert res_qa["completed"] is True

    # Agno control-flow primitives: ConditionStep, LoopStep, RouterStep
    c_true = ConditionStep(lambda ctx: ctx["score"] >= 0.8, lambda ctx: "promote", lambda ctx: "retry")
    assert c_true.run({"score": 0.9}) == "promote"
    assert c_true.run({"score": 0.5}) == "retry"

    loop = LoopStep(
        body=lambda ctx, i: ctx.__setitem__("count", ctx.get("count", 0) + 1),
        end_condition=lambda ctx, _i: ctx.get("count", 0) >= 3,
        max_iterations=5,
    )
    loop_ctx: dict[str, int] = {}
    loop_res = loop.run(loop_ctx)
    assert loop_res["iterations"] == 3
    assert loop_res["stopped_by_condition"] is True
    assert loop_ctx["count"] == 3

    router = RouterStep(
        selector=lambda ctx: ctx["tier"],
        routes={"fast": lambda _c: "tier0", "deep": lambda _c: "tier2"},
    )
    assert router.run({"tier": "deep"}) == "tier2"

    # AFlow ExperiencePool UCB1 scoring & PerfectJudge threshold
    r1 = pool.record("wf_a", 0.70, "baseline")
    r2 = pool.record("wf_b", 0.96, "perfect candidate")
    assert isinstance(r1, ExperienceRecordDTO)
    assert ExperienceRecordDTO("e0", "k0", 0.5, 1, 0.5, "s").perfect is False
    assert r1.perfect is False
    assert r2.perfect is True
    assert r2.ucb1_priority > r2.score
    with pytest.raises(FrozenInstanceError):
        r2.score = 0.0  # type: ignore[misc]
    best = pool.select_best_ucb1()
    assert best is not None and best.workflow_key == "wf_b"


def test_sop_negative_and_boundary() -> None:
    """Negative & Boundary scenarios: unreachable final_stage, loop cap, unknown route, invalid threshold/cap."""
    unreachable_wf = QASOPWorkflow(
        sop_id="broken_sop",
        version="1.0.0",
        title="Broken",
        description="",
        initial_stage="s1",
        final_stage="s3",
        stages={
            "s1": SOPStageDefinition("s1", "PM", "", [], ["s2"]),
            "s2": SOPStageDefinition("s2", "ENG", "", [], []),
            "s3": SOPStageDefinition("s3", "QA", "", [], []),
        },
    )
    ok, errs = validate_sop_workflow(unreachable_wf)
    assert ok is False
    assert any("reachable" in e.lower() for e in errs)

    # Disallowed transition rejected
    rt = SOPWorkflowRuntime(_build_team_sop())
    bad_jump = rt.advance("qa_signoff", evidence={"prd_hash": "a", "ac_count": 1})
    assert bad_jump["allowed"] is False

    # LoopStep hard max_iterations cap
    with pytest.raises(ValueError, match="max_iterations"):
        LoopStep(body=lambda _c, _i: None, end_condition=lambda _c, _i: False, max_iterations=0)

    capped = LoopStep(
        body=lambda ctx, _i: ctx.__setitem__("n", ctx.get("n", 0) + 1),
        end_condition=lambda _ctx, _i: False,
        max_iterations=2,
    )
    cap_ctx: dict[str, int] = {}
    cap_res = capped.run(cap_ctx)
    assert cap_res["iterations"] == 2
    assert cap_res["stopped_by_condition"] is False

    # RouterStep unknown route raises KeyError
    router = RouterStep(selector=lambda _c: "missing", routes={"a": lambda _c: 1})
    with pytest.raises(KeyError):
        router.run({})

    # ExperiencePool empty & invalid bounds + ApprovalGate empty ID/approver guards
    with pytest.raises(ValueError, match="gate_id"):
        ApprovalGate("   ", "arch_design")
    with pytest.raises(ValueError, match="stage_id"):
        ApprovalGate("g1", "   ")
    with pytest.raises(ValueError, match="approver"):
        ApprovalGate("g1", "arch_design").resolve("approved", approver="   ")

    empty_pool = ExperiencePool()
    assert empty_pool.select_best_ucb1() is None
    with pytest.raises(ValueError, match="workflow_key"):
        empty_pool.record("   ", 0.5, "empty key")
    with pytest.raises(ValueError, match="score"):
        empty_pool.record("wf_x", 1.5, "out of range")


def test_sop_runtime_cli_json_contract(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI scenario: run demo SOP workflow via --demo --json (in-process + subprocess)."""
    assert sop_main(["--demo", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["current_stage"] == "qa_signoff"
    assert out["completed"] is True

    worktree_root = Path(__file__).resolve().parents[1]
    script = str(worktree_root / "tools" / "orchestration" / "sop_workflow_runtime.py")
    r = subprocess.run([sys.executable, script, "--demo", "--json"], capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr
    sub_data = json.loads(r.stdout)
    assert sub_data["experience_count"] >= 1
