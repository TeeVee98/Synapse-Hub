#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Unit Tests for On-Demand Field Validation Checklist & Invariants Query Engine
------------------------------------------------------------------------------
Validates:
  1. Full catalog of 25 input fields and 7 resilience invariants
  2. Single & multi-field extraction with boundary data
  3. Case-insensitivity and robust alias resolution
  4. Invariant querying (individual, 'all', 'none')
  5. JSON & Markdown output formatting
  6. Graceful failure on invalid field/invariant names
  7. CLI subprocess execution and return codes
"""

import os
import sys
import json
import subprocess
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from tools.manual.checklist_query import (
    CANONICAL_FIELDS,
    CANONICAL_INVARIANTS,
    resolve_field_key,
    resolve_invariant_key,
    query_checklist,
    render_markdown,
    list_catalog
)


class TestChecklistQuery(unittest.TestCase):

    def test_canonical_catalog_counts(self):
        """Verifies exactly 25 field codes and 8 invariant codes are registered."""
        self.assertEqual(len(CANONICAL_FIELDS), 25, "Must declare exactly 25 canonical fields")
        self.assertEqual(len(CANONICAL_INVARIANTS), 8, "Must declare exactly 8 canonical invariants")

        expected_fields = [
            "text", "email", "phone", "password", "number", "date", "date-range",
            "dropdown", "multi-select", "checkbox-radio", "textarea", "file-upload",
            "otp", "slider", "richtext", "geo", "signature", "biometric",
            "camera-qr", "currency", "card-iban", "autocomplete", "cron",
            "json-code", "data-grid"
        ]
        for ef in expected_fields:
            self.assertIn(ef, CANONICAL_FIELDS, f"Field '{ef}' missing from catalog")

        expected_invariants = [
            "unicode-ime", "utf8mb4-emoji", "clipboard-invisible",
            "multi-tab-locking", "rbac-idor", "async-webhook", "mobile-viewport",
            "payment-ui-latency"
        ]
        for ei in expected_invariants:
            self.assertIn(ei, CANONICAL_INVARIANTS, f"Invariant '{ei}' missing from catalog")

    def test_list_catalog_contains_all_items(self):
        """Verifies text listing outputs all 25 field codes and 8 invariant codes."""
        listing = list_catalog()
        for f_code in CANONICAL_FIELDS:
            self.assertIn(f"`{f_code}`", listing)
        for inv_code in CANONICAL_INVARIANTS:
            self.assertIn(f"`{inv_code}`", listing)

    def test_alias_resolution(self):
        """Verifies case-insensitive alias mapping for fields and invariants."""
        self.assertEqual(resolve_field_key("EMAIL"), "email")
        self.assertEqual(resolve_field_key("mail"), "email")
        self.assertEqual(resolve_field_key("PWD"), "password")
        self.assertEqual(resolve_field_key("2fa"), "otp")
        self.assertEqual(resolve_field_key("wysiwyg"), "richtext")
        self.assertEqual(resolve_field_key("credit-card"), "card-iban")
        self.assertEqual(resolve_field_key("unknown_field_xyz"), None)

        self.assertEqual(resolve_invariant_key("UNICODE-IME"), "unicode-ime")
        self.assertEqual(resolve_invariant_key("telex"), "unicode-ime")
        self.assertEqual(resolve_invariant_key("emoji"), "utf8mb4-emoji")
        self.assertEqual(resolve_invariant_key("idor"), "rbac-idor")
        self.assertEqual(resolve_invariant_key("unknown_inv_abc"), None)

    def test_query_fields_and_invariants(self):
        """Verifies querying specific fields and invariants extracts non-empty data."""
        res = query_checklist(
            fields=["email", "otp", "currency"],
            invariants=["unicode-ime", "rbac-idor"]
        )
        self.assertEqual(len(res["fields"]), 3)
        self.assertEqual(len(res["invariants"]), 2)
        self.assertEqual(res["invalid_fields"], [])
        self.assertEqual(res["invalid_invariants"], [])

        codes = [f["code"] for f in res["fields"]]
        self.assertEqual(codes, ["email", "otp", "currency"])
        for f in res["fields"]:
            self.assertTrue(len(f["positive"]) > 0)
            self.assertTrue(len(f["boundary_negative"]) > 0)
            self.assertTrue(len(f["security_edge_cases"]) > 0)

        inv_codes = [i["code"] for i in res["invariants"]]
        self.assertEqual(inv_codes, ["unicode-ime", "rbac-idor"])
        for i in res["invariants"]:
            self.assertTrue(len(i["title"]) > 0)
            self.assertTrue(len(i["content"]) > 0)

    def test_query_invariants_all_and_none(self):
        """Verifies 'all' returns all 8 invariants, and 'none' returns empty."""
        res_all = query_checklist(fields=["email"], invariants=["all"])
        self.assertEqual(len(res_all["invariants"]), 8)

        res_none = query_checklist(fields=["email"], invariants=["none"])
        self.assertEqual(len(res_none["invariants"]), 0)

    def test_render_markdown(self):
        """Verifies markdown rendering produces proper table headers and section tags."""
        res = query_checklist(fields=["email", "password"], invariants=["unicode-ime"])
        md = render_markdown(res)
        self.assertIn("### Field Validation Matrix (Filtered)", md)
        self.assertIn("| `email` |", md)
        self.assertIn("| `password` |", md)
        self.assertIn("#### `unicode-ime`:", md)

    def test_invalid_query_reporting(self):
        """Verifies unknown field/invariant inputs are captured in invalid lists."""
        res = query_checklist(fields=["email", "invalid_field_123"], invariants=["fake_inv_999"])
        self.assertIn("invalid_field_123", res["invalid_fields"])
        self.assertIn("fake_inv_999", res["invalid_invariants"])
        self.assertEqual(len(res["fields"]), 1)

    def test_cli_execution_success(self):
        """Verifies CLI execution with exit code 0."""
        cmd = [sys.executable, os.path.join(REPO_ROOT, "tools", "manual", "checklist_query.py"), "--fields", "email,otp", "--format", "json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertEqual(len(data["fields"]), 2)
        self.assertEqual(data["fields"][0]["code"], "email")
        self.assertEqual(data["fields"][1]["code"], "otp")

    def test_cli_execution_invalid_field_exit_code_1(self):
        """Verifies CLI execution with invalid field produces exit code 1."""
        cmd = [sys.executable, os.path.join(REPO_ROOT, "tools", "manual", "checklist_query.py"), "--fields", "nonexistent_field"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Unknown field", proc.stderr)

    def test_query_payment_ui_latency_invariant(self):
        """Verifies query of payment-ui-latency invariant extracts double-click and interrupt contents."""
        self.assertEqual(resolve_invariant_key("payment-ui-latency"), "payment-ui-latency")
        self.assertEqual(resolve_invariant_key("payment"), "payment-ui-latency")
        self.assertEqual(resolve_invariant_key("slow-3g"), "payment-ui-latency")
        self.assertEqual(resolve_invariant_key("double-click"), "payment-ui-latency")

        res = query_checklist(invariants=["payment-ui-latency"])
        self.assertEqual(len(res["invariants"]), 1)
        inv = res["invariants"][0]
        self.assertEqual(inv["code"], "payment-ui-latency")
        self.assertIn("Double-Click", inv["content"])
        self.assertIn("Idempotency-Key", inv["content"])
        self.assertIn("Browser Interrupt", inv["content"])


if __name__ == "__main__":
    unittest.main()
