#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/reasoning/telegraphic_enforcer.py — Tier 5 Telegraphic Reasoning Enforcer
--------------------------------------------------------------------------------
Detects and purges conversational fluff, pleasantries, and verbose phrasing from AI
thoughts and direct outputs. Enforces concise keyword and arrow-based telegraphic notation.

Targeted Fluff:
  - Greetings: "Xin chào", "Hello", "Chào bạn", "Tôi hy vọng bạn khỏe"
  - Apologies: "Tôi xin lỗi", "I apologize", "Rất tiếc về sự cố này"
  - Filler lead-ins: "Dưới đây là kết quả của việc...", "Chắc chắn rồi, tôi sẽ...",
    "Sure thing! Here is what I did...", "Hope this helps!"
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import List, Tuple

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

FLUFF_PATTERNS = [
    re.compile(r"^(?:xin\s+chào[^\n.!?]*[.!?]?|chào\s+bạn[^\n.!?]*[.!?]?|hello\s+there[^\n.!?]*[.!?]?|hi\s+there[^\n.!?]*[.!?]?|sure\s+thing[^\n.!?]*[.!?]?)\s*", re.IGNORECASE | re.MULTILINE),
    re.compile(r"(?:tôi\s+rất\s+vui\s+được\s+hỗ\s+trợ[^\n.!?]*[.!?]?|i'm\s+happy\s+to\s+help[^\n.!?]*[.!?]?)\s*", re.IGNORECASE),
    re.compile(r"(?:dưới\s+đây\s+là\s+kết\s+quả[^\n.!?:]*[:.]?|here\s+is\s+the\s+result[^\n.!?:]*[:.]?|as\s+requested[^\n.!?:]*[:.]?)\s*", re.IGNORECASE),
    re.compile(r"(?:hy\s+vọng\s+điều\s+này\s+giúp\s+ích[^\n.!?]*[.!?]?|hope\s+this\s+helps[^\n.!?]*[.!?]?|let\s+me\s+know\s+if\s+you\s+need[^\n.!?]*[.!?]?)\s*", re.IGNORECASE),
    re.compile(r"(?:tôi\s+rất\s+xin\s+lỗi[^\n.!?]*[.!?]?|i\s+sincerely\s+apologize[^\n.!?]*[.!?]?)\s*", re.IGNORECASE),
]


class TelegraphicEnforcer:
    """Detects and strips verbose conversational filler to minimize output tokens."""

    @classmethod
    def audit_text(cls, text: str) -> Tuple[bool, List[str]]:
        """Audits text for conversational fluff violations."""
        found = []
        for pat in FLUFF_PATTERNS:
            matches = pat.findall(text)
            if matches:
                found.extend([m.strip() for m in matches if m.strip()])
        return len(found) == 0, found

    @classmethod
    def purify_to_telegraphic(cls, text: str) -> Tuple[str, int]:
        """Strips conversational fluff and transforms verbose lead-ins into telegraphic form."""
        original_len = len(text)
        purified = text

        for pat in FLUFF_PATTERNS:
            purified = pat.sub("", purified)

        # Clean multiple newlines and spaces
        purified = re.sub(r"\n{3,}", "\n\n", purified).strip()
        tokens_saved = max(0, int((original_len - len(purified)) / 3.8))

        return purified, tokens_saved


def main() -> int:
    parser = argparse.ArgumentParser(description="Tier 5 Telegraphic Reasoning Enforcer")
    parser.add_argument("--demo", action="store_true", help="Run telegraphic purification demo")
    parser.add_argument("--text", help="Raw text to audit")
    args = parser.parse_args()

    if args.demo:
        sample = (
            "Xin chào bạn! Tôi rất vui được hỗ trợ bạn hôm nay.\n\n"
            "Chắc chắn rồi, dưới đây là kết quả của việc phân tích log hệ thống:\n"
            "- Step 1: Kiểm tra cấu hình -> OK\n"
            "- Step 2: Chạy kiểm thử -> FAILED ở line 42 do NullPointerException.\n\n"
            "Hy vọng điều này giúp ích cho bạn! Let me know if you need any further assistance!"
        )
        clean, saved = TelegraphicEnforcer.purify_to_telegraphic(sample)
        print("=== Demo Telegraphic Reasoning Purification ===")
        print("--- Original Output (Conversational Fluff) ---")
        print(sample)
        print(f"\n--- Purified Output (Telegraphic Syntax, Saved ~{saved} tokens) ---")
        print(clean)
        return 0

    if args.text:
        is_clean, violations = TelegraphicEnforcer.audit_text(args.text)
        if is_clean:
            print("PASS: Text is strictly telegraphic and fluff-free.")
            return 0
        else:
            print(f"FAIL: Detected conversational fluff ({len(violations)}): {violations}", file=sys.stderr)
            return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
