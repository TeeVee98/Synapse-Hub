#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for Gate 5: Temporary Files Blacklist Sentinel."""

import os
import shutil
import tempfile
import unittest

from tools.core.gates.gate_05_blacklist import Gate05Blacklist, gate_5_cleanup_blacklist


class TestGate05Blacklist(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="synapse_test_gate5_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_clean_workspace_passes(self):
        file_path = os.path.join(self.temp_dir, "normal_file.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("Clean file\n")

        self.assertTrue(gate_5_cleanup_blacklist(self.temp_dir, mode="TARGET"))
        gate = Gate05Blacklist()
        res = gate.execute(self.temp_dir, mode="TARGET")
        self.assertTrue(res.passed)

    def test_debug_output_fails(self):
        bad_file = os.path.join(self.temp_dir, "debug_output.txt")
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write("Debug info\n")

        self.assertFalse(gate_5_cleanup_blacklist(self.temp_dir, mode="TARGET"))
        gate = Gate05Blacklist()
        res = gate.execute(self.temp_dir, mode="TARGET")
        self.assertFalse(res.passed)

    def test_heapsnapshot_exempt_in_reports_perf(self):
        perf_dir = os.path.join(self.temp_dir, "Reports", "perf")
        os.makedirs(perf_dir, exist_ok=True)
        exempt_file = os.path.join(perf_dir, "heap.heapsnapshot")
        with open(exempt_file, "w", encoding="utf-8") as f:
            f.write("Heap snapshot data")

        self.assertTrue(gate_5_cleanup_blacklist(self.temp_dir, mode="TARGET"))


if __name__ == "__main__":
    unittest.main()
