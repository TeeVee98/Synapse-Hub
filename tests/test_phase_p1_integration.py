# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Phase P1 Implementation Verification Suite
Tests:
  1. DSPy Declarative QA Signatures & DoD Metric (Subsystem 3)
  2. Pocock Grilling Primitive (Subsystem 6)
  3. Closed-Loop Reflexion Integration in auto_heal.py (Subsystem 2)
  4. DFSDT Backtracking Locator Resolver in browser_helpers.js (Subsystem 5)
"""

import os
import sys
import subprocess
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

import dspy_qa_signatures
import interview_story
import auto_heal


def test_dspy_qa_signatures_classes():
    assert hasattr(dspy_qa_signatures, "UserStoryToUniversalIR")
    assert hasattr(dspy_qa_signatures, "UniversalIRToCleanPOM")
    assert hasattr(dspy_qa_signatures, "RCAFailureDiagnosis")


def test_dspy_qa_dod_metric_evaluates_clean_pom():
    class CleanPred:
        test_script_code = """
import { test } from '@playwright/test';
import { InvoicePage } from './pages/InvoicePage';

test('TC-301 Approve Invoice', async ({ page }) => {
    const invoicePage = new InvoicePage(page);
    await invoicePage.approveInvoice('INV-001');
    expect(await invoicePage.isReconciled()).toBe(true);
});
"""
        page_class_code = "class InvoicePage {}"

    score = dspy_qa_signatures.qa_dod_metric(None, CleanPred())
    assert score == 1.0


def test_dspy_qa_dod_metric_rejects_raw_xpath():
    class RawXPathPred:
        test_script_code = """
test('TC-302 Raw XPath Violation', async ({ page }) => {
    await page.locator("//div[@id='invoice']//button").click();
    assert True;
});
"""
        page_class_code = ""

    score = dspy_qa_signatures.qa_dod_metric(None, RawXPathPred())
    assert score == 0.0


def test_dspy_qa_dod_metric_rejects_swallowed_exception():
    class SwallowedPred:
        test_script_code = """
test('TC-303 Swallowed Catch', async ({ page }) => {
    try {
        await page.click();
    } catch(e) {}
    assert True;
});
"""
        page_class_code = ""

    score = dspy_qa_signatures.qa_dod_metric(None, SwallowedPred())
    assert score == 0.0


def test_pocock_griller_frontier_questions():
    griller = interview_story.PocockGriller()
    questions = griller.generate_frontier_questions("As a user I want to export CSV reports")
    assert len(questions) >= 2
    for q in questions:
        assert "question" in q
        assert "options" in q
        assert any("(Recommended)" in opt for opt in q["options"])


def test_auto_heal_verbal_reflection_present():
    plan = auto_heal.diagnose_and_plan_heal(ROOT_DIR)
    assert "status" in plan


def test_browser_helpers_dfsdt_syntax():
    js_path = os.path.join(TOOLS_DIR, "browser_helpers.js")
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "dfsdtResolve" in content
    res = subprocess.run(["node", "-c", js_path], capture_output=True, text=True)
    assert res.returncode == 0


def test_dspy_offline_story_compiler():
    ir = dspy_qa_signatures.OfflineSignatureCompiler.compile_story_to_universal_ir(
        "As an admin I want to approve invoice so that payment is issued"
    )
    assert ir["version"] == "1.0.0"
    assert "scenarios" in ir
    assert len(ir["scenarios"]) >= 2

    page_code, test_code = dspy_qa_signatures.OfflineSignatureCompiler.compile_universal_ir_to_clean_pom(
        ir, target_framework="Playwright_TS"
    )
    assert "class" in page_code
    assert "waitForLoadState" in page_code
    assert "test(" in test_code


def test_dspy_offline_rca_diagnosis():
    diag = dspy_qa_signatures.OfflineSignatureCompiler.diagnose_rca_failure(
        "ElementClickInterceptedException: overlay is blocking pointer"
    )
    assert "Root Cause" in diag["root_cause_diagnosis"]
    assert "overlay" in diag["recommended_patch"]
