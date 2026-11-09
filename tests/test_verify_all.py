#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/test_verify_all.py — Unit Tests for 10 Quality Gates Sentinel
"""

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

    def test_format_gates_junit(self):
        results = [
            ("Gate 0: Author Integrity", True, "Passed"),
            ("Gate 1: BOM Check", False, "1 BOM violation detected"),
        ]
        xml = verify_all.format_gates_junit(results, REPO_ROOT)
        self.assertIn('<testsuite name="synapse-quality-gates" tests="2" failures="1"', xml)
        self.assertIn('<failure message="Quality Gate Failed: Gate 1: BOM Check">', xml)


if __name__ == "__main__":
    unittest.main()
