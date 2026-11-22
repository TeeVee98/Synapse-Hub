#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/core/cache_proxy.py — Tier 1 Runtime Context Caching Proxy & Assembler
----------------------------------------------------------------------------
Assembles agent prompts by separating the hash-locked Immutable Anchor Prefix
(Sections 0 through 1.1) from dynamic task suffixes.
Provides output adapters for:
  - Google Gemini Context Caching (`cached_content`)
  - Anthropic Claude Prompt Caching (`cache_control: {"type": "ephemeral"}`)
  - OpenAI Prefix Caching (Deterministic prefix ordering)

Usage:
  python3 tools/core/cache_proxy.py --target AGENTS.md --provider gemini --json
  python3 tools/core/cache_proxy.py --verify-prefix
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

# Enforce UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.core.cache_prefix_enforcer import CachePrefixEnforcer


class ContextCachingProxy:
    """Assembles prompt payloads with deterministic KV-cache prefix guarantees."""

    @classmethod
    def assemble_prompt_payload(
        cls,
        prompt_text: str,
        provider: str = "gemini",
        repo_root: str = _REPO_ROOT
    ) -> Dict[str, Any]:
        """Partitions and packages prompt for specific LLM caching API."""
        partition = CachePrefixEnforcer.partition_prompt(prompt_text, auto_isolate_volatile=True)
        provider_payload = CachePrefixEnforcer.format_provider_caching(partition, provider=provider)

        return {
            "provider": provider,
            "prefix_sha256": partition["prefix_hash"],
            "prefix_tokens": partition["prefix_tokens"],
            "suffix_tokens": partition["suffix_tokens"],
            "is_cache_eligible": partition["is_cache_eligible"],
            "isolated_volatiles": partition["isolated_volatiles"],
            "payload": provider_payload
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Tier 1 Runtime Context Caching Proxy & Assembler")
    parser.add_argument("--target", default=os.path.join(_REPO_ROOT, "AGENTS.md"), help="File to assemble")
    parser.add_argument("--provider", default="gemini", choices=["gemini", "anthropic", "standard"], help="Target LLM provider")
    parser.add_argument("--json", action="store_true", help="Output JSON payload")
    parser.add_argument("--verify-prefix", action="store_true", help="Verify prefix hash stability")
    args = parser.parse_args()

    if not os.path.exists(args.target):
        print(f"Error: Target file not found: {args.target}", file=sys.stderr)
        return 1

    with open(args.target, "r", encoding="utf-8") as f:
        content = f.read()

    res = ContextCachingProxy.assemble_prompt_payload(content, provider=args.provider)

    if args.verify_prefix:
        print(f"Static Prefix Hash (SHA-256): {res['prefix_sha256']}")
        print(f"Prefix Tokens: {res['prefix_tokens']} (Cache Eligible: {res['is_cache_eligible']})")
        if res["isolated_volatiles"]:
            print(f"Isolated Volatiles ({len(res['isolated_volatiles'])}): {res['isolated_volatiles']}")
        return 0

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    print(f"=== Prompt Assembled for Provider: {args.provider.upper()} ===")
    print(f"Static Prefix  : {res['prefix_tokens']:,} tokens (SHA-256: {res['prefix_sha256'][:16]}...)")
    print(f"Dynamic Suffix : {res['suffix_tokens']:,} tokens")
    print(f"Cache Status   : {'OPTIMAL (Cache Active)' if res['is_cache_eligible'] else 'BELOW THRESHOLD'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
