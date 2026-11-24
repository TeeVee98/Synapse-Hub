---
name: actor-qa-swarm
description: "Asynchronous Actor Model message broker and matrix sharding coordinator for multi-agent test execution. Use when distributing parallel test workloads or wiring decoupled subagent event pub/sub."
category: context_and_optimization
version: "1.0.0"
policies:
  network: none
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---
# Actor QA Swarm Skill — Asynchronous Actor Messaging & Matrix Sharding

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Asynchronous Actor Model message broker and matrix sharding coordinator for multi-agent test execution. Use when distributing parallel test workloads or wiring decoupled subagent event pub/sub.
- **Activation Scope:** Domain workflows for `10-agent-orchestration` involving `actor-qa-swarm`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT allow subagents to share mutable global state; communicate via isolated message passing.
- Do NOT spawn unbounded subagent hierarchies that exceed token and resource ceilings.
- Do NOT allow subagents to stall on trivial decisions (follow Jesse Vincent Protocol).
- **Sibling Skill Boundaries:**
  - agent-orchestration-multi-agent-optimize schedules work; actor-qa-swarm provides the Actor Model execution harness for concurrent subagents.

---

## 3. Ordered Execution Workflow

> **Paradigm Attribution:** Inspired by **Microsoft AutoGen v0.4+ (AG2 Actor Framework)**.  
> **Core Principle:** Transition from synchronous lock-step file coordination to an asynchronous Actor Model. Subagents exchange messages via non-blocking mailboxes and subscribe to test failure events in real time.

---

### The Actor Swarm Architecture

```mermaid
flowchart TD
    Orchestrator["Orchestrator Actor"] -->|dispatch-shards| Broker["Actor QA Message Broker (tools/orchestration/autogen_qa_broker.py)"]
    Broker -->|ASSIGN_SHARD| W1["test-runner:worker_1 (Playwright Shard 1)"]
    Broker -->|ASSIGN_SHARD| W2["test-runner:worker_2 (Playwright Shard 2)"]
    Broker -->|ASSIGN_SHARD| W3["test-runner:worker_3 (Playwright Shard 3)"]
    
    W1 -.->|publish(TEST_FAILED)| Broker
    Broker -.->|notify| Analyst["failure-analyst Actor (Triage in Parallel)"]
```

1. **Decoupled Actor Mailboxes (`send-message` / `fetch-messages`):**
   - Each QA subagent operates as an autonomous Actor with its own private mailbox.
   - Eliminates monolithic conversational logs and prevents context contamination across subagents.

2. **Parallel Matrix Sharding (`dispatch-shards`):**
   - Automatically splits regression test suites into $N$ balanced shards.
   - Dispatches shards to headless Playwright worker actors running in parallel.

3. **Event-Driven Triage (`subscribe` / `publish`):**
   - When a test runner encounters a failure, it immediately publishes `TEST_FAILED`.
   - `failure-analyst` diagnoses the failure concurrently while other test runners continue uninterrupted.

---

### CLI Tool Usage

Autonomous commands via `tools/orchestration/autogen_qa_broker.py`:

<!-- classification: illustrative -->
```bash
# 1. Dispatch regression suite across 4 parallel shards
python tools/orchestration/autogen_qa_broker.py dispatch-shards \
  --suite-manifest tests/regression_manifest.json \
  --shard-count 4 \
  --worker-role "test-runner"

# 2. Subscribe failure-analyst to test failure events
python tools/orchestration/autogen_qa_broker.py subscribe \
  --actor "failure-analyst" \
  --event "TEST_FAILED"

# 3. Send direct message between subagents
python tools/orchestration/autogen_qa_broker.py send-message \
  --from-actor "test-runner:worker_1" \
  --to-actor "failure-analyst" \
  --topic "TEST_FAILED" \
  --payload '{"test_case": "TC-102", "error": "TimeoutError"}'

# 4. Fetch messages from actor mailbox
python tools/orchestration/autogen_qa_broker.py fetch-messages \
  --actor "failure-analyst"

# 5. Check broker health and verify zero deadlocks
python tools/orchestration/autogen_qa_broker.py check-health
```

---

### Strict Operating Invariants

- **Deadlock Prevention:** Enforce 300s timeout ceilings on actor response waits.
- **Asynchronous Execution:** No subagent shall block the main thread waiting for another subagent's response.
- **Zero Raw Selectors:** Messages instructing code synthesis must strictly enforce Clean POM standards.

---

## 4. Verification Points & DoD

1. Subagents maintain isolated state directories and strictly bounded role assignments.
2. Messages between agents follow structured context, content, and action contracts.
3. Execution finishes within allocated token budget and concurrency limits.

---

## 5. Handoff Protocol

- **Deliverables:** Swarm execution traces, subagent state records, and aggregated task deliverables.
- **Next Subagent:** orchestrator
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
