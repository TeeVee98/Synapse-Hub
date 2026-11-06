# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""Unit tests for tools/core/adapters.py (Unified Memory Bus Adapters)."""

import os
import sys
import tempfile
import shutil
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
CORE_DIR = os.path.join(TOOLS_DIR, "core")
for p in (TOOLS_DIR, CORE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from memory_bus import UnifiedMemoryBus
from autogen_qa_broker import ActorQaBroker
from qa_event_stream import QaEventStream
from test_memory_os import TestMemoryOS
from tools.core.adapters import (
    BrokerMemoryBusAdapter,
    EventStreamMemoryBusAdapter,
    TestMemoryOSAdapter
)


@pytest.fixture
def bus():
    """In-memory UnifiedMemoryBus for isolated testing."""
    mb = UnifiedMemoryBus(db_path=":memory:")
    yield mb
    mb.close()


def test_broker_memory_bus_adapter_messaging(bus):
    adapter = BrokerMemoryBusAdapter(bus=bus)
    r = adapter.send_message(
        from_actor="test-runner",
        to_actor="failure-analyst",
        topic="TEST_FAILED",
        payload={"test": "login.spec.ts", "error": "timeout"}
    )
    assert r["status"] == "PASS"
    assert "message_id" in r

    msgs = adapter.fetch_messages("failure-analyst", mark_read=True)
    assert len(msgs) == 1
    assert msgs[0]["from_actor"] == "test-runner"
    assert msgs[0]["topic"] == "TEST_FAILED"
    assert msgs[0]["payload"]["test"] == "login.spec.ts"
    assert msgs[0]["read"] is True


def test_broker_memory_bus_adapter_pubsub(bus):
    adapter = BrokerMemoryBusAdapter(bus=bus)
    adapter.subscribe("failure-analyst", "MUTATION_ALERT")
    adapter.subscribe("pom-crafter", "MUTATION_ALERT")

    pub_res = adapter.publish("MUTATION_ALERT", {"mutant_id": "MUT-0001", "survived": True})
    assert pub_res["status"] == "PASS"
    assert pub_res["delivered_count"] == 2

    fa_msgs = adapter.fetch_messages("failure-analyst")
    pom_msgs = adapter.fetch_messages("pom-crafter")
    assert len(fa_msgs) == 1
    assert len(pom_msgs) == 1


def test_actor_qa_broker_delegation_to_bus(bus):
    broker = ActorQaBroker(use_memory_bus=True, memory_bus=bus)
    assert broker._bus_adapter is not None

    broker.send_message("lead-qa", "live-explorer", "PROBE_PAGE", {"url": "https://example.com"})
    msgs = broker.fetch_messages("live-explorer")
    assert len(msgs) == 1
    assert msgs[0]["topic"] == "PROBE_PAGE"

    health = broker.check_health()
    assert health["status"] == "PASS"
    assert health["backend"] == "UnifiedMemoryBus"

    # Verify state property delegation to UnifiedMemoryBus
    state = broker.state
    assert "live-explorer" in state["mailboxes"]
    assert len(state["mailboxes"]["live-explorer"]) == 1
    assert state["mailboxes"]["live-explorer"][0]["topic"] == "PROBE_PAGE"


def test_event_stream_memory_bus_adapter(bus):
    adapter = EventStreamMemoryBusAdapter(bus=bus)
    init_res = adapter.init_stream("TEST_SESSION_01")
    assert init_res["status"] == "PASS"
    assert "genesis_hash" in init_res

    adapter.record_event("stream_01", "ACTION_CLICK", "live-explorer", {"target": "#btn"})
    adapter.record_event("stream_01", "CHECKPOINT", "system", {"checkpoint_id": "CP1"}, checkpoint_id="CP1")
    adapter.record_event("stream_01", "ACTION_TYPE", "live-explorer", {"text": "hello"})

    ver_res = adapter.verify_stream("stream_01")
    assert ver_res["status"] == "PASS"
    assert ver_res["valid"] is True
    assert ver_res["events_verified"] >= 3

    # Rollback to CP1
    rb = adapter.rollback("stream_01", "CP1")
    assert rb["status"] == "PASS"
    assert rb["rolled_back_to"] == "CP1"


def test_qa_event_stream_delegation_to_bus(bus):
    engine = QaEventStream(use_memory_bus=True, memory_bus=bus)
    assert engine._bus_adapter is not None

    init = engine.init_stream("SESS_DELEGATE", "out.jsonl")
    assert init["status"] == "PASS"

    rec = engine.record_event("SESS_DELEGATE", "ACTION_NAVIGATE", "live-explorer", {"url": "/home"})
    assert rec["status"] == "PASS"

    ver = engine.verify_stream("SESS_DELEGATE")
    assert ver["status"] == "PASS"
    assert ver["valid"] is True


def test_test_memory_os_adapter_core_recall_archival(bus):
    adapter = TestMemoryOSAdapter(bus=bus)

    # Core
    adapter.update_core("auth_token", {"token": "secret_jwt", "expires": 3600})
    core = adapter.get_core("auth_token")
    assert core is not None
    assert core["data"]["token"] == "secret_jwt"

    # Recall
    adapter.record_recall_step("SESS_RECALL", "CLICK", "live-explorer", {"elem": "#submit"})
    history = adapter.get_recall_history("SESS_RECALL")
    assert len(history) == 1
    assert history[0]["actor"] == "live-explorer"

    # Archival
    adapter.archival_insert("LOCATOR_FIX", {"page": "LoginPage", "locator": "getByRole('button')"}, aut_version="v2.1")
    search_res = adapter.archival_search("LoginPage", aut_version="v2.1")
    assert len(search_res) >= 1
    assert search_res[0]["payload"]["page"] == "LoginPage"


def test_test_memory_os_delegation_to_bus(bus):
    mem = TestMemoryOS(use_memory_bus=True, memory_bus=bus)
    assert mem._bus_adapter is not None

    mem.update_core("env_config", {"base_url": "http://localhost:3000"})
    res = mem.get_core("env_config")
    assert res is not None
    assert res["data"]["base_url"] == "http://localhost:3000"

    seq = mem.recall_insert("SESS_TEST", "TYPE", "live-explorer", {"text": "admin"})
    assert seq >= 1
    rec_log = mem.recall_log("SESS_TEST")
    assert len(rec_log) == 1

    mem.archival_insert("FLAKY_PATTERN", {"test": "Checkout", "fix": "smart_wait"}, aut_version="v3.0")
    results = mem.archival_search("Checkout", aut_version="v3.0")
    assert len(results["matches"]) >= 1

    # Verify list_core and gc delegation
    core_list = mem.list_core()
    assert len(core_list) >= 1
    assert any(b["block_key"] == "env_config" for b in core_list)

    gc_res = mem.gc()
    assert gc_res["status"] == "PASS"
    assert gc_res["backend"] == "UnifiedMemoryBus"
