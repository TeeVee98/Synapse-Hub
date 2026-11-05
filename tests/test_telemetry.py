#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Unit tests for tools/core/telemetry.py (Structured Observability & OpenTelemetry W3C)
"""

import json
import logging
import unittest
from tools.core.telemetry import (
    TraceContext,
    generate_trace_id,
    generate_span_id,
    format_traceparent,
    parse_traceparent,
    inject_traceparent,
    extract_traceparent,
    create_trace_context,
    get_current_trace_context,
    set_current_trace_context,
    StructuredJsonFormatter,
    get_logger,
    log_event,
    trace_span,
    TRACEPARENT_HEADER,
)


class TestTelemetry(unittest.TestCase):
    def setUp(self):
        set_current_trace_context(None)

    def tearDown(self):
        set_current_trace_context(None)

    def test_generate_ids(self):
        trace_id = generate_trace_id()
        self.assertEqual(len(trace_id), 32)
        self.assertTrue(all(c in "0123456789abcdef" for c in trace_id))

        span_id = generate_span_id()
        self.assertEqual(len(span_id), 16)
        self.assertTrue(all(c in "0123456789abcdef" for c in span_id))

    def test_w3c_traceparent_format_and_parse(self):
        t_id = "4bf92f3577b34da6a3ce929d0e0e4736"
        s_id = "00f067aa0ba902b7"
        tp = format_traceparent(t_id, s_id, sampled=True)
        self.assertEqual(tp, f"00-{t_id}-{s_id}-01")

        parsed = parse_traceparent(tp)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.trace_id, t_id)
        self.assertEqual(parsed.span_id, s_id)
        self.assertTrue(parsed.sampled)

        # Invalid traceparent tests
        self.assertIsNone(parse_traceparent(""))
        self.assertIsNone(parse_traceparent("invalid"))
        self.assertIsNone(parse_traceparent("00-short-short-01"))
        # All zeros are illegal in W3C
        self.assertIsNone(parse_traceparent("00-00000000000000000000000000000000-0000000000000000-01"))

    def test_inject_and_extract_traceparent(self):
        ctx = create_trace_context()
        headers = {}
        inject_traceparent(headers, context=ctx)
        self.assertIn(TRACEPARENT_HEADER, headers)
        self.assertEqual(headers[TRACEPARENT_HEADER], ctx.traceparent)

        extracted = extract_traceparent(headers)
        self.assertIsNotNone(extracted)
        self.assertEqual(extracted.trace_id, ctx.trace_id)
        self.assertEqual(extracted.span_id, ctx.span_id)

    def test_child_context_creation(self):
        parent = create_trace_context()
        child = create_trace_context(parent=parent)
        self.assertEqual(child.trace_id, parent.trace_id)
        self.assertNotEqual(child.span_id, parent.span_id)
        self.assertEqual(child.parent_span_id, parent.span_id)

    def test_trace_span_context_manager(self):
        parent_ctx = create_trace_context()
        set_current_trace_context(parent_ctx)

        with trace_span("unit_test_operation", module="test_module", custom_attr="val") as span:
            self.assertEqual(span.trace_id, parent_ctx.trace_id)
            self.assertEqual(span.parent_span_id, parent_ctx.span_id)
            self.assertEqual(get_current_trace_context().span_id, span.span_id)

        # Context restored after exit
        self.assertEqual(get_current_trace_context().span_id, parent_ctx.span_id)

    def test_structured_json_formatter(self):
        formatter = StructuredJsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="User %s logged in",
            args=("alice",),
            exc_info=None,
        )
        record.module_name = "auth"
        record.event = "user_login"
        record.duration_ms = 42.5

        formatted_json = formatter.format(record)
        data = json.loads(formatted_json)
        self.assertIn("timestamp", data)
        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["module"], "auth")
        self.assertEqual(data["event"], "user_login")
        self.assertEqual(data["duration_ms"], 42.5)

    def test_log_event_direct(self):
        res = log_event(
            level="WARN",
            event="disk_space_low",
            module="infra",
            duration_ms=12.3,
            free_gb=1.5,
        )
        self.assertEqual(res["level"], "WARN")
        self.assertEqual(res["event"], "disk_space_low")
        self.assertEqual(res["module"], "infra")
        self.assertEqual(res["duration_ms"], 12.3)
        self.assertEqual(res["free_gb"], 1.5)


if __name__ == "__main__":
    unittest.main()
