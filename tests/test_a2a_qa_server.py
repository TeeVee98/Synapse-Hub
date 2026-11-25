# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""Unit tests for A2AQAServer (tests/test_a2a_qa_server.py).

Verifies A2A 1.0 JSON-RPC 2.0 handshake, tool dispatch, error code handling,
and Server-Sent Events (SSE) streaming format.

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

import os
import pytest

from tools.api.a2a_qa_server import A2AQAServer


@pytest.fixture
def a2a_server():
    return A2AQAServer()


def test_a2a_handshake_successful(a2a_server):
    req = {
        "jsonrpc": "2.0",
        "id": "req-001",
        "method": "a2a.handshake",
        "params": {"client_name": "Cursor-Claude-3.7"},
    }
    resp = a2a_server.process_jsonrpc(req)

    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == "req-001"
    assert "result" in resp

    res = resp["result"]
    assert res["protocol"] == "A2A/1.0"
    assert res["server"] == "Synapse-Hub-QA-Agent"
    assert res["author"] == "Thế Vị (@TeeVee98)"
    assert res["client_acknowledged"] == "Cursor-Claude-3.7"
    assert "qa.quality_gates" in res["capabilities"]


def test_a2a_tools_list(a2a_server):
    req = {
        "jsonrpc": "2.0",
        "id": "req-002",
        "method": "a2a.tools.list",
        "params": {},
    }
    resp = a2a_server.process_jsonrpc(req)
    assert resp["jsonrpc"] == "2.0"
    assert "result" in resp
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "verify_quality_gates" in tool_names
    assert "audit_shell_command" in tool_names
    assert "run_qa_sop" in tool_names


def test_a2a_tools_call_audit_command(a2a_server):
    req = {
        "jsonrpc": "2.0",
        "id": "req-003",
        "method": "a2a.tools.call",
        "params": {
            "tool": "audit_shell_command",
            "arguments": {"command": "rm -rf /"},
        },
    }
    resp = a2a_server.process_jsonrpc(req)
    assert resp["jsonrpc"] == "2.0"
    res = resp["result"]
    assert res["is_safe"] is False
    assert res["action"] == "HALT_AND_ESCALATE"


def test_a2a_invalid_method_error(a2a_server):
    req = {
        "jsonrpc": "2.0",
        "id": "req-004",
        "method": "unknown_method_xyz",
        "params": {},
    }
    resp = a2a_server.process_jsonrpc(req)
    assert resp["jsonrpc"] == "2.0"
    assert "error" in resp
    assert resp["error"]["code"] == -32601


def test_a2a_invalid_jsonrpc_version(a2a_server):
    req = {
        "jsonrpc": "1.0",
        "id": "req-005",
        "method": "a2a.ping",
    }
    resp = a2a_server.process_jsonrpc(req)
    assert resp["error"]["code"] == -32600


def test_a2a_sse_streaming_format(a2a_server):
    events = [
        {"stage": "INIT", "progress": 10},
        {"stage": "EXEC", "progress": 50},
    ]
    stream_chunks = list(a2a_server.stream_events(task_id="task_99", events=events))

    assert len(stream_chunks) == 3
    assert "event: message\ndata: " in stream_chunks[0]
    assert '"task_id": "task_99"' in stream_chunks[0]
    assert "event: done\ndata: " in stream_chunks[2]
    assert '"status": "COMPLETED"' in stream_chunks[2]


def test_a2a_verify_quality_gates_reflects_real_gate_pass_and_failure(monkeypatch, a2a_server):
    """P0-2 Truth Anchor: verify_quality_gates must execute verify_all and never hardcode dod_compliant=True."""
    calls = []

    def fake_run_all_gates(repo_root, mode="AUTO", tier=None, fast=False, output_format="text", **_kw):
        calls.append({"repo_root": repo_root, "mode": mode, "tier": tier, "fast": fast})
        return 1 if tier == "impact" else 0

    monkeypatch.setattr("tools.core.verify_all.run_all_gates", fake_run_all_gates)

    pass_resp = a2a_server.process_jsonrpc({
        "jsonrpc": "2.0",
        "id": "req-pass",
        "method": "a2a.tools.call",
        "params": {
            "tool": "verify_quality_gates",
            "arguments": {"tier": "fast", "mode": "hub"},
        },
    })
    assert pass_resp["result"]["dod_compliant"] is True
    assert pass_resp["result"]["exit_code"] == 0
    assert pass_resp["result"]["message"] == "Quality gates passed."
    assert calls[0]["fast"] is True
    assert os.path.isdir(calls[0]["repo_root"])

    fail_resp = a2a_server.process_jsonrpc({
        "jsonrpc": "2.0",
        "id": "req-fail",
        "method": "a2a.tools.call",
        "params": {
            "tool": "verify_quality_gates",
            "arguments": {"tier": "impact", "mode": "hub", "target": "/tmp/custom_target"},
        },
    })
    assert fail_resp["result"]["dod_compliant"] is False
    assert fail_resp["result"]["exit_code"] == 1
    assert fail_resp["result"]["message"] == "Quality gates failed (exit code 1)."
    assert calls[1]["fast"] is False
    assert calls[1]["repo_root"] == "/tmp/custom_target"
    assert len(calls) == 2


def test_a2a_verify_quality_gates_handles_exception_and_invalid_tier(monkeypatch, a2a_server):
    """P0-2 Negative/Boundary: exceptions fail closed (dod_compliant=False) and invalid tier returns JSON-RPC error."""
    def exploding_run(*_args, **_kwargs):
        raise RuntimeError("gate engine unavailable")

    monkeypatch.setattr("tools.core.verify_all.run_all_gates", exploding_run)
    err_resp = a2a_server.process_jsonrpc({
        "jsonrpc": "2.0",
        "id": "req-err",
        "method": "a2a.tools.call",
        "params": {
            "tool": "verify_quality_gates",
            "arguments": {"tier": "fast"},
        },
    })
    assert err_resp["result"]["dod_compliant"] is False
    assert err_resp["result"]["exit_code"] == 1
    assert "gate engine unavailable" in err_resp["result"]["message"]

    bad_tier_resp = a2a_server.process_jsonrpc({
        "jsonrpc": "2.0",
        "id": "req-bad-tier",
        "method": "a2a.tools.call",
        "params": {
            "tool": "verify_quality_gates",
            "arguments": {"tier": "invalid_tier_xyz"},
        },
    })
    assert "error" in bad_tier_resp
    assert bad_tier_resp["error"]["code"] == -32602
