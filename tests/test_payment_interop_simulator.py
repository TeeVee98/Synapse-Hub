#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-

"""
Unit tests for tools/payment_interop_simulator.py
Validates ISO 8583 parsing, HMAC-SHA256 signature security, and idempotency guarantees.
"""

import time
import unittest
from tools.payment_interop_simulator import ISO8583Message, PaymentInteropSentinel


class TestPaymentInteropSimulator(unittest.TestCase):
    def setUp(self):
        self.sentinel = PaymentInteropSentinel()

    def test_iso8583_pack_and_unpack(self):
        """Verifies bitmapped ISO 8583 pack and unpack integrity."""
        msg = ISO8583Message(mti="0200")
        msg.set_field(3, "000000")
        msg.set_field(4, "150000")
        msg.set_field(11, "998877")
        msg.set_field(41, "TERM1234")

        wire = msg.pack()
        self.assertTrue(wire.startswith("0200"))

        unpacked = ISO8583Message.unpack(wire)
        self.assertEqual(unpacked.mti, "0200")
        self.assertEqual(unpacked.get_field(3), "000000")
        self.assertEqual(unpacked.get_field(4), "000000150000")
        self.assertEqual(unpacked.get_field(11), "998877")
        self.assertEqual(unpacked.get_field(41), "TERM1234")

    def test_webhook_signature_verification_success(self):
        """Verifies HMAC-SHA256 signature passes with valid secret and timestamp."""
        payload = '{"amount":10000,"currency":"VND"}'
        secret = "secret_key_abc_123"
        sig_header, ts = self.sentinel.generate_webhook_signature(payload, secret)

        valid, msg = self.sentinel.verify_webhook_signature(payload, secret, sig_header, tolerance_sec=300)
        self.assertTrue(valid)
        self.assertIn("successfully", msg)

    def test_webhook_signature_verification_tampered(self):
        """Verifies HMAC-SHA256 fails when payload is tampered with."""
        payload = '{"amount":10000,"currency":"VND"}'
        tampered_payload = '{"amount":999999,"currency":"VND"}'
        secret = "secret_key_abc_123"
        sig_header, ts = self.sentinel.generate_webhook_signature(payload, secret)

        valid, msg = self.sentinel.verify_webhook_signature(tampered_payload, secret, sig_header)
        self.assertFalse(valid)
        self.assertIn("mismatch", msg)

    def test_webhook_signature_verification_expired_replay(self):
        """Verifies signature fails when timestamp breaches tolerance window (anti-replay)."""
        payload = '{"amount":10000}'
        secret = "secret_key_abc_123"
        old_ts = int(time.time()) - 400  # 400s in the past
        sig_header, ts = self.sentinel.generate_webhook_signature(payload, secret, timestamp=old_ts)

        valid, msg = self.sentinel.verify_webhook_signature(payload, secret, sig_header, tolerance_sec=300)
        self.assertFalse(valid)
        self.assertIn("tolerance", msg)

    def test_idempotency_guard(self):
        """Verifies idempotency key returns identical transaction and cached flag."""
        key = "IDEMP-TEST-UNIQUE-01"
        res1 = self.sentinel.process_idempotent_transaction(key, "ORD-1", 500.0)
        self.assertFalse(res1["idempotent_cached"])
        self.assertEqual(res1["status"], "CREATED")

        res2 = self.sentinel.process_idempotent_transaction(key, "ORD-1", 500.0)
        self.assertTrue(res2["idempotent_cached"])
        self.assertEqual(res2["status"], "PROCESSED")
        self.assertEqual(res1["transaction_id"], res2["transaction_id"])

    def test_rest_to_iso8583_translation(self):
        """Verifies REST JSON payload bridges to ISO 8583 fields."""
        rest_req = {
            "amount": 250.0,
            "stan": "543210",
            "terminal_id": "POS_MOBILE",
            "merchant_id": "STORE_VN_01",
        }
        iso_msg = self.sentinel.translate_rest_to_iso8583(rest_req)
        self.assertEqual(iso_msg.mti, "0200")
        self.assertEqual(iso_msg.get_field(3), "000000")
        self.assertEqual(iso_msg.get_field(4), "25000")
        self.assertEqual(iso_msg.get_field(11), "543210")
        self.assertEqual(iso_msg.get_field(41), "POS_MOBILE")


if __name__ == "__main__":
    unittest.main()
