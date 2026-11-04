---
name: event-stream-qa-orchestrator
description: "Immutable EventStream orchestrator recording deterministic action/observation timelines with SHA-256 hash chains and reversible checkpoint rollbacks. Use when tracing test executions and managing replayable state."
---

# QA Event Stream Orchestrator Skill — Immutable Audit & Replay Timeline

> **Paradigm Attribution:** Inspired by **All-Hands-AI OpenHands (EventStream & CodeAct Runtime)**.  
> **Core Principle:** Treat automated testing sessions as an append-only, immutable stream of events. Prevent state corruption and lost context by chaining each event with cryptographic SHA-256 hashes and enabling deterministic check-pointed rollbacks.

---

## 1. The EventStream Pipeline

```mermaid
flowchart LR
    Init["init-stream<br/>Genesis Hash (000...0)"] --> Act["record-event<br/>ACTION_NAVIGATE / ACTION_CLICK"]
    Act --> Obs["record-event<br/>OBSERVATION_DOM / ASSERTION"]
    Obs --> Check["Checkpoint Anchor<br/>CHECKPOINT_PRE_SUBMIT"]
    Check --> Verify["verify-stream<br/>Cryptographic Audit"]
    Verify --> Rollback["rollback<br/>Rewind to Checkpoint"]
```

1. **Immutable Event Logging (`record-event`):**
   - Each event records: `index`, `session_id`, `event_type`, `actor`, `payload`, `timestamp`, `prev_hash`, and `event_hash`.
   - Continuous SHA-256 hash chaining prevents unobserved event injection or tampering.

2. **Reversible Checkpointing (`rollback`):**
   - In conjunction with GoEx LIFO undo stack (`tools/reversible_sandbox.py`), enables restoring the browser or data state when an unexpected crash occurs.
   - Appends a `ROLLBACK_EXECUTED` event to the stream without destroying the audit trail.

3. **Cryptographic Verification (`verify-stream`):**
   - Verifies hash continuity from genesis to latest event.
   - Ensures zero missing or out-of-order events before certifying run results.

---

## 2. CLI Tool Usage

Autonomous commands via `tools/qa_event_stream.py`:

```bash
# 1. Initialize stream
python tools/qa_event_stream.py init-stream \
  --session-id "CHECKOUT_E2E_001" \
  --out-file .agent_memory/timeline.jsonl

# 2. Record an action event
python tools/qa_event_stream.py record-event \
  --stream .agent_memory/timeline.jsonl \
  --event-type ACTION_CLICK \
  --actor live-explorer \
  --payload '{"page":"CartPage","element":"checkout_button"}'

# 3. Create a state checkpoint
python tools/qa_event_stream.py record-event \
  --stream .agent_memory/timeline.jsonl \
  --event-type CHECKPOINT \
  --actor test-runner \
  --payload '{"cart_total": 99.99}' \
  --checkpoint-id "PRE_CHECKOUT_FORM"

# 4. Verify stream integrity
python tools/qa_event_stream.py verify-stream \
  --stream .agent_memory/timeline.jsonl

# 5. Rollback to checkpoint on test failure
python tools/qa_event_stream.py rollback \
  --stream .agent_memory/timeline.jsonl \
  --to-checkpoint "PRE_CHECKOUT_FORM"
```

---

## 3. Strict Operating Invariants

- **Hash Chain Integrity:** All events must compute `SHA-256(prev_hash | session_id | event_type | actor | payload | timestamp)`.
- **Zero Log Tampering:** Never edit `timeline.jsonl` lines manually; always append via the CLI tool.
- **UTF-8 No BOM:** Timeline files must remain clean UTF-8 without byte-order marks.
