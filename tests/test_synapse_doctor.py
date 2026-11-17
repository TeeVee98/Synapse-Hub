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

from tools.synapse_doctor import (
    check_ci_and_display_environment,
    check_filesystem_health,
    check_python_environment,
    run_doctor_diagnostics,
)


class TestSynapseDoctor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="doctor_test_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_check_python_environment(self):
        res = check_python_environment()
        self.assertEqual(res["name"], "Python Runtime")
        self.assertTrue(res["passed"])
        self.assertIn("Python 3.", res["message"])

    def test_check_filesystem_health(self):
        res = check_filesystem_health(self.temp_dir)
        self.assertEqual(res["name"], "Filesystem Health")
        self.assertTrue(res["passed"])
        self.assertTrue(res["workspace_writable"])
        self.assertTrue(res["temp_writable"])

    def test_check_ci_and_display_environment(self):
        res = check_ci_and_display_environment()
        self.assertEqual(res["name"], "Display / CI Environment")
        self.assertIn("passed", res)

    def test_run_doctor_diagnostics_structure(self):
        report = run_doctor_diagnostics(self.temp_dir)
        self.assertIn("timestamp", report)
        self.assertIn("platform", report)
        self.assertEqual(report["total_checks"], 6)
        self.assertIsInstance(report["checks"], list)

    def test_cli_execution(self):
        script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "synapse_doctor.py")
        res = subprocess.run(
            [sys.executable, script, "--repo-root", self.temp_dir, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertIn("checks", data)


if __name__ == "__main__":
    unittest.main()
