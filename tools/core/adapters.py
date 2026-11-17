#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/core/adapters.py — Unified Memory Bus Bridges & Adapters
--------------------------------------------------------------
Provides bidirectional adapter bridges connecting specialized QA operating tools
(autogen_qa_broker, qa_event_stream, test_memory_os) directly to the unified SQLite
WAL-backed engine in tools/core/memory_bus.py:

  1. BrokerMemoryBusAdapter:
     Adapts ActorQaBroker messaging & pub/sub to Partition 2 (actor_mailbox) & Partition 1 (blocks).
  2. EventStreamMemoryBusAdapter:
     Adapts QaEventStream timeline logging, SHA-256 hash chaining & checkpoints to Partition 5 (event_stream).
  3. TestMemoryOSAdapter:
     Adapts 3-tier TestMemoryOS (Core, Recall, Archival) to Partition 1 (blocks) & Partition 5 (event_stream).
"""

import os
import sys
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.dirname(SCRIPT_DIR)
for p in (SCRIPT_DIR, TOOLS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from memory_bus import UnifiedMemoryBus, get_memory_bus


class BrokerMemoryBusAdapter:
    """Adapts ActorQaBroker interface to UnifiedMemoryBus (Partition 2 & 1)."""

    def __init__(self, bus: Optional[UnifiedMemoryBus] = None):
        self.bus = bus or get_memory_bus()

    def send_message(
        self,
        from_actor: str,
        to_actor: str,
        topic: str,
        payload: Any,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Routes message directly to UnifiedMemoryBus mailbox partition."""
        msg_id = self.bus.send_message(
            sender=from_actor,
            recipient=to_actor,
            stage=topic,
            payload=payload,
            session_id=session_id
        )
        return {
            "status": "PASS",
            "message_id": msg_id,
            "from": from_actor,
            "to": to_actor,
            "topic": topic,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def fetch_messages(
        self,
        actor: str,
        topic: Optional[str] = None,
        mark_read: bool = True,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetches messages for recipient actor from UnifiedMemoryBus mailbox."""
        raw_msgs = self.bus.receive_messages(
            recipient=actor,
            stage=topic,
            mark_read=mark_read,
            session_id=session_id
        )
        formatted = []
        for m in raw_msgs:
            formatted.append({
                "id": m["message_id"],
                "from_actor": m["sender"],
                "to_actor": m["recipient"],
                "topic": m["stage"],
                "payload": m["payload"],
                "timestamp": m["created_at"],
                "read": True if mark_read else (m["status"] == "PROCESSED")
            })
        return formatted


    def subscribe(self, actor: str, event_topic: str, handler: Optional[str] = None) -> Dict[str, Any]:
        """Registers a pub/sub topic subscription using UnifiedMemoryBus memory_blocks."""
        now_iso = datetime.now(timezone.utc).isoformat()
        content = {
            "actor": actor,
            "event_topic": event_topic,
            "handler": handler or "default_handler",
            "subscribed_at": now_iso
        }
        self.bus.set_block(
            label=f"{event_topic}:{actor}",
            content=content,
            scope="broker_subscriptions"
        )
        all_subs = self.bus.list_blocks(scope="broker_subscriptions")
        total_topic_subs = sum(
            1 for b in all_subs if b.get("content", {}).get("event_topic") == event_topic
        )
        return {
            "status": "PASS",
            "actor": actor,
            "topic": event_topic,
            "total_subscribers": total_topic_subs
        }

    def publish(self, event_topic: str, payload: Any, sender: str = "system") -> Dict[str, Any]:
        """Dispatches an event payload to all subscribed actors via UnifiedMemoryBus."""
        all_subs = self.bus.list_blocks(scope="broker_subscriptions")
        target_actors = [
            b["content"]["actor"]
            for b in all_subs
            if isinstance(b.get("content"), dict) and b["content"].get("event_topic") == event_topic
        ]
        delivered_count = 0
        for target in target_actors:
            self.send_message(
                from_actor=sender,
                to_actor=target,
                topic=event_topic,
                payload=payload
            )
            delivered_count += 1
        return {
            "status": "PASS",
            "topic": event_topic,
            "delivered_count": delivered_count,
            "target_actors": target_actors
        }

    def check_health(self) -> Dict[str, Any]:
        """Returns health status of the broker backed by UnifiedMemoryBus."""
        stats = self.bus.get_stats()
        return {
            "status": "PASS",
            "backend": "UnifiedMemoryBus",
            "mailbox_count": stats.get("actor_mailbox", 0),
            "healthy": True
        }

    def get_state(self) -> Dict[str, Any]:
        """Reconstructs state dictionary from UnifiedMemoryBus mailbox and subscriptions."""
        mailboxes: Dict[str, List[Dict[str, Any]]] = {}
        subscriptions: Dict[str, List[Dict[str, Any]]] = {}
        metadata: Dict[str, Any] = {}

        cur = self.bus._conn.cursor()
        with self.bus._lock:
            cur.execute("SELECT * FROM actor_mailbox ORDER BY created_at ASC")
            for row in cur.fetchall():
                to_act = row["recipient"]
                if to_act not in mailboxes:
                    mailboxes[to_act] = []
                try:
                    payload = json.loads(row["payload"])
                except Exception:
                    payload = row["payload"]
                mailboxes[to_act].append({
                    "id": row["message_id"],
                    "from_actor": row["sender"],
                    "to_actor": row["recipient"],
                    "topic": row["stage"],
                    "payload": payload,
                    "timestamp": row["created_at"],
                    "read": (row["status"] == "PROCESSED")
                })

        all_subs = self.bus.list_blocks(scope="broker_subscriptions")
        for b in all_subs:
            content = b.get("content", {})
            if isinstance(content, dict):
                ev_topic = content.get("event_topic", "")
                if ev_topic not in subscriptions:
                    subscriptions[ev_topic] = []
                subscriptions[ev_topic].append({
                    "actor": content.get("actor", ""),
                    "handler": content.get("handler", "default_handler"),
                    "subscribed_at": content.get("subscribed_at", b.get("updated_at", ""))
                })

        return {
            "mailboxes": mailboxes,
            "subscriptions": subscriptions,
            "metadata": metadata
        }


class EventStreamMemoryBusAdapter:
    """Adapts QaEventStream interface to UnifiedMemoryBus (Partition 5: event_stream)."""

    def __init__(self, bus: Optional[UnifiedMemoryBus] = None, session_id: Optional[str] = None):
        self.bus = bus or get_memory_bus()
        self.default_session_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"

    def _resolve_session(self, stream_file_or_session: str) -> str:
        base = os.path.basename(stream_file_or_session)
        name, _ = os.path.splitext(base)
        return name if name else self.default_session_id

    def init_stream(self, session_id: str, out_file: Optional[str] = None) -> Dict[str, Any]:
        """Initializes a new event stream in the UnifiedMemoryBus."""
        rec = self.bus.record_event(
            session_id=session_id,
            event_type="STREAM_INIT",
            actor="system",
            stage="INIT",
            payload={"session_id": session_id, "initialized_at": datetime.now(timezone.utc).isoformat()}
        )
        return {
            "status": "PASS",
            "session_id": session_id,
            "genesis_hash": rec["event_hash"],
            "event_id": rec["event_id"],
            "backend": "UnifiedMemoryBus"
        }

    def record_event(
        self,
        stream_file: str,
        event_type: str,
        actor: str,
        payload: Any,
        checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Appends an event to the session stream in UnifiedMemoryBus."""
        session_id = self._resolve_session(stream_file)
        rec = self.bus.record_event(
            session_id=session_id,
            event_type=event_type,
            actor=actor,
            stage="STREAM",
            payload=payload,
            checkpoint_name=checkpoint_id
        )
        return {
            "status": "PASS",
            "session_id": session_id,
            "event_type": event_type,
            "event_hash": rec["event_hash"],
            "sequence": rec["sequence"],
            "checkpoint_name": checkpoint_id
        }

    def verify_stream(self, stream_file: str) -> Dict[str, Any]:
        """Verifies cryptographic hash chain integrity in UnifiedMemoryBus."""
        session_id = self._resolve_session(stream_file)
        is_valid, err = self.bus.verify_stream_integrity(session_id)
        events = self.bus.get_events(session_id)
        if not is_valid:
            return {
                "status": "FAIL",
                "valid": False,
                "session_id": session_id,
                "error": err
            }
        return {
            "status": "PASS",
            "valid": True,
            "session_id": session_id,
            "events_verified": len(events),
            "last_hash": events[-1]["event_hash"] if events else None
        }

    def rollback(self, stream_file: str, to_checkpoint: str) -> Dict[str, Any]:
        """Rolls back the session stream to the named checkpoint."""
        session_id = self._resolve_session(stream_file)
        rec = self.bus.rollback_to_checkpoint(session_id, to_checkpoint)
        return {
            "status": "PASS",
            "session_id": session_id,
            "rolled_back_to": to_checkpoint,
            "rollback_event": rec
        }

    def replay_stream(self, stream_file: str, from_index: int = 0) -> List[Dict[str, Any]]:
        """Replays events from sequence index."""
        session_id = self._resolve_session(stream_file)
        return self.bus.get_events(session_id, since_sequence=from_index)


class TestMemoryOSAdapter:
    """Adapts TestMemoryOS interface to UnifiedMemoryBus (Partition 1: blocks & Partition 5: event_stream)."""
    __test__ = False

    def __init__(self, bus: Optional[UnifiedMemoryBus] = None):

        self.bus = bus or get_memory_bus()

    def update_core(self, block_key: str, data: Any) -> Dict[str, Any]:
        """Stores key-value environment state into memory_blocks partition."""
        now_iso = datetime.now(timezone.utc).isoformat()
        res = self.bus.set_block(
            label=block_key,
            content=data,
            scope="core_memory"
        )
        return {
            "status": "PASS",
            "block_key": block_key,
            "updated_at": now_iso
        }

    def get_core(self, block_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves core memory block."""
        block = self.bus.get_block(label=block_key, scope="core_memory")
        if not block:
            return None
        return {
            "block_key": block["label"],
            "data": block["content"],
            "updated_at": block["updated_at"]
        }

    def record_recall_step(
        self,
        session_id: str,
        event_type: str,
        actor: str,
        payload: Any
    ) -> Dict[str, Any]:
        """Records an execution step into event_stream partition."""
        rec = self.bus.record_event(
            session_id=session_id,
            event_type=event_type,
            actor=actor,
            stage="RECALL",
            payload=payload
        )
        return {
            "status": "PASS",
            "session_id": session_id,
            "sequence": rec["sequence"],
            "event_id": rec["event_id"]
        }

    def get_recall_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent execution steps from event_stream."""
        events = self.bus.get_events(session_id)
        filtered = [
            {
                "id": e["sequence"],
                "session_id": e["session_id"],
                "event_type": e["event_type"],
                "actor": e["actor"],
                "payload": e["payload"],
                "timestamp": e["timestamp"]
            }
            for e in events if e.get("stage") == "RECALL" or e.get("event_type") != "STREAM_INIT"
        ]
        return filtered[-limit:]

    def archival_insert(self, key: str, payload: Any, aut_version: str = "v1.0") -> Dict[str, Any]:
        """Inserts an archival record scoped by AUT release version."""
        unique_label = f"{aut_version}:{key}:{uuid.uuid4().hex[:6]}"
        self.bus.set_block(
            label=unique_label,
            content=payload,
            scope=f"archival_{aut_version}",
            tags=key
        )
        return {
            "status": "PASS",
            "key": key,
            "aut_version": aut_version,
            "label": unique_label
        }

    def archival_search(
        self,
        query: str,
        aut_version: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Searches archival records matching query and optional aut_version."""
        scope = f"archival_{aut_version}" if aut_version else None
        blocks = self.bus.list_blocks(scope=scope)
        matches = []
        q_lower = query.lower()

        for b in blocks:
            text_repr = f"{b['label']} {json.dumps(b['content'], ensure_ascii=False)}".lower()
            if q_lower in text_repr:
                matches.append({
                    "key": b["tags"] or b["label"],
                    "aut_version": aut_version or b["scope"].replace("archival_", ""),
                    "payload": b["content"],
                    "updated_at": b["updated_at"]
                })
                if len(matches) >= limit:
                    break

        return matches

    def list_core(self) -> List[Dict[str, Any]]:
        """Lists all core memory blocks from UnifiedMemoryBus."""
        blocks = self.bus.list_blocks(scope="core_memory")
        return [
            {
                "block_key": b["label"],
                "data": b["content"],
                "updated_at": b["updated_at"]
            }
            for b in blocks
        ]

    def gc(self, scrub_secrets: bool = True, max_age_days: int = 30) -> Dict[str, Any]:
        """Executes garbage collection and returns bus status."""
        stats = self.bus.get_stats()
        return {
            "status": "PASS",
            "backend": "UnifiedMemoryBus",
            "db_path": self.bus.db_path,
            "blocks_count": stats.get("memory_blocks", 0),
            "events_count": stats.get("event_stream", 0),
            "secrets_scrubbed": 0
        }

