#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/core/provider_usage_adapter.py — Standardized Provider Usage Ingestion & Context Splitter
------------------------------------------------------------------------------------------------
Provides strict boundary enforcement between:
  1. Real LLM provider-reported tokens (OpenAI, Anthropic, Gemini, Antigravity Transcripts).
  2. Static documentation / rule estimates (cl100k_base / heuristic polyglot).
  3. Synthetic micro-workload benchmark tokens.
  4. Avoided filesystem read bytes (I/O footprint, strictly non-token).

Invariants:
  - Zero Guesswork / Zero Interpolation: When live provider usage response is not present,
    provider fields MUST remain None (null).
  - Explicit Provenance: Every record declares measurement_kind, tokenizer/model, version, commit,
    and timestamp.
  - Context Decomposition: Statically estimated skill payloads are subtracted from total provider
    input tokens to accurately isolate the external system prompt, conversation history, and tool schemas.
  - Paired Run Verification: Live reduction claims are strictly guarded and rejected unless BOTH
    baseline and optimized runs originate from real provider-observed responses.
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


from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
import os
import subprocess
from typing import Any, Dict, Optional, Tuple

_logger = logging.getLogger("provider_usage_adapter")
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_repo_version_and_commit(repo_root: Optional[str] = None) -> Tuple[str, str]:
    """Retrieves current hub version from skills_manifest.json and git commit hash."""
    root = repo_root or _REPO_ROOT
    version = "1.0.0"
    manifest_path = os.path.join(root, "skills_manifest.json")
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                version = data.get("version", "1.0.0")
        except (OSError, json.JSONDecodeError, KeyError) as err:
            _logger.debug("Failed to read version from manifest: %s", err)

    commit = "unversioned"
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            stderr=subprocess.DEVNULL,
        )
        commit = out.decode("utf-8").strip()
    except (OSError, subprocess.SubprocessError) as err:
        _logger.debug("Failed to get git commit: %s", err)
        commit = "unversioned"

    return version, commit


@dataclass(frozen=True)
class ProviderUsageRecord:
    """Immutable, audited record of actual live LLM provider usage."""
    provider: str
    model: str
    measurement_kind: str  # Always "provider_observed"
    provider_reported_input_tokens: int
    provider_reported_output_tokens: int
    provider_cached_tokens: Optional[int]
    total_provider_tokens: int
    timestamp: str
    version: str
    commit: str
    raw_usage: Dict[str, Any]

    def __post_init__(self) -> None:
        if self.measurement_kind != "provider_observed":
            raise ValueError(
                f"ProviderUsageRecord requires measurement_kind == 'provider_observed', got {self.measurement_kind!r}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Converts to dictionary representation."""
        return asdict(self)


@dataclass
class TokenMeasurementRecord:
    """Standardized record of token measurements with full provenance metadata."""
    measurement_kind: str  # "provider_observed" | "synthetic_estimate"
    token_count: int
    model_name: str
    encoding: str
    is_fallback: bool
    commit_sha: str
    input_hash: str
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """Converts to dictionary representation."""
        return asdict(self)


def serialize_provider_usage(record: Any) -> Dict[str, Any]:
    """
    Serializes a TokenMeasurementRecord or ProviderUsageRecord into provider usage fields.
    Strictly enforces that synthetic estimates or non-provider-observed measurements
    cannot be serialized into provider billing fields.

    Raises:
        ValueError: If record.measurement_kind != 'provider_observed'.
    """
    kind = getattr(record, "measurement_kind", None)
    if isinstance(record, dict):
        kind = record.get("measurement_kind")

    if kind != "provider_observed":
        raise ValueError(
            f"Cannot serialize non-provider-observed record into provider usage fields: "
            f"measurement_kind={kind!r}"
        )

    if isinstance(record, ProviderUsageRecord):
        return record.to_dict()

    if isinstance(record, TokenMeasurementRecord):
        return {
            "measurement_kind": "provider_observed",
            "provider_reported_input_tokens": record.token_count,
            "provider_reported_output_tokens": 0,
            "provider_cached_tokens": None,
            "total_provider_tokens": record.token_count,
            "model": record.model_name,
            "encoding": record.encoding,
            "is_fallback": record.is_fallback,
            "commit_sha": record.commit_sha,
            "input_hash": record.input_hash,
            "timestamp": record.timestamp,
        }

    if isinstance(record, dict):
        return dict(record)

    raise ValueError(f"Unsupported record type: {type(record).__name__}")


def create_unobserved_provider_record(
    measurement_kind: str = "static_estimate",
    note: str = "No live LLM provider usage observed; fields remain null.",
) -> Dict[str, Any]:
    """
    Returns a standardized dictionary for records where live provider data was not captured.
    Guarantees that provider fields remain strictly None without interpolation.
    """
    version, commit = get_repo_version_and_commit()
    return {
        "measurement_kind": measurement_kind,
        "provider": None,
        "model": None,
        "provider_observed": False,
        "provider_reported_input_tokens": None,
        "provider_reported_output_tokens": None,
        "provider_cached_tokens": None,
        "total_provider_tokens": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "commit": commit,
        "note": note,
    }


def parse_provider_usage(
    response: Dict[str, Any],
    provider_hint: Optional[str] = None,
    model_hint: Optional[str] = None,
    repo_root: Optional[str] = None,
) -> ProviderUsageRecord:
    """
    Parses live provider usage from standard LLM response payloads.
    Supported payloads:
      1. OpenAI / Compatible: {"usage": {"prompt_tokens": ..., "completion_tokens": ..., "prompt_tokens_details": {"cached_tokens": ...}}}
      2. Anthropic: {"usage": {"input_tokens": ..., "output_tokens": ..., "cache_read_input_tokens": ...}}
      3. Google GenAI: {"usage_metadata": {"prompt_token_count": ..., "candidates_token_count": ..., "cached_content_token_count": ...}}
      4. Antigravity transcript step: {"input_tokens": ..., "output_tokens": ..., "cache_read_tokens": ...}
      5. Mock / Test payload: {"provider": ..., "model": ..., "usage": {"input_tokens": ..., ...}}

    Raises:
      ValueError: When no valid provider usage payload is present (refuses to guess).
    """
    if not isinstance(response, dict):
        raise ValueError(f"Expected dict response payload, got {type(response).__name__}")

    version, commit = get_repo_version_and_commit(repo_root)
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Google GenAI (Gemini SDK) format: usage_metadata
    if "usage_metadata" in response and isinstance(response["usage_metadata"], dict):
        um = response["usage_metadata"]
        in_tok = um.get("prompt_token_count")
        out_tok = um.get("candidates_token_count", 0)
        cache_tok = um.get("cached_content_token_count")
        model = response.get("model") or model_hint or "gemini"
        provider = provider_hint or "google"
        if in_tok is not None:
            total = in_tok + out_tok
            return ProviderUsageRecord(
                provider=provider,
                model=model,
                measurement_kind="provider_observed",
                provider_reported_input_tokens=int(in_tok),
                provider_reported_output_tokens=int(out_tok),
                provider_cached_tokens=int(cache_tok) if cache_tok is not None else None,
                total_provider_tokens=total,
                timestamp=now_iso,
                version=version,
                commit=commit,
                raw_usage=um,
            )

    # 2. OpenAI / Anthropic format: usage key
    if "usage" in response and isinstance(response["usage"], dict):
        u = response["usage"]
        model = response.get("model") or model_hint or "unknown_model"

        # OpenAI style: prompt_tokens, completion_tokens
        if "prompt_tokens" in u:
            in_tok = u["prompt_tokens"]
            out_tok = u.get("completion_tokens", 0)
            cache_tok = None
            if "prompt_tokens_details" in u and isinstance(u["prompt_tokens_details"], dict):
                cache_tok = u["prompt_tokens_details"].get("cached_tokens")
            provider = provider_hint or ("openai" if "gpt" in model.lower() else "llm_provider")
            total = u.get("total_tokens", in_tok + out_tok)
            return ProviderUsageRecord(
                provider=provider,
                model=model,
                measurement_kind="provider_observed",
                provider_reported_input_tokens=int(in_tok),
                provider_reported_output_tokens=int(out_tok),
                provider_cached_tokens=int(cache_tok) if cache_tok is not None else None,
                total_provider_tokens=int(total),
                timestamp=now_iso,
                version=version,
                commit=commit,
                raw_usage=u,
            )

        # Anthropic style: input_tokens, output_tokens
        if "input_tokens" in u:
            in_tok = u["input_tokens"]
            out_tok = u.get("output_tokens", 0)
            cache_tok = u.get("cache_read_input_tokens")
            provider = provider_hint or ("anthropic" if "claude" in model.lower() else "llm_provider")
            total = in_tok + out_tok
            return ProviderUsageRecord(
                provider=provider,
                model=model,
                measurement_kind="provider_observed",
                provider_reported_input_tokens=int(in_tok),
                provider_reported_output_tokens=int(out_tok),
                provider_cached_tokens=int(cache_tok) if cache_tok is not None else None,
                total_provider_tokens=total,
                timestamp=now_iso,
                version=version,
                commit=commit,
                raw_usage=u,
            )

    # 3. Direct / Antigravity transcript step format: input_tokens, output_tokens directly in root
    if "input_tokens" in response:
        in_tok = response["input_tokens"]
        out_tok = response.get("output_tokens", 0)
        cache_tok = response.get("cache_read_tokens")
        provider = response.get("provider") or provider_hint or "antigravity"
        model = response.get("model") or model_hint or "gemini"
        total = in_tok + out_tok + (cache_tok or 0)
        return ProviderUsageRecord(
            provider=provider,
            model=model,
            measurement_kind="provider_observed",
            provider_reported_input_tokens=int(in_tok),
            provider_reported_output_tokens=int(out_tok),
            provider_cached_tokens=int(cache_tok) if cache_tok is not None else None,
            total_provider_tokens=int(total),
            timestamp=now_iso,
            version=version,
            commit=commit,
            raw_usage={k: response[k] for k in ("input_tokens", "output_tokens", "cache_read_tokens") if k in response},
        )

    raise ValueError(
        "No valid LLM provider usage metadata found in response. "
        "Synapse Hub refuses to fabricate synthetic numbers as live provider data."
    )


def decompose_prompt_context(
    provider_record: ProviderUsageRecord,
    skill_payload_tokens: int,
    rule_payload_tokens: int = 0,
) -> Dict[str, Any]:
    """
    Separates the statically estimated skill/rule documentation payload from the
    overall provider input tokens to isolate external host system instructions,
    conversation history turns, and provider tool calling schemas.
    """
    if not isinstance(provider_record, ProviderUsageRecord):
        raise TypeError(f"Expected ProviderUsageRecord, got {type(provider_record).__name__}")

    total_in = provider_record.provider_reported_input_tokens
    managed_tokens = skill_payload_tokens + rule_payload_tokens
    external_wrapper = max(0, total_in - managed_tokens)
    ratio = round((managed_tokens / max(1, total_in)) * 100.0, 2)

    return {
        "measurement_kind": "provider_observed_with_decomposition",
        "provider": provider_record.provider,
        "model": provider_record.model,
        "provider_reported_input_tokens": total_in,
        "provider_reported_output_tokens": provider_record.provider_reported_output_tokens,
        "provider_cached_tokens": provider_record.provider_cached_tokens,
        "skill_payload_static_estimated_tokens": skill_payload_tokens,
        "rule_payload_static_estimated_tokens": rule_payload_tokens,
        "total_managed_static_tokens": managed_tokens,
        "external_system_prompt_and_wrapper_tokens": external_wrapper,
        "managed_payload_ratio_pct": ratio,
        "timestamp": provider_record.timestamp,
        "version": provider_record.version,
        "commit": provider_record.commit,
        "disclaimer": (
            "Provider reported input tokens reflect total live API billing usage. "
            "Skill and rule payloads are statically estimated via offline tokenizer and subtracted "
            "to isolate unmanaged host system prompt, user prompt, and provider tool schemas."
        ),
    }


def compare_paired_provider_runs(
    baseline_run: ProviderUsageRecord,
    optimized_run: ProviderUsageRecord,
) -> Dict[str, Any]:
    """
    Computes verified token reduction between two live provider runs.
    Enforces scientific honesty: strictly refuses to claim live provider reduction unless
    BOTH baseline and optimized runs originate from real provider_observed responses.
    """
    if not isinstance(baseline_run, ProviderUsageRecord) or not isinstance(optimized_run, ProviderUsageRecord):
        raise TypeError("Both baseline_run and optimized_run must be verified ProviderUsageRecord instances.")

    if baseline_run.measurement_kind != "provider_observed" or optimized_run.measurement_kind != "provider_observed":
        raise ValueError("Both runs must have measurement_kind == 'provider_observed' to claim live provider reduction.")

    in_saved = baseline_run.provider_reported_input_tokens - optimized_run.provider_reported_input_tokens
    out_saved = baseline_run.provider_reported_output_tokens - optimized_run.provider_reported_output_tokens
    total_saved = baseline_run.total_provider_tokens - optimized_run.total_provider_tokens
    reduction_pct = round((total_saved / max(1, baseline_run.total_provider_tokens)) * 100.0, 2)

    return {
        "verified_provider_savings": True,
        "measurement_kind": "paired_provider_observed",
        "baseline_provider": baseline_run.provider,
        "baseline_model": baseline_run.model,
        "baseline_input_tokens": baseline_run.provider_reported_input_tokens,
        "baseline_output_tokens": baseline_run.provider_reported_output_tokens,
        "baseline_total_tokens": baseline_run.total_provider_tokens,
        "optimized_provider": optimized_run.provider,
        "optimized_model": optimized_run.model,
        "optimized_input_tokens": optimized_run.provider_reported_input_tokens,
        "optimized_output_tokens": optimized_run.provider_reported_output_tokens,
        "optimized_total_tokens": optimized_run.total_provider_tokens,
        "input_tokens_saved": in_saved,
        "output_tokens_saved": out_saved,
        "net_tokens_saved": total_saved,
        "reduction_pct": reduction_pct,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
