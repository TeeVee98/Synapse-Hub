#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""ETH Zurich Graph of Thoughts (GoT) Composable Graph of Operations Engine.

Models non-linear reasoning as an acyclic Graph of Operations (GoO) supporting
multi-branch generation, multi-parent thought aggregation, scoring, top-N
pruning, bounded validation-and-improvement loops, and deterministic trace
serialization.
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import asdict, dataclass, field, replace
import json
import os
import sys
from typing import Any, Callable, Dict, List, Literal, Optional, Sequence, Tuple

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

GoTOpKind = Literal[
    "generate",
    "aggregate",
    "score",
    "keep_best_n",
    "keep_valid",
    "improve",
    "validate_and_improve",
    "selector",
]


@dataclass(frozen=True)
class ThoughtStateDTO:
    thought_id: str
    content: str
    score: float = 0.0
    valid: bool = True
    parent_ids: Tuple[str, ...] = ()
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GoTOperation:
    """Base node in a Graph of Operations."""

    def __init__(self, op_id: str, kind: GoTOpKind) -> None:
        if not isinstance(op_id, str) or not op_id.strip():
            raise ValueError("op_id must be a non-empty string.")
        self.op_id = op_id.strip()
        self.kind = kind
        self.predecessors: List["GoTOperation"] = []
        self.successors: List["GoTOperation"] = []
        self.thoughts: List[ThoughtStateDTO] = []

    def execute(self, incoming: Sequence[ThoughtStateDTO]) -> List[ThoughtStateDTO]:
        raise NotImplementedError("Subclasses must implement execute().")


class Generate(GoTOperation):
    def __init__(self, op_id: str, generator: Callable[[Sequence[ThoughtStateDTO]], Sequence[ThoughtStateDTO]]) -> None:
        super().__init__(op_id, "generate")
        self.generator = generator

    def execute(self, incoming: Sequence[ThoughtStateDTO]) -> List[ThoughtStateDTO]:
        self.thoughts = list(self.generator(incoming))
        return list(self.thoughts)


class Aggregate(GoTOperation):
    def __init__(self, op_id: str, aggregator: Callable[[Sequence[ThoughtStateDTO]], ThoughtStateDTO]) -> None:
        super().__init__(op_id, "aggregate")
        self.aggregator = aggregator

    def execute(self, incoming: Sequence[ThoughtStateDTO]) -> List[ThoughtStateDTO]:
        if not incoming:
            self.thoughts = []
            return []
        merged = self.aggregator(incoming)
        self.thoughts = [merged]
        return [merged]


class Score(GoTOperation):
    def __init__(self, op_id: str, scorer: Callable[[ThoughtStateDTO], float]) -> None:
        super().__init__(op_id, "score")
        self.scorer = scorer

    def execute(self, incoming: Sequence[ThoughtStateDTO]) -> List[ThoughtStateDTO]:
        self.thoughts = [replace(t, score=float(self.scorer(t))) for t in incoming]
        return list(self.thoughts)


class KeepBestN(GoTOperation):
    def __init__(self, op_id: str, n: int, higher_is_better: bool = True) -> None:
        super().__init__(op_id, "keep_best_n")
        if int(n) <= 0:
            raise ValueError("n must be a positive integer.")
        self.n = int(n)
        self.higher_is_better = bool(higher_is_better)

    def execute(self, incoming: Sequence[ThoughtStateDTO]) -> List[ThoughtStateDTO]:
        ranked = sorted(incoming, key=lambda t: t.score, reverse=self.higher_is_better)
        self.thoughts = list(ranked[: self.n])
        return list(self.thoughts)


class KeepValid(GoTOperation):
    def __init__(self, op_id: str) -> None:
        super().__init__(op_id, "keep_valid")

    def execute(self, incoming: Sequence[ThoughtStateDTO]) -> List[ThoughtStateDTO]:
        self.thoughts = [t for t in incoming if t.valid]
        return list(self.thoughts)


class Improve(GoTOperation):
    def __init__(self, op_id: str, improver: Callable[[ThoughtStateDTO], ThoughtStateDTO]) -> None:
        super().__init__(op_id, "improve")
        self.improver = improver

    def execute(self, incoming: Sequence[ThoughtStateDTO]) -> List[ThoughtStateDTO]:
        self.thoughts = [self.improver(t) for t in incoming]
        return list(self.thoughts)


class ValidateAndImprove(GoTOperation):
    def __init__(
        self,
        op_id: str,
        validator: Callable[[ThoughtStateDTO], bool],
        improver: Callable[[ThoughtStateDTO, int], ThoughtStateDTO],
        max_retries: int = 2,
    ) -> None:
        super().__init__(op_id, "validate_and_improve")
        if int(max_retries) < 0:
            raise ValueError("max_retries must be non-negative.")
        self.validator = validator
        self.improver = improver
        self.max_retries = int(max_retries)

    def execute(self, incoming: Sequence[ThoughtStateDTO]) -> List[ThoughtStateDTO]:
        refined: List[ThoughtStateDTO] = []
        for t in incoming:
            current = t
            is_valid = bool(self.validator(current))
            attempt = 0
            while not is_valid and attempt < self.max_retries:
                attempt += 1
                current = self.improver(current, attempt)
                is_valid = bool(self.validator(current))
            refined.append(replace(current, valid=is_valid))
        self.thoughts = refined
        return list(self.thoughts)


class Selector(GoTOperation):
    def __init__(self, op_id: str, selector: Callable[[Sequence[ThoughtStateDTO]], Sequence[ThoughtStateDTO]]) -> None:
        super().__init__(op_id, "selector")
        self.selector = selector

    def execute(self, incoming: Sequence[ThoughtStateDTO]) -> List[ThoughtStateDTO]:
        self.thoughts = list(self.selector(incoming))
        return list(self.thoughts)


class GraphOfOperations:
    """Directed acyclic Graph of Operations (GoO) with Kahn topological verification."""

    def __init__(self) -> None:
        self._ops: Dict[str, GoTOperation] = {}
        self._order_added: List[GoTOperation] = []

    def add_operation(self, op: GoTOperation, predecessors: Sequence[GoTOperation] = ()) -> GoTOperation:
        if op.op_id in self._ops:
            raise ValueError(f"Duplicate operation id '{op.op_id}'.")
        for pred in predecessors:
            if pred.op_id not in self._ops or self._ops[pred.op_id] is not pred:
                raise ValueError(f"Predecessor '{pred.op_id}' is not registered in this GraphOfOperations.")
        self._ops[op.op_id] = op
        self._order_added.append(op)
        for pred in predecessors:
            pred.successors.append(op)
            op.predecessors.append(pred)
        return op

    def topological_order(self) -> List[GoTOperation]:
        in_degree: Dict[str, int] = {op.op_id: len(op.predecessors) for op in self._order_added}
        queue: deque[GoTOperation] = deque(op for op in self._order_added if in_degree[op.op_id] == 0)
        ordered: List[GoTOperation] = []
        while queue:
            cur = queue.popleft()
            ordered.append(cur)
            for succ in cur.successors:
                in_degree[succ.op_id] -= 1
                if in_degree[succ.op_id] == 0:
                    queue.append(succ)
        if len(ordered) != len(self._order_added):
            raise ValueError("Cycle detected in GraphOfOperations.")
        return ordered

    def leaf_operations(self) -> List[GoTOperation]:
        return [op for op in self._order_added if not op.successors]


class GoTController:
    """Deterministic executor for GraphOfOperations with full graph trace export."""

    def __init__(self, graph: GraphOfOperations) -> None:
        self.graph = graph
        self._executed_ops: List[GoTOperation] = []
        self._final_thoughts: List[ThoughtStateDTO] = []

    def run(self, initial_thoughts: Sequence[ThoughtStateDTO] = ()) -> List[ThoughtStateDTO]:
        ordered = self.graph.topological_order()
        self._executed_ops = []
        if not ordered:
            self._final_thoughts = []
            return []

        for op in ordered:
            if not op.predecessors:
                incoming = list(initial_thoughts)
            else:
                incoming = []
                for pred in op.predecessors:
                    incoming.extend(pred.thoughts)
            op.execute(incoming)
            self._executed_ops.append(op)

        finals: List[ThoughtStateDTO] = []
        for leaf in self.graph.leaf_operations():
            finals.extend(leaf.thoughts)
        self._final_thoughts = finals
        return list(finals)

    def export_graph_trace(self) -> Dict[str, Any]:
        best_score = max((t.score for t in self._final_thoughts), default=0.0)
        return {
            "status": "ok",
            "operations_executed": len(self._executed_ops),
            "final_thought_count": len(self._final_thoughts),
            "best_score": round(float(best_score), 4),
            "nodes": [
                {
                    "op_id": op.op_id,
                    "kind": op.kind,
                    "predecessors": [p.op_id for p in op.predecessors],
                    "thoughts": [t.to_dict() for t in op.thoughts],
                }
                for op in self._executed_ops
            ],
            "final_thoughts": [t.to_dict() for t in self._final_thoughts],
        }


def run_default_story_got(story: str, top_k: int = 2) -> Dict[str, Any]:
    """Built-in deterministic QA exploratory GoT workflow for CLI and bridge use."""
    g = GraphOfOperations()
    gen = g.add_operation(
        Generate(
            "generate_perspectives",
            lambda _in: [
                ThoughtStateDTO("branch_race", f"[{story}] Concurrency & idempotency race check"),
                ThoughtStateDTO("branch_boundary", f"[{story}] Exact boundary & negative input check"),
                ThoughtStateDTO("branch_happy", f"[{story}] Standard happy-path verification"),
            ],
        )
    )
    sc = g.add_operation(
        Score(
            "score_risk",
            lambda t: 0.92 if "race" in t.thought_id else (0.84 if "boundary" in t.thought_id else 0.35),
        ),
        predecessors=[gen],
    )
    kb = g.add_operation(KeepBestN("keep_top_risks", n=max(1, int(top_k))), predecessors=[sc])
    agg = g.add_operation(
        Aggregate(
            "aggregate_suite",
            lambda ts: ThoughtStateDTO(
                thought_id="got_synthesis",
                content=" && ".join(t.content for t in ts),
                score=round(sum(t.score for t in ts) / max(1, len(ts)), 4),
                valid=False,
                parent_ids=tuple(t.thought_id for t in ts),
            ),
        ),
        predecessors=[kb],
    )
    g.add_operation(
        ValidateAndImprove(
            "enforce_assertion_contract",
            validator=lambda t: "ASSERT_CONTRACT" in t.content,
            improver=lambda t, _attempt: replace(t, content=t.content + " | ASSERT_CONTRACT", valid=True),
            max_retries=1,
        ),
        predecessors=[agg],
    )
    ctrl = GoTController(g)
    ctrl.run()
    return ctrl.export_graph_trace()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Synapse Hub Graph of Thoughts (GoT) Engine")
    parser.add_argument("--story", required=True, help="Story or problem statement to analyze")
    parser.add_argument("--top-k", type=int, default=2, help="Top branches to aggregate")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    trace = run_default_story_got(args.story, top_k=args.top_k)
    if args.json:
        print(json.dumps(trace, indent=2))
    else:
        print(trace)
    return 0


if __name__ == "__main__":
    sys.exit(main())
