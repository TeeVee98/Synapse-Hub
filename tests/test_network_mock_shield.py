#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""4-Scenario Unit Tests for tools/api/network_mock_shield.py."""

import json
import os
import subprocess
import sys

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.api.network_mock_shield import NetworkMockShield


class TestNetworkMockShieldPositive:
    def test_generate_ts_python_cypress_mocks(self):
        ts_code = NetworkMockShield.generate_playwright_ts(
            "**/api/orders", status=201, body={"id": 42}, delay_ms=150
        )
        assert "page.route('**/api/orders'" in ts_code
        assert "status: 201" in ts_code
        assert '"id": 42' in ts_code
        assert "setTimeout(r, 150)" in ts_code

        py_code = NetworkMockShield.generate_playwright_python(
            "**/api/orders", status=500, body={"error": "down"}, delay_ms=250
        )
        assert "time.sleep" not in py_code
        assert "threading.Event().wait(0.25)" in py_code
        assert "status=500" in py_code
        assert "page.route('**/api/orders'" in py_code

        cy_code = NetworkMockShield.generate_cypress_js(
            "**/api/orders", method="PUT", status=200, body={"ok": True}, delay_ms=100
        )
        assert "cy.intercept('PUT', '**/api/orders'" in cy_code
        assert "delay: 100" in cy_code
        assert ".as('mock_orders')" in cy_code

    def test_har_harness_uses_canonical_tool_path(self):
        py_rec = NetworkMockShield.generate_playwright_har_harness(
            "fixtures/trace.har", mode="record", lang="python"
        )
        ts_rec = NetworkMockShield.generate_playwright_har_harness(
            "fixtures/trace.har", mode="record", lang="ts"
        )
        assert "tools/api/network_mock_shield.py" in py_rec
        assert "tools/api/network_mock_shield.py" in ts_rec
        assert "tools/network_mock_shield.py" not in py_rec
        assert "tools/network_mock_shield.py" not in ts_rec

        ts_replay = NetworkMockShield.generate_playwright_har_harness(
            "fixtures/trace.har", mode="replay", lang="ts"
        )
        assert "routeFromHAR('fixtures/trace.har'" in ts_replay


class TestNetworkMockShieldNegativeAndBoundary:
    def test_unknown_preset_and_missing_har_raise(self, tmp_path):
        with pytest.raises(ValueError, match="Unknown preset"):
            NetworkMockShield.get_preset("does_not_exist")

        with pytest.raises(FileNotFoundError):
            NetworkMockShield.sanitize_har_file(str(tmp_path / "missing.har"))

    def test_sanitize_har_redacts_secrets_and_empty_entries(self, tmp_path):
        har_in = tmp_path / "sample.har"
        har_out = tmp_path / "clean.har"
        payload = {
            "log": {
                "entries": [
                    {
                        "request": {
                            "headers": [
                                {"name": "Authorization", "value": "Bearer super_secret_jwt"},
                                {"name": "X-Custom", "value": "keep-me"},
                            ],
                            "postData": {
                                "text": '{"password":"my_pw","email":"user@real.com"}'
                            },
                        },
                        "response": {
                            "headers": [{"name": "Set-Cookie", "value": "sid=xyz"}]
                        },
                    }
                ]
            }
        }
        har_in.write_text(json.dumps(payload), encoding="utf-8")
        redacted = NetworkMockShield.sanitize_har_file(str(har_in), str(har_out))
        assert redacted == 2
        cleaned = json.loads(har_out.read_text(encoding="utf-8"))
        req_headers = cleaned["log"]["entries"][0]["request"]["headers"]
        assert req_headers[0]["value"] == "Bearer REDACTED_TOKEN"
        assert req_headers[1]["value"] == "keep-me"
        post_txt = cleaned["log"]["entries"][0]["request"]["postData"]["text"]
        assert "REDACTED_SECRET" in post_txt
        assert "my_pw" not in post_txt


class TestNetworkMockShieldCLI:
    def test_cli_list_presets_and_python_generation(self):
        tool_path = os.path.join(ROOT_DIR, "tools", "api", "network_mock_shield.py")
        res_presets = subprocess.run(
            [sys.executable, tool_path, "--list-presets"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res_presets.returncode == 0
        assert "payment_success" in res_presets.stdout

        res_py = subprocess.run(
            [sys.executable, tool_path, "--preset", "rate_limit_429", "--delay", "200", "--lang", "python"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res_py.returncode == 0
        assert "time.sleep" not in res_py.stdout
        assert "status=429" in res_py.stdout
