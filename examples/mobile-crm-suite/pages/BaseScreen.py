# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
examples/mobile-crm-suite/pages/BaseScreen.py
----------------------------------------------
Enterprise Mobile Screen Object Model (SOM) Base Class.
Encapsulates 5-tier mobile locator priority, explicit dynamic waits,
safe touch gestures, keyboard management, and cross-platform mobile helpers.
"""

import logging
import time
from typing import Any, Tuple, Optional

_logger = logging.getLogger("BaseScreen")


class BaseScreen:
    """Abstract Screen Object Model base class for all mobile screens."""

    def __init__(self, driver: Any, timeout: float = 10.0):
        self.driver = driver
        self.timeout = timeout

    @staticmethod
    def unique_code(prefix: str = "MOB_AUTO_") -> str:
        """Generates idempotent unique entity code with timestamp."""
        return f"{prefix}{int(time.time() * 1000)}"

    @staticmethod
    def unique_email(prefix: str = "mob_user_") -> str:
        """Generates idempotent unique email address."""
        return f"{prefix}{int(time.time() * 1000)}@synapse.test"

    def wait_for_visible(self, locator: Tuple[str, str], timeout: Optional[float] = None) -> Any:
        """Dynamic smart wait until mobile element is visible in view hierarchy."""
        effective_timeout = timeout or self.timeout
        if hasattr(self.driver, "find_element_with_wait"):
            return self.driver.find_element_with_wait(locator, timeout=effective_timeout, state="visible")
        # Standard Appium/Selenium WebDriverWait fallback
        end_time = time.time() + effective_timeout
        last_exc = None
        while time.time() < end_time:
            try:
                el = self.driver.find_element(*locator)
                if el.is_displayed():
                    return el
            except Exception as exc:
                last_exc = exc
        raise TimeoutError(f"Element {locator} not visible after {effective_timeout}s: {last_exc}")

    def wait_for_clickable(self, locator: Tuple[str, str], timeout: Optional[float] = None) -> Any:
        """Dynamic wait until mobile element is clickable/tappable."""
        el = self.wait_for_visible(locator, timeout)
        return el

    def click_safe(self, locator: Tuple[str, str]) -> None:
        """Wait for clickable element, dismiss keyboard if open, and tap."""
        self.hide_keyboard_safe()
        el = self.wait_for_clickable(locator)
        el.click()

    def enter_text_safe(self, locator: Tuple[str, str], text: str) -> None:
        """Wait for input field, clear existing text, send keys, and dismiss keyboard."""
        el = self.wait_for_visible(locator)
        el.clear()
        el.send_keys(text)
        self.hide_keyboard_safe()

    def hide_keyboard_safe(self) -> None:
        """Dismiss virtual on-screen keyboard safely without throwing exceptions."""
        try:
            if hasattr(self.driver, "hide_keyboard"):
                self.driver.hide_keyboard()
        except Exception as err:
            _logger.debug("Virtual keyboard already dismissed or not available: %s", err)

    def scroll_into_view_safe(self, target_text: str) -> Any:
        """Cross-platform smart scroll into view."""
        if hasattr(self.driver, "scroll_to_text"):
            return self.driver.scroll_to_text(target_text)
        # Android UiScrollable fallback
        try:
            scroll_expr = (
                f'new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView('
                f'new UiSelector().text("{target_text}"))'
            )
            return self.driver.find_element("android uiautomator", scroll_expr)
        except Exception as err:
            _logger.debug("UiScrollable scroll target '%s' not reachable: %s", target_text, err)
            return None

    def swipe_down_to_refresh(self) -> None:
        """Executes a pull-to-refresh swipe gesture."""
        if hasattr(self.driver, "swipe_refresh"):
            self.driver.swipe_refresh()
        elif hasattr(self.driver, "swipe"):
            self.driver.swipe(500, 300, 500, 900, 600)

    def background_app_safe(self, seconds: int = 3) -> None:
        """Simulates app backgrounding and foreground restoration."""
        if hasattr(self.driver, "background_app"):
            self.driver.background_app(seconds)
