#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

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
import uuid
import secrets
import logging
import contextvars
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Generator
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

        # Include custom extra fields
        if hasattr(record, "extra_payload") and isinstance(record.extra_payload, dict):
            record_dict.update(record.extra_payload)

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
        payload.update(extra_payload)

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
