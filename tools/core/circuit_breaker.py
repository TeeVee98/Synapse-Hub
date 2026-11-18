#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Synapse Hub — In-Flight Token Circuit Breaker & Model Cascade Engine
-------------------------------------------------------------------
Prevents runaway token spend, recursive agent loops, and cascading HTTP 429
rate limit lockouts across multi-agent executions.

Capabilities:
  1. Streaming Token Budget Sentinel:
     - Enforces hard task-level and session-level token spend boundaries.
  2. Rate Limit & 429 Interceptor:
     - Automatically monitors HTTP 429 quota exhaustion events.
  3. Dynamic Fallback Model Cascade:
     - Cascades seamlessly across model tiers upon quota trip:
       Tier 1 (Claude 3.7 Sonnet / Gemini Pro) -> Tier 2 (Gemini Flash) -> Local SLM.
  4. Automatic Half-Open Recovery:
     - Probes downstream provider readiness after cooldown window.
"""
import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import time
import threading
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager


class CircuitBreakerState(str, Enum):
    CLOSED = "CLOSED"         # Normal operation, traffic allowed
    OPEN = "OPEN"             # Tripped, traffic blocked
    HALF_OPEN = "HALF_OPEN"   # Probing recovery after cooldown
    FALLBACK = "FALLBACK"     # Tripped primary, running on secondary fallback model


class CircuitBreakerError(Exception):
    """Base exception for circuit breaker faults."""
    pass


class TokenBudgetExceededError(CircuitBreakerError):
    """Raised when token consumption exceeds maximum allowed budget."""
    pass


class RateLimitExceededError(CircuitBreakerError):
    """Raised when HTTP 429 quota exhaustion locks the circuit breaker."""
    pass


DEFAULT_FALLBACK_MODELS = [
    "claude-sonnet",
    "gemini-pro",
    "gemini-flash",
]


class TokenCircuitBreaker:
    """Enterprise in-flight token circuit breaker and automated model cascade controller."""

    def __init__(
        self,
        task_token_budget: int = 200_000,
        session_token_budget: int = 1_000_000,
        rate_limit_threshold: int = 2,
        fallback_models: Optional[List[str]] = None,
        cooldown_seconds: float = 30.0,
    ):
        self.task_token_budget = task_token_budget
        self.session_token_budget = session_token_budget
        self.rate_limit_threshold = rate_limit_threshold
        self.fallback_models = list(fallback_models or DEFAULT_FALLBACK_MODELS)
        self.cooldown_seconds = cooldown_seconds

        self.state = CircuitBreakerState.CLOSED
        self.task_tokens = 0
        self.session_tokens = 0
        self.consecutive_429_count = 0
        self.current_model_idx = 0
        self.tripped_timestamp = 0.0
        self.trip_reason = ""
        self._lock = threading.Lock()

    def get_active_model(self) -> str:
        """Returns the currently active model from the fallback cascade."""
        with self._lock:
            if self.current_model_idx < len(self.fallback_models):
                return self.fallback_models[self.current_model_idx]
            return self.fallback_models[-1]

    def can_execute(self) -> Tuple[bool, str]:
        """
        Evaluates whether an execution attempt is authorized.
        Returns: (is_allowed, active_model_or_rejection_reason)
        """
        with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                # Check if cooldown has elapsed to attempt HALF_OPEN probe
                elapsed = time.time() - self.tripped_timestamp
                if elapsed >= self.cooldown_seconds:
                    self.state = CircuitBreakerState.HALF_OPEN
                    return True, self._current_model_unlocked()
                return False, f"Circuit breaker is OPEN ({self.trip_reason}). Cooldown: {int(self.cooldown_seconds - elapsed)}s remaining."

            return True, self._current_model_unlocked()

    def _current_model_unlocked(self) -> str:
        if self.current_model_idx < len(self.fallback_models):
            return self.fallback_models[self.current_model_idx]
        return self.fallback_models[-1]

    def record_tokens(self, count: int, model: Optional[str] = None) -> int:
        """
        Records consumed tokens and enforces budget limits.
        Triggers model fallback cascade or trips to OPEN if budgets are violated.
        """
        if count <= 0:
            return self.task_tokens

        with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                raise CircuitBreakerError(f"Cannot record tokens: Circuit breaker is OPEN ({self.trip_reason})")

            self.task_tokens += count
            self.session_tokens += count

            # Enforce hard session-level budget
            if self.session_tokens > self.session_token_budget:
                self._trip_unlocked(f"Session token budget exceeded: {self.session_tokens} > {self.session_token_budget}")
                raise TokenBudgetExceededError(self.trip_reason)

            # Enforce task-level budget
            if self.task_tokens > self.task_token_budget:
                # Attempt to cascade to fallback model if available
                if self.current_model_idx < len(self.fallback_models) - 1:
                    prev_model = self.fallback_models[self.current_model_idx]
                    self.current_model_idx += 1
                    new_model = self.fallback_models[self.current_model_idx]
                    self.state = CircuitBreakerState.FALLBACK
                    # Grant additional headroom for fallback model
                    self.task_token_budget += count
                    return self.task_tokens
                else:
                    self._trip_unlocked(f"Task token budget exhausted: {self.task_tokens} > {self.task_token_budget} with no remaining fallback models")
                    raise TokenBudgetExceededError(self.trip_reason)

            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.CLOSED

            return self.task_tokens

    def record_http_status(self, status_code: int, error_message: str = "") -> Optional[str]:
        """
        Records HTTP response status code. If HTTP 429 (rate limit) is encountered,
        triggers automated model cascade or trips breaker.
        Returns the active fallback model name if cascade occurred, or None.
        """
        with self._lock:
            if status_code == 429:
                if self.state == CircuitBreakerState.HALF_OPEN:
                    self._trip_unlocked(f"Probe request failed in HALF_OPEN with HTTP 429: {error_message}")
                    raise RateLimitExceededError(self.trip_reason)

                self.consecutive_429_count += 1
                if self.consecutive_429_count >= self.rate_limit_threshold:
                    if self.current_model_idx < len(self.fallback_models) - 1:
                        self.current_model_idx += 1
                        self.consecutive_429_count = 0
                        self.state = CircuitBreakerState.FALLBACK
                        return self._current_model_unlocked()
                    else:
                        self._trip_unlocked(f"Rate limit (HTTP 429) threshold exceeded ({self.consecutive_429_count}): {error_message}")
                        raise RateLimitExceededError(self.trip_reason)
            elif 200 <= status_code < 300:
                self.consecutive_429_count = 0
                if self.state == CircuitBreakerState.HALF_OPEN:
                    self.state = CircuitBreakerState.CLOSED
            elif status_code >= 500 and self.state == CircuitBreakerState.HALF_OPEN:
                self._trip_unlocked(f"Probe request failed in HALF_OPEN with HTTP {status_code}: {error_message}")
                raise RateLimitExceededError(self.trip_reason)

            return None

    def trip(self, reason: str):
        """Manually forces the circuit breaker into OPEN state."""
        with self._lock:
            self._trip_unlocked(reason)

    def _trip_unlocked(self, reason: str):
        self.state = CircuitBreakerState.OPEN
        self.tripped_timestamp = time.time()
        self.trip_reason = reason

    def reset(self):
        """Resets all token counters, error state, and restores CLOSED state."""
        with self._lock:
            self.state = CircuitBreakerState.CLOSED
            self.task_tokens = 0
            self.session_tokens = 0
            self.consecutive_429_count = 0
            self.current_model_idx = 0
            self.tripped_timestamp = 0.0
            self.trip_reason = ""

    def get_status(self) -> Dict[str, Any]:
        """Returns structured circuit breaker status."""
        with self._lock:
            return {
                "state": self.state.value,
                "active_model": self._current_model_unlocked(),
                "active_model_index": self.current_model_idx,
                "task_tokens": self.task_tokens,
                "task_token_budget": self.task_token_budget,
                "session_tokens": self.session_tokens,
                "session_token_budget": self.session_token_budget,
                "consecutive_429_count": self.consecutive_429_count,
                "trip_reason": self.trip_reason,
                "tripped_timestamp": self.tripped_timestamp,
            }

    @contextmanager
    def protect_execution(self, estimated_tokens: int = 0):
        """
        Context manager that gates execution through circuit breaker and records tokens.
        """
        allowed, reason = self.can_execute()
        if not allowed:
            raise CircuitBreakerError(reason)
        failed = False
        try:
            yield self.get_active_model()
        except Exception:
            failed = True
            raise
        finally:
            if not failed and estimated_tokens > 0:
                self.record_tokens(estimated_tokens)


# Global singleton instance for runtime interception
GLOBAL_CIRCUIT_BREAKER = TokenCircuitBreaker()


def record_tokens(count: int, model: Optional[str] = None) -> int:
    return GLOBAL_CIRCUIT_BREAKER.record_tokens(count, model=model)


def record_http_status(status_code: int, error_message: str = "") -> Optional[str]:
    return GLOBAL_CIRCUIT_BREAKER.record_http_status(status_code, error_message=error_message)


def can_execute() -> Tuple[bool, str]:
    return GLOBAL_CIRCUIT_BREAKER.can_execute()


def get_active_model() -> str:
    return GLOBAL_CIRCUIT_BREAKER.get_active_model()


def get_circuit_breaker() -> TokenCircuitBreaker:
    return GLOBAL_CIRCUIT_BREAKER


# ---------------------------------------------------------------------------
# Integrated Runaway & Turn-Loop Sentinel (Absorbed from runaway_stopper.py)
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLDS = {
    "max_turns": 30,
    "warn_turns": 20,
    "max_tokens": 150000,
    "warn_tokens": 100000,
    "max_repeated_calls": 3,
    "empty_turn_threshold": 4,
}


class RunawaySentinel:
    """Evaluates agent transcript turns to detect infinite loops and token blowouts."""

    def __init__(self, thresholds: Optional[Dict[str, int]] = None):
        self.thresholds = dict(DEFAULT_THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)

    def evaluate_transcript(self, turns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluates a list of turn records for budget and loop patterns."""
        turn_count = len(turns)
        total_tokens = sum(t.get("tokens_est", 0) for t in turns)
        flags = []
        verdict = "OK"

        if turn_count >= self.thresholds["max_turns"]:
            flags.append({
                "severity": "CRITICAL",
                "type": "TURN_LIMIT_EXCEEDED",
                "message": f"Turn count ({turn_count}) exceeded maximum threshold ({self.thresholds['max_turns']}).",
            })
            verdict = "STOP"
        elif turn_count >= self.thresholds["warn_turns"]:
            flags.append({
                "severity": "WARNING",
                "type": "TURN_LIMIT_WARNING",
                "message": f"Turn count ({turn_count}) approached warning threshold ({self.thresholds['warn_turns']}).",
            })
            if verdict == "OK":
                verdict = "WARN"

        if total_tokens >= self.thresholds["max_tokens"]:
            flags.append({
                "severity": "CRITICAL",
                "type": "TOKEN_BUDGET_EXCEEDED",
                "message": f"Estimated token usage ({total_tokens:,}) exceeded budget ({self.thresholds['max_tokens']:,}).",
            })
            verdict = "STOP"
        elif total_tokens >= self.thresholds["warn_tokens"]:
            flags.append({
                "severity": "WARNING",
                "type": "TOKEN_BUDGET_WARNING",
                "message": f"Estimated token usage ({total_tokens:,}) reached warning limit ({self.thresholds['warn_tokens']:,}).",
            })
            if verdict == "OK":
                verdict = "WARN"

        recent_commands = [
            (t.get("command") or t.get("tool_name") or t.get("tool") or t.get("name") or "")
            for t in turns
            if (t.get("command") or t.get("tool_name") or t.get("tool") or t.get("name"))
        ]
        if len(recent_commands) >= self.thresholds["max_repeated_calls"]:
            last_cmd = recent_commands[-1]
            repeat_count = 1
            for cmd in reversed(recent_commands[:-1]):
                if cmd == last_cmd and last_cmd:
                    repeat_count += 1
                else:
                    break
            if repeat_count >= self.thresholds["max_repeated_calls"]:
                flags.append({
                    "severity": "CRITICAL",
                    "type": "TOOL_LOOP_DETECTED",
                    "message": f"Command repeated {repeat_count} consecutive times: '{last_cmd[:60]}...'",
                })
                verdict = "STOP"

        empty_turns = 0
        for t in reversed(turns):
            if t.get("output_length", 1) == 0 and not t.get("tool_name"):
                empty_turns += 1
            else:
                break
        if empty_turns >= self.thresholds["empty_turn_threshold"]:
            flags.append({
                "severity": "CRITICAL",
                "type": "EMPTY_TURNS_LOOP",
                "message": f"Detected {empty_turns} consecutive empty turns without progress.",
            })
            verdict = "STOP"

        return {
            "verdict": verdict,
            "turn_count": turn_count,
            "total_tokens_est": total_tokens,
            "flags": flags,
            "is_runaway": verdict == "STOP",
        }
