"""
Shared test fixtures and teardown registry for Pytest API suite.
"""

import pytest
import time
from pages.user_api_client import UserApiClient


@pytest.fixture(scope="session")
def api_client():
    """Initializes and provides the base UserApiClient."""
    return UserApiClient(base_url="https://staging-api.example.com")


@pytest.fixture
def user_teardown_registry(api_client):
    """Tracks created user IDs and deletes them after each test run."""
    created_ids = []

    def _register(user_id: int):
        created_ids.append(user_id)
        return user_id

    yield _register

    for uid in created_ids:
        try:
            api_client.delete_user(uid)
        except Exception:
            pass
