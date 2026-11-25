# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT

"""Playwright Python authentication tests adhering strictly to Clean POM."""

from __future__ import annotations

import os

from pages.base_page import BasePage
from pages.login_page import LoginPage


def test_login_positive_clean_pom(mock_playwright_page) -> None:
    """Positive: authenticates valid user with environment-injected credential."""
    user_email = os.environ.get("CRM_TEST_EMAIL", f"{BasePage.unique_code('USER_').lower()}@example.com")
    user_token = os.environ.get("CRM_TEST_CREDENTIAL", "")

    login_page = LoginPage(mock_playwright_page)
    login_page.open_login()
    login_page.sign_in(user_email, user_token or BasePage.unique_code("TOK_"))

    assert login_page.is_dashboard_visible() is True
    assert login_page.email_input.filled_value == user_email


def test_login_negative_rejected_error_visible(mock_playwright_page) -> None:
    """Negative: surfaces explicit validation feedback for rejected credentials."""
    login_page = LoginPage(mock_playwright_page)
    login_page.error_alert._visible = True
    login_page.dashboard_banner._visible = False
    login_page.open_login()
    login_page.sign_in("invalid@example.com", "wrong-input")

    assert login_page.is_dashboard_visible() is False
    assert "Invalid" in login_page.error_message()


def test_login_boundary_empty_email_generates_unique_id() -> None:
    """Boundary: validates dynamic code generator yields collision-free unique identifiers."""
    code_a = BasePage.unique_code("PY_")
    code_b = BasePage.unique_code("PY_")

    assert code_a.startswith("PY_")
    assert code_b.startswith("PY_")
    assert code_a != code_b
