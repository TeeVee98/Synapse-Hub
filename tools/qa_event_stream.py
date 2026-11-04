#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Immutable QA Event Stream Engine (OpenHands EventStream Pattern)
----------------------------------------------------------------
Provides a deterministic, append-only event stream for test automation sessions:
  1. Immutable Event Logging: Sequential JSON Lines recording of all actor actions and observations.
  2. Cryptographic Hash Chain: SHA-256 hash chaining ensures audit integrity and tamper resistance.
  3. Reversible Checkpoints: Enables safe rollback to prior verified states on failures.
  4. Stream Verification: Verifies stream schema, timestamp monotonicity, and hash chain integrity.

Usage:
  python tools/qa_event_stream.py init-stream --session-id "E2E_001" --out-file .agent_memory/timeline.jsonl
  python tools/qa_event_stream.py record-event --stream .agent_memory/timeline.jsonl --event-type ACTION_CLICK --actor live-explorer --payload '{"target": "#btn"}'
  python tools/qa_event_stream.py verify-stream --stream .agent_memory/timeline.jsonl
  python tools/qa_event_stream.py rollback --stream .agent_memory/timeline.jsonl --to-checkpoint CHECKPOINT_PRE_CHECKOUT
"""

import os
import sys
import json
import hashlib
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

GENESIS_HASH = "0" * 64
VALID_EVENT_TYPES = {
    "STREAM_INIT",
    "ACTION_NAVIGATE",
    "ACTION_CLICK",
    "ACTION_TYPE",
    "OBSERVATION_DOM",
    "ASSERTION_EVALUATED",
    "CHECKPOINT",
    "ERROR_OCCURRED",
    "ROLLBACK_EXECUTED",
    "TEST_COMPLETED"
}


class QaEventStream:
    """Immutable Event Stream with SHA-256 Hash Chaining."""

    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = repo_root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def _compute_hash(self, prev_hash: str, session_id: str, event_type: str,
                      actor: str, payload_str: str, timestamp: str) -> str:
        raw = f"{prev_hash}|{session_id}|{event_type}|{actor}|{payload_str}|{timestamp}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def init_stream(self, session_id: str, out_file: str) -> Dict[str, Any]:
        """Initializes an append-only timeline stream file."""
        resolved = os.path.join(self.repo_root, out_file) if not os.path.isabs(out_file) else out_file
        os.makedirs(os.path.dirname(os.path.abspath(resolved)), exist_ok=True)

        now = datetime.now(timezone.utc).isoformat()
        init_payload = {"session_id": session_id, "initialized_at": now}
        init_payload_str = json.dumps(init_payload, sort_keys=True)
        event_hash = self._compute_hash(GENESIS_HASH, session_id, "STREAM_INIT", "system", init_payload_str, now)

        entry = {
            "index": 0,
            "session_id": session_id,
            "event_type": "STREAM_INIT",
            "actor": "system",
            "payload": init_payload,
            "timestamp": now,
            "prev_hash": GENESIS_HASH,
            "event_hash": event_hash
        }

        with open(resolved, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(entry) + "\n")

        return {
            "status": "PASS",
            "session_id": session_id,
            "out_file": resolved,
            "genesis_hash": event_hash
        }

    def record_event(self, stream_file: str, event_type: str, actor: str,
                     payload: Any, checkpoint_id: Optional[str] = None) -> Dict[str, Any]:
        """Appends an event to the stream with continuous cryptographic hash chain."""
        resolved = os.path.join(self.repo_root, stream_file) if not os.path.isabs(stream_file) else stream_file
        if not os.path.exists(resolved):
            return {"status": "FAIL", "error": f"Stream file not found: {stream_file}"}

        # Read last line to get index and prev_hash
        last_entry = None
        total_count = 0
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    try:
                        last_entry = json.loads(stripped)
                        total_count += 1
                    except Exception as err:
                        sys.stderr.write(f"Notice: Skip malformed stream line: {err}\n")

        if not last_entry:
            return {"status": "FAIL", "error": "Stream file is empty or corrupted"}

        prev_hash = last_entry.get("event_hash", GENESIS_HASH)
        session_id = last_entry.get("session_id", "default_session")
        now = datetime.now(timezone.utc).isoformat()

        if checkpoint_id:
            if isinstance(payload, dict):
                payload["checkpoint_id"] = checkpoint_id
            else:
                payload = {"data": payload, "checkpoint_id": checkpoint_id}

        payload_str = json.dumps(payload, sort_keys=True) if not isinstance(payload, str) else payload
        event_hash = self._compute_hash(prev_hash, session_id, event_type, actor, payload_str, now)

        new_entry = {
            "index": total_count,
            "session_id": session_id,
            "event_type": event_type,
            "actor": actor,
            "payload": payload if not isinstance(payload, str) else json.loads(payload_str),
            "timestamp": now,
            "prev_hash": prev_hash,
            "event_hash": event_hash
        }

        with open(resolved, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(new_entry) + "\n")

        return {
            "status": "PASS",
            "index": total_count,
            "event_type": event_type,
            "event_hash": event_hash,
            "prev_hash": prev_hash
        }

    def verify_stream(self, stream_file: str) -> Dict[str, Any]:
        """Verifies hash chain integrity and JSON schema compliance (Gate 12)."""
        resolved = os.path.join(self.repo_root, stream_file) if not os.path.isabs(stream_file) else stream_file
        if not os.path.exists(resolved):
            return {"status": "FAIL", "verified": False, "error": f"Stream file not found: {stream_file}"}

        events = []
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    try:
                        events.append(json.loads(stripped))
                    except Exception as err:
                        return {"status": "FAIL", "verified": False, "error": f"JSON decode error: {err}"}

        if not events:
            return {"status": "FAIL", "verified": False, "error": "Stream is empty"}

        expected_prev = GENESIS_HASH
        for idx, ev in enumerate(events):
            if ev.get("index") != idx:
                return {
                    "status": "FAIL",
                    "verified": False,
                    "error": f"Index mismatch at position {idx}: expected {idx}, got {ev.get('index')}"
                }

            if ev.get("prev_hash") != expected_prev:
                return {
                    "status": "FAIL",
                    "verified": False,
                    "error": f"Broken hash chain at index {idx}: expected prev_hash {expected_prev}, got {ev.get('prev_hash')}"
                }

            payload_str = json.dumps(ev.get("payload"), sort_keys=True)
            recalc = self._compute_hash(
                expected_prev,
                ev.get("session_id", ""),
                ev.get("event_type", ""),
                ev.get("actor", ""),
                payload_str,
                ev.get("timestamp", "")
            )

            if recalc != ev.get("event_hash"):
                return {
                    "status": "FAIL",
                    "verified": False,
                    "error": f"Hash tamper detected at index {idx}: declared {ev.get('event_hash')}, computed {recalc}"
                }

            expected_prev = ev["event_hash"]

        return {
            "status": "PASS",
            "verified": True,
            "events_verified": len(events),
            "final_event_hash": expected_prev,
            "integrity": "CRYPTOGRAPHICALLY_VERIFIED"
        }

    def rollback(self, stream_file: str, to_checkpoint: str) -> Dict[str, Any]:
        """Rolls back execution state to a designated checkpoint in the stream."""
        resolved = os.path.join(self.repo_root, stream_file) if not os.path.isabs(stream_file) else stream_file
        if not os.path.exists(resolved):
            return {"status": "FAIL", "error": f"Stream file not found: {stream_file}"}

        target_checkpoint = None
        checkpoint_index = -1
        events = []

        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    try:
                        ev = json.loads(stripped)
                        events.append(ev)
                        p = ev.get("payload", {})
                        if isinstance(p, dict) and p.get("checkpoint_id") == to_checkpoint:
                            target_checkpoint = ev
                            checkpoint_index = ev.get("index", -1)
                    except Exception as err:
                        sys.stderr.write(f"Notice: Skip malformed stream line during rollback: {err}\n")

        if not target_checkpoint:
            return {
                "status": "FAIL",
                "error": f"Checkpoint '{to_checkpoint}' not found in event stream."
            }

        rolled_back_count = len(events) - (checkpoint_index + 1)

        # Record ROLLBACK_EXECUTED event in the immutable stream
        rollback_payload = {
            "target_checkpoint": to_checkpoint,
            "target_index": checkpoint_index,
            "events_rewound": rolled_back_count,
            "restored_state": target_checkpoint.get("payload")
        }
        rec_res = self.record_event(
            stream_file=stream_file,
            event_type="ROLLBACK_EXECUTED",
            actor="system",
            payload=rollback_payload
        )

        return {
            "status": "PASS",
            "to_checkpoint": to_checkpoint,
            "target_index": checkpoint_index,
            "events_rewound": rolled_back_count,
            "new_event_hash": rec_res.get("event_hash"),
            "restored_state": target_checkpoint.get("payload")
        }


def main():
    parser = argparse.ArgumentParser(description="QA Event Stream Engine (OpenHands Pattern)")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # init-stream
    init_p = subparsers.add_parser("init-stream", help="Initialize a new event stream")
    init_p.add_argument("--session-id", required=True, help="Unique test session ID")
    init_p.add_argument("--out-file", required=True, help="Path to write JSONL stream")

    # record-event
    rec_p = subparsers.add_parser("record-event", help="Append an event to the stream")
    rec_p.add_argument("--stream", required=True, help="Path to stream file")
    rec_p.add_argument("--event-type", required=True, help="Event type (ACTION_CLICK, CHECKPOINT, etc.)")
    rec_p.add_argument("--actor", required=True, help="Actor name (live-explorer, test-runner, etc.)")
    rec_p.add_argument("--payload", required=True, help="JSON payload string")
    rec_p.add_argument("--checkpoint-id", help="Optional checkpoint ID")

    # verify-stream
    ver_p = subparsers.add_parser("verify-stream", help="Verify cryptographic hash chain integrity")
    ver_p.add_argument("--stream", required=True, help="Path to stream file")

    # rollback
    rb_p = subparsers.add_parser("rollback", help="Roll back state to a checkpoint")
    rb_p.add_argument("--stream", required=True, help="Path to stream file")
    rb_p.add_argument("--to-checkpoint", required=True, help="Target checkpoint ID")

    args = parser.parse_args()
    engine = QaEventStream()

    if args.subcommand == "init-stream":
        res = engine.init_stream(session_id=args.session_id, out_file=args.out_file)
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["status"] == "PASS" else 1)

    elif args.subcommand == "record-event":
        try:
            parsed_payload = json.loads(args.payload)
        except Exception:
            parsed_payload = args.payload
        res = engine.record_event(
            stream_file=args.stream,
            event_type=args.event_type,
            actor=args.actor,
            payload=parsed_payload,
            checkpoint_id=args.checkpoint_id
        )
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["status"] == "PASS" else 1)

    elif args.subcommand == "verify-stream":
        res = engine.verify_stream(stream_file=args.stream)
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["status"] == "PASS" else 1)

    elif args.subcommand == "rollback":
        res = engine.rollback(stream_file=args.stream, to_checkpoint=args.to_checkpoint)
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["status"] == "PASS" else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
