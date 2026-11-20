# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
examples/mobile-crm-suite/tests/test_mobile_auth.py
----------------------------------------------------
Mobile Appium Authentication Test Suite (Clean SOM Flat Architecture).
Orchestrates Screen Object Model methods only. Zero raw selectors in scripts.
"""

import os
import secrets
import pytest
from pages import LoginScreen, CustomerListScreen, BaseScreen


@pytest.mark.mobile
@pytest.mark.smoke
def test_mob_01_successful_login(mobile_driver):
    """TC-MOB-01: Happy Path - Successful login with valid admin credentials."""
    login_screen = LoginScreen(mobile_driver)
    customer_list = CustomerListScreen(mobile_driver)

    admin_user = os.environ.get("CRM_USER", "admin@example.com")
    admin_pass = os.environ.get("CRM_PASS") or secrets.token_urlsafe(16)
    login_screen.login(admin_user, admin_pass)
    # Verify successful authentication: customer list is visible and no login error displayed
    assert customer_list.is_screen_visible()
    assert not login_screen.is_error_displayed()


@pytest.mark.mobile
@pytest.mark.regression
def test_mob_02_empty_credentials_error(mobile_driver):
    """TC-MOB-02: Validation - Submit empty login form displays error."""
    login_screen = LoginScreen(mobile_driver)

    login_screen.login("", "")
    assert login_screen.is_error_displayed()


@pytest.mark.mobile
@pytest.mark.security
def test_mob_03_password_field_masked(mobile_driver):
    """TC-MOB-03: Security - Verify native password field attribute is masked."""
    login_screen = LoginScreen(mobile_driver)

    assert login_screen.is_password_masked()


@pytest.mark.mobile
@pytest.mark.regression
def test_mob_04_invalid_credentials_error(mobile_driver):
    """TC-MOB-04: Negative - Invalid credentials displays generic failure message."""
    login_screen = LoginScreen(mobile_driver)
    random_user = BaseScreen.unique_email("unauth_")
    invalid_pass = secrets.token_urlsafe(16)

    login_screen.login(random_user, invalid_pass)
    assert login_screen.is_error_displayed()
    assert "Invalid" in login_screen.get_error_message()


@pytest.mark.mobile
@pytest.mark.regression
def test_mob_05_login_with_remember_me(mobile_driver):
    """TC-MOB-05: State - Login with Remember Me toggle preserves state."""
    login_screen = LoginScreen(mobile_driver)
    admin_user = os.environ.get("CRM_USER", "admin@example.com")
    admin_pass = os.environ.get("CRM_PASS") or secrets.token_urlsafe(16)

    login_screen.login(admin_user, admin_pass, remember_me=True)
    assert not login_screen.is_error_displayed()
