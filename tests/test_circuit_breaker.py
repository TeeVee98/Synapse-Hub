#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Unit tests for tools/core/circuit_breaker.py (In-Flight Token Circuit Breaker & Cascades)
"""

import time
import unittest
from tools.core.circuit_breaker import (
    TokenCircuitBreaker,
    CircuitBreakerState,
    TokenBudgetExceededError,
    RateLimitExceededError,
    CircuitBreakerError,
    record_tokens,
    record_http_status,
    can_execute,
    get_active_model,
)


class TestCircuitBreaker(unittest.TestCase):
    def test_record_tokens_normal(self):
        cb = TokenCircuitBreaker(task_token_budget=10_000, session_token_budget=50_000)
        used = cb.record_tokens(1500)
        self.assertEqual(used, 1500)
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)

    def test_token_budget_cascade_and_trip(self):
        # 3 fallback models
        cb = TokenCircuitBreaker(
            task_token_budget=1_000,
            session_token_budget=100_000,
            fallback_models=["tier-1", "tier-2", "tier-3"]
        )
        self.assertEqual(cb.get_active_model(), "tier-1")

        # Exceed first budget -> cascades to tier-2
        cb.record_tokens(1_200)
        self.assertEqual(cb.state, CircuitBreakerState.FALLBACK)
        self.assertEqual(cb.get_active_model(), "tier-2")

        # Exceed second budget -> cascades to tier-3
        cb.record_tokens(2_000)
        self.assertEqual(cb.state, CircuitBreakerState.FALLBACK)
        self.assertEqual(cb.get_active_model(), "tier-3")

        # Exceed last model budget -> trips breaker to OPEN
        with self.assertRaises(TokenBudgetExceededError):
            cb.record_tokens(5_000)
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)

        # Subsequent execution blocked
        allowed, reason = cb.can_execute()
        self.assertFalse(allowed)
        self.assertIn("OPEN", reason)

    def test_session_budget_exceeded(self):
        cb = TokenCircuitBreaker(task_token_budget=100_000, session_token_budget=2_000)
        with self.assertRaises(TokenBudgetExceededError):
            cb.record_tokens(3_000)
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)

    def test_http_429_cascade_and_trip(self):
        cb = TokenCircuitBreaker(
            rate_limit_threshold=2,
            fallback_models=["model-a", "model-b"]
        )
        self.assertEqual(cb.get_active_model(), "model-a")

        # First 429
        cb.record_http_status(429)
        # Second 429 -> cascades to model-b
        new_model = cb.record_http_status(429)
        self.assertEqual(new_model, "model-b")
        self.assertEqual(cb.get_active_model(), "model-b")

        # 429 on last model -> trips to OPEN
        cb.record_http_status(429)
        with self.assertRaises(RateLimitExceededError):
            cb.record_http_status(429)
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)

    def test_half_open_cooldown_recovery(self):
        cb = TokenCircuitBreaker(cooldown_seconds=0.05)
        cb.trip("Manual test trip")
        self.assertEqual(cb.state, CircuitBreakerState.OPEN)

        cb.tripped_timestamp = time.time() - 1.0
        # Should transition to HALF_OPEN
        allowed, model = cb.can_execute()
        self.assertTrue(allowed)
        self.assertEqual(cb.state, CircuitBreakerState.HALF_OPEN)

        # Successful request heals to CLOSED
        cb.record_http_status(200)
        self.assertEqual(cb.state, CircuitBreakerState.CLOSED)

    def test_protect_execution_context(self):
        cb = TokenCircuitBreaker(task_token_budget=5_000)
        with cb.protect_execution(estimated_tokens=500) as active_model:
            self.assertEqual(active_model, "claude-sonnet")
        self.assertEqual(cb.task_tokens, 500)

        cb.trip("Emergency stop")
        with self.assertRaises(CircuitBreakerError):
            with cb.protect_execution():
                pass

    def test_reset_and_status(self):
        cb = TokenCircuitBreaker()
        cb.record_tokens(500)
        status = cb.get_status()
        self.assertEqual(status["task_tokens"], 500)
        self.assertEqual(status["state"], "CLOSED")

        cb.reset()
        status_after = cb.get_status()
        self.assertEqual(status_after["task_tokens"], 0)


if __name__ == "__main__":
    unittest.main()
