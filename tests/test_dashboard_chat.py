# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""Unit tests for Dashboard QA Chat endpoints (tests/test_dashboard_chat.py).

Verifies /api/chat POST routing, standard default framework responses,
and /api/chat/stream SSE responses.

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

import json
from io import BytesIO
from unittest.mock import MagicMock

from tools.dashboard.serve_dashboard import DashboardHTTPHandler


def create_mock_handler(method="POST", path="/api/chat", body=b""):
    handler = DashboardHTTPHandler.__new__(DashboardHTTPHandler)
    handler.command = method
    handler.path = path
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = BytesIO(body)
    handler.wfile = BytesIO()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler


def test_dashboard_chat_post_routing():
    body_data = json.dumps({"message": "Perform root cause analysis on flaky login test"}).encode("utf-8")
    handler = create_mock_handler(method="POST", path="/api/chat", body=body_data)
    handler.do_POST()

    assert handler.send_response.called
    response_code = handler.send_response.call_args[0][0]
    assert response_code == 200

    raw_output = handler.wfile.getvalue().decode("utf-8")
    res = json.loads(raw_output)
    assert res["status"] == "SUCCESS"
    assert "route_decision" in res
    assert res["route_decision"]["tier"] == "pro"
    assert "gemini-4-neon" in res["reply"]


def test_dashboard_chat_stream_get():
    handler = create_mock_handler(method="GET", path="/api/chat/stream?q=run+smoke+test")
    handler.do_GET()

    assert handler.send_response.called
    response_code = handler.send_response.call_args[0][0]
    assert response_code == 200

    raw_output = handler.wfile.getvalue().decode("utf-8")
    assert "data: " in raw_output
    assert "Routing task" in raw_output


def test_dashboard_chat_post_action_trigger():
    body_data = json.dumps({"message": "Chạy fast gate kiểm tra chất lượng"}).encode("utf-8")
    handler = create_mock_handler(method="POST", path="/api/chat", body=body_data)
    handler.do_POST()

    assert handler.send_response.called
    raw_output = handler.wfile.getvalue().decode("utf-8")
    res = json.loads(raw_output)
    assert res["status"] == "SUCCESS"
    assert res["action"] == "fast-gate"
    assert "job" in res
    assert "job_status" in res["job"]
    assert "Mission Control" in res["reply"]


def test_dashboard_chat_default_framework_response():
    body_data = json.dumps({"message": "Hệ thống hỗ trợ những tính năng gì?"}).encode("utf-8")
    handler = create_mock_handler(method="POST", path="/api/chat", body=body_data)
    handler.do_POST()

    assert handler.send_response.called
    raw_output = handler.wfile.getvalue().decode("utf-8")
    res = json.loads(raw_output)
    assert res["status"] == "SUCCESS"
    assert res["action"] is None
    assert "trợ lý kiểm định chất lượng Synapse Hub" in res["reply"]
    assert "Định tuyến tính toán" in res["reply"]
    assert "QA Hub" in res["reply"]
    assert "10 DoD Quality Gates" in res["reply"]


def test_dashboard_chat_empty_message_boundary():
    body_data = json.dumps({"message": ""}).encode("utf-8")
    handler = create_mock_handler(method="POST", path="/api/chat", body=body_data)
    handler.do_POST()

    assert handler.send_response.called
    raw_output = handler.wfile.getvalue().decode("utf-8")
    res = json.loads(raw_output)
    assert res["status"] == "SUCCESS"


def test_dashboard_latest_job_endpoint():
    handler = create_mock_handler(method="GET", path="/api/jobs/latest")
    handler.do_GET()

    assert handler.send_response.called
    assert handler.send_response.call_args[0][0] == 200
    raw_output = handler.wfile.getvalue().decode("utf-8")
    res = json.loads(raw_output)
    assert "status" in res
    assert "lines" in res
