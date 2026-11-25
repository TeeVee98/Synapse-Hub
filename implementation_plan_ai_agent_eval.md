<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Implementation Plan: AI & Agent Evaluation Sensor Integrity Hardening (P0 + P1 + P2)

> **Reference Protocol:** [AGENTS.md §5](AGENTS.md), [standards/qa-process/plan-protocol.md](standards/qa-process/plan-protocol.md)
> **Super-Plan Metadata:** `Tier 2 (DEEP_SUPER_PLAN)` | `RiskScore = 0.70` (`FanIn = 91`, `StateMutation = True`)
> **Execution Mode:** Sequential Single-Agent `/solo` (`M1` -> `M6`, strictly `0` `swarm` workers or parallel subagents)
> **Plan Artifact Path:** `implementation_plan_ai_agent_eval.md` (isolated from `implementation_plan.md` per user request)
> **Governing Rulings (Locked at Stage 2 Ambiguity Gate):**
> - `Ruling 1 (Full 5-Sensor Scope + ADR-0022):` Execute end-to-end remediation across all 5 AI/Agent evaluation pillars (`eval_runner.py`, `agent_canary.py`, `ai_eval_sentinel.py`, `synapse_qa_bench.py`, and `harness_sentinel.py`) plus Tier-2 `ADR-0022`, elevating `agent_canary.py` from `75.0%` (`Level 4.5`) to genuine `100.0%` (`Level 5.0`) and `synapse_qa_bench.py` to open-pool retrieval across all `166` CLI tools.
> - `Ruling 2 (In-Memory Gate DTO & Proportional Fast-Tier Proxy):` Return structured gate results directly in memory from `verify_all.py` to eliminate concurrent races on `reports/verify_all_report.json`; preserve `WEIGHT_GATES + WEIGHT_TESTS + WEIGHT_MUTATION + WEIGHT_HARNESS == 1.0`, compute `s_tests` proportionally from static gate health (`s_gates`) with explicit `static_fast_proxy` metadata when `--tier fast` skips Pytest (instead of a `0.0` cliff), and remove the hardcoded `95.58` mutation fallback.
> - `Ruling 3 (Fail-Closed Multi-Turn Transcript Auditing):` Enforce fail-closed `is_trustworthy = False` on security injection or hallucination verdicts and return `INCONCLUSIVE` (`is_trustworthy = False`) when `total_conversation_turns == 0`; strip system metadata envelopes from `USER_INPUT`, ingest `SYSTEM_MESSAGE` outputs plus per-step `transcript_full.jsonl` hydration on `truncated_fields`, and exempt intermediate tool-progress turns (turns carrying `tool_calls`) from `compute_answer_relevance` false positives while still auditing every spoken turn for faithfulness and prompt injection.
> 📝 **Plan Changelog (v1.0):** Initial Tier-2 super-plan grounded via AST signatures and Stage 2 Ambiguity Gate rulings.

---

## 0. Orthogonal Architectural Tournament (Trade-off Matrix)

| Evaluation Criteria | 🏛️ Branch A: Minimalist Patch | 📐 Branch B: Clean Sensor Contracts | ⚡ Branch C: High-Throughput Async |
| :--- | :--- | :--- | :--- |
| **Core Philosophy** | Patch broken paths & method names inline; keep file-based IPC | Typed in-memory DTOs, fail-closed contracts, IDF open-pool resolver | Multiprocess shared-memory IPC & async transcript streaming |
| **Blast Radius** | Small (`4` files), leaves shared JSON race & 3-tool toy bench intact | Modular (`9` code/test files + `ADR-0022`), 100% backward-compatible | High (`14+` files), alters CLI runner concurrency semantics |
| **Regression Risk** | Medium (shared `verify_all_report.json` race persists under CI) | Lowest (preserves `run_all_gates() -> int` for all `91` callers) | Medium-High (process pool lifecycle overhead on macOS/Windows) |
| **Sensor Fidelity** | Partial (fixes crashes, leaves vacuous `0`-turn pass & toy BFCL) | Highest (enforces Invariant 2 Truth Anchor across all 5 sensors) | High, but over-engineered for `< 10s` local CLI diagnostics |
| **Selection Verdict** | Score `6.85` — Insufficient sensor rigor | **(Recommended)** Score `8.92` — Optimal Truth-Anchor isolation | Score `7.40` — Unnecessary IPC complexity |

> **Ruling:** Selected Branch: **[Branch B: Clean Sensor Contracts]** — Eliminates silent fake passes and file-level race conditions via in-memory DTO handoffs while preserving 100% CLI and caller backward compatibility across `91` downstream references.

---

## Cognitive Grounding & Budget
- **Step-Back Principles:** Truth Anchor Integrity (Invariant 2): Evaluation sensors must fail closed on missing methods, exceptions, zero-turn transcripts, or unexecuted gates rather than synthesizing `100.0` fallback scores; Isolation of State: In-process callers must exchange immutable DTOs in memory rather than racing on global report files.
- **Self-Discover Primitives:** `MOD_CONTRACT_ISOLATION: In-Memory Typed DTO Boundary`, `MOD_FAIL_CLOSED_GATE: Zero Vacuous Pass Sentinel`, `MOD_IDF_RETRIEVAL: Open-Corpus Tool Resolution`.
- **DynamicBudget Allocation:** category=`architectural_remediation` | thinking_budget=`8192` | max_tokens=`4096`

---

## 1. Affected Files & Blast Radius

| Action | Target File & AST Structural Anchor | Line Range | Change Purpose & Blast Radius |
| :---: | :--- | :---: | :--- |
| `[MODIFY]` | `tools/core/verify_all.py` (AST: run_all_gates) | `L146-L342` | Add `run_all_gates_detailed()` returning `(exit_code, result_dict)` in memory plus optional `report_path` parameter while keeping `run_all_gates() -> int` 100% compatible for all `91` callers. |
| `[MODIFY]` | `tools/core/harness_sentinel.py` (AST: HarnessSentinel) | `L49-L255` | Upgrade Step 2 and Step 6 from file-existence checks to callable module smoke probes (`infer_linter`, `fact_forcing_gate`, `token_estimator`, `distill_log`) without masking import/runtime defects. |
| `[MODIFY]` | `tools/core/eval_runner.py` (AST: EvalRunner) | `L96-L510` | Call `sentinel.run_full_audit()` with fail-closed `0.0` error handling, consume `run_all_gates_detailed()` in memory, replace `fast`-tier `0.0` cliff with proportional `static_fast_proxy`, remove magic `95.58` fallback, and render dynamic `11/11` gate counts. |
| `[MODIFY]` | `tools/lint/agent_canary.py` (AST: CanaryArena) | `L50-L521` | Fix subpackage paths (`_TOOLS_ROOT/browser_helpers.js`, `resolve_tool_path("verify_all.py", "core")`, `skills/01-web-automation/clean-pom-crafter/SKILL.md`) and upgrade `V6_PATH_LEAK` / `V7_CLEAN_POM` to real temp-file sanitization checks. |
| `[MODIFY]` | `tools/lint/ai_eval_sentinel.py` (AST: audit_agent_transcript) | `L262-L465` | Strip metadata tags from `USER_INPUT`, ingest `SYSTEM_MESSAGE` and per-step `transcript_full.jsonl` on `truncated_fields`, exempt intermediate `tool_calls` progress turns from `FAIL_IRRELEVANT`, and fail closed on `0` turns or security/hallucination verdicts. |
| `[MODIFY]` | `tools/orchestration/synapse_qa_bench.py` (AST: SynapseQABench) | `L52-L299` | Upgrade `_default_tool_resolver()` to IDF-weighted scoring over all `166` tools in `tools_schema.json`, fix `TC-BENCH-04` `--dir skills` arg, and add out-of-domain abstention test cases. |
| `[MODIFY]` | `tests/test_eval_runner.py` (AST: TestEvalRunnerScoring) | `L22-L180` | Add unit tests for `HarnessSentinel` exception fail-closed behavior, in-memory gate bundle consumption, proportional `fast`-tier proxy scoring, and missing mutation metric handling. |
| `[MODIFY]` | `tests/test_ai_eval_sentinel.py` (AST: test_audit_agent_transcript_mock) | `L72-L87` | Add unit tests for `SYSTEM_MESSAGE` grounding, `transcript_full.jsonl` step lookup, `0`-turn inconclusive fail-closed handling, security injection veto, and progress-turn relevance exemption. |
| `[CREATE]` | `tests/test_ai_agent_eval_hardening.py` (New) | `L1-L240` | End-to-end 4-scenario verification battery (Positive, Negative, Boundary, CLI `--json` / gate flags) across `agent_canary.py`, `synapse_qa_bench.py` (166-tool pool), `harness_sentinel.py`, `eval_runner.py`, and `ai_eval_sentinel.py`. |
| `[CREATE]` | `docs/adr/ADR-0022-ai-agent-sensor-integrity.md` (New) | `L1-L95` | Permanent Tier-2 Architectural Decision Record documenting the 3 Stage 2 rulings on AI/Agent sensor truth-anchor hardening. |
| `[MODIFY]` | `docs/adr/README.md` (L12-L24) | `L12-L24` | Register `ADR-0022-ai-agent-sensor-integrity.md` in the ADR inventory table. |

---

## 2. Data Flow & Interface Signatures

> **Anti-Full-Code Invariant:** Define ONLY frozen DTOs and function/method signatures with strict type contracts. Full algorithmic bodies are deferred to sequential `/solo` execution.

```python
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class SensorHardeningInputDTO:
    """Root input contract locking Stage 2 rulings for sequential /solo execution."""
    repo_root: str
    tier: str
    open_pool_benchmark: bool = True


@dataclass(frozen=True)
class GateExecutionBundleDTO:
    """In-memory DoD gate execution payload eliminating verify_all_report.json races."""
    return_code: int
    all_passed: bool
    total_gates: int
    passed_gates: int
    failed_gates: int
    gates: List[Dict[str, Any]]
    pytest_metrics: Dict[str, Any]
    mutation_metrics: Dict[str, Any]
    performance_metrics: Dict[str, Any]


@dataclass(frozen=True)
class EvalCompositeScoreDTO:
    """Normalized composite score s(e) with explicit proxy telemetry."""
    composite_score: float
    tests_measurement_mode: str
    harness_readiness_score: float
    failures_count: int


@dataclass(frozen=True)
class CanaryArenaReportDTO:
    """Empirical Canary self-healing scorecard with verified post-DoD gate status."""
    total_vectors: int
    detection_rate_pct: float
    resolution_rate_pct: float
    dod_compliant: bool
    autonomous_tier: str


@dataclass(frozen=True)
class TranscriptAuditVerdictDTO:
    """Fail-closed multi-turn agent transcript hallucination & safety verdict."""
    audit_status: str
    total_conversation_turns: int
    overall_faithfulness_rate: float
    is_trustworthy: bool
    security_blocked_turns: int


@dataclass(frozen=True)
class BFCLOpenPoolReportDTO:
    """Open-pool 166-tool function-calling & abstention benchmark report."""
    candidate_pool_size: int
    total_cases: int
    overall_score: float
    tool_selection_accuracy: float
    arg_validity_accuracy: float
    irrelevance_detection_rate: float
    passed: bool


# Key Function & Method Signatures (Signatures Only)
def run_all_gates_detailed(
    repo_root: str,
    mode: str = "AUTO",
    fast: bool = False,
    tier: Optional[str] = None,
    output_format: str = "text",
    report_path: Optional[str] = None,
) -> Tuple[int, Dict[str, Any]]: ...

def sanitize_user_query_envelope(raw_query: str) -> str: ...

def load_full_transcript_steps(transcript_path: str, needed_steps: set[int]) -> Dict[int, str]: ...

def score_open_pool_candidates(
    intent: str,
    candidates: List[str],
    abstain_threshold: float = 0.18,
) -> str: ...
```

---

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: In-Memory Gate Result DTO & Callable Harness Smoke Probes
- Node ID: M1
- depends_on: []
- Compute Tier: [Model: Pro | Thinking: High | Temp: 0.1]
- Files Modified: `tools/core/verify_all.py`, `tools/core/harness_sentinel.py`, `tests/test_eval_runner.py`
- Write Set: ['tools/core/verify_all.py', 'tools/core/harness_sentinel.py', 'tests/test_eval_runner.py']
- consumes: [{'contract': 'SensorHardeningInputDTO'}]
- produces: [{'contract': 'GateExecutionBundleDTO'}]
- Circuit Breaker: Max Fix Attempts: 2 | Scope Guard: <= 3 files
- Rollback Hook: git restore tools/core/verify_all.py tools/core/harness_sentinel.py tests/test_eval_runner.py
- Pass Gate: pytest tests/test_eval_runner.py -q

### Milestone 2: Harden EvalRunner Truth Anchor, Proportional Fast Proxy & 11-Gate Telemetry
- Node ID: M2
- depends_on: ['M1']
- Compute Tier: [Model: Pro | Thinking: High | Temp: 0.1]
- Files Modified: `tools/core/eval_runner.py`
- Write Set: ['tools/core/eval_runner.py']
- consumes: [{'contract': 'GateExecutionBundleDTO'}]
- produces: [{'contract': 'EvalCompositeScoreDTO'}]
- Circuit Breaker: Max Fix Attempts: 2 | Scope Guard: <= 1 file
- Rollback Hook: git restore tools/core/eval_runner.py
- Pass Gate: pytest tests/test_eval_runner.py -q

### Milestone 3: Remediate Subpackage Path Drift & Temp-Artifact Healing in Agent Canary
- Node ID: M3
- depends_on: ['M2']
- Compute Tier: [Model: Pro | Thinking: High | Temp: 0.1]
- Files Modified: `tools/lint/agent_canary.py`
- Write Set: ['tools/lint/agent_canary.py']
- consumes: [{'contract': 'EvalCompositeScoreDTO'}]
- produces: [{'contract': 'CanaryArenaReportDTO'}]
- Circuit Breaker: Max Fix Attempts: 2 | Scope Guard: <= 1 file
- Rollback Hook: git restore tools/lint/agent_canary.py
- Pass Gate: python3 tools/lint/agent_canary.py --run

### Milestone 4: Harden Multi-Turn Transcript Grounding & Fail-Closed Security in AI Eval Sentinel
- Node ID: M4
- depends_on: ['M3']
- Compute Tier: [Model: Pro | Thinking: High | Temp: 0.1]
- Files Modified: `tools/lint/ai_eval_sentinel.py`, `tests/test_ai_eval_sentinel.py`
- Write Set: ['tools/lint/ai_eval_sentinel.py', 'tests/test_ai_eval_sentinel.py']
- consumes: [{'contract': 'CanaryArenaReportDTO'}]
- produces: [{'contract': 'TranscriptAuditVerdictDTO'}]
- Circuit Breaker: Max Fix Attempts: 2 | Scope Guard: <= 2 files
- Rollback Hook: git restore tools/lint/ai_eval_sentinel.py tests/test_ai_eval_sentinel.py
- Pass Gate: pytest tests/test_ai_eval_sentinel.py -q

### Milestone 5: Expand Synapse-QA-Bench to 166-Tool Open-Pool Retrieval & Full 4-Scenario Suite
- Node ID: M5
- depends_on: ['M4']
- Compute Tier: [Model: Pro | Thinking: High | Temp: 0.1]
- Files Modified: `tools/orchestration/synapse_qa_bench.py`, `tests/test_ai_agent_eval_hardening.py`
- Write Set: ['tools/orchestration/synapse_qa_bench.py', 'tests/test_ai_agent_eval_hardening.py']
- consumes: [{'contract': 'TranscriptAuditVerdictDTO'}]
- produces: [{'contract': 'BFCLOpenPoolReportDTO'}]
- Circuit Breaker: Max Fix Attempts: 2 | Scope Guard: <= 2 files
- Rollback Hook: git restore tools/orchestration/synapse_qa_bench.py && rm -f tests/test_ai_agent_eval_hardening.py
- Pass Gate: pytest tests/test_ai_agent_eval_hardening.py -q

### Milestone 6: Harvest Tier-2 Architectural Rulings into ADR-0022 & Update ADR Index
- Node ID: M6
- depends_on: ['M5']
- Compute Tier: [Model: Flash | Thinking: Off | Temp: 0.1]
- Files Modified: `docs/adr/ADR-0022-ai-agent-sensor-integrity.md`, `docs/adr/README.md`
- Write Set: ['docs/adr/ADR-0022-ai-agent-sensor-integrity.md', 'docs/adr/README.md']
- consumes: [{'contract': 'BFCLOpenPoolReportDTO'}]
- produces: [{'contract': 'BFCLOpenPoolReportDTO'}]
- Circuit Breaker: Max Fix Attempts: 2 | Scope Guard: <= 2 files
- Rollback Hook: git restore docs/adr/README.md && rm -f docs/adr/ADR-0022-ai-agent-sensor-integrity.md
- Pass Gate: python3 tools/lint/lint_ai_docs.py

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Milestone | Scenario & Precondition | Expected Deterministic Outcome | Verification Command |
| :---: | :---: | :--- | :--- | :--- |
| **V-01** | `M1`–`M2` | **Negative Fake-Pass & Race Prevention:** Inject `RuntimeError` or broken step in `HarnessSentinel`; run `EvalRunner(tier="fast")` without touching shared `reports/verify_all_report.json` | `harness` component drops below `100.0` (`0.0` on exception) with `HARNESS_LAYER_DEFECT` recorded; `1` failed static gate yields proportional `s_tests` proxy (`90.91`) instead of `0.0` cliff; `95.58` magic fallback eliminated | `pytest tests/test_eval_runner.py -v` |
| **V-02** | `M1`–`M2` | **CLI Live Verification (`eval_runner` & `harness_sentinel`):** Execute `harness_sentinel.py --json` and `eval_runner.py --tier fast --no-compare --json` | `harness_sentinel.py` exits `0` (`100.0%` with callable smoke probes); `eval_runner.py` exits `0` (`11/11` gates reported accurately, `all_passed == True`) | `python3 tools/core/harness_sentinel.py --json && python3 tools/core/eval_runner.py --tier fast --no-compare --json` |
| **V-03** | `M3` | **Positive & Clean-CI Boundary (`agent_canary`):** Run `agent_canary.py --run` both with and without `~/.agent_memory/global_cache.db` mocked absent; inspect `V3`, `V4`, `V6`, `V7`, `V8`, and post-DoD gate | `8/8` vectors detected (`100.0%`) and `8/8` healed (`100.0%`); `V6`/`V7` sanitize real temp files; `verify_all.py` executes cleanly (`dod_compliant == True`, `Level 5.0`, exit `0`) | `python3 tools/lint/agent_canary.py --run && pytest tests/test_ai_agent_eval_hardening.py -k "canary"` |
| **V-04** | `M4` | **Boundary & Adversarial Transcript Audit (`ai_eval_sentinel`):** Audit (a) `0`-turn transcript, (b) `SYSTEM_MESSAGE` + `truncated_fields` paired with `transcript_full.jsonl`, (c) intermediate `tool_calls` progress turn, (d) prompt-injected turn | (a) `audit_status == "INCONCLUSIVE"` & `is_trustworthy == False`; (b) numbers from full log/system message grounded (`faithfulness == 1.0`); (c) progress turn not flagged irrelevant; (d) injection forces `is_trustworthy == False` (exit `1` with `--gate-safety`) | `pytest tests/test_ai_eval_sentinel.py tests/test_ai_eval_p0_p2.py -v` |
| **V-05** | `M5` | **Open-Pool 166-Tool BFCL & Abstention (`synapse_qa_bench`):** Run `synapse_qa_bench.py --json` over all `166` schema tools plus out-of-domain negative queries (e.g. Kubernetes Helm / iOS Xcode signing) | `candidate_pool_size >= 160`; `overall_score >= 90.0%`, `arg_validity_accuracy == 100.0%`; out-of-domain intents abstain cleanly instead of hallucinating a QA CLI tool | `python3 tools/orchestration/synapse_qa_bench.py --json && pytest tests/test_ai_agent_eval_hardening.py -k "qa_bench"` |
| **V-06** | `M1`–`M6` | **Full Solo Mandate (Mutation >= 80% + Impact DoD Gates):** Run `micro_mutator.py` across modified sensors and execute Hub impact quality gates + ADR schema lint | Live/syntactic mutation score `>= 80.0%`; `lint_ai_docs.py` and all `11` Hub DoD Quality Gates exit `0` | `pytest tests/test_ai_agent_eval_hardening.py -v && python3 tools/core/verify_all.py --mode hub --tier impact` |

---

## 5. Tri-Vulnerability Self-Critique & Red-Teaming

1. **Race Condition & Concurrency Safety:**
   - Previously, `EvalRunner.run_quality_gates()` executed `run_all_gates()` and then re-read the global `reports/verify_all_report.json` file on disk, causing intermittent score drops (`98.93` -> `65.29`) whenever a concurrent process updated `reports/`. Returning `GateExecutionBundleDTO` directly in memory from `run_all_gates_detailed()` and allowing optional isolated `report_path` overrides makes concurrent evaluations 100% race-free and idempotent.
2. **Boundary & Extreme Resource Resilience:**
   - When `audit_agent_transcript()` encounters `truncated_fields` on a compact `transcript.jsonl`, `load_full_transcript_steps()` streams `transcript_full.jsonl` line-by-line extracting only matching `step_index` records capped at `16 KB` per step rather than loading multi-megabyte session logs into memory.
   - Empty transcripts (`0` spoken planner turns), malformed JSONL lines, missing `transcript_full.jsonl` siblings, and missing `tools_schema.json` entries are handled without unhandled exceptions while failing closed on trustworthiness gates.
3. **Backward Compatibility & Caller Blast Radius:**
   - `verify_all.run_all_gates()` retains its exact legacy parameter list and `int` return type by delegating to `run_all_gates_detailed()[0]`, guaranteeing zero breakage across all `91` existing callers and `tests/test_verify_all.py`.
   - `SynapseQABench(cases=custom_cases)` preserves deterministic compatibility with `tests/test_ai_eval_p0_p2.py` while enabling full `166`-tool `tools_schema.json` candidate resolution by default on standard benchmark runs.

---

## Recommended Execution Model & Thinking Level

- **Primary Executor Model & Thinking Level (Single-Session Default):** `Gemini 4 Hydrogen (High)` (or `Gemini 4 Carbon (Medium)` / `Gemini 4 Neon (Medium)` for single-session sequential `/solo` execution across `M1` -> `M6` with Red-Green-Purple TDD and `>= 80%` mutation verification).
- **Milestone Escalation Overrides (Optional / `/teamwork` Only):** Under default `/solo`, all `6` milestones run sequentially in one session on the Primary Executor (`0` `swarm` workers spawned). `M6` (ADR documentation) is lightweight (`Flash`), whereas `M1`–`M5` modify core verification sensors and IDF scoring logic that benefit from `High` thinking.
- **Rationale:** `M1` (`verify_all.py` with `91` callers), `M4` (multi-turn transcript state machine), and `M5` (166-tool IDF retrieval calibration) require high analytical precision to maintain 100% backward compatibility while achieving `>= 80%` mutation kill sensitivity.
- **Clean Context Handoff:** `"Read implementation_plan_ai_agent_eval.md and execute sequentially via /solo (single-agent mode, no swarm workers)"`
