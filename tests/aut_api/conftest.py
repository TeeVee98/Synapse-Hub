# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/aut_api/conftest.py — Pytest fixtures for REST API test automation suite.
Provides authenticated client sessions, dynamic teardown registries, and idempotent data fixtures.
"""

import hashlib
import os
import time
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional
import pytest
import requests
from tests.aut_api.api_client_helper import (
    BookApiClient,
    UserApiClient,
    resolve_api_transport_config,
)

logger = logging.getLogger(__name__)


def scoped_token_cache_path(base_url: str, target_alias: Optional[str] = None) -> str:
    """Returns a target-scoped session token cache path so staging tokens never leak across targets."""
    cache_dir = os.environ.get("SYNAPSE_TOKEN_CACHE_DIR") or os.path.dirname(__file__)
    scope_key = f"{(target_alias or '').strip()}|{(base_url or '').strip().rstrip('/')}"
    digest = hashlib.sha256(scope_key.encode("utf-8")).hexdigest()[:12]
    return os.path.join(cache_dir, f".session_token_{digest}.txt")


def _read_valid_cached_token(cache_file: str, resolved_url: str) -> Optional[str]:
    """Returns cached staging token if fresh and accepted by target, else None."""
    if not os.path.exists(cache_file):
        return None
    try:
        if datetime.now(timezone.utc).timestamp() - os.path.getmtime(cache_file) >= 3600:
            return None
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_tok = f.read().strip()
        if not cached_tok or cached_tok.startswith("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.synapse_test_token_"):
            return None
        test_resp = requests.get(
            f"{resolved_url}/api/book?page=1&limit=1",
            headers={"Authorization": f"Bearer {cached_tok}"},
            timeout=5,
        )
        return cached_tok if test_resp.status_code == 200 else None
    except Exception as err:
        logger.debug("Failed reading cached token: %s", err)
        return None


def _attempt_register_and_login(resolved_url: str, attempt: int, cache_file: str) -> tuple[Optional[str], str]:
    """Perform a single registration+login attempt and cache the token on HTTP 200."""
    ts = int(time.time() * 1000) + attempt * 200
    email = f"synapse_runner_{ts}@example.com"
    pwd = os.getenv("AUT_TEST_PASSWORD") or secrets.token_urlsafe(16)
    try:
        requests.post(
            f"{resolved_url}/api/register",
            json={"email": email, "password": pwd, "name": "Synapse Runner"},
            timeout=8,
        )
        res = requests.post(
            f"{resolved_url}/api/login",
            json={"email": email, "password": pwd},
            timeout=8,
        )
        if res.status_code != 200:
            return None, f"HTTP {res.status_code}"
        token = res.json().get("accessToken")
        if not token:
            return None, "missing accessToken"
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(token)
        return token, ""
    except Exception as err:
        logger.warning("Auth token acquisition attempt %d failed: %s", attempt + 1, err)
        return None, str(err)


def _obtain_live_or_mock_token(
    base_url: str,
    mode: Optional[str] = None,
    target_alias: Optional[str] = None,
) -> str:
    """Obtains a live target-scoped session token in staging mode, or deterministic mock token offline."""
    resolved_url, resolved_mode, resolved_alias = resolve_api_transport_config(
        base_url=base_url,
        mode=mode,
        target_alias=target_alias,
    )
    if resolved_mode == "offline":
        return f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.synapse_test_token_{int(time.time() * 1000)}"

    cache_file = scoped_token_cache_path(resolved_url, target_alias=resolved_alias)
    cached_tok = _read_valid_cached_token(cache_file, resolved_url)
    if cached_tok:
        return cached_tok

    last_error = "no response"
    for attempt in range(4):
        token, err = _attempt_register_and_login(resolved_url, attempt, cache_file)
        if token:
            return token
        last_error = err

    raise RuntimeError(
        f"Staging API login failed for target '{resolved_alias}' ({resolved_url}): {last_error}"
    )


@pytest.fixture(scope="session")
def auth_token():
    base_url, mode, alias = resolve_api_transport_config()
    return _obtain_live_or_mock_token(base_url, mode=mode, target_alias=alias)


@pytest.fixture
def book_api_client(auth_token):
    client = BookApiClient(auth_token=auth_token)
    return client


@pytest.fixture
def unauth_book_client():
    return BookApiClient(auth_token=None)


@pytest.fixture
def user_api_client(auth_token):
    client = UserApiClient(auth_token=auth_token)
    return client


@pytest.fixture
def unauth_user_client():
    return UserApiClient(auth_token=None)


@pytest.fixture
def book_teardown_registry(book_api_client):
    """Tracks created book IDs and issues DELETE cleanup during teardown."""
    created_ids = []

    def _register(book_id: int):
        created_ids.append(book_id)
        return book_id

    yield _register

    for bid in created_ids:
        try:
            book_api_client.delete_book(bid)
        except Exception as err:
            logger.warning("Teardown failed for book %s: %s", bid, err)


@pytest.fixture
def user_teardown_registry(user_api_client):
    """Tracks created user IDs and issues DELETE cleanup during teardown."""
    created_ids = []

    def _register(user_id: int):
        created_ids.append(user_id)
        return user_id

    yield _register

    for uid in created_ids:
        try:
            user_api_client.delete_user(uid)
        except Exception as err:
            logger.warning("Teardown failed for user %s: %s", uid, err)
