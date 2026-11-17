# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for tools/tot_exploratory_tester.py (Tree-of-Thoughts Exploratory Testing Engine)."""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from tot_exploratory_tester import TotExploratoryTester


def test_expand_story_3_branches():
    tester = TotExploratoryTester()
    story = """
    # User Story: Checkout Payment Gateway
    As a customer, I want to checkout my shopping cart and pay with credit card
    so that I receive an order confirmation and invoice.
    """
    res = tester.expand_story(story, max_depth=3, beam_width=3)

    assert res["status"] == "PASS"
    assert res["domain"] == "FINANCIAL_CHECKOUT"
    assert res["total_branches_explored"] == 3
    assert len(res["branches"]) == 3

    branch_ids = [b["branch_id"] for b in res["branches"]]
    assert "BRANCH_BOUNDARY_RACE" in branch_ids
    assert "BRANCH_NEGATIVE_CHAOS" in branch_ids
    assert "BRANCH_HAPPY_PATH" in branch_ids

    # Highest risk branch should be boundary/race
    assert res["highest_risk_branch"] == "BRANCH_BOUNDARY_RACE"
    assert len(res["clean_pom_recommendations"]) >= 1


def test_rca_hypotheses_dom_timeout():
    tester = TotExploratoryTester()
    log = """
    playwright.errors.TimeoutError: Page.waitForSelector timed out 5000ms
    Call log:
      - waiting for locator('#submit') to be visible
    """
    res = tester.rca_hypotheses(log)

    assert res["status"] == "PASS"
    assert res["primary_root_cause"] == "DOM_TIMEOUT"
    assert res["confidence"] >= 0.8
    assert "networkidle" in res["recommended_fix"]


def test_rca_hypotheses_backend_500():
    tester = TotExploratoryTester()
    log = """
    AxiosError: Request failed with status code 500
    Internal Server Error: NullPointerException in BillingService.processPayment
    """
    res = tester.rca_hypotheses(log)

    assert res["status"] == "PASS"
    assert res["primary_root_cause"] == "BACKEND_500"
    assert res["confidence"] >= 0.9
