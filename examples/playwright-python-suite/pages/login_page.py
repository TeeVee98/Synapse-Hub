# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT

"""LoginPage encapsulating authentication selectors and semantic assertions."""

from __future__ import annotations

from pages.base_page import BasePage


class LoginPage(BasePage):
    """Clean POM Page Class for CRM authentication."""

    def __init__(self, page) -> None:
        super().__init__(page)
        self.email_input = self.page.get_by_label("Email")
        self.secret_input = self.page.get_by_label("Credential")
        self.submit_button = self.page.get_by_role("button", name="Sign In")
        self.dashboard_banner = self.page.get_by_test_id("dashboard-welcome")
        self.error_alert = self.page.get_by_test_id("auth-error")

    def open_login(self, base_url: str = "https://crm-demo.local/login") -> "LoginPage":
        """Opens the CRM login view."""
        self.navigate(base_url)
        return self

    def sign_in(self, email: str, secret: str) -> "LoginPage":
        """Submits user credentials using encapsulated ARIA locators."""
        self.email_input.wait_for(state="visible", timeout=10000)
        self.email_input.fill(email)
        self.secret_input.fill(secret)
        self.submit_button.click()
        return self

    def is_dashboard_visible(self) -> bool:
        """Checks dashboard readiness after sign-in."""
        return bool(self.dashboard_banner.is_visible())

    def error_message(self) -> str:
        """Returns validation message text when authentication is rejected."""
        return self.error_alert.inner_text()
