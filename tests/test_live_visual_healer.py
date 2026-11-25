#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_live_visual_healer.py — Unit Tests for Live Visual Self-Healing
-------------------------------------------------------------------------
Verifies:
1. LiveVisualHealer transparently passes successful primary locator actions.
2. Intercepts broken locator failures and falls back to Layer 3.5 SoM coordinates.
3. Successfully dispatches physical mouse clicks and updates visual healing ledger.
"""

import os
import sys
import json
import unittest
from unittest.mock import MagicMock, patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from tools.heal.live_visual_healer import LiveVisualHealer, record_healing_event


class TestLiveVisualHealer(unittest.TestCase):
    """Test suite for Playwright Live Visual Healer."""

    def setUp(self):
        self.healer = LiveVisualHealer(debug_shots=False)

    def test_primary_locator_success(self):
        """When primary locator succeeds, no visual fallback is needed."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_page.locator.return_value = mock_locator

        success = self.healer.heal_and_click_sync(mock_page, "button#active-btn", timeout_ms=500)
        self.assertTrue(success)
        mock_locator.click.assert_called_once_with(timeout=500)
        mock_page.screenshot.assert_not_called()
        mock_page.mouse.click.assert_not_called()

    @patch("tools.heuristic_locator_matcher.HeuristicLocatorMatcher.match")
    def test_visual_fallback_intercepts_failure(self, mock_match):
        """When primary locator throws TimeoutError, SoM fallback clicks center coordinates."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.click.side_effect = TimeoutError("Locator timeout")
        mock_page.locator.return_value = mock_locator

        # Mock HeuristicLocatorMatcher returning Layer 3.5 visual match
        mock_match.return_value = {
            "matched": True,
            "layer": 3.5,
            "strategy": "VISUAL_SOM_GROUNDING",
            "coordinates": {"x": 300, "y": 500},
            "confidence": 0.94,
        }

        # Test the direct fallback logic
        healer = LiveVisualHealer(debug_shots=False)
        with patch.object(healer.som_helper, "detect_canvas_interactive_regions", return_value=[{"x": 200, "y": 400}]):
            res = healer.heal_and_click_sync(mock_page, "button#broken-cta", timeout_ms=100)

        self.assertTrue(res)
        mock_page.screenshot.assert_called_once()
        mock_page.mouse.click.assert_called_once_with(300, 500)

    @patch("tools.heuristic_locator_matcher.HeuristicLocatorMatcher.match")
    def test_visual_fallback_dpi_normalization(self, mock_match):
        """When devicePixelRatio is 2.0 (Retina display), image coordinates are scaled down by 2x."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.click.side_effect = TimeoutError("Locator timeout")
        mock_page.locator.return_value = mock_locator
        # Simulate Retina 2x DPI
        mock_page.evaluate.return_value = 2.0

        mock_match.return_value = {
            "matched": True,
            "layer": 3.5,
            "strategy": "VISUAL_SOM_GROUNDING",
            "coordinates": {"x": 600, "y": 800},
            "confidence": 0.95,
        }

        healer = LiveVisualHealer(debug_shots=False)
        with patch.object(healer.som_helper, "detect_canvas_interactive_regions", return_value=[{"x": 600, "y": 800}]):
            res = healer.heal_and_click_sync(mock_page, "button#retina-cta", timeout_ms=100)

        self.assertTrue(res)
        # Should click normalized CSS pixels: (600 / 2, 800 / 2) -> (300, 400)
        mock_page.mouse.click.assert_called_once_with(300, 400)

    def test_record_healing_event(self):
        """Verify healing telemetry records valid JSON entry inside an isolated temp reports dir."""
        import tempfile
        import shutil
        tmp_dir = tempfile.mkdtemp()
        try:
            with patch("tools.heal.live_visual_healer.REPORTS_DIR", tmp_dir):
                record_healing_event(
                    broken_locator="button#submit-order",
                    action="click",
                    coordinates={"x": 250, "y": 450},
                    strategy="VISUAL_SOM_GROUNDING",
                    confidence=0.92,
                )
            ledger_path = os.path.join(tmp_dir, "visual_healing_ledger.json")
            self.assertTrue(os.path.exists(ledger_path))
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
            self.assertEqual(len(ledger), 1)
            latest = ledger[-1]
            self.assertEqual(latest["broken_locator"], "button#submit-order")
            self.assertEqual(latest["coordinates"], {"x": 250, "y": 450})
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
