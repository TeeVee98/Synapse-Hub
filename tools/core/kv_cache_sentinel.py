#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/core/kv_cache_sentinel.py — Live KV-Cache Telemetry Sentinel & Attention Dilution Guard
----------------------------------------------------------------------------------------------
Enforces Invariant 0.2 & Section 1.4:
  1. Ingests live LLM provider usage records (Anthropic, OpenAI, Gemini, Antigravity Transcripts).
  2. Computes the empirical KV-Cache hit rate: (cache_read_input_tokens / total_input_tokens) * 100.
  3. Audits against synapse.config.json::telemetry.min_kv_cache_hit_rate_pct (threshold: 85.0%).
  4. Triggers alerts on cache misses or attention dilution (< 85%).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import logging
import os
import sys
from typing import Any, Dict, List

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_ROOT = os.path.dirname(_SCRIPT_DIR)
_REPO_ROOT = os.path.abspath(os.path.join(_TOOLS_ROOT, ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.core.provider_usage_adapter import parse_provider_usage

logger = logging.getLogger("kv_cache_sentinel")


@dataclass(frozen=True)
class KVCacheAuditDTO:
    timestamp: str
    provider: str
    model: str
    input_tokens: int
    cached_tokens: int
    cache_hit_rate_pct: float
    min_required_pct: float
    passed: bool
    alert_triggered: bool
    details: str


def load_telemetry_config(repo_root: str = _REPO_ROOT) -> Dict[str, Any]:
    """Loads telemetry thresholds from synapse.config.json."""
    config_path = os.path.join(repo_root, "synapse.config.json")
    default_cfg = {
        "min_kv_cache_hit_rate_pct": 85.0,
        "alert_on_cache_miss": True,
    }
    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("telemetry", default_cfg)
        except Exception as e:
            logger.warning("Failed to load synapse.config.json: %s", e)
    return default_cfg


def evaluate_cache_hit_rate(
    input_tokens: int,
    cached_tokens: int,
    min_pct: float = 85.0,
    provider: str = "unknown",
    model: str = "unknown",
) -> KVCacheAuditDTO:
    """Computes KV cache hit rate and verifies compliance with minimum SLA threshold."""
    if input_tokens <= 0:
        rate = 100.0 if cached_tokens >= 0 else 0.0
    else:
        rate = round((cached_tokens / input_tokens) * 100.0, 2)

    passed = (rate >= min_pct)
    alert = (not passed)

    if passed:
        details = f"KV Cache Hit Rate {rate}% conforms to threshold (>= {min_pct}%)."
    else:
        details = (
            f"ALERT: KV Cache Hit Rate {rate}% is below required SLA ({min_pct}%). "
            f"Attention dilution detected in immutable prefix foundation."
        )

    return KVCacheAuditDTO(
        timestamp=datetime.now(timezone.utc).isoformat(),
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        cached_tokens=cached_tokens,
        cache_hit_rate_pct=rate,
        min_required_pct=min_pct,
        passed=passed,
        alert_triggered=alert,
        details=details,
    )


def audit_provider_usage_payload(payload: Dict[str, Any], repo_root: str = _REPO_ROOT) -> KVCacheAuditDTO:
    """Parses live provider usage payload and evaluates KV-cache efficiency."""
    cfg = load_telemetry_config(repo_root)
    min_pct = float(cfg.get("min_kv_cache_hit_rate_pct", 85.0))

    try:
        record = parse_provider_usage(payload, repo_root=repo_root)
        in_tok = record.provider_reported_input_tokens
        cached_tok = record.provider_cached_tokens or 0
        prov = record.provider
        mod = record.model
    except Exception:
        # Fallback parsing for raw usage structures
        usage = payload.get("usage", payload)
        in_tok = int(usage.get("input_tokens", usage.get("prompt_tokens", 0)))
        cached_tok = int(
            usage.get("cache_read_input_tokens",
            usage.get("prompt_tokens_details", {}).get("cached_tokens",
            usage.get("cached_content_token_count", 0)))
        )
        prov = payload.get("provider", "generic")
        mod = payload.get("model", "generic")

    return evaluate_cache_hit_rate(
        input_tokens=in_tok,
        cached_tokens=cached_tok,
        min_pct=min_pct,
        provider=prov,
        model=mod,
    )


def audit_transcript_file(transcript_path: str, repo_root: str = _REPO_ROOT) -> List[KVCacheAuditDTO]:
    """Audits an Antigravity transcript JSONL file for step-level KV cache utilization."""
    results: List[KVCacheAuditDTO] = []
    if not os.path.isfile(transcript_path):
        return results

    cfg = load_telemetry_config(repo_root)
    min_pct = float(cfg.get("min_kv_cache_hit_rate_pct", 85.0))

    with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                step = json.loads(line_str)
                # Look for token metrics in step
                in_tok = step.get("input_tokens", 0)
                cached_tok = step.get("cache_read_tokens", step.get("cache_read_input_tokens", 0))
                if in_tok > 0:
                    dto = evaluate_cache_hit_rate(
                        input_tokens=in_tok,
                        cached_tokens=cached_tok,
                        min_pct=min_pct,
                        provider="antigravity",
                        model=step.get("model", "unknown"),
                    )
                    results.append(dto)
            except Exception:
                continue
    return results


def record_audit_to_history(dto: KVCacheAuditDTO, repo_root: str = _REPO_ROOT) -> str:
    """Persists audit record to .synapse/telemetry/kv_cache_history.json."""
    telemetry_dir = os.path.join(repo_root, ".synapse", "telemetry")
    os.makedirs(telemetry_dir, exist_ok=True)
    history_file = os.path.join(telemetry_dir, "kv_cache_history.json")

    history = []
    if os.path.isfile(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    history.append(asdict(dto))
    # Keep last 100 records
    history = history[-100:]

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    return history_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Live KV-Cache Telemetry Sentinel")
    parser.add_argument("--record", help="JSON string representing provider response or usage")
    parser.add_argument("--transcript", help="Path to transcript.jsonl file to audit")
    parser.add_argument("--check-latest", action="store_true", help="Audits the most recent session telemetry")
    parser.add_argument("--repo-root", default=_REPO_ROOT, help="Repository root path")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    if args.record:
        try:
            data = json.loads(args.record)
        except Exception as e:
            print(f"Error parsing --record JSON: {e}", file=sys.stderr)
            return 1

        audit = audit_provider_usage_payload(data, repo_root=args.repo_root)
        record_audit_to_history(audit, repo_root=args.repo_root)

        if args.json:
            print(json.dumps(asdict(audit), indent=2))
        else:
            print("======================================================================")
            print("📊 KV-CACHE TELEMETRY AUDIT")
            print("======================================================================")
            print(f"  Provider / Model   : {audit.provider} / {audit.model}")
            print(f"  Input Tokens       : {audit.input_tokens}")
            print(f"  Cached Tokens      : {audit.cached_tokens}")
            print(f"  Cache Hit Rate     : {audit.cache_hit_rate_pct}% (Required >= {audit.min_required_pct}%)")
            print(f"  Audit Status       : {'✅ PASS' if audit.passed else '❌ ALERT: ATTENTION DILUTION'}")
            print(f"  Details            : {audit.details}")
            print("======================================================================")
        return 0 if audit.passed else 1

    if args.transcript:
        audits = audit_transcript_file(args.transcript, repo_root=args.repo_root)
        if args.json:
            print(json.dumps([asdict(a) for a in audits], indent=2))
        else:
            print(f"Audited {len(audits)} steps from {args.transcript}")
            for a in audits:
                print(f"  Step: Hit Rate {a.cache_hit_rate_pct}% -> {'PASS' if a.passed else 'ALERT'}")
        return 0

    # Default check
    cfg = load_telemetry_config(args.repo_root)
    print("======================================================================")
    print("⚡ KV-CACHE TELEMETRY SENTINEL STATUS")
    print("======================================================================")
    print(f"  Configured Min Hit Rate SLA : {cfg.get('min_kv_cache_hit_rate_pct', 85.0)}%")
    print(f"  Alert On Cache Miss         : {cfg.get('alert_on_cache_miss', True)}")
    print("  Ready to ingest IDE live telemetry via --record or --transcript.")
    print("======================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
