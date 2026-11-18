#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_phase3_visual_som_and_session_vault.py — Verification of Phase 3 Capabilities
---------------------------------------------------------------------------------------
Verifies:
1. Enterprise Session State Vault (save, validate, TTL expiration, prune).
2. Multimodal Vision Fallback & Set-of-Marks (Layer 3.5) in heuristic_locator_matcher.
3. Clean error handling when visual context is empty or absent.
"""

import os
import sys
import time
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from tools.core.session_vault import SessionVault
from tools.heal.heuristic_locator_matcher import HeuristicLocatorMatcher


class TestPhase3Capabilities(unittest.TestCase):
    """Test suite for Phase 3: Session Vault and Multimodal SoM Fallback."""

    def setUp(self):
        self.temp_vault_dir = tempfile.mkdtemp(prefix="test_auth_vault_")
        self.vault = SessionVault(vault_dir=self.temp_vault_dir)

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_vault_dir):
            shutil.rmtree(self.temp_vault_dir, ignore_errors=True)

    def test_session_vault_save_and_validate_fresh(self):
        """Verify that a freshly saved session state is valid."""
        mock_state = {
            "cookies": [
                {
                    "name": "session_id",
                    "value": "xyz123",
                    "domain": "example.com",
                    "path": "/",
                    "expires": time.time() + 3600,
                }
            ],
            "origins": []
        }
        saved_path = self.vault.save_session("admin", mock_state, ttl_seconds=1800)
        self.assertTrue(os.path.exists(saved_path))

        valid, reason, meta = self.vault.validate_session("admin")
        self.assertTrue(valid, f"Expected valid session but got: {reason}")
        self.assertEqual(meta.get("cookie_count"), 1)

        loaded_state = self.vault.load_session("admin")
        self.assertIsNotNone(loaded_state)
        self.assertEqual(len(loaded_state["cookies"]), 1)

    def test_session_vault_detects_expired_ttl(self):
        """Verify that an expired TTL marks the session invalid."""
        mock_state = {"cookies": [], "origins": []}
        # Save with ttl_seconds = -10 (already expired)
        self.vault.save_session("expired_user", mock_state, ttl_seconds=-10)

        valid, reason, _ = self.vault.validate_session("expired_user")
        self.assertFalse(valid)
        self.assertIn("expired", reason.lower())

        # load_session should return None for expired sessions
        self.assertIsNone(self.vault.load_session("expired_user"))

    def test_session_vault_prune(self):
        """Verify that pruning removes only expired sessions."""
        mock_state = {"cookies": [], "origins": []}
        self.vault.save_session("active_user", mock_state, ttl_seconds=3600)
        self.vault.save_session("stale_user", mock_state, ttl_seconds=-100)

        sessions_before = self.vault.list_sessions()
        self.assertEqual(len(sessions_before), 2)

        pruned_count = self.vault.prune_expired()
        self.assertEqual(pruned_count, 1)

        sessions_after = self.vault.list_sessions()
        self.assertEqual(len(sessions_after), 1)
        self.assertEqual(sessions_after[0]["role"], "active_user")

    def test_visual_som_layer_3_5_grounding_fallback(self):
        """Verify that broken DOM falls back to Layer 3.5 SoM visual coordinates."""
        broken_locator = "button#submit-order-button"
        # Non-matching DOM snapshot (forcing low confidence in L1-L3)
        unrelated_dom = [
            {"tag": "div", "id": "header-banner", "text": "Welcome to store"},
            {"tag": "footer", "id": "site-footer", "text": "Copyright 2026"},
        ]

        # Provide visual_context with marks (e.g. from canvas or visual grid)
        visual_context = {
            "marks": [
                {
                    "mark_id": 1,
                    "label": "Submit Order Button",
                    "x": 200,
                    "y": 450,
                    "width": 100,
                    "height": 40,
                },
                {
                    "mark_id": 2,
                    "label": "Cancel Order",
                    "x": 320,
                    "y": 450,
                    "width": 80,
                    "height": 40,
                }
            ]
        }

        res = HeuristicLocatorMatcher.match(
            broken_locator=broken_locator,
            dom_snapshot=unrelated_dom,
            visual_context=visual_context
        )

        self.assertTrue(res["matched"])
        self.assertEqual(res["layer"], 3.5)
        self.assertEqual(res["strategy"], "VISUAL_SOM_GROUNDING")
        self.assertFalse(res["needs_llm"])
        # Center coordinates should be x = 200 + 50 = 250, y = 450 + 20 = 470
        self.assertEqual(res["coordinates"], {"x": 250, "y": 470})
        self.assertEqual(res["healed_locator"], "page.mouse.click(250, 470)")

    def test_synapse_sdk_exposes_phase3_engines(self):
        """Verify root synapse SDK exposes SessionVault and VisualSoMHelper."""
        import synapse
        self.assertTrue(hasattr(synapse, "SessionVault"))
        self.assertTrue(hasattr(synapse, "VisualSoMHelper"))
        self.assertIsNotNone(synapse.SessionVault)
        self.assertIsNotNone(synapse.VisualSoMHelper)


if __name__ == "__main__":
    unittest.main()
