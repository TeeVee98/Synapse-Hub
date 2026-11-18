#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-

"""
Unit tests for tools/mobile_resilience_sentinel.py
Validates hardware interrupt command generation, OWASP MASVS checks, and HIG/Material tap targets.
"""

import unittest
from tools.perf.mobile_resilience_sentinel import (
    MobileInterruptSimulator,
    OWASPMASVSAuditor,
    DesignGuidelinesAuditor,
)


class TestMobileResilienceSentinel(unittest.TestCase):
    def test_hardware_interrupt_commands(self):
        """Verifies ADB commands for call, SMS, battery, and network interruption."""
        call_cmds = MobileInterruptSimulator.get_interrupt_commands("incoming_call", phone="0988776655")
        self.assertEqual(call_cmds, ["adb emu gsm call 0988776655"])

        sms_cmds = MobileInterruptSimulator.get_interrupt_commands("sms", phone="0988776655", message="Hello")
        self.assertEqual(sms_cmds, ['adb emu sms send 0988776655 "Hello"'])

        bat_cmds = MobileInterruptSimulator.get_interrupt_commands("battery_low", battery_level=5)
        self.assertIn("adb shell dumpsys battery set level 5", bat_cmds)

        net_cmds = MobileInterruptSimulator.get_interrupt_commands("network_drop")
        self.assertEqual(len(net_cmds), 2)
        self.assertIn("adb shell svc wifi disable", net_cmds)

    def test_owasp_masvs_android_pass(self):
        """Verifies secure AndroidManifest configuration passes MASVS audit."""
        manifest = """
        <manifest>
            <application android:debuggable="false" android:allowBackup="false" android:usesCleartextTraffic="false" />
        </manifest>
        """
        res = OWASPMASVSAuditor.audit_android_manifest(manifest)
        self.assertEqual(res["status"], "PASSED")
        self.assertEqual(res["failed_count"], 0)

    def test_owasp_masvs_android_fail_debuggable(self):
        """Verifies insecure debuggable=true fails MASVS-RESILIENCE-1."""
        manifest = """
        <manifest>
            <application android:debuggable="true" android:allowBackup="false" />
        </manifest>
        """
        res = OWASPMASVSAuditor.audit_android_manifest(manifest)
        self.assertEqual(res["status"], "FAILED")
        self.assertGreater(res["failed_count"], 0)
        rules = [f["rule"] for f in res["findings"] if not f["pass"]]
        self.assertIn("MASVS-RESILIENCE-1", rules)

    def test_owasp_masvs_ios_arbitrary_loads(self):
        """Verifies NSAllowsArbitraryLoads=true fails MASVS-NETWORK-1."""
        insecure_plist = """
        <dict>
            <key>NSAppTransportSecurity</key>
            <dict>
                <key>NSAllowsArbitraryLoads</key>
                <true/>
            </dict>
        </dict>
        """
        res_fail = OWASPMASVSAuditor.audit_ios_plist(insecure_plist)
        self.assertEqual(res_fail["status"], "FAILED")

        secure_plist = """
        <dict>
            <key>NSAppTransportSecurity</key>
            <dict>
                <key>NSAllowsArbitraryLoads</key>
                <false/>
            </dict>
        </dict>
        """
        res_pass = OWASPMASVSAuditor.audit_ios_plist(secure_plist)
        self.assertEqual(res_pass["status"], "PASSED")

    def test_tap_target_sizes(self):
        """Verifies Apple HIG (44x44pt) and Material Design (48x48dp) minimum boundaries."""
        # Apple HIG: 44x44 pt minimum
        ios_pass = DesignGuidelinesAuditor.evaluate_tap_target(44.0, 48.0, platform="ios")
        self.assertTrue(ios_pass["passed"])

        ios_fail = DesignGuidelinesAuditor.evaluate_tap_target(43.9, 44.0, platform="ios")
        self.assertFalse(ios_fail["passed"])

        # Material Design: 48x48 dp minimum
        android_pass = DesignGuidelinesAuditor.evaluate_tap_target(48.0, 52.0, platform="android")
        self.assertTrue(android_pass["passed"])

        android_fail = DesignGuidelinesAuditor.evaluate_tap_target(47.9, 50.0, platform="android")
        self.assertFalse(android_fail["passed"])


if __name__ == "__main__":
    unittest.main()
