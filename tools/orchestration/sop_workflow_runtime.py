#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""MetaGPT SOP Runtime + Agno Control-Flow/HITL Approval + AFlow Experience Pool.

Provides an executable `Code = SOP(Team)` role-gated pipeline enforcing required
evidence fields before stage transitions, composable control-flow steps
(`ConditionStep`, `LoopStep`, `RouterStep`), human-in-the-loop `ApprovalGate`
pause/resume receipts, and an AFlow-style UCB1 `ExperiencePool`.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
import os
import sys
from typing import Any, Callable, Dict, List, Literal, Optional, Sequence
import uuid

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass

from tools.core.sop_schema import QASOPWorkflow, SOPStageDefinition, validate_sop_workflow

ApprovalDecision = Literal["pending", "approved", "rejected"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ApprovalReceiptDTO:
    gate_id: str
    stage_id: str
    decision: ApprovalDecision
    approver: str
    reason: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExperienceRecordDTO:
    exp_id: str
    workflow_key: str
    score: float
    visits: int
    ucb1_priority: float
    summary: str
    perfect: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ApprovalGate:
    """Agno-inspired Human-in-the-Loop pause/resume approval gate."""

    def __init__(self, gate_id: str, stage_id: str) -> None:
        if not isinstance(gate_id, str) or not gate_id.strip():
            raise ValueError("gate_id must be a non-empty string.")
        if not isinstance(stage_id, str) or not stage_id.strip():
            raise ValueError("stage_id must be a non-empty string.")
        self.gate_id = gate_id.strip()
        self.stage_id = stage_id.strip()

    def request_approval(self, reason: str = "") -> ApprovalReceiptDTO:
        return ApprovalReceiptDTO(
            gate_id=self.gate_id,
            stage_id=self.stage_id,
            decision="pending",
            approver="unassigned",
            reason=str(reason),
            timestamp=_utc_now_iso(),
        )

    def resolve(self, decision: ApprovalDecision, approver: str, reason: str = "") -> ApprovalReceiptDTO:
        if decision not in ("approved", "rejected"):
            raise ValueError("Resolved approval decision must be 'approved' or 'rejected'.")
        if not isinstance(approver, str) or not approver.strip():
            raise ValueError("approver must be a non-empty string.")
        return ApprovalReceiptDTO(
            gate_id=self.gate_id,
            stage_id=self.stage_id,
            decision=decision,
            approver=approver.strip(),
            reason=str(reason),
            timestamp=_utc_now_iso(),
        )


class ConditionStep:
    """Composable branching control-flow step."""

    def __init__(
        self,
        predicate: Callable[[Dict[str, Any]], bool],
        on_true: Callable[[Dict[str, Any]], Any],
        on_false: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> None:
        self.predicate = predicate
        self.on_true = on_true
        self.on_false = on_false

    def run(self, context: Dict[str, Any]) -> Any:
        if self.predicate(context):
            return self.on_true(context)
        if self.on_false is not None:
            return self.on_false(context)
        return None


class LoopStep:
    """Bounded iterative control-flow loop with explicit end condition and hard cap."""

    def __init__(
        self,
        body: Callable[[Dict[str, Any], int], Any],
        end_condition: Callable[[Dict[str, Any], int], bool],
        max_iterations: int = 5,
    ) -> None:
        if int(max_iterations) <= 0:
            raise ValueError("max_iterations must be a positive integer.")
        self.body = body
        self.end_condition = end_condition
        self.max_iterations = int(max_iterations)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        iterations = 0
        stopped_by_condition = False
        last_result: Any = None
        for idx in range(1, self.max_iterations + 1):
            iterations = idx
            last_result = self.body(context, idx)
            if self.end_condition(context, idx):
                stopped_by_condition = True
                break
        return {
            "iterations": iterations,
            "stopped_by_condition": stopped_by_condition,
            "last_result": last_result,
        }


class RouterStep:
    """Dynamic route dispatcher."""

    def __init__(
        self,
        selector: Callable[[Dict[str, Any]], str],
        routes: Dict[str, Callable[[Dict[str, Any]], Any]],
    ) -> None:
        self.selector = selector
        self.routes = dict(routes)

    def run(self, context: Dict[str, Any]) -> Any:
        route_key = self.selector(context)
        if route_key not in self.routes:
            raise KeyError(f"Route '{route_key}' is not registered.")
        return self.routes[route_key](context)


class ExperiencePool:
    """AFlow-inspired scored workflow archive with UCB1 selection & PerfectJudge threshold."""

    def __init__(self, perfect_threshold: float = 0.95, exploration_c: float = 1.414) -> None:
        self.perfect_threshold = float(perfect_threshold)
        self.exploration_c = float(exploration_c)
        self._stats: Dict[str, Dict[str, Any]] = {}
        self._total_visits = 0

    def record(self, workflow_key: str, score: float, summary: str) -> ExperienceRecordDTO:
        if not isinstance(workflow_key, str) or not workflow_key.strip():
            raise ValueError("workflow_key must be a non-empty string.")
        sc = float(score)
        if sc < 0.0 or sc > 1.0:
            raise ValueError("score must be between 0.0 and 1.0.")
        key = workflow_key.strip()
        self._total_visits += 1
        entry = self._stats.get(key)
        if entry is None:
            entry = {
                "exp_id": f"exp_{uuid.uuid4().hex[:10]}",
                "workflow_key": key,
                "score_sum": sc,
                "visits": 1,
                "summary": str(summary),
            }
            self._stats[key] = entry
        else:
            entry["score_sum"] += sc
            entry["visits"] += 1
            entry["summary"] = str(summary)
        return self._build_dto(entry)

    def _build_dto(self, entry: Dict[str, Any]) -> ExperienceRecordDTO:
        visits = int(entry["visits"])
        mean_score = round(float(entry["score_sum"]) / float(visits), 4)
        ucb_bonus = self.exploration_c * math.sqrt(math.log(max(1, self._total_visits)) / float(visits))
        priority = round(mean_score + ucb_bonus, 4)
        return ExperienceRecordDTO(
            exp_id=entry["exp_id"],
            workflow_key=entry["workflow_key"],
            score=mean_score,
            visits=visits,
            ucb1_priority=priority,
            summary=entry["summary"],
            perfect=mean_score >= self.perfect_threshold,
        )

    def list_records(self) -> List[ExperienceRecordDTO]:
        return [self._build_dto(e) for e in self._stats.values()]

    def select_best_ucb1(self) -> Optional[ExperienceRecordDTO]:
        records = self.list_records()
        if not records:
            return None
        return max(records, key=lambda r: (r.ucb1_priority, r.score, r.workflow_key))


class SOPWorkflowRuntime:
    """MetaGPT-inspired role-gated SOP workflow executor with fail-closed evidence & HITL checks."""

    def __init__(self, workflow: QASOPWorkflow, experience_pool: Optional[ExperiencePool] = None) -> None:
        valid, errors = validate_sop_workflow(workflow)
        if not valid:
            raise ValueError(f"Invalid SOP workflow: {'; '.join(errors)}")
        self.workflow = workflow
        self.current_stage = workflow.initial_stage
        self.experience_pool = experience_pool or ExperiencePool()
        self.history: List[Dict[str, Any]] = []

    def advance(
        self,
        next_stage: str,
        evidence: Dict[str, Any],
        approval_receipt: Optional[ApprovalReceiptDTO] = None,
    ) -> Dict[str, Any]:
        cur_def = self.workflow.stages[self.current_stage]
        if next_stage not in cur_def.transitions:
            return {
                "allowed": False,
                "current_stage": self.current_stage,
                "requested_stage": next_stage,
                "reason": f"Transition '{self.current_stage}' -> '{next_stage}' is not declared in SOP.",
                "missing_evidence": [],
                "approval_status": "not_required",
                "completed": False,
            }

        missing = [f for f in cur_def.required_evidence_fields if f not in evidence or evidence[f] is None]
        if missing:
            return {
                "allowed": False,
                "current_stage": self.current_stage,
                "requested_stage": next_stage,
                "reason": "Missing required stage evidence fields.",
                "missing_evidence": missing,
                "approval_status": "blocked_evidence",
                "completed": False,
            }

        approval_status = "not_required"
        if getattr(cur_def, "approval_required", False):
            if approval_receipt is None:
                return {
                    "allowed": False,
                    "current_stage": self.current_stage,
                    "requested_stage": next_stage,
                    "reason": f"HITL approval required for stage '{self.current_stage}'.",
                    "missing_evidence": [],
                    "approval_status": "pending",
                    "completed": False,
                }
            if approval_receipt.stage_id != self.current_stage or approval_receipt.decision != "approved":
                return {
                    "allowed": False,
                    "current_stage": self.current_stage,
                    "requested_stage": next_stage,
                    "reason": f"HITL approval not granted (decision={approval_receipt.decision}).",
                    "missing_evidence": [],
                    "approval_status": approval_receipt.decision,
                    "completed": False,
                }
            approval_status = "approved"

        prev_stage = self.current_stage
        self.current_stage = next_stage
        completed = bool(self.workflow.final_stage and self.current_stage == self.workflow.final_stage)
        record = {
            "from_stage": prev_stage,
            "to_stage": next_stage,
            "actor_role": cur_def.actor_role,
            "approval_status": approval_status,
            "timestamp": _utc_now_iso(),
        }
        self.history.append(record)
        return {
            "allowed": True,
            "current_stage": self.current_stage,
            "requested_stage": next_stage,
            "missing_evidence": [],
            "approval_status": approval_status,
            "completed": completed,
        }


def run_demo_sop() -> Dict[str, Any]:
    wf = QASOPWorkflow(
        sop_id="demo_team_sop",
        version="2.0.0",
        title="Demo PM->Architect->Engineer->QA SOP",
        description="Deterministic verification demo",
        initial_stage="pm_prd",
        final_stage="qa_signoff",
        stages={
            "pm_prd": SOPStageDefinition("pm_prd", "PM", "PRD", ["prd_hash"], ["arch_design"]),
            "arch_design": SOPStageDefinition("arch_design", "ARCHITECT", "Design", ["spec"], ["eng_impl"], approval_required=True),
            "eng_impl": SOPStageDefinition("eng_impl", "ENGINEER", "Impl", ["tests_ok"], ["qa_signoff"]),
            "qa_signoff": SOPStageDefinition("qa_signoff", "QA", "DoD", ["mutation_ok"], []),
        },
    )
    pool = ExperiencePool()
    rt = SOPWorkflowRuntime(wf, experience_pool=pool)
    rt.advance("arch_design", {"prd_hash": "sha256_demo"})
    gate = ApprovalGate("demo_gate", "arch_design")
    approved = gate.resolve("approved", approver="tech_lead", reason="verified")
    rt.advance("eng_impl", {"spec": "typed_dto_v1"}, approval_receipt=approved)
    final_res = rt.advance("qa_signoff", {"tests_ok": True})
    pool.record("demo_team_sop", 0.96, "Completed PM->QA SOP cleanly")
    return {
        "status": "ok",
        "current_stage": rt.current_stage,
        "completed": final_res["completed"],
        "history_len": len(rt.history),
        "experience_count": len(pool.list_records()),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Synapse Hub MetaGPT SOP & Agno HITL Workflow Runtime")
    parser.add_argument("--demo", action="store_true", help="Run deterministic PM->Architect->Engineer->QA SOP demo")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.demo:
        parser.print_help()
        return 1
    payload = run_demo_sop()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
