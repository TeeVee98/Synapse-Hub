#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/test_ui_server.py
-----------------------
Unit and integration tests for Synapse Hub Interactive QA Mission Control:
1. JobManager execution, streaming logs, and lifecycle.
2. HTTP REST APIs: /api/status, /api/run, /api/run/<id>.
3. Path traversal security on /reports/*.
4. Port allocation resilience.
"""

import os
import sys
import time
import json
import socket
import unittest
import urllib.request
import urllib.error
from threading import Thread

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from ui_server import (
    JobManager,
    ThreadingHTTPServer,
    SynapseUiHandler,
    find_free_port,
    COMMAND_MAP
)


class TestUiServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.port = find_free_port(9850)
        cls.server = ThreadingHTTPServer(("127.0.0.1", cls.port), SynapseUiHandler)
        cls.server_thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        time.sleep(0.3)  # Allow server to bind

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_job_manager_lifecycle(self):
        """Verifies JobManager starts, streams output, and terminates cleanly."""
        jm = JobManager()
        self.assertIn("version", COMMAND_MAP)

        job_id = jm.start_job("version")
        self.assertTrue(job_id.startswith("job_"))

        # Wait for job to complete
        start_wait = time.time()
        completed = False
        while time.time() - start_wait < 5.0:
            info = jm.get_job(job_id)
            if info and info["status"] in ("PASSED", "FAILED"):
                completed = True
                break
            time.sleep(0.1)

        self.assertTrue(completed, "Job did not complete within timeout")
        final_info = jm.get_job(job_id)
        self.assertEqual(final_info["status"], "PASSED")
        self.assertEqual(final_info["exit_code"], 0)
        self.assertTrue(len(final_info["logs"]) > 0)
        log_text = "".join(final_info["logs"])
        self.assertIn("Agent-QA Hub CLI", log_text)

    def test_job_manager_rejects_disallowed_command(self):
        """Ensures JobManager strictly rejects arbitrary unauthorized commands."""
        jm = JobManager()
        with self.assertRaises(ValueError):
            jm.start_job("malicious_command_injection")

    def test_api_status_endpoint(self):
        """Tests GET /api/status returns valid JSON metadata."""
        url = f"{self.base_url}/api/status"
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("version"), "3.2.2")
            self.assertEqual(data.get("status"), "ONLINE")
            self.assertIn("TeeVee998", data.get("author", ""))

    def test_get_index_html(self):
        """Tests GET / serves the SPA dashboard HTML."""
        url = f"{self.base_url}/"
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            content = resp.read().decode("utf-8")
            self.assertIn("SYNAPSE HUB", content)
            self.assertIn("MISSION CONTROL", content)

    def test_api_run_flow(self):
        """Tests POST /api/run and subsequent polling via GET /api/run/<id>."""
        run_url = f"{self.base_url}/api/run"
        payload = json.dumps({"command": "version"}).encode("utf-8")
        req = urllib.request.Request(run_url, data=payload, headers={"Content-Type": "application/json"})

        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            job_id = data.get("job_id")
            self.assertTrue(job_id)

        # Poll the job
        poll_url = f"{self.base_url}/api/run/{job_id}?offset=0"
        with urllib.request.urlopen(poll_url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            poll_data = json.loads(resp.read().decode("utf-8"))
            self.assertIn(poll_data.get("status"), ("RUNNING", "PASSED"))

    def test_path_traversal_protection_on_reports(self):
        """Verifies directory traversal attacks are blocked on /reports/."""
        traversal_url = f"{self.base_url}/reports/../../etc/passwd"
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(traversal_url, timeout=3.0)
        self.assertEqual(ctx.exception.code, 404)

    def test_find_free_port(self):
        """Verifies find_free_port returns a bindable port."""
        port = find_free_port(10000)
        self.assertIsInstance(port, int)
        self.assertGreaterEqual(port, 10000)


if __name__ == "__main__":
    unittest.main()
