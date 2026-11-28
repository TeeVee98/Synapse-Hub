#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/orchestration/llm_council_engine.py
-----------------------------------------
Double-Blind 3-Stage LLM Council, MARS N-Pass Consensus & PlanSearch Engine.
Harvests core mechanisms from:
  - karpathy/llm-council (Stage 1 parallel collect -> Stage 2 anonymized Response A/B/C
    peer ranking & aggregate rank calculation -> Stage 3 Chairman synthesis)
  - algorithmicsuperintelligence/optillm (MARS multi-pass verification consensus &
    PlanSearch observation-first combinatorial ideation)
Runs 100% offline/deterministic by default; opt-in live execution layers on ADR-0030
`tools/orchestration/multi_model_gateway.py`.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

RANK_LINE_PATTERN = re.compile(r"^\s*\d+\.\s*(Response\s+[A-Z])\s*$", re.IGNORECASE)
INLINE_LABEL_PATTERN = re.compile(r"\b(Response\s+[A-Z])\b", re.IGNORECASE)


@dataclass(frozen=True)
class CouncilCandidateDTO:
    model_id: str
    provider_family: str
    response_text: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CouncilVerdictDTO:
    query: str
    label_to_model: Dict[str, str]
    aggregate_rankings: Tuple[Tuple[str, float], ...]
    winner_model: str
    consensus_passes: int
    chairman_synthesis: str
    offline_mode: bool

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["aggregate_rankings"] = [
            {"model_id": m, "average_rank": r} for m, r in self.aggregate_rankings
        ]
        return payload


def parse_ranking_from_text(review_text: str, valid_labels: Sequence[str]) -> List[str]:
    """Extracts ordered anonymized labels following the 'FINAL RANKING:' sentinel."""
    if not review_text or "FINAL RANKING:" not in review_text.upper():
        return []

    valid_lookup = {lbl.upper(): lbl for lbl in valid_labels}
    idx = review_text.upper().rfind("FINAL RANKING:")
    tail = review_text[idx + len("FINAL RANKING:") :]

    parsed: List[str] = []
    for line in tail.splitlines():
        m = RANK_LINE_PATTERN.match(line)
        if m:
            norm = m.group(1).upper()
            if norm in valid_lookup and valid_lookup[norm] not in parsed:
                parsed.append(valid_lookup[norm])
    if parsed:
        return parsed

    # Fallback: extract Response X labels strictly inside the FINAL RANKING tail.
    for match in INLINE_LABEL_PATTERN.finditer(tail):
        norm = match.group(1).upper()
        if norm in valid_lookup and valid_lookup[norm] not in parsed:
            parsed.append(valid_lookup[norm])
    return parsed


class LLMCouncilEngine:
    """Double-blind peer-ranking council with MARS consensus verification."""

    def __init__(self, min_verification_passes: int = 2) -> None:
        if min_verification_passes < 1:
            raise ValueError("min_verification_passes must be >= 1")
        self.min_verification_passes = min_verification_passes

    def build_anonymized_ranking_prompt(
        self,
        query: str,
        candidates: Sequence[CouncilCandidateDTO],
    ) -> Tuple[Dict[str, str], str]:
        """Stage 2 preparation: replaces model names with Response A/B/C labels."""
        clean_query = (query or "").strip()
        if not clean_query:
            raise ValueError("query must be non-empty")
        if len(candidates) < 2:
            raise ValueError("At least 2 council candidates are required for peer ranking")

        labels = [f"Response {chr(65 + idx)}" for idx in range(len(candidates))]
        label_to_model = {
            label: cand.model_id for label, cand in zip(labels, candidates)
        }
        body_blocks = [
            f"{label}:\n{cand.response_text.strip()}"
            for label, cand in zip(labels, candidates)
        ]
        prompt = (
            f"Evaluate the following anonymized responses to the query:\n\n"
            f"Query: {clean_query}\n\n"
            + "\n\n".join(body_blocks)
            + "\n\nFirst critique each response individually, then finish with:\n"
            "FINAL RANKING:\n1. Response X\n2. Response Y"
        )
        return label_to_model, prompt

    def adjudicate_offline(
        self,
        query: str,
        candidates: Sequence[CouncilCandidateDTO],
        peer_reviews: Sequence[str],
    ) -> CouncilVerdictDTO:
        """Executes deterministic Stage 2 ranking aggregation + Stage 3 Chairman synthesis."""
        label_to_model, _ = self.build_anonymized_ranking_prompt(query, candidates)
        valid_labels = list(label_to_model.keys())
        model_order = {cand.model_id: idx for idx, cand in enumerate(candidates)}
        candidate_by_model = {cand.model_id: cand for cand in candidates}

        positions: Dict[str, List[int]] = {cand.model_id: [] for cand in candidates}
        top_votes: Dict[str, int] = {cand.model_id: 0 for cand in candidates}

        for review in peer_reviews:
            ranked_labels = parse_ranking_from_text(review, valid_labels)
            if not ranked_labels:
                continue
            for pos, label in enumerate(ranked_labels, start=1):
                model_id = label_to_model[label]
                positions[model_id].append(pos)
                if pos == 1:
                    top_votes[model_id] += 1

        fallback_rank = float(len(candidates))
        scored_models: List[Tuple[str, float]] = []
        for cand in candidates:
            ranks = positions[cand.model_id]
            avg_rank = round(sum(ranks) / len(ranks), 4) if ranks else fallback_rank
            scored_models.append((cand.model_id, avg_rank))

        # Deterministic ordering: lowest average rank wins, tie broken by input candidate order.
        scored_models.sort(key=lambda item: (item[1], model_order[item[0]]))
        winner_model, winner_avg = scored_models[0]
        consensus_passes = top_votes[winner_model]
        mars_status = (
            "CONSENSUS_VERIFIED"
            if consensus_passes >= self.min_verification_passes
            else f"BELOW_MARS_THRESHOLD ({consensus_passes}/{self.min_verification_passes})"
        )
        winner_text = candidate_by_model[winner_model].response_text.strip()
        synthesis = (
            f"Chairman Synthesis [{mars_status}]: Selected '{winner_model}' "
            f"(avg_rank={winner_avg}, #1_votes={consensus_passes}). "
            f"Winning recommendation: {winner_text}"
        )

        return CouncilVerdictDTO(
            query=query.strip(),
            label_to_model=label_to_model,
            aggregate_rankings=tuple(scored_models),
            winner_model=winner_model,
            consensus_passes=consensus_passes,
            chairman_synthesis=synthesis,
            offline_mode=True,
        )


def plansearch_combine_observations(
    observations: Sequence[str],
    max_pairs: int = 6,
) -> List[Dict[str, Any]]:
    """PlanSearch observation-first combinatorial ideation helper (optillm pattern)."""
    clean = [str(obs).strip() for obs in observations if str(obs).strip()]
    if not clean:
        return []
    if len(clean) == 1:
        return [{"combo_id": "PS-1", "observations": [clean[0]], "prompt_seed": f"Derive architecture from: {clean[0]}"}]

    combos: List[Dict[str, Any]] = []
    for idx, pair in enumerate(itertools.combinations(clean, 2), start=1):
        if idx > max(1, int(max_pairs)):
            break
        combos.append(
            {
                "combo_id": f"PS-{idx}",
                "observations": [pair[0], pair[1]],
                "prompt_seed": f"Synthesize plan combining: (1) {pair[0]} AND (2) {pair[1]}",
            }
        )
    return combos


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synapse Hub Double-Blind LLM Council & PlanSearch Engine")
    sub = parser.add_subparsers(dest="command")

    p_adj = sub.add_parser("adjudicate", help="Adjudicate anonymized candidates from a JSON fixture")
    p_adj.add_argument("--candidates-file", required=True)
    p_adj.add_argument("--min-passes", type=int, default=2)
    p_adj.add_argument("--json", action="store_true")

    p_ps = sub.add_parser("plansearch", help="Combine observations into PlanSearch candidate seeds")
    p_ps.add_argument("--observation", action="append", required=True)
    p_ps.add_argument("--max-pairs", type=int, default=6)
    p_ps.add_argument("--json", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "adjudicate":
            raw = json.loads(Path(args.candidates_file).read_text(encoding="utf-8"))
            cands = [
                CouncilCandidateDTO(
                    model_id=str(c["model_id"]),
                    provider_family=str(c.get("provider_family", "unknown")),
                    response_text=str(c["response_text"]),
                )
                for c in raw.get("candidates", [])
            ]
            eng = LLMCouncilEngine(min_verification_passes=args.min_passes)
            verdict = eng.adjudicate_offline(
                query=str(raw.get("query", "")),
                candidates=cands,
                peer_reviews=[str(r) for r in raw.get("peer_reviews", [])],
            )
            payload: Any = verdict.to_dict()
        elif args.command == "plansearch":
            combos = plansearch_combine_observations(args.observation, max_pairs=args.max_pairs)
            payload = {"count": len(combos), "combinations": combos}
        else:
            return 1
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        err = {"ok": False, "error": str(exc)}
        print(json.dumps(err, indent=2) if getattr(args, "json", False) else f"Error: {exc}")
        return 1

    print(json.dumps(payload, indent=2) if getattr(args, "json", False) else json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
