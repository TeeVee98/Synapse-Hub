# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
examples/mobile-crm-suite/tests/test_mobile_resilience.py
----------------------------------------------------------
Mobile Appium Resilience & Hardware Interruption Suite.
Validates session persistence across backgrounding, keyboard safety,
and integration with tools/perf/mobile_resilience_sentinel.py.
"""

import pytest
from pages import CustomerListScreen, CustomerFormScreen
from tools.perf.mobile_resilience_sentinel import MobileInterruptSimulator


@pytest.mark.mobile
@pytest.mark.resilience
def test_mob_13_background_session_persistence(mobile_driver):
    """TC-MOB-13: Resilience - App backgrounding for 5 seconds preserves session state."""
    customer_list = CustomerListScreen(mobile_driver)

    customer_list.background_app_safe(seconds=5)
    assert customer_list.is_screen_visible()


@pytest.mark.mobile
@pytest.mark.resilience
def test_mob_14_keyboard_dismissal_safety(mobile_driver):
    """TC-MOB-14: Resilience - Virtual keyboard dismissal avoids tap interception."""
    customer_list = CustomerListScreen(mobile_driver)

    # Calling hide_keyboard_safe should never raise exception even if keyboard is closed
    customer_list.hide_keyboard_safe()
    assert customer_list.is_screen_visible()


@pytest.mark.mobile
@pytest.mark.regression
def test_mob_15_cancel_form_dismisses_without_save(mobile_driver):
    """TC-MOB-15: Workflow - Cancel button dismisses form without persisting record."""
    customer_list = CustomerListScreen(mobile_driver)
    form_screen = CustomerFormScreen(mobile_driver)

    customer_list.open_new_customer()
    form_screen.cancel()
    assert customer_list.is_screen_visible()


@pytest.mark.mobile
@pytest.mark.resilience
def test_mob_16_hardware_interrupt_incoming_call():
    """TC-MOB-16: Interruption - Simulate incoming phone call ADB command generation."""
    cmds = MobileInterruptSimulator.get_interrupt_commands("incoming_call", phone="0987654321")
    assert len(cmds) > 0
    assert any("gsm call 0987654321" in c for c in cmds)


@pytest.mark.mobile
@pytest.mark.resilience
def test_mob_17_hardware_interrupt_sms_otp():
    """TC-MOB-17: Interruption - Simulate incoming SMS OTP broadcast."""
    cmds = MobileInterruptSimulator.get_interrupt_commands("sms", phone="0987654321")
    assert len(cmds) > 0
    assert any("sms send" in c for c in cmds)


@pytest.mark.mobile
@pytest.mark.resilience
def test_mob_18_hardware_interrupt_low_battery():
    """TC-MOB-18: Interruption - Simulate low battery hardware warning."""
    cmds = MobileInterruptSimulator.get_interrupt_commands("battery_low")
    assert len(cmds) > 0
    assert any("battery set level" in c for c in cmds)
