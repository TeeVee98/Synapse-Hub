#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""4-Scenario Unit Tests for tools/transpiler/traffic_session_converter.py."""

import json
import os
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.transpiler.traffic_session_converter import TrafficConverter


class TestTrafficSessionConverter:
    def _sample_har(self):
        return {
            "log": {
                "entries": [
                    {"request": {"url": "https://cdn.example.com/logo.png", "method": "GET"}, "response": {"status": 200}},
                    {"request": {"url": "https://www.google-analytics.com/collect", "method": "POST"}, "response": {"status": 204}},
                    {
                        "request": {
                            "url": "https://app.example.com/api/checkout",
                            "method": "POST",
                            "headers": [
                                {"name": "Authorization", "value": "Bearer live_jwt_123"},
                                {"name": "Content-Type", "value": "application/json"},
                            ],
                            "postData": {"text": '{"password":"secret_pw","email":"alice@corp.com"}'},
                        },
                        "response": {
                            "status": 201,
                            "content": {"text": '{"token":"resp_secret_99","ok":true}'},
                        },
                    },
                ]
            }
        }

    def test_positive_filter_sanitize_and_generate_playwright(self):
        conv = TrafficConverter()
        assert conv.sanitize_pii is True
        assert conv.is_static_or_tracking("https://cdn.example.com/app.css") is True
        assert conv.is_static_or_tracking("https://app.example.com/api/orders") is False

        reqs = conv.parse_har(self._sample_har())
        assert len(reqs) == 1
        r = reqs[0]
        assert r["headers"]["Authorization"] == "Bearer REDACTED_TOKEN"
        assert "secret_pw" not in r["request_body"]
        assert "REDACTED_SECRET" in r["request_body"]
        assert "resp_secret_99" not in r["response_body"]

        ts = conv.generate_playwright_test(reqs, test_name="CheckoutReplay")
        assert "test.describe('CheckoutReplay'" in ts
        assert "await request.post('https://app.example.com/api/checkout'" in ts
        assert "expect(resp1.status()).toBe(201);" in ts

    def test_negative_no_sanitize_and_boundary_empty_har(self):
        conv_raw = TrafficConverter(sanitize_pii=False)
        reqs = conv_raw.parse_har(self._sample_har())
        assert "secret_pw" in reqs[0]["request_body"]

        empty_reqs = conv_raw.parse_har({})
        assert empty_reqs == []
        assert "No actionable HTTP requests" in conv_raw.generate_playwright_test(empty_reqs)

    def test_cli_json_and_output_file(self, tmp_path):
        har_file = tmp_path / "session.har"
        har_file.write_text(json.dumps(self._sample_har()), encoding="utf-8")
        out_spec = tmp_path / "replay.spec.ts"
        tool = os.path.join(ROOT_DIR, "tools", "transpiler", "traffic_session_converter.py")

        res_json = subprocess.run(
            [sys.executable, tool, str(har_file), "--json"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res_json.returncode == 0
        parsed = json.loads(res_json.stdout)
        assert parsed["total_requests"] == 1
        assert len(parsed["requests"]) == 1

        res_out = subprocess.run(
            [sys.executable, tool, str(har_file), "--output", str(out_spec), "--name", "E2EReplay"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res_out.returncode == 0
        assert out_spec.is_file()
        assert "E2EReplay" in out_spec.read_text(encoding="utf-8")

        res_stdout = subprocess.run(
            [sys.executable, tool, str(har_file), "--name", "StdoutReplay"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res_stdout.returncode == 0
        assert "StdoutReplay" in res_stdout.stdout
