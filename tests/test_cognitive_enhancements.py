# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_cognitive_enhancements.py — Verification of Agent Intelligence Upgrades
----------------------------------------------------------------------------------
Verifies:
  1. Stanford DSPy / MIPROv2 Prompt Candidate Optimization against DoD metrics.
  2. Cold-Memory (Archival Memory) automated session context retrieval & prompt hydration.
  3. TaskMemoryManager automatic seeding of historical lessons.
  4. Graph-of-Thoughts (GoT) multi-depth tree expansion & cross-branch relations.
"""

import os
import sys
import tempfile
import shutil
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from typed_prompt_signatures import MIPROv2PromptOptimizer
from test_memory_os import TestMemoryOS
from task_memory_manager import TaskMemoryManager
from tot_exploratory_tester import TotExploratoryTester


@pytest.fixture
def temp_workspace():
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def test_mipro_prompt_optimizer_selects_best_candidate():
    """Verifies that MIPROv2 optimizer evaluates candidate strategies against Quality Gates DoD."""
    res = MIPROv2PromptOptimizer.optimize()
    assert res["status"] == "OPTIMIZED"
    assert "optimal_strategy_id" in res
    assert res["benchmark_accuracy"] == 1.0
    assert res["candidates_evaluated"] >= 3
    assert len(res["evaluations"]) == 3


def test_test_memory_os_retrieve_session_context(temp_workspace):
    """Verifies that Cold Memory formats compact prompt markdown snippet."""
    db_path = os.path.join(temp_workspace, "qa_memory.db")
    mem = TestMemoryOS(db_path=db_path)

    # Empty state test
    empty_ctx = mem.retrieve_session_context(query="payment checkout")
    assert empty_ctx["status"] == "EMPTY"
    assert empty_ctx["count"] == 0
    assert "No historical anomalies" in empty_ctx["markdown_block"]

    # Insert historical lesson
    mem.archival_insert(
        key="LOCATOR_MUTATION",
        payload={"page": "CheckoutPage", "patch": "Use getByRole('button', {name: 'Pay'})", "reason": "Dynamic ID change"},
        tags="checkout,payment"
    )

    # Retrieve context
    hydrated_ctx = mem.retrieve_session_context(query="checkout payment")
    assert hydrated_ctx["status"] == "PASS"
    assert hydrated_ctx["count"] >= 1
    assert "Historical Insights & Anti-Patterns" in hydrated_ctx["markdown_block"]
    assert "LOCATOR_MUTATION" in hydrated_ctx["markdown_block"]


def test_task_memory_manager_auto_hydrates_cold_memory(temp_workspace):
    """Verifies that TaskMemoryManager automatically seeds task_plan.md with cold memory lessons."""
    from unittest.mock import patch

    # Seed isolated cold memory inside temp_workspace to prevent xdist SQLite collisions
    db_path = os.path.join(temp_workspace, ".agent_memory", "qa_memory.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    mem = TestMemoryOS(db_path=db_path)
    mem.archival_insert(
        key="ANTI_PATTERN_GIS",
        payload={"reason": "GIS collision with fixed coordinates", "patch": "Randomize bounding box"},
        tags="gis,map,coordinates"
    )

    # Init Task Memory with TestMemoryOS bound to the isolated workspace DB
    mgr = TaskMemoryManager(memory_dir=os.path.join(temp_workspace, ".task_memory"))
    with patch("test_memory_os.TestMemoryOS", return_value=mem):
        mgr.init_memory(title="GIS Map Polygon Task", goal="Automate GIS map coordinates and polygon drag")

    with open(mgr.plan_path, "r", encoding="utf-8") as f:
        plan_content = f.read()

    assert "Historical Insights (Cold-Memory Hydration)" in plan_content
    assert "ANTI_PATTERN_GIS" in plan_content


def test_tot_exploratory_tester_graph_of_thoughts_expansion():
    """Verifies Graph-of-Thoughts (GoT) multi-depth expansion and edge relations."""
    tester = TotExploratoryTester()
    res = tester.expand_story("# As a User I want to Checkout Cart", max_depth=2, beam_width=3)

    assert res["status"] == "PASS"
    assert res["domain"] == "FINANCIAL_CHECKOUT"
    assert "graph_of_thoughts_edges" in res
    assert len(res["graph_of_thoughts_edges"]) == 3

    # Verify deep 4th thought generated for max_depth >= 2
    happy_branch = next(b for b in res["branches"] if b["branch_id"] == "BRANCH_HAPPY_PATH")
    assert len(happy_branch["thoughts"]) == 4
    assert any("idempotent" in t["thought"].lower() for t in happy_branch["thoughts"])
