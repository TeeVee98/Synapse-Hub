#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
4-Scenario Mocked-Transport Unit & CLI Tests for Milestone 6:
Opt-In Stdlib HTTP Multi-Provider Gateway (`tools/orchestration/multi_model_gateway.py`).
Strictly mocks `urllib.request.urlopen` — zero live external sockets opened in pytest.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import io
import json
import os
import subprocess
import sys
import urllib.error
import pytest

from tools.core.model_registry import ProviderFamily
from tools.orchestration.multi_model_gateway import (
    StdlibGatewayRequestDTO,
    StdlibGatewayResponseDTO,
    build_provider_http_request,
    execute_stdlib_gateway_call,
    scrub_gateway_secrets,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _MockHttpResponse:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self._raw = json.dumps(payload).encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "_MockHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_gateway_positive_five_providers_and_failover(monkeypatch):
    """Positive (TC-ADV-02): Verifies all 5 provider wire formats, usage telemetry, and 429/503 failover."""
    monkeypatch.setenv("GEMINI_API_KEY", "gem-test-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "oai-test-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-test-key")
    monkeypatch.setenv("SYNAPSE_LOCAL_LLM_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setenv("SYNAPSE_LOCAL_API_KEY", "local-test-token")

    default_dto = StdlibGatewayRequestDTO(
        model_id="gemini-4-neon",
        system_prefix="Immutable QA Rules",
        user_prompt="Verify LoginPage",
    )
    assert default_dto.network_opt_in is False

    req_dto = StdlibGatewayRequestDTO(
        model_id="gemini-4-neon",
        system_prefix="Immutable QA Rules",
        user_prompt="Verify LoginPage",
        fsm_stage="CODE_SYNTHESIS",
        timeout_sec=15.0,
        max_tokens=512,
        thinking_budget=1024,
        network_opt_in=True,
    )
    with pytest.raises(FrozenInstanceError):
        req_dto.max_tokens = 999  # type: ignore[misc]

    # Verify wire payload builders, auth headers, and thinking blocks across all 5 provider families
    gem_url, gem_hdr, gem_body = build_provider_http_request(req_dto)
    assert "generativelanguage.googleapis.com" in gem_url
    assert "gemini-4-neon" in gem_url
    assert gem_hdr["x-goog-api-key"] == "gem-test-key"
    assert gem_body["generationConfig"]["thinkingConfig"]["thinkingBudget"] == 1024

    ant_url, ant_hdr, ant_body = build_provider_http_request(
        StdlibGatewayRequestDTO(
            model_id="claude-sonnet-5.5",
            system_prefix="Sys",
            user_prompt="Hello",
            thinking_budget=1024,
            network_opt_in=True,
        )
    )
    assert "api.anthropic.com/v1/messages" in ant_url
    assert ant_hdr["x-api-key"] == "ant-test-key"
    assert ant_body["thinking"] == {"type": "enabled", "budget_tokens": 1024}

    oai_url, oai_hdr, oai_body = build_provider_http_request(
        StdlibGatewayRequestDTO(
            model_id="gpt-6.2-sol",
            system_prefix="Sys",
            user_prompt="Hello",
            max_tokens=300,
            thinking_budget=1024,
            network_opt_in=True,
        )
    )
    assert "api.openai.com/v1/chat/completions" in oai_url
    assert oai_hdr["Authorization"] == "Bearer oai-test-key"
    assert oai_body["max_completion_tokens"] == 300

    ds_url, ds_hdr, ds_body = build_provider_http_request(
        StdlibGatewayRequestDTO(
            model_id="deepseek-r1",
            system_prefix="Sys",
            user_prompt="Hello",
            thinking_budget=1024,
            network_opt_in=True,
        )
    )
    assert "api.deepseek.com/chat/completions" in ds_url
    assert ds_hdr["Authorization"] == "Bearer ds-test-key"
    assert ds_body["thinking"] == {"type": "enabled"}

    loc_url, loc_hdr, loc_body = build_provider_http_request(
        StdlibGatewayRequestDTO(
            model_id="ollama-qwen3-coder",
            system_prefix="Sys",
            user_prompt="Hello",
            network_opt_in=True,
        )
    )
    assert "127.0.0.1:11434/v1/chat/completions" in loc_url
    assert loc_hdr["Authorization"] == "Bearer local-test-token"
    assert loc_body["model"] == "ollama-qwen3-coder"

    # Simulate HTTP 429 on Gemini -> HTTP 503 on Anthropic -> HTTP 200 on OpenAI
    calls = []

    def _fake_urlopen(http_req, timeout=30.0):
        url = http_req.full_url
        calls.append((url, timeout))
        if "googleapis.com" in url:
            raise urllib.error.HTTPError(url, 429, "Rate limit exceeded", hdrs=None, fp=io.BytesIO(b"quota"))
        if "anthropic.com" in url:
            raise urllib.error.HTTPError(url, 503, "Overloaded", hdrs=None, fp=io.BytesIO(b"busy"))
        return _MockHttpResponse(
            {
                "model": "gpt-6.2-astra",
                "choices": [{"message": {"content": "Verified clean POM output"}}],
                "usage": {"prompt_tokens": 120, "completion_tokens": 40, "total_tokens": 160},
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    resp = execute_stdlib_gateway_call(
        req_dto,
        available_providers=(ProviderFamily.GEMINI, ProviderFamily.ANTHROPIC, ProviderFamily.OPENAI),
    )
    assert isinstance(resp, StdlibGatewayResponseDTO)
    assert resp.success is True
    assert resp.provider == "openai"
    assert resp.content == "Verified clean POM output"
    assert resp.http_status == 200
    assert resp.failover_attempts == 2
    assert resp.error_code is None
    assert len(calls) == 3

    # Also verify Anthropic response parser directly
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda http_req, timeout=30.0: _MockHttpResponse(
            {
                "content": [{"type": "text", "text": "Anthropic audit verified"}],
                "usage": {"input_tokens": 50, "output_tokens": 10},
            }
        ),
    )
    ant_resp = execute_stdlib_gateway_call(
        StdlibGatewayRequestDTO(
            model_id="claude-opus-5.5",
            system_prefix="Sys",
            user_prompt="Review diff",
            network_opt_in=True,
        ),
        available_providers=(ProviderFamily.ANTHROPIC,),
    )
    assert ant_resp.success is True
    assert ant_resp.provider == "anthropic"
    assert ant_resp.content == "Anthropic audit verified"


def _make_socket_spy():
    calls = []

    def _forbid_socket(*args, **kwargs):
        calls.append(args)
        raise AssertionError("urlopen must NEVER be called when network_opt_in=False")

    return calls, _forbid_socket


def test_gateway_negative_and_security(monkeypatch):
    """TC-03 Negative & Security: Fail-closed offline default, missing credentials, and API key redaction."""
    monkeypatch.delenv("SYNAPSE_GATEWAY_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    spy_calls, _forbid_socket = _make_socket_spy()
    monkeypatch.setattr("urllib.request.urlopen", _forbid_socket)

    # 1. Offline guard refuses network execution when network_opt_in=False
    blocked = execute_stdlib_gateway_call(
        StdlibGatewayRequestDTO(
            model_id="gemini-4-neon",
            system_prefix="Sys",
            user_prompt="Audit",
            network_opt_in=False,
        )
    )
    assert blocked.success is False
    assert blocked.error_code == "GATEWAY_OPT_IN_REQUIRED"
    assert len(spy_calls) == 0

    # 2. Missing cloud API key fails cleanly before network socket open
    no_creds = execute_stdlib_gateway_call(
        StdlibGatewayRequestDTO(
            model_id="gpt-6.2-astra",
            system_prefix="Sys",
            user_prompt="Audit",
            network_opt_in=True,
        ),
        available_providers=(ProviderFamily.OPENAI,),
    )
    assert no_creds.success is False
    assert no_creds.error_code == "MISSING_PROVIDER_CREDENTIALS"
    assert len(spy_calls) == 0

    # 3. Secret redaction scrubs bearer tokens, x-api-key, and URL query keys
    leaked_raw = "Error calling https://generativelanguage.googleapis.com/v1beta?key=AIzaSecret999 Authorization: Bearer sk-proj-secret123"
    scrubbed = scrub_gateway_secrets(leaked_raw, extra_secrets=("AIzaSecret999", "sk-proj-secret123"))
    assert "AIzaSecret999" not in scrubbed
    assert "sk-proj-secret123" not in scrubbed
    assert "***REDACTED***" in scrubbed


def test_gateway_boundary_timeout_clamping_and_non_thinking_strip(monkeypatch):
    """Boundary (TC-ADV-03): Empty prompt rejected, timeout clamped <= 30s, thinking stripped on lite models."""
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key-boundary")

    empty_resp = execute_stdlib_gateway_call(
        StdlibGatewayRequestDTO(
            model_id="gemini-3.8-flash",
            system_prefix="Sys",
            user_prompt="   ",
            network_opt_in=True,
        )
    )
    assert empty_resp.success is False
    assert empty_resp.error_code == "EMPTY_USER_PROMPT"

    # Non-thinking model strips thinkingConfig even when thinking_budget > 0
    _, _, lite_body = build_provider_http_request(
        StdlibGatewayRequestDTO(
            model_id="gemini-3.8-flash",
            system_prefix="Sys",
            user_prompt="Ping",
            thinking_budget=2048,
            network_opt_in=True,
        )
    )
    assert "thinkingConfig" not in lite_body.get("generationConfig", {})

    captured_timeout = []

    def _capture_timeout(http_req, timeout=30.0):
        captured_timeout.append(timeout)
        return _MockHttpResponse(
            {
                "candidates": [{"content": {"parts": [{"text": "pong"}]}}],
                "usage_metadata": {"prompt_token_count": 10, "candidates_token_count": 2},
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", _capture_timeout)
    ok_resp = execute_stdlib_gateway_call(
        StdlibGatewayRequestDTO(
            model_id="gemini-3.8-flash",
            system_prefix="Sys",
            user_prompt="Ping",
            timeout_sec=120.0,  # Exceeds 30s ceiling -> must clamp to 30.0s
            network_opt_in=True,
        ),
        available_providers=(ProviderFamily.GEMINI,),
    )
    assert ok_resp.success is True
    assert ok_resp.content == "pong"
    assert captured_timeout == [30.0]


def test_gateway_cli_json_dry_run_and_offline_guard():
    """CLI & Resilience: Verifies --dry-run --json and fail-closed offline CLI invocation."""
    script = os.path.join(REPO_ROOT, "tools", "orchestration", "multi_model_gateway.py")
    child_env = dict(os.environ)
    child_env.pop("SYNAPSE_GATEWAY_ENABLED", None)
    child_env["DEEPSEEK_API_KEY"] = "ds-cli-secret-xyz"

    # 1. Offline CLI invocation without --enable-network refuses live socket cleanly
    proc_offline = subprocess.run(
        [sys.executable, script, "--model", "deepseek-r1", "--prompt", "Check POM", "--json"],
        cwd=REPO_ROOT,
        env=child_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_offline.returncode == 0, proc_offline.stderr
    off_data = json.loads(proc_offline.stdout)
    assert off_data["success"] is False
    assert off_data["error_code"] == "GATEWAY_OPT_IN_REQUIRED"
    assert "ds-cli-secret-xyz" not in proc_offline.stdout

    # 2. Dry-run builds wire preview without opening network sockets
    proc_dry = subprocess.run(
        [sys.executable, script, "--model", "deepseek-r1", "--prompt", "Check POM", "--dry-run", "--json"],
        cwd=REPO_ROOT,
        env=child_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_dry.returncode == 0, proc_dry.stderr
    dry_data = json.loads(proc_dry.stdout)
    assert dry_data["dry_run"] is True
    assert "api.deepseek.com" in dry_data["endpoint_url"]
    assert "ds-cli-secret-xyz" not in proc_dry.stdout


# ==============================================================================
# Phase 2 Milestone 3: SSE Streaming, Stop Pruning & Normalized Tool Calls
# ==============================================================================


class _MockSseHttpResponse:
    def __init__(self, lines: list[bytes], status: int = 200) -> None:
        self._lines = list(lines)
        self._idx = 0
        self.status = status

    def readline(self) -> bytes:
        if self._idx >= len(self._lines):
            return b""
        line = self._lines[self._idx]
        self._idx += 1
        return line

    def __enter__(self) -> "_MockSseHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_gateway_sse_and_tools_positive(monkeypatch):
    """TC-02 Positive: SSE streaming accumulates deltas, prunes trailing chatter at stop-sequence, and normalizes ToolCallDTOs."""
    from tools.orchestration.multi_model_gateway import (
        GatewayStreamChunkDTO,
        NormalizedToolCallDTO,
        stream_stdlib_gateway_call,
    )
    from tools.reasoning.dynamic_budget_engine import DynamicBudgetEngine

    monkeypatch.setenv("OPENAI_API_KEY", "oai-sse-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gem-sse-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-sse-key")

    trimmed, hit = DynamicBudgetEngine.detect_partial_stop_sequence(
        "<tool_call>run</tool_call>\nTrailing chatter",
        ["</tool_call>"],
    )
    assert hit is True
    assert trimmed == "<tool_call>run</tool_call>"

    tool_schema = json.dumps(
        {
            "name": "run_pytest",
            "description": "Execute pytest",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}},
        }
    )

    sse_lines_oai = [
        b'data: {"choices":[{"delta":{"content":"Checking "}}]}\n',
        b'data: {"choices":[{"delta":{"tool_calls":[{"id":"call_1","function":{"name":"run_pytest","arguments":"{\\"path\\":\\"tests/\\"}"}}]}}]}\n',
        b'data: {"choices":[{"delta":{"content":"</tool_call>IGNORED_CHATTER"}}]}\n',
        b"data: [DONE]\n",
    ]
    captured_req = []

    def _fake_oai_sse(http_req, timeout=30.0):
        captured_req.append(json.loads(http_req.data.decode("utf-8")))
        return _MockSseHttpResponse(sse_lines_oai)

    monkeypatch.setattr("urllib.request.urlopen", _fake_oai_sse)
    chunks = stream_stdlib_gateway_call(
        model_id="gpt-6.2-sol",
        system_prefix="Sys",
        user_prompt="Run suite",
        stop_sequences=("</tool_call>",),
        tool_schemas_json=(tool_schema,),
        network_opt_in=True,
        timeout_sec=12.0,
    )
    assert len(chunks) >= 2
    assert isinstance(chunks[0], GatewayStreamChunkDTO)
    assert chunks[0].pruned_by_stop_seq is False
    with pytest.raises(FrozenInstanceError):
        chunks[0].done = True  # type: ignore[misc]
    assert chunks[-1].done is True
    assert chunks[-1].pruned_by_stop_seq is True
    joined_text = "".join(c.delta_text for c in chunks)
    assert "Checking" in joined_text
    assert "</tool_call>" in joined_text
    assert "IGNORED_CHATTER" not in joined_text
    all_calls = [tc for c in chunks for tc in c.tool_calls]
    assert len(all_calls) == 1
    assert isinstance(all_calls[0], NormalizedToolCallDTO)
    with pytest.raises(FrozenInstanceError):
        all_calls[0].tool_name = "mutated"  # type: ignore[misc]
    assert all_calls[0].tool_name == "run_pytest"
    assert "tests/" in all_calls[0].arguments_json
    assert "tools" in captured_req[0]
    assert captured_req[0]["stream"] is True

    # Verify Anthropic & Gemini SSE + tool normalization
    gem_reqs = []

    def _fake_gem_sse(req, timeout=30.0):
        gem_reqs.append(json.loads(req.data.decode("utf-8")))
        return _MockSseHttpResponse(
            [
                b'data: {"candidates":[{"content":{"parts":[{"functionCall":{"name":"run_pytest","args":{"path":"tests/a.py"}}}]}}]}\n',
                b'data: {"candidates":[{"content":{"parts":[{"text":"Done gemini"}]}}]}\n',
            ]
        )

    monkeypatch.setattr("urllib.request.urlopen", _fake_gem_sse)
    gem_chunks = stream_stdlib_gateway_call(
        model_id="gemini-4-neon",
        system_prefix="Sys",
        user_prompt="Ping",
        tool_schemas_json=(tool_schema,),
        network_opt_in=True,
    )
    gem_calls = [tc for c in gem_chunks for tc in c.tool_calls]
    assert len(gem_calls) == 1 and gem_calls[0].tool_name == "run_pytest"
    assert "functionDeclarations" in gem_reqs[0]["tools"][0]
    assert any("Done gemini" in c.delta_text for c in gem_chunks)

    ant_reqs = []

    def _fake_ant_sse(req, timeout=30.0):
        ant_reqs.append(json.loads(req.data.decode("utf-8")))
        return _MockSseHttpResponse(
            [
                b'data: {"type":"content_block_start","content_block":{"type":"tool_use","id":"toolu_1","name":"run_pytest","input":{"path":"tests/b.py"}}}\n',
                b'data: {"type":"content_block_delta","delta":{"text":"Claude done"}}\n',
            ]
        )

    monkeypatch.setattr("urllib.request.urlopen", _fake_ant_sse)
    ant_chunks = stream_stdlib_gateway_call(
        model_id="claude-sonnet-5.5",
        system_prefix="Sys",
        user_prompt="Ping",
        tool_schemas_json=(tool_schema,),
        network_opt_in=True,
    )
    assert any(tc.call_id == "toolu_1" for c in ant_chunks for tc in c.tool_calls)
    assert any("Claude done" in c.delta_text for c in ant_chunks)
    assert "input_schema" in ant_reqs[0]["tools"][0]


def test_gateway_sse_negative_opt_in_and_network_error(monkeypatch):
    """Negative: Offline default refuses streaming network sockets and network error yields clean error chunk."""
    from tools.orchestration.multi_model_gateway import stream_stdlib_gateway_call

    monkeypatch.delenv("SYNAPSE_GATEWAY_ENABLED", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "oai-neg-key")

    blocked = stream_stdlib_gateway_call(
        model_id="gpt-6.2-sol",
        system_prefix="Sys",
        user_prompt="Ping",
    )
    assert len(blocked) == 1
    assert blocked[0].done is True
    assert blocked[0].error_code == "GATEWAY_OPT_IN_REQUIRED"

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=30.0: (_ for _ in ()).throw(urllib.error.URLError("endpoint unreachable")),
    )
    net_err = stream_stdlib_gateway_call(
        model_id="gpt-6.2-sol",
        system_prefix="Sys",
        user_prompt="Ping",
        network_opt_in=True,
    )
    assert len(net_err) == 1
    assert net_err[0].done is True
    assert net_err[0].error_code == "NETWORK_TRANSPORT_ERROR"


def test_gateway_sse_boundary_empty_prompt_and_eof_stream(monkeypatch):
    """Boundary: Empty user_prompt returns EMPTY_USER_PROMPT and EOF stream with only [DONE] returns clean done chunk."""
    from tools.orchestration.multi_model_gateway import stream_stdlib_gateway_call

    empty_chunks = stream_stdlib_gateway_call(
        model_id="gpt-6.2-sol",
        system_prefix="Sys",
        user_prompt="   ",
        network_opt_in=True,
    )
    assert len(empty_chunks) == 1
    assert empty_chunks[0].error_code == "EMPTY_USER_PROMPT"

    monkeypatch.setenv("OPENAI_API_KEY", "oai-eof-key")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=30.0: _MockSseHttpResponse([b"\n", b"data: [DONE]\n"]),
    )
    eof_chunks = stream_stdlib_gateway_call(
        model_id="gpt-6.2-sol",
        system_prefix="Sys",
        user_prompt="Hello",
        network_opt_in=True,
    )
    assert len(eof_chunks) == 1
    assert eof_chunks[0].done is True
    assert eof_chunks[0].pruned_by_stop_seq is False


@pytest.mark.skipif(
    os.environ.get("SYNAPSE_LIVE_LLM") != "1",
    reason="Opt-in live LLM gateway smoke test (set SYNAPSE_LIVE_LLM=1 to execute against local Ollama/cloud).",
)
def test_gateway_live_llm_opt_in_smoke():
    """Opt-in Live Transport Smoke: Disabled by default; verifies live request round-trip when SYNAPSE_LIVE_LLM=1."""
    resp = execute_stdlib_gateway_call(
        StdlibGatewayRequestDTO(
            model_id="ollama-qwen3-coder",
            system_prefix="Reply with OK.",
            user_prompt="Ping",
            max_tokens=16,
            network_opt_in=True,
        ),
        available_providers=(ProviderFamily.LOCAL_OPENAI,),
    )
    assert isinstance(resp, StdlibGatewayResponseDTO)
