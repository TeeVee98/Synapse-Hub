# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""4-scenario verification suite for M4: ETH Graph of Thoughts (GoT) & ToT Bridge."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.orchestration.tot_exploratory_tester import TotExploratoryTester
from tools.reasoning.graph_of_thoughts import (
    Aggregate,
    Generate,
    GoTController,
    GraphOfOperations,
    Improve,
    KeepBestN,
    KeepValid,
    Score,
    Selector,
    ThoughtStateDTO,
    ValidateAndImprove,
    main as got_main,
    run_default_story_got,
)


def test_got_aggregate_and_validate_improve() -> None:
    """Positive scenario: Generate -> Score -> KeepBestN -> Aggregate (multi-parent) -> ValidateAndImprove -> Trace."""
    g = GraphOfOperations()

    op_gen = g.add_operation(
        Generate(
            "gen_branches",
            lambda _in: [
                ThoughtStateDTO("t1", "Check payment idempotency key", score=0.0),
                ThoughtStateDTO("t2", "Check happy path receipt", score=0.0),
                ThoughtStateDTO("t3", "Check double-submit race condition", score=0.0),
            ],
        )
    )
    op_score = g.add_operation(
        Score(
            "score_branches",
            lambda t: 0.95 if "race" in t.content else (0.85 if "idempotency" in t.content else 0.30),
        ),
        predecessors=[op_gen],
    )
    op_top2 = g.add_operation(KeepBestN("keep_top2", n=2), predecessors=[op_score])
    assert ThoughtStateDTO("default_check", "ok").valid is True

    op_agg = g.add_operation(
        Aggregate(
            "merge_top2",
            lambda ts: ThoughtStateDTO(
                thought_id="agg_1",
                content=" + ".join(t.content for t in ts),
                score=round(sum(t.score for t in ts) / max(1, len(ts)), 3),
                valid=False,
                parent_ids=tuple(t.thought_id for t in ts),
            ),
        ),
        predecessors=[op_top2],
    )

    op_val = g.add_operation(
        ValidateAndImprove(
            "validate_and_refine",
            validator=lambda t: "ASSERT_IDEMPOTENT" in t.content,
            improver=lambda t, attempt: ThoughtStateDTO(
                thought_id=f"{t.thought_id}_r{attempt}",
                content=t.content + (" | ASSERT_IDEMPOTENT" if attempt >= 2 else " | draft"),
                score=round(t.score + 0.05, 3),
                valid=True,
                parent_ids=(t.thought_id,),
            ),
            max_retries=2,
        ),
        predecessors=[op_agg],
    )
    op_valid = g.add_operation(KeepValid("keep_valid"), predecessors=[op_val])
    op_imp = g.add_operation(
        Improve(
            "final_polish",
            lambda t: ThoughtStateDTO(
                thought_id=f"{t.thought_id}_final",
                content=t.content + " [POLISHED]",
                score=t.score,
                valid=t.valid,
                parent_ids=(t.thought_id,),
            ),
        ),
        predecessors=[op_valid],
    )
    g.add_operation(Selector("select_all", lambda ts: list(ts)), predecessors=[op_imp])

    ctrl = GoTController(g)
    finals = ctrl.run()
    assert len(finals) == 1
    final_t = finals[0]
    assert isinstance(final_t, ThoughtStateDTO)
    assert final_t.valid is True
    assert "ASSERT_IDEMPOTENT" in final_t.content
    assert "[POLISHED]" in final_t.content
    assert set(op_agg.thoughts[0].parent_ids) == {"t1", "t3"}
    assert op_top2.thoughts[0].score >= op_top2.thoughts[1].score

    with pytest.raises(FrozenInstanceError):
        final_t.score = 0.0  # type: ignore[misc]

    trace = ctrl.export_graph_trace()
    assert trace["operations_executed"] == 8
    assert trace["final_thought_count"] == 1
    assert trace["best_score"] == final_t.score
    assert len(trace["nodes"]) == 8

    # ToT bridge test
    tester = TotExploratoryTester()
    got_res = tester.run_graph_search(story_title="Checkout Double Submit", domain="FINANCIAL_CHECKOUT", top_k=2)
    assert got_res["status"] == "PASS"
    assert got_res["final_thought_count"] >= 1
    assert len(got_res["synthesized_parents"]) == 2
    assert got_res["best_score"] > 0.0


def test_got_negative_and_boundary() -> None:
    """Negative & Boundary scenarios: duplicate op_id, cycle detection, invalid n/retries, empty graph, k > len."""
    with pytest.raises(ValueError, match="op_id"):
        KeepValid("   ")
    with pytest.raises(ValueError, match="n must be"):
        KeepBestN("kb", n=0)
    with pytest.raises(ValueError, match="max_retries"):
        ValidateAndImprove("vi", validator=lambda _t: True, improver=lambda t, _a: t, max_retries=-1)

    g = GraphOfOperations()
    # Empty graph boundary
    assert GoTController(g).run() == []

    op_a = g.add_operation(KeepValid("a"))
    with pytest.raises(ValueError, match="Duplicate"):
        g.add_operation(KeepValid("a"))

    unregistered = KeepValid("ghost")
    with pytest.raises(ValueError, match="registered"):
        g.add_operation(KeepValid("b"), predecessors=[unregistered])

    # Cycle injection caught
    op_b = g.add_operation(KeepValid("b"), predecessors=[op_a])
    op_a.predecessors.append(op_b)
    op_b.successors.append(op_a)
    with pytest.raises(ValueError, match="Cycle"):
        g.topological_order()

    # KeepBestN with higher_is_better=False and k > len + ValidateAndImprove exhausted retries
    g2 = GraphOfOperations()
    s1 = g2.add_operation(
        Generate(
            "g",
            lambda _in: [
                ThoughtStateDTO("low", "low", score=0.2),
                ThoughtStateDTO("high", "high", score=0.9),
            ],
        )
    )
    s2 = g2.add_operation(KeepBestN("min_first", n=5, higher_is_better=False), predecessors=[s1])
    g2.add_operation(
        ValidateAndImprove("always_fail", validator=lambda _t: False, improver=lambda t, _a: t, max_retries=1),
        predecessors=[s2],
    )
    out = GoTController(g2).run()
    assert [t.thought_id for t in s2.thoughts] == ["low", "high"]
    assert all(t.valid is False for t in out)


def test_got_cli_json_contract(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI scenario: run built-in GoT pipeline via --story --json (in-process + subprocess)."""
    trace = run_default_story_got("Checkout retry", top_k=2)
    agg_node = next(n for n in trace["nodes"] if n["op_id"] == "aggregate_suite")
    assert agg_node["thoughts"][0]["valid"] is False
    assert trace["final_thoughts"][0]["valid"] is True

    assert got_main(["--story", "Auth token refresh", "--top-k", "2", "--json"]) == 0
    captured = json.loads(capsys.readouterr().out)
    assert captured["status"] == "ok"
    assert captured["operations_executed"] == 5

    with pytest.raises(SystemExit) as exc_info:
        got_main([])
    assert exc_info.value.code != 0

    worktree_root = Path(__file__).resolve().parents[1]
    script = str(worktree_root / "tools" / "reasoning" / "graph_of_thoughts.py")
    r = subprocess.run(
        [sys.executable, script, "--story", "Auth token refresh race condition", "--top-k", "2", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["status"] == "ok"
    assert data["operations_executed"] >= 4
    assert data["final_thought_count"] >= 1
