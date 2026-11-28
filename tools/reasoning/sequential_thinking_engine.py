#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/reasoning/sequential_thinking_engine.py
---------------------------------------------
Stdlib Sequential Thinking, ToT Beam Pruner, Ulysses Protocol & OODA Loop Engine.
Harvests core state machines from:
  - modelcontextprotocol/servers (sequentialthinking: revision, branching, eras, item caps)
  - princeton-nlp/tree-of-thought-llm (BFS/Beam propose -> score/vote -> top-k prune)
  - waldzellai/clearthought-onepointfive (Ulysses Protocol hard escalation & OODA Loop)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Literal, Optional, Sequence

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

UlyssesPhase = Literal["plan", "execute", "verify", "escalate", "complete"]
OODAPhase = Literal["observe", "orient", "decide", "act"]
OODA_ORDER: Sequence[OODAPhase] = ("observe", "orient", "decide", "act")


@dataclass(frozen=True)
class ThoughtStepDTO:
    thought_number: int
    total_thoughts: int
    content: str
    next_thought_needed: bool
    is_revision: bool = False
    revises_thought: Optional[int] = None
    branch_from_thought: Optional[int] = None
    branch_id: Optional[str] = None
    beam_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UlyssesGateResultDTO:
    session_id: str
    phase: UlyssesPhase
    iteration: int
    max_iterations: int
    elapsed_sec: float
    time_budget_sec: float
    must_escalate: bool
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SequentialThinkingSession:
    """Stateful sequential thought tracker with revision, branching, and era resets."""

    def __init__(self, session_id: str = "default", max_thought_chars: int = 4000) -> None:
        if max_thought_chars <= 0:
            raise ValueError("max_thought_chars must be positive")
        self.session_id = session_id
        self.max_thought_chars = max_thought_chars
        self.era: int = 1
        self.history: List[ThoughtStepDTO] = []
        self.branches: Dict[str, List[ThoughtStepDTO]] = {}

    def reset_era(self) -> int:
        self.era += 1
        self.history.clear()
        self.branches.clear()
        return self.era

    def record_thought(
        self,
        thought_number: int,
        total_thoughts: int,
        content: str,
        next_thought_needed: bool = True,
        is_revision: bool = False,
        revises_thought: Optional[int] = None,
        branch_from_thought: Optional[int] = None,
        branch_id: Optional[str] = None,
        beam_score: Optional[float] = None,
    ) -> ThoughtStepDTO:
        clean = (content or "").strip()
        if not clean:
            raise ValueError("content must be non-empty")
        if len(clean) > self.max_thought_chars:
            raise ValueError(f"content exceeds max_thought_chars ({len(clean)} > {self.max_thought_chars})")
        if thought_number < 1 or total_thoughts < 1:
            raise ValueError("thought_number and total_thoughts must be >= 1")
        adjusted_total = max(total_thoughts, thought_number)

        existing_numbers = {t.thought_number for t in self.history}
        if is_revision:
            if revises_thought is None or revises_thought not in existing_numbers:
                raise ValueError(f"revises_thought ({revises_thought}) does not reference a recorded thought")
        if branch_from_thought is not None and branch_from_thought not in existing_numbers:
            raise ValueError(f"branch_from_thought ({branch_from_thought}) does not reference a recorded thought")

        step = ThoughtStepDTO(
            thought_number=thought_number,
            total_thoughts=adjusted_total,
            content=clean,
            next_thought_needed=bool(next_thought_needed),
            is_revision=bool(is_revision),
            revises_thought=revises_thought if is_revision else None,
            branch_from_thought=branch_from_thought,
            branch_id=branch_id,
            beam_score=beam_score,
        )
        self.history.append(step)
        if branch_id:
            self.branches.setdefault(branch_id, []).append(step)
        return step

    def export_markdown(self) -> str:
        lines = [f"# Sequential Thinking Trace (`{self.session_id}` | Era {self.era})"]
        for step in self.history:
            tags: List[str] = []
            if step.is_revision:
                tags.append(f"revises #{step.revises_thought}")
            if step.branch_id:
                tags.append(f"branch:{step.branch_id}")
            if step.beam_score is not None:
                tags.append(f"score:{step.beam_score:.3f}")
            suffix = f" [{', '.join(tags)}]" if tags else ""
            lines.append(f"{step.thought_number}/{step.total_thoughts}{suffix}: {step.content}")
        return "\n".join(lines)


class UlyssesProtocolSession:
    """Time-boxed, iteration-capped hard-gate debug protocol (aligned with Invariant 13)."""

    def __init__(
        self,
        session_id: str = "default",
        max_iterations: int = 2,
        time_budget_sec: float = 180.0,
    ) -> None:
        if max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        if time_budget_sec <= 0:
            raise ValueError("time_budget_sec must be positive")
        self.session_id = session_id
        self.max_iterations = max_iterations
        self.time_budget_sec = float(time_budget_sec)
        self.iteration = 0
        self.elapsed_sec = 0.0
        self.logs: List[Dict[str, Any]] = []

    def step(
        self,
        phase: UlyssesPhase = "execute",
        elapsed_sec: float = 0.0,
        summary: str = "",
    ) -> UlyssesGateResultDTO:
        if elapsed_sec < 0:
            raise ValueError("elapsed_sec cannot be negative")
        self.iteration += 1
        self.elapsed_sec += float(elapsed_sec)
        self.logs.append({"iteration": self.iteration, "phase": phase, "elapsed_sec": self.elapsed_sec, "summary": summary})

        if self.elapsed_sec >= self.time_budget_sec:
            return UlyssesGateResultDTO(
                session_id=self.session_id,
                phase="escalate",
                iteration=self.iteration,
                max_iterations=self.max_iterations,
                elapsed_sec=round(self.elapsed_sec, 3),
                time_budget_sec=self.time_budget_sec,
                must_escalate=True,
                reason=f"Time budget exhausted ({self.elapsed_sec:.2f}s >= {self.time_budget_sec:.2f}s).",
            )
        if self.iteration >= self.max_iterations and phase != "complete":
            return UlyssesGateResultDTO(
                session_id=self.session_id,
                phase="escalate",
                iteration=self.iteration,
                max_iterations=self.max_iterations,
                elapsed_sec=round(self.elapsed_sec, 3),
                time_budget_sec=self.time_budget_sec,
                must_escalate=True,
                reason=f"Max iteration cap reached ({self.iteration}/{self.max_iterations}); circuit breaker triggered.",
            )
        return UlyssesGateResultDTO(
            session_id=self.session_id,
            phase=phase,
            iteration=self.iteration,
            max_iterations=self.max_iterations,
            elapsed_sec=round(self.elapsed_sec, 3),
            time_budget_sec=self.time_budget_sec,
            must_escalate=False,
            reason="Within iteration and time-box constraints.",
        )


class OODALoopSession:
    """Observe-Orient-Decide-Act rapid triage cycle with min_evidence gating."""

    def __init__(self, session_id: str = "default", min_evidence: int = 2) -> None:
        if min_evidence < 1:
            raise ValueError("min_evidence must be >= 1")
        self.session_id = session_id
        self.min_evidence = min_evidence
        self.phase_index = 0
        self.cycle_count = 1
        self.active_hypotheses: List[str] = []

    @property
    def current_phase(self) -> OODAPhase:
        return OODA_ORDER[self.phase_index]

    def advance(self, evidence: Sequence[str], hypothesis: Optional[str] = None) -> Dict[str, Any]:
        clean_evidence = [str(e).strip() for e in evidence if str(e).strip()]
        if hypothesis and hypothesis.strip() and hypothesis.strip() not in self.active_hypotheses:
            self.active_hypotheses.append(hypothesis.strip())

        if self.current_phase == "observe" and len(clean_evidence) < self.min_evidence:
            return {
                "session_id": self.session_id,
                "cycle": self.cycle_count,
                "phase": self.current_phase,
                "advanced": False,
                "evidence_count": len(clean_evidence),
                "min_evidence": self.min_evidence,
                "active_hypotheses": list(self.active_hypotheses),
                "reason": f"Blocked: min_evidence gate requires >= {self.min_evidence} observations (got {len(clean_evidence)}).",
            }

        prev_phase = self.current_phase
        self.phase_index += 1
        if self.phase_index >= len(OODA_ORDER):
            self.phase_index = 0
            self.cycle_count += 1
        return {
            "session_id": self.session_id,
            "cycle": self.cycle_count,
            "previous_phase": prev_phase,
            "phase": self.current_phase,
            "advanced": True,
            "evidence_count": len(clean_evidence),
            "min_evidence": self.min_evidence,
            "active_hypotheses": list(self.active_hypotheses),
            "reason": f"Advanced from {prev_phase} to {self.current_phase}.",
        }


def beam_prune_branches(
    candidates: Sequence[Dict[str, Any]],
    beam_width: int = 2,
) -> List[Dict[str, Any]]:
    """Tree-of-Thoughts BFS/Beam candidate evaluator (propose -> score/vote -> top-k prune)."""
    if beam_width < 1:
        raise ValueError("beam_width must be >= 1")
    if not candidates:
        return []

    scored: List[Dict[str, Any]] = []
    for idx, cand in enumerate(candidates):
        votes = cand.get("votes")
        if isinstance(votes, (list, tuple)) and votes:
            numeric = [float(v) for v in votes]
            beam_score = sum(numeric) / len(numeric)
        else:
            beam_score = float(cand.get("score", 0.0))
        enriched = dict(cand)
        enriched["beam_score"] = round(beam_score, 6)
        enriched["_orig_idx"] = idx
        scored.append(enriched)

    scored.sort(key=lambda item: (-item["beam_score"], item["_orig_idx"]))
    selected = scored[:beam_width]
    for item in selected:
        item.pop("_orig_idx", None)
    return selected


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synapse Hub Sequential Thinking, ToT, Ulysses & OODA Engine")
    sub = parser.add_subparsers(dest="command")

    p_think = sub.add_parser("think", help="Record a structured thought step")
    p_think.add_argument("--session", default="default")
    p_think.add_argument("--thought", required=True)
    p_think.add_argument("--number", type=int, default=1)
    p_think.add_argument("--total", type=int, default=1)
    p_think.add_argument("--branch-id", default=None)
    p_think.add_argument("--json", action="store_true")

    p_ul = sub.add_parser("ulysses", help="Evaluate Ulysses Protocol escalation gate")
    p_ul.add_argument("--session", default="default")
    p_ul.add_argument("--iteration", type=int, default=1)
    p_ul.add_argument("--max-iterations", type=int, default=2)
    p_ul.add_argument("--elapsed", type=float, default=0.0)
    p_ul.add_argument("--budget", type=float, default=180.0)
    p_ul.add_argument("--json", action="store_true")

    p_beam = sub.add_parser("beam", help="Beam-prune JSON candidate proposals")
    p_beam.add_argument("--candidates-json", required=True)
    p_beam.add_argument("--width", type=int, default=2)
    p_beam.add_argument("--json", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "think":
            sess = SequentialThinkingSession(session_id=args.session)
            step = sess.record_thought(
                thought_number=args.number,
                total_thoughts=args.total,
                content=args.thought,
                next_thought_needed=args.number < args.total,
                branch_id=args.branch_id,
            )
            payload: Any = step.to_dict()
        elif args.command == "ulysses":
            u = UlyssesProtocolSession(
                session_id=args.session,
                max_iterations=args.max_iterations,
                time_budget_sec=args.budget,
            )
            u.iteration = max(0, args.iteration - 1)
            res = u.step(phase="execute", elapsed_sec=args.elapsed)
            payload = res.to_dict()
        elif args.command == "beam":
            cands = json.loads(args.candidates_json)
            payload = {"selected": beam_prune_branches(cands, beam_width=args.width)}
        else:
            return 1
    except (ValueError, json.JSONDecodeError) as exc:
        err = {"ok": False, "error": str(exc)}
        print(json.dumps(err, indent=2) if getattr(args, "json", False) else f"Error: {exc}")
        return 1

    print(json.dumps(payload, indent=2) if getattr(args, "json", False) else json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
