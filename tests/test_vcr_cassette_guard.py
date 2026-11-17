#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from tools.vcr_cassette_guard import (
    CassetteMismatchError,
    CassetteNotFoundError,
    REDACTED_VALUE,
    VCRCassetteGuard,
    find_orphaned_cassettes,
    sanitize_headers,
    sanitize_payload,
)


class TestVCRCassetteGuard(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="vcr_test_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_sanitize_headers(self):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer super-secret-jwt-token-12345",
            "Cookie": "session_id=xyz; auth=abc",
            "X-Api-Key": "live_key_9999",
            "User-Agent": "Mozilla/5.0",
        }
        sanitized = sanitize_headers(headers)
        self.assertEqual(sanitized["Content-Type"], "application/json")
        self.assertEqual(sanitized["User-Agent"], "Mozilla/5.0")
        self.assertEqual(sanitized["Authorization"], REDACTED_VALUE)
        self.assertEqual(sanitized["Cookie"], REDACTED_VALUE)
        self.assertEqual(sanitized["X-Api-Key"], REDACTED_VALUE)

    def test_sanitize_payload_nested(self):
        payload = {
            "user": "test_user",
            "password": "ClearTextPassword123",
            "api_key": "secret_abc",
            "metadata": {
                "access_token": "token_xyz",
                "normal_field": "visible",
                "nested_list": [
                    {"client_secret": "shhh", "item": 1},
                    {"description": "public"},
                ],
            },
            "auth_header": "Bearer ghp_1234567890abcdef1234567890",
        }
        sanitized = sanitize_payload(payload)
        self.assertEqual(sanitized["user"], "test_user")
        self.assertEqual(sanitized["password"], REDACTED_VALUE)
        self.assertEqual(sanitized["api_key"], REDACTED_VALUE)
        self.assertEqual(sanitized["metadata"]["access_token"], REDACTED_VALUE)
        self.assertEqual(sanitized["metadata"]["normal_field"], "visible")
        self.assertEqual(sanitized["metadata"]["nested_list"][0]["client_secret"], REDACTED_VALUE)
        self.assertEqual(sanitized["metadata"]["nested_list"][0]["item"], 1)
        self.assertEqual(sanitized["metadata"]["nested_list"][1]["description"], "public")
        self.assertIn(f"Bearer {REDACTED_VALUE}", sanitized["auth_header"])

    def test_record_and_replay_interaction(self):
        guard = VCRCassetteGuard(cassette_dir=self.temp_dir, mode="record")
        req = {
            "method": "POST",
            "url": "https://api.crm.example/v1/deals",
            "headers": {"Authorization": "Bearer secret123", "Accept": "application/json"},
            "body": {"deal_name": "Mega Deal", "password": "sensitive_pwd"},
        }
        res = {
            "status": 201,
            "headers": {"Content-Type": "application/json"},
            "body": {"id": "deal_001", "deal_name": "Mega Deal"},
        }

        path = guard.record_interaction("create_deal", req, res)
        self.assertTrue(os.path.exists(path))

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["interactions"]), 1)
        stored_req = data["interactions"][0]["request"]
        self.assertEqual(stored_req["headers"]["Authorization"], REDACTED_VALUE)
        self.assertEqual(stored_req["body"]["password"], REDACTED_VALUE)
        self.assertEqual(stored_req["body"]["deal_name"], "Mega Deal")

        # Test Replay
        replay_guard = VCRCassetteGuard(cassette_dir=self.temp_dir, mode="replay")
        replayed_res = replay_guard.replay_interaction("create_deal", req)
        self.assertEqual(replayed_res["status"], 201)
        self.assertEqual(replayed_res["body"]["id"], "deal_001")

    def test_replay_mismatch_and_not_found(self):
        guard = VCRCassetteGuard(cassette_dir=self.temp_dir, mode="replay")
        with self.assertRaises(CassetteNotFoundError):
            guard.replay_interaction("non_existent", {"method": "GET", "url": "/test"})

        # Record one endpoint
        record_guard = VCRCassetteGuard(cassette_dir=self.temp_dir, mode="record")
        record_guard.record_interaction(
            "existing",
            {"method": "GET", "url": "/endpoint-a"},
            {"status": 200, "body": "ok"},
        )

        with self.assertRaises(CassetteMismatchError):
            record_guard.replay_interaction(
                "existing",
                {"method": "GET", "url": "/endpoint-different"},
            )

    def test_ast_orphan_cassette_detection(self):
        cassettes_dir = os.path.join(self.temp_dir, "tests", "cassettes")
        tests_dir = os.path.join(self.temp_dir, "tests")
        os.makedirs(cassettes_dir, exist_ok=True)

        # Create two cassette files
        used_cassette = os.path.join(cassettes_dir, "user_login.json")
        orphan_cassette = os.path.join(cassettes_dir, "abandoned_payment.json")
        for p in (used_cassette, orphan_cassette):
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"interactions": []}, f)

        # Create a Python test referencing user_login
        test_py = os.path.join(tests_dir, "test_auth.py")
        with open(test_py, "w", encoding="utf-8") as f:
            f.write(
                'import pytest\n\n'
                '@pytest.mark.vcr(cassette="user_login")\n'
                'def test_login():\n'
                '    assert True\n'
            )

        orphans = find_orphaned_cassettes(self.temp_dir, cassette_dir=cassettes_dir)
        self.assertEqual(len(orphans), 1)
        self.assertTrue(orphans[0].endswith("abandoned_payment.json"))

        # Now add a reference to abandoned_payment in a TS test file
        test_ts = os.path.join(tests_dir, "payment.spec.ts")
        with open(test_ts, "w", encoding="utf-8") as f:
            f.write("test('pay', async () => { use_cassette('abandoned_payment'); });")

        orphans_after = find_orphaned_cassettes(self.temp_dir, cassette_dir=cassettes_dir)
        self.assertEqual(len(orphans_after), 0)

    def test_cli_execution(self):
        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "vcr_cassette_guard.py")
        res = subprocess.run([sys.executable, script, "--help"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("VCR Cassette Guard", res.stdout)


if __name__ == "__main__":
    unittest.main()
