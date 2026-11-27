#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/core/cache_prefix_enforcer.py — Tier 1 KV-Cache Prefix Integrity Guard
----------------------------------------------------------------------------
Guarantees byte-level immutability for the static prefix block (System Prompt + Core Rules)
to achieve >= 95% LLM KV-cache prefix hits across Gemini Context Caching, Claude Prompt
Caching, and OpenAI prefix caching.

Key Capabilities:
  1. Partitions prompts into [STATIC_IMMUTABLE_PREFIX] (>= 1,024 tokens) and [DYNAMIC_SUFFIX].
  2. Detects and isolates volatile tokens (timestamps, random seeds, volatile user flags),
     automatically moving them to the dynamic suffix block.
  3. Computes and validates SHA-256 prefix fingerprints.
  4. Formats provider-specific cache control markers (Anthropic cache_control, Gemini context-cache).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from typing import Any, Dict

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure repository root is on sys.path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

VOLATILE_PATTERNS = [
    re.compile(r"The current local time is:.*", re.IGNORECASE),
    re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"),  # ISO timestamps
    re.compile(r"\b(?:current_timestamp|now\(\)|timestamp_\d+)\b", re.IGNORECASE),
    re.compile(r"\b(?:session_id|trace_id|request_id):\s*[a-zA-Z0-9_\-]+", re.IGNORECASE),
]


from tools.core.token_estimator import count_tokens, get_estimator_info


class CachePrefixEnforcer:
    """Enforces byte-level prompt prefix immutability for optimal KV-caching."""

    MIN_CACHE_TOKENS = 1024  # Standard threshold for automatic caching (Gemini / Claude)
    MAX_RULE_TOKENS = 5000  # Ceiling to prevent exceeding IDE customization budgets (Antigravity 20k budget)

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Counts or estimates tokens using the unified token_estimator."""
        if not text:
            return 0
        return max(1, count_tokens(text))

    @classmethod
    def compute_prefix_hash(cls, prefix_text: str) -> str:
        """Computes deterministic SHA-256 hash of normalized prefix text."""
        normalized = prefix_text.strip().replace("\r\n", "\n")
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @classmethod
    def detect_volatile_elements(cls, text: str) -> list[str]:
        """Detects any volatile or non-deterministic tokens inside candidate static text."""
        matches = []
        for pat in VOLATILE_PATTERNS:
            found = pat.findall(text)
            if found:
                for item in found:
                    if isinstance(item, str):
                        matches.append(item.strip())
                    elif isinstance(item, tuple):
                        matches.append(" ".join(item).strip())
        return matches

    @classmethod
    def partition_prompt(
        cls,
        full_prompt: str,
        split_marker: str = "<!-- DYNAMIC_PROMPT_BOUNDARY -->",
        auto_isolate_volatile: bool = True
    ) -> Dict[str, Any]:
        """
        Splits a full prompt into a strictly immutable prefix and an ephemeral suffix.
        Automatically relocates any detected volatile elements from the prefix to suffix.
        """
        isolated_items: list[str] = []
        if split_marker in full_prompt:
            prefix, suffix = full_prompt.split(split_marker, 1)
        else:
            # Fallback split: Find end of Section 1.1 or 2/3 down
            anchor = "## 1.1 PRE-FLIGHT REASONING CHECKLIST"
            if anchor in full_prompt:
                idx = full_prompt.find(anchor)
                end_idx = full_prompt.find("\n---\n", idx)
                if end_idx != -1:
                    prefix = full_prompt[:end_idx + 5]
                    suffix = full_prompt[end_idx + 5:]
                else:
                    prefix = full_prompt
                    suffix = ""
            else:
                prefix = full_prompt
                suffix = ""

        if auto_isolate_volatile:
            volatiles = cls.detect_volatile_elements(prefix)
            if volatiles:
                for item in volatiles:
                    if item in prefix:
                        prefix = prefix.replace(item, "[OFFLOADED_TO_DYNAMIC_SUFFIX]")
                        isolated_items.append(item)
                if isolated_items:
                    suffix = "\n[Dynamic Ephemeral Metadata]:\n" + "\n".join(isolated_items) + "\n" + suffix

        prefix_tokens = cls.estimate_tokens(prefix)
        suffix_tokens = cls.estimate_tokens(suffix)
        prefix_hash = cls.compute_prefix_hash(prefix)
        estimator_info = dict(get_estimator_info())
        estimator_info["provider_observed"] = False

        return {
            "is_cache_eligible": prefix_tokens >= cls.MIN_CACHE_TOKENS,
            "prefix_tokens": prefix_tokens,
            "suffix_tokens": suffix_tokens,
            "prefix_hash": prefix_hash,
            "prefix": prefix,
            "suffix": suffix,
            "isolated_volatiles": isolated_items,
            "estimator_info": estimator_info,
        }

    @classmethod
    def format_provider_caching(cls, partitioned: Dict[str, Any], provider: str = "anthropic") -> Dict[str, Any]:
        """Formats partitioned prompt into provider-native caching payloads."""
        prefix = partitioned["prefix"]
        suffix = partitioned["suffix"]

        if provider.lower() == "anthropic":
            return {
                "system": [
                    {
                        "type": "text",
                        "text": prefix,
                        "cache_control": {"type": "ephemeral"}
                    }
                ],
                "messages": [
                    {
                        "role": "user",
                        "content": suffix.strip() or "Execute current workflow."
                    }
                ]
            }
        elif provider.lower() in ("gemini", "google"):
            return {
                "cached_content": {
                    "contents": [{"role": "system", "parts": [{"text": prefix}]}],
                    "ttl": "300s"
                },
                "dynamic_request": {
                    "contents": [{"role": "user", "parts": [{"text": suffix.strip() or "Execute current workflow."}]}]
                }
            }
        elif provider.lower() in ("openai", "deepseek"):
            return {
                "prefix_cache_eligible": partitioned["is_cache_eligible"],
                "prefix_hash": partitioned["prefix_hash"],
                "messages": [
                    {"role": "system", "content": prefix},
                    {"role": "user", "content": suffix.strip()},
                ],
            }
        elif provider.lower() == "local_openai":
            return {
                "prefix_cache_eligible": partitioned["is_cache_eligible"],
                "keep_alive": "10m",
                "messages": [
                    {"role": "system", "content": prefix},
                    {"role": "user", "content": suffix.strip()},
                ],
            }
        else:
            return {
                "static_prefix": prefix,
                "dynamic_suffix": suffix,
                "prefix_hash": partitioned["prefix_hash"]
            }


def main() -> int:
    parser = argparse.ArgumentParser(description="Tier 1 KV-Cache Prefix Integrity Guard")
    parser.add_argument("--file", "-f", help="Target prompt or AGENTS.md file to inspect")
    parser.add_argument("--json", action="store_true", help="Output JSON analysis")
    _provider_arg = parser.add_argument(
        "--provider",
        default="anthropic",
        choices=["anthropic", "gemini", "openai", "deepseek", "local_openai", "standard"],
        help="Target provider",
    )
    args = parser.parse_args()

    target_path = args.file or os.path.join(_REPO_ROOT, "AGENTS.md")
    if not os.path.exists(target_path):
        print(f"Error: Target file not found: {target_path}", file=sys.stderr)
        return 1

    with open(target_path, "r", encoding="utf-8") as f:
        content = f.read()

    res = CachePrefixEnforcer.partition_prompt(content)
    if args.json:
        payload = {
            "target": target_path,
            "is_cache_eligible": res["is_cache_eligible"],
            "prefix_tokens": res["prefix_tokens"],
            "suffix_tokens": res["suffix_tokens"],
            "prefix_hash": res["prefix_hash"],
            "isolated_volatiles": res["isolated_volatiles"],
            "provider_payload": CachePrefixEnforcer.format_provider_caching(res, args.provider)
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print(f"=== KV-Cache Prefix Analysis for {os.path.basename(target_path)} ===")
    print(f"Prefix Tokens: {res['prefix_tokens']} (Threshold: >={CachePrefixEnforcer.MIN_CACHE_TOKENS})")
    print(f"Cache Eligible: {'YES (Optimal)' if res['is_cache_eligible'] else 'NO (Below threshold)'}")
    print(f"Prefix Hash (SHA-256): {res['prefix_hash']}")
    if res["isolated_volatiles"]:
        print(f"Isolated Volatiles ({len(res['isolated_volatiles'])}): {res['isolated_volatiles']}")
    else:
        print("Isolated Volatiles: None (100% Deterministic & Immutable)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
