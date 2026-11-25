#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""4-Scenario Unit Tests for tools/heal/heuristic_locator_matcher.py."""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.heal.heuristic_locator_matcher import (
    HeuristicLocatorMatcher,
    levenshtein_distance,
    levenshtein_ratio,
)


class TestHeuristicLocatorMatcher:
    def test_levenshtein_metrics(self):
        assert levenshtein_distance("abc", "abc") == 0
        assert levenshtein_distance("", "xyz") == 3
        assert levenshtein_distance("xyz", "") == 3
        assert levenshtein_ratio("Confirm", "Confirm") == 1.0
        assert levenshtein_ratio("", "") == 1.0
        assert 0.0 < levenshtein_ratio("Submit Order", "Submit Order Now") < 1.0

    def test_layer1_exact_attribute_and_layer2_semantic(self):
        snapshot = [
            {"tag": "input", "id": "email", "name": "user_email"},
            {"tag": "button", "data-testid": "checkout-submit", "text": "Place Order", "aria-label": "Place Order"},
        ]
        res1 = HeuristicLocatorMatcher.match("#checkout-submit", dom_snapshot=snapshot)
        assert res1["matched"] is True
        assert res1["layer"] == 1
        assert res1["healed_locator"] == "[data-testid='checkout-submit']"

        res2 = HeuristicLocatorMatcher.match("//button[text()='Place Order']", dom_snapshot=snapshot)
        assert res2["matched"] is True
        assert res2["layer"] in (1, 2)
        assert res2["confidence"] >= 0.85

    def test_layer3_geometric_relative_matching_and_boundary(self):
        snapshot = [
            {"tag": "label", "id": "lbl-password", "x": 100, "y": 100, "width": 120, "height": 24},
            {"tag": "input", "id": "txt-password", "bbox": {"x": 100, "y": 140, "width": 200, "height": 32}},
            {"tag": "button", "data-testid": "btn-signin", "text": "Sign In", "x": 100, "y": 200, "width": 100, "height": 36},
        ]
        res_below = HeuristicLocatorMatcher.match(
            "#stale-login",
            dom_snapshot=snapshot,
            relative={"relation": "below", "anchor": "#txt-password"},
        )
        assert res_below["matched"] is True
        assert res_below["layer"] == 3
        assert "btn-signin" in res_below["healed_locator"]

        res_empty = HeuristicLocatorMatcher.match("#missing", dom_snapshot=[])
        assert res_empty["matched"] is False
        assert res_empty["layer"] == 4
