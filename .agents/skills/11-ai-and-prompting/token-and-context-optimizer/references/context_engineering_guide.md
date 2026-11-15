# Context Engineering & Token Optimization Guide (Full Architecture)

*(Synthesized from `muratcankoylan/Agent-Skills-for-Context-Engineering`, `alexgreensh/token-optimizer`, and `obra/superpowers`)*

---

## 1. Pillar 1: Observation Masking
Raw tool outputs (CLI execution logs, Gradle builds, browser console traces) contain 90% repetitive noise and low-signal tokens.
- **Log Truncation & Summarization:** Never dump thousands of lines into the active conversation. Extract only: failing line number, exception name, test case identifier (`TC-xxx`), and status.
- **Pointer Masking:** Use structured references pointing to files on disk: `[Full raw log saved to file://<path>; 2,400 verbose lines omitted]`.

---

## 2. Pillar 2: Progressive Disclosure
Never load large codebases or giant classes (over 500 lines) into context at once. Load information in 3 progressive tiers:
- **Tier 1:** High-Level Index & Repo Map (< 150 lines) via `tools/repo_map.txt`.
- **Tier 2:** Graph Semantic Scoping via `graphify explain` or `test_impact.py`.
- **Tier 3:** Targeted Micro-Read (20-50 lines using `StartLine`/`EndLine`).

---

## 3. Pillar 3: KV-Cache Friendly Ordering
LLM inference engines cache Key-Value (KV) attention states for identical prompt prefixes.
- **Static Prefix First:** Keep instructions, rules, and tool schemas immutable at the top.
- **Append-Only Dynamic State:** Only append new test results and tool observations at the bottom.
- **Predictable Format:** Use identical pre-flight status badges on every turn to maximize cache hits (> 85%).

---

## 4. Pillar 4: Scoped Context & Compaction Anchoring
- **Compaction State Anchoring:** Critical state must be persisted to disk in `PROJECT_STATE.md`. When compaction fires, re-anchor immediately from disk with zero memory loss.
- **Workspace Isolation (`Workspace: 'share'`):** Subagents use isolated worktrees to prevent dirty tree collisions.
- **Zero Context Contagion:** Subagents return distilled 3-5 line summaries; stdout remains in subagent sandbox.
- **Data Partitioning:** Subagents append agent IDs to test data (`uniqueCode = "AUTO_" + time + "_SUB" + id`).

---

## 5. Pillar 5: Semantic Context Distillation (Pure Signal, Zero Noise)
All sensory inputs must pass through deterministic filters:
- **CLI Logs (`tools/distill_log.py`):** Truncate 95% of verbose lines.
- **DOM Purifier (`qa.getCompactAOM`):** Strictly forbidden to send raw HTML. Use compact AOM (< 500 tokens).
- **Universal IR (`tools/universal_ir.py`):** Author clean universal IR before emitting framework-specific code.

---

## 6. Pillar 6: Elephant-Goldfish Memory Model
- **The Elephant (Stateful Orchestrator):** Narrows problem boundaries, gathers intent, drafts specs in `docs/specs/*.md`, maintains `PROJECT_STATE.md`. Never writes tests during design phase.
- **The Goldfish (Stateless Subagent Swarm):** Fresh subagent with ZERO conversation history; evaluates solely cold artifacts on disk via `tools/goldfish_review.py`.
- **Air-Gap Data Contract:** All inter-stage data exchanges pass via disk files (JSON/JUnit XML), never raw prompt inheritance.
