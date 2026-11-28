#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/reasoning/structured_reasoning_engine.py
----------------------------------------------
Anti-Sycophancy Challenge, 7-Level Monotonic Confidence Debug Gate,
Stance-Assigned Multi-Perspective Debate & 6-Direction Progressive Elicitation Engine.
Harvests core mechanisms from:
  - BeehiveInnovations/pal-mcp-server (challenge, consensus stances, 7-level debug confidence)
  - bmad-code-org/BMAD-METHOD (6-direction progressive-disclosure elicitation catalog)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ConfidenceLevel = Literal["exploring", "low", "medium", "high", "very_high", "almost_certain", "certain"]
ElicitationDirection = Literal["wrong", "missing", "premise", "future", "other-side", "simplify"]
StanceType = Literal["for", "against", "neutral"]

CONFIDENCE_ORDER: Tuple[ConfidenceLevel, ...] = (
    "exploring",
    "low",
    "medium",
    "high",
    "very_high",
    "almost_certain",
    "certain",
)
VALID_DIRECTIONS: Tuple[ElicitationDirection, ...] = (
    "wrong",
    "missing",
    "premise",
    "future",
    "other-side",
    "simplify",
)
VALID_STANCES: Tuple[StanceType, ...] = ("for", "against", "neutral")

SYCOPHANCY_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"\byou(?:'re|\s+are)\s+(?:absolutely|totally|completely|100%)\s+right\b", re.IGNORECASE),
    re.compile(r"\bgreat\s+catch\s*[!,]\s*(?:let'?s|we\s+should)\s+(?:skip|drop|bypass)\b", re.IGNORECASE),
    re.compile(r"\b(?:skip|drop|bypass|disable)\s+(?:tests?|validation|checks?|verification)\b", re.IGNORECASE),
    re.compile(r"\bno\s+need\s+to\s+(?:test|verify|check)\b", re.IGNORECASE),
)

DEFAULT_CATALOG_PATH = Path(_TOOLS_ROOT) / "catalogs" / "elicitation_methods.json"


@dataclass(frozen=True)
class ChallengeReportDTO:
    original_claim: str
    sycophancy_risk_detected: bool
    counter_hypotheses: Tuple[str, ...]
    missing_evidence_prompts: Tuple[str, ...]
    recommended_stance: StanceType

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["counter_hypotheses"] = list(self.counter_hypotheses)
        payload["missing_evidence_prompts"] = list(self.missing_evidence_prompts)
        return payload


@dataclass(frozen=True)
class ConfidenceTransitionDTO:
    previous_level: ConfidenceLevel
    requested_level: ConfidenceLevel
    effective_level: ConfidenceLevel
    accepted: bool
    rejection_reason: str
    evidence_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StructuredReasoningEngine:
    """Deterministic structured-reasoning guardrails with progressive catalog loading."""

    def __init__(self, catalog_path: Optional[Union[str, Path]] = None) -> None:
        self.catalog_path = Path(catalog_path) if catalog_path else DEFAULT_CATALOG_PATH
        self._catalog_cache: Optional[Dict[str, Any]] = None

    def _load_catalog(self) -> Dict[str, Any]:
        if self._catalog_cache is None:
            raw = self.catalog_path.read_text(encoding="utf-8")
            self._catalog_cache = json.loads(raw)
        return self._catalog_cache

    def challenge_claim(self, claim: str) -> ChallengeReportDTO:
        """Anti-sycophancy guard: forces counter-hypotheses and evidence prompts before agreement."""
        clean = (claim or "").strip()
        if not clean:
            raise ValueError("claim must be a non-empty string")

        sycophancy_detected = any(pat.search(clean) is not None for pat in SYCOPHANCY_PATTERNS)
        counter_hypotheses = (
            f"Falsification test: What empirical defect or regression appears if '{clean[:80]}' fails under boundary or concurrent input?",
            "Hidden-assumption check: Which unverified dependency, stale state, or silent fallback is assumed to hold?",
            "Alternative explanation: Could an orthogonal root cause explain the observed symptom with smaller blast radius?",
        )
        missing_evidence = (
            "Provide raw command output, stack trace, or reproducible minimal test proving the claim.",
            "Identify downstream callers or invariants impacted if this claim is acted upon.",
        )
        recommended_stance: StanceType = "against" if sycophancy_detected else "neutral"
        return ChallengeReportDTO(
            original_claim=clean,
            sycophancy_risk_detected=sycophancy_detected,
            counter_hypotheses=counter_hypotheses,
            missing_evidence_prompts=missing_evidence,
            recommended_stance=recommended_stance,
        )

    def evaluate_confidence_transition(
        self,
        previous_level: ConfidenceLevel,
        requested_level: ConfidenceLevel,
        evidence_count: int = 0,
        unresolved_unknowns: int = 0,
    ) -> ConfidenceTransitionDTO:
        """Enforces 7-level monotonic confidence discipline (blocks premature 'certain')."""
        if previous_level not in CONFIDENCE_ORDER:
            raise ValueError(f"Invalid previous_level: {previous_level}")
        if requested_level not in CONFIDENCE_ORDER:
            raise ValueError(f"Invalid requested_level: {requested_level}")
        if evidence_count < 0 or unresolved_unknowns < 0:
            raise ValueError("evidence_count and unresolved_unknowns must be >= 0")

        req_idx = CONFIDENCE_ORDER.index(requested_level)
        if requested_level == "certain":
            if unresolved_unknowns > 0:
                fallback: ConfidenceLevel = "almost_certain" if evidence_count >= 2 else "medium"
                return ConfidenceTransitionDTO(
                    previous_level=previous_level,
                    requested_level=requested_level,
                    effective_level=fallback,
                    accepted=False,
                    rejection_reason=f"Cannot claim 'certain' with {unresolved_unknowns} unresolved unknown(s).",
                    evidence_count=evidence_count,
                )
            if evidence_count < 2:
                cap: ConfidenceLevel = "low" if evidence_count == 0 else "medium"
                return ConfidenceTransitionDTO(
                    previous_level=previous_level,
                    requested_level=requested_level,
                    effective_level=cap,
                    accepted=False,
                    rejection_reason=f"Cannot claim 'certain' with insufficient evidence ({evidence_count} < 2).",
                    evidence_count=evidence_count,
                )
        elif req_idx >= CONFIDENCE_ORDER.index("high") and evidence_count < 1:
            return ConfidenceTransitionDTO(
                previous_level=previous_level,
                requested_level=requested_level,
                effective_level="low",
                accepted=False,
                rejection_reason=f"Confidence '{requested_level}' requires >= 1 verified evidence item.",
                evidence_count=evidence_count,
            )

        return ConfidenceTransitionDTO(
            previous_level=previous_level,
            requested_level=requested_level,
            effective_level=requested_level,
            accepted=True,
            rejection_reason="",
            evidence_count=evidence_count,
        )

    def build_stance_debate(
        self,
        topic: str,
        stances: Sequence[Tuple[str, StanceType]],
    ) -> Dict[str, Any]:
        """Builds structured stance-assigned consensus prompts (for/against/neutral)."""
        clean_topic = (topic or "").strip()
        if not clean_topic:
            raise ValueError("topic must be non-empty")
        if not stances:
            raise ValueError("At least one (model_id, stance) assignment is required")

        assignments: List[Dict[str, str]] = []
        for model_id, stance in stances:
            if stance not in VALID_STANCES:
                raise ValueError(f"Invalid stance '{stance}' for {model_id}")
            if stance == "for":
                directive = f"Argue FOR '{clean_topic}' with strongest concrete benefits and edge-case mitigations."
            elif stance == "against":
                directive = f"Argue AGAINST '{clean_topic}' exposing hidden costs, failure modes, and simpler alternatives."
            else:
                directive = f"Evaluate '{clean_topic}' neutrally, weighing trade-offs, evidence gaps, and invariants."
            assignments.append({"model_id": model_id, "stance": stance, "prompt": directive})
        return {
            "topic": clean_topic,
            "assignments": assignments,
            "synthesis_rule": "Reconcile all stances via verifiable evidence; never rubber-stamp uncontested claims.",
        }

    def list_elicitation_methods(
        self,
        direction: Optional[ElicitationDirection] = None,
        tier: Optional[Literal["core", "more"]] = None,
        allow_all: bool = False,
    ) -> List[Dict[str, Any]]:
        """Progressive-disclosure catalog query: refuses unfiltered full dump unless allow_all=True."""
        if direction is not None and direction not in VALID_DIRECTIONS:
            raise ValueError(f"Invalid direction: {direction}")
        if tier is not None and tier not in ("core", "more"):
            raise ValueError(f"Invalid tier: {tier}")
        if direction is None and tier is None and not allow_all:
            raise ValueError("Explicit filter (--direction, --tier, or allow_all=True) required to prevent context bloat.")

        methods: List[Dict[str, Any]] = list(self._load_catalog().get("methods", []))
        if direction is not None:
            methods = [m for m in methods if m.get("direction") == direction]
        if tier is not None:
            methods = [m for m in methods if m.get("tier") == tier]
        return methods

    def pick_elicitation_methods(
        self,
        count: int = 3,
        direction: Optional[ElicitationDirection] = None,
        tier: Optional[Literal["core", "more"]] = "core",
        spread: bool = True,
    ) -> List[Dict[str, Any]]:
        """Selects orthogonal elicitation methods deterministically (at most one per direction when spread=True)."""
        if count < 1:
            raise ValueError("count must be >= 1")
        pool = self.list_elicitation_methods(direction=direction, tier=tier, allow_all=(direction is None and tier is None))
        if not spread or direction is not None:
            return pool[:count]

        selected: List[Dict[str, Any]] = []
        used_directions: set[str] = set()
        for dir_key in VALID_DIRECTIONS:
            for item in pool:
                if item.get("direction") == dir_key and dir_key not in used_directions:
                    selected.append(item)
                    used_directions.add(dir_key)
                    break
            if len(selected) >= count:
                break
        return selected[:count]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synapse Hub Structured Reasoning Engine")
    sub = parser.add_subparsers(dest="command")

    p_ch = sub.add_parser("challenge", help="Run anti-sycophancy challenge on a claim")
    p_ch.add_argument("--claim", required=True)
    p_ch.add_argument("--json", action="store_true")

    p_conf = sub.add_parser("confidence", help="Evaluate confidence transition gate")
    p_conf.add_argument("--prev", required=True, choices=list(CONFIDENCE_ORDER))
    p_conf.add_argument("--next", required=True, dest="requested", choices=list(CONFIDENCE_ORDER))
    p_conf.add_argument("--evidence", type=int, default=0)
    p_conf.add_argument("--unknowns", type=int, default=0)
    p_conf.add_argument("--json", action="store_true")

    p_el = sub.add_parser("elicit", help="Pick progressive-disclosure elicitation methods")
    p_el.add_argument("--direction", default=None, choices=list(VALID_DIRECTIONS))
    p_el.add_argument("--tier", default="core", choices=["core", "more"])
    p_el.add_argument("--count", type=int, default=3)
    p_el.add_argument("--spread", action="store_true")
    p_el.add_argument("--all", action="store_true", dest="allow_all")
    p_el.add_argument("--json", action="store_true")
    return parser


def _dispatch_reasoning_cli(eng: StructuredReasoningEngine, args: argparse.Namespace) -> Optional[Dict[str, Any]]:
    if args.command == "challenge":
        return eng.challenge_claim(args.claim).to_dict()
    if args.command == "confidence":
        return eng.evaluate_confidence_transition(
            previous_level=args.prev,
            requested_level=args.requested,
            evidence_count=args.evidence,
            unresolved_unknowns=args.unknowns,
        ).to_dict()
    if args.command == "elicit":
        methods = (
            eng.list_elicitation_methods(direction=args.direction, tier=None, allow_all=True)
            if args.allow_all
            else eng.pick_elicitation_methods(
                count=args.count,
                direction=args.direction,
                tier=args.tier,
                spread=args.spread,
            )
        )
        return {"count": len(methods), "methods": methods}
    return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    as_json = bool(getattr(args, "json", False))
    try:
        payload = _dispatch_reasoning_cli(StructuredReasoningEngine(), args)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2) if as_json else f"Error: {exc}")
        return 1

    if payload is None:
        return 1
    print(json.dumps(payload, indent=2) if as_json else json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
