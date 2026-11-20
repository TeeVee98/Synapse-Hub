# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tests/aut_api/conftest.py — Pytest fixtures for REST API test automation suite.
Provides authenticated client sessions, dynamic teardown registries, and idempotent data fixtures.
"""

import os
import time
import secrets
import logging
import pytest
import requests
from tests.aut_api.api_client_helper import BookApiClient, UserApiClient

logger = logging.getLogger(__name__)


def _obtain_live_or_mock_token(base_url: str) -> str:
    """Attempts to register/login a live session, caching across xdist workers."""
    cache_file = os.path.join(os.path.dirname(__file__), ".session_token.txt")
    if os.path.exists(cache_file):
        try:
            if time.time() - os.path.getmtime(cache_file) < 3600:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_tok = f.read().strip()
                if cached_tok and not cached_tok.startswith("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.synapse_test_token_"):
                    test_resp = requests.get(
                        f"{base_url}/api/book?page=1&limit=1",
                        headers={"Authorization": f"Bearer {cached_tok}"},
                        timeout=5
                    )
                    if test_resp.status_code == 200:
                        return cached_tok
        except Exception as err:
            logger.debug("Failed reading cached token: %s", err)

    for attempt in range(4):
        ts = int(time.time() * 1000) + attempt * 200
        email = f"synapse_runner_{ts}@example.com"
        pwd = os.getenv("AUT_TEST_PASSWORD") or secrets.token_urlsafe(16)

        try:
            requests.post(
                f"{base_url}/api/register",
                json={"email": email, "password": pwd, "name": "Synapse Runner"},
                timeout=8
            )
            res = requests.post(
                f"{base_url}/api/login",
                json={"email": email, "password": pwd},
                timeout=8
            )
            if res.status_code == 200:
                token = res.json().get("accessToken")
                if token:
                    try:
                        with open(cache_file, "w", encoding="utf-8") as f:
                            f.write(token)
                    except Exception as err:
                        logger.warning("Failed writing token to cache: %s", err)
                    return token
        except Exception as err:
            logger.warning("Auth token acquisition attempt %d failed: %s", attempt + 1, err)

    return f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.synapse_test_token_{int(time.time() * 1000)}"


@pytest.fixture(scope="session")
def auth_token():
    base_url = os.environ.get("BOOK_API_BASE_URL", "https://book.anhtester.com")
    return _obtain_live_or_mock_token(base_url)


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
