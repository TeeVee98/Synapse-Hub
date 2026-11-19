#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for Gate 2: Path Portability Sentinel."""

import os
import shutil
import tempfile
import unittest

from tools.core.gates.gate_02_portability import Gate02Portability, gate_2_path_portability


class TestGate02Portability(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="synapse_test_gate2_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_relative_paths_pass(self):
        file_path = os.path.join(self.temp_dir, "portable.ts")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("import { foo } from '../utils/helper';\nconst relPath = './data/fixture.json';\n")

        self.assertTrue(gate_2_path_portability(self.temp_dir, mode="TARGET"))
        gate = Gate02Portability()
        res = gate.execute(self.temp_dir, mode="TARGET")
        self.assertTrue(res.passed)

    def test_absolute_windows_user_path_fails(self):
        file_path = os.path.join(self.temp_dir, "non_portable.ts")
        win_path = "C:\\" + "Users" + "\\JohnDoe\\project\\data.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"const localFile = '{win_path}';\n")

        self.assertFalse(gate_2_path_portability(self.temp_dir, mode="TARGET"))
        gate = Gate02Portability()
        res = gate.execute(self.temp_dir, mode="TARGET")
        self.assertFalse(res.passed)

    def test_absolute_unix_user_path_fails(self):
        file_path = os.path.join(self.temp_dir, "unix_abs.py")
        unix_path = "/" + "home" + "/johndoe/workspace/target"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"ABS_DIR = '{unix_path}'\n")

        self.assertFalse(gate_2_path_portability(self.temp_dir, mode="TARGET"))


if __name__ == "__main__":
    unittest.main()
