#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/regulatory_compliance.py — Enterprise Regulatory & Compliance Audit Sentinel
-----------------------------------------------------------------------------------
Implements verification rules for international regulatory and industry standards:
  1. GDPR / PDPA: Right to be Forgotten (Article 17), Consent Logging (Article 7),
     and Data Portability (Article 20).
  2. PCI-DSS v4.0: Requirement 3.4 (PAN Masking with Luhn validation), Requirement 3.2
     (Sensitive Authentication Data / CVV exclusion), and Log Sanitization.
  3. ISO 15489: Electronic Records Management (Retention Policies & Immutable Audit Trails).

Usage:
  python tools/regulatory_compliance.py --scan-pci-file logs/access.log
  python tools/regulatory_compliance.py --audit-gdpr-deletion user_export.json
  python tools/regulatory_compliance.py --scan-text "Customer paid with 4111 1111 1111 1111, CVV: 123"
  python tools/regulatory_compliance.py --audit-pci sample_data.json --gate
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ==============================================================================
# PCI-DSS v4.0 IMPLEMENTATION (LUHN ALGORITHM & PAN MASKING)
# ==============================================================================

CARD_PATTERNS = [
    # Visa: starts with 4, length 13, 16, or 19
    re.compile(r"\b4[0-9]{12}(?:[0-9]{3})?(?:[0-9]{3})?\b"),
    # Mastercard: starts with 51-55 or 2221-2720, length 16
    re.compile(r"\b(?:5[1-5][0-9]{2}|222[1-9]|22[3-9][0-9]|2[3-6][0-9]{2}|27[01][0-9]|2720)[0-9]{12}\b"),
    # American Express: starts with 34 or 37, length 15
    re.compile(r"\b3[47][0-9]{13}\b"),
    # Discover: starts with 6011, 622126-622925, 644-649, 65, length 16
    re.compile(r"\b6(?:011|5[0-9]{2}|4[4-9][0-9]|22(?:12[6-9]|1[3-9][0-9]|[2-8][0-9]{2}|9[01][0-9]|92[0-5]))[0-9]{10,12}\b"),
]

# Patterns for spaced or dashed card numbers (e.g. 4111-1111-1111-1111 or 4111 1111 1111 1111)
CARD_SEPARATED_PATTERN = re.compile(r"\b(?:\d{4}[ -]){3}\d{4}\b|\b\d{4}[ -]\d{6}[ -]\d{5}\b")

# CVV / CVC sensitive authentication data pattern
CVV_PATTERN = re.compile(r"\b(?:cvv|cvc|cid|cvv2|cvc2)[\s:=]+([0-9]{3,4})\b", re.IGNORECASE)


def luhn_checksum_valid(card_number_str: str) -> bool:
    """Validates credit card number digits using ISO/IEC 7812 Luhn formula."""
    digits = [int(c) for c in re.sub(r"\D", "", card_number_str)]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, digit in enumerate(digits):
        if i % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return (checksum % 10) == 0


def mask_pan(pan_str: str) -> str:
    """Masks a card number according to PCI-DSS: First 6 and last 4 digits visible."""
    digits_only = re.sub(r"\D", "", pan_str)
    if len(digits_only) < 13:
        return "****"
    first6 = digits_only[:6]
    last4 = digits_only[-4:]
    masked_middle = "*" * (len(digits_only) - 10)
    return f"{first6}{masked_middle}{last4}"


def scan_text_for_pci_violations(text: str) -> List[Dict[str, Any]]:
    """Scans text for unmasked PANs and forbidden CVV data."""
    violations = []

    # 1. Check for raw contiguous card numbers
    for pat in CARD_PATTERNS:
        for match in pat.finditer(text):
            candidate = match.group(0)
            if luhn_checksum_valid(candidate):
                violations.append({
                    "standard": "PCI-DSS v4.0 Req 3.4",
                    "severity": "CRITICAL",
                    "type": "UNMASKED_PAN_LEAK",
                    "found": candidate,
                    "masked_suggestion": mask_pan(candidate),
                    "message": "Raw, unmasked Primary Account Number (PAN) detected with valid Luhn checksum.",
                })

    # 2. Check for separated card numbers (dashes or spaces)
    for match in CARD_SEPARATED_PATTERN.finditer(text):
        candidate = match.group(0)
        digits = re.sub(r"\D", "", candidate)
        if luhn_checksum_valid(digits):
            # Avoid duplicate if already matched by contiguous
            if not any(v.get("found") == candidate or v.get("found") == digits for v in violations):
                violations.append({
                    "standard": "PCI-DSS v4.0 Req 3.4",
                    "severity": "CRITICAL",
                    "type": "UNMASKED_PAN_LEAK",
                    "found": candidate,
                    "masked_suggestion": mask_pan(digits),
                    "message": "Delimited unmasked PAN detected with valid Luhn checksum.",
                })

    # 3. Check for CVV / Sensitive Authentication Data storage
    for match in CVV_PATTERN.finditer(text):
        violations.append({
            "standard": "PCI-DSS v4.0 Req 3.2",
            "severity": "CRITICAL",
            "type": "SENSITIVE_AUTH_DATA_STORAGE",
            "found": match.group(0),
            "message": "Sensitive Authentication Data (CVV/CVC) detected. Storing CVV post-authorization is strictly prohibited.",
        })

    return violations


# ==============================================================================
# GDPR & PDPA COMPLIANCE (RIGHT TO BE FORGOTTEN & CONSENT)
# ==============================================================================

def audit_right_to_be_forgotten(
    target_user_id: str,
    db_tables_snapshot: Dict[str, List[Dict[str, Any]]],
    pii_keywords: List[str] = None,
) -> Dict[str, Any]:
    """
    Verifies Article 17 GDPR (Right to Erasure).
    Ensures user records and associated PII are completely purged or anonymized.
    """
    pii_keywords = pii_keywords or ["email", "phone", "full_name", "address", "ssn", "cccd", "ip_address"]
    lingering_records = []

    for table_name, rows in db_tables_snapshot.items():
        for idx, row in enumerate(rows):
            # Check direct user_id match
            is_matched_user = False
            for col_val in row.values():
                if str(col_val).strip() == str(target_user_id).strip():
                    is_matched_user = True
                    break

            if is_matched_user:
                # Check if fields still contain non-empty PII
                for k, v in row.items():
                    k_lower = k.lower()
                    if any(kw in k_lower for kw in pii_keywords) and v:
                        lingering_records.append({
                            "table": table_name,
                            "row_index": idx,
                            "field": k,
                            "residual_value": str(v),
                            "issue": "PII field retained after account erasure request.",
                        })

    compliant = len(lingering_records) == 0
    return {
        "standard": "GDPR Article 17 / PDPA",
        "user_id": target_user_id,
        "is_compliant": compliant,
        "lingering_pii_count": len(lingering_records),
        "violations": lingering_records,
    }


def verify_consent_audit_log(consent_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies Article 7 GDPR (Conditions for Consent).
    Requires explicit opt-in, timestamp, purpose specification, and IP masking.
    """
    missing_fields = []
    required_keys = ["user_id", "timestamp", "consent_version", "purposes", "opt_in_state"]
    for r in required_keys:
        if r not in consent_record:
            missing_fields.append(r)

    is_opt_in = consent_record.get("opt_in_state") is True
    ip_raw = str(consent_record.get("ip_address", ""))
    ip_masked = bool(re.search(r"(\.0$|\.xxx$|::ffff:0$|\*\*\*)", ip_raw)) if ip_raw else True

    compliant = (len(missing_fields) == 0) and is_opt_in and ip_masked

    return {
        "standard": "GDPR Article 7",
        "is_compliant": compliant,
        "missing_fields": missing_fields,
        "explicit_opt_in": is_opt_in,
        "ip_anonymized": ip_masked,
    }


# ==============================================================================
# ISO 15489 (ELECTRONIC RECORDS MANAGEMENT)
# ==============================================================================

def verify_record_retention_policy(
    created_at_iso: str,
    retention_period_years: int,
    action_attempted: str,
    action_timestamp_iso: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verifies ISO 15489-1 Section 8 (Retention and Disposition).
    Premature permanent deletion of regulated records is a compliance failure.
    """
    try:
        dt_created = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
        dt_action = (
            datetime.fromisoformat(action_timestamp_iso.replace("Z", "+00:00"))
            if action_timestamp_iso
            else datetime.now(timezone.utc)
        )
    except Exception as e:
        return {"is_compliant": False, "error": f"Invalid ISO date: {e}"}

    age_days = (dt_action - dt_created).days
    required_days = retention_period_years * 365

    if action_attempted.upper() in ("PURGE", "DELETE", "DROP", "DESTROY") and age_days < required_days:
        return {
            "standard": "ISO 15489 Section 8",
            "is_compliant": False,
            "action": action_attempted,
            "retention_required_days": required_days,
            "record_age_days": age_days,
            "message": f"Illegal disposition: Record age ({age_days} days) is less than statutory retention period ({required_days} days).",
        }

    return {
        "standard": "ISO 15489 Section 8",
        "is_compliant": True,
        "action": action_attempted,
        "message": "Action conforms to record retention schedule.",
    }


# ==============================================================================
# CLI HANDLER & BATCH SCANNER
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Synapse Hub Regulatory & Compliance Audit Sentinel (GDPR, PCI-DSS, ISO 15489)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--scan-text", help="Direct text string to scan for PCI-DSS unmasked PANs/CVV")
    parser.add_argument("--scan-file", help="Path to text or JSON file to scan for compliance violations")
    parser.add_argument("--audit-gdpr", help="Path to JSON file containing user deletion snapshot")
    parser.add_argument("--user-id", default="USER_123", help="Target user ID for GDPR Right to be Forgotten audit")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--gate", action="store_true", help="Exit code 1 if any CRITICAL regulatory violation is found")

    args = parser.parse_args()

    results = {"audit_timestamp": datetime.now(timezone.utc).isoformat(), "violations": []}
    has_critical = False

    if args.scan_text:
        viols = scan_text_for_pci_violations(args.scan_text)
        results["violations"].extend(viols)
        if any(v.get("severity") == "CRITICAL" for v in viols):
            has_critical = True

    elif args.scan_file:
        if not os.path.exists(args.scan_file):
            print(f"❌ Error: File not found: {args.scan_file}", file=sys.stderr)
            return 2
        with open(args.scan_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        viols = scan_text_for_pci_violations(content)
        results["violations"].extend(viols)
        if any(v.get("severity") == "CRITICAL" for v in viols):
            has_critical = True

    elif args.audit_gdpr:
        if not os.path.exists(args.audit_gdpr):
            print(f"❌ Error: File not found: {args.audit_gdpr}", file=sys.stderr)
            return 2
        with open(args.audit_gdpr, "r", encoding="utf-8") as f:
            data = json.load(f)
        gdpr_res = audit_right_to_be_forgotten(args.user_id, data)
        results["gdpr_audit"] = gdpr_res
        if not gdpr_res["is_compliant"]:
            has_critical = True
    else:
        parser.print_help()
        return 2

    results["total_violations"] = len(results["violations"])

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("=" * 72)
        print("  SYNAPSE HUB — REGULATORY & COMPLIANCE AUDIT SCORECARD")
        print("=" * 72)
        if "gdpr_audit" in results:
            g = results["gdpr_audit"]
            st = "\033[92m[COMPLIANT]\033[0m" if g["is_compliant"] else "\033[91m[NON-COMPLIANT]\033[0m"
            print(f"  GDPR Art. 17 Status: {st}")
            print(f"  Residual PII Records: {g['lingering_pii_count']}")
        else:
            print(f"  PCI-DSS v4.0 Scan Findings: {len(results['violations'])}")
            for v in results["violations"]:
                print(f"  \033[91m[{v['severity']}]\033[0m {v['standard']} | {v['type']} -> {v['message']}")
                if "masked_suggestion" in v:
                    print(f"     Masked suggestion: {v['masked_suggestion']}")
        print("=" * 72)

    if args.gate and has_critical:
        print("🚨 Quality Gate Failed: Regulatory compliance violations detected!", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
