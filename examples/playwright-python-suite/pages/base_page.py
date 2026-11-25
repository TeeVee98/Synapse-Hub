# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT

"""BasePage encapsulating Playwright Python smart waits and dynamic data generation."""

from __future__ import annotations

import time
import uuid


class BasePage:
    """Base Page Object enforcing dynamic waits and zero hardcoded selectors in tests."""

    def __init__(self, page) -> None:
        self.page = page

    @staticmethod
    def unique_code(prefix: str = "PY_") -> str:
        """Generates collision-free dynamic identifier using timestamp and random hex."""
        return f"{prefix}{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"

    def navigate(self, url: str) -> None:
        """Navigates to target URL and waits for DOMContentLoaded readiness."""
        self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_load_state("domcontentloaded")
