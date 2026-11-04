# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""Unit tests for tools/browsergym_eval.py (BrowserGym Web Agent Benchmark Harness)."""

import os
import sys
import tempfile
import shutil
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from browsergym_eval import BrowserGymEvaluator


@pytest.fixture
def temp_page_dir():
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_run_suite_default_tasks():
    gym = BrowserGymEvaluator()
    res = gym.run_suite(tasks=["ecommerce_order", "crm_lead_create", "filter_data_grid"], headless=True)

    assert res["status"] == "PASS"
    assert res["total_tasks"] == 3
    assert res["passed_tasks"] == 3
    assert res["action_success_rate"] >= 0.90
    assert res["avg_latency_ms"] <= 200.0
    assert res["database_assertion_pass_rate"] == 1.0
    assert res["certification"] == "APPROVED"


def test_evaluate_pageclass_clean_pom(temp_page_dir):
    page_file = os.path.join(temp_page_dir, "GoodOrderPage.ts")
    with open(page_file, "w", encoding="utf-8") as f:
        f.write("\n".join([
            "export class GoodOrderPage {",
            "  async submitOrder() {",
            "    const btn = this.page.getByRole('button', { name: 'Submit' });",
            "    await btn.click();",
            "  }",
            "  async verifySuccess() {",
            "    await this.page.getByTestId('order-success').isVisible();",
            "  }",
            "}"
        ]))

    gym = BrowserGymEvaluator(repo_root=temp_page_dir)
    res = gym.evaluate_pageclass(page_file)

    assert res["status"] == "PASS"
    assert res["clean_pom_score"] >= 0.8
    assert res["aom_selector_hits"] >= 2
    assert res["raw_xpath_hits"] == 0
    assert res["static_sleep_hits"] == 0
    assert res["certification"] == "APPROVED"


def test_evaluate_pageclass_rejection_on_sleep_and_xpath(temp_page_dir):
    bad_page = os.path.join(temp_page_dir, "BadPage.ts")
    with open(bad_page, "w", encoding="utf-8") as f:
        f.write("\n".join([
            "export class BadPage {",
            "  async brokenMethod() {",
            "    await page.locator('//div[@id=\"modal\"]//button').click();",
            "    Thread.sleep(5000);",
            "  }",
            "}"
        ]))

    gym = BrowserGymEvaluator(repo_root=temp_page_dir)
    res = gym.evaluate_pageclass(bad_page)

    assert res["status"] == "FAIL"
    assert res["certification"] == "REJECTED"
    assert res["raw_xpath_hits"] >= 1
    assert res["static_sleep_hits"] >= 1
    assert len(res["violations"]) >= 2
