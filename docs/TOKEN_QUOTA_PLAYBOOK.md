# Enterprise Token & Context Engineering Playbook (AI QA Hub)

> **Objective:** Maximize AI Agent performance, eliminate context rot, and optimize token quota across the automated test engineering lifecycle.

---

## 1. AI Model Allocation Matrix

Avoid depleting high-tier model quotas by applying the **"Right Task - Right Model"** strategy:

| AI Model Tier | Capability & Relative Cost | Recommended QA Workloads | Token Consumption |
| :--- | :--- | :--- | :--- |
| **Claude Sonnet / Opus / GPT-4o** | ⭐⭐⭐ High | • Complex logic, nested Shadow DOM / iFrames<br>• Race conditions & complex async synchronization<br>• Flaky test root-cause autopsy & Clean POM refactoring | 🔴 Expensive (Use selectively) |
| **Gemini Pro / Claude 3.5 Sonnet** | ⭐⭐ Balanced | • Everyday POM code generation, assertions, locator updates<br>• User Story to automated test transpilation<br>• Unit tests, REST API stubs & mock routes | 🟡 Moderate |
| **Gemini Flash / Claude Haiku** | ⭐ High-Speed & Low-Cost | • Parsing multi-thousand-line CI/CD logs (`distill_log.py`)<br>• Generating synthetic test data (JSON/CSV rows)<br>• Compact AOM extraction & DOM structure filtering<br>• Summaries, documentation, commit messages | 🟢 Ultra-economical |

---

## 2. Operational Mode Strategy

- **Planning Mode:**
  - Bootstrap new test automation frameworks from scratch.
  - Architect multi-tier Page Object Model hierarchies for large modules.
  - Analyze complex End-to-End user journeys traversing multiple microservices.
- **Fast / Chat Mode:**
  - Add individual test cases to existing Page Classes.
  - Heal single selectors after UI builds.
  - Debug and re-run isolated test scripts.

---

## 3. Context Window Invariants (Zero Context Rot)

1. **Progressive Disclosure (Never Load Large Files Whole):**
   - Never load classes over 500 lines into the active conversation prompt.
   - Query `tools/repo_map.txt` for method signatures first (~500 tokens). Micro-read targeted 20-50 line slices (`StartLine`, `EndLine`).
2. **Log Distillation (`distill_log.py`):**
   - Never dump thousands of lines of raw build/runner output.
   - Run `python3 tools/core/distill_log.py <path_to_log>` to filter out 95% noise, extracting only the exact failure line and last 3 HTTP requests.
3. **Compaction State Anchoring (`project_state.py`):**
   - Antigravity automatically triggers Context Compaction near the ~135k token threshold. Ensure active test run statuses and defect IDs are persisted to `PROJECT_STATE.md` on disk to avoid lossy state compression.

---

## 4. 15-Tier Apex Token & Neuro-Symbolic Intelligence Architecture

Synapse-Hub implements a 15-tier token reduction and intelligence amplification architecture, validated automatically by **Gate 11: Token Reduction Architecture Sentinel**:

| Tier | Subsystem | Core Mechanism | Token / FLOPs Savings |
|---|---|---|---|
| **Tier 1** | KV-Cache Prefix Immutability | Static immutable anchor prefix ($\ge 95\%$ KV cache hit) | 95% cache hit |
| **Tier 2** | Meta-Tool MCP & Minified Schema | Sharded tool discovery & compact schema definitions | 70% schema tokens |
| **Tier 3** | AST Skeleton Slicer & TOON | Extracts signatures & serializes JSON into TOON/TSV | 60% AST tokens |
| **Tier 4** | Observation Masking & O(1) State | Masks repetitive command outputs, keeps compact state | O(1) context growth |
| **Tier 5** | Output Diff Sentinel & Telegraphic | Enforces compact search/replace and telegraphic thought | 50% response tokens |
| **Tier 6** | Action Bundler & Deterministic Tools | Batches atomic tool invocations into single execution turn | 70% turn roundtrips |
| **Tier 7** | CodeAct Programmatic Engine | Runs sandboxed Python to filter massive data in-memory | 80-95% context tokens |
| **Tier 8** | Reversible AST Symbol Minifier | Shortens long identifiers with reversible symbol aliases | 40-50% code tokens |
| **Tier 9** | Dynamic Budget & Stop-Sequences | Sets zero/low thinking budgets on mechanical tasks | 80% reasoning tokens |
| **Tier 10** | Macro Cache Engine | Zero-token local SQLite repairs for recurring syntax drifts | 100% token elimination |
| **Tier 11** | Repo Speculative Decoding | Suffix Automaton / N-gram lookup for 1-pass verification | 40-60% forward passes |
| **Tier 12** | Symbolic Micro-DSL | Kolmogorov-minimal communication protocol (`CTX\|INV\|ACT`) | 65-75% prompt tokens |
| **Tier 13** | Logprob-Triggered Branching | Freezes KV-cache prefix; forks branches only at entropy spikes | 60-80% vs naive ToT |
| **Tier 14** | Boundary Counterfactual Few-Shot | Injects exactly 2 near-miss counterfactual pairs on boundary | 80-85% few-shot tokens |
| **Tier 15** | Neuro-Symbolic Constraint Solver | Offloads SAT, cycle & RBAC logic to pure Python solvers | 95% thinking tokens |

