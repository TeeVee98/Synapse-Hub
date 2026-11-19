#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for Gate 1: UTF-8 No BOM & Clean Encoding Sentinel."""

import os
import shutil
import tempfile
import unittest

from tools.core.gates.gate_01_utf8 import Gate01UTF8, gate_1_bom_check


class TestGate01UTF8(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="synapse_test_gate1_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_clean_utf8_file_passes(self):
        file_path = os.path.join(self.temp_dir, "clean.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# Clean UTF-8 file\nx = 42\n")

        self.assertTrue(gate_1_bom_check(self.temp_dir, mode="TARGET"))
        gate = Gate01UTF8()
        res = gate.execute(self.temp_dir, mode="TARGET")
        self.assertTrue(res.passed)

    def test_utf8_with_bom_fails(self):
        file_path = os.path.join(self.temp_dir, "with_bom.py")
        with open(file_path, "wb") as f:
            f.write(b"\xef\xbb\xbf# UTF-8 with BOM\nx = 42\n")

        self.assertFalse(gate_1_bom_check(self.temp_dir, mode="TARGET"))
        gate = Gate01UTF8()
        res = gate.execute(self.temp_dir, mode="TARGET")
        self.assertFalse(res.passed)

    def test_mojibake_encoding_fails(self):
        file_path = os.path.join(self.temp_dir, "mojibake.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("Some text with corrupted characters: \u00c3\u00a1\n")

        self.assertFalse(gate_1_bom_check(self.temp_dir, mode="TARGET"))


if __name__ == "__main__":
    unittest.main()
