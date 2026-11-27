#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_live_client_modes.py
Verifies browser pilot matrix configuration, strict Appium error propagation,
and distinguishable mock/emulator/physical-device mobile session records.
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
import types
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MOBILE_CONFTEST_PATH = os.path.join(REPO_ROOT, "examples", "mobile-crm-suite", "conftest.py")
PLAYWRIGHT_CONFIG_PATH = os.path.join(REPO_ROOT, "examples", "playwright-crm-suite", "playwright.config.ts")


def _load_mobile_conftest():
    spec = None
    for finder in sys.meta_path:
        if type(finder).__name__ == "_SynapseShadowFinder":
            spec = finder.find_spec("conftest", None)
            if spec is not None:
                break
    if spec is None:
        spec = importlib.util.spec_from_file_location("mobile_crm_conftest_m5", MOBILE_CONFTEST_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_playwright_matrix_projects_and_mobile_distinguishable_records():
    """Positive: Browser projects enumerate chromium/firefox/webkit and mobile distinguishes 3 kinds."""
    with open(PLAYWRIGHT_CONFIG_PATH, "r", encoding="utf-8") as fp:
        cfg_text = fp.read()

    for browser in ("chromium", "firefox", "webkit"):
        assert re.search(rf"name\s*:\s*['\"]{browser}['\"]", cfg_text), (
            f"playwright.config.ts missing project '{browser}'"
        )
    assert "SYNAPSE_WEB_MODE" in cfg_text and "BASE_URL" in cfg_text

    mod = _load_mobile_conftest()
    mock_drv = mod.StatefulMockAppiumDriver()
    mock_rec = mod.build_mobile_session_record(
        driver=mock_drv,
        platform_name="Android",
        platform_version="mock",
    )
    emu_rec = mod.build_mobile_session_record(
        session_id="emu-sess-1",
        platform_name="Android",
        platform_version="14",
        device_name="Pixel_7_API_34",
        is_emulator=True,
    )
    real_rec = mod.build_mobile_session_record(
        session_id="real-sess-1",
        platform_name="Android",
        platform_version="14",
        device_name="Galaxy_S24_USB",
    )
    unknown_sid_rec = mod.build_mobile_session_record(device_kind="emulator")
    assert unknown_sid_rec["session_id"] == "unknown"

    assert mock_rec["device_kind"] == "mock"
    assert mock_rec["session_id"].startswith("mock_session_")
    assert emu_rec["device_kind"] == "emulator"
    assert real_rec["device_kind"] == "physical_device"
    assert len({mock_rec["device_kind"], emu_rec["device_kind"], real_rec["device_kind"]}) == 3
    assert real_rec["platform_name"] == "Android"
    assert real_rec["platform_version"] == "14"
    assert real_rec["ios_status"] == "pending"

    with pytest.raises(ValueError, match="device_kind") as dk_exc:
        mod.build_mobile_session_record(device_kind="tablet_unknown")
    assert "device_kind" in str(dk_exc.value)


def test_broken_appium_url_fails_strict_mode_without_mock_fallback(monkeypatch):
    """Negative: Broken APPIUM_SERVER_URL in strict mode raises instead of falling back to mock."""
    mod = _load_mobile_conftest()
    monkeypatch.setenv("APPIUM_SERVER_URL", "http://127.0.0.1:1/wd/hub")
    monkeypatch.setenv("SYNAPSE_MOBILE_STRICT", "1")
    monkeypatch.delenv("SYNAPSE_MOBILE_MODE", raising=False)

    with pytest.raises(RuntimeError, match="Appium|strict|connection|webdriver") as exc_info:
        mod.create_mobile_driver()
    assert "appium" in str(exc_info.value).lower()

    # Verify strict webdriver options capability setup via lightweight module stub
    captured = {}

    class FakeOptions:
        def set_capability(self, k, v):
            captured[k] = v

    class FakeWebdriver:
        @staticmethod
        def Remote(url, options=None):
            captured["url"] = url
            return "fake-remote-driver"

    fake_appium = types.ModuleType("appium")
    fake_appium.webdriver = FakeWebdriver
    fake_opts_mod = types.ModuleType("appium.options.android")
    fake_opts_mod.UiAutomator2Options = FakeOptions
    monkeypatch.setitem(sys.modules, "appium", fake_appium)
    monkeypatch.setitem(sys.modules, "appium.options", types.ModuleType("appium.options"))
    monkeypatch.setitem(sys.modules, "appium.options.android", fake_opts_mod)
    monkeypatch.setenv("SYNAPSE_MOBILE_MODE", "device")
    monkeypatch.delenv("SYNAPSE_MOBILE_STRICT", raising=False)
    assert mod.create_mobile_driver() == "fake-remote-driver"
    assert captured["platformName"] == "Android"


def test_staging_mobile_requires_appium_url_and_offline_preserves_mock(monkeypatch):
    """Boundary: Staging/device mode without APPIUM_SERVER_URL fails; offline mode keeps StatefulMockAppiumDriver."""
    mod = _load_mobile_conftest()

    monkeypatch.setenv("APPIUM_SERVER_URL", "   ")
    monkeypatch.setenv("SYNAPSE_MOBILE_MODE", "staging")
    with pytest.raises(ValueError, match="APPIUM_SERVER_URL") as val_exc:
        mod.create_mobile_driver()
    assert "staging" in str(val_exc.value).lower()

    monkeypatch.delenv("APPIUM_SERVER_URL", raising=False)
    monkeypatch.setenv("SYNAPSE_MOBILE_MODE", "emulator")
    with pytest.raises(ValueError, match="APPIUM_SERVER_URL") as emu_exc:
        mod.create_mobile_driver()
    assert "emulator" in str(emu_exc.value).lower()

    monkeypatch.delenv("SYNAPSE_MOBILE_MODE", raising=False)
    monkeypatch.delenv("SYNAPSE_MOBILE_STRICT", raising=False)
    driver = mod.create_mobile_driver()
    assert isinstance(driver, mod.StatefulMockAppiumDriver)
    driver.quit()


def _eval_playwright_config_js(web_mode: str, base_url: str) -> subprocess.CompletedProcess:
    """Execute playwright.config.ts env guard logic in Node under isolated env settings."""
    node_script = (
        "const fs=require('fs'),vm=require('vm');"
        "let src=fs.readFileSync(process.env.CFG_PATH,'utf8')"
        ".replace(/^import[^;]+;\\s*/gm,'')"
        ".replace(/export\\s+default\\s+defineConfig\\(/,'module.exports = defineConfig(');"
        "const defineConfig=(c)=>c;"
        "const devices={'Desktop Chrome':{},'Desktop Firefox':{},'Desktop Safari':{}};"
        "const mod={exports:{}};"
        "vm.runInNewContext(src,{process,require,module:mod,defineConfig,devices,Error});"
        "console.log(JSON.stringify({baseURL:mod.exports.use.baseURL,projects:mod.exports.projects.map(p=>p.name)}));"
    )
    env = {**os.environ, "CFG_PATH": PLAYWRIGHT_CONFIG_PATH, "SYNAPSE_WEB_MODE": web_mode, "BASE_URL": base_url}
    return subprocess.run(["node", "-e", node_script], capture_output=True, text=True, env=env, timeout=15)


def test_playwright_staging_url_guard_and_ios_pending_status():
    """CLI & Resilience: Staging Playwright guard requires BASE_URL and iOS stays pending until exercised."""
    with open(PLAYWRIGHT_CONFIG_PATH, "r", encoding="utf-8") as fp:
        cfg_text = fp.read()
    assert "throw new Error" in cfg_text and "process.env.BASE_URL" in cfg_text

    # 1) Staging mode without BASE_URL must fail fast
    bad_staging = _eval_playwright_config_js("staging", "")
    assert bad_staging.returncode != 0
    assert "SYNAPSE_WEB_MODE=staging requires an explicit BASE_URL" in bad_staging.stderr

    # 2) Staging mode with explicit BASE_URL must succeed
    good_staging = _eval_playwright_config_js("staging", "https://staging.crm.example.com")
    assert good_staging.returncode == 0, good_staging.stderr
    assert json.loads(good_staging.stdout)["baseURL"] == "https://staging.crm.example.com"

    # 3) Offline mode without BASE_URL must not raise staging error
    offline_run = _eval_playwright_config_js("offline", "")
    assert offline_run.returncode == 0, offline_run.stderr
    assert json.loads(offline_run.stdout)["projects"] == ["chromium", "firefox", "webkit"]

    mod = _load_mobile_conftest()
    ios_mock = mod.build_mobile_session_record(
        session_id="ios-mock-1",
        device_kind="mock",
        platform_name="iOS",
        platform_version="17.5",
    )
    assert ios_mock["ios_status"] == "pending"

    ios_rec = mod.build_mobile_session_record(
        session_id="ios-real-1",
        device_kind="physical_device",
        platform_name="iOS",
        platform_version="17.5",
        device_name="iPhone_15",
        is_emulator=False,
    )
    assert ios_rec["ios_status"] == "verified"

    android_only = mod.build_mobile_session_record(
        session_id="and-emu-1",
        device_kind="emulator",
        platform_name="Android",
        platform_version="14",
        device_name="Pixel_7_API_34",
        is_emulator=True,
    )
    assert android_only["ios_status"] == "pending"
