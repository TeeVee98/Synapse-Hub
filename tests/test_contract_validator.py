#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

import unittest
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "tools"))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import contract_validator


class TestContractValidator(unittest.TestCase):
    """Unit tests for SelectorContract validation."""

    def test_valid_contract(self):
        contract = {
            "url": "https://app.enterprise.com/login",
            "screen_name": "LoginPage",
            "elements": [
                {
                    "name": "usernameInput",
                    "role": "textbox",
                    "selector": "getByRole('textbox', name='Username')",
                    "latency_ms": 45
                },
                {
                    "name": "submitButton",
                    "role": "button",
                    "target": "getByRole('button', name='Sign In')",
                    "latency_ms": 60
                }
            ]
        }
        valid, errors = contract_validator.validate_contract_dict(contract)
        self.assertTrue(valid, f"Contract should be valid: {errors}")
        self.assertEqual(len(errors), 0)

    def test_missing_fields(self):
        invalid_contract = {
            "screen_name": "IncompletePage"
        }
        valid, errors = contract_validator.validate_contract_dict(invalid_contract)
        self.assertFalse(valid)
        self.assertTrue(any("url" in e for e in errors))
        self.assertTrue(any("elements" in e for e in errors))

    def test_latency_budget_exceeded(self):
        slow_contract = {
            "url": "https://app.enterprise.com/orders",
            "screen_name": "OrdersPage",
            "elements": [
                {
                    "name": "slowRow",
                    "role": "row",
                    "selector": "div.slow-table",
                    "latency_ms": 450
                }
            ]
        }
        valid, errors = contract_validator.validate_contract_dict(slow_contract)
        self.assertFalse(valid)
        self.assertTrue(any("latency" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
