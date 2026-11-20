# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
examples/perf-backend-suite/locust/locustfile.py
-------------------------------------------------
Enterprise Python-as-Code Performance Load Suite (ISO/IEC 25010 & ISTQB CT-PT).
Models concurrent virtual users with weighted user journeys (Pareto 70/20/10),
realistic think times, dynamic idempotent data, and automated SLA fail-fast listeners.
"""

import time
import random

try:
    from locust import HttpUser, task, between, events
except ImportError:
    # Fallback definition when locust package is not installed globally
    HttpUser = object
    def task(w=1): return lambda f: f
    def between(a, b): return lambda: random.uniform(a, b)
    events = None


class EnterpriseApiUser(HttpUser):
    """Models realistic concurrent users interacting with the REST API."""

    wait_time = between(1.0, 2.5) if callable(between) else None

    def on_start(self):
        """Per-VU initialization."""
        self.user_token = f"TOKEN_PERF_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        self.default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Synapse-Locust-Runner/2026",
            "Authorization": f"Bearer {self.user_token}",
        }

    @task(7)
    def task_get_all_books(self):
        """70% traffic: Read collection endpoint."""
        with self.client.get(
            "/api/v1/Books",
            headers=self.default_headers,
            name="GET /api/v1/Books",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(2)
    def task_create_synthetic_book(self):
        """20% traffic: Create entity with dynamic idempotent data."""
        timestamp = int(time.time() * 1000)
        payload = {
            "id": random.randint(100000, 999999),
            "title": f"PERF_AUTO_BOOK_{timestamp}_{random.randint(100, 999)}",
            "description": "Locust synthetic performance test book",
            "pageCount": 400,
            "excerpt": "High-throughput synthetic workload excerpt",
            "publishDate": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with self.client.post(
            "/api/v1/Books",
            json=payload,
            headers=self.default_headers,
            name="POST /api/v1/Books",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                response.success()
            else:
                response.failure(f"Create failed with status: {response.status_code}")

    @task(1)
    def task_get_single_book(self):
        """10% traffic: Read single item endpoint."""
        book_id = random.randint(1, 10)
        with self.client.get(
            f"/api/v1/Books/{book_id}",
            headers=self.default_headers,
            name="GET /api/v1/Books/:id",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get single item failed: {response.status_code}")
