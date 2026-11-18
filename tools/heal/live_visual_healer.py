#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Live Visual Healer & Playwright Grounding Bridge
------------------------------------------------
Provides end-to-end self-healing for live Playwright browser sessions
when standard DOM locators fail (Canvas, WebGL, Shadow DOM, cross-origin iframes).

Pipeline:
  1. Primary Action: Attempts standard Playwright locator click/action.
  2. Failure Intercept: Catches locator timeout or missing element errors.
  3. Visual Capture: Takes full-page or viewport screenshot to temp file.
  4. Set-of-Marks (SoM) Grounding:
     - Uses VisualSoMHelper to detect interactive regions or perceptual cache.
     - Feeds marks into HeuristicLocatorMatcher (Layer 3.5 SoM Grounding).
  5. Physical Mouse Dispatch:
     - Directly executes page.mouse.click(x, y) at the grounded center coordinates.
  6. Audit Ledger:
     - Records healing telemetry to 'reports/visual_healing_ledger.json'.
"""
from __future__ import annotations

import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import os
import sys
import json
import time
import tempfile
from typing import Dict, Any, Optional

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
REPORTS_DIR = os.path.join(REPO_ROOT, "reports")

from tools.heal.visual_som_helper import VisualSoMHelper
from tools.heal.heuristic_locator_matcher import HeuristicLocatorMatcher


def record_healing_event(
    broken_locator: str,
    action: str,
    coordinates: Dict[str, int],
    strategy: str,
    confidence: float,
    screenshot_path: Optional[str] = None
) -> None:
    """Records self-healing event to persistent JSON ledger for audit and telemetry."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    ledger_path = os.path.join(REPORTS_DIR, "visual_healing_ledger.json")

    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "broken_locator": broken_locator,
        "action": action,
        "coordinates": coordinates,
        "strategy": strategy,
        "confidence": confidence,
        "screenshot_saved": bool(screenshot_path and os.path.exists(screenshot_path)),
    }

    ledger = []
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            ledger = []

    ledger.append(entry)
    try:
        with open(ledger_path, "w", encoding="utf-8") as f:
            json.dump(ledger, f, indent=2)
    except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
        pass


class LiveVisualHealer:
    """Synchronous & Asynchronous Playwright Visual Self-Healing Interceptor."""

    def __init__(self, debug_shots: bool = False):
        self.som_helper = VisualSoMHelper()
        self.debug_shots = debug_shots

    def heal_and_click_sync(
        self,
        page: Any,
        broken_locator: str,
        timeout_ms: int = 3000,
        fallback_keyword: Optional[str] = None,
    ) -> bool:
        """
        Executes a click action on a synchronous Playwright page with automatic
        Layer 3.5 Set-of-Marks visual fallback upon timeout.
        """
        try:
            # 1. Primary standard locator attempt
            page.locator(broken_locator).click(timeout=timeout_ms)
            return True
        except Exception as primary_err:
            # 2. Intercept failure and capture screenshot
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                shot_path = tf.name

            try:
                page.screenshot(path=shot_path)

                # 3. Detect visual regions via SoM helper
                regions = self.som_helper.detect_canvas_interactive_regions(shot_path)
                visual_context = {"marks": regions}

                # 4. Match via Layer 3.5 SoM Grounding
                match_res = HeuristicLocatorMatcher.match(
                    broken_locator=broken_locator,
                    dom_snapshot=[],
                    visual_context=visual_context,
                    screenshot_path=shot_path,
                )

                if match_res.get("matched") and match_res.get("coordinates"):
                    coords = match_res["coordinates"]
                    x, y = coords["x"], coords["y"]

                    # 5. Physical mouse dispatch
                    page.mouse.click(x, y)

                    # 6. Record audit ledger
                    record_healing_event(
                        broken_locator=broken_locator,
                        action="click",
                        coordinates=coords,
                        strategy=match_res.get("strategy", "VISUAL_SOM"),
                        confidence=match_res.get("confidence", 0.9),
                        screenshot_path=shot_path if self.debug_shots else None,
                    )
                    return True
                else:
                    raise primary_err
            finally:
                if not self.debug_shots and os.path.exists(shot_path):
                    try:
                        os.remove(shot_path)
                    except OSError:  # synapse-ignore: SWALLOWED_EXCEPTION
                        pass

    async def heal_and_click_async(
        self,
        page: Any,
        broken_locator: str,
        timeout_ms: int = 3000,
        fallback_keyword: Optional[str] = None,
    ) -> bool:
        """
        Executes a click action on an asynchronous Playwright page with automatic
        Layer 3.5 Set-of-Marks visual fallback upon timeout.
        """
        try:
            # 1. Primary standard locator attempt
            await page.locator(broken_locator).click(timeout=timeout_ms)
            return True
        except Exception as primary_err:
            # 2. Intercept failure and capture screenshot
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                shot_path = tf.name

            try:
                await page.screenshot(path=shot_path)

                # 3. Detect visual regions via SoM helper
                regions = self.som_helper.detect_canvas_interactive_regions(shot_path)
                visual_context = {"marks": regions}

                # 4. Match via Layer 3.5 SoM Grounding
                match_res = HeuristicLocatorMatcher.match(
                    broken_locator=broken_locator,
                    dom_snapshot=[],
                    visual_context=visual_context,
                    screenshot_path=shot_path,
                )

                if match_res.get("matched") and match_res.get("coordinates"):
                    coords = match_res["coordinates"]
                    x, y = coords["x"], coords["y"]

                    # 5. Physical mouse dispatch
                    await page.mouse.click(x, y)

                    # 6. Record audit ledger
                    record_healing_event(
                        broken_locator=broken_locator,
                        action="click",
                        coordinates=coords,
                        strategy=match_res.get("strategy", "VISUAL_SOM"),
                        confidence=match_res.get("confidence", 0.9),
                        screenshot_path=shot_path if self.debug_shots else None,
                    )
                    return True
                else:
                    raise primary_err
            finally:
                if not self.debug_shots and os.path.exists(shot_path):
                    try:
                        os.remove(shot_path)
                    except OSError:  # synapse-ignore: SWALLOWED_EXCEPTION
                        pass
