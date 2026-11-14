# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
UserApiClient — Encapsulates REST API client methods adhering to Clean POM / Flat Architecture.
"""

import time
import requests
from typing import Dict, Any, Optional


class UserApiClient:
    def __init__(self, base_url: str = "https://staging-api.example.com", auth_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Synapse-QA-Client/2.0"
        })
        if auth_token:
            self.session.headers["Authorization"] = f"Bearer {auth_token}"

    @staticmethod
    def unique_email(prefix: str = "auto_user_") -> str:
        """Generates idempotent dynamic email to eliminate database uniqueness collision."""
        return f"{prefix}{int(time.time() * 1000)}@example.com"

    def create_user(self, payload: Dict[str, Any]) -> requests.Response:
        """Invokes POST /api/v1/users to register a new user."""
        return self.session.post(f"{self.base_url}/api/v1/users", json=payload, timeout=10)

    def get_user(self, user_id: int) -> requests.Response:
        """Invokes GET /api/v1/users/{id} to fetch user details."""
        return self.session.get(f"{self.base_url}/api/v1/users/{user_id}", timeout=10)

    def delete_user(self, user_id: int) -> requests.Response:
        """Invokes DELETE /api/v1/users/{id} for teardown cleanup."""
        return self.session.delete(f"{self.base_url}/api/v1/users/{user_id}", timeout=10)
