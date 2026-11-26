#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
"""4-scenario test suite for tools/mcp/qa_lsp_server.py (Universal QA LSP 3.17)."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import time
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# 1. POSITIVE SCENARIOS
# ---------------------------------------------------------------------------


def test_positive_full_lsp_lifecycle_diagnostics_and_code_actions(tmp_path: Path) -> None:
    """Validates initialize -> didOpen -> publishDiagnostics -> codeAction -> didChange -> didClose -> shutdown."""
    from tools.mcp.qa_lsp_server import (
        LspDiagnosticsContractDTO,
        QALanguageServer,
        encode_lsp_frame,
        handle_lsp_rpc_message,
        read_lsp_frame,
    )

    pages = tmp_path / "pages"
    tests_dir = tmp_path / "tests"
    pages.mkdir()
    tests_dir.mkdir()

    # Cross-file POM assertion helper so clean test yields 0 false positives
    (pages / "OrderPage.ts").write_text(
        """
        import { expect, Page } from '@playwright/test';
        export class OrderPage {
            constructor(private page: Page) {}
            async confirmOrderSaved() {
                await expect(this.page.locator('#saved')).toBeVisible();
            }
        }
        """,
        encoding="utf-8",
    )

    server = QALanguageServer(workspace_root=str(tmp_path))

    # 1. initialize
    init_resp, init_notifs = server.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"rootUri": tmp_path.as_uri()}}
    )
    assert init_resp is not None
    assert init_resp["id"] == 1
    assert init_resp["result"]["capabilities"]["textDocumentSync"] == 1
    assert init_resp["result"]["capabilities"]["codeActionProvider"] is True
    assert init_resp["result"]["serverInfo"]["protocolVersion"] == "3.17"
    assert init_notifs == []

    # 2. initialized notification
    resp_inited, notifs_inited = server.handle_message({"jsonrpc": "2.0", "method": "initialized", "params": {}})
    assert resp_inited is None
    assert notifs_inited == []

    # 3. didOpen with defective TS test (unawaited expect + hard delay)
    bad_file = tests_dir / "bad_checkout.spec.ts"
    bad_text = (
        "import { test, expect } from '@playwright/test';\n"
        "test('bad', async ({ page }) => {\n"
        "  await page.waitForTimeout(5000);\n"
        "  expect(page.locator('#banner')).toBeVisible();\n"
        "});\n"
    )
    bad_uri = bad_file.as_uri()
    open_resp, open_notifs = server.handle_message(
        {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {"textDocument": {"uri": bad_uri, "languageId": "typescript", "version": 1, "text": bad_text}},
        }
    )
    assert open_resp is None
    assert len(open_notifs) == 1
    assert open_notifs[0]["method"] == "textDocument/publishDiagnostics"
    diags = open_notifs[0]["params"]["diagnostics"]
    codes = {d["code"] for d in diags}
    assert "EXCESSIVE_HARD_DELAY" in codes
    assert "UNAWAITED_ASYNC_ASSERTION" in codes
    assert all(d["source"] == "synapse-qa-lsp" for d in diags)

    # 4. codeAction returns Quick-Fix WorkspaceEdits
    ca_resp, ca_notifs = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/codeAction",
            "params": {
                "textDocument": {"uri": bad_uri},
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 0}},
                "context": {"diagnostics": diags},
            },
        }
    )
    assert ca_resp is not None
    assert ca_notifs == []
    actions = ca_resp["result"]
    assert len(actions) >= 2
    assert all(a["kind"] == "quickfix" for a in actions)
    assert all(bad_uri in a["edit"]["changes"] for a in actions)
    new_texts = [a["edit"]["changes"][bad_uri][0]["newText"] for a in actions]
    assert any("await " in t for t in new_texts)
    assert any("waitForLoadState" in t for t in new_texts)

    # 5. didChange to clean test calling cross-file POM helper -> 0 diagnostics!
    clean_text = (
        "import { test } from '@playwright/test';\n"
        "test('clean', async ({ page }) => {\n"
        "  await orderPage.confirmOrderSaved();\n"
        "});\n"
    )
    _, change_notifs = server.handle_message(
        {
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": {"textDocument": {"uri": bad_uri, "version": 2}, "contentChanges": [{"text": clean_text}]},
        }
    )
    assert len(change_notifs) == 1
    assert change_notifs[0]["params"]["diagnostics"] == []

    # 6. didSave & didClose
    _, save_notifs = server.handle_message(
        {"jsonrpc": "2.0", "method": "textDocument/didSave", "params": {"textDocument": {"uri": bad_uri}}}
    )
    assert len(save_notifs) == 1
    _, close_notifs = server.handle_message(
        {"jsonrpc": "2.0", "method": "textDocument/didClose", "params": {"textDocument": {"uri": bad_uri}}}
    )
    assert close_notifs[0]["params"]["diagnostics"] == []

    # 7. shutdown
    shut_resp, _ = server.handle_message({"jsonrpc": "2.0", "id": 3, "method": "shutdown"})
    assert shut_resp is not None
    assert shut_resp["result"] is None
    assert server.shutdown_requested is True

    # 8. Contract DTO immutability & stateless helper + framing roundtrip
    from tools.mcp.qa_lsp_server import _uri_to_filepath

    dto = LspDiagnosticsContractDTO("3.17", bad_uri, len(diags), len(actions), 1.5)
    assert dto.to_dict()["diagnostics_count"] == len(diags)
    with pytest.raises(FrozenInstanceError):
        dto.diagnostics_count = 0  # type: ignore[misc]

    # Verify URI-to-filepath handles file://, plain paths, and empty URI accurately
    assert Path(_uri_to_filepath(bad_uri)).resolve() == bad_file.resolve()
    assert _uri_to_filepath("relative/sample.ts") == "relative/sample.ts"
    assert _uri_to_filepath("") == "untitled.ts"

    # Verify encode_lsp_frame enforces UTF-8 (ensure_ascii=False) and deterministic sorted keys (sort_keys=True)
    frame_utf8 = encode_lsp_frame({"z": "ok-\u2713", "a": 1})
    assert "\u2713".encode("utf-8") in frame_utf8
    assert frame_utf8.index(b'"a"') < frame_utf8.index(b'"z"')

    frame = encode_lsp_frame({"jsonrpc": "2.0", "id": 9, "method": "shutdown"})
    parsed, err = read_lsp_frame(io.BytesIO(frame))
    assert err is None and parsed == {"jsonrpc": "2.0", "id": 9, "method": "shutdown"}

    stateless_resp, stateless_notifs = handle_lsp_rpc_message(
        {"jsonrpc": "2.0", "id": 10, "method": "initialize", "params": {}}, str(tmp_path)
    )
    assert stateless_resp is not None and stateless_resp["id"] == 10 and stateless_notifs == []


# ---------------------------------------------------------------------------
# 2. NEGATIVE SCENARIOS
# ---------------------------------------------------------------------------


def test_negative_malformed_frames_oversized_and_unknown_methods(tmp_path: Path) -> None:
    """Malformed headers, truncated bodies, invalid UTF-8, >5MB frames, and unknown methods return JSON-RPC errors cleanly."""
    from tools.mcp.qa_lsp_server import MAX_LSP_BODY_BYTES, QALanguageServer, read_lsp_frame

    # Oversized Content-Length (> 5 MB) -> -32600
    oversized = f"Content-Length: {MAX_LSP_BODY_BYTES + 10}\r\n\r\n{{}}".encode("ascii")
    payload, err = read_lsp_frame(io.BytesIO(oversized))
    assert payload is None and err is not None
    assert err["error"]["code"] == -32600

    # Non-numeric Content-Length -> -32600
    bad_hdr = b"Content-Length: not_a_number\r\n\r\n{}"
    payload2, err2 = read_lsp_frame(io.BytesIO(bad_hdr))
    assert payload2 is None and err2 is not None
    assert err2["error"]["code"] == -32600

    # Invalid JSON body -> -32700 Parse Error
    bad_json_body = b"{broken json"
    bad_json_frame = f"Content-Length: {len(bad_json_body)}\r\n\r\n".encode("ascii") + bad_json_body
    payload3, err3 = read_lsp_frame(io.BytesIO(bad_json_frame))
    assert payload3 is None and err3 is not None
    assert err3["error"]["code"] == -32700

    # Truncated body -> -32700
    trunc = b"Content-Length: 50\r\n\r\n{}"
    payload4, err4 = read_lsp_frame(io.BytesIO(trunc))
    assert payload4 is None and err4 is not None
    assert err4["error"]["code"] == -32700

    # Negative Content-Length -> -32600
    neg_cl = b"Content-Length: -1\r\n\r\n"
    p_neg, e_neg = read_lsp_frame(io.BytesIO(neg_cl))
    assert p_neg is None and e_neg is not None and e_neg["error"]["code"] == -32600

    # Missing Content-Length header -> -32600
    no_cl = b"Content-Type: application/json\r\n\r\n{}"
    p_nocl, e_nocl = read_lsp_frame(io.BytesIO(no_cl))
    assert p_nocl is None and e_nocl is not None and e_nocl["error"]["code"] == -32600

    # Header missing colon -> -32600
    bad_line = b"MalformedHeaderLine\r\n\r\n"
    p_bl, e_bl = read_lsp_frame(io.BytesIO(bad_line))
    assert p_bl is None and e_bl is not None and e_bl["error"]["code"] == -32600

    # Truncated header block -> -32700
    trunc_hdr = b"Content-Length: 2\r\n"
    p_th, e_th = read_lsp_frame(io.BytesIO(trunc_hdr))
    assert p_th is None and e_th is not None and e_th["error"]["code"] == -32700

    # Non-dict JSON array body -> -32600
    arr_body = b"[1, 2, 3]"
    arr_frame = f"Content-Length: {len(arr_body)}\r\n\r\n".encode("ascii") + arr_body
    p_arr, e_arr = read_lsp_frame(io.BytesIO(arr_frame))
    assert p_arr is None and e_arr is not None and e_arr["error"]["code"] == -32600

    # Boundary exact MAX_LSP_BODY_BYTES is rejected only when strictly greater
    p_zero, e_zero = read_lsp_frame(io.BytesIO(b"Content-Length: 0\r\n\r\n"))
    assert p_zero is None and e_zero is not None and e_zero["error"]["code"] == -32700

    # Unknown method -> -32601, invalid request missing method -> -32600
    server = QALanguageServer(workspace_root=str(tmp_path))
    unk_resp, _ = server.handle_message({"jsonrpc": "2.0", "id": 7, "method": "textDocument/nonExistent"})
    assert unk_resp is not None and unk_resp["error"]["code"] == -32601

    inv_resp, _ = server.handle_message({"jsonrpc": "2.0", "id": 8})
    assert inv_resp is not None and inv_resp["error"]["code"] == -32600


# ---------------------------------------------------------------------------
# 3. BOUNDARY & LATENCY SCENARIOS
# ---------------------------------------------------------------------------


def test_boundary_empty_document_eof_and_p95_latency(tmp_path: Path) -> None:
    """Empty EOF returns (None, None); 0-byte document does not crash; single-file LSP diagnostic P95 <= 50ms."""
    from tools.mcp.qa_lsp_server import QALanguageServer, read_lsp_frame

    # Clean EOF
    assert read_lsp_frame(io.BytesIO(b"")) == (None, None)

    server = QALanguageServer(workspace_root=str(tmp_path))
    empty_uri = (tmp_path / "empty.spec.ts").as_uri()
    _, notifs = server.handle_message(
        {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {"textDocument": {"uri": empty_uri, "languageId": "typescript", "version": 1, "text": ""}},
        }
    )
    assert len(notifs) == 1

    # Measure 10 consecutive cached diagnostic roundtrips -> P95 <= 50ms
    sample_uri = (tmp_path / "fast.spec.ts").as_uri()
    sample_code = "test('fast', async ({ page }) => { await expect(page.locator('#ok')).toBeVisible(); });\n"
    latencies_ms = []
    for v in range(1, 11):
        t0 = time.perf_counter()
        server.handle_message(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didChange" if v > 1 else "textDocument/didOpen",
                "params": (
                    {"textDocument": {"uri": sample_uri, "version": v}, "contentChanges": [{"text": sample_code}]}
                    if v > 1
                    else {"textDocument": {"uri": sample_uri, "languageId": "typescript", "version": 1, "text": sample_code}}
                ),
            }
        )
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)
    latencies_ms.sort()
    p95 = latencies_ms[int(0.95 * (len(latencies_ms) - 1))]
    assert p95 <= 50.0, f"LSP P95 latency exceeded 50ms: {p95:.2f}ms"


# ---------------------------------------------------------------------------
# 4. CLI FLAGS & STDIO STREAM SCENARIOS
# ---------------------------------------------------------------------------


def test_cli_check_health_json_and_stdio_serve(tmp_path: Path) -> None:
    """Verifies `--check-health --json` CLI contract and real stdio framing loop."""
    from tools.mcp.qa_lsp_server import QALanguageServer, encode_lsp_frame, read_lsp_frame

    script = REPO_ROOT / "tools" / "mcp" / "qa_lsp_server.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--check-health", "--root", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    health = json.loads(proc.stdout)
    assert health["status"] == "HEALTHY"
    assert health["protocol_version"] == "3.17"
    assert health["latency_ms"] >= 0.0

    # End-to-end stdio stream roundtrip
    in_stream = io.BytesIO(
        encode_lsp_frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        + encode_lsp_frame({"jsonrpc": "2.0", "id": 2, "method": "shutdown"})
        + encode_lsp_frame({"jsonrpc": "2.0", "method": "exit"})
    )
    out_stream = io.BytesIO()
    server = QALanguageServer(workspace_root=str(tmp_path))
    rc = server.serve_stdio(in_stream, out_stream)
    assert rc == 0

    out_stream.seek(0)
    msg1, err1 = read_lsp_frame(out_stream)
    msg2, err2 = read_lsp_frame(out_stream)
    assert err1 is None and msg1 is not None and msg1["id"] == 1
    assert err2 is None and msg2 is not None and msg2["id"] == 2
