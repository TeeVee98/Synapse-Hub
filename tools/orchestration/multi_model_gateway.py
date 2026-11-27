#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/orchestration/multi_model_gateway.py — Opt-In Stdlib HTTP Multi-Provider Gateway
--------------------------------------------------------------------------------------
Zero-SDK Python stdlib (`urllib.request`) execution gateway for Headless CLI/CI across:
  - Google Gemini (`google_genai`)
  - Anthropic Claude (`anthropic_messages`)
  - OpenAI / Codex (`openai_chat`)
  - DeepSeek (`openai_compatible`)
  - Local Ollama / vLLM / LM Studio (`openai_compatible`)

Security & Governance Invariants:
  1. Fail-Closed Offline Default: Refuses network sockets unless `network_opt_in=True`
     or `SYNAPSE_GATEWAY_ENABLED=1` is explicitly set.
  2. Bounded Socket Timeout: Clamps every HTTP request timeout to `<= 30.0s`.
  3. Zero Secret Leakage: Never places API keys in URLs; scrubs Authorization, x-api-key,
     and query key tokens before returning errors or CLI output.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.core.circuit_breaker import resolve_tier_preserving_failover
from tools.core.model_registry import (
    ModelRegistry,
    ModelSpecDTO,
    ProviderFamily,
)
from tools.core.provider_usage_adapter import parse_provider_usage

REDACTION_MASK = "***REDACTED***"
MAX_GATEWAY_TIMEOUT_SEC = 30.0

_SECRET_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE),
    re.compile(r"([?&](?:key|api_key)=)[^&\s\"']+", re.IGNORECASE),
    re.compile(r"((?:x-api-key|x-goog-api-key)\s*[:=]\s*)[A-Za-z0-9._\-]+", re.IGNORECASE),
)

_PROVIDER_BASE_URLS: Dict[ProviderFamily, str] = {
    ProviderFamily.GEMINI: "https://generativelanguage.googleapis.com/v1beta/models",
    ProviderFamily.ANTHROPIC: "https://api.anthropic.com/v1/messages",
    ProviderFamily.OPENAI: "https://api.openai.com/v1/chat/completions",
    ProviderFamily.DEEPSEEK: "https://api.deepseek.com/chat/completions",
}


@dataclass(frozen=True)
class StdlibGatewayRequestDTO:
    model_id: str
    system_prefix: str
    user_prompt: str
    fsm_stage: str = "CODE_SYNTHESIS"
    timeout_sec: float = 30.0
    max_tokens: int = 2048
    thinking_budget: int = 0
    network_opt_in: bool = False


@dataclass(frozen=True)
class StdlibGatewayResponseDTO:
    success: bool
    provider: str
    model_id: str
    content: str
    http_status: int
    failover_attempts: int
    error_code: Optional[str] = None


@dataclass(frozen=True)
class NormalizedToolCallDTO:
    call_id: str
    tool_name: str
    arguments_json: str


@dataclass(frozen=True)
class GatewayStreamChunkDTO:
    delta_text: str
    done: bool
    pruned_by_stop_seq: bool = False
    tool_calls: Tuple[NormalizedToolCallDTO, ...] = ()
    error_code: Optional[str] = None


def scrub_gateway_secrets(text: str, extra_secrets: Tuple[str, ...] = ()) -> str:
    """Masks bearer tokens, API key headers, query keys, and explicit secret values."""
    cleaned = str(text or "")
    for pat in _SECRET_PATTERNS:
        cleaned = pat.sub(rf"\1{REDACTION_MASK}", cleaned)
    for secret in extra_secrets:
        tok = secret.strip()
        if tok:
            cleaned = cleaned.replace(tok, REDACTION_MASK)
    return cleaned


def _resolve_model_spec(model_id: str, registry: ModelRegistry) -> ModelSpecDTO:
    found = registry.get_model(model_id)
    if found is not None:
        return found
    return next(iter(registry.list_models()))


def build_provider_http_request(
    request: StdlibGatewayRequestDTO,
    registry: Optional[ModelRegistry] = None,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    """Builds `(url, headers, json_body)` for the resolved provider without opening sockets."""
    reg = registry or ModelRegistry()
    spec = _resolve_model_spec(request.model_id, reg)
    api_key = os.environ.get(spec.auth_env_var, "").strip()
    eff_thinking = request.thinking_budget if (spec.supports_thinking and request.thinking_budget) else 0
    headers: Dict[str, str] = {"Content-Type": "application/json"}

    if spec.provider == ProviderFamily.GEMINI:
        url = f"{_PROVIDER_BASE_URLS[ProviderFamily.GEMINI]}/{spec.model_id}:generateContent"
        if api_key:
            headers["x-goog-api-key"] = api_key
        gen_cfg: Dict[str, Any] = {"maxOutputTokens": request.max_tokens}
        if eff_thinking:
            gen_cfg["thinkingConfig"] = {"thinkingBudget": eff_thinking}
        body: Dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": request.system_prefix}]},
            "contents": [{"role": "user", "parts": [{"text": request.user_prompt}]}],
            "generationConfig": gen_cfg,
        }
        return url, headers, body

    if spec.provider == ProviderFamily.ANTHROPIC:
        url = _PROVIDER_BASE_URLS[ProviderFamily.ANTHROPIC]
        if api_key:
            headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        body = {
            "model": spec.model_id,
            "max_tokens": request.max_tokens,
            "system": request.system_prefix,
            "messages": [{"role": "user", "content": request.user_prompt}],
        }
        if eff_thinking:
            body["thinking"] = {"type": "enabled", "budget_tokens": eff_thinking}
        return url, headers, body

    if spec.provider == ProviderFamily.LOCAL_OPENAI:
        default_local = str(reg.orchestration_policy.get("local_endpoint_url", "http://127.0.0.1:11434/v1"))
        local_base = os.environ.get("SYNAPSE_LOCAL_LLM_URL", default_local).strip().rstrip("/")
        url = f"{local_base}/chat/completions"
        local_token = os.environ.get("SYNAPSE_LOCAL_API_KEY", "").strip()
        if local_token:
            headers["Authorization"] = f"Bearer {local_token}"
        body = {
            "model": spec.model_id,
            "max_tokens": request.max_tokens,
            "messages": [
                {"role": "system", "content": request.system_prefix},
                {"role": "user", "content": request.user_prompt},
            ],
        }
        return url, headers, body

    url = _PROVIDER_BASE_URLS[spec.provider]
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body = {
        "model": spec.model_id,
        "messages": [
            {"role": "system", "content": request.system_prefix},
            {"role": "user", "content": request.user_prompt},
        ],
    }
    if spec.provider == ProviderFamily.OPENAI:
        body["max_completion_tokens"] = request.max_tokens
    else:
        body["max_tokens"] = request.max_tokens
        body["thinking"] = {"type": "enabled" if eff_thinking else "disabled"}
    return url, headers, body


def _extract_completion_text(payload: Dict[str, Any], provider: ProviderFamily) -> str:
    """Extracts assistant text from Gemini, Anthropic, or OpenAI-compatible JSON responses."""
    if provider == ProviderFamily.GEMINI:
        first_cand = next(iter(payload.get("candidates", ())), {})
        first_part = next(iter(first_cand.get("content", {}).get("parts", ())), {})
        return str(first_part.get("text", ""))
    if provider == ProviderFamily.ANTHROPIC:
        blocks = payload.get("content", ())
        return "".join(str(b.get("text", "")) for b in blocks if isinstance(b, dict))
    first_choice = next(iter(payload.get("choices", ())), {})
    return str(first_choice.get("message", {}).get("content", ""))


def _has_credentials_for_spec(spec: ModelSpecDTO) -> bool:
    return spec.provider == ProviderFamily.LOCAL_OPENAI or bool(os.environ.get(spec.auth_env_var, "").strip())


def _is_gateway_enabled(explicit_flag: bool) -> bool:
    env_val = os.environ.get("SYNAPSE_GATEWAY_ENABLED", "").strip().lower()
    return explicit_flag or env_val in ("1", "true", "yes")


def _invoke_single_candidate(
    cand: ModelSpecDTO,
    base_req: StdlibGatewayRequestDTO,
    reg: ModelRegistry,
    timeout_sec: float,
) -> Tuple[bool, int, str, Optional[str]]:
    """Executes one stdlib HTTP request and returns `(ok, status_code, text_or_err, error_code)`."""
    cand_req = StdlibGatewayRequestDTO(
        model_id=cand.model_id,
        system_prefix=base_req.system_prefix,
        user_prompt=base_req.user_prompt,
        fsm_stage=base_req.fsm_stage,
        timeout_sec=timeout_sec,
        max_tokens=base_req.max_tokens,
        thinking_budget=base_req.thinking_budget,
        network_opt_in=base_req.network_opt_in,
    )
    url, headers, body = build_provider_http_request(cand_req, registry=reg)
    http_req = urllib.request.Request(
        url=url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    secret_val = os.environ.get(cand.auth_env_var, "")
    try:
        with urllib.request.urlopen(http_req, timeout=timeout_sec) as resp:  # nosec B310
            raw_bytes = resp.read()
            status_code = int(getattr(resp, "status", 200))
    except urllib.error.HTTPError as http_err:
        code = int(http_err.code)
        safe_msg = scrub_gateway_secrets(str(http_err), extra_secrets=(secret_val,))
        return False, code, safe_msg, f"HTTP_{code}"
    except (urllib.error.URLError, TimeoutError, OSError) as net_err:
        safe_msg = scrub_gateway_secrets(str(net_err), extra_secrets=(secret_val,))
        return False, 503, safe_msg, "NETWORK_TRANSPORT_ERROR"

    parsed = json.loads(raw_bytes.decode("utf-8", errors="replace"))
    try:
        _usage_rec = parse_provider_usage(parsed, provider_hint=cand.provider.value, model_hint=cand.model_id)
    except ValueError:
        _usage_rec = None
    text = _extract_completion_text(parsed, cand.provider)
    return True, status_code, text, None


def execute_stdlib_gateway_call(
    request: StdlibGatewayRequestDTO,
    available_providers: Optional[Tuple[ProviderFamily, ...]] = None,
) -> StdlibGatewayResponseDTO:
    """Executes opt-in stdlib urllib HTTP call with circuit-breaker failover; refuses network when network_opt_in=False."""
    if not str(request.user_prompt or "").strip():
        return StdlibGatewayResponseDTO(
            success=False,
            provider="none",
            model_id=request.model_id,
            content="",
            http_status=0,
            failover_attempts=0,
            error_code="EMPTY_USER_PROMPT",
        )

    if not _is_gateway_enabled(request.network_opt_in):
        return StdlibGatewayResponseDTO(
            success=False,
            provider="none",
            model_id=request.model_id,
            content="",
            http_status=0,
            failover_attempts=0,
            error_code="GATEWAY_OPT_IN_REQUIRED",
        )

    reg = ModelRegistry()
    initial_spec = _resolve_model_spec(request.model_id, reg)
    failover_tail = resolve_tier_preserving_failover(
        failed_model_id=initial_spec.model_id,
        required_tier=initial_spec.capability_tier,
    )
    raw_chain: List[ModelSpecDTO] = [initial_spec] + failover_tail
    if available_providers is not None:
        allowed = set(available_providers)
        raw_chain = [m for m in raw_chain if m.provider in allowed]

    credentialed_chain = [m for m in raw_chain if _has_credentials_for_spec(m)]
    if not credentialed_chain:
        return StdlibGatewayResponseDTO(
            success=False,
            provider=initial_spec.provider.value,
            model_id=initial_spec.model_id,
            content="",
            http_status=0,
            failover_attempts=0,
            error_code="MISSING_PROVIDER_CREDENTIALS",
        )

    clamped_timeout = min(MAX_GATEWAY_TIMEOUT_SEC, max(1.0, float(request.timeout_sec)))
    attempts = 0
    last_status = 503
    last_err = "FAILOVER_EXHAUSTED"
    last_spec = credentialed_chain[0]

    failed_providers: set[ProviderFamily] = set()
    for cand in credentialed_chain:
        if cand.provider in failed_providers:
            continue
        last_spec = cand
        ok, status_code, text_or_err, err_code = _invoke_single_candidate(
            cand=cand,
            base_req=request,
            reg=reg,
            timeout_sec=clamped_timeout,
        )
        if ok:
            return StdlibGatewayResponseDTO(
                success=True,
                provider=cand.provider.value,
                model_id=cand.model_id,
                content=text_or_err,
                http_status=status_code,
                failover_attempts=attempts,
                error_code=None,
            )
        last_status = status_code
        last_err = err_code or "GATEWAY_CALL_FAILED"
        if status_code not in (429, 500, 502, 503, 504):
            break
        failed_providers.add(cand.provider)
        if not any(rem.provider not in failed_providers for rem in credentialed_chain):
            break
        attempts += 1

    return StdlibGatewayResponseDTO(
        success=False,
        provider=last_spec.provider.value,
        model_id=last_spec.model_id,
        content="",
        http_status=last_status,
        failover_attempts=attempts,
        error_code=last_err,
    )


def _attach_stream_and_tools(
    body: Dict[str, Any],
    url: str,
    provider: ProviderFamily,
    tool_schemas_json: Tuple[str, ...],
) -> Tuple[str, Dict[str, Any]]:
    parsed_tools = [json.loads(s) for s in tool_schemas_json if s.strip()]
    if provider == ProviderFamily.GEMINI:
        if parsed_tools:
            body["tools"] = [{"functionDeclarations": parsed_tools}]
        return f"{url}?alt=sse", body
    body["stream"] = True
    if not parsed_tools:
        return url, body
    if provider == ProviderFamily.ANTHROPIC:
        body["tools"] = [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t.get("parameters", {"type": "object"}),
            }
            for t in parsed_tools
        ]
    else:
        body["tools"] = [{"type": "function", "function": t} for t in parsed_tools]
    return url, body


def _parse_sse_data_line(raw_line: str, provider: ProviderFamily) -> Tuple[str, Tuple[NormalizedToolCallDTO, ...]]:
    cleaned = raw_line.strip()
    if not cleaned.startswith("data:"):
        return "", ()
    data_str = cleaned[5:].strip()
    if data_str in ("", "[DONE]"):
        return "", ()
    try:
        payload = json.loads(data_str)
    except ValueError:
        return "", ()

    if provider == ProviderFamily.GEMINI:
        parts = next(iter(payload.get("candidates", ())), {}).get("content", {}).get("parts", ())
        texts: List[str] = []
        calls: List[NormalizedToolCallDTO] = []
        for part in parts:
            if isinstance(part, dict) and "text" in part:
                texts.append(str(part["text"]))
            if isinstance(part, dict) and isinstance(part.get("functionCall"), dict):
                fn = part["functionCall"]
                calls.append(
                    NormalizedToolCallDTO(
                        call_id=f"gem_{fn['name']}",
                        tool_name=str(fn["name"]),
                        arguments_json=json.dumps(fn.get("args", {})),
                    )
                )
        return "".join(texts), tuple(calls)

    if provider == ProviderFamily.ANTHROPIC:
        ev_type = payload.get("type", "")
        if ev_type == "content_block_start":
            blk = payload.get("content_block") or {}
            if blk.get("type") == "tool_use":
                call = NormalizedToolCallDTO(
                    call_id=str(blk["id"]),
                    tool_name=str(blk["name"]),
                    arguments_json=json.dumps(blk.get("input", {})),
                )
                return "", (call,)
        if ev_type == "content_block_delta":
            return str(payload.get("delta", {}).get("text", "")), ()
        return "", ()

    delta = next(iter(payload.get("choices", ())), {}).get("delta", {})
    delta_text = str(delta.get("content", ""))
    oai_calls = tuple(
        NormalizedToolCallDTO(
            call_id=str(tc.get("id", "")),
            tool_name=str(tc.get("function", {}).get("name", "")),
            arguments_json=str(tc.get("function", {}).get("arguments", "{}")),
        )
        for tc in delta.get("tool_calls", ())
        if isinstance(tc, dict)
    )
    return delta_text, oai_calls


def _consume_sse_response(
    resp: Any,
    provider: ProviderFamily,
    stops_list: List[str],
) -> List[GatewayStreamChunkDTO]:
    """Reads SSE lines from an open response stream and applies stop-sequence truncation."""
    from tools.reasoning.dynamic_budget_engine import DynamicBudgetEngine

    chunks: List[GatewayStreamChunkDTO] = []
    acc_text = ""
    while True:
        raw_bytes = resp.readline()
        if not raw_bytes:
            break
        delta_text, calls = _parse_sse_data_line(raw_bytes.decode("utf-8", errors="replace"), provider)
        if not delta_text and not calls:
            continue
        emitted_text = delta_text
        pruned = False
        if stops_list and delta_text:
            trimmed, hit = DynamicBudgetEngine.detect_partial_stop_sequence(acc_text + delta_text, stops_list)
            emitted_text = trimmed[len(acc_text):]
            acc_text = trimmed
            pruned = hit
        elif delta_text:
            acc_text += delta_text
        chunks.append(
            GatewayStreamChunkDTO(
                delta_text=emitted_text,
                done=pruned,
                pruned_by_stop_seq=pruned,
                tool_calls=calls,
            )
        )
        if pruned:
            return chunks
    chunks.append(GatewayStreamChunkDTO(delta_text="", done=True, pruned_by_stop_seq=False))
    return chunks


def stream_stdlib_gateway_call(
    model_id: str,
    system_prefix: str,
    user_prompt: str,
    stop_sequences: Tuple[str, ...] = (),
    tool_schemas_json: Tuple[str, ...] = (),
    network_opt_in: bool = False,
    timeout_sec: float = 30.0,
) -> List[GatewayStreamChunkDTO]:
    """Executes opt-in stdlib SSE streaming + normalized tool-calling over urllib.request, truncating at stop sequences."""
    if not str(user_prompt or "").strip():
        return [GatewayStreamChunkDTO(delta_text="", done=True, error_code="EMPTY_USER_PROMPT")]
    if not _is_gateway_enabled(network_opt_in):
        return [GatewayStreamChunkDTO(delta_text="", done=True, error_code="GATEWAY_OPT_IN_REQUIRED")]

    reg = ModelRegistry()
    spec = _resolve_model_spec(model_id, reg)
    req_dto = StdlibGatewayRequestDTO(
        model_id=spec.model_id,
        system_prefix=system_prefix,
        user_prompt=user_prompt,
        timeout_sec=min(MAX_GATEWAY_TIMEOUT_SEC, float(timeout_sec)),
        network_opt_in=True,
    )
    url, headers, body = build_provider_http_request(req_dto, registry=reg)
    stream_url, stream_body = _attach_stream_and_tools(body, url, spec.provider, tool_schemas_json)
    http_req = urllib.request.Request(
        url=stream_url,
        data=json.dumps(stream_body).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    stops_list = list(stop_sequences)
    try:
        with urllib.request.urlopen(http_req, timeout=req_dto.timeout_sec) as resp:  # nosec B310
            return _consume_sse_response(resp, spec.provider, stops_list)
    except (urllib.error.URLError, TimeoutError, OSError):
        return [GatewayStreamChunkDTO(delta_text="", done=True, error_code="NETWORK_TRANSPORT_ERROR")]


def main() -> int:
    parser = argparse.ArgumentParser(description="Synapse Hub Opt-In Stdlib Multi-Model HTTP Gateway")
    _a1 = parser.add_argument("--model", default="gemini-4-neon", help="Target model ID from models_manifest.json")
    _a2 = parser.add_argument("--system", default="You are Synapse Hub QA Orchestrator.", help="Static system prefix")
    _a3 = parser.add_argument("--prompt", required=True, help="User prompt payload")
    _a4 = parser.add_argument("--fsm-stage", default="CODE_SYNTHESIS", help="FSM stage label")
    _a5 = parser.add_argument("--max-tokens", type=int, default=1024, help="Max completion tokens")
    _a6 = parser.add_argument("--thinking-budget", type=int, default=0, help="Thinking token budget")
    _a7 = parser.add_argument("--timeout", type=float, default=30.0, help="Socket timeout in seconds (clamped <= 30s)")
    _a8 = parser.add_argument("--enable-network", action="store_true", help="Explicitly opt into live HTTP network call")
    _a9 = parser.add_argument("--dry-run", action="store_true", help="Build wire request preview without opening sockets")
    _a10 = parser.add_argument("--json", action="store_true", help="Output structured JSON")
    args = parser.parse_args()

    req = StdlibGatewayRequestDTO(
        model_id=args.model,
        system_prefix=args.system,
        user_prompt=args.prompt,
        fsm_stage=args.fsm_stage,
        timeout_sec=args.timeout,
        max_tokens=args.max_tokens,
        thinking_budget=args.thinking_budget,
        network_opt_in=bool(args.enable_network),
    )

    if args.dry_run:
        url, headers, body = build_provider_http_request(req)
        redacted_headers = {
            k: (REDACTION_MASK if any(s in k.lower() for s in ("key", "auth")) else v)
            for k, v in headers.items()
        }
        preview = {
            "dry_run": True,
            "model_id": req.model_id,
            "endpoint_url": scrub_gateway_secrets(url),
            "headers": redacted_headers,
            "payload_keys": sorted(body.keys()),
        }
        print(json.dumps(preview, indent=2) if args.json else f"[DRY-RUN] {preview['endpoint_url']}")
        return 0

    resp = execute_stdlib_gateway_call(req)
    out_dict = asdict(resp)
    if args.json:
        print(json.dumps(out_dict, indent=2))
    else:
        print(f"[GATEWAY] success={resp.success} provider={resp.provider} model={resp.model_id} error={resp.error_code}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
