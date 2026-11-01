#!/usr/bin/env python3
"""
Enterprise Action Safety Firewall & Blast Radius Containment Engine
--------------------------------------------------------------------
Prevents AI agents and test runners from executing catastrophic or irreversible
actions on Live/Staging/UAT environments (e.g. Delete All, Purge, Wipe, Pay, Drop).

Supports:
  - Direct action checking (--action, --text, --selector)
  - Code snippet and script inspection (--code, --file)
  - Pipeline stdin stream inspection (e.g. echo 'page.click(...)' | python safety_firewall.py --dry-run)
  - Pre-execution validation hooks before Playwright/CDP browser dispatch
"""

import os
import re
import sys
import json
import argparse
from typing import List, Dict, Any, Tuple

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

DANGEROUS_ACTION_KEYWORDS = [
    r"\bdelete\b",
    r"\bpurge\b",
    r"\bwipe\b",
    r"\bdrop\b",
    r"\bpay\b",
    r"\bpurchase\b",
    r"\bplace\s+order\b",
    r"\bconfirm\s+(?:payment|order|delete|deletion|purge|wipe|destroy)\b",
    r"\bsubmit\s+order\b",
    r"\barchive\s+(?:all|data|system|database|account)\b",
    r"\brevoke\s+access\b",
    r"\bcancel\s+subscription\b",
    r"\berase\s+all\s+data\b",
    r"\bterminate(?:\s+account)?\b",
    r"\bdestroy\b",
    r"\bformat\s+(?:disk|drive|system|database|table|partition)\b",
    # Multilingual & Vietnamese destructive keywords with strict word boundaries
    r"(?<!\w)x[oóòỏõọ][aáàảãạ](?!\w)",
    r"(?<!\w)x[oóòỏõọ]a\s+t[aáàảãạ]t\s+c[aảáàãạ](?!\w)",
    r"(?<!\w)h[uủúùũụ]y\s+b[oỏóòõọ](?!\w)",
    r"(?<!\w)h[uủúùũụ]y\s+t[aàáảãạ]i\s+kho[aảáàãạ]n(?!\w)",
    r"(?<!\w)thanh\s+to[aáàảãạ]n(?!\w)",
    r"(?<!\w)r[uúùủũụ]t\s+ti[eềéèẻẽẹ]n(?!\w)",
    r"(?<!\w)n[aạáàảã]p\s+ti[eềéèẻẽẹ]n(?!\w)",
]

# Explicit whitelist of benign user-flow patterns that require exact fullmatch to authorize
BENIGN_ACTIONS_WHITELIST = [
    re.compile(r"(?i)^\s*(?:checkout|proceed\s+to\s+checkout)\s*$"),
    re.compile(r"(?i)^\s*(?:reset\s+password)\s*$"),
    re.compile(r"(?i)^\s*(?:remove\s+from\s+cart)\s*$"),
    re.compile(r"(?i)^\s*(?:xoay\s+[aảáàãạ]nh)\s*$"),
]

def _split_words_and_camel(s: str) -> str:
    """Expands camelCase and PascalCase into separated words for keyword inspection."""
    return re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', s)

DANGEROUS_SELECTOR_PATTERNS = [
    r"\[data-action\*=['\"]?(?:delete|pay|confirm)['\"]?\]",
    r"\.btn-danger\b",
    r"\.p-button-danger\b",
    r"#(?:btn-confirm|btn-delete|btn-purge)\b",
    r"\[aria-label\*=['\"]?(?:delete|pay|confirm)['\"]?\]",
    r"button[#\.\-_a-zA-Z0-9]*[_\-]*(?:del|delete|purge|wipe|drop|confirm|archive)",
    r":(?:has-text|text)\s*\(\s*(['\"])[^'\"]*(?:delete|wipe|purge|pay|confirm|archive|x[oóòỏõọ][aáàảãạ]|h[uủúùũụ]y\s+b[oỏóòõọ]|thanh\s*to[aáàảãạ]n)[^'\"]*\1\s*\)",
    r"text=(['\"])[^'\"]*(?:delete|wipe|purge|pay|confirm|archive|x[oóòỏõọ][aáàảãạ]|h[uủúùũụ]y\s+b[oỏóòõọ]|thanh\s*to[aáàảãạ]n)\1",
]

COMPILED_TEXT_REGEX = re.compile("|".join(DANGEROUS_ACTION_KEYWORDS), re.IGNORECASE)
COMPILED_SEL_REGEX = re.compile("|".join(DANGEROUS_SELECTOR_PATTERNS), re.IGNORECASE)

# Pattern to extract interaction statements from Playwright / Selenium / Groovy
INTERACTION_CODE_PATTERNS = [
    # page.click('selector'), page.fill('selector', 'val') - supports nested quotes
    re.compile(r"""(?:page|frame)\.(?P<act>click|dblclick|fill|type|press|check)\s*\(\s*(?P<q>['"])(?P<sel>(?:(?!(?P=q)|\\).|\\.)*)(?P=q)(?:\s*,\s*['"](?P<text>[^'"]*)['"])?""", re.IGNORECASE),
    # page.locator('selector').click()
    re.compile(r"""(?:page|frame)\.locator\s*\(\s*(?P<q>['"])(?P<sel>(?:(?!(?P=q)|\\).|\\.)*)(?P=q)\s*\)\.(?P<act>click|fill|press)""", re.IGNORECASE),
    # page.getByText('text').click()
    re.compile(r"""(?:page|frame)\.getByText\s*\(\s*(?P<q>['"])(?P<text>(?:(?!(?P=q)|\\).|\\.)*)(?P=q)\s*\)\.(?P<act>click)""", re.IGNORECASE),
    # page.getByRole('button', { name: 'Delete' }).click()
    re.compile(r"""(?:page|frame)\.getByRole\s*\(\s*['"](?P<role>[^'"]+)['"]\s*,\s*\{[^}]*name:\s*['"](?P<text>[^'"]+)['"]""", re.IGNORECASE),
    # WebUI.click(findTestObject(...)) or WebUI.clickOffset
    re.compile(r"""WebUI\.(?P<act>click|setText)\s*\([^)]*['"](?P<sel>[^'"]*)['"]""", re.IGNORECASE),
    # Clean POM method invocation: e.g. customerPage.deleteAllCustomers(), accountPO.purgeAccount(userId)
    re.compile(r"""(?P<page>(?!page\b|frame\b|WebUI\b)[a-zA-Z0-9_]*(?:Page|PO|View|Service|Component|[a-z]))\.(?P<act>[a-zA-Z0-9_]+)\s*\((?P<args>[^)]*)\)""", re.IGNORECASE),
    # Variable locator call: e.g. deleteBtn.click(), btnConfirm.click()
    re.compile(r"""(?P<var>[a-zA-Z0-9_]*(?:btn|button|link|icon|input|elem|element|action)[a-zA-Z0-9_]*|[a-zA-Z0-9_]*(?:delete|del|purge|wipe|drop|pay|confirm)[a-zA-Z0-9_]*)\.(?P<act>click|dblclick|fill|press|tap)\s*\(""", re.IGNORECASE),
]


def is_action_dangerous(action_type: str, text: str = "", selector: str = "") -> Tuple[bool, str]:
    """
    Evaluates whether an intended action touches a dangerous or irreversible UI element.
    Returns (is_dangerous: bool, reason: str).
    """
    text_clean = text.strip() if text else ""
    sel_clean = selector.strip() if selector else ""
    act_clean = action_type.strip() if action_type else "click"

    # 1. Action type verification
    act_expanded = _split_words_and_camel(act_clean)
    if act_clean.lower() in ("drop_database", "wipe_environment", "execute_payment"):
        return True, f"Action type '{action_type}' is classified as irreversible"
    match_act = COMPILED_TEXT_REGEX.search(act_clean) or COMPILED_TEXT_REGEX.search(act_expanded)
    if match_act:
        return True, f"Action method contains dangerous verb: '{match_act.group(0)}'"

    # 2. Check text (Dangerous check runs FIRST; benign whitelist requires strict fullmatch)
    if text_clean:
        text_expanded = _split_words_and_camel(text_clean)
        match = COMPILED_TEXT_REGEX.search(text_clean) or COMPILED_TEXT_REGEX.search(text_expanded)
        if match:
            # Check strict benign whitelist fullmatch before flagging
            if any(p.fullmatch(text_clean) for p in BENIGN_ACTIONS_WHITELIST):
                pass
            else:
                return True, f"Element text contains dangerous keyword: '{match.group(0)}'"

    # 3. Check selector
    if sel_clean:
        if not any(p.fullmatch(sel_clean) for p in BENIGN_ACTIONS_WHITELIST):
            if COMPILED_SEL_REGEX.search(sel_clean):
                return True, f"Element selector matches destructive pattern: '{sel_clean}'"
            sel_expanded = _split_words_and_camel(sel_clean)
            match = COMPILED_TEXT_REGEX.search(sel_clean) or COMPILED_TEXT_REGEX.search(sel_expanded)
            if match:
                return True, f"Element selector contains dangerous keyword: '{match.group(0)}' in '{sel_clean}'"

    return False, "Action passed safety firewall inspection"


def inspect_and_authorize(action_type: str, text: str = "", selector: str = "", force: bool = False) -> Dict[str, Any]:
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


def inspect_code_snippet(code: str, force: bool = False) -> List[Dict[str, Any]]:
    """
    Parses a code snippet or script and checks all discovered UI interaction statements.
    """
    inspections = []
    lines = code.splitlines()

    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "#", "/*", "*")):
            continue

        matched = False
        for pattern in INTERACTION_CODE_PATTERNS:
            found_any = False
            for match in pattern.finditer(line):
                found_any = True
                groups = match.groupdict()
                act = groups.get("act") or "click"
                sel = groups.get("sel") or ""
                text = groups.get("text") or ""
                if not sel and groups.get("page"):
                    sel = f"{groups.get('page')}.{act}"
                if not sel and groups.get("var"):
                    sel = groups.get("var")
                auth = inspect_and_authorize(act, text=text, selector=sel, force=force)
                auth["line"] = line_idx
                auth["code"] = stripped
                inspections.append(auth)
            if found_any:
                matched = True
                break

        # Fallback: line itself contains dangerous keyword and an action verb
        if not matched:
            line_expanded = _split_words_and_camel(stripped)
            if (COMPILED_TEXT_REGEX.search(stripped) or COMPILED_TEXT_REGEX.search(line_expanded)) and any(w in stripped.lower() for w in ("click", "press", "submit", "post", "delete", "purge", "wipe", "drop", "pay")):
                auth = inspect_and_authorize("dispatch", text=stripped, selector="", force=force)
                auth["line"] = line_idx
                auth["code"] = stripped
                inspections.append(auth)

    return inspections


def main():
    parser = argparse.ArgumentParser(description="Action Safety Firewall & Blast Radius Containment Engine")
    parser.add_argument("--action", default="click", help="Action type (click, fill, submit)")
    parser.add_argument("--text", default="", help="Text content of target element")
    parser.add_argument("--selector", default="", help="CSS/XPath selector of target element")
    parser.add_argument("--code", default="", help="Direct code snippet or command line to evaluate (use '-' for stdin)")
    parser.add_argument("--file", default="", help="Path to script file to evaluate")
    parser.add_argument("--stdin", action="store_true", help="Read code or action from standard input")
    parser.add_argument("--dry-run", action="store_true", help="Execute in pre-execution dry-run mode (outputs validation report)")
    parser.add_argument("--force", action="store_true", help="Force bypass safety firewall")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    # Determine input source: explicit stdin flag/arg, --file, --code, or parameters
    code_content = ""
    if args.code and args.code != "-":
        code_content = args.code
    elif args.file and os.path.exists(args.file):
        with open(args.file, "r", encoding="utf-8", errors="ignore") as f:
            code_content = f.read()
    elif args.stdin or args.code == "-":
        try:
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                # Check if stdin is JSON
                if stdin_data.startswith("{") and stdin_data.endswith("}"):
                    try:
                        parsed = json.loads(stdin_data)
                        if "action" in parsed or "selector" in parsed:
                            args.action = parsed.get("action", args.action)
                            args.text = parsed.get("text", args.text)
                            args.selector = parsed.get("selector", args.selector)
                        else:
                            code_content = stdin_data
                    except Exception:
                        code_content = stdin_data
                else:
                    code_content = stdin_data
        except Exception:
            pass

    # Evaluation
    if code_content:
        inspections = inspect_code_snippet(code_content, force=args.force)
        has_blocked = any(not item["authorized"] for item in inspections)
        all_authorized = not has_blocked

        report = {
            "mode": "dry-run" if args.dry_run else "enforce",
            "total_inspected": len(inspections),
            "authorized": all_authorized,
            "blocked_count": sum(1 for item in inspections if not item["authorized"]),
            "inspections": inspections
        }

        if args.json:
            print(json.dumps(report, indent=2))
        else:
            tag = "DRY-RUN INSPECTION" if args.dry_run else "FIREWALL SENTINEL"
            print(f"\n🛡️  [{tag}] Inspected {len(inspections)} interaction statements:")
            for item in inspections:
                status = "[PASS]" if item["authorized"] else "[BLOCKED]"
                line_info = f"Line {item.get('line', '?')}: " if 'line' in item else ""
                print(f"  {status} {line_info}{item['action']} -> {item['reason']}")
                if not item["authorized"]:
                    print(f"         Code: {item.get('code', '')}")

            if all_authorized:
                print(f"\n✅ All actions cleared by Safety Firewall{' (Dry-Run)' if args.dry_run else ''}.\n")
            else:
                print(f"\n❌ Pre-execution Blocked: Destructive actions intercepted without --force or ALLOW_DESTRUCTIVE=1.\n")

        return 0 if all_authorized else 1

    # Single-action check (legacy / parameter mode)
    auth = inspect_and_authorize(args.action, args.text, args.selector, args.force)
    auth["mode"] = "dry-run" if args.dry_run else "enforce"

    if args.json:
        print(json.dumps(auth, indent=2))
    else:
        prefix = "[DRY-RUN] " if args.dry_run else ""
        if auth["authorized"]:
            status_tag = f"{prefix}[PASS] Action Authorized" if not auth["dangerous"] else f"{prefix}[BYPASS] Destructive Action Force-Authorized"
            print(f"🛡️  {status_tag}: {auth['reason']}")
        else:
            print(f"❌ {prefix}[BLOCKED] Action Safety Firewall Intercepted: {auth['reason']}")
            print("   👉 To authorize, pass --force or set ALLOW_DESTRUCTIVE=1.")

    return 0 if auth["authorized"] else 1


if __name__ == "__main__":
    sys.exit(main())
