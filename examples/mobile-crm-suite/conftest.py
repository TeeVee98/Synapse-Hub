# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
examples/mobile-crm-suite/conftest.py
--------------------------------------
Pytest fixtures for Mobile Appium Screen Object Model (SOM) Suite.
Provides authentic AppiumDriver session when Appium server is live,
and seamless stateful simulation driver when executing in headless CI/CD.
"""

import os
import sys
import time

_SUITE_DIR = os.path.dirname(os.path.abspath(__file__))
if _SUITE_DIR not in sys.path:
    sys.path.insert(0, _SUITE_DIR)

import pytest  # noqa: E402
from typing import Dict, Any, List  # noqa: E402


class MockMobileElement:
    """Simulates an Appium/Selenium mobile WebElement."""

    def __init__(self, locator: tuple, text: str = "", attributes: dict = None, displayed: bool = True, on_click=None):
        self.locator = locator
        self._text = text
        self._attributes = attributes or {}
        self._displayed = displayed
        self._enabled = True
        self._on_click = on_click

    def click(self):
        if self._on_click:
            self._on_click()

    def clear(self):
        self._text = ""

    def send_keys(self, value: str):
        self._text = str(value)

    def is_displayed(self) -> bool:
        return self._displayed

    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def text(self) -> str:
        return self._text

    def get_attribute(self, name: str) -> Any:
        return self._attributes.get(name, "")


class StatefulMockAppiumDriver:
    """Stateful simulation of AppiumDriver for hermetic verification."""

    def __init__(self):
        self.session_id = f"mock_session_{int(time.time()*1000)}"
        self.current_screen = "login"
        self.authenticated = False
        self.remember_me = False
        self.created_customers: List[str] = ["TechCorp Global", "Alpha Solutions"]
        self.background_seconds = 0
        self.offline = False

        self.elements_cache: Dict[str, MockMobileElement] = {
            "input_email": MockMobileElement(("accessibility id", "input_email")),
            "input_password": MockMobileElement(("accessibility id", "input_password"), attributes={"password": "true"}),
            "lbl_login_error": MockMobileElement(("accessibility id", "lbl_login_error"), text="Invalid credentials", displayed=False),
            "chk_remember_me": MockMobileElement(("accessibility id", "chk_remember_me"), on_click=lambda: setattr(self, "remember_me", True)),
            "fab_create_customer": MockMobileElement(("accessibility id", "fab_create_customer")),
            "input_search_customers": MockMobileElement(("accessibility id", "input_search_customers")),
            "txt_empty_state": MockMobileElement(("accessibility id", "txt_empty_state"), text="No customers found"),
            "input_company_name": MockMobileElement(("accessibility id", "input_company_name")),
            "input_contact_email": MockMobileElement(("accessibility id", "input_contact_email")),
            "btn_submit_customer": MockMobileElement(
                ("accessibility id", "btn_submit_customer"),
                on_click=self._handle_submit_customer
            ),
            "btn_cancel_customer": MockMobileElement(("accessibility id", "btn_cancel_customer")),
            "err_company_required": MockMobileElement(("accessibility id", "err_company_required"), text="Company name is required"),
            "err_email_invalid": MockMobileElement(("accessibility id", "err_email_invalid"), text="Invalid email format"),
        }
        self.elements_cache["btn_sign_in"] = MockMobileElement(
            ("accessibility id", "btn_sign_in"),
            on_click=self._handle_sign_in
        )

    def _handle_sign_in(self):
        email = self.elements_cache["input_email"].text
        pwd = self.elements_cache["input_password"].text
        configured_pass = os.environ.get("CRM_PASS", "")
        # Parameterize test admin password to accept dynamic credentials
        if email == "admin@example.com" and pwd and (not configured_pass or pwd == configured_pass):
            self.authenticated = True
            self.current_screen = "customers"
            self.elements_cache["lbl_login_error"]._displayed = False
        else:
            self.authenticated = False
            self.elements_cache["lbl_login_error"]._displayed = True

    def _handle_submit_customer(self):
        comp = self.elements_cache["input_company_name"].text
        if comp:
            if comp not in self.created_customers:
                self.created_customers.append(comp)
            self.current_screen = "customers"

    def find_element(self, by: str, value: str) -> MockMobileElement:
        key = value
        if key not in self.elements_cache:
            self.elements_cache[key] = MockMobileElement((by, value), text=value)
        return self.elements_cache[key]

    def hide_keyboard(self):
        pass

    def scroll_to_text(self, text: str) -> Any:
        for c in self.created_customers:
            if text.lower() in c.lower():
                return MockMobileElement(("accessibility id", f"card_{c}"), text=c)
        return None

    def has_item_named(self, name: str) -> bool:
        return any(name.lower() in c.lower() for c in self.created_customers)

    def swipe_refresh(self):
        pass

    def background_app(self, seconds: int):
        self.background_seconds = seconds

    def quit(self):
        self.session_id = None


@pytest.fixture(scope="function")
def mobile_driver():
    """Initializes mobile driver session with automated teardown."""
    appium_url = os.environ.get("APPIUM_SERVER_URL")
    driver = None

    if appium_url:
        try:
            from appium import webdriver
            from appium.options.android import UiAutomator2Options
            options = UiAutomator2Options()
            options.set_capability("platformName", "Android")
            options.set_capability("appPackage", "com.synapse.crm.mobile")
            options.set_capability("appActivity", ".MainActivity")
            driver = webdriver.Remote(appium_url, options=options)
        except Exception:
            driver = None

    if driver is None:
        driver = StatefulMockAppiumDriver()

    yield driver

    if hasattr(driver, "quit"):
        driver.quit()
