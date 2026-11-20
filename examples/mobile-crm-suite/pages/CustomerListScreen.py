# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
examples/mobile-crm-suite/pages/CustomerListScreen.py
------------------------------------------------------
Screen Object Model for the CRM Customers Main List Screen.
Encapsulates list scrolling, search filtering, pull-to-refresh, and FAB actions.
"""

from typing import Any, Tuple
try:
    from .BaseScreen import BaseScreen
except ImportError:
    from pages.BaseScreen import BaseScreen


class CustomerListScreen(BaseScreen):
    """Encapsulates list, search, and navigation controls for Customers view."""

    LOC_SEARCH_INPUT: Tuple[str, str] = ("accessibility id", "input_search_customers")
    LOC_FAB_NEW_CUSTOMER: Tuple[str, str] = ("accessibility id", "fab_create_customer")
    LOC_RECYCLER_VIEW: Tuple[str, str] = ("accessibility id", "recycler_customers")
    LOC_TXT_EMPTY_STATE: Tuple[str, str] = ("accessibility id", "txt_empty_state")
    LOC_BTN_LOGOUT: Tuple[str, str] = ("accessibility id", "btn_action_logout")
    LOC_HEADER_TITLE: Tuple[str, str] = ("accessibility id", "txt_screen_title")

    def __init__(self, driver: Any):
        super().__init__(driver)

    def is_screen_visible(self) -> bool:
        """Verifies customer list screen is active and displayed."""
        try:
            return self.wait_for_visible(self.LOC_FAB_NEW_CUSTOMER, timeout=5.0).is_displayed()
        except Exception:
            return False

    def search_customer(self, keyword: str) -> None:
        """Enters search term into the mobile search bar."""
        self.enter_text_safe(self.LOC_SEARCH_INPUT, keyword)

    def open_new_customer(self) -> None:
        """Taps the Floating Action Button (FAB) to open customer creation form."""
        self.click_safe(self.LOC_FAB_NEW_CUSTOMER)

    def refresh_list(self) -> None:
        """Performs pull-to-refresh swipe to trigger real-time list sync."""
        self.swipe_down_to_refresh()

    def has_customer(self, company_name: str) -> bool:
        """Scrolls if needed and checks if company card is present in list."""
        el = self.scroll_into_view_safe(company_name)
        if el is not None:
            return True
        if hasattr(self.driver, "has_item_named"):
            return self.driver.has_item_named(company_name)
        return False

    def is_empty_state_displayed(self) -> bool:
        """Verifies if empty state banner is visible."""
        try:
            return self.wait_for_visible(self.LOC_TXT_EMPTY_STATE, timeout=2.0).is_displayed()
        except Exception:
            return False
