# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
examples/mobile-crm-suite/pages/CustomerFormScreen.py
------------------------------------------------------
Screen Object Model for New/Edit Customer Creation Screen.
Encapsulates form input, field validation error checks, and submission.
"""

from typing import Any, Tuple, Optional
try:
    from .BaseScreen import BaseScreen
except ImportError:
    from pages.BaseScreen import BaseScreen


class CustomerFormScreen(BaseScreen):
    """Encapsulates creation form controls for Synapse CRM Mobile."""

    LOC_TXT_COMPANY: Tuple[str, str] = ("accessibility id", "input_company_name")
    LOC_TXT_EMAIL: Tuple[str, str] = ("accessibility id", "input_contact_email")
    LOC_TXT_PHONE: Tuple[str, str] = ("accessibility id", "input_phone_number")
    LOC_TXT_VAT: Tuple[str, str] = ("accessibility id", "input_vat_number")
    LOC_BTN_SAVE: Tuple[str, str] = ("accessibility id", "btn_submit_customer")
    LOC_BTN_CANCEL: Tuple[str, str] = ("accessibility id", "btn_cancel_customer")
    LOC_ERR_COMPANY: Tuple[str, str] = ("accessibility id", "err_company_required")
    LOC_ERR_EMAIL: Tuple[str, str] = ("accessibility id", "err_email_invalid")

    def __init__(self, driver: Any):
        super().__init__(driver)

    def is_screen_visible(self) -> bool:
        """Verifies customer form screen is active."""
        try:
            return self.wait_for_visible(self.LOC_BTN_SAVE, timeout=4.0).is_displayed()
        except Exception:
            return False

    def fill_and_submit(
        self,
        company: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        vat: Optional[str] = None,
    ) -> None:
        """Fills form fields and taps Save button."""
        self.enter_text_safe(self.LOC_TXT_COMPANY, company)
        if email:
            self.enter_text_safe(self.LOC_TXT_EMAIL, email)
        if phone:
            self.enter_text_safe(self.LOC_TXT_PHONE, phone)
        if vat:
            self.enter_text_safe(self.LOC_TXT_VAT, vat)
        self.click_safe(self.LOC_BTN_SAVE)

    def is_company_error_visible(self) -> bool:
        """Checks if required Company name validation error is displayed."""
        try:
            return self.wait_for_visible(self.LOC_ERR_COMPANY, timeout=2.0).is_displayed()
        except Exception:
            return False

    def is_email_error_visible(self) -> bool:
        """Checks if invalid email format validation error is displayed."""
        try:
            return self.wait_for_visible(self.LOC_ERR_EMAIL, timeout=2.0).is_displayed()
        except Exception:
            return False

    def cancel(self) -> None:
        """Taps Cancel to dismiss form without saving."""
        self.click_safe(self.LOC_BTN_CANCEL)
