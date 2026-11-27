#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_staging_transport.py
Verifies strict staging API transport, target-scoped token caching, teardown receipts,
and hermetic offline preservation for tests/aut_api.
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import pytest


def _start_staging_stub(reject_login: bool = False):
    """Starts an ephemeral local HTTP server simulating a live staging API."""
    state = {"created": [], "deleted": [], "auth_headers": []}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            body = json.loads(raw) if raw else {}
            if self.path == "/api/register":
                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))
                return
            if self.path == "/api/login":
                if reject_login:
                    self.send_response(401)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"msg": "Invalid credentials"}).encode("utf-8"))
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"accessToken": "live_tok_staging_1"}).encode("utf-8"))
                return
            if self.path == "/api/book":
                state["auth_headers"].append(self.headers.get("Authorization"))
                item_id = f"stg-{len(state['created']) + 1}"
                state["created"].append((item_id, body.get("name")))
                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"id": item_id, "name": body.get("name")}).encode("utf-8"))
                return
            self.send_response(404)
            self.end_headers()

        def do_GET(self):
            if self.path.startswith("/api/book"):
                state["auth_headers"].append(self.headers.get("Authorization"))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"list": [], "pagination": {"total": 0}}).encode("utf-8"))
                return
            self.send_response(404)
            self.end_headers()

        def do_DELETE(self):
            if self.path.startswith("/api/book/"):
                bid = self.path.rsplit("/", 1)[-1]
                state["deleted"].append(bid)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"msg": "Deleted"}).encode("utf-8"))
                return
            self.send_response(404)
            self.end_headers()

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}", state


def test_staging_mode_exercises_live_http_token_and_teardown_receipt(monkeypatch, tmp_path):
    """Positive: Explicit staging mode obtains target-scoped token, hits live HTTP, and cleans up."""
    from tests.aut_api.api_client_helper import BookApiClient
    from tests.aut_api.conftest import _obtain_live_or_mock_token, scoped_token_cache_path

    server, base_url, state = _start_staging_stub(reject_login=False)
    try:
        monkeypatch.setenv("SYNAPSE_API_MODE", "staging")
        monkeypatch.setenv("SYNAPSE_API_OFFLINE", "0")
        monkeypatch.setenv("BOOK_API_BASE_URL", base_url)
        monkeypatch.setenv("SYNAPSE_TOKEN_CACHE_DIR", str(tmp_path))

        token = _obtain_live_or_mock_token(base_url, mode="staging", target_alias="staging-eu")
        assert token == "live_tok_staging_1"
        cache_path = scoped_token_cache_path(base_url, target_alias="staging-eu")
        assert os.path.isfile(cache_path)

        client = BookApiClient(
            base_url=base_url,
            auth_token=token,
            mode="staging",
            target_alias="staging-eu",
            build_id="build-123",
        )
        assert client.offline_mode is False
        res_get = client.get_books()
        assert res_get.status_code == 200
        res_create = client.create_book({"name": "STG_BOOK_1"})
        assert res_create.status_code == 201
        created_id = res_create.json()["id"]
        res_del = client.delete_book(created_id)
        assert res_del.status_code == 200
        assert created_id in state["deleted"]

        receipt = client.build_transport_receipt(cleanup_count=1)
        assert receipt["build_id"] == "build-123"
        assert receipt["target_alias"] == "staging-eu"
        assert receipt["transport"] == "staging"
        assert receipt["executed"] == 3
        assert receipt["cleanup_count"] == 1
    finally:
        server.shutdown()
        server.server_close()


def test_staging_rejected_login_and_unreachable_transport_fail_closed(monkeypatch, tmp_path):
    """Negative: Rejected login or unreachable staging transport fails instead of mock fallback."""
    import requests
    from tests.aut_api.api_client_helper import BookApiClient
    from tests.aut_api.conftest import _obtain_live_or_mock_token

    monkeypatch.setenv("SYNAPSE_API_MODE", "staging")
    monkeypatch.setenv("SYNAPSE_API_OFFLINE", "0")
    monkeypatch.setenv("SYNAPSE_TOKEN_CACHE_DIR", str(tmp_path))

    bad_server, bad_url, _ = _start_staging_stub(reject_login=True)
    try:
        with pytest.raises(RuntimeError, match="login|auth|staging") as login_exc:
            _obtain_live_or_mock_token(bad_url, mode="staging", target_alias="staging-bad")
        assert "staging" in str(login_exc.value).lower()
    finally:
        bad_server.shutdown()
        bad_server.server_close()

    dead_client = BookApiClient(base_url="http://127.0.0.1:1", mode="staging", target_alias="staging-dead")
    with pytest.raises(requests.RequestException) as req_exc:
        dead_client.get_books()
    assert req_exc.value is not None


def test_staging_requires_explicit_target_and_isolates_token_cache(monkeypatch, tmp_path):
    """Boundary: Staging without explicit target rejects localhost fallback; tokens stay target-scoped."""
    from tests.aut_api.api_client_helper import BookApiClient, resolve_api_transport_config
    from tests.aut_api.conftest import scoped_token_cache_path

    monkeypatch.setenv("SYNAPSE_API_MODE", "staging")
    monkeypatch.delenv("BOOK_API_BASE_URL", raising=False)
    monkeypatch.setenv("SYNAPSE_TOKEN_CACHE_DIR", str(tmp_path))

    with pytest.raises(ValueError, match="BOOK_API_BASE_URL|target"):
        resolve_api_transport_config(base_url=None, mode="staging")

    p1 = scoped_token_cache_path("https://staging-a.example.com", target_alias="a")
    p2 = scoped_token_cache_path("https://staging-b.example.com", target_alias="b")
    assert p1 != p2

    # Offline default remains hermetic and explicitly marked offline
    monkeypatch.delenv("SYNAPSE_API_MODE", raising=False)
    monkeypatch.setenv("SYNAPSE_API_OFFLINE", "1")
    off_client = BookApiClient()
    assert off_client.offline_mode is True
    off_receipt = off_client.build_transport_receipt()
    assert off_receipt["transport"] == "offline"


def test_offline_fixture_preserves_default_hermetic_behavior(monkeypatch):
    """CLI & Resilience: Hermetic PR default returns MockResponse without network sockets."""
    from tests.aut_api.api_client_helper import BookApiClient, MockResponse
    from tests.aut_api.conftest import _obtain_live_or_mock_token

    monkeypatch.delenv("SYNAPSE_API_MODE", raising=False)
    monkeypatch.setenv("SYNAPSE_API_OFFLINE", "1")
    tok = _obtain_live_or_mock_token("http://localhost:8080")
    assert "synapse_test_token_" in tok

    client = BookApiClient(auth_token=tok)
    resp = client.get_books()
    assert isinstance(resp, MockResponse)
    assert resp.status_code == 200
    assert client.build_transport_receipt()["executed"] == 1
