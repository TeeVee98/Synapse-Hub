#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

import os
import sys
import unittest
import tempfile
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools")))
from token_telemetry import TokenTelemetryStore


class TestTokenTelemetry(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_telemetry.db")
        self.store = TokenTelemetryStore(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_and_compute_summary(self):
        self.store.record_fix("BUG-1", "playwright", 500, 100, 20.0, 0)
        self.store.record_fix("BUG-2", "playwright", 800, 200, 40.0, 1)

        summary = self.store.compute_summary("playwright")
        self.assertEqual(summary["count"], 2)
        self.assertGreater(summary["median_mttr_s"], 0)
        self.assertEqual(summary["avg_retries"], 0.5)

    def test_empty_summary(self):
        summary = self.store.compute_summary("non_existent")
        self.assertEqual(summary["count"], 0)
        self.assertEqual(summary["median_mttr_s"], 0.0)


if __name__ == "__main__":
    unittest.main()
