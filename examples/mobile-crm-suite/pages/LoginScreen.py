# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
examples/mobile-crm-suite/pages/LoginScreen.py
-----------------------------------------------
Screen Object Model implementation for Mobile Authentication Screen.
Strictly encapsulates Tier 1 (Accessibility ID) and Tier 2 (Resource-ID) locators.
Flat Architecture: 1-level inheritance from BaseScreen.
"""

from typing import Any, Tuple
try:
    from .BaseScreen import BaseScreen
except ImportError:
    from pages.BaseScreen import BaseScreen


class LoginScreen(BaseScreen):
    """Encapsulates all authentication controls and interactions for Synapse CRM Mobile."""

    # --- Locators (Tier 1: Accessibility ID / Tier 2: Android Resource-ID) ---
    LOC_TXT_EMAIL: Tuple[str, str] = ("accessibility id", "input_email")
    LOC_TXT_PASSWORD: Tuple[str, str] = ("accessibility id", "input_password")
    LOC_BTN_LOGIN: Tuple[str, str] = ("accessibility id", "btn_sign_in")
    LOC_LBL_ERROR: Tuple[str, str] = ("accessibility id", "lbl_login_error")
    LOC_CHK_REMEMBER: Tuple[str, str] = ("accessibility id", "chk_remember_me")
    LOC_HEADER_TITLE: Tuple[str, str] = ("accessibility id", "txt_welcome_title")

    def __init__(self, driver: Any):
        super().__init__(driver)

    def login(self, email: str, password: str, remember_me: bool = False) -> None:
        """Performs full login sequence through Screen Object encapsulation."""
        self.enter_text_safe(self.LOC_TXT_EMAIL, email)
        self.enter_text_safe(self.LOC_TXT_PASSWORD, password)
        if remember_me:
            self.click_safe(self.LOC_CHK_REMEMBER)
        self.click_safe(self.LOC_BTN_LOGIN)

    def is_error_displayed(self) -> bool:
        """Returns True if error banner is displayed on screen."""
        try:
            el = self.wait_for_visible(self.LOC_LBL_ERROR, timeout=3.0)
            return el.is_displayed()
        except Exception:
            return False

    def get_error_message(self) -> str:
        """Reads text from login error banner."""
        el = self.wait_for_visible(self.LOC_LBL_ERROR, timeout=3.0)
        return getattr(el, "text", "")

    def is_password_masked(self) -> bool:
        """Verifies native password input field is masked with password attribute."""
        el = self.wait_for_visible(self.LOC_TXT_PASSWORD)
        return el.get_attribute("password") in ("true", True, "1")

    def is_login_screen_visible(self) -> bool:
        """Verifies if login screen header and fields are visible."""
        try:
            return self.wait_for_visible(self.LOC_BTN_LOGIN, timeout=3.0).is_displayed()
        except Exception:
            return False
