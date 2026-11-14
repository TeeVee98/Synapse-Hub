#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_verify_all.py — Unit Tests for 10 Quality Gates Sentinel
"""

import io
import json
import os
import sys
import unittest
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

import verify_all


class TestVerifyAllGates(unittest.TestCase):
    """Tests individual Quality Gate sentinels in verify_all."""

    def test_detect_repo_mode_hub(self):
        mode = verify_all.detect_repo_mode(REPO_ROOT)
        self.assertEqual(mode, "HUB")

    def test_detect_repo_mode_client(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mode = verify_all.detect_repo_mode(tmpdir)
            self.assertEqual(mode, "TARGET")

    def test_gate_1_bom_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            clean_file = os.path.join(tmpdir, "clean.groovy")
            with open(clean_file, "wb") as f:
                f.write("class CleanPage {}".encode("utf-8"))
            self.assertTrue(verify_all.gate_1_bom_check(tmpdir, mode="TARGET"))

    def test_gate_1_bom_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bom_file = os.path.join(tmpdir, "bom.groovy")
            with open(bom_file, "wb") as f:
                f.write(b"\xef\xbb\xbfclass BomPage {}")
            self.assertFalse(verify_all.gate_1_bom_check(tmpdir, mode="TARGET"))

    def test_gate_2_path_portability_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            clean_file = os.path.join(tmpdir, "script.py")
            with open(clean_file, "w", encoding="utf-8") as f:
                f.write("import os\npath = os.path.join('.', 'data')\n")
            self.assertTrue(verify_all.gate_2_path_portability(tmpdir, mode="TARGET"))

    def test_gate_2_path_portability_forbidden(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = os.path.join(tmpdir, "bad_script.py")
            forbidden_sample = "".join(["C:", "\\Users\\", "Administrator\\", "secret"])
            with open(bad_file, "w", encoding="utf-8") as f:
                f.write(f'hardcoded_path = "{forbidden_sample}"\n')
            self.assertFalse(verify_all.gate_2_path_portability(tmpdir, mode="TARGET"))

    def test_gate_2_path_portability_quoted_users_and_home_paths(self):
        bad_users = "".join(["/", "Users", "/developer/project"])
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = os.path.join(tmpdir, "bad_quoted.py")
            with open(bad_file, "w", encoding="utf-8") as f:
                f.write(f'DEV_PATH = "{bad_users}"\n')
            self.assertFalse(verify_all.gate_2_path_portability(tmpdir, mode="TARGET"))

        bad_home = "".join(["/", "home", "/jenkins/build"])
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = os.path.join(tmpdir, "bad_home.py")
            with open(bad_file, "w", encoding="utf-8") as f:
                f.write(f"HOME_PATH = '{bad_home}'\n")
            self.assertFalse(verify_all.gate_2_path_portability(tmpdir, mode="TARGET"))

    def test_pre_commit_guard_scans_python_files(self):
        from git_pre_commit_guard import check_forbidden_paths
        secret_path = "".join(["/", "Users", "/developer/secret"])
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tf:
            tf.write(f'SECRET_DIR = "{secret_path}"\n')
            tf_path = tf.name
        try:
            violations = check_forbidden_paths([tf_path])
            self.assertGreater(len(violations), 0, "Pre-commit guard must flag forbidden paths in .py files")
        finally:
            if os.path.exists(tf_path):
                os.unlink(tf_path)

    def test_gate_5_cleanup_blacklist_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertTrue(verify_all.gate_5_cleanup_blacklist(tmpdir, mode="CLIENT"))

    def test_gate_5_cleanup_blacklist_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            leak_file = os.path.join(tmpdir, "run_debug.txt")
            with open(leak_file, "w", encoding="utf-8") as f:
                f.write("temporary log")
            self.assertFalse(verify_all.gate_5_cleanup_blacklist(tmpdir, mode="CLIENT"))

    def test_gate_6_credential_security_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            clean_file = os.path.join(tmpdir, "config.py")
            with open(clean_file, "w", encoding="utf-8") as f:
                f.write("AUTH_HEADER = 'Bearer ' + os.environ.get('TOKEN', '')\n")
            self.assertTrue(verify_all.gate_6_credential_security(tmpdir, mode="CLIENT"))

    def test_gate_6_credential_security_forbidden(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            leak_file = os.path.join(tmpdir, "secrets.py")
            priv_key = "".join(["-----BEGIN ", "RSA ", "PRIVATE ", "KEY-----"])
            with open(leak_file, "w", encoding="utf-8") as f:
                f.write(f'KEY = "{priv_key}\\nMIICXAIBAAKCAQEA0"\n')
            self.assertFalse(verify_all.gate_6_credential_security(tmpdir, mode="CLIENT"))

    def test_gate_10_performance_sla_skipped_when_no_reports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertTrue(verify_all.gate_10_performance_sla(tmpdir, mode="CLIENT"))

    def test_gate_10_performance_sla_passes_on_good_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            perf_dir = os.path.join(tmpdir, "Reports", "perf")
            os.makedirs(perf_dir, exist_ok=True)
            jtl_file = os.path.join(perf_dir, "results.jtl")
            with open(jtl_file, "w", encoding="utf-8") as f:
                f.write("timeStamp,elapsed,label,responseCode,responseMessage,threadName,dataType,success,failureMessage,bytes,sentBytes,grpThreads,allThreads,URL,Latency,IdleTime,Connect\n")
                f.write("1700000000000,120,GET /api/v1/items,200,OK,Thread 1-1,text,true,,1024,256,1,1,http://api.local/items,110,0,10\n")
                f.write("1700000000100,150,GET /api/v1/items,200,OK,Thread 1-1,text,true,,1024,256,1,1,http://api.local/items,140,0,10\n")
            self.assertTrue(verify_all.gate_10_performance_sla(tmpdir, mode="CLIENT"))

    def test_gate_10_performance_sla_fails_on_sla_breach(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            perf_dir = os.path.join(tmpdir, "Reports", "perf")
            os.makedirs(perf_dir, exist_ok=True)
            jtl_file = os.path.join(perf_dir, "results.jtl")
            with open(jtl_file, "w", encoding="utf-8") as f:
                f.write("timeStamp,elapsed,label,responseCode,responseMessage,threadName,dataType,success,failureMessage,bytes,sentBytes,grpThreads,allThreads,URL,Latency,IdleTime,Connect\n")
                # Exceeds default SLA P95 of 500ms
                f.write("1700000000000,1500,POST /api/v1/orders,500,Internal Error,Thread 1-1,text,false,Timeout,1024,256,1,1,http://api.local/orders,1490,0,10\n")
            self.assertFalse(verify_all.gate_10_performance_sla(tmpdir, mode="CLIENT"))

    def test_gate_5_heapsnapshot_exempt_in_reports_perf(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            perf_dir = os.path.join(tmpdir, "Reports", "perf")
            os.makedirs(perf_dir, exist_ok=True)
            allowed_heap = os.path.join(perf_dir, "test.heapsnapshot")
            with open(allowed_heap, "w", encoding="utf-8") as f:
                f.write("{}")
            self.assertTrue(verify_all.gate_5_cleanup_blacklist(tmpdir, mode="CLIENT"))

            # Rogue heap snapshot in repo root must fail
            rogue_heap = os.path.join(tmpdir, "leak.heapsnapshot")
            with open(rogue_heap, "w", encoding="utf-8") as f:
                f.write("{}")
            self.assertFalse(verify_all.gate_5_cleanup_blacklist(tmpdir, mode="CLIENT"))

    def test_format_gates_junit(self):
        results = [
            ("Gate 1: BOM Check", True, "Passed"),
            ("Gate 2: Path Portability", False, "1 path violation detected"),
        ]
        xml = verify_all.format_gates_junit(results, REPO_ROOT)
        self.assertIn('<testsuite name="synapse-quality-gates" tests="2" failures="1"', xml)
        self.assertIn('<failure message="Quality Gate Failed: Gate 2: Path Portability">', xml)

    def test_verify_all_json_format_purity(self):
        """Verifies that run_all_gates with output_format='json' emits strictly parseable JSON to stdout."""
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            code = verify_all.run_all_gates(REPO_ROOT, mode="HUB", output_format="json")
            output = sys.stdout.getvalue().strip()
        finally:
            sys.stdout = old_stdout

        self.assertEqual(code, 0, "All gates should pass in HUB mode")
        self.assertTrue(output.startswith("{"), f"JSON output must start with '{{', got: {output[:50]}")
        self.assertTrue(output.endswith("}"), f"JSON output must end with '}}', got: {output[-50:]}")
        parsed = json.loads(output)
        self.assertIn("all_passed", parsed)
        self.assertEqual(len(parsed["gates"]), 10)


if __name__ == "__main__":
    unittest.main()
