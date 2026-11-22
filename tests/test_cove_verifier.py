# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for tools/ai/cove_verifier.py (Meta AI CoVe Pattern)."""

import os
import sys
import tempfile

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from ai.cove_verifier import ChainOfVerificationEngine


def test_cove_generate_verification_questions():
    engine = ChainOfVerificationEngine()
    draft = """
class CheckoutPage(BasePage):
    def click_submit(self):
        time.sleep(2)
        self.page.locator("//div[1]/button").click()

def test_checkout():
    pass
"""
    questions = engine.generate_verification_questions(draft, "checkout_page.py")
    assert len(questions) >= 3
    categories = [q["category"] for q in questions]
    assert "INHERITANCE_INVARIANT" in categories
    assert "WAIT_INVARIANT" in categories
    assert "TRUTH_ANCHOR" in categories


def test_cove_blind_execution_and_reconciliation_pass():
    engine = ChainOfVerificationEngine()
    clean_code = """
class LoginPage(BasePage):
    def enter_credentials(self, username, password):
        self.username_input.fill(username)
        self.password_input.fill(password)

def test_login_flow():
    page = LoginPage()
    assert page is not None
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(clean_code)
        f_path = f.name

    try:
        report = engine.verify(f_path)
        assert report["status"] == "PASS"
        assert report["factual_confidence_pct"] == 100.0
        assert report["discrepancies_count"] == 0
    finally:
        os.remove(f_path)


def test_cove_blind_execution_detects_discrepancy():
    engine = ChainOfVerificationEngine()
    flaky_code = """
import time

class CustomPage(BasePage):
    def wait_something(self):
        time.sleep(10)
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(flaky_code)
        f_path = f.name

    try:
        report = engine.verify(f_path)
        assert report["status"] == "DISCREPANCY_DETECTED"
        assert report["discrepancies_count"] >= 1
        disc_cats = [d["category"] for d in report["discrepancies"]]
        assert "WAIT_INVARIANT" in disc_cats
    finally:
        os.remove(f_path)
