#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Deep unit tests for tools/update_sentinel.py to achieve >= 80% coverage
"""

import os
import json
import time
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import tools.update_sentinel as us


class TestUpdateSentinelDeep(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="sentinel_test_")
        self.orig_cache = us.CACHE_FILE
        self.test_cache = os.path.join(self.temp_dir, "test_cache.json")
        us.CACHE_FILE = self.test_cache

    def tearDown(self):
        us.CACHE_FILE = self.orig_cache
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_semver_edge_cases(self):
        self.assertEqual(us.parse_semver("v3.2.1"), (3, 2, 1))
        self.assertEqual(us.parse_semver("3.0"), (3, 0, 0))
        self.assertEqual(us.parse_semver("4"), (4, 0, 0))
        self.assertEqual(us.parse_semver("invalid.text.here"), (0, 0, 0))

    def test_get_local_version_fallbacks(self):
        with patch("os.path.exists", return_value=False):
            ver = us.get_local_version()
            self.assertTrue(isinstance(ver, str) and len(ver.split(".")) >= 3)

    @patch("urllib.request.urlopen")
    def test_fetch_remote_version_npm_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"version": "4.0.0"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        ver, src = us.fetch_remote_version()
        self.assertEqual(ver, "4.0.0")
        self.assertEqual(src, "npm")

    @patch("urllib.request.urlopen")
    def test_fetch_remote_version_github_fallback(self, mock_urlopen):
        # First call (npm) fails, second call (github) succeeds
        import urllib.error
        mock_enter = MagicMock()
        mock_enter.read.return_value = json.dumps({"version": "3.5.0"}).encode("utf-8")
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_enter

        mock_urlopen.side_effect = [urllib.error.URLError("NPM down"), mock_cm]

        ver, src = us.fetch_remote_version()
        self.assertEqual(ver, "3.5.0")
        self.assertEqual(src, "github")

    def test_fetch_remote_version_offline(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Total network failure")):
            ver, src = us.fetch_remote_version()
            self.assertIsNone(ver)
            self.assertIsNone(src)

    def test_check_for_updates_offline_env_guards(self):
        with patch.dict(os.environ, {"AGENT_QA_OFFLINE": "1"}):
            has_up, local, remote = us.check_for_updates()
            self.assertFalse(has_up)
            self.assertIsNone(remote)

        with patch.dict(os.environ, {"CI": "true"}):
            has_up, local, remote = us.check_for_updates()
            self.assertFalse(has_up)
            self.assertIsNone(remote)

    def test_check_for_updates_cache_fresh(self):
        # Pre-seed cache with a recent check
        now = time.time()
        us.write_update_cache({
            "latest_remote_version": "3.2.0",
            "last_check_timestamp": now - 100,  # 100s ago < 24h
        })
        env_clean = {k: v for k, v in os.environ.items() if k not in ("CI", "GITHUB_ACTIONS", "AGENT_QA_OFFLINE", "SYNAPSE_OFFLINE")}
        with patch.dict(os.environ, env_clean, clear=True):
            with patch("tools.update_sentinel.fetch_remote_version") as mock_fetch:
                has_up, local, remote = us.check_for_updates(force=False, notify=False)
                self.assertFalse(has_up)
                mock_fetch.assert_not_called()

    def test_check_for_updates_newer_version(self):
        now = time.time()
        us.write_update_cache({
            "latest_remote_version": "9.9.9",
            "last_check_timestamp": now - 100,
        })
        env_clean = {k: v for k, v in os.environ.items() if k not in ("CI", "GITHUB_ACTIONS", "AGENT_QA_OFFLINE", "SYNAPSE_OFFLINE")}
        with patch.dict(os.environ, env_clean, clear=True):
            with patch("tools.update_sentinel.print_update_banner") as mock_banner:
                has_up, local, remote = us.check_for_updates(force=False, notify=True)
                self.assertTrue(has_up)
                self.assertEqual(remote, "9.9.9")
                mock_banner.assert_called_once()

    def test_print_update_banner_output(self):
        # Ensure it prints without exception
        us.print_update_banner("3.2.0", "4.0.0")

    def test_trusted_remote_verification(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="https://github.com/teevee998/synapse-hub.git\n")
            self.assertTrue(us._is_trusted_remote(self.temp_dir))

            mock_run.return_value = MagicMock(returncode=0, stdout="https://github.com/evil/fork.git\n")
            self.assertFalse(us._is_trusted_remote(self.temp_dir))

    def test_verify_git_provenance(self):
        with patch("tools.update_sentinel._is_trusted_remote", return_value=False):
            ok, msg = us.verify_git_provenance(self.temp_dir)
            self.assertTrue(ok)
            self.assertIn("bypassed", msg)

        with patch("tools.update_sentinel._is_trusted_remote", return_value=True):
            with patch("subprocess.run") as mock_run:
                # Good commit
                mock_run.return_value = MagicMock(returncode=0, stdout="abcdef12 G TeeVee998\n")
                ok, msg = us.verify_git_provenance(self.temp_dir)
                self.assertTrue(ok)
                self.assertIn("Verified", msg)

                # Bad signature
                mock_run.return_value = MagicMock(returncode=0, stdout="bad12345 B BadActor\n")
                ok, msg = us.verify_git_provenance(self.temp_dir)
                self.assertFalse(ok)
                self.assertIn("Bad/forged", msg)

    @patch("subprocess.run")
    def test_perform_update_git_flow(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Already up to date.\n", stderr="")
        with patch("tools.update_sentinel.check_for_updates", return_value=(True, "3.2.0", "3.3.0")):
            with patch("os.path.exists", return_value=True):
                res = us.perform_update()
                self.assertTrue(res)


if __name__ == "__main__":
    unittest.main()
