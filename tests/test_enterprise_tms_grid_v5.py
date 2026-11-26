#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
"""4-scenario test suite for Enterprise TMS adapters (Zephyr/Qase/ReportPortal) & Cloud Grid profiles."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


SAMPLE_JUNIT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="checkout" tests="2" failures="1" errors="0" skipped="0">
  <testcase classname="CheckoutSpec" name="TC-101_valid_order" time="0.42"/>
  <testcase classname="CheckoutSpec" name="TC-102_declined_card" time="0.88">
    <failure message="Expected 402 error banner">AssertionError: banner missing</failure>
  </testcase>
</testsuite>
"""


# ---------------------------------------------------------------------------
# 1. POSITIVE SCENARIOS
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("platform", ["zephyr", "qase", "reportportal"])
def test_positive_tms_dry_run_and_live_mocked_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    """Zephyr Scale, Qase.io, and ReportPortal support offline dry-run and bounded 15s live HTTP sync."""
    from tools.alm.alm_bridge import ALMBridge, DEFAULT_HTTP_TIMEOUT

    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(SAMPLE_JUNIT_XML, encoding="utf-8")

    # Offline dry-run
    dry_bridge = ALMBridge(platform=platform, dry_run=True)
    dry_res = dry_bridge.sync_execution(str(xml_path))
    assert dry_res["status"] == "SIMULATED"
    assert dry_res["platform"] == platform
    assert dry_res["total_tests"] == 2
    assert dry_res["passed"] == 1
    assert dry_res["failed"] == 1

    # Live mocked HTTP POST asserting bounded 15s timeout and exact endpoint paths
    monkeypatch.setenv("ZEPHYR_API_TOKEN", "zph_live_secret_token")
    monkeypatch.setenv("QASE_API_TOKEN", "qase_live_secret_token")
    monkeypatch.setenv("REPORTPORTAL_API_TOKEN", "rp_live_secret_token")

    captured: Dict[str, Any] = {}

    def _fake_post(self_bridge: Any, url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int = 15) -> Dict[str, Any]:
        captured["url"] = url
        captured["timeout"] = timeout
        captured["headers"] = headers
        captured["payload"] = payload
        return {"ok": True, "http_status": 200, "data": {"id": f"{platform}-exec-777"}}

    monkeypatch.setattr(ALMBridge, "_http_post_json", _fake_post)
    live_bridge = ALMBridge(platform=platform, dry_run=False)
    live_res = live_bridge.sync_execution(str(xml_path))

    assert live_res["status"] == "SUCCESS"
    assert live_res["execution_id"] == f"{platform}-exec-777"
    assert captured["timeout"] == DEFAULT_HTTP_TIMEOUT == 15
    if platform == "zephyr":
        assert "/v2/testexecutions" in captured["url"]
    elif platform == "qase":
        assert "/v1/result/" in captured["url"]
    elif platform == "reportportal":
        assert "/api/v1/" in captured["url"] and captured["url"].endswith("/launch")


@pytest.mark.parametrize("provider", ["browserstack", "saucelabs", "lambdatest"])
def test_positive_cloud_grid_capabilities_and_redaction(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    """BrowserStack, Sauce Labs, and LambdaTest build W3C/Playwright caps from env vars and redact secrets."""
    from tools.orchestration.synapse_grid import (
        REDACTION_MASK,
        build_cloud_capabilities,
        redact_cloud_capabilities,
    )

    monkeypatch.setenv("BROWSERSTACK_USERNAME", "qa_bs_user")
    monkeypatch.setenv("BROWSERSTACK_ACCESS_KEY", "SUPER_SECRET_BS_KEY_999")
    monkeypatch.setenv("SAUCE_USERNAME", "qa_sl_user")
    monkeypatch.setenv("SAUCE_ACCESS_KEY", "SUPER_SECRET_SL_KEY_888")
    monkeypatch.setenv("LT_USERNAME", "qa_lt_user")
    monkeypatch.setenv("LT_ACCESS_KEY", "SUPER_SECRET_LT_KEY_777")

    caps = build_cloud_capabilities(provider, browser_name="chromium", os_name="Windows 11", build_tag="v5-ci")
    assert caps["provider"] == provider
    assert caps["browserName"] == "chromium"
    assert caps["credentials_configured"] is True
    assert caps["endpoint"].startswith(("wss://", "https://"))

    redacted = redact_cloud_capabilities(caps)
    dumped = json.dumps(redacted)
    assert "SUPER_SECRET_BS_KEY_999" not in dumped
    assert "SUPER_SECRET_SL_KEY_888" not in dumped
    assert "SUPER_SECRET_LT_KEY_777" not in dumped
    assert REDACTION_MASK in dumped


# ---------------------------------------------------------------------------
# 2. NEGATIVE SCENARIOS
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("platform", "env_var"),
    [
        ("zephyr", "ZEPHYR_API_TOKEN"),
        ("qase", "QASE_API_TOKEN"),
        ("reportportal", "REPORTPORTAL_API_TOKEN"),
    ],
)
def test_negative_missing_tms_token_returns_structured_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: str, env_var: str
) -> None:
    """Missing live TMS API token returns structured ERROR dict with zero unhandled exceptions."""
    from tools.alm.alm_bridge import ALMBridge

    monkeypatch.delenv(env_var, raising=False)
    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(SAMPLE_JUNIT_XML, encoding="utf-8")

    bridge = ALMBridge(platform=platform, dry_run=False)
    res = bridge.sync_execution(str(xml_path))
    assert res["status"] == "ERROR"
    assert res["execution_id"] is None
    assert env_var in res["error_message"]


def test_negative_unsupported_cloud_provider_raises_value_error() -> None:
    """Unsupported Cloud Grid provider raises descriptive ValueError."""
    from tools.orchestration.synapse_grid import build_cloud_capabilities

    with pytest.raises(ValueError, match="Unsupported cloud grid provider"):
        build_cloud_capabilities("unknown_cloud_vendor")


# ---------------------------------------------------------------------------
# 3. BOUNDARY SCENARIOS
# ---------------------------------------------------------------------------


def test_boundary_empty_junit_xml_and_unconfigured_cloud_redaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty JUnit XML returns 0 tests safely; unconfigured cloud grid sets credentials_configured=False without leaking."""
    from tools.alm.alm_bridge import ALMBridge
    from tools.orchestration.synapse_grid import (
        build_cloud_capabilities,
        redact_cloud_capabilities,
    )

    empty_xml = tmp_path / "empty.xml"
    empty_xml.write_text("<testsuite name='empty' tests='0'></testsuite>", encoding="utf-8")

    bridge = ALMBridge(platform="zephyr", dry_run=True)
    res = bridge.sync_execution(str(empty_xml))
    assert res["status"] == "SIMULATED"
    assert res["total_tests"] == 0
    assert res["passed"] == 0
    assert res["failed"] == 0

    status = bridge.get_status()
    assert "zephyr" in status and "qase" in status and "reportportal" in status

    for var in ("BROWSERSTACK_USERNAME", "BROWSERSTACK_ACCESS_KEY"):
        monkeypatch.delenv(var, raising=False)
    caps = build_cloud_capabilities("browserstack")
    assert caps["credentials_configured"] is False
    safe = redact_cloud_capabilities(caps)
    assert isinstance(safe, dict)


# ---------------------------------------------------------------------------
# 4. CLI FLAGS & JSON CONTRACT SCENARIOS
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("platform", ["zephyr", "qase", "reportportal"])
def test_cli_alm_bridge_sync_exec_dry_run_flags(tmp_path: Path, platform: str) -> None:
    """CLI `alm_bridge.py sync-exec --platform <p> --dry-run` emits valid JSON for all new TMS platforms."""
    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(SAMPLE_JUNIT_XML, encoding="utf-8")

    script = REPO_ROOT / "tools" / "alm" / "alm_bridge.py"
    proc = subprocess.run(
        [sys.executable, str(script), "sync-exec", "--report", str(xml_path), "--platform", platform, "--dry-run"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    data = json.loads(proc.stdout)
    assert data["status"] == "SIMULATED"
    assert data["platform"] == platform
    assert data["total_tests"] == 2
