#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/manual/checklist_query.py — 0-Token On-Demand Field Validation & Invariant Query Engine
---------------------------------------------------------------------------------------------
Queries and extracts targeted field-level validation rules and resilience protocols directly
from test-design/manual-rbt/rbt-manual-testing/references/field_validation_checklist.md.
Eliminates context rot by serving exact micro-slices instead of loading the entire 24 KB file.

Usage:
  python tools/manual/checklist_query.py --list
  python tools/manual/checklist_query.py --fields email,password,otp
  python tools/manual/checklist_query.py --fields email,currency --invariants unicode-ime,rbac-idor
  python tools/manual/checklist_query.py --fields email --invariants all --format json
"""

import os
import sys
import re
import json
import argparse
from typing import Dict, Any, List, Optional

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_CHECKLIST_PATH = os.path.join(
    REPO_ROOT,
    "skills",
    "02-test-design",
    "rbt-manual-testing",
    "references",
    "field_validation_checklist.md"
)

# 25 Canonical Field Types with aliases
CANONICAL_FIELDS: Dict[str, Dict[str, Any]] = {
    "text": {
        "index": 1,
        "name": "Text (Name, Title)",
        "aliases": ["text", "name", "title", "string", "text_input", "input_text"]
    },
    "email": {
        "index": 2,
        "name": "Email",
        "aliases": ["email", "mail", "email_address", "e-mail"]
    },
    "phone": {
        "index": 3,
        "name": "Phone",
        "aliases": ["phone", "tel", "telephone", "mobile", "cell", "phone_number"]
    },
    "password": {
        "index": 4,
        "name": "Password",
        "aliases": ["password", "pwd", "pass", "secret"]
    },
    "number": {
        "index": 5,
        "name": "Number (Quantity, Price)",
        "aliases": ["number", "quantity", "price", "amount", "int", "float", "integer", "numeric"]
    },
    "date": {
        "index": 6,
        "name": "Date / Datetime",
        "aliases": ["date", "datetime", "date_time", "time", "timestamp"]
    },
    "date-range": {
        "index": 7,
        "name": "Date Range",
        "aliases": ["date-range", "daterange", "date_range", "range_date"]
    },
    "dropdown": {
        "index": 8,
        "name": "Dropdown / Select",
        "aliases": ["dropdown", "select", "combo", "combobox", "single-select", "dropdown_select"]
    },
    "multi-select": {
        "index": 9,
        "name": "Multi-Select",
        "aliases": ["multi-select", "multiselect", "multi_select", "tags_input", "chip_input"]
    },
    "checkbox-radio": {
        "index": 10,
        "name": "Checkbox / Radio",
        "aliases": ["checkbox-radio", "checkbox", "radio", "checkboxes", "radios", "toggle", "boolean"]
    },
    "textarea": {
        "index": 11,
        "name": "Textarea (Notes, Bio)",
        "aliases": ["textarea", "notes", "bio", "description", "comment", "long_text", "multiline"]
    },
    "file-upload": {
        "index": 12,
        "name": "File Upload",
        "aliases": ["file-upload", "fileupload", "file_upload", "file", "upload", "attachment", "document"]
    },
    "otp": {
        "index": 13,
        "name": "OTP / MFA Code",
        "aliases": ["otp", "mfa", "2fa", "verification-code", "verification_code", "totp", "pin"]
    },
    "slider": {
        "index": 14,
        "name": "Range Slider",
        "aliases": ["slider", "range-slider", "range_slider", "range"]
    },
    "richtext": {
        "index": 15,
        "name": "Rich Text Editor (Basic WYSIWYG & Advanced WYSIWYG & Table Editor)",
        "aliases": ["richtext", "rich-text", "wysiwyg", "editor", "rich_text"]
    },
    "geo": {
        "index": 16,
        "name": "Geo Location & Address Autocomplete",
        "aliases": ["geo", "address", "location", "map", "coordinates", "gps", "geolocation"]
    },
    "signature": {
        "index": 17,
        "name": "Digital Signature Pad (Canvas)",
        "aliases": ["signature", "canvas", "sign", "digital_signature"]
    },
    "biometric": {
        "index": 18,
        "name": "Biometric / WebAuthn (Biometric Authentication Token)",
        "aliases": ["biometric", "webauthn", "passkey", "touchid", "faceid", "fido2", "biometrics"]
    },
    "camera-qr": {
        "index": 19,
        "name": "Camera / Barcode / QR Scanner (Camera / Barcode / QR Code Scanner)",
        "aliases": ["camera-qr", "camera_qr", "qr", "barcode", "scanner", "camera", "qr_code"]
    },
    "currency": {
        "index": 20,
        "name": "Currency & FX (Multi-Currency & Dynamic FX) (Multi-Currency & Exchange Rate Formatter)",
        "aliases": ["currency", "fx", "exchange-rate", "exchange_rate", "money", "foreign_exchange"]
    },
    "card-iban": {
        "index": 21,
        "name": "Credit Card / IBAN / Masked Input",
        "aliases": ["card-iban", "card_iban", "card", "credit-card", "credit_card", "iban", "pan", "payment_card"]
    },
    "autocomplete": {
        "index": 22,
        "name": "Async Autocomplete / Typeahead",
        "aliases": ["autocomplete", "typeahead", "async-search", "suggest", "search_autocomplete"]
    },
    "cron": {
        "index": 23,
        "name": "Cron Expression & Recurring Schedule",
        "aliases": ["cron", "schedule", "recurring", "crontab", "recurrence"]
    },
    "json-code": {
        "index": 24,
        "name": "JSON / Code / Formula Editor",
        "aliases": ["json-code", "json_code", "json", "code", "formula", "formula-editor"]
    },
    "data-grid": {
        "index": 25,
        "name": "Inline Editable Data Grid",
        "aliases": ["data-grid", "datagrid", "data_grid", "grid", "spreadsheet", "table-edit"]
    }
}

# 7 Canonical Resilience Invariant Codes with aliases
CANONICAL_INVARIANTS: Dict[str, Dict[str, Any]] = {
    "unicode-ime": {
        "index": 1,
        "title": "Unicode Normalization & IME Vietnamese Composing Protocol",
        "aliases": ["unicode-ime", "unicode_ime", "unicode", "ime", "nfc", "nfd", "vietnamese", "telex"]
    },
    "utf8mb4-emoji": {
        "index": 2,
        "title": "4-Byte Surrogate Pairs UTF-8 & Emoji Safety",
        "aliases": ["utf8mb4-emoji", "utf8mb4_emoji", "emoji", "utf8mb4", "surrogate", "emojis"]
    },
    "clipboard-invisible": {
        "index": 3,
        "title": "Clipboard Paste Special & Invisible Control Characters",
        "aliases": ["clipboard-invisible", "clipboard_invisible", "clipboard", "invisible", "control-chars", "paste", "bom"]
    },
    "multi-tab-locking": {
        "index": 4,
        "title": "Multi-Tab State Drift & Stepper Navigation",
        "aliases": ["multi-tab-locking", "multi_tab_locking", "multi-tab", "multitab", "stepper", "concurrent", "optimistic-locking"]
    },
    "rbac-idor": {
        "index": 5,
        "title": "Permission / RBAC Resilience",
        "aliases": ["rbac-idor", "rbac_idor", "rbac", "idor", "permission", "privilege", "role", "authorization"]
    },
    "async-webhook": {
        "index": 6,
        "title": "Integration, Asynchronous & Queue Backpressure",
        "aliases": ["async-webhook", "async_webhook", "async", "webhook", "queue", "backpressure", "ipn"]
    },
    "mobile-viewport": {
        "index": 7,
        "title": "Device & Viewport Distortion (Mobile Virtual Keyboard)",
        "aliases": ["mobile-viewport", "mobile_viewport", "mobile", "viewport", "dvh", "keyboard", "cls"]
    },
    "payment-ui-latency": {
        "index": 8,
        "title": "UI Latency, Payment Redirect & Browser Interrupt Resilience",
        "aliases": [
            "payment-ui-latency", "payment_ui_latency", "payment-latency", "payment",
            "ui-latency", "latency", "redirect-interrupt", "interrupt", "slow-3g", "double-click"
        ]
    }
}


def resolve_field_key(query: str) -> Optional[str]:
    """Resolves a field key or alias case-insensitively to its canonical key."""
    q = query.strip().lower()
    if q in CANONICAL_FIELDS:
        return q
    for key, data in CANONICAL_FIELDS.items():
        if q in data["aliases"] or q == key:
            return key
    return None


def resolve_invariant_key(query: str) -> Optional[str]:
    """Resolves an invariant key or alias case-insensitively to its canonical key."""
    q = query.strip().lower()
    if q in CANONICAL_INVARIANTS:
        return q
    for key, data in CANONICAL_INVARIANTS.items():
        if q in data["aliases"] or q == key:
            return key
    return None


def load_raw_checklist(checklist_path: Optional[str] = None) -> str:
    """Reads the field validation checklist file from disk."""
    path = checklist_path or DEFAULT_CHECKLIST_PATH
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Field validation checklist file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def parse_checklist_matrix(content: str) -> Dict[int, Dict[str, Any]]:
    """Parses Section 1 of the checklist into index-keyed dictionary of field data."""
    matrix: Dict[int, Dict[str, Any]] = {}
    lines = content.splitlines()
    in_section_1 = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## 1."):
            in_section_1 = True
            continue
        if stripped.startswith("## 2."):
            break
        if not in_section_1:
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            parts = [p.strip() for p in stripped.split("|")[1:-1]]
            if len(parts) >= 5:
                # Check if first col is number
                idx_str = re.sub(r"[^\d]", "", parts[0])
                if idx_str.isdigit():
                    idx = int(idx_str)
                    matrix[idx] = {
                        "index": idx,
                        "raw_type": parts[1].replace("**", "").strip(),
                        "positive": parts[2],
                        "boundary_negative": parts[3],
                        "security_edge_cases": parts[4]
                    }
    return matrix


def parse_invariants_sections(content: str) -> Dict[int, Dict[str, Any]]:
    """Parses Section 2 subsections into index-keyed dictionary of invariant content."""
    invariants: Dict[int, Dict[str, Any]] = {}
    lines = content.splitlines()
    in_section_2 = False
    current_idx: Optional[int] = None
    current_title = ""
    current_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## 2."):
            in_section_2 = True
            continue
        if in_section_2 and stripped.startswith("## 3."):
            break
        if not in_section_2:
            continue

        m_sub = re.match(r"^###\s+(\d+)\.\s+(.*)$", stripped)
        if m_sub:
            if current_idx is not None:
                invariants[current_idx] = {
                    "index": current_idx,
                    "title": current_title,
                    "content": "\n".join(current_lines).strip()
                }
            current_idx = int(m_sub.group(1))
            current_title = m_sub.group(2).strip()
            current_lines = []
        elif current_idx is not None:
            current_lines.append(line)

    if current_idx is not None:
        invariants[current_idx] = {
            "index": current_idx,
            "title": current_title,
            "content": "\n".join(current_lines).strip()
        }

    return invariants


def _find_raw_invariant(raw_invariants: Dict[int, Dict[str, Any]], inv_meta: Dict[str, Any]) -> Dict[str, Any]:
    idx = inv_meta["index"]
    if idx in raw_invariants:
        return raw_invariants[idx]
    for raw in raw_invariants.values():
        t = raw.get("title", "").lower()
        if inv_meta["title"].lower() in t or any(a in t for a in inv_meta.get("aliases", [])):
            return raw
    return {}


def query_checklist(
    fields: Optional[List[str]] = None,
    invariants: Optional[List[str]] = None,
    checklist_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Core functional query engine returning structured data for requested fields & invariants.
    """
    content = load_raw_checklist(checklist_path)
    matrix = parse_checklist_matrix(content)
    raw_invariants = parse_invariants_sections(content)

    selected_fields: List[Dict[str, Any]] = []
    invalid_fields: List[str] = []

    if fields:
        for f_query in fields:
            resolved = resolve_field_key(f_query)
            if resolved:
                f_meta = CANONICAL_FIELDS[resolved]
                idx = f_meta["index"]
                f_data = matrix.get(idx, {})
                selected_fields.append({
                    "code": resolved,
                    "index": idx,
                    "name": f_meta["name"],
                    "positive": f_data.get("positive", ""),
                    "boundary_negative": f_data.get("boundary_negative", ""),
                    "security_edge_cases": f_data.get("security_edge_cases", "")
                })
            else:
                invalid_fields.append(f_query.strip())

    selected_invariants: List[Dict[str, Any]] = []
    invalid_invariants: List[str] = []

    if invariants:
        # Handle 'all' or 'none'
        if any(inv.strip().lower() == "all" for inv in invariants):
            for code, inv_meta in CANONICAL_INVARIANTS.items():
                idx = inv_meta["index"]
                inv_data = _find_raw_invariant(raw_invariants, inv_meta)
                selected_invariants.append({
                    "code": code,
                    "index": idx,
                    "title": inv_meta["title"],
                    "content": inv_data.get("content", "")
                })
        elif any(inv.strip().lower() == "none" for inv in invariants):
            selected_invariants = []
        else:
            for inv_query in invariants:
                resolved = resolve_invariant_key(inv_query)
                if resolved:
                    inv_meta = CANONICAL_INVARIANTS[resolved]
                    idx = inv_meta["index"]
                    inv_data = _find_raw_invariant(raw_invariants, inv_meta)
                    selected_invariants.append({
                        "code": resolved,
                        "index": idx,
                        "title": inv_meta["title"],
                        "content": inv_data.get("content", "")
                    })
                else:
                    invalid_invariants.append(inv_query.strip())

    return {
        "fields": selected_fields,
        "invariants": selected_invariants,
        "invalid_fields": invalid_fields,
        "invalid_invariants": invalid_invariants
    }


def render_markdown(query_result: Dict[str, Any]) -> str:
    """Formats query results as clean, compact Markdown tables & sections."""
    lines: List[str] = []

    fields = query_result.get("fields", [])
    if fields:
        lines.append("### Field Validation Matrix (Filtered)")
        lines.append("")
        lines.append("| Code | Field Type | Positive Verification | Boundary & Negative Checks (3-Value BVA) | Security & Enterprise Edge Cases |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for f in fields:
            lines.append(f"| `{f['code']}` | **{f['name']}** | {f['positive']} | {f['boundary_negative']} | {f['security_edge_cases']} |")
        lines.append("")

    invariants = query_result.get("invariants", [])
    if invariants:
        lines.append("### Non-Functional & Resilience Protocols")
        lines.append("")
        for inv in invariants:
            lines.append(f"#### `{inv['code']}`: {inv['title']}")
            lines.append(inv["content"])
            lines.append("")

    return "\n".join(lines).strip()


def list_catalog() -> str:
    """Returns a clean formatted table listing all 25 field types and 7 resilience invariants."""
    lines: List[str] = [
        "=========================================================================================",
        "        SYNAPSE-HUB ON-DEMAND FIELD VALIDATION CHECKLIST & INVARIANTS CATALOG           ",
        "=========================================================================================",
        "",
        "## 1. 25 Input Field Types (Query via: --fields <codes>)",
        "",
        "| # | Code | Canonical Name | Sample Aliases |",
        "| :- | :--- | :--- | :--- |"
    ]
    for code, data in CANONICAL_FIELDS.items():
        aliases = ", ".join(data["aliases"][:3])
        lines.append(f"| {data['index']:02d} | `{code}` | {data['name']} | {aliases} |")

    lines.extend([
        "",
        "## 2. 8 Non-Functional Invariants (Query via: --invariants <codes> / all / none)",
        "",
        "| # | Code | Protocol Title | Sample Aliases |",
        "| :- | :--- | :--- | :--- |"
    ])
    for code, data in CANONICAL_INVARIANTS.items():
        aliases = ", ".join(data["aliases"][:3])
        lines.append(f"| {data['index']:02d} | `{code}` | {data['title']} | {aliases} |")

    lines.extend([
        "",
        "⚡ Quick Examples:",
        "  python tools/manual/checklist_query.py --fields email,password,otp",
        "  python tools/manual/checklist_query.py --fields number,currency --invariants unicode-ime,payment-ui-latency",
        "  agent-qa checklist --fields text,email --format json"
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query field-level validation checklist and resilience invariants on demand (0-token)"
    )
    parser.add_argument("--list", "-l", action="store_true", help="List all 25 field codes and 8 invariant codes")
    parser.add_argument("--fields", "-f", default=None, help="Comma-separated field codes or aliases (e.g. email,password,otp)")
    parser.add_argument("--invariants", "-i", default=None, help="Comma-separated invariant codes, 'all', or 'none'")
    parser.add_argument("--format", choices=["md", "json"], default="md", help="Output format: 'md' (default) or 'json'")
    parser.add_argument("--checklist-path", default=None, help="Custom path to field_validation_checklist.md")

    args = parser.parse_args()

    if args.list or (not args.fields and not args.invariants):
        if args.format == "json":
            catalog = {
                "fields": [
                    {"index": d["index"], "code": k, "name": d["name"], "aliases": d["aliases"]}
                    for k, d in CANONICAL_FIELDS.items()
                ],
                "invariants": [
                    {"index": d["index"], "code": k, "title": d["title"], "aliases": d["aliases"]}
                    for k, d in CANONICAL_INVARIANTS.items()
                ]
            }
            print(json.dumps(catalog, indent=2, ensure_ascii=False))
        else:
            print(list_catalog())
        return 0

    field_list = [f.strip() for f in args.fields.split(",") if f.strip()] if args.fields else None
    invariant_list = [i.strip() for i in args.invariants.split(",") if i.strip()] if args.invariants else None

    result = query_checklist(
        fields=field_list,
        invariants=invariant_list,
        checklist_path=args.checklist_path
    )

    if result["invalid_fields"]:
        sys.stderr.write(
            f"❌ Unknown field(s): {', '.join(result['invalid_fields'])}. Run with --list to view valid codes.\n"
        )
    if result["invalid_invariants"]:
        sys.stderr.write(
            f"❌ Unknown invariant(s): {', '.join(result['invalid_invariants'])}. Run with --list to view valid codes.\n"
        )

    if result["invalid_fields"] or result["invalid_invariants"]:
        return 1

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        rendered = render_markdown(result)
        if rendered:
            print(rendered)
        else:
            print("No matching fields or invariants selected.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
