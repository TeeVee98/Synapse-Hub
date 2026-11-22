# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for upgraded Tree-of-Thoughts & LATS Search Engine in tot_exploratory_tester.py."""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from tot_exploratory_tester import TotExploratoryTester, SearchNode


def test_tot_search_node_structure():
    node = SearchNode(
        node_id="TEST_NODE",
        parent_id="ROOT",
        depth=1,
        branch_type="BRANCH_BOUNDARY_RACE",
        thought="Test double-click race condition",
        risk_score=0.88,
        value_score=0.92
    )
    d = node.to_dict()
    assert d["node_id"] == "TEST_NODE"
    assert d["risk_score"] == 0.88
    assert d["value_score"] == 0.92
    assert d["status"] == "EXPLORED"


def test_tot_dynamic_state_evaluation():
    tester = TotExploratoryTester()
    r_fin, v_fin = tester.evaluate_state_value("BRANCH_BOUNDARY_RACE", "Check idempotent retry", "FINANCIAL_CHECKOUT")
    r_gen, v_gen = tester.evaluate_state_value("BRANCH_BOUNDARY_RACE", "Check retry", "GENERAL_CRUD")

    # Financial checkout should carry elevated risk score
    assert r_fin >= r_gen
    assert v_fin > 0.0


def test_tot_tree_search_with_backtracking():
    tester = TotExploratoryTester()
    res = tester.expand_story(
        story_content="# User Story: Payment Checkout with High Volatility\nAs a shopper I want to pay securely",
        max_depth=3,
        beam_width=3
    )

    assert "tree_search_engine" in res
    engine_telemetry = res["tree_search_engine"]
    assert engine_telemetry["nodes_evaluated"] >= 4
    assert engine_telemetry["backtracks_count"] >= 1
    assert len(engine_telemetry["search_trace"]) >= 1

    search_tree = engine_telemetry["search_tree"]
    assert search_tree["node_id"] == "ROOT"
    assert len(search_tree["children"]) >= 3

    # Verify dead-end backtracked node exists in tree
    chaos_node = next(c for c in search_tree["children"] if c["branch_type"] == "BRANCH_NEGATIVE_CHAOS")
    assert any(c["status"] == "BACKTRACKED" for c in chaos_node["children"])
