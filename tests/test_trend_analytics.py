#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_trend_analytics.py
-----------------------------
Unit tests for Historical Quality Trend & Flakiness Analytics Engine:
1. Snapshot recording and rolling ledger persistence.
2. Pure SVG trend chart generation.
3. Execution duration bar chart generation.
4. Rolling window capacity capping (<= 50 entries).
"""

import os
import sys
import unittest
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from trend_analytics import (
    load_history_ledger,
    save_history_ledger,
    record_snapshot,
    seed_sample_history_if_empty,
    generate_trend_svg,
    generate_duration_svg,
    MAX_HISTORY_ENTRIES
)


class TestTrendAnalytics(unittest.TestCase):

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        self.temp_path = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        if os.path.isfile(self.temp_path):
            os.remove(self.temp_path)

    def test_record_snapshot_and_load(self):
        """Verifies snapshot recording and ledger retrieval."""
        snapshot = record_snapshot(
            gates_passed=10,
            total_gates=10,
            mutation_score=91.5,
            tests_total=30,
            tests_passed=30,
            tests_failed=0,
            duration_s=4.8,
            suite_name="Unit Verification",
            ledger_path=self.temp_path
        )
        self.assertTrue(snapshot["id"].startswith("run_"))
        self.assertEqual(snapshot["pass_rate"], 100.0)
        self.assertEqual(snapshot["mutation_score"], 91.5)

        ledger = load_history_ledger(self.temp_path)
        self.assertEqual(len(ledger), 1)
        self.assertEqual(ledger[0]["suite"], "Unit Verification")

    def test_rolling_window_capping(self):
        """Ensures ledger never exceeds MAX_HISTORY_ENTRIES (50)."""
        entries = [{"id": f"run_{i}", "duration_s": 1.0} for i in range(MAX_HISTORY_ENTRIES + 15)]
        save_history_ledger(entries, self.temp_path)

        loaded = load_history_ledger(self.temp_path)
        self.assertEqual(len(loaded), MAX_HISTORY_ENTRIES)
        self.assertEqual(loaded[-1]["id"], f"run_{MAX_HISTORY_ENTRIES + 14}")

    def test_seed_sample_history(self):
        """Verifies initial sample seeding when ledger is empty."""
        seed_sample_history_if_empty(self.temp_path)
        ledger = load_history_ledger(self.temp_path)
        self.assertGreaterEqual(len(ledger), 5)
        self.assertIn("Hub DoD v3.2.2", [r["suite"] for r in ledger])

    def test_generate_trend_svg(self):
        """Verifies pure SVG trend line chart synthesis."""
        seed_sample_history_if_empty(self.temp_path)
        svg = generate_trend_svg(ledger_path=self.temp_path)
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("polyline", svg)
        self.assertIn("polygon", svg)
        self.assertIn("Mutation Sensitivity", svg)
        self.assertTrue(svg.endswith("</svg>"))

    def test_generate_duration_svg(self):
        """Verifies pure SVG execution duration bar chart synthesis."""
        seed_sample_history_if_empty(self.temp_path)
        svg = generate_duration_svg(ledger_path=self.temp_path)
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("<rect", svg)
        self.assertIn("Execution Duration", svg)
        self.assertTrue(svg.endswith("</svg>"))


if __name__ == "__main__":
    unittest.main()
