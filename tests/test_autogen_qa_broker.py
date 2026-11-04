# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""Unit tests for tools/autogen_qa_broker.py (AutoGen v0.4+ Actor QA Message Broker)."""

import os
import sys
import tempfile
import shutil
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from autogen_qa_broker import ActorQaBroker


@pytest.fixture
def temp_broker_dir():
    tmp_dir = tempfile.mkdtemp()
    state_file = os.path.join(tmp_dir, "actor_broker.json")
    yield state_file
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_send_and_fetch_messages(temp_broker_dir):
    broker = ActorQaBroker(state_file=temp_broker_dir)
    res = broker.send_message(
        from_actor="test-runner",
        to_actor="failure-analyst",
        topic="TEST_FAILED",
        payload={"test": "checkout.spec.ts", "line": 42}
    )
    assert res["status"] == "PASS"
    assert res["to"] == "failure-analyst"

    # Fetch messages
    msgs = broker.fetch_messages("failure-analyst")
    assert len(msgs) == 1
    assert msgs[0]["topic"] == "TEST_FAILED"
    assert msgs[0]["payload"]["line"] == 42


def test_pub_sub_event_dispatch(temp_broker_dir):
    broker = ActorQaBroker(state_file=temp_broker_dir)
    broker.subscribe("failure-analyst", "TEST_FAILED")
    broker.subscribe("orchestrator", "TEST_FAILED")

    pub_res = broker.publish("TEST_FAILED", {"error": "TimeoutError"}, sender="worker_1")
    assert pub_res["status"] == "PASS"
    assert pub_res["subscribers_notified"] == 2

    # Verify both actors received the event
    fa_msgs = broker.fetch_messages("failure-analyst")
    orch_msgs = broker.fetch_messages("orchestrator")
    assert len(fa_msgs) == 1
    assert len(orch_msgs) == 1


def test_dispatch_shards(temp_broker_dir):
    broker = ActorQaBroker(state_file=temp_broker_dir)
    res = broker.dispatch_shards("non_existent_manifest.json", shard_count=4, worker_role="test-runner")

    assert res["status"] == "PASS"
    assert res["shard_count"] == 4
    assert res["total_tests"] == 12
    assert res["shards"]["worker_1"] == 3


def test_check_health(temp_broker_dir):
    broker = ActorQaBroker(state_file=temp_broker_dir)
    health = broker.check_health()
    assert health["status"] == "PASS"
    assert health["deadlock_free"] is True
