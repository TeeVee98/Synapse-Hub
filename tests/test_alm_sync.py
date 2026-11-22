# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""Unit tests for Enterprise ALM & TMS Sync Orchestrator."""

import os
import tempfile
from tools.alm.alm_bridge import ALMBridge


def test_alm_bridge_status():
    """Verify ALM bridge inspects configuration properly."""
    bridge = ALMBridge(platform="jira", dry_run=True)
    status = bridge.get_status()
    assert status["platform_selected"] == "jira"
    assert status["dry_run"] is True
    assert "jira" in status
    assert "testrail" in status
    assert status["jira"]["project_key"] == "AUTO"


def test_alm_bridge_push_bug_dry_run():
    """Verify dry-run bug ticket creation formats fields properly."""
    bridge = ALMBridge(dry_run=True)
    res = bridge.create_bug(
        summary="Payment gateway timeout",
        trace="ConnectionError: 504 Gateway Timeout",
        severity="Highest",
        attachments=["screenshot.png"],
    )
    assert res["status"] == "SIMULATED"
    assert "AUTO-SIM" in res["ticket_id"]
    assert res["payload"]["severity"] == "Highest"
    assert "[AUT Defect]" in res["payload"]["summary"]
    assert "screenshot.png" in res["payload"]["attachments"]


def test_alm_bridge_parse_junit_xml():
    """Verify parsing a valid JUnit XML into structured metrics."""
    junit_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="E2E Checkout Suite" tests="3" failures="1" errors="0" skipped="1">
    <testcase name="test_login_success" classname="tests.test_auth" time="1.23"/>
    <testcase name="test_payment_gateway" classname="tests.test_pay" time="2.45">
        <failure message="Payment declined">AssertionError: Expected 200 got 402</failure>
    </testcase>
    <testcase name="test_promo_code" classname="tests.test_promo" time="0.0">
        <skipped/>
    </testcase>
</testsuite>
"""
    with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as f:
        f.write(junit_content)
        temp_xml = f.name

    try:
        bridge = ALMBridge(dry_run=True)
        metrics = bridge.parse_junit_report(temp_xml)
        assert metrics["tests"] == 3
        assert metrics["passed"] == 1
        assert metrics["failures"] == 1
        assert metrics["skipped"] == 1
        assert len(metrics["cases"]) == 3

        sync_res = bridge.sync_execution(temp_xml)
        assert sync_res["passed"] == 1
        assert sync_res["failed"] == 1
        assert sync_res["dry_run"] is True
    finally:
        if os.path.exists(temp_xml):
            os.remove(temp_xml)
