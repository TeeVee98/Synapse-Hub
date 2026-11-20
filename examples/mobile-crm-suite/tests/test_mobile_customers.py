# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
examples/mobile-crm-suite/tests/test_mobile_customers.py
---------------------------------------------------------
Mobile Appium Customer Management Test Suite (Clean SOM Flat Architecture).
Orchestrates Screen Object Model methods only. Zero raw selectors in scripts.
"""

import pytest
from pages import CustomerListScreen, CustomerFormScreen, BaseScreen


@pytest.mark.mobile
@pytest.mark.smoke
def test_mob_06_customer_list_displayed(mobile_driver):
    """TC-MOB-06: Verify Customer List screen is visible and active."""
    customer_list = CustomerListScreen(mobile_driver)
    assert customer_list.is_screen_visible()


@pytest.mark.mobile
@pytest.mark.regression
def test_mob_07_create_customer_happy_path(mobile_driver):
    """TC-MOB-07: Happy Path - Create new customer with unique code and verify."""
    customer_list = CustomerListScreen(mobile_driver)
    form_screen = CustomerFormScreen(mobile_driver)

    unique_company = BaseScreen.unique_code("MOB_CORP_")
    unique_email = BaseScreen.unique_email("corp_")

    customer_list.open_new_customer()
    assert form_screen.is_screen_visible()

    form_screen.fill_and_submit(
        company=unique_company,
        email=unique_email,
        phone="+84901234567",
        vat="VN0102030405",
    )
    assert customer_list.has_customer(unique_company)


@pytest.mark.mobile
@pytest.mark.regression
def test_mob_08_create_customer_missing_company_blocked(mobile_driver):
    """TC-MOB-08: Validation - Blank company name triggers validation error."""
    customer_list = CustomerListScreen(mobile_driver)
    form_screen = CustomerFormScreen(mobile_driver)

    customer_list.open_new_customer()
    form_screen.fill_and_submit(company="", email="test@synapse.test")
    assert form_screen.is_company_error_visible()


@pytest.mark.mobile
@pytest.mark.regression
def test_mob_09_create_customer_invalid_email_error(mobile_driver):
    """TC-MOB-09: Validation - Invalid email syntax displays email error."""
    customer_list = CustomerListScreen(mobile_driver)
    form_screen = CustomerFormScreen(mobile_driver)

    customer_list.open_new_customer()
    form_screen.fill_and_submit(company="Acme Corp", email="invalid-email-format")
    assert form_screen.is_email_error_visible()


@pytest.mark.mobile
@pytest.mark.regression
def test_mob_10_search_existing_customer(mobile_driver):
    """TC-MOB-10: Search - Keyword search on customer list filters matching company."""
    customer_list = CustomerListScreen(mobile_driver)

    customer_list.search_customer("TechCorp")
    assert customer_list.has_customer("TechCorp")


@pytest.mark.mobile
@pytest.mark.regression
def test_mob_11_search_non_existent_customer_shows_empty(mobile_driver):
    """TC-MOB-11: Empty State - Non-existent search displays empty state."""
    customer_list = CustomerListScreen(mobile_driver)

    customer_list.search_customer("NO_EXIST_XYZ_9999999")
    assert customer_list.is_empty_state_displayed()


@pytest.mark.mobile
@pytest.mark.regression
def test_mob_12_pull_to_refresh_gesture(mobile_driver):
    """TC-MOB-12: Gesture - Pull-to-refresh swipe executes safely without crash."""
    customer_list = CustomerListScreen(mobile_driver)

    customer_list.refresh_list()
    assert customer_list.is_screen_visible()
