#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for Gate 6: Credential Security Sentinel."""

import os
import shutil
import tempfile
import unittest

from tools.core.gates.gate_06_credentials import Gate06Credentials, gate_6_credential_security


class TestGate06Credentials(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="synapse_test_gate6_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_clean_codebase_passes(self):
        file_path = os.path.join(self.temp_dir, "config.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("import os\nDB_PASS = os.getenv('DB_PASSWORD')\n")

        self.assertTrue(gate_6_credential_security(self.temp_dir, mode="TARGET"))
        gate = Gate06Credentials()
        res = gate.execute(self.temp_dir, mode="TARGET")
        self.assertTrue(res.passed)

    def test_hardcoded_aws_key_fails(self):
        file_path = os.path.join(self.temp_dir, "aws_secret.py")
        # Build token dynamically to prevent self-scan detection in this test file
        aws_token = "AKIA" + "IOSFODNN7EXAMPLE"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"AWS_KEY = '{aws_token}'\n")

        self.assertFalse(gate_6_credential_security(self.temp_dir, mode="TARGET"))
        gate = Gate06Credentials()
        res = gate.execute(self.temp_dir, mode="TARGET")
        self.assertFalse(res.passed)

    def test_unprotected_password_in_glbl_fails(self):
        profiles_dir = os.path.join(self.temp_dir, "Profiles")
        os.makedirs(profiles_dir, exist_ok=True)
        glbl_file = os.path.join(profiles_dir, "default.glbl")
        with open(glbl_file, "w", encoding="utf-8") as f:
            f.write("""<GlobalVariableEntity>
                <description></description>
                <initValue>'secret'</initValue>
                <name>PASSWORD</name>
                <protected>false</protected>
            </GlobalVariableEntity>""")

        self.assertFalse(gate_6_credential_security(self.temp_dir, mode="TARGET"))


if __name__ == "__main__":
    unittest.main()
