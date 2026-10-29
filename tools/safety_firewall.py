#!/usr/bin/env python3
"""
Enterprise Action Safety Firewall & Blast Radius Containment Engine
--------------------------------------------------------------------
Prevents AI agents and test runners from executing catastrophic or irreversible
actions on Live/Staging/UAT environments (e.g. Delete All, Purge, Wipe, Pay, Drop).
"""

import os
import re
import sys
import json
import argparse

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

DANGEROUS_ACTION_KEYWORDS = [
    r"\bdelete\b",
    r"\bremove\b",
    r"\bpurge\b",
    r"\bwipe\b",
    r"\bdrop\b",
    r"\bpay\b",
    r"\bpurchase\b",
    r"\bcheckout\b",
    r"\bterminate\b",
    r"\bdestroy\b",
    r"\breset\b",
    r"\btransfer\b",
    r"\bformat\b",
]

DANGEROUS_SELECTOR_PATTERNS = [
    r"\[data-action\*=['\"]?delete['\"]?\]",
    r"\[data-action\*=['\"]?pay['\"]?\]",
    r"\.btn-danger\b",
    r"\.p-button-danger\b",
    r"\[aria-label\*=['\"]?delete['\"]?\]",
]

COMPILED_TEXT_REGEX = re.compile("|".join(DANGEROUS_ACTION_KEYWORDS), re.IGNORECASE)
COMPILED_SEL_REGEX = re.compile("|".join(DANGEROUS_SELECTOR_PATTERNS), re.IGNORECASE)


def is_action_dangerous(action_type: str, text: str = "", selector: str = "") -> tuple[bool, str]:
    """
    Evaluates whether an intended action touches a dangerous or irreversible UI element.
    Returns (is_dangerous: bool, reason: str).
    """
    text_clean = text.strip() if text else ""
    sel_clean = selector.strip() if selector else ""

    # Check text content
    if text_clean and COMPILED_TEXT_REGEX.search(text_clean):
        match = COMPILED_TEXT_REGEX.search(text_clean).group(0)
        return True, f"Element text contains dangerous keyword: '{match}'"

    # Check selector
    if sel_clean and COMPILED_SEL_REGEX.search(sel_clean):
        return True, f"Element selector matches destructive pattern: '{sel_clean}'"

    # Specific dangerous action types
    if action_type.lower() in ("drop_database", "wipe_environment", "execute_payment"):
        return True, f"Action type '{action_type}' is classified as irreversible"

    return False, "Action passed safety firewall inspection"


def inspect_and_authorize(action_type: str, text: str = "", selector: str = "", force: bool = False) -> dict:
    """
    Evaluates action and checks authorization policy.
    Bypass is permitted only if force=True or ALLOW_DESTRUCTIVE=1 environment variable is set.
    """
    dangerous, reason = is_action_dangerous(action_type, text, selector)
    bypass = force or os.environ.get("ALLOW_DESTRUCTIVE", "").lower() in ("true", "1", "yes")

    result = {
        "action": action_type,
        "text": text,
        "selector": selector,
        "dangerous": dangerous,
        "reason": reason,
        "authorized": (not dangerous) or bypass,
        "bypass_granted": bypass if dangerous else False
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Action Safety Firewall & Blast Radius Containment")
    parser.add_argument("--action", default="click", help="Action type (click, fill, submit)")
    parser.add_argument("--text", default="", help="Text content of target element")
    parser.add_argument("--selector", default="", help="CSS/XPath selector of target element")
    parser.add_argument("--force", action="store_true", help="Force bypass safety firewall")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    auth = inspect_and_authorize(args.action, args.text, args.selector, args.force)

    if args.json:
        print(json.dumps(auth, indent=2))
    else:
        if auth["authorized"]:
            status_tag = "[PASS] Action Authorized" if not auth["dangerous"] else "[BYPASS] Destructive Action Force-Authorized"
            print(f"🛡️  {status_tag}: {auth['reason']}")
        else:
            print(f"❌ [BLOCKED] Action Safety Firewall Intercepted: {auth['reason']}")
            print("   👉 To authorize, pass --force or set ALLOW_DESTRUCTIVE=1.")

    return 0 if auth["authorized"] else 1


if __name__ == "__main__":
    sys.exit(main())
