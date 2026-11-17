# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests for tools/autogen_qa_broker.py (AutoGen v0.4+ Actor QA Message Broker)."""

import os
import sys
import json
import time
import tempfile
import shutil
import pytest
from concurrent.futures import ThreadPoolExecutor

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from autogen_qa_broker import (
    ActorQaBroker,
    StorageBackend,
    SQLiteStorageBackend,
    RedisStorageBackend,
)


@pytest.fixture
def temp_broker_dir():
    tmp_dir = tempfile.mkdtemp()
    state_file = os.path.join(tmp_dir, "actor_broker.db")
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
    assert msgs[0]["read"] is True

    # Fetch again should return already-read messages
    msgs_after = broker.fetch_messages("failure-analyst")
    assert len(msgs_after) == 1
    assert msgs_after[0]["read"] is True


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


def test_dispatch_shards_with_real_manifest(temp_broker_dir):
    broker = ActorQaBroker(state_file=temp_broker_dir)
    manifest_path = os.path.join(os.path.dirname(temp_broker_dir), "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(["test1.spec.ts", "test2.spec.ts", "test3.spec.ts", "test4.spec.ts"], f)

    res = broker.dispatch_shards(manifest_path, shard_count=2, worker_role="test-runner")
    assert res["status"] == "PASS"
    assert res["shard_count"] == 2
    assert res["total_tests"] == 4
    assert res["shards"]["worker_1"] == 2
    assert res["shards"]["worker_2"] == 2


def test_dispatch_shards_fail_closed_on_missing_manifest(temp_broker_dir):
    broker = ActorQaBroker(state_file=temp_broker_dir)
    # Without allow_mock, must fail closed
    res = broker.dispatch_shards("non_existent_manifest.json", shard_count=4, allow_mock=False)
    assert res["status"] == "FAIL"
    assert "not found" in res["error"].lower()

    # With allow_mock=True, falls back explicitly
    mock_res = broker.dispatch_shards("non_existent_manifest.json", shard_count=4, allow_mock=True)
    assert mock_res["status"] == "PASS"
    assert mock_res["total_tests"] == 12


def test_check_health_and_timeout(temp_broker_dir):
    broker = ActorQaBroker(state_file=temp_broker_dir)
    health = broker.check_health()
    assert health["status"] == "PASS"
    assert health["deadlock_free"] is True

    # Send an unread message and check with 0s timeout
    broker.send_message("worker", "tester", "PING", {})
    time.sleep(0.05)
    expired_health = broker.check_health(timeout_sec=0.01)
    assert expired_health["status"] == "WARNING_DEADLOCK"
    assert expired_health["deadlock_free"] is False
    assert "timeout ceiling exceeded" in expired_health["warning"]


def test_concurrent_message_safety_zero_loss(temp_broker_dir):
    """Verifies that concurrent workers sending messages simultaneously lose 0 messages."""
    broker = ActorQaBroker(state_file=temp_broker_dir)
    worker_count = 20

    def worker_send(idx):
        b = ActorQaBroker(state_file=temp_broker_dir)
        return b.send_message(
            from_actor=f"worker_{idx}",
            to_actor="collector",
            topic="DATA_CHUNK",
            payload={"worker_id": idx, "val": idx * 10}
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(worker_send, range(worker_count)))

    assert len(results) == worker_count
    for r in results:
        assert r["status"] == "PASS"

    messages = broker.fetch_messages("collector", mark_read=False)
    assert len(messages) == worker_count, f"Expected {worker_count} messages, got {len(messages)}"


def test_independent_os_processes_concurrency(temp_broker_dir):
    """Verifies that independent OS processes sending messages concurrently lose 0 messages."""
    import subprocess
    broker = ActorQaBroker(state_file=temp_broker_dir)
    proc_count = 15

    # Run separate python processes that write to the same broker
    code = f"""
import sys
sys.path.insert(0, r'{TOOLS_DIR}')
from autogen_qa_broker import (
    ActorQaBroker,
    StorageBackend,
    SQLiteStorageBackend,
    RedisStorageBackend,
)
b = ActorQaBroker(r'{temp_broker_dir}')
b.send_message('external_proc', 'main_agent', 'STATUS', {{'pid': sys.argv[1]}})
"""
    procs = []
    for i in range(proc_count):
        p = subprocess.Popen([sys.executable, "-c", code, str(i)])
        procs.append(p)

    for p in procs:
        p.wait()
        assert p.returncode == 0

    msgs = broker.fetch_messages("main_agent", mark_read=False)
    assert len(msgs) == proc_count, f"Expected {proc_count} messages from independent processes, got {len(msgs)}"


class MockRedisClient:
    """In-memory dictionary-backed mock for Redis client methods used by RedisStorageBackend."""

    def __init__(self):
        self.strings = {}
        self.lists = {}
        self.sets = {}
        self.hashes = {}

    def ping(self):
        return True

    def set(self, key, value):
        self.strings[key] = str(value)
        return True

    def get(self, key):
        return self.strings.get(key)

    def rpush(self, key, *values):
        if key not in self.lists:
            self.lists[key] = []
        for v in values:
            self.lists[key].append(str(v))
        return len(self.lists[key])

    def lrange(self, key, start, end):
        lst = self.lists.get(key, [])
        if end == -1 or end >= len(lst):
            return lst[start:]
        return lst[start : end + 1]

    def sadd(self, key, *members):
        if key not in self.sets:
            self.sets[key] = set()
        added = 0
        for m in members:
            if str(m) not in self.sets[key]:
                self.sets[key].add(str(m))
                added += 1
        return added

    def scard(self, key):
        return len(self.sets.get(key, set()))

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    def hset(self, key, field, value):
        if key not in self.hashes:
            self.hashes[key] = {}
        self.hashes[key][str(field)] = str(value)
        return 1

    def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    def keys(self, pattern):
        import fnmatch
        all_keys = list(self.strings.keys()) + list(self.lists.keys()) + list(self.sets.keys()) + list(self.hashes.keys())
        return [k for k in set(all_keys) if fnmatch.fnmatch(k, pattern)]


def test_sqlite_storage_backend_property(temp_broker_dir):
    """Verifies that default ActorQaBroker instantiates SQLiteStorageBackend correctly."""
    broker = ActorQaBroker(state_file=temp_broker_dir)
    assert isinstance(broker.backend, StorageBackend)
    assert isinstance(broker.backend, SQLiteStorageBackend)
    assert broker.backend.state_file == temp_broker_dir

    # Verify state structure
    state = broker.state
    assert "mailboxes" in state
    assert "subscriptions" in state
    assert "metadata" in state


def test_redis_storage_backend_with_mock():
    """Verifies complete messaging lifecycle through RedisStorageBackend using mock client."""
    mock_client = MockRedisClient()
    backend = RedisStorageBackend(client=mock_client)
    broker = ActorQaBroker(backend=backend)

    # 1. Send messages
    res1 = broker.send_message(
        from_actor="test-runner",
        to_actor="quality-gatekeeper",
        topic="GATE_READY",
        payload={"gate": 9, "status": "PENDING"}
    )
    assert res1["status"] == "PASS"

    res2 = broker.send_message(
        from_actor="orchestrator",
        to_actor="quality-gatekeeper",
        topic="GATE_READY",
        payload={"gate": 10, "status": "PENDING"}
    )
    assert res2["status"] == "PASS"

    # 2. Fetch messages with topic filter and read marking
    msgs = broker.fetch_messages("quality-gatekeeper", topic="GATE_READY", mark_read=True)
    assert len(msgs) == 2
    assert msgs[0]["payload"]["gate"] == 9
    assert msgs[0]["read"] is True

    # 3. Pub/Sub subscription and event publishing
    sub_res = broker.subscribe("live-explorer", "PROBE_TRIGGERED")
    assert sub_res["status"] == "PASS"
    assert sub_res["total_subscribers"] == 1

    pub_res = broker.publish("PROBE_TRIGGERED", {"url": "https://synapse.local"})
    assert pub_res["status"] == "PASS"
    assert pub_res["subscribers_notified"] == 1

    received = broker.fetch_messages("live-explorer")
    assert len(received) == 1
    assert received[0]["payload"]["url"] == "https://synapse.local"

    # 4. Health check
    health = broker.check_health()
    assert health["status"] == "PASS"
    assert health["deadlock_free"] is True
    assert health["active_actors"] >= 2


def test_redis_storage_backend_missing_package_error():
    """Verifies that RedisStorageBackend raises RuntimeError if redis package is not installed."""
    import importlib.util
    if importlib.util.find_spec("redis") is None:
        with pytest.raises(RuntimeError, match="redis package is required"):
            RedisStorageBackend(redis_url="redis://nonexistent-host:6379/0")


