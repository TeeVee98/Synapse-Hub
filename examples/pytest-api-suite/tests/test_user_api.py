# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Pytest API Test Cases — Clean client calls and strict contract assertions.
"""

import pytest


def test_create_user_positive(api_client, user_teardown_registry):
    """TC-API-01: Verify successful user creation with valid payload."""
    email = api_client.unique_email()
    payload = {
        "email": email,
        "name": "QA Automation Engineer",
        "role": "MEMBER"
    }

    res = api_client.create_user(payload)
    assert res.status_code == 201, f"Expected 201 Created, got {res.status_code}: {res.text}"

    data = res.json()
    assert "id" in data, "Response body must contain generated user ID"
    assert data["email"] == email, "Response email must match requested payload"

    # Register for automated teardown cleanup
    user_teardown_registry(data["id"])


def test_create_user_duplicate_email_conflict(api_client, user_teardown_registry):
    """TC-API-02: Verify 409 Conflict when attempting to register duplicate email."""
    email = api_client.unique_email()
    payload = {
        "email": email,
        "name": "First User",
        "role": "MEMBER"
    }

    # 1. Create first user
    first_res = api_client.create_user(payload)
    assert first_res.status_code == 201
    user_teardown_registry(first_res.json()["id"])

    # 2. Re-submit same payload -> must return 409 Conflict
    conflict_res = api_client.create_user(payload)
    assert conflict_res.status_code == 409, f"Expected 409 Conflict, got {conflict_res.status_code}"
