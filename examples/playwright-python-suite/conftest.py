# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT

"""Shared Pytest fixtures providing a deterministic headless Page double when Chromium is offline."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest

SUITE_ROOT = os.path.dirname(os.path.abspath(__file__))
if SUITE_ROOT not in sys.path:
    sys.path.insert(0, SUITE_ROOT)


class _DummyLocator:
    """Lightweight Playwright Locator stand-in supporting visibility and interaction checks."""

    def __init__(self, text: str = "CRM Dashboard", visible: bool = True) -> None:
        self._text = text
        self._visible = visible
        self.filled_value = ""

    def wait_for(self, state: str = "visible", timeout: int = 10000) -> None:
        return None

    def fill(self, value: str) -> None:
        self.filled_value = value

    def click(self) -> None:
        return None

    def is_visible(self) -> bool:
        return self._visible

    def inner_text(self) -> str:
        return self._text


@pytest.fixture
def mock_playwright_page():
    """Creates a synthetic Playwright Page supporting Clean POM workflows without live network."""
    page = MagicMock()
    page.url = "https://crm-demo.local/dashboard"
    email_loc = _DummyLocator()
    secret_loc = _DummyLocator()
    submit_loc = _DummyLocator()
    banner_loc = _DummyLocator("Welcome Admin", visible=True)
    error_loc = _DummyLocator("Invalid credentials", visible=False)

    page.get_by_label.side_effect = lambda label: email_loc if "Email" in label else secret_loc
    page.get_by_role.return_value = submit_loc
    page.get_by_test_id.side_effect = lambda tid: banner_loc if "dashboard" in tid else error_loc
    page.wait_for_load_state.return_value = None
    return page
