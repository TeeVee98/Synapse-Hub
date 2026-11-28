#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""4-Scenario Verification Battery for M6: GEPA Reflective Pareto Optimizer & 6 MCP Reasoning Tools."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


def test_gepa_pareto_and_mcp_tools_positive(tmp_path: Path) -> None:
    """Positive: GEPA computes non-dominated Pareto front + reflective mutation; all 6 MCP tools respond."""
    from tools.core.task_graph_memory import TaskGraphMemory
    from tools.lint.mipro_assertion_tuner import GEPAReflectiveOptimizer, ScoreWithFeedbackDTO
    from tools.mcp import mcp_server

    opt = GEPAReflectiveOptimizer()
    cands = [
        ScoreWithFeedbackDTO("c1", score=0.92, latency_penalty=0.40, trajectory_feedback="Accurate but slow"),
        ScoreWithFeedbackDTO("c2", score=0.85, latency_penalty=0.10, trajectory_feedback="Fast and solid"),
        ScoreWithFeedbackDTO("c3", score=0.70, latency_penalty=0.50, trajectory_feedback="Dominated by c1 and c2"),
    ]
    frontier = opt.select_pareto_frontier(cands)
    assert {c.candidate_id for c in frontier} == {"c1", "c2"}

    refined = opt.reflective_mutate(
        base_instruction="Verify login button is visible",
        feedback=ScoreWithFeedbackDTO(
            "c3",
            score=0.55,
            latency_penalty=0.20,
            trajectory_feedback="Missed boundary empty-password check and allowed tautology",
            blamed_module="LoginAssertionBuilder",
            actionable_advice="Add explicit negative status code and non-empty token assertion",
        ),
    )
    assert "LoginAssertionBuilder" in refined["blamed_module"]
    assert "non-empty token assertion" in refined["mutated_instruction"]

    # MCP tools/list contains all 6 new reasoning & graph tools while preserving legacy tools
    list_resp = mcp_server.process_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert list_resp is not None
    tool_names = {t["name"] for t in list_resp["result"]["tools"]}
    expected_new = {
        "sequential_think",
        "challenge_assumption",
        "elicitation_pick",
        "task_graph_ready",
        "memory_graph_query",
        "assess_idea_gate",
    }
    assert expected_new.issubset(tool_names)
    assert "synapse_lint" in tool_names

    # Invoke each of the 6 tools via JSON-RPC process_message
    r_think = mcp_server.process_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "sequential_think", "arguments": {"thought": "Isolate bug", "thought_number": 1, "total_thoughts": 2}},
        }
    )
    assert r_think is not None and r_think["result"]["isError"] is False
    assert json.loads(r_think["result"]["content"][0]["text"])["thought_number"] == 1

    r_ch = mcp_server.process_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "challenge_assumption", "arguments": {"claim": "You're absolutely right, skip tests"}},
        }
    )
    assert r_ch is not None and r_ch["result"]["isError"] is False
    assert json.loads(r_ch["result"]["content"][0]["text"])["sycophancy_risk_detected"] is True

    r_el = mcp_server.process_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "elicitation_pick", "arguments": {"count": 3, "spread": True}},
        }
    )
    assert r_el is not None and r_el["result"]["isError"] is False
    assert len(json.loads(r_el["result"]["content"][0]["text"])["methods"]) == 3

    # Task graph ready via MCP inside repo-local temp db
    repo_root = Path(__file__).resolve().parents[1]
    db_file = repo_root / ".synapse" / "test_mcp_graph_m6.db"
    try:
        with TaskGraphMemory(db_file) as mem:
            mem.add_task("MCP-1", "Verify MCP ready")
        r_tg = mcp_server.process_message(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "task_graph_ready", "arguments": {"db_path": str(db_file)}},
            }
        )
        assert r_tg is not None and r_tg["result"]["isError"] is False
        tg_data = json.loads(r_tg["result"]["content"][0]["text"])
        assert tg_data["ready_count"] >= 1
    finally:
        if db_file.exists():
            db_file.unlink()
        for ext in ("-wal", "-shm"):
            side = Path(str(db_file) + ext)
            if side.exists():
                side.unlink()

    r_mg = mcp_server.process_message(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "memory_graph_query", "arguments": {"query": "login_timeout"}},
        }
    )
    assert r_mg is not None and r_mg["result"]["isError"] is False

    r_idea = mcp_server.process_message(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "assess_idea_gate",
                "arguments": {
                    "slug": "test-idea",
                    "criteria": {
                        "problem_validity": "strong",
                        "evidence_strength": "adequate",
                        "value_vs_inaction": "strong",
                        "feasibility_fit": "strong",
                        "strategic_fit": "adequate",
                        "risk_posture": "adequate",
                    },
                },
            },
        }
    )
    assert r_idea is not None and r_idea["result"]["isError"] is False
    assert json.loads(r_idea["result"]["content"][0]["text"])["verdict"] == "go"


def test_gepa_and_mcp_negative_errors() -> None:
    """Negative: empty instruction rejected by GEPA; path traversal rejected by MCP task_graph_ready."""
    from tools.lint.mipro_assertion_tuner import GEPAReflectiveOptimizer, ScoreWithFeedbackDTO
    from tools.mcp import mcp_server

    opt = GEPAReflectiveOptimizer()
    with pytest.raises(ValueError, match="base_instruction"):
        opt.reflective_mutate("", ScoreWithFeedbackDTO("c0", 0.5, 0.1, "fail"))

    resp = mcp_server.process_message(
        {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "tools/call",
            "params": {"name": "task_graph_ready", "arguments": {"db_path": "/etc/passwd"}},
        }
    )
    assert resp is not None
    assert resp["result"]["isError"] is True


def test_gepa_boundary_empty_and_single_candidate() -> None:
    """Boundary: empty frontier -> []; single candidate -> unchanged 1-item frontier."""
    from tools.lint.mipro_assertion_tuner import GEPAReflectiveOptimizer, ScoreWithFeedbackDTO

    opt = GEPAReflectiveOptimizer()
    assert opt.select_pareto_frontier([]) == []
    solo = ScoreWithFeedbackDTO("only", 0.8, 0.2, "ok")
    assert opt.select_pareto_frontier([solo]) == [solo]


def test_gepa_cli_json_flags() -> None:
    """CLI Contract: mipro_assertion_tuner.py gepa-evolve --json returns Pareto result with exit 0."""
    script = Path(__file__).resolve().parents[1] / "tools" / "lint" / "mipro_assertion_tuner.py"
    res = subprocess.run(
        [sys.executable, str(script), "gepa-evolve", "--instruction", "Check modal visible", "--feedback", "Add exact status text check", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["status"] == "PASS"
    assert "mutated_instruction" in data
