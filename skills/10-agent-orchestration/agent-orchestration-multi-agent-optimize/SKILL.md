---
name: agent-orchestration-multi-agent-optimize
description: "Profile, benchmark, and orchestrate multi-agent test workloads and token throughput. Use when orchestrating multi-agent swarms, partitioning workloads, or optimizing agent roles."
category: context_and_optimization
version: "2.0.0"
policies:
  network: none
  shell: read-only
  filesystem: read-only
---
# Multi-Agent Optimization & Orchestration Skill

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Profile, benchmark, and orchestrate multi-agent test workloads and token throughput. Use when orchestrating multi-agent swarms, partitioning workloads, or optimizing agent roles.
- **Activation Scope:** Domain workflows for `10-agent-orchestration` involving `agent-orchestration-multi-agent-optimize`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT dispatch tasks to subagents with incomplete or ambiguous task briefings.
- Do NOT spawn parallel subagents for sequential dependent tasks.
- Do NOT omit timeout and failure recovery handlers for worker agents.
- **Sibling Skill Boundaries:**
  - actor-qa-swarm provides actor primitives; agent-orchestration-multi-agent-optimize plans and coordinates multi-agent workload sharding.

---

## 3. Ordered Execution Workflow

> **Target:** Optimize multi-agent test workloads, reduce context overhead, streamline agent handoffs, and monitor token consumption across autonomous test swarms.

---

### When to Use

- Managing multi-agent coordination, test suite sharding, and throughput.
- Profiling sub-agent task decomposition to eliminate redundant execution.
- Implementing dynamic model tiering (fast models for search, deep models for healing).
- Budgeting context tokens across collaborative agent swarms.

---

### Core Orchestration Principles

1. **Single Front-Door Protocol:**
   - All inbound tasks route through `orchestrator` to prevent split-brain execution.
2. **Context Isolation (`Workspace: 'share'`):**
   - Subagents run in isolated workspaces to avoid git index collisions and context pollution.
3. **Observation Distillation:**
   - Subagents return only 3-5 line summaries and pointers to logs on disk, never dumping thousands of stdout lines into the parent context.
4. **Dynamic Model Routing:**
   - Use lighter models (`flash`, `flash_lite`) for element exploration and log filtering.
   - Use deeper models (`inherit`, `pro`) for root-cause synthesis and AST mutation testing.

---

### Workload Sharding & Matrix Execution

<!-- classification: illustrative -->
```python
# Multi-agent workload partition example
def shard_test_workload(suite_files: list, max_agents: int = 4) -> list:
    """Partitions test cases across parallel subagents to minimize total execution wall-clock time."""
    shards = [[] for _ in range(max_agents)]
    for idx, test_file in enumerate(suite_files):
        shards[idx % max_agents].append(test_file)
    return [s for s in shards if s]
```

---

### Token & Latency Governance

| Optimization Layer | Baseline (Naive) | Optimized (Synapse Swarm) | Savings |
| :--- | :--- | :--- | :--- |
| **CLI Log Output** | Dump 3,000 lines | `tools/core/distill_log.py` (< 50 tokens) | **95%** |
| **Codebase Reading** | Read whole classes | `tools/repo_map.txt` (via `python tools/core/repo_map.py`, < 600 tokens) | **90%** |
| **Failure Resolution**| Multiple prompt loops | SQLite cache lookup (< 0.1s) | **> 90%** |
| **DOM Inspection** | Raw HTML DOM | Compact AOM (< 500 tokens) | **90%** |

---

### Verification & Safety Guidelines

- Always establish baseline metrics before applying workflow changes.
- Ensure subagent dynamic test data uses unique runtime IDs (`AUTO_<timestamp>_<agentId>`).
- Enforce automated teardown for all creation actions dispatched by subagents.

---

### Hierarchical Process & Manager Delegation

> *Borrowed and adapted from the crewAI hierarchical process model (MIT license, crewAIInc/crewAI).*

The hub's default is a flat swarm with the `orchestrator` as single front-door
(Section 2). For tasks too large for one dispatch round, escalate to a
**hierarchical process**:

1. **Manager delegation** — the orchestrator becomes a manager: it decomposes
   the goal, assigns one bounded sub-task per specialist (`live-explorer`,
   `pom-crafter`, `test-runner`, `failure-analyst`), and validates each result
   before assigning the next. Workers never talk sideways; all coordination
   flows through the manager.
2. **Bounded delegation depth** — max 2 levels (orchestrator → specialist →
   sub-task). Deeper recursion hides cost and breaks the token budget.
3. **Validation gates between hops** — a manager accepts a sub-task result
   only when it passes its stage gate (e.g. Stage 1 Data Contract JSON is
   schema-valid); rejected results are retried once, then escalated.
4. **Escalate structure, not authority** — the hierarchy speeds coordination;
   Truth Anchor, safety firewall and quality gates apply identically at every
   level. Delegation never bypasses a gate.

---

## 4. Verification Points & DoD

1. Task decomposed into independent, parallelizable sub-milestones.
2. Subagent dispatch briefings are 100% self-contained (`BRIEFING.md` format).
3. Consolidated outputs verified against definition of done before milestone completion.

---

## 5. Handoff Protocol

- **Deliverables:** Milestone orchestration plan, dispatch records, and consolidated verification summary.
- **Next Subagent:** orchestrator
- **Output Format:** Multi-agent throughput profiles, token-per-task benchmarks, and DAG concurrency schedules.
