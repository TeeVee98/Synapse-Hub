# Context Engineering & Token Optimization Protocol

> **Mandatory Rule:** Governs context windows, tool outputs, and attention budgets across all agent sessions.  
> Detailed architecture guide: [context_engineering_guide.md](file://.agents/skills/token-and-context-optimizer/references/context_engineering_guide.md).

---

## 1. Observation Masking & Log Truncation
- Never dump thousands of lines of raw tool outputs (CLI, build logs, browser traces) into the chat.
- Extract strictly: failing line number, exception name, test ID (`TC-xxx`), and status.
- Mask verbose logs with pointer references: `[Full raw log saved to file://<path>; verbose lines omitted]`.

## 2. Progressive Disclosure & Micro-Reads
- Never read large files (> 150 lines) into context at once.
- Tier 1: Check `tools/repo_map.txt` for class signatures (~500 tokens).
- Tier 2: Check dependency blast radius via `tools/test_impact.py`.
- Tier 3: Micro-read targeted 20–50 lines using `StartLine` and `EndLine`.

## 3. KV-Cache Optimization & Static Prefix
- Keep system instructions and rule headers static and immutable at the top.
- Append new observations strictly at the bottom. Use identical status badges to maintain > 85% cache hit rates.

## 4. Compaction Anchoring & Subagent Isolation
- Persist active test registers, IDs, and state to `PROJECT_STATE.md` so automated context compaction never causes state loss.
- Always isolate subagents (`Workspace: 'share'`); subagents must return only 3–5 line distilled summaries.
- Partition test data with dynamic agent IDs (`uniqueCode = "AUTO_" + time + "_SUB" + id`).

## 5. Semantic Signal Distillation
- **Forbidden Raw HTML:** Never send raw HTML trees into context. Use `qa.getCompactAOM()` (< 500 tokens).
- **Universal IR First:** Reason over clean Universal IR (`tools/universal_ir.py`) before generating Groovy/TS/Java boilerplate.
- **Elephant-Goldfish Swarm:** Stateful Orchestrator writes specs to disk; stateless verification subagents audit cold files with zero context contagion.
