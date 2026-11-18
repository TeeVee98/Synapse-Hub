#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

from tools.security.regulatory_compliance import (
    luhn_checksum_valid,
    mask_pan,
    scan_text_for_pci_violations,
    audit_right_to_be_forgotten,
    verify_consent_audit_log,
    verify_record_retention_policy,
)


def test_luhn_checksum_validation():
    # Valid Visa card number
    assert luhn_checksum_valid("4111111111111111") is True
    # Invalid card number (fails Luhn)
    assert luhn_checksum_valid("4111111111111112") is False
    # Short string
    assert luhn_checksum_valid("12345") is False


def test_pan_masking():
    masked = mask_pan("4111111111111111")
    assert masked == "411111******1111"
    assert len(masked) == 16


def test_scan_text_pci_violations():
    text_with_card = "Customer account billed with 4111-1111-1111-1111, cvv: 789 on file."
    viols = scan_text_for_pci_violations(text_with_card)
    assert len(viols) == 2
    types = [v["type"] for v in viols]
    assert "UNMASKED_PAN_LEAK" in types
    assert "SENSITIVE_AUTH_DATA_STORAGE" in types


def test_clean_text_no_pci_violations():
    clean_text = "Customer account billed with 411111******1111. Security code verified via token."
    viols = scan_text_for_pci_violations(clean_text)
    assert len(viols) == 0


def test_gdpr_right_to_be_forgotten():
    # Residual user data found
    db_snapshot = {
        "users": [{"id": "U123", "email": "test@example.com", "name": "John Doe"}],
        "orders": [{"id": "ORD_1", "customer_id": "U123", "total": 50}],
    }
    res = audit_right_to_be_forgotten("U123", db_snapshot)
    assert res["is_compliant"] is False
    assert res["lingering_pii_count"] >= 1

    # Completely purged / anonymized data
    db_snapshot_clean = {
        "users": [],
        "orders": [{"id": "ORD_1", "customer_id": "ANONYMOUS", "total": 50}],
    }
    res_clean = audit_right_to_be_forgotten("U123", db_snapshot_clean)
    assert res_clean["is_compliant"] is True
    assert res_clean["lingering_pii_count"] == 0


def test_gdpr_consent_audit_log():
    valid_consent = {
        "user_id": "U123",
        "timestamp": "2026-11-17T09:00:00Z",
        "consent_version": "v2.0",
        "purposes": ["essential", "analytics"],
        "opt_in_state": True,
        "ip_address": "192.168.1.0",  # Masked subnet
    }
    res = verify_consent_audit_log(valid_consent)
    assert res["is_compliant"] is True


def test_iso_15489_retention_policy():
    # Attempting to delete a 1-year old financial record that requires 5-year retention
    res_premature = verify_record_retention_policy(
        created_at_iso="2025-11-17T00:00:00Z",
        retention_period_years=5,
        action_attempted="DELETE",
        action_timestamp_iso="2026-11-17T00:00:00Z",
    )
    assert res_premature["is_compliant"] is False
    assert "Illegal disposition" in res_premature["message"]

    # Legitimate purge after retention period expired (e.g. created 7 years ago)
    res_expired = verify_record_retention_policy(
        created_at_iso="2018-01-01T00:00:00Z",
        retention_period_years=5,
        action_attempted="DELETE",
        action_timestamp_iso="2026-11-17T00:00:00Z",
    )
    assert res_expired["is_compliant"] is True
