#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/cldr_l10n_verifier.py — Enterprise Unicode CLDR & L10n/I18n Verification Engine
-------------------------------------------------------------------------------------
Conforms to Unicode Common Locale Data Repository (CLDR) standards:
  1. Date, Time, Number, and Currency formatting validation across world locales
     (en-US, vi-VN, de-DE, fr-FR, ja-JP, ar-SA).
  2. Pseudo-Localization Transformation Engine: Generates diacritic-expanded strings
     with length padding ([!!! ... !!!]) to detect hardcoded text and UI truncation.
  3. Locale Alphabetical Collation (sorting order) verification.
  4. Template Hardcoded String Scanner.

Usage:
  python tools/cldr_l10n_verifier.py --pseudo "Confirm Payment"
  python tools/cldr_l10n_verifier.py --verify-currency "1.234.500 ₫" --locale vi-VN
  python tools/cldr_l10n_verifier.py --verify-date "17/11/2026" --locale vi-VN
  python tools/cldr_l10n_verifier.py --scan-html template.html
"""

import os
import sys
import json
import re
import argparse
from typing import Dict, List, Any, Tuple
from html.parser import HTMLParser

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ==============================================================================
# UNICODE CLDR LOCALE DEFINITIONS & SPECIFICATIONS
# ==============================================================================

CLDR_LOCALES = {
    "en-US": {
        "name": "English (United States)",
        "decimal": ".",
        "thousands": ",",
        "currency_symbol": "$",
        "currency_pattern": re.compile(r"^\$\s?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?$"),
        "date_pattern": re.compile(r"^(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12][0-9]|3[01])/\d{4}$"),
        "date_format_example": "MM/DD/YYYY (e.g. 11/17/2026)",
        "rtl": False,
    },
    "vi-VN": {
        "name": "Vietnamese (Vietnam)",
        "decimal": ",",
        "thousands": ".",
        "currency_symbol": "₫",
        "currency_pattern": re.compile(r"^[0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{1,2})?\s?(?:₫|VND)$", re.IGNORECASE),
        "date_pattern": re.compile(r"^(?:0?[1-9]|[12][0-9]|3[01])/(?:0?[1-9]|1[0-2])/\d{4}$"),
        "date_format_example": "DD/MM/YYYY (e.g. 17/11/2026)",
        "rtl": False,
    },
    "de-DE": {
        "name": "German (Germany)",
        "decimal": ",",
        "thousands": ".",
        "currency_symbol": "€",
        "currency_pattern": re.compile(r"^[0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?\s?€$"),
        "date_pattern": re.compile(r"^(?:0?[1-9]|[12][0-9]|3[01])\.(?:0?[1-9]|1[0-2])\.\d{4}$"),
        "date_format_example": "DD.MM.YYYY (e.g. 17.11.2026)",
        "rtl": False,
    },
    "fr-FR": {
        "name": "French (France)",
        "decimal": ",",
        "thousands": " ",
        "currency_symbol": "€",
        "currency_pattern": re.compile(r"^[0-9]{1,3}(?:[\s\u00A0\u202F][0-9]{3})*(?:,[0-9]{2})?\s?€$"),
        "date_pattern": re.compile(r"^(?:0?[1-9]|[12][0-9]|3[01])/(?:0?[1-9]|1[0-2])/\d{4}$"),
        "date_format_example": "DD/MM/YYYY (e.g. 17/11/2026)",
        "rtl": False,
    },
    "ja-JP": {
        "name": "Japanese (Japan)",
        "decimal": ".",
        "thousands": ",",
        "currency_symbol": "¥",
        "currency_pattern": re.compile(r"^[¥￥]\s?[0-9]{1,3}(?:,[0-9]{3})*$"),
        "date_pattern": re.compile(r"^\d{4}/(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12][0-9]|3[01])$|^\d{4}年(?:0?[1-9]|1[0-2])月(?:0?[1-9]|[12][0-9]|3[01])日$"),
        "date_format_example": "YYYY/MM/DD (e.g. 2026/11/17)",
        "rtl": False,
    },
    "ar-SA": {
        "name": "Arabic (Saudi Arabia)",
        "decimal": "٫",
        "thousands": "٬",
        "currency_symbol": "ر.س",
        "currency_pattern": re.compile(r"^[0-9\u0660-\u0669]+.*(?:ر\.س|SAR)"),
        "date_pattern": re.compile(r"^(?:0?[1-9]|[12][0-9]|3[01])/(?:0?[1-9]|1[0-2])/\d{4}$"),
        "date_format_example": "DD/MM/YYYY",
        "rtl": True,
    },
}


# ==============================================================================
# PSEUDO-LOCALIZATION ENGINE
# ==============================================================================

ACCENT_CHAR_MAP = {
    "A": "Å", "B": "Ɓ", "C": "Ç", "D": "Ð", "E": "É", "F": "Ƒ", "G": "Ĝ",
    "H": "Ĥ", "I": "Ì", "J": "Ĵ", "K": "Ķ", "L": "Ł", "M": "Ṁ", "N": "Ñ",
    "O": "Ò", "P": "Þ", "Q": "Ǫ", "R": "Ŕ", "S": "Š", "T": "Ţ", "U": "Ù",
    "V": "Ṽ", "W": "Ŵ", "X": "Ẋ", "Y": "Ý", "Z": "Ž",
    "a": "à", "b": "ƀ", "c": "ç", "d": "đ", "e": "è", "f": "ƒ", "g": "ĝ",
    "h": "ĥ", "i": "ì", "j": "ĵ", "k": "ķ", "l": "ł", "m": "ṁ", "n": "ñ",
    "o": "ò", "p": "þ", "q": "ǫ", "r": "ŕ", "s": "š", "t": "ţ", "u": "ù",
    "v": "ṽ", "w": "ŵ", "x": "ẋ", "y": "ý", "z": "ž",
}


def pseudo_localize(text: str, expand_pct: int = 35) -> str:
    """
    Transforms plain English strings into pseudo-localized test strings:
      1. Replaces ASCII letters with accented visual equivalents.
      2. Preserves format placeholders like {0}, %s, {name}.
      3. Expands length by expand_pct% to detect UI layout overflow / truncation.
      4. Wraps in [!!! ... !!!] markers.
    """
    if not text:
        return text

    # Protect formatting placeholders: {variable}, %s, %d
    placeholder_pattern = re.compile(r"(\{[a-zA-Z0-9_]+\}|%[a-zA-Z])")
    tokens = placeholder_pattern.split(text)

    transformed_tokens = []
    for token in tokens:
        if placeholder_pattern.match(token):
            transformed_tokens.append(token)
        else:
            transformed_chars = [ACCENT_CHAR_MAP.get(c, c) for c in token]
            transformed_tokens.append("".join(transformed_chars))

    body = "".join(transformed_tokens)

    # Calculate padding length for UI overflow testing
    pad_len = max(int(len(text) * (expand_pct / 100.0)), 2)
    padding = "~" + ("one two three four five six seven eight nine ten"[:pad_len].strip()) + "~"

    return f"[!!! {body} {padding} !!!]"


# ==============================================================================
# CLDR FORMAT VERIFIER FUNCTIONS
# ==============================================================================

def verify_date_format(date_str: str, locale_code: str) -> Tuple[bool, str]:
    """Validates date string conformance against CLDR locale pattern."""
    loc = CLDR_LOCALES.get(locale_code)
    if not loc:
        return False, f"Unsupported locale '{locale_code}'"
    pat = loc["date_pattern"]
    if pat.match(date_str.strip()):
        return True, f"Valid {locale_code} date format ({loc['date_format_example']})"
    return False, f"Invalid {locale_code} date format: '{date_str}'. Expected {loc['date_format_example']}."


def verify_currency_format(currency_str: str, locale_code: str) -> Tuple[bool, str]:
    """Validates currency string conformance against CLDR locale rules."""
    loc = CLDR_LOCALES.get(locale_code)
    if not loc:
        return False, f"Unsupported locale '{locale_code}'"
    pat = loc["currency_pattern"]
    if pat.match(currency_str.strip()):
        return True, f"Valid {locale_code} currency format ({loc['name']})"
    return False, f"Invalid {locale_code} currency format: '{currency_str}'."


def verify_collation_order(items: List[str], locale_code: str = "vi-VN") -> Tuple[bool, List[str]]:
    """
    Verifies that a list of strings is sorted in correct alphabetical collation.
    For vi-VN, accounts for Vietnamese diacritics ordering (a, ă, â, b, c, d, đ, e, ê, ...).
    """
    # Vietnamese custom alphabet weight table
    vi_alphabet = "aàáảãạăằắẳẵặâầấẩẫậbcdđeèéẻẽẹêềếểễệghiìíỉĩịklmnoòóỏõọôồốổỗộơờớởỡợpqrstuùúủũụưừứửữựvxyỳýỷỹỵ"
    char_weight = {c: i for i, c in enumerate(vi_alphabet)}

    def vi_sort_key(s: str):
        key = []
        for ch in s.lower():
            key.append(char_weight.get(ch, ord(ch) + 1000))
        return key

    if locale_code == "vi-VN":
        sorted_expected = sorted(items, key=vi_sort_key)
    else:
        sorted_expected = sorted(items)

    is_sorted = (items == sorted_expected)
    return is_sorted, sorted_expected


# ==============================================================================
# HTML TEMPLATE HARDCODED STRINGS AUDITOR
# ==============================================================================

class HTMLHardcodedStringAuditor(HTMLParser):
    """Scans HTML documents to find untranslated, hardcoded text nodes."""

    def __init__(self):
        super().__init__()
        self.hardcoded_strings: List[Dict[str, Any]] = []
        self.current_tag = ""
        self.ignored_tags = {"script", "style", "code", "pre", "svg", "noscript"}

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag.lower()

    def handle_data(self, data):
        if self.current_tag in self.ignored_tags:
            return
        cleaned = data.strip()
        # Heuristic: Text with letters that is not a template placeholder like {{ ... }} or {% ... %}
        if cleaned and len(cleaned) > 2 and re.search(r"[a-zA-Z]{2,}", cleaned):
            if not (cleaned.startswith("{{") or cleaned.startswith("{%") or cleaned.startswith("$")):
                self.hardcoded_strings.append({
                    "tag": self.current_tag,
                    "text": cleaned,
                    "suggestion": f"Wrap with i18n translation key (e.g. t('{cleaned}'))",
                })


# ==============================================================================
# CLI HANDLER
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Synapse Hub Unicode CLDR & L10n/I18n Verification Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pseudo", help="Generate pseudo-localized string for UI truncation/encoding testing")
    parser.add_argument("--expand", type=int, default=35, help="Expansion percentage for pseudo-localization (default: 35%%)")
    parser.add_argument("--verify-date", help="Date string to validate against locale (e.g. '17/11/2026')")
    parser.add_argument("--verify-currency", help="Currency string to validate (e.g. '1.500.000 ₫' or '$1,234.56')")
    parser.add_argument("--locale", default="vi-VN", choices=list(CLDR_LOCALES.keys()), help="Target CLDR locale code")
    parser.add_argument("--scan-html", help="Path to HTML template to detect hardcoded non-i18n strings")
    parser.add_argument("--json", action="store_true", help="Output results in structured JSON format")

    args = parser.parse_args()

    if args.pseudo:
        res = pseudo_localize(args.pseudo, expand_pct=args.expand)
        if args.json:
            print(json.dumps({"original": args.pseudo, "pseudo_localized": res, "expansion_pct": args.expand}, indent=2, ensure_ascii=False))
        else:
            print(f"Original : {args.pseudo}")
            print(f"Pseudo   : {res}")
            print(f"Length   : {len(args.pseudo)} -> {len(res)} chars (+{len(res)-len(args.pseudo)} chars for layout test)")
        return 0

    if args.verify_date:
        valid, msg = verify_date_format(args.verify_date, args.locale)
        status = "\033[92m[PASS]\033[0m" if valid else "\033[91m[FAIL]\033[0m"
        print(f"{status} {msg}")
        return 0 if valid else 1

    if args.verify_currency:
        valid, msg = verify_currency_format(args.verify_currency, args.locale)
        status = "\033[92m[PASS]\033[0m" if valid else "\033[91m[FAIL]\033[0m"
        print(f"{status} {msg}")
        return 0 if valid else 1

    if args.scan_html:
        if not os.path.exists(args.scan_html):
            print(f"❌ Error: HTML file not found: {args.scan_html}", file=sys.stderr)
            return 2
        with open(args.scan_html, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        auditor = HTMLHardcodedStringAuditor()
        auditor.feed(html)
        payload = {
            "file": args.scan_html,
            "total_hardcoded_strings": len(auditor.hardcoded_strings),
            "findings": auditor.hardcoded_strings,
        }
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print("=" * 70)
            print("  SYNAPSE HUB — L10N HARDCODED STRING AUDIT REPORT")
            print("=" * 70)
            print(f"  Target File : {args.scan_html}")
            print(f"  Total Found : {len(auditor.hardcoded_strings)}")
            for item in auditor.hardcoded_strings[:10]:
                print(f"  \033[93m[UNTRANSLATED]\033[0m <{item['tag']}>: '{item['text']}'")
            print("=" * 70)
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
