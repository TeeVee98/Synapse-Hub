#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Unit & Integration Tests for SynapseFlow Cyclic State Graph Runtime
-------------------------------------------------------------------
Verifies cyclic loops, conditional edges, checkpointing, time-travel,
and deterministic gate interceptors.
"""

import pytest
import os
import tempfile
from tools.core.synapse_flow import (
    StateGraph,
    START,
    END,
    InfiniteLoopError,
    NodeExecutionError,
    GateRejectionError
)


def test_linear_flow_execution():
    """Verifies standard linear execution A -> B -> END."""
    def step_a(state):
        return {"a": state.get("input", 0) + 1}

    def step_b(state):
        return {"b": state["a"] * 2}

    graph = StateGraph()
    graph.add_node("node_a", step_a)
    graph.add_node("node_b", step_b)
    graph.add_edge(START, "node_a")
    graph.add_edge("node_a", "node_b")
    graph.add_edge("node_b", END)

    app = graph.compile()
    try:
        final_state = app.invoke({"input": 5})
        assert final_state["input"] == 5
        assert final_state["a"] == 6
        assert final_state["b"] == 12
    finally:
        app.close()


def test_cyclic_healing_flow():
    """
    Verifies cyclic flow mimicking QA Auto-Heal:
    Run test -> If fails -> Heal locator -> Re-run test -> Until pass or max tries.
    """
    def execute_test(state):
        state["attempts"] = state.get("attempts", 0) + 1
        # Test fails until 3rd attempt
        if state["attempts"] < 3:
            state["test_status"] = "FAILED"
        else:
            state["test_status"] = "PASSED"
        return state

    def heal_locator(state):
        state["healed_count"] = state.get("healed_count", 0) + 1
        return state

    def route_test_result(state):
        if state.get("test_status") == "PASSED":
            return "passed"
        return "failed"

    graph = StateGraph()
    graph.add_node("run_test", execute_test)
    graph.add_node("heal", heal_locator)

    graph.add_edge(START, "run_test")
    graph.add_conditional_edge("run_test", route_test_result, {"passed": END, "failed": "heal"})
    graph.add_edge("heal", "run_test")  # Cycle back

    app = graph.compile(max_iterations=20)
    try:
        final_state = app.invoke({"suite": "LoginSuite"})
        assert final_state["test_status"] == "PASSED"
        assert final_state["attempts"] == 3
        assert final_state["healed_count"] == 2
    finally:
        app.close()


def test_infinite_loop_guard():
    """Verifies that an unyielding cyclic loop raises InfiniteLoopError."""
    def forever_loop(state):
        state["count"] = state.get("count", 0) + 1
        return state

    graph = StateGraph()
    graph.add_node("spin", forever_loop)
    graph.add_edge(START, "spin")
    graph.add_edge("spin", "spin")  # Infinite cycle

    app = graph.compile(max_iterations=10)
    try:
        with pytest.raises(InfiniteLoopError) as exc_info:
            app.invoke({})
        assert "exceeded max_iterations (10)" in str(exc_info.value)
    finally:
        app.close()


def test_pre_and_post_gate_rejection():
    """Verifies that gate interceptors prevent unvalidated transitions."""
    def node_work(state):
        return {"data": state.get("val", 0)}

    # Pre-gate requires 'auth_token'
    def require_auth(node_name, state):
        if node_name == "work" and not state.get("auth_token"):
            return False
        return True

    graph = StateGraph()
    graph.add_node("work", node_work)
    graph.add_edge(START, "work")
    graph.add_edge("work", END)
    graph.add_pre_gate(require_auth)

    app = graph.compile()
    try:
        # Rejection scenario
        with pytest.raises(GateRejectionError) as exc_info:
            app.invoke({"val": 10})
        assert "Pre-node gate rejected" in str(exc_info.value)

        # Acceptance scenario
        passed_state = app.invoke({"val": 10, "auth_token": "valid_secret_token"})
        assert passed_state["data"] == 10
    finally:
        app.close()


def test_checkpointing_and_time_travel():
    """Verifies SQLite WAL checkpointing and resumption from intermediate step."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_checkpoints.db")

        def step_1(state):
            return {"step1_val": 100}

        def step_2(state):
            return {"step2_val": state["step1_val"] + 50}

        def step_3(state):
            return {"final_val": state["step2_val"] * 2}

        graph = StateGraph()
        graph.add_node("s1", step_1)
        graph.add_node("s2", step_2)
        graph.add_node("s3", step_3)
        graph.add_edge(START, "s1")
        graph.add_edge("s1", "s2")
        graph.add_edge("s2", "s3")
        graph.add_edge("s3", END)

        app = graph.compile(checkpoint_db=db_path)
        try:
            flow_id = "test_flow_time_travel"
            final_state = app.invoke({"init": 1}, flow_id=flow_id)

            assert final_state["final_val"] == 300

            # Inspect recorded checkpoints
            checkpoints = app.checkpointer.list_checkpoints(flow_id)
            assert len(checkpoints) >= 4  # START, s1, s2, s3, END

            # Find checkpoint after s1
            s1_chk = next(c for c in checkpoints if c["node_name"] == "s1")

            # Resume from checkpoint s1 with altered flow id
            resumed_state = app.invoke(
                {},
                flow_id="resumed_flow",
                resume_from_checkpoint=s1_chk["checkpoint_id"]
            )

            assert resumed_state["step1_val"] == 100
            assert resumed_state["final_val"] == 300
        finally:
            app.close()


def test_node_execution_error_wrapping():
    """Verifies that uncaught exceptions in nodes are cleanly wrapped in NodeExecutionError."""
    def buggy_node(state):
        raise ValueError("Invalid parameter value inside node")

    graph = StateGraph()
    graph.add_node("bad_node", buggy_node)
    graph.add_edge(START, "bad_node")
    graph.add_edge("bad_node", END)

    app = graph.compile()
    try:
        with pytest.raises(NodeExecutionError) as exc_info:
            app.invoke({})

        assert exc_info.value.node_name == "bad_node"
        assert "Invalid parameter value" in str(exc_info.value)
    finally:
        app.close()
