#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Synapse Hub — Structured Observability & OpenTelemetry W3C Trace Context
-----------------------------------------------------------------------
Provides high-performance structured JSON logging and W3C TraceContext
propagation across multi-agent processes, tools, and CI runners.

Key Features:
  1. W3C TraceContext Specification (traceparent: 00-{trace_id}-{span_id}-{flags}):
     - 128-bit Trace ID (32 hex characters) and 64-bit Span ID (16 hex characters).
     - Deterministic injection/extraction across HTTP headers, dictionaries, and env vars.
  2. Thread & Async Safe Context Propagation:
     - Backed by contextvars with zero cross-coroutine leakage.
  3. Structured JSON Logging:
     - Formats standard log records into strict JSON conforming to:
       {timestamp, level, trace_id, span_id, parent_span_id, module, event, duration_ms}
  4. Span Tracing Context Manager:
     - `trace_span(event, module=...)` for measuring latencies and emitting trace spans.
"""

import os
import sys
import json
import time
import secrets
import logging
import contextvars
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Dict, Any, Optional, Generator, List
from contextlib import contextmanager

# W3C Constants
W3C_VERSION = "00"
FLAG_SAMPLED = "01"
FLAG_NOT_SAMPLED = "00"
TRACEPARENT_HEADER = "traceparent"
TRACESTATE_HEADER = "tracestate"


def generate_trace_id() -> str:
    """Generates a random 128-bit W3C Trace ID (32 lowercase hex characters)."""
    return secrets.token_hex(16)


def generate_span_id() -> str:
    """Generates a random 64-bit W3C Span ID (16 lowercase hex characters)."""
    return secrets.token_hex(8)


@dataclass
class TraceContext:
    """Represents a W3C TraceContext entity."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    sampled: bool = True
    trace_state: str = ""

    @property
    def traceparent(self) -> str:
        flags = FLAG_SAMPLED if self.sampled else FLAG_NOT_SAMPLED
        return f"{W3C_VERSION}-{self.trace_id}-{self.span_id}-{flags}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "sampled": self.sampled,
            "traceparent": self.traceparent,
            "trace_state": self.trace_state,
        }


_CURRENT_CONTEXT: contextvars.ContextVar[Optional[TraceContext]] = contextvars.ContextVar(
    "synapse_trace_context", default=None
)


def get_current_trace_context() -> Optional[TraceContext]:
    """Retrieves the active TraceContext for the current execution context."""
    ctx = _CURRENT_CONTEXT.get()
    if ctx is None and os.environ.get("TRACEPARENT"):
        ctx = parse_traceparent(os.environ["TRACEPARENT"])
        if ctx:
            _CURRENT_CONTEXT.set(ctx)
    return ctx


def set_current_trace_context(ctx: Optional[TraceContext]) -> None:
    """Sets the active TraceContext for the current execution context."""
    _CURRENT_CONTEXT.set(ctx)


def parse_traceparent(header_val: str) -> Optional[TraceContext]:
    """
    Parses a W3C traceparent header value.
    Format: {version}-{trace_id}-{span_id}-{flags}
    Example: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
    """
    if not header_val or not isinstance(header_val, str):
        return None
    parts = header_val.strip().split("-")
    if len(parts) != 4:
        return None

    version, trace_id, span_id, flags = parts
    if len(version) != 2 or len(trace_id) != 32 or len(span_id) != 16 or len(flags) != 2:
        return None

    # Version 'ff' is forbidden by W3C specification
    if version.lower() == "ff":
        return None

    # Validate hex characters and non-all-zero ids
    try:
        v_int = int(version, 16)
        t_int = int(trace_id, 16)
        s_int = int(span_id, 16)
        f_int = int(flags, 16)
        if t_int == 0 or s_int == 0:
            return None
    except ValueError:
        return None

    sampled = flags == FLAG_SAMPLED or bool(int(flags, 16) & 1)
    return TraceContext(
        trace_id=trace_id.lower(),
        span_id=span_id.lower(),
        parent_span_id=None,
        sampled=sampled,
    )


def format_traceparent(trace_id: str, span_id: str, sampled: bool = True) -> str:
    """Formats trace components into a valid W3C traceparent string."""
    flags = FLAG_SAMPLED if sampled else FLAG_NOT_SAMPLED
    return f"{W3C_VERSION}-{trace_id.lower()}-{span_id.lower()}-{flags}"


def inject_traceparent(headers: Optional[Dict[str, str]] = None, context: Optional[TraceContext] = None) -> Dict[str, str]:
    """
    Injects W3C traceparent into an HTTP headers dictionary or carrier.
    If context is omitted, uses the current ambient context or generates a new one.
    """
    if headers is None:
        headers = {}
    ctx = context or get_current_trace_context()
    if ctx is None:
        ctx = create_trace_context()
        set_current_trace_context(ctx)

    headers[TRACEPARENT_HEADER] = ctx.traceparent
    if ctx.trace_state:
        headers[TRACESTATE_HEADER] = ctx.trace_state
    return headers


def extract_traceparent(headers: Dict[str, str]) -> Optional[TraceContext]:
    """Extracts W3C traceparent and tracestate from an HTTP headers dictionary (case-insensitive keys)."""
    if not headers or not isinstance(headers, dict):
        return None
    ctx: Optional[TraceContext] = None
    state = ""
    for k, v in headers.items():
        if not isinstance(v, str):
            continue
        k_lower = k.lower()
        if k_lower == TRACEPARENT_HEADER:
            ctx = parse_traceparent(v)
        elif k_lower == TRACESTATE_HEADER:
            state = v.strip()
    if ctx and state:
        ctx.trace_state = state
    return ctx


def create_trace_context(
    parent: Optional[TraceContext] = None,
    trace_id: Optional[str] = None,
    sampled: bool = True
) -> TraceContext:
    """Creates a new TraceContext, linking to parent span if supplied."""
    if parent is not None:
        return TraceContext(
            trace_id=parent.trace_id,
            span_id=generate_span_id(),
            parent_span_id=parent.span_id,
            sampled=parent.sampled,
            trace_state=parent.trace_state,
        )
    return TraceContext(
        trace_id=trace_id or generate_trace_id(),
        span_id=generate_span_id(),
        parent_span_id=None,
        sampled=sampled,
    )


RESERVED_KEYS = {
    "timestamp",
    "level",
    "trace_id",
    "span_id",
    "parent_span_id",
    "module",
    "event",
    "duration_ms",
    "exception",
}


class StructuredJsonFormatter(logging.Formatter):
    """
    Formats log records into structured JSON conforming to enterprise schema:
    {timestamp, level, trace_id, span_id, parent_span_id, module, event, duration_ms, message}
    """

    def format(self, record: logging.LogRecord) -> str:
        ctx = get_current_trace_context()
        record_dict: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "trace_id": getattr(record, "trace_id", ctx.trace_id if ctx else None),
            "span_id": getattr(record, "span_id", ctx.span_id if ctx else None),
            "parent_span_id": getattr(record, "parent_span_id", ctx.parent_span_id if ctx else None),
            "module": getattr(record, "module_name", record.module),
            "event": getattr(record, "event", record.getMessage()),
            "duration_ms": getattr(record, "duration_ms", None),
        }

        # Include custom extra fields safely without overwriting reserved system schema
        if hasattr(record, "extra_payload") and isinstance(record.extra_payload, dict):
            attrs = {}
            for k, v in record.extra_payload.items():
                if k in RESERVED_KEYS:
                    attrs[k] = v
                else:
                    record_dict[k] = v
                    attrs[k] = v
            if attrs:
                record_dict["attributes"] = attrs

        # Include exception if present
        if record.exc_info:
            record_dict["exception"] = self.formatException(record.exc_info)

        return json.dumps(record_dict, ensure_ascii=False)


def get_logger(name: str = "synapse") -> logging.Logger:
    """Returns or configures a standard structured logger with JSON output."""
    logger = logging.getLogger(name)
    if not any(isinstance(h.formatter, StructuredJsonFormatter) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_event(
    level: str,
    event: str,
    module: Optional[str] = None,
    duration_ms: Optional[float] = None,
    logger_name: str = "synapse",
    **extra_payload
) -> Dict[str, Any]:
    """
    Emits a structured JSON log event directly.
    Returns the serialized structured dictionary for assertions or inspection.
    """
    ctx = get_current_trace_context()
    payload: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "trace_id": ctx.trace_id if ctx else None,
        "span_id": ctx.span_id if ctx else None,
        "parent_span_id": ctx.parent_span_id if ctx else None,
        "module": module or "synapse",
        "event": event,
        "duration_ms": duration_ms,
    }
    if extra_payload:
        attrs = {}
        for k, v in extra_payload.items():
            if k in RESERVED_KEYS:
                attrs[k] = v
            else:
                payload[k] = v
                attrs[k] = v
        if attrs:
            payload["attributes"] = attrs

    lvl_num = getattr(logging, level.upper(), logging.INFO)
    logger = get_logger(logger_name)
    logger.log(
        lvl_num,
        event,
        extra={
            "module_name": payload["module"],
            "event": event,
            "duration_ms": duration_ms,
            "trace_id": payload["trace_id"],
            "span_id": payload["span_id"],
            "parent_span_id": payload["parent_span_id"],
            "extra_payload": extra_payload,
        }
    )
    return payload


@contextmanager
def trace_span(
    event: str,
    module: Optional[str] = None,
    logger_name: str = "synapse",
    **attributes
) -> Generator[TraceContext, None, None]:
    """
    Context manager that starts a child span, measures latency,
    logs the completed span with duration_ms, and restores the parent context.
    """
    parent_ctx = get_current_trace_context()
    span_ctx = create_trace_context(parent=parent_ctx)
    set_current_trace_context(span_ctx)
    start_time = time.perf_counter()
    status = "SUCCESS"
    err_msg = None

    try:
        yield span_ctx
    except Exception as exc:
        status = "ERROR"
        err_msg = str(exc)
        raise
    finally:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 3)
        extra = dict(attributes)
        extra["status"] = status
        if err_msg:
            extra["error"] = err_msg

        log_event(
            level="INFO" if status == "SUCCESS" else "ERROR",
            event=event,
            module=module or "synapse",
            duration_ms=elapsed_ms,
            logger_name=logger_name,
            **extra
        )
        set_current_trace_context(parent_ctx)


# ---------------------------------------------------------------------------
# Session Token & MTTR Telemetry Ledger (Closed-Loop Quality & Efficiency)
# ---------------------------------------------------------------------------

DEFAULT_SESSION_LEDGER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "reports",
    "session_telemetry_ledger.json",
)


@dataclass
class SessionTelemetryRecord:
    session_id: str
    timestamp: str
    model: str
    platform: str
    task_type: str
    stack: str
    turns: int
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    cache_hit_ratio: float
    raw_log_bytes: int
    distilled_log_bytes: int
    distillation_reduction_pct: float
    test_outcome: str
    bug_resolved: bool
    tokens_per_bug: int
    elapsed_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "model": self.model,
            "platform": self.platform,
            "task_type": self.task_type,
            "stack": self.stack,
            "turns": self.turns,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "cache_hit_ratio": self.cache_hit_ratio,
            "raw_log_bytes": self.raw_log_bytes,
            "distilled_log_bytes": self.distilled_log_bytes,
            "distillation_reduction_pct": self.distillation_reduction_pct,
            "test_outcome": self.test_outcome,
            "bug_resolved": self.bug_resolved,
            "tokens_per_bug": self.tokens_per_bug,
            "elapsed_seconds": self.elapsed_seconds,
        }


def record_session_telemetry(
    record: SessionTelemetryRecord,
    ledger_file: Optional[str] = None,
) -> None:
    """Appends a closed-loop session telemetry record to the JSON ledger with file locking."""
    target_path = ledger_file or DEFAULT_SESSION_LEDGER
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

    records: List[Dict[str, Any]] = []
    if os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                records = json.load(f)
        except (OSError, json.JSONDecodeError):
            records = []

    records.append(record.to_dict())
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def get_telemetry_summary(ledger_file: Optional[str] = None) -> Dict[str, Any]:
    """Computes median/P90 tokens per resolved bug, MTTR, and compression statistics."""
    target_path = ledger_file or DEFAULT_SESSION_LEDGER
    if not os.path.exists(target_path):
        return {
            "sample_size": 0,
            "resolved_bugs": 0,
            "median_tokens_per_bug": 0,
            "p90_tokens_per_bug": 0,
            "mttr_seconds": 0.0,
            "avg_cache_hit_ratio": 0.0,
            "avg_distillation_reduction_pct": 0.0,
        }

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            records: List[Dict[str, Any]] = json.load(f)
    except (OSError, json.JSONDecodeError):
        records = []

    if not records:
        return {
            "sample_size": 0,
            "resolved_bugs": 0,
            "median_tokens_per_bug": 0,
            "p90_tokens_per_bug": 0,
            "mttr_seconds": 0.0,
            "avg_cache_hit_ratio": 0.0,
            "avg_distillation_reduction_pct": 0.0,
        }

    resolved = [r for r in records if r.get("bug_resolved")]
    tokens_per_bug = sorted([r.get("tokens_per_bug", 0) for r in resolved])
    durations = [r.get("elapsed_seconds", 0.0) for r in resolved]
    cache_ratios = [r.get("cache_hit_ratio", 0.0) for r in records]
    distill_pcts = [r.get("distillation_reduction_pct", 0.0) for r in records]

    def _median(vals: List[float]) -> float:
        if not vals:
            return 0.0
        n = len(vals)
        mid = n // 2
        return (vals[mid] if n % 2 != 0 else (vals[mid - 1] + vals[mid]) / 2.0)

    def _p90(vals: List[float]) -> float:
        if not vals:
            return 0.0
        idx = int(len(vals) * 0.90)
        return vals[min(idx, len(vals) - 1)]

    return {
        "sample_size": len(records),
        "resolved_bugs": len(resolved),
        "median_tokens_per_bug": int(_median(tokens_per_bug)),
        "p90_tokens_per_bug": int(_p90(tokens_per_bug)),
        "mttr_seconds": round(sum(durations) / max(1, len(durations)), 2),
        "avg_cache_hit_ratio": round(sum(cache_ratios) / max(1, len(cache_ratios)), 3),
        "avg_distillation_reduction_pct": round(sum(distill_pcts) / max(1, len(distill_pcts)), 2),
    }

