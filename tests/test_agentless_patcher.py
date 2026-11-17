# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for tools/agentless_patcher.py (Agentless 3-Stage Patcher)."""

import os
import sys
import tempfile
import shutil
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from agentless_patcher import AgentlessPatcher


@pytest.fixture
def temp_workspace():
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_parse_stacktrace_playwright():
    patcher = AgentlessPatcher()
    log = """
    Error: Timed out 5000ms waiting for expect(locator).toBeVisible()
    Locator: locator('#old-btn')
        at LoginPage.clickLogin (src/pages/LoginPage.ts:42:15)
        at tests/login.spec.ts:18:20
    """
    frame = patcher.parse_stacktrace(log)
    assert frame is not None
    assert frame["file"] == "tests/login.spec.ts"
    assert frame["line"] == 18


def test_parse_stacktrace_python():
    patcher = AgentlessPatcher()
    log = """
    Traceback (most recent call last):
      File "tools/verify_all.py", line 125, in check_health
        assert False
    AssertionError
    """
    frame = patcher.parse_stacktrace(log)
    assert frame is not None
    assert frame["file"] == "tools/verify_all.py"
    assert frame["line"] == 125
    assert frame["method"] == "check_health"


def test_localize_error(temp_workspace):
    test_file = os.path.join(temp_workspace, "src", "pages", "SamplePage.ts")
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("\n".join([
            "export class SamplePage {",
            "  async submitOrder() {",
            "    await this.page.click('#submit-btn');",
            "  }",
            "}"
        ]))

    patcher = AgentlessPatcher(repo_root=temp_workspace)
    log = f"Error: at SamplePage.submitOrder ({test_file}:3:5)"
    loc = patcher.localize_error(log)

    assert loc["line"] == 3
    assert loc["method"] == "submitOrder"
    assert loc["line_span"] == [1, 5]


def test_generate_candidates():
    patcher = AgentlessPatcher()
    failing_chunk = "await page.click('#submit-button');"
    candidates = patcher.generate_candidates("SamplePage.ts", 10, failing_chunk=failing_chunk)

    assert len(candidates) == 3
    types = [c["type"] for c in candidates]
    assert "ARIA_ROLE_SEMANTIC" in types
    assert "TEST_ID_RESILIENT" in types
    assert "SMART_WAIT_SAFE_CLICK" in types


def test_validate_syntax_python():
    patcher = AgentlessPatcher()
    valid_code = "def foo():\n    return 42"
    invalid_code = "def foo(:\n    return 42"

    ok, _ = patcher.validate_syntax(valid_code, file_type="py")
    assert ok is True

    bad, msg = patcher.validate_syntax(invalid_code, file_type="py")
    assert bad is False
    assert "Syntax" in msg


def test_validate_syntax_brackets():
    patcher = AgentlessPatcher()
    valid_ts = "async function test() { await page.click('button'); }"
    invalid_ts = "async function test() { await page.click('button'); "

    ok, _ = patcher.validate_syntax(valid_ts, file_type="ts")
    assert ok is True

    bad, _ = patcher.validate_syntax(invalid_ts, file_type="ts")
    assert bad is False


def test_enforce_clean_pom_in_tests():
    patcher = AgentlessPatcher()
    clean_patch = "await loginPage.clickSubmitButton();"
    dirty_patch = "await page.locator('//button[@id=\"sub\"]').click();"

    ok, _ = patcher.enforce_clean_pom("tests/login.spec.ts", clean_patch)
    assert ok is True

    bad, msg = patcher.enforce_clean_pom("tests/login.spec.ts", dirty_patch)
    assert bad is False
    assert "Clean POM violation" in msg


def test_heal_failure_end_to_end(temp_workspace):
    page_file = os.path.join(temp_workspace, "src", "pages", "OrderPage.ts")
    os.makedirs(os.path.dirname(page_file), exist_ok=True)
    with open(page_file, "w", encoding="utf-8") as f:
        f.write("\n".join([
            "export class OrderPage {",
            "  async checkout() {",
            "    await page.click('#submit-order');",
            "  }",
            "}"
        ]))

    patcher = AgentlessPatcher(repo_root=temp_workspace)
    log = f"Error: Timeout\n  at OrderPage.checkout ({page_file}:3:5)"
    res = patcher.heal_failure(log, apply_patch=True)

    assert res["status"] == "PASS"
    assert res["selected_winner"] is not None
    assert res["tokens_consumed"] < 2500
    assert res["elapsed_seconds"] >= 0.0

    # Verify the file was patched on disk
    with open(page_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "#submit-order" not in content
