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

Synapse-Hub organizes its 15 token-reduction and neuro-symbolic subsystems into **Core-6 Production Active Tiers**, **Active Supporting Deterministic Utilities**, and **Experimental / Inference-Server Reference Modules (`RESEARCH_SIMULATION`)**, validated behaviorally by **Gate 11: Token Reduction Architecture Sentinel** (`tools/core/gates/gate_11_token_reduction.py`):

### 4.1 Core-6 Production Active Tiers

| Tier | Subsystem | Active Modules | Empirically Verified ROI |
|---|---|---|---|
| **Tier 1** | KV-Cache Prefix Immutability | `tools/core/cache_prefix_enforcer.py`, `tools/lint/lint_cache_prefix.py` | Static prefix >= 1,024 tokens, total < 3,500 tokens, 0 volatiles (>= 95% cache hit) |
| **Tier 2** | Meta-Tool MCP & Minified Schema | `tools/runtime/meta_tool_engine.py`, `tools/mcp/synapse_meta_mcp.py`, `tools/core/schema_minifier.py` | `44.5%` minified schema (`tools/tools_schema.min.json`) / `99.1%` MCP meta-tools |
| **Tier 3** | AST Skeleton Slicer & TOON | `tools/context/context_slicer.py`, `tools/context/high_density_encoder.py` | `97.9%` AST skeleton / `48.7–61.4%` TOON record serialization |
| **Tier 4** | Observation Masking & O(1) State | `tools/runtime/trajectory_compressor.py`, `tools/core/project_state.py` | Offloads > 400-char / > 15-line logs; stateless working block < 950 chars (O(1) growth) |
| **Tier 10** | Macro Cache Engine | `tools/core/macro_cache.py`, `tools/heal/auto_heal.py` | `0` LLM tokens consumed on cached recurring syntax & schema-drift repairs |
| **Tier 15** | Neuro-Symbolic Constraint Solver | `tools/reasoning/neuro_symbolic_solver.py`, `tools/orchestration/solo_runner.py` | Deterministic Python graph cycle, SAT & RBAC verification (zero LLM reasoning tokens) |

### 4.2 Active Deterministic Supporting Utilities

| Tier | Subsystem | Active Modules | Role |
|---|---|---|---|
| **Tier 5** | Output Diff Sentinel & Telegraphic | `tools/lint/output_diff_sentinel.py`, `tools/reasoning/telegraphic_enforcer.py` | Validates compact search/replace diff blocks and telegraphic output constraints |
| **Tier 6** | Action Bundler & Deterministic Tools | `tools/runtime/action_bundler.py`, `tools/lint/infer_linter.py` | Batches atomic tool invocations and deterministic static code lint checks |
| **Tier 7** | CodeAct Programmatic Engine | `tools/runtime/codeact_engine.py` | Runs sandboxed Python to filter large datasets in-memory before returning summaries |

### 4.3 Experimental / Inference-Server Reference Modules (`RESEARCH_SIMULATION`)

These modules are inventoried on disk for research benchmarking and inference-server reference integration rather than active IDE client runtime savings:

| Tier | Subsystem | Reference Module | Empirical / Operational Note |
|---|---|---|---|
| **Tier 8** | Reversible AST Symbol Minifier | `tools/context/ast_symbol_minifier.py` | `RESEARCH_SIMULATION`: `23.0%` code-only / `17.0%` net non-lossless savings |
| **Tier 9** | Dynamic Budget & Stop-Sequences | `tools/reasoning/dynamic_budget_engine.py` | `RESEARCH_SIMULATION`: Inference-server thinking budget & stop-sequence policy |
| **Tier 11** | Repo Speculative Decoding | `tools/runtime/suffix_speculative_decoder.py` | `RESEARCH_SIMULATION`: Suffix Automaton / N-gram lookup reference for token drafting |
| **Tier 12** | Symbolic Micro-DSL | `tools/context/symbolic_micro_dsl.py` | `RESEARCH_SIMULATION`: `-19.5%` with `include_goal=True` (reference protocol only) |
| **Tier 13** | Logprob-Triggered Branching | `tools/reasoning/logprob_branching_engine.py` | `RESEARCH_SIMULATION`: Inference-server logprob-gated branching reference |
| **Tier 14** | Boundary Counterfactual Few-Shot | `tools/context/counterfactual_distiller.py` | `RESEARCH_SIMULATION`: Reference 2-pair boundary counterfactual prompt distiller |

