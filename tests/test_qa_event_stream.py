# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""Unit tests for tools/qa_event_stream.py (OpenHands EventStream Pattern)."""

import os
import sys
import tempfile
import shutil
import json
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from qa_event_stream import QaEventStream


@pytest.fixture
def temp_stream_dir():
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_init_stream(temp_stream_dir):
    engine = QaEventStream(repo_root=temp_stream_dir)
    stream_file = os.path.join(temp_stream_dir, "timeline.jsonl")
    res = engine.init_stream(session_id="SESS_TEST_01", out_file=stream_file)

    assert res["status"] == "PASS"
    assert os.path.exists(stream_file)

    # Verify genesis line
    with open(stream_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["event_type"] == "STREAM_INIT"
    assert data["prev_hash"] == "0" * 64


def test_record_event_and_hash_chain(temp_stream_dir):
    engine = QaEventStream(repo_root=temp_stream_dir)
    stream_file = os.path.join(temp_stream_dir, "timeline.jsonl")
    engine.init_stream(session_id="SESS_TEST_02", out_file=stream_file)

    # Record event 1
    ev1 = engine.record_event(
        stream_file=stream_file,
        event_type="ACTION_NAVIGATE",
        actor="live-explorer",
        payload={"url": "/home"}
    )
    assert ev1["status"] == "PASS"
    assert ev1["index"] == 1

    # Record event 2 with checkpoint
    ev2 = engine.record_event(
        stream_file=stream_file,
        event_type="CHECKPOINT",
        actor="test-runner",
        payload={"state": "logged_in"},
        checkpoint_id="CHK_LOGIN"
    )
    assert ev2["status"] == "PASS"
    assert ev2["prev_hash"] == ev1["event_hash"]

    # Verify stream integrity
    v_res = engine.verify_stream(stream_file=stream_file)
    assert v_res["status"] == "PASS"
    assert v_res["verified"] is True
    assert v_res["events_verified"] == 3


def test_verify_stream_tamper_detection(temp_stream_dir):
    engine = QaEventStream(repo_root=temp_stream_dir)
    stream_file = os.path.join(temp_stream_dir, "timeline.jsonl")
    engine.init_stream(session_id="SESS_TEST_03", out_file=stream_file)

    engine.record_event(stream_file, "ACTION_CLICK", "live-explorer", {"btn": "save"})
    engine.record_event(stream_file, "ACTION_CLICK", "live-explorer", {"btn": "submit"})

    # Tamper with the second event payload
    with open(stream_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    tampered_event = json.loads(lines[1])
    tampered_event["payload"]["btn"] = "TAMPERED_BUTTON"
    lines[1] = json.dumps(tampered_event) + "\n"

    with open(stream_file, "w", encoding="utf-8") as f:
        f.writelines(lines)

    # Verification must catch the hash tamper
    v_res = engine.verify_stream(stream_file=stream_file)
    assert v_res["status"] == "FAIL"
    assert v_res["verified"] is False
    assert "tamper" in v_res["error"].lower()


def test_rollback_to_checkpoint(temp_stream_dir):
    engine = QaEventStream(repo_root=temp_stream_dir)
    stream_file = os.path.join(temp_stream_dir, "timeline.jsonl")
    engine.init_stream(session_id="SESS_TEST_04", out_file=stream_file)

    # Checkpoint
    engine.record_event(stream_file, "CHECKPOINT", "system", {"balance": 1000}, checkpoint_id="CHK_PRE_PAY")
    # Action
    engine.record_event(stream_file, "ACTION_CLICK", "live-explorer", {"btn": "pay"})
    # Error
    engine.record_event(stream_file, "ERROR_OCCURRED", "test-runner", {"code": 500})

    # Rollback to CHK_PRE_PAY
    rb_res = engine.rollback(stream_file=stream_file, to_checkpoint="CHK_PRE_PAY")
    assert rb_res["status"] == "PASS"
    assert rb_res["to_checkpoint"] == "CHK_PRE_PAY"
    assert rb_res["events_rewound"] == 2
    assert rb_res["restored_state"]["balance"] == 1000

    # Verify stream remains cryptographically valid after rollback event append
    v_res = engine.verify_stream(stream_file=stream_file)
    assert v_res["status"] == "PASS"
    assert v_res["verified"] is True
