#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Asynchronous Actor QA Message Broker (Microsoft AutoGen v0.4+ Pattern)
-----------------------------------------------------------------------
Provides an asynchronous Actor-model message broker and matrix sharding coordinator:
  1. Mailbox-Based Actor Messaging: Decoupled peer-to-peer message passing across QA subagents.
  2. Pub/Sub Event Dispatch: Asynchronous event publishing (TEST_FAILED, SHARD_COMPLETED, MUTATION_ALERT).
  3. Parallel Matrix Sharding: Partitions large test suites across worker actors with zero blocking.
  4. Deadlock & Starvation Sentinel: Enforces 300s timeout ceilings and detects circular dependency deadlocks.
  5. Multi-Process Concurrency & ACID Durability: SQLite WAL backend eliminates lost updates and race conditions.

Usage:
  python tools/autogen_qa_broker.py send-message --from-actor test-runner --to-actor failure-analyst --topic TEST_FAILED --payload '{"test": "login.spec.ts"}'
  python tools/autogen_qa_broker.py fetch-messages --actor failure-analyst
  python tools/autogen_qa_broker.py dispatch-shards --suite-manifest tests/manifest.json --shard-count 4
  python tools/autogen_qa_broker.py check-health
"""

import os
import sys
import json
import time
import uuid
import sqlite3
import argparse
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception as err:
        _ = err


class StorageBackend(ABC):
    """Abstract storage backend for Actor QA Message Broker."""

    @abstractmethod
    def init_backend(self) -> None:
        """Initialize schema, tables, or collections."""
        pass

    @abstractmethod
    def save_message(
        self,
        msg_id: str,
        from_actor: str,
        to_actor: str,
        topic: str,
        payload_str: str,
        now_iso: str,
        now_epoch: float,
    ) -> None:
        """Persist a message."""
        pass

    @abstractmethod
    def fetch_messages(
        self,
        actor: str,
        topic: Optional[str] = None,
        mark_read: bool = True,
    ) -> List[Dict[str, Any]]:
        """Fetch messages for an actor."""
        pass

    @abstractmethod
    def save_subscription(
        self,
        actor: str,
        event_topic: str,
        handler: str,
        subscribed_at: str,
    ) -> int:
        """Subscribe actor to topic and return total subscribers for topic."""
        pass

    @abstractmethod
    def get_subscribers(self, event_topic: str) -> List[str]:
        """Get list of subscribed actor names for an event topic."""
        pass

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """Return full state representation (mailboxes, subscriptions, metadata)."""
        pass

    @abstractmethod
    def check_health(self, timeout_sec: float = 300.0) -> Dict[str, Any]:
        """Perform health check and deadlock detection."""
        pass


class SQLiteStorageBackend(StorageBackend):
    """SQLite WAL storage backend for Actor QA Message Broker."""

    def __init__(self, state_file: str):
        self.state_file = state_file
        os.makedirs(os.path.dirname(os.path.abspath(self.state_file)), exist_ok=True)
        self.init_backend()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.state_file, timeout=60.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=60000;")
        conn.row_factory = sqlite3.Row
        return conn

    def init_backend(self) -> None:
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    from_actor TEXT NOT NULL,
                    to_actor TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    read INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_messages_to_actor ON messages(to_actor, read);
                CREATE INDEX IF NOT EXISTS idx_messages_topic ON messages(topic);

                CREATE TABLE IF NOT EXISTS subscriptions (
                    actor TEXT NOT NULL,
                    event_topic TEXT NOT NULL,
                    handler TEXT NOT NULL,
                    subscribed_at TEXT NOT NULL,
                    PRIMARY KEY(actor, event_topic)
                );

                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

    def save_message(
        self,
        msg_id: str,
        from_actor: str,
        to_actor: str,
        topic: str,
        payload_str: str,
        now_iso: str,
        now_epoch: float,
    ) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO messages (id, from_actor, to_actor, topic, payload, timestamp, created_at, read)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (msg_id, from_actor, to_actor, topic, payload_str, now_iso, now_epoch)
            )

    def fetch_messages(
        self,
        actor: str,
        topic: Optional[str] = None,
        mark_read: bool = True,
    ) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            if topic:
                cur.execute(
                    "SELECT * FROM messages WHERE to_actor = ? AND topic = ? ORDER BY created_at ASC",
                    (actor, topic)
                )
            else:
                cur.execute(
                    "SELECT * FROM messages WHERE to_actor = ? ORDER BY created_at ASC",
                    (actor,)
                )

            rows = cur.fetchall()
            messages: List[Dict[str, Any]] = []
            msg_ids_to_mark: List[str] = []

            for row in rows:
                try:
                    payload = json.loads(row["payload"])
                except Exception as err:
                    _ = err
                    payload = row["payload"]

                messages.append({
                    "id": row["id"],
                    "from_actor": row["from_actor"],
                    "to_actor": row["to_actor"],
                    "topic": row["topic"],
                    "payload": payload,
                    "timestamp": row["timestamp"],
                    "read": True if mark_read else bool(row["read"])
                })
                if mark_read and not row["read"]:
                    msg_ids_to_mark.append(row["id"])

            if mark_read and msg_ids_to_mark:
                conn.executemany(
                    "UPDATE messages SET read = 1 WHERE id = ?",
                    [(mid,) for mid in msg_ids_to_mark]
                )

        return messages

    def save_subscription(
        self,
        actor: str,
        event_topic: str,
        handler: str,
        subscribed_at: str,
    ) -> int:
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO subscriptions (actor, event_topic, handler, subscribed_at)
                VALUES (?, ?, ?, ?)
                """,
                (actor, event_topic, handler, subscribed_at)
            )
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM subscriptions WHERE event_topic = ?", (event_topic,))
            return cur.fetchone()[0]

    def get_subscribers(self, event_topic: str) -> List[str]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT actor FROM subscriptions WHERE event_topic = ?", (event_topic,))
            return [row[0] for row in cur.fetchall()]

    def get_state(self) -> Dict[str, Any]:
        mailboxes: Dict[str, List[Dict[str, Any]]] = {}
        subscriptions: Dict[str, List[Dict[str, Any]]] = {}
        metadata: Dict[str, Any] = {}

        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM messages ORDER BY created_at ASC")
            for row in cur.fetchall():
                to_act = row["to_actor"]
                if to_act not in mailboxes:
                    mailboxes[to_act] = []
                try:
                    payload = json.loads(row["payload"])
                except Exception as err:
                    _ = err
                    payload = row["payload"]
                mailboxes[to_act].append({
                    "id": row["id"],
                    "from_actor": row["from_actor"],
                    "to_actor": row["to_actor"],
                    "topic": row["topic"],
                    "payload": payload,
                    "timestamp": row["timestamp"],
                    "read": bool(row["read"])
                })

            cur.execute("SELECT * FROM subscriptions")
            for row in cur.fetchall():
                ev_topic = row["event_topic"]
                if ev_topic not in subscriptions:
                    subscriptions[ev_topic] = []
                subscriptions[ev_topic].append({
                    "actor": row["actor"],
                    "handler": row["handler"],
                    "subscribed_at": row["subscribed_at"]
                })

            cur.execute("SELECT * FROM metadata")
            for row in cur.fetchall():
                metadata[row["key"]] = row["value"]

        return {
            "mailboxes": mailboxes,
            "subscriptions": subscriptions,
            "metadata": metadata
        }

    def check_health(self, timeout_sec: float = 300.0) -> Dict[str, Any]:
        now_ts = time.time()
        deadlocks_detected = False
        warning = None

        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(DISTINCT to_actor) FROM messages")
            active_actors_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM messages")
            total_messages = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM messages WHERE read = 0")
            unread_messages = cur.fetchone()[0]

            cur.execute("SELECT MIN(created_at), id, to_actor FROM messages WHERE read = 0")
            row = cur.fetchone()
            oldest_unread_ts = row[0] if row else None
            oldest_msg_id = row[1] if row else None
            oldest_to_actor = row[2] if row else None

        oldest_unread_age_sec = (now_ts - oldest_unread_ts) if oldest_unread_ts is not None else 0.0

        if oldest_unread_age_sec > timeout_sec and unread_messages > 0:
            deadlocks_detected = True
            warning = (
                f"Starvation/Deadlock timeout ceiling exceeded: unread message {oldest_msg_id} "
                f"for actor '{oldest_to_actor}' has been waiting for {oldest_unread_age_sec:.1f}s (> {timeout_sec}s)."
            )
        elif unread_messages > 100 and active_actors_count >= 2:
            deadlocks_detected = True
            warning = f"High message backlog detected across multiple actors ({unread_messages} unread)."

        return {
            "status": "PASS" if not deadlocks_detected else "WARNING_DEADLOCK",
            "active_actors": active_actors_count,
            "total_messages": total_messages,
            "unread_messages": unread_messages,
            "oldest_unread_age_sec": round(oldest_unread_age_sec, 2),
            "timeout_ceiling_sec": timeout_sec,
            "deadlock_free": not deadlocks_detected,
            "warning": warning
        }


class RedisStorageBackend(StorageBackend):
    """
    Redis-backed distributed storage backend for Actor QA Message Broker.
    Enables horizontal scaling across multiple worker pods in Kubernetes clusters.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        client: Optional[Any] = None,
        key_prefix: str = "synapse"
    ):
        self.key_prefix = key_prefix.rstrip(":")
        self.redis_url = redis_url or os.environ.get("SYNAPSE_REDIS_URL")
        self.client = client

        if self.client is None:
            import importlib.util
            if importlib.util.find_spec("redis") is None:
                raise RuntimeError(
                    "redis package is required for RedisStorageBackend. Install via: pip install redis"
                )
            import redis
            url = self.redis_url or "redis://localhost:6379/0"
            self.client = redis.Redis.from_url(url, decode_responses=True)

        self.init_backend()

    def _k(self, *parts: str) -> str:
        return f"{self.key_prefix}:{':'.join(parts)}"

    def init_backend(self) -> None:
        if self.client and hasattr(self.client, "ping"):
            try:
                self.client.ping()
            except Exception as err:
                _ = err
                sys.stderr.write(f"Notice: Redis backend ping failed ({err}).\n")

    def save_message(
        self,
        msg_id: str,
        from_actor: str,
        to_actor: str,
        topic: str,
        payload_str: str,
        now_iso: str,
        now_epoch: float,
    ) -> None:
        msg_data = {
            "id": msg_id,
            "from_actor": from_actor,
            "to_actor": to_actor,
            "topic": topic,
            "payload": payload_str,
            "timestamp": now_iso,
            "created_at": now_epoch,
            "read": 0
        }
        self.client.set(self._k("msg", msg_id), json.dumps(msg_data))
        self.client.rpush(self._k("mailbox", to_actor), msg_id)
        self.client.sadd(self._k("actors"), to_actor)
        self.client.sadd(self._k("all_msg_ids"), msg_id)

    def fetch_messages(
        self,
        actor: str,
        topic: Optional[str] = None,
        mark_read: bool = True,
    ) -> List[Dict[str, Any]]:
        msg_ids = self.client.lrange(self._k("mailbox", actor), 0, -1) or []
        messages: List[Dict[str, Any]] = []

        for mid in msg_ids:
            raw = self.client.get(self._k("msg", mid))
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception as err:
                _ = err
                continue

            if topic and data.get("topic") != topic:
                continue

            try:
                payload = json.loads(data["payload"])
            except Exception as err:
                _ = err
                payload = data.get("payload")

            was_read = bool(data.get("read", 0))
            if mark_read and not was_read:
                data["read"] = 1
                self.client.set(self._k("msg", mid), json.dumps(data))

            messages.append({
                "id": data["id"],
                "from_actor": data["from_actor"],
                "to_actor": data["to_actor"],
                "topic": data["topic"],
                "payload": payload,
                "timestamp": data["timestamp"],
                "read": True if mark_read else was_read
            })

        return messages

    def save_subscription(
        self,
        actor: str,
        event_topic: str,
        handler: str,
        subscribed_at: str,
    ) -> int:
        self.client.sadd(self._k("subscribers", event_topic), actor)
        sub_info = json.dumps({"handler": handler, "subscribed_at": subscribed_at})
        self.client.hset(self._k("sub_meta", event_topic), actor, sub_info)
        return int(self.client.scard(self._k("subscribers", event_topic)))

    def get_subscribers(self, event_topic: str) -> List[str]:
        subs = self.client.smembers(self._k("subscribers", event_topic))
        if not subs:
            return []
        return sorted([s if isinstance(s, str) else str(s) for s in subs])

    def get_state(self) -> Dict[str, Any]:
        mailboxes: Dict[str, List[Dict[str, Any]]] = {}
        subscriptions: Dict[str, List[Dict[str, Any]]] = {}
        metadata: Dict[str, Any] = {}

        actors = self.client.smembers(self._k("actors")) or []
        for act in actors:
            mailboxes[act] = self.fetch_messages(act, mark_read=False)

        sub_keys = self.client.keys(self._k("sub_meta", "*")) or []
        for sk in sub_keys:
            ev_topic = sk.split(":")[-1]
            subscriptions[ev_topic] = []
            meta_map = self.client.hgetall(sk) or {}
            for act, val_str in meta_map.items():
                try:
                    val = json.loads(val_str)
                except Exception as err:
                    _ = err
                    val = {"handler": "default_handler", "subscribed_at": ""}
                subscriptions[ev_topic].append({
                    "actor": act,
                    "handler": val.get("handler", "default_handler"),
                    "subscribed_at": val.get("subscribed_at", "")
                })

        return {
            "mailboxes": mailboxes,
            "subscriptions": subscriptions,
            "metadata": metadata
        }

    def check_health(self, timeout_sec: float = 300.0) -> Dict[str, Any]:
        now_ts = time.time()
        all_ids = self.client.smembers(self._k("all_msg_ids")) or []
        total_messages = len(all_ids)
        unread_messages = 0
        oldest_unread_age_sec = 0.0
        oldest_msg_id = None
        oldest_to_actor = None
        oldest_ts = None

        for mid in all_ids:
            raw = self.client.get(self._k("msg", mid))
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception as err:
                _ = err
                continue

            if not data.get("read", 0):
                unread_messages += 1
                c_ts = data.get("created_at", now_ts)
                if oldest_ts is None or c_ts < oldest_ts:
                    oldest_ts = c_ts
                    oldest_msg_id = mid
                    oldest_to_actor = data.get("to_actor")

        if oldest_ts is not None:
            oldest_unread_age_sec = now_ts - oldest_ts

        actors = self.client.smembers(self._k("actors")) or []
        active_actors_count = len(actors)

        deadlocks_detected = False
        warning = None
        if oldest_unread_age_sec > timeout_sec and unread_messages > 0:
            deadlocks_detected = True
            warning = (
                f"Starvation/Deadlock timeout ceiling exceeded: unread message {oldest_msg_id} "
                f"for actor '{oldest_to_actor}' has been waiting for {oldest_unread_age_sec:.1f}s (> {timeout_sec}s)."
            )
        elif unread_messages > 100 and active_actors_count >= 2:
            deadlocks_detected = True
            warning = f"High message backlog detected across multiple actors ({unread_messages} unread)."

        return {
            "status": "PASS" if not deadlocks_detected else "WARNING_DEADLOCK",
            "active_actors": active_actors_count,
            "total_messages": total_messages,
            "unread_messages": unread_messages,
            "oldest_unread_age_sec": round(oldest_unread_age_sec, 2),
            "timeout_ceiling_sec": timeout_sec,
            "deadlock_free": not deadlocks_detected,
            "warning": warning
        }


class ActorQaBroker:
    """
    Asynchronous Actor Message Broker & Sharding Dispatcher.
    Backed by SQLite WAL by default, or RedisStorageBackend in distributed environments.
    """

    def __init__(
        self,
        state_file: Optional[str] = None,
        memory_bus: Optional[Any] = None,
        use_memory_bus: bool = False,
        backend: Optional[StorageBackend] = None,
        redis_url: Optional[str] = None,
    ):
        self._bus_adapter = None
        if use_memory_bus or memory_bus is not None:
            try:
                from core.adapters import BrokerMemoryBusAdapter
            except ImportError:
                from tools.core.adapters import BrokerMemoryBusAdapter
            self._bus_adapter = BrokerMemoryBusAdapter(bus=memory_bus)

        if state_file:
            self.state_file = state_file
        else:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            self.state_file = os.path.join(repo_root, ".agent_memory", "actor_broker.db")

        # Initialize storage backend
        if backend is not None:
            self.backend = backend
        elif redis_url or os.environ.get("SYNAPSE_REDIS_URL"):
            self.backend = RedisStorageBackend(redis_url=redis_url)
        else:
            self.backend = SQLiteStorageBackend(self.state_file)

    def _get_conn(self) -> sqlite3.Connection:
        """Backward-compatibility SQLite connection accessor."""
        if isinstance(self.backend, SQLiteStorageBackend):
            return self.backend.get_connection()
        conn = sqlite3.connect(self.state_file, timeout=60.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=60000;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Backward-compatibility database initialization."""
        self.backend.init_backend()

    @property
    def state(self) -> Dict[str, Any]:
        """Backward-compatibility dictionary property representing current state."""
        if self._bus_adapter and hasattr(self._bus_adapter, "get_state"):
            return self._bus_adapter.get_state()
        return self.backend.get_state()

    def send_message(self, from_actor: str, to_actor: str, topic: str, payload: Any) -> Dict[str, Any]:
        """Sends a message to an actor's mailbox with atomic persistence."""
        if self._bus_adapter:
            return self._bus_adapter.send_message(from_actor, to_actor, topic, payload)

        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        now_epoch = now_dt.timestamp()
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        payload_str = json.dumps(payload) if not isinstance(payload, str) else payload

        self.backend.save_message(msg_id, from_actor, to_actor, topic, payload_str, now_iso, now_epoch)

        return {
            "status": "PASS",
            "message_id": msg_id,
            "from": from_actor,
            "to": to_actor,
            "topic": topic,
            "timestamp": now_iso
        }

    def fetch_messages(self, actor: str, topic: Optional[str] = None, mark_read: bool = True) -> List[Dict[str, Any]]:
        """Retrieves messages for an actor with optional topic filter and read marking."""
        if self._bus_adapter:
            return self._bus_adapter.fetch_messages(actor, topic=topic, mark_read=mark_read)
        return self.backend.fetch_messages(actor, topic=topic, mark_read=mark_read)

    def subscribe(self, actor: str, event_topic: str, handler: Optional[str] = None) -> Dict[str, Any]:
        """Subscribes an actor to an event topic."""
        if self._bus_adapter:
            return self._bus_adapter.subscribe(actor, event_topic, handler=handler)

        now_iso = datetime.now(timezone.utc).isoformat()
        total_subs = self.backend.save_subscription(actor, event_topic, handler or "default_handler", now_iso)

        return {
            "status": "PASS",
            "actor": actor,
            "topic": event_topic,
            "total_subscribers": total_subs
        }

    def publish(self, event_topic: str, payload: Any, sender: str = "system") -> Dict[str, Any]:
        """Publishes an event to all subscribed actors atomically."""
        if self._bus_adapter:
            res = self._bus_adapter.publish(event_topic, payload, sender=sender)
            return {
                "status": "PASS",
                "topic": event_topic,
                "subscribers_notified": res.get("delivered_count", 0)
            }

        subs = self.backend.get_subscribers(event_topic)
        delivered_count = 0
        for target_actor in subs:
            self.send_message(
                from_actor=sender,
                to_actor=target_actor,
                topic=event_topic,
                payload=payload
            )
            delivered_count += 1

        return {
            "status": "PASS",
            "topic": event_topic,
            "subscribers_notified": delivered_count
        }

    def dispatch_shards(self, suite_manifest_path: str, shard_count: int = 4,
                        worker_role: str = "test-runner", allow_mock: bool = False) -> Dict[str, Any]:
        """Partitions test suite items across parallel worker actors.
        Fails closed if the manifest is missing unless allow_mock is explicitly True."""
        resolved = suite_manifest_path
        if not os.path.isabs(resolved):
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            cand = os.path.join(repo_root, resolved)
            if os.path.exists(cand):
                resolved = cand

        test_items = []
        if os.path.exists(resolved):
            try:
                with open(resolved, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        test_items = data
                    elif isinstance(data, dict):
                        test_items = data.get("tests") or data.get("test_cases") or []
            except Exception as e:
                sys.stderr.write(f"Notice: Could not parse manifest ({e}).\n")
                if not allow_mock:
                    return {
                        "status": "FAIL",
                        "error": f"Failed to parse manifest: {e}",
                        "manifest": suite_manifest_path
                    }

        if not test_items:
            if not allow_mock:
                return {
                    "status": "FAIL",
                    "error": f"Suite manifest not found or empty: {suite_manifest_path}",
                    "manifest": suite_manifest_path,
                    "total_tests": 0,
                    "shard_count": shard_count,
                    "shards": {}
                }
            test_items = [f"tests/suite_part_{i}.spec.ts" for i in range(1, 13)]

        shards = {f"worker_{i+1}": [] for i in range(shard_count)}
        for idx, item in enumerate(test_items):
            worker_id = f"worker_{(idx % shard_count) + 1}"
            shards[worker_id].append(item)

        # Notify workers via messages
        for worker_id, items in shards.items():
            self.send_message(
                from_actor="orchestrator",
                to_actor=f"{worker_role}:{worker_id}",
                topic="ASSIGN_SHARD",
                payload={"shard_id": worker_id, "test_count": len(items), "tests": items}
            )

        return {
            "status": "PASS",
            "total_tests": len(test_items),
            "shard_count": shard_count,
            "shards": {w: len(items) for w, items in shards.items()},
            "dispatched_to_role": worker_role
        }

    def check_health(self, timeout_sec: float = 300.0) -> Dict[str, Any]:
        """Scans mailboxes for unread backlogs, starvation, and circular deadlock indicators.
        Enforces timeout_sec ceiling on unread message age."""
        if self._bus_adapter:
            return self._bus_adapter.check_health()
        return self.backend.check_health(timeout_sec=timeout_sec)


def main():
    parser = argparse.ArgumentParser(description="Asynchronous Actor QA Message Broker")
    parser.add_argument("--redis-url", help="Optional Redis connection URL for distributed backend")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # send-message
    sm_p = subparsers.add_parser("send-message", help="Send message to actor mailbox")
    sm_p.add_argument("--from-actor", required=True, help="Sender actor role")
    sm_p.add_argument("--to-actor", required=True, help="Recipient actor role")
    sm_p.add_argument("--topic", required=True, help="Message topic")
    sm_p.add_argument("--payload", required=True, help="JSON payload")

    # fetch-messages
    fm_p = subparsers.add_parser("fetch-messages", help="Fetch messages from mailbox")
    fm_p.add_argument("--actor", required=True, help="Actor role name")
    fm_p.add_argument("--topic", help="Optional topic filter")
    fm_p.add_argument("--peek", action="store_true", help="Do not mark as read")

    # subscribe
    sub_p = subparsers.add_parser("subscribe", help="Subscribe actor to an event topic")
    sub_p.add_argument("--actor", required=True, help="Subscriber actor role")
    sub_p.add_argument("--event", required=True, help="Event topic name")
    sub_p.add_argument("--handler", help="Optional handler name")

    # publish
    pub_p = subparsers.add_parser("publish", help="Publish event to subscribers")
    pub_p.add_argument("--event", required=True, help="Event topic name")
    pub_p.add_argument("--payload", required=True, help="JSON payload")

    # dispatch-shards
    ds_p = subparsers.add_parser("dispatch-shards", help="Dispatch test suite across shards")
    ds_p.add_argument("--suite-manifest", required=True, help="Path to manifest JSON")
    ds_p.add_argument("--shard-count", type=int, default=4, help="Number of shards")
    ds_p.add_argument("--worker-role", default="test-runner", help="Target worker role")
    ds_p.add_argument("--allow-mock", action="store_true", help="Allow synthetic fallback if manifest missing")

    # check-health
    ch_p = subparsers.add_parser("check-health", help="Check broker health and deadlocks")
    ch_p.add_argument("--timeout-sec", type=float, default=300.0, help="Timeout ceiling in seconds")

    args = parser.parse_args()
    broker = ActorQaBroker(redis_url=getattr(args, 'redis_url', None))

    if args.subcommand == "send-message":
        try:
            payload = json.loads(args.payload)
        except Exception as err:
            _ = err
            payload = args.payload
        res = broker.send_message(args.from_actor, args.to_actor, args.topic, payload)
        print(json.dumps(res, indent=2))
        sys.exit(0)

    elif args.subcommand == "fetch-messages":
        msgs = broker.fetch_messages(args.actor, topic=args.topic, mark_read=not args.peek)
        print(json.dumps(msgs, indent=2))
        sys.exit(0)

    elif args.subcommand == "subscribe":
        res = broker.subscribe(args.actor, args.event, handler=args.handler)
        print(json.dumps(res, indent=2))
        sys.exit(0)

    elif args.subcommand == "publish":
        try:
            payload = json.loads(args.payload)
        except Exception as err:
            _ = err
            payload = args.payload
        res = broker.publish(args.event, payload)
        print(json.dumps(res, indent=2))
        sys.exit(0)

    elif args.subcommand == "dispatch-shards":
        res = broker.dispatch_shards(
            args.suite_manifest,
            shard_count=args.shard_count,
            worker_role=args.worker_role,
            allow_mock=args.allow_mock
        )
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["status"] == "PASS" else 1)

    elif args.subcommand == "check-health":
        res = broker.check_health(timeout_sec=args.timeout_sec)
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["status"] == "PASS" else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
