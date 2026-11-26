#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
"""
Zero-Dependency Universal QA Language Server (LSP 3.17 over JSON-RPC 2.0 stdio).

Delivers real-time Meta Infer-style static defect diagnostics and Quick-Fix
WorkspaceEdit code actions across TypeScript, JavaScript, Python, Java, and
Groovy for JetBrains IDEs (IntelliJ, PyCharm, WebStorm, Aqua), Neovim, Cursor,
and VS Code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, BinaryIO, Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.context.pom_assertion_indexer import (
    CrossFileAssertionMapDTO,
    build_pom_assertion_index,
)
from tools.lint import infer_linter

LSP_PROTOCOL_VERSION: str = "3.17"
SERVER_NAME: str = "synapse-qa-lsp"
SERVER_VERSION: str = "4.9.0"
MAX_LSP_BODY_BYTES: int = 5 * 1024 * 1024  # 5 MB safety cap against OOM

JSONRPC_PARSE_ERROR: int = -32700
JSONRPC_INVALID_REQUEST: int = -32600
JSONRPC_METHOD_NOT_FOUND: int = -32601

SEVERITY_MAP: Dict[str, int] = {
    "CRITICAL": 1,  # Error
    "ERROR": 1,
    "WARNING": 2,
    "INFO": 3,
    "HINT": 4,
}


@dataclass(frozen=True)
class LspDiagnosticsContractDTO:
    """Immutable telemetry contract for a single LSP diagnostic cycle."""

    protocol_version: str
    uri: str
    diagnostics_count: int
    code_actions_available: int
    latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "uri": self.uri,
            "diagnostics_count": self.diagnostics_count,
            "code_actions_available": self.code_actions_available,
            "latency_ms": round(self.latency_ms, 3),
        }


def _jsonrpc_error(code: int, message: str, req_id: Any = None) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }


def _uri_to_filepath(uri: str) -> str:
    """Converts a `file://` LSP document URI to a local filesystem path."""
    if not uri:
        return "untitled.ts"
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        return url2pathname(unquote(parsed.path))
    return uri


def encode_lsp_frame(message: Dict[str, Any]) -> bytes:
    """Encodes a JSON-RPC 2.0 dictionary into an LSP Content-Length framed byte payload."""
    body = json.dumps(message, ensure_ascii=False, sort_keys=True).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


def read_lsp_frame(
    stream: BinaryIO,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Reads one Content-Length framed JSON-RPC 2.0 message from `stream`.
    Returns `(payload, error_response)`. On clean EOF, returns `(None, None)`.
    """
    headers: Dict[str, str] = {}
    saw_any_header = False

    while True:
        raw_line = stream.readline()
        if not raw_line:
            if not saw_any_header:
                return None, None
            return None, _jsonrpc_error(JSONRPC_PARSE_ERROR, "Truncated LSP header block")
        line = raw_line.decode("ascii", errors="replace").strip()
        if line == "":
            if saw_any_header:
                break
            continue
        saw_any_header = True
        if ":" not in line:
            return None, _jsonrpc_error(JSONRPC_INVALID_REQUEST, f"Malformed LSP header: {line}")
        key, val = line.split(":", 1)
        headers[key.strip().lower()] = val.strip()

    cl_raw = headers.get("content-length")
    if cl_raw is None:
        return None, _jsonrpc_error(JSONRPC_INVALID_REQUEST, "Missing Content-Length header")
    try:
        content_length = int(cl_raw)
    except ValueError:
        return None, _jsonrpc_error(
            JSONRPC_INVALID_REQUEST, f"Invalid Content-Length header: {cl_raw}"
        )

    if content_length < 0 or content_length > MAX_LSP_BODY_BYTES:
        return None, _jsonrpc_error(
            JSONRPC_INVALID_REQUEST,
            f"Content-Length {content_length} exceeds allowed bounds [0, {MAX_LSP_BODY_BYTES}]",
        )

    body_bytes = stream.read(content_length)
    if len(body_bytes) < content_length:
        return None, _jsonrpc_error(
            JSONRPC_PARSE_ERROR,
            f"Truncated LSP message body: expected {content_length} bytes, got {len(body_bytes)}",
        )

    try:
        decoded = body_bytes.decode("utf-8")
        payload = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, _jsonrpc_error(JSONRPC_PARSE_ERROR, f"JSON parse error: {exc}")

    if not isinstance(payload, dict):
        return None, _jsonrpc_error(JSONRPC_INVALID_REQUEST, "JSON-RPC payload must be an object")

    return payload, None


def _build_quick_fix_for_diagnostic(
    uri: str,
    diag: Dict[str, Any],
    lines: List[str],
) -> Optional[Dict[str, Any]]:
    """Builds an LSP 3.17 Quick-Fix CodeAction with WorkspaceEdit for a supported defect."""
    code = str(diag.get("code", "")).upper()
    diag_range = diag.get("range", {})
    start_line = int(diag_range.get("start", {}).get("line", 0))
    if start_line < 0 or start_line >= len(lines):
        return None

    orig_line = lines[start_line]
    new_line: Optional[str] = None
    title = ""

    if code == "UNAWAITED_ASYNC_ASSERTION":
        if "await " not in orig_line and "expect" in orig_line:
            new_line = re.sub(r"\bexpect\b", "await expect", orig_line, count=1)
            title = "Synapse Quick-Fix: Prepend 'await' to async Playwright assertion"
    elif code in ("EXCESSIVE_HARD_DELAY", "HARD_DELAY_ANTI_PATTERN"):
        if "waitForTimeout" in orig_line:
            new_line = re.sub(
                r"(?:page\.)?waitForTimeout\s*\([^)]*\)",
                "page.waitForLoadState('domcontentloaded')",
                orig_line,
                count=1,
            )
            title = "Synapse Quick-Fix: Replace static waitForTimeout with smart wait"
        elif "time.sleep" in orig_line:
            indent = orig_line[: len(orig_line) - len(orig_line.lstrip())]
            new_line = f"{indent}# Synapse Quick-Fix: replace static sleep with explicit smart wait"
            title = "Synapse Quick-Fix: Remove static time.sleep delay"
        elif "Thread.sleep" in orig_line or "WebUI.delay" in orig_line:
            indent = orig_line[: len(orig_line) - len(orig_line.lstrip())]
            new_line = f"{indent}// Synapse Quick-Fix: replace static delay with dynamic smart wait"
            title = "Synapse Quick-Fix: Remove static sleep delay"
    elif code == "SWALLOWED_EXCEPTION":
        if "catch" in orig_line and "{}" in orig_line.replace(" ", ""):
            new_line = re.sub(r"\{\s*\}", "{ throw e; }", orig_line, count=1)
            title = "Synapse Quick-Fix: Re-throw caught exception instead of swallowing"
        elif orig_line.strip() == "pass":
            indent = orig_line[: len(orig_line) - len(orig_line.lstrip())]
            new_line = f"{indent}raise"
            title = "Synapse Quick-Fix: Replace swallowed 'pass' with 'raise'"
    elif code == "DANGLING_ASSERTION_NO_MATCHER":
        stripped = orig_line.rstrip()
        if stripped.endswith(";"):
            new_line = stripped[:-1] + ".toBeVisible();"
        else:
            new_line = stripped + ".toBeVisible()"
        title = "Synapse Quick-Fix: Append '.toBeVisible()' matcher to dangling expect()"

    if new_line is None or new_line == orig_line:
        return None

    edit_range = {
        "start": {"line": start_line, "character": 0},
        "end": {"line": start_line, "character": len(orig_line)},
    }
    return {
        "title": title,
        "kind": "quickfix",
        "diagnostics": [diag],
        "edit": {
            "changes": {
                uri: [{"range": edit_range, "newText": new_line}],
            }
        },
    }


class QALanguageServer:
    """Thread-safe LSP 3.17 server wrapping infer_linter and cross-file POM indexing."""

    def __init__(self, workspace_root: str = ".") -> None:
        self.workspace_root: str = os.path.abspath(workspace_root)
        self.shutdown_requested: bool = False
        self.exit_requested: bool = False
        self._lock = threading.RLock()
        self._documents: Dict[str, str] = {}
        self._diagnostics: Dict[str, List[Dict[str, Any]]] = {}
        self._pom_cache_key: Optional[Tuple[str, str]] = None
        self._pom_cache_map: Optional[CrossFileAssertionMapDTO] = None

    def _compute_workspace_fingerprint(self) -> str:
        """Computes a lightweight mtime/size fingerprint for workspace POM cache validation."""
        if not os.path.isdir(self.workspace_root):
            return "empty"
        h = hashlib.sha256()
        count = 0
        for root, dirs, files in os.walk(self.workspace_root):
            dirs[:] = sorted(
                d
                for d in dirs
                if d not in {".git", "node_modules", "__pycache__", ".venv", "dist", "build", "reports"}
                and not d.startswith(".")
            )
            for fname in sorted(files):
                if os.path.splitext(fname)[1].lower() in (".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".groovy"):
                    fpath = os.path.join(root, fname)
                    try:
                        st = os.stat(fpath)
                        h.update(f"{fpath}:{st.st_mtime_ns}:{st.st_size};".encode("utf-8"))
                    except OSError:
                        continue
                    count += 1
                    if count >= 200:
                        return h.hexdigest()
        return h.hexdigest()

    def _get_assertion_map(self, force_refresh: bool = False) -> CrossFileAssertionMapDTO:
        with self._lock:
            fp = self._compute_workspace_fingerprint()
            cache_key = (self.workspace_root, fp)
            if not force_refresh and self._pom_cache_key == cache_key and self._pom_cache_map is not None:
                return self._pom_cache_map
            idx = build_pom_assertion_index(self.workspace_root, max_depth=3, prefer_tree_sitter=True)
            self._pom_cache_key = cache_key
            self._pom_cache_map = idx
            return idx

    def _lint_document(
        self, uri: str, text: str, force_refresh: bool = False
    ) -> Tuple[List[Dict[str, Any]], float]:
        t0 = time.perf_counter()
        filepath = _uri_to_filepath(uri)
        assertion_map = self._get_assertion_map(force_refresh=force_refresh)
        report = infer_linter.analyze_script(
            filepath,
            assertion_map=assertion_map,
            source_content=text,
        )

        lines = text.splitlines()
        lsp_diags: List[Dict[str, Any]] = []
        for defect in report.get("defects", []):
            line_0 = max(0, int(defect.get("line", 1)) - 1)
            line_len = len(lines[line_0]) if line_0 < len(lines) else 1
            lsp_diags.append(
                {
                    "range": {
                        "start": {"line": line_0, "character": 0},
                        "end": {"line": line_0, "character": max(1, line_len)},
                    },
                    "severity": SEVERITY_MAP.get(str(defect.get("severity", "WARNING")).upper(), 2),
                    "code": str(defect.get("type", "QA_DEFECT")),
                    "source": SERVER_NAME,
                    "message": str(defect.get("message", "")),
                }
            )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        with self._lock:
            self._diagnostics[uri] = lsp_diags
        return lsp_diags, elapsed_ms

    def handle_message(
        self, payload: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """Processes a single JSON-RPC 2.0 request or notification."""
        if not isinstance(payload, dict) or "method" not in payload:
            req_id = payload.get("id") if isinstance(payload, dict) else None
            return _jsonrpc_error(JSONRPC_INVALID_REQUEST, "Missing JSON-RPC 'method'", req_id), []

        method = str(payload.get("method", ""))
        req_id = payload.get("id")
        params = payload.get("params") or {}
        if not isinstance(params, dict):
            params = {}

        if method == "initialize":
            root_uri = params.get("rootUri") or params.get("rootPath")
            if isinstance(root_uri, str) and root_uri:
                candidate = _uri_to_filepath(root_uri)
                if os.path.isdir(candidate):
                    with self._lock:
                        self.workspace_root = os.path.abspath(candidate)
                        self._pom_cache_key = None
            result = {
                "capabilities": {
                    "textDocumentSync": 1,  # Full sync
                    "codeActionProvider": True,
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                    "protocolVersion": LSP_PROTOCOL_VERSION,
                },
            }
            return {"jsonrpc": "2.0", "id": req_id, "result": result}, []

        if method == "initialized":
            return None, []

        if method == "shutdown":
            self.shutdown_requested = True
            return {"jsonrpc": "2.0", "id": req_id, "result": None}, []

        if method == "exit":
            self.exit_requested = True
            return None, []

        if method == "textDocument/didOpen":
            td = params.get("textDocument", {})
            uri = str(td.get("uri", ""))
            text = str(td.get("text", ""))
            with self._lock:
                self._documents[uri] = text
            diags, _ = self._lint_document(uri, text)
            notif = {
                "jsonrpc": "2.0",
                "method": "textDocument/publishDiagnostics",
                "params": {"uri": uri, "diagnostics": diags},
            }
            return None, [notif]

        if method == "textDocument/didChange":
            td = params.get("textDocument", {})
            uri = str(td.get("uri", ""))
            changes = params.get("contentChanges", [])
            if isinstance(changes, list) and changes:
                last_change = changes[-1]
                text = str(last_change.get("text", "")) if isinstance(last_change, dict) else ""
                with self._lock:
                    self._documents[uri] = text
                diags, _ = self._lint_document(uri, text)
                notif = {
                    "jsonrpc": "2.0",
                    "method": "textDocument/publishDiagnostics",
                    "params": {"uri": uri, "diagnostics": diags},
                }
                return None, [notif]
            return None, []

        if method == "textDocument/didSave":
            td = params.get("textDocument", {})
            uri = str(td.get("uri", ""))
            with self._lock:
                text = str(params.get("text", self._documents.get(uri, "")))
                self._documents[uri] = text
            diags, _ = self._lint_document(uri, text, force_refresh=True)
            notif = {
                "jsonrpc": "2.0",
                "method": "textDocument/publishDiagnostics",
                "params": {"uri": uri, "diagnostics": diags},
            }
            return None, [notif]

        if method == "textDocument/didClose":
            td = params.get("textDocument", {})
            uri = str(td.get("uri", ""))
            with self._lock:
                self._documents.pop(uri, None)
                self._diagnostics.pop(uri, None)
            notif = {
                "jsonrpc": "2.0",
                "method": "textDocument/publishDiagnostics",
                "params": {"uri": uri, "diagnostics": []},
            }
            return None, [notif]

        if method == "textDocument/codeAction":
            td = params.get("textDocument", {})
            uri = str(td.get("uri", ""))
            ctx = params.get("context", {})
            req_range = params.get("range", {})
            start_l = int(req_range.get("start", {}).get("line", 0))
            end_l = int(req_range.get("end", {}).get("line", 10**9))
            with self._lock:
                text = self._documents.get(uri, "")
                stored_diags = self._diagnostics.get(uri, [])
            diag_source = ctx.get("diagnostics") if isinstance(ctx, dict) and ctx.get("diagnostics") else stored_diags
            lines = text.splitlines()
            actions: List[Dict[str, Any]] = []
            for d in diag_source:
                if not isinstance(d, dict):
                    continue
                d_line = int(d.get("range", {}).get("start", {}).get("line", 0))
                if start_l <= d_line <= end_l:
                    action = _build_quick_fix_for_diagnostic(uri, d, lines)
                    if action is not None:
                        actions.append(action)
            return {"jsonrpc": "2.0", "id": req_id, "result": actions}, []

        if req_id is not None:
            return _jsonrpc_error(JSONRPC_METHOD_NOT_FOUND, f"Method not found: {method}", req_id), []
        return None, []

    def serve_stdio(self, stdin_stream: BinaryIO, stdout_stream: BinaryIO) -> int:
        """Runs the blocking Content-Length JSON-RPC 2.0 stdio message loop."""
        while not self.exit_requested:
            payload, err_resp = read_lsp_frame(stdin_stream)
            if err_resp is not None:
                stdout_stream.write(encode_lsp_frame(err_resp))
                stdout_stream.flush()
                continue
            if payload is None:
                break
            resp, notifs = self.handle_message(payload)
            if resp is not None:
                stdout_stream.write(encode_lsp_frame(resp))
            for notif in notifs:
                stdout_stream.write(encode_lsp_frame(notif))
            stdout_stream.flush()
        return 0 if self.shutdown_requested or not self.exit_requested else 1


def handle_lsp_rpc_message(
    payload: Dict[str, Any],
    workspace_root: str,
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Processes a single stateless JSON-RPC 2.0 LSP request/notification."""
    server = QALanguageServer(workspace_root=workspace_root)
    return server.handle_message(payload)


def check_lsp_health(workspace_root: str = ".") -> Dict[str, Any]:
    """Runs an in-process LSP initialization and diagnostic smoke check."""
    t0 = time.perf_counter()
    server = QALanguageServer(workspace_root=workspace_root)
    resp, _ = server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    ok = bool(resp and "result" in resp)
    return {
        "status": "HEALTHY" if ok else "UNHEALTHY",
        "server_name": SERVER_NAME,
        "server_version": SERVER_VERSION,
        "protocol_version": LSP_PROTOCOL_VERSION,
        "workspace_root": os.path.abspath(workspace_root),
        "max_body_bytes": MAX_LSP_BODY_BYTES,
        "latency_ms": round(elapsed_ms, 3),
    }


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint for `synapse lsp` / `qa_lsp_server.py`."""
    parser = argparse.ArgumentParser(
        description="Synapse Hub Universal QA Language Server (LSP 3.17 over stdio)"
    )
    parser.add_argument("--root", default=".", help="Workspace root for cross-file POM indexing")
    parser.add_argument(
        "--check-health",
        action="store_true",
        help="Run LSP server self-diagnostics and exit",
    )
    parser.add_argument("--json", action="store_true", help="Emit health report as JSON")
    args = parser.parse_args(argv)

    if args.check_health:
        health = check_lsp_health(args.root)
        if args.json:
            print(json.dumps(health, indent=2, sort_keys=True))
        else:
            print(
                f"[LSP] {health['status']} | {health['server_name']} v{health['server_version']} "
                f"(LSP {health['protocol_version']}, {health['latency_ms']}ms)"
            )
        return 0 if health["status"] == "HEALTHY" else 1

    server = QALanguageServer(workspace_root=args.root)
    return server.serve_stdio(sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    raise SystemExit(main())
