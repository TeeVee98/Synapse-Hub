# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""Unit tests for Enterprise ALM & TMS Sync Orchestrator."""

import io
import json
import os
import tempfile
import urllib.error
from unittest.mock import MagicMock, patch
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
    assert "ConnectionError: 504 Gateway Timeout" in res["payload"]["description"]
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


def _mock_http_response(status_code: int, body_dict: dict):
    resp = MagicMock()
    resp.status = status_code
    resp.read.return_value = json.dumps(body_dict).encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def test_alm_bridge_fail_closed_missing_credentials(monkeypatch, tmp_path):
    """Negative: live mode without API token must fail closed with ERROR, never return fake IDs."""
    monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
    monkeypatch.delenv("TESTRAIL_API_KEY", raising=False)

    bridge = ALMBridge(platform="jira", dry_run=False)
    bug_res = bridge.create_bug(summary="Checkout crash", trace="NullPointerException")
    assert bug_res["status"] == "ERROR"
    assert bug_res["ticket_id"] is None
    assert "JIRA_API_TOKEN" in (bug_res.get("error_message") or "")

    junit_file = tmp_path / "junit.xml"
    junit_file.write_text('<testsuite><testcase name="t1"/></testsuite>', encoding="utf-8")

    xray_bridge = ALMBridge(platform="xray", dry_run=False)
    xray_res = xray_bridge.sync_execution(str(junit_file))
    assert xray_res["status"] == "ERROR"
    assert xray_res["execution_id"] is None

    tr_bridge = ALMBridge(platform="testrail", dry_run=False)
    tr_res = tr_bridge.sync_execution(str(junit_file))
    assert tr_res["status"] == "ERROR"
    assert tr_res["execution_id"] is None


def test_alm_bridge_live_http_success_jira_and_tms(monkeypatch, tmp_path):
    """Positive: live mode issues real stdlib HTTP POST with auth headers and timeout=15."""
    monkeypatch.setenv("JIRA_BASE_URL", "https://jira.acme.test")
    monkeypatch.setenv("JIRA_EMAIL", "qa@acme.test")
    monkeypatch.setenv("JIRA_API_TOKEN", "tok-123")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "ACME")
    monkeypatch.setenv("TESTRAIL_BASE_URL", "https://tr.acme.test")
    monkeypatch.setenv("TESTRAIL_USER", "qa@acme.test")
    monkeypatch.setenv("TESTRAIL_API_KEY", "tr-secret")

    bridge = ALMBridge(platform="jira", dry_run=False)
    with patch("urllib.request.urlopen", return_value=_mock_http_response(201, {"key": "ACME-777"})) as mock_open:
        res = bridge.create_bug(summary="Button disabled", trace="AssertionError: expected enabled")
        assert res["status"] == "SUCCESS"
        assert res["ticket_id"] == "ACME-777"
        assert res["http_status"] == 201
        assert "ACME-777" in res["url"]
        req = mock_open.call_args[0][0]
        assert req.full_url == "https://jira.acme.test/rest/api/3/issue"
        assert req.get_header("Authorization").startswith("Basic ")
        sent_jira = json.loads(req.data.decode("utf-8"))
        assert sent_jira["fields"]["description"]["version"] == 1
        assert mock_open.call_args[1]["timeout"] == 15

    junit_file = tmp_path / "junit.xml"
    junit_file.write_text('<testsuite><testcase name="t1"/></testsuite>', encoding="utf-8")

    xray_bridge = ALMBridge(platform="xray", dry_run=False)
    with patch("urllib.request.urlopen", return_value=_mock_http_response(200, {"testExecIssue": {"key": "ACME-EXEC-5"}})):
        xray_res = xray_bridge.sync_execution(str(junit_file))
        assert xray_res["status"] == "SUCCESS"
        assert xray_res["execution_id"] == "ACME-EXEC-5"
        assert xray_res["http_status"] == 200

    tr_bridge = ALMBridge(platform="testrail", dry_run=False)
    with patch("urllib.request.urlopen", return_value=_mock_http_response(200, {"id": 42})) as mock_tr:
        tr_res = tr_bridge.sync_execution(str(junit_file))
        assert tr_res["status"] == "SUCCESS"
        assert tr_res["execution_id"] == "42"
        assert tr_res["http_status"] == 200
        sent_tr = json.loads(mock_tr.call_args[0][0].data.decode("utf-8"))
        assert sent_tr["include_all"] is False


def test_alm_bridge_live_http_error_and_timeout(monkeypatch, tmp_path):
    """Negative: HTTP 401/500 and network timeout return structured ERROR without fake pass."""
    monkeypatch.setenv("JIRA_API_TOKEN", "tok-123")
    bridge = ALMBridge(platform="jira", dry_run=False)

    http_err = urllib.error.HTTPError(
        url="https://jira.example.com/rest/api/3/issue",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=io.BytesIO(b'{"errorMessages":["Invalid credentials"]}'),
    )
    with patch("urllib.request.urlopen", side_effect=http_err):
        res = bridge.create_bug(summary="Auth bug", trace="401")
        assert res["status"] == "ERROR"
        assert res["http_status"] == 401
        assert res["ticket_id"] is None
        assert "401" in (res.get("error_message") or "")

    junit_file = tmp_path / "junit.xml"
    junit_file.write_text('<testsuite><testcase name="t1"/></testsuite>', encoding="utf-8")
    xray_bridge = ALMBridge(platform="xray", dry_run=False)
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timed out")):
        sync_res = xray_bridge.sync_execution(str(junit_file))
        assert sync_res["status"] == "ERROR"
        assert sync_res["execution_id"] is None
        assert "timed out" in (sync_res.get("error_message") or "")


def test_alm_bridge_boundary_malformed_xml_and_oversized_trace(monkeypatch, tmp_path):
    """Boundary: malformed JUnit XML and missing file return ERROR; oversized trace is bounded."""
    bad_xml = tmp_path / "broken.xml"
    bad_xml.write_text("<testsuite><unclosed>", encoding="utf-8")

    bridge = ALMBridge(platform="xray", dry_run=True)
    res_bad = bridge.sync_execution(str(bad_xml))
    assert res_bad["status"] == "ERROR"

    res_missing = bridge.sync_execution(str(tmp_path / "missing.xml"))
    assert res_missing["status"] == "ERROR"

    huge_trace = "X" * 20000
    bug_sim = bridge.create_bug(summary="Huge trace", trace=huge_trace)
    assert bug_sim["status"] == "SIMULATED"
    assert len(bug_sim["payload"]["description"]) < 6000
