#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tools/break_ui_generator.py — Edge-Case UI Stress Testing Data Generator
Inspired by Emil Kowalski's break-ui skill (emilkowalski/skills).
Generates extreme data boundaries, unspaced strings, Zalgo, RTL, boundary floats,
and odd viewports to proactively discover layout breakages, text truncation bugs,
and visual regressions before production deployment.
100% UTF-8 No BOM. Zero external dependencies.
"""
from __future__ import annotations

import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import argparse
import json
import sys
from typing import Any, Dict, List

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 1. Extreme Strings (Zalgo, unspaced overflow, zero-width, markup injection)
BREAK_STRINGS: List[Dict[str, str]] = [
    {
        "name": "unspaced_500_chars",
        "description": "500-char continuous string to test CSS word-break / overflow-wrap",
        "value": "Supercalifragilisticexpialidocious" * 15,
    },
    {
        "name": "unspaced_2000_chars",
        "description": "2,000-char continuous string to force container overflow",
        "value": "A" * 2000,
    },
    {
        "name": "zero_width_spaces",
        "description": "Invisible zero-width joiners and spaces to test renderer length calculation",
        "value": "Zero\u200BWidth\u200CSpace\u200DTest\uFEFFInvisible",
    },
    {
        "name": "zalgo_corrupted_text",
        "description": "Heavily combining diacritic marks to test vertical line-height clipping",
        "value": "T̶͕͂é̷̯s̴̱͘t̸͙͒ ̸͚̈́Z̷̯̆a̴͖̓l̸͔̐g̶̭͒ỏ̷̱ ̶̦̋C̴̠̃o̶̧͝r̶̠̾r̵͇̈́ǘ̸͎p̸̀ͅẗ̴͚́ì̷̳o̸̭͝n̶̡̈́",
    },
    {
        "name": "html_markup_injection",
        "description": "Unescaped HTML tags to ensure UI framework escapes entities safely",
        "value": "<script>alert('XSS')</script><b>Bold</b>&amp;\"'<svg onload=alert(1)>",
    },
    {
        "name": "sql_syntax_injection",
        "description": "SQL special characters in UI input to verify backend sanitization",
        "value": "' OR '1'='1' -- /* drop table users; */ \";",
    },
    {
        "name": "emoji_complex_graphemes",
        "description": "Multi-codepoint composite emojis testing font glyph rendering",
        "value": "👨‍👩‍👧‍👦 🏳️‍⚧️ 🧑🏾‍🚀 🦾 👁️‍🗨️",
    },
]

# 2. Localization & Directional Boundaries (RTL, German compounds, CJK, Vietnamese tones)
BREAK_LOCALIZATION: List[Dict[str, str]] = [
    {
        "name": "rtl_arabic",
        "description": "Right-to-Left Arabic text to test bidirectional layout mirroring",
        "value": "مرحبا بالعالم! هذا اختبار لتخطيط الواجهة من اليمين إلى اليسار.",
    },
    {
        "name": "rtl_hebrew",
        "description": "Right-to-Left Hebrew text with mixed LTR numbers",
        "value": "בדיקת ממשק משתמש בעברית עם מספרים: 12345 וטקست באנגלית ABC.",
    },
    {
        "name": "german_compound_noun",
        "description": "Extremely long German word to test column wrapping",
        "value": "Rindfleischetikettierungsüberwachungsaufgabenübertragungsgesetz",
    },
    {
        "name": "vietnamese_complex_tones",
        "description": "Stacked diacritics testing font vertical metrics and accent collisions",
        "value": "Khảo sát tự động hóa kiểm thử: Độc lập - Tự do - Hạnh phúc (Thuở, Nghĩa, Triệu)",
    },
    {
        "name": "cjk_wide_characters",
        "description": "Full-width East Asian glyphs testing monospace alignment and line breaks",
        "value": "日本語のテスト文字列。全角文字と半角文字の混在チェック：１２３４５ＡＢＣＤＥ。",
    },
]

# 3. Numeric Boundaries & Floating Point Edge Cases
BREAK_NUMBERS: List[Dict[str, Any]] = [
    {
        "name": "max_safe_integer_js",
        "description": "JavaScript Number.MAX_SAFE_INTEGER (2^53 - 1)",
        "value": 9007199254740991,
    },
    {
        "name": "min_safe_integer_js",
        "description": "JavaScript Number.MIN_SAFE_INTEGER -(2^53 - 1)",
        "value": -9007199254740991,
    },
    {
        "name": "int64_max",
        "description": "Signed 64-bit maximum integer (2^63 - 1)",
        "value": 9223372036854775807,
    },
    {
        "name": "extreme_decimal_precision",
        "description": "20-decimal float testing rounding and currency formatting truncation",
        "value": 1234567.12345678901234567890,
    },
    {
        "name": "near_zero_subnormal",
        "description": "Subnormal scientific notation close to zero",
        "value": 1e-15,
    },
    {
        "name": "extreme_large_scientific",
        "description": "Large exponent testing scientific notation formatting",
        "value": 1.7976931348623157e308,
    },
    {
        "name": "zero_and_negative_zero",
        "description": "Zero and boundary float 0.0",
        "value": 0.0,
    },
]

# 4. Viewport Dimensions for Layout Stress Testing
BREAK_VIEWPORTS: List[Dict[str, Any]] = [
    {"name": "mobile_compact_se", "width": 320, "height": 568, "device_scale": 2.0},
    {"name": "mobile_modern_tall", "width": 390, "height": 844, "device_scale": 3.0},
    {"name": "tablet_portrait", "width": 768, "height": 1024, "device_scale": 2.0},
    {"name": "tablet_landscape", "width": 1024, "height": 768, "device_scale": 2.0},
    {"name": "desktop_standard_hd", "width": 1366, "height": 768, "device_scale": 1.0},
    {"name": "desktop_full_hd_standard", "width": 1920, "height": 1080, "device_scale": 1.0},
    {"name": "desktop_ultrawide", "width": 3440, "height": 1440, "device_scale": 1.0},
    {"name": "desktop_4k_extreme", "width": 3840, "height": 2160, "device_scale": 2.0},
]


def get_break_strings() -> List[Dict[str, str]]:
    """Returns extreme string boundaries for text input and layout testing."""
    return list(BREAK_STRINGS)


def get_break_localization() -> List[Dict[str, str]]:
    """Returns bidirectional, CJK, and complex diacritic strings."""
    return list(BREAK_LOCALIZATION)


def get_break_numbers() -> List[Dict[str, Any]]:
    """Returns numerical edge cases and boundary floats."""
    return list(BREAK_NUMBERS)


def get_break_viewports() -> List[Dict[str, Any]]:
    """Returns standard and extreme responsive viewport configurations."""
    return list(BREAK_VIEWPORTS)


def generate_all_break_payloads() -> Dict[str, Any]:
    """Generates the unified break-ui testing catalog."""
    return {
        "version": "1.0.0",
        "source": "Synapse Hub break-ui generator (Emil Kowalski pattern)",
        "categories": {
            "strings": get_break_strings(),
            "localization": get_break_localization(),
            "numbers": get_break_numbers(),
            "viewports": get_break_viewports(),
        },
        "total_cases": (
            len(BREAK_STRINGS)
            + len(BREAK_LOCALIZATION)
            + len(BREAK_NUMBERS)
            + len(BREAK_VIEWPORTS)
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Break-UI Edge-Case Test Data Generator for Synapse Hub")
    parser.add_argument(
        "--category",
        "-c",
        choices=["strings", "localization", "numbers", "viewports", "all"],
        default="all",
        help="Category of edge-case test data to generate (default: all)",
    )
    parser.add_argument("--limit", "-l", type=int, default=0, help="Limit number of items output (0 = all)")
    parser.add_argument("--json", action="store_true", help="Output in machine-readable JSON format")
    args = parser.parse_args()

    catalog = generate_all_break_payloads()

    if args.category == "all":
        data: Any = catalog["categories"]
    else:
        data = catalog["categories"][args.category]
        if args.limit > 0:
            data = data[:args.limit]

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"💥 Break-UI Generator (Category: {args.category})")
        if isinstance(data, dict):
            for cat, items in data.items():
                print(f"\n[{cat.upper()}] ({len(items)} items)")
                for item in items[: (args.limit if args.limit > 0 else len(items))]:
                    val = str(item.get("value", f"{item.get('width')}x{item.get('height')}"))
                    if len(val) > 60:
                        val = val[:57] + "..."
                    print(f"  • {item['name']:<28} : {val}")
        else:
            for item in data:
                val = str(item.get("value", f"{item.get('width')}x{item.get('height')}"))
                if len(val) > 60:
                    val = val[:57] + "..."
                print(f"  • {item['name']:<28} : {val}")


if __name__ == "__main__":
    main()
