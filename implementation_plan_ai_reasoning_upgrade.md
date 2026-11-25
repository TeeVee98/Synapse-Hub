<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Spec-Driven Implementation Plan: 6-Layer AI Reasoning & Verification Pipeline Upgrade

> **Reference Protocol:** [AGENTS.md §5](AGENTS.md), [.agent/skills/super-plan/SKILL.md](.agent/skills/super-plan/SKILL.md)
> **Super-Plan Metadata:** `Tier 2 (DEEP_SUPER_PLAN)` | `BlastRadius = 28` (`FanIn = 23` across `tools/` and `tests/`, `9` target files)
> **Isolated Plan Path:** `implementation_plan_ai_reasoning_upgrade.md` (strictly isolated from `implementation_plan.md` and `implementation_plan_phase2_wiring.md`)
> **Execution Mode:** Sequential Single-Agent `/solo` (`M1` -> `M5`, one session, one primary model/thinking level; strictly `0` `swarm` workers or parallel subagents)
> **Ambiguity Gate Status:** Resolved (3 architectural forks locked with user rulings at Stage 2)
> **Governing Rulings (Locked at Stage 2 Ambiguity Gate):**
> - `Ruling 1 (EvalRunner & TextGrad Dual Hardening):` Remediate both sides of the Truth Anchor gap — eliminate bare `pass` exception blocks and wall-clock `time.time` duration drift in `tools/core/eval_runner.py` (achieving native `10.0/10` quality) AND wire the `--metric` flag (`all | clean-pom | resilience`) plus controlled `# synapse-ignore` awareness and safe bootstrap updates in `tools/ai/textgrad_optimizer.py` — eliminates both root defects and false-positive bootstrap penalties across `tools/`.
> - `Ruling 2 (Grounded Repo-AST Probe in Semantic Entropy):` Upgrade `tools/reasoning/semantic_entropy.py` with a zero-LLM, stdlib-only repository symbol/file grounding probe when `--prompt` is invoked directly (allowing grounded repository queries to converge at `SE <= 0.50` while keeping genuinely ambiguous prompts locked at `SE > 0.50`), strip project brand noise (`Synapse`, `Hub`) from epistemic search targets, and preserve 100% backward compatibility with all existing prompt triggers and test suites.
> - `Ruling 3 (Full 6-Layer Tier-2 Scope & Isolated Export):` Upgrade all 6 AI reasoning/verification engines (`step_back_engine.py`, `self_discover_engine.py`, `semantic_entropy.py`, `prover_verifier_games.py`, `cove_verifier.py`, `textgrad_optimizer.py`) alongside `eval_runner.py`, certify with a 4-scenario regression suite (`tests/test_ai_reasoning_6layer_upgrade.py`), and harvest rulings into `docs/adr/ADR-0022-ai-reasoning-6layer-pipeline-upgrade.md`.
> **Plan Changelog (v1.0):**
> - Initial Tier-2 Deep Super-Plan synthesized from empirical findings of the 6-layer self-verification audit on Synapse Hub.

---

## 0. Orthogonal Architectural Tournament (Trade-off Matrix)

| Evaluation Criteria | Branch A: Minimalist | Branch B: Clean Architecture | Branch C: High Performance |
| :--- | :--- | :--- | :--- |
| **Core Philosophy** | Patch only `eval_runner.py` exception blocks; leave reasoning engines untouched | Domain-grounded adapters, typed contracts, and AST-verified sensors across all 6 layers | Async parallel file indexing with persistent in-memory daemon cache |
| **Blast Radius** | Minimal (`1` file) but leaves 5 reasoning blind spots unresolved | Bounded (`7` existing modules + `1` test suite + `1` ADR, `<= 2` files per milestone) | High (requires changing synchronous CLI interfaces across `fan_in = 23` callers) |
| **Regression Risk** | Low, yet fails to fix dead `--metric` CLI flag or CoVe substring false positives | Lowest for multi-module upgrade (100% backward-compatible signatures & CLI JSON schemas) | Medium-High (cache invalidation and event-loop friction in CLI subprocesses) |
| **Execution Speed** | Sub-5ms | Sub-25ms stdlib AST/index inspection (0 external dependencies, 0 LLM tokens) | Sub-5ms warm cache, slow cold boot |
| **Selection Verdict** | Score `6.45` — Insufficient sensor rigor | **(Recommended)** Score `9.32` — Optimal isolation, contract fidelity, and zero caller breakage | Score `7.18` — Over-engineered for deterministic CLI tools |

> **Ruling:** Selected Branch: **[Branch B: Clean Architecture]** — `fan_in = 23` across `super_plan_engine.py`, `solo_runner.py`, `senior_code_review.py`, and `15` test suites demands strict backward-compatible method signatures combined with clean internal domain separation — cost: `5` sequential `/solo` milestones (`9` total files).

---

## Cognitive Grounding & Budget
- **Step-Back Principles:** Guide-Sensor Feedback Completeness: Every architectural invariant declared in Guides (`AGENTS.md`) must map to an AST-grounded, non-vacuous Sensor without substring false positives or swallowed-exception blind spots; Monotonic Quality Ratchet: Self-verification engines must uphold the exact rules they enforce (`max_fix_attempts = 2`, zero unconditional `networkidle`, monotonic duration clocks).
- **Self-Discover Primitives:** `MOD_INVARIANT_ISOLATION: Invariant Isolation`, `MOD_AST_GROUNDED_TRACING: AST Grounded Tracing`, `MOD_TRUTH_ANCHOR_VERIFICATION: Truth Anchor Verification`, `MOD_RESOURCE_EXHAUSTION_PROBING: Resource Exhaustion Probing`
- **DynamicBudget Allocation:** category=`architectural_reasoning` | thinking_budget=`8192` | max_tokens=`4096`

---

## 1. Affected Files & Blast Radius

### Target Files & Structural Anchors

| Action | File Path & Structural Anchor | Line Range | Scope & Responsibility |
| :---: | :--- | :---: | :--- |
| `[MODIFY]` | `tools/reasoning/step_back_engine.py` (AST: StepBackEngine) | `L59-L186` | Add `HARNESS_VERIFICATION_ARCHITECTURE` domain (`architecture`, `verification`, `pipeline`, `harness`, `invariant`, `gate`) so architecture prompts derive Guide-Sensor invariants instead of Clean POM defaults; replace unconditional `network idle` guardrail at `L170` with bounded `waitForURL` / `waitForResponse` predicates per `AGENTS.md` Rule 1.3. |
| `[MODIFY]` | `tools/reasoning/self_discover_engine.py` (AST: SelfDiscoverEngine) | `L65-L168` | Add domain selection boosters for `architecture` / `verification` / `pipeline` / `harness` (`MOD_INVARIANT_ISOLATION`, `MOD_AST_GROUNDED_TRACING`, `MOD_TRUTH_ANCHOR_VERIFICATION`); add module-specific `MOD_TRUTH_ANCHOR_VERIFICATION` directives in `adapt()` and align `resilience_recovery` retry cap to `K <= 2` (`AGENTS.md` Rule 1.13). |
| `[MODIFY]` | `tools/reasoning/semantic_entropy.py` (AST: SemanticEntropyEngine) | `L304-L390` | Add stdlib `_probe_repo_grounding()` in `generate_candidate_hypotheses()` to inspect physical repo artifacts/symbols when `--prompt` references real Hub entities while keeping all legacy prompt triggers intact; filter brand noise (`Synapse`, `Hub`) in `_generate_epistemic_search_plan()`. |
| `[MODIFY]` | `tools/reasoning/prover_verifier_games.py` (AST: VerifierAgent) | `L336-L426` | Upgrade `VerifierAgent.generate_attack()` to rotate distinct adversarial stress vectors across rounds `1..5` (concurrency memory pressure, subprocess timeout/rollback drift, cross-bridge schema skew) instead of repeating identical fallback text across all rounds on governance specs like `AGENTS.md`. |
| `[MODIFY]` | `tools/ai/cove_verifier.py` (AST: ChainOfVerificationEngine) | `L56-L271` | Replace substring triggers (`post`, `add`, `timeout`) with word/call-boundary regexes; add `EXCEPTION_HYGIENE` blind AST check catching unsanctioned `except ...: pass` / `_ = err` blocks on Python modules; inspect all `ast.ClassDef` nodes in `INHERITANCE_INVARIANT`. |
| `[MODIFY]` | `tools/ai/textgrad_optimizer.py` (AST: TextGradOptimizer) | `L74-L284` | Wire CLI `--metric` (`all | clean-pom | resilience`) into `TextGradOptimizer` and `evaluate_loss()`; honor inline `# synapse-ignore` suppression markers with bounded advisory weighting; guard `apply_textual_update()` against breaking `except ImportError` module bootstrap blocks. |
| `[MODIFY]` | `tools/core/eval_runner.py` (AST: EvalRunner) | `L45-L345` | Replace bare `pass` in `except ImportError` (`L57`) and broad `except Exception` (`L65`) with narrowed `(AttributeError, OSError, ValueError)` handling and explicit debug diagnostics; switch `duration_sec` timing (`L300`, `L324`) to `time.monotonic()`; add bounded subprocess timeout/memory-pressure resilience metadata. |
| `[CREATE]` | `tests/test_ai_reasoning_6layer_upgrade.py` (New) | `L1-L260` | Dedicated 4-scenario regression battery (Positive, Negative, Boundary, CLI Flags) covering all 6 upgraded reasoning/AI tools and `EvalRunner`, engineered for `>= 80.0%` AST mutation kill score. |
| `[CREATE]` | `docs/adr/ADR-0022-ai-reasoning-6layer-pipeline-upgrade.md` (New) | `L1-L95` | Tier-2 Architecture Decision Record documenting the 6-layer self-verification audit, Stage 2 rulings, interface contracts, and empirical before/after verification metrics. |

### Blast Radius & Downstream Dependencies
- **Direct Callers (`fan_in = 23`):** `tools/design/super_plan_engine.py` (imports `StepBackEngine`, `SelfDiscoverEngine`, `TextGradOptimizer`), `tools/orchestration/solo_runner.py` (invokes `ProverVerifierGame`), `tools/orchestration/senior_code_review.py`, and `tools/core/self_evolving_loop.py` (invokes `EvalRunner`).
- **Downstream Test Suites:** `tests/test_step_back_engine.py`, `tests/test_self_discover_engine.py`, `tests/test_semantic_entropy.py`, `tests/test_prover_verifier_games.py`, `tests/test_cove_verifier.py`, `tests/test_textgrad_optimizer.py`, `tests/test_eval_runner.py`, `tests/test_ai_eval_p0_p2.py`, and `tests/e2e/test_deep_reasoning_pipeline_e2e.py`.
- **Backward Compatibility Guarantee:** Zero breaking changes to existing class constructors, method names, return dictionary keys, or CLI flags (`optional` default parameters only).

---

## 2. Data Flow & Interface Signatures

> **Anti-Full-Code Invariant:** Define ONLY typed DTOs, schemas, and function signatures. Full algorithmic bodies are deferred strictly to sequential `/solo` execution.

```python
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class CognitiveAbstractionBundleDTO:
    """Output contract produced by Milestone 1 (Step-Back & Self-Discover alignment)."""
    domain_category: str
    governing_invariant: str
    selected_module_ids: Tuple[str, ...]
    retry_ceiling: int


@dataclass(frozen=True)
class EpistemicDebateVerdictDTO:
    """Output contract produced by Milestone 2 (Grounded Entropy & Multi-Round Debate)."""
    normalized_entropy: float
    repo_grounded_hits: int
    epistemic_targets: Tuple[str, ...]
    distinct_round_vectors: int
    nash_equilibrium_score: float


@dataclass(frozen=True)
class AstGradientAuditDTO:
    """Output contract produced by Milestone 3 (CoVe Word-Boundary AST & TextGrad Metric)."""
    metric_profile: str
    factual_confidence_pct: float
    unsanctioned_swallowed_count: int
    sanctioned_ignore_count: int
    quality_score: float


@dataclass(frozen=True)
class EvalHarnessScoreReceiptDTO:
    """Output contract produced by Milestone 4 (EvalRunner Hardening & 4-Scenario Suite)."""
    composite_score: float
    monotonic_duration_sec: float
    textgrad_loss: float
    cove_confidence_pct: float
    mutation_kill_pct: float


@dataclass(frozen=True)
class AdrHarvestReceiptDTO:
    """Output contract produced by Milestone 5 (ADR-0022 & Hub Impact DoD Gate)."""
    adr_path: str
    gates_passed: int
    retention_accepted: bool


# Layer 1 & 2 Signatures
def generate_abstract_questions(self, task_text: str) -> List[Dict[str, str]]: ...
def select(self, task_text: str, top_k: int = 4) -> List[Dict[str, Any]]: ...
def adapt(self, selected_modules: List[Dict[str, Any]], task_text: str) -> List[Dict[str, Any]]: ...

# Layer 3 & 4 Signatures
def _probe_repo_grounding(self, prompt: str) -> Tuple[bool, List[str]]: ...
def generate_candidate_hypotheses(self, prompt: str, count: int = 4) -> List[str]: ...
def generate_attack(
    cls,
    round_num: int,
    proposal_text: str,
    context_text: str,
    prover_argument: Any,
) -> Any: ...

# Layer 5, 6 & EvalRunner Signatures
def generate_verification_questions(self, draft_content: str, filename: str) -> List[Dict[str, str]]: ...
def evaluate_loss(
    self,
    code_content: str,
    filename: str,
    metric: Optional[str] = None,
) -> Tuple[float, List[Any]]: ...
def evaluate(self, compare_baseline: bool = True, silent: bool = False) -> Dict[str, Any]: ...
```

---

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Step-Back & Self-Discover Domain Alignment
- **Node ID:** `M1` | **depends_on:** `[]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Best-of-3]`
- **Files Modified (Max 3):** `tools/reasoning/step_back_engine.py`, `tools/reasoning/self_discover_engine.py`
- **Write Set:** `['tools/reasoning/step_back_engine.py', 'tools/reasoning/self_discover_engine.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[]`
  - **produces:** `[{"contract": "CognitiveAbstractionBundleDTO", "fields": {"domain_category": "str", "retry_ceiling": "int"}}]`
  - **invariants:** `["zero_unconditional_networkidle", "retry_ceiling == 2", "backward_compat_super_plan_engine"]`
- **Goal:** Add `HARNESS_VERIFICATION_ARCHITECTURE` abstraction principles in `StepBackEngine`, eliminate unconditional `network idle` advice (`L170`), add architecture/verification boosters in `SelfDiscoverEngine.select()`, and add explicit `MOD_TRUTH_ANCHOR_VERIFICATION` adaptation directives with `K <= 2` circuit-breaker alignment.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if `super_plan_engine.py` cognitive brief schema breaks
- **Rollback Hook:** `git restore --source=HEAD --staged --worktree -- tools/reasoning/step_back_engine.py tools/reasoning/self_discover_engine.py`
- **Pass Gate:** `pytest tests/test_step_back_engine.py tests/test_self_discover_engine.py`

### Milestone 2: Grounded Semantic Entropy & Multi-Round Adversarial Debate
- **Node ID:** `M2` | **depends_on:** `[M1]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Best-of-3]`
- **Files Modified (Max 3):** `tools/reasoning/semantic_entropy.py`, `tools/reasoning/prover_verifier_games.py`
- **Write Set:** `['tools/reasoning/semantic_entropy.py', 'tools/reasoning/prover_verifier_games.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[{"contract": "CognitiveAbstractionBundleDTO"}]`
  - **produces:** `[{"contract": "EpistemicDebateVerdictDTO", "fields": {"normalized_entropy": "float", "distinct_round_vectors": "int"}}]`
  - **invariants:** `["0.0 <= normalized_entropy <= 1.0", "distinct_round_vectors >= rounds_for_spec", "preserve_legacy_prompt_triggers"]`
- **Goal:** Implement `_probe_repo_grounding()` in `SemanticEntropyEngine` for grounded repository prompts, filter `Synapse` and `Hub` brand tokens out of epistemic search targets while keeping symbol extraction (`BasePage`) intact, and rotate distinct round-indexed adversarial counter-examples in `VerifierAgent.generate_attack()` across multi-round debates on governance documents.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if any assertion in `test_semantic_entropy.py` or `test_prover_verifier_games.py` regresses
- **Rollback Hook:** `git restore --source=HEAD --staged --worktree -- tools/reasoning/semantic_entropy.py tools/reasoning/prover_verifier_games.py`
- **Pass Gate:** `pytest tests/test_semantic_entropy.py tests/test_prover_verifier_games.py tests/e2e/test_deep_reasoning_pipeline_e2e.py`

### Milestone 3: CoVe AST Exception Hygiene & TextGrad Metric Wiring
- **Node ID:** `M3` | **depends_on:** `[M2]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Best-of-3]`
- **Files Modified (Max 3):** `tools/ai/cove_verifier.py`, `tools/ai/textgrad_optimizer.py`
- **Write Set:** `['tools/ai/cove_verifier.py', 'tools/ai/textgrad_optimizer.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[{"contract": "EpistemicDebateVerdictDTO"}]`
  - **produces:** `[{"contract": "AstGradientAuditDTO", "fields": {"metric_profile": "str", "quality_score": "float"}}]`
  - **invariants:** `["word_boundary_question_triggers", "metric_flag_enforced", "safe_bootstrap_textual_update"]`
- **Goal:** Replace substring matching in `ChainOfVerificationEngine` with word/call-boundary regexes, add blind `EXCEPTION_HYGIENE` AST verification + multi-class `BasePage` inheritance checks, wire `--metric` (`all | clean-pom | resilience`) through `TextGradOptimizer`, respect `# synapse-ignore: SWALLOWED_EXCEPTION` markers without false fatal loss, and prevent `apply_textual_update()` from injecting breaking `RuntimeError` raises into `except ImportError` bootstrap guards.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if `super_plan_engine.py calibrate` contract changes
- **Rollback Hook:** `git restore --source=HEAD --staged --worktree -- tools/ai/cove_verifier.py tools/ai/textgrad_optimizer.py`
- **Pass Gate:** `pytest tests/test_cove_verifier.py tests/test_textgrad_optimizer.py tests/test_ai_eval_p0_p2.py`

### Milestone 4: EvalRunner Zero-Loss Hardening & 4-Scenario Verification Suite
- **Node ID:** `M4` | **depends_on:** `[M3]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Best-of-3]`
- **Files Modified (Max 3):** `tools/core/eval_runner.py`, `tests/test_ai_reasoning_6layer_upgrade.py`
- **Write Set:** `['tools/core/eval_runner.py', 'tests/test_ai_reasoning_6layer_upgrade.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[{"contract": "AstGradientAuditDTO"}]`
  - **produces:** `[{"contract": "EvalHarnessScoreReceiptDTO", "fields": {"composite_score": "float", "textgrad_loss": "float", "mutation_kill_pct": "float"}}]`
  - **invariants:** `["eval_runner_textgrad_loss == 0.0", "monotonic_clock_enforced", "mutation_kill_pct >= 80.0"]`
- **Goal:** Refactor `tools/core/eval_runner.py` to remove bare `pass` exception blocks (`L57`, `L65`), narrow UTF-8 stream reconfiguration to `(AttributeError, OSError, ValueError)` with explicit debug logging, switch `duration_sec` to `time.monotonic()`, add bounded subprocess timeout resilience, and author `tests/test_ai_reasoning_6layer_upgrade.py` covering Positive, Negative, Boundary, and CLI Flag scenarios across all 7 upgraded modules.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if `EvalRunner` retention or baseline schema breaks
- **Rollback Hook:** `git restore --source=HEAD --staged --worktree -- tools/core/eval_runner.py && rm -f tests/test_ai_reasoning_6layer_upgrade.py`
- **Pass Gate:** `pytest tests/test_eval_runner.py tests/test_ai_reasoning_6layer_upgrade.py`

### Milestone 5: Tier-2 ADR-0022 Harvesting & Full Hub Impact Certification
- **Node ID:** `M5` | **depends_on:** `[M4]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 3):** `docs/adr/ADR-0022-ai-reasoning-6layer-pipeline-upgrade.md`
- **Write Set:** `['docs/adr/ADR-0022-ai-reasoning-6layer-pipeline-upgrade.md']`
- **Typed Interface Manifest:**
  - **consumes:** `[{"contract": "EvalHarnessScoreReceiptDTO"}]`
  - **produces:** `[{"contract": "AdrHarvestReceiptDTO", "fields": {"adr_path": "str", "retention_accepted": "bool"}}]`
  - **invariants:** `["english_only_rule_16", "mit_attribution_preserved", "zero_gate_regressions"]`
- **Goal:** Author `docs/adr/ADR-0022-ai-reasoning-6layer-pipeline-upgrade.md` recording the Stage 2 architectural rulings, re-run all 6 AI reasoning CLI layers to capture empirical post-upgrade telemetry, and certify via `solo_runner.py` (`--mutation`, `--purple`), `infer_linter.py`, `invariant_checker.py --rule 16`, and `verify_all.py --mode hub --tier impact`.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt and report if any out-of-scope legacy gate fails (`AGENTS.md` Rule 1.6)
- **Rollback Hook:** `rm -f docs/adr/ADR-0022-ai-reasoning-6layer-pipeline-upgrade.md`
- **Pass Gate:** `python3 tools/lint/invariant_checker.py --rule 16 --json && python3 tools/lint/infer_linter.py`

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
| :--- | :--- | :--- | :--- | :--- |
| **TC-01** | **Positive — Architecture Step-Back & Self-Discover** | Task `"Evaluate Synapse Hub architecture and verification pipeline"` | `StepBackEngine` emits `HARNESS_VERIFICATION_ARCHITECTURE` principle (zero `network idle`); `SelfDiscoverEngine` selects `MOD_INVARIANT_ISOLATION` / `MOD_TRUTH_ANCHOR_VERIFICATION` with `K <= 2` directives | `pytest tests/test_ai_reasoning_6layer_upgrade.py -k "test_step_back_and_self_discover_architecture"` |
| **TC-02** | **Positive — Grounded Entropy & Multi-Round Debate** | Grounded repo prompt on `verify_all.py` vs `AGENTS.md` 3-round debate | Grounded prompt resolves real repo file targets without `Synapse`/`Hub` noise; `ProverVerifierGame` emits `3` distinct round counter-examples on `AGENTS.md` | `pytest tests/test_ai_reasoning_6layer_upgrade.py -k "test_grounded_entropy_and_multi_round_debate"` |
| **TC-03** | **Positive — EvalRunner Native 10/10 on CoVe & TextGrad** | Run `cove_verifier.py` and `textgrad_optimizer.py --metric all` on `tools/core/eval_runner.py` | CoVe `status == "PASS"` (`100.0%`, zero false `DATA_COLLISION` from `composite`); TextGrad `initial_quality == "10.0/10"`, `loss == 0.0`, monotonic `duration_sec >= 0.0` | `pytest tests/test_ai_reasoning_6layer_upgrade.py -k "test_eval_runner_zero_loss_and_cove_precision"` |
| **TC-04** | **Negative — Unsanctioned Swallowed Exception & Invalid Metric** | Python draft containing unsanctioned `except ValueError: pass` and invalid CLI `--metric unknown` | CoVe flags `DISCREPANCY_DETECTED` under `EXCEPTION_HYGIENE`; TextGrad `--metric resilience` filters out POM-only gradients while invalid CLI `--metric` exits non-zero cleanly | `pytest tests/test_ai_reasoning_6layer_upgrade.py -k "test_negative_exception_hygiene_and_metric_filter"` |
| **TC-05** | **Boundary — Empty/Single Inputs & Bootstrap Import Guard** | Empty draft, single hypothesis, `# synapse-ignore` bootstrap `except ImportError`, `rounds=0` / `rounds=10` | Zero `ZeroDivisionError` or `SyntaxError`; `apply_textual_update` preserves valid Python syntax on `except ImportError` blocks | `pytest tests/test_ai_reasoning_6layer_upgrade.py -k "test_boundary_empty_and_bootstrap_update"` |
| **TC-06** | **CLI Flags & Backward-Compatibility Regression** | Execute all 6 CLI scripts with `--json` plus all legacy unit/E2E suites | Exit code `0` on valid runs, valid JSON schemas, `100%` pass across all `9` existing reasoning/AI test suites, mutation score `>= 80.0%` | `pytest tests/test_step_back_engine.py tests/test_self_discover_engine.py tests/test_semantic_entropy.py tests/test_prover_verifier_games.py tests/test_cove_verifier.py tests/test_textgrad_optimizer.py tests/test_eval_runner.py tests/test_ai_eval_p0_p2.py tests/e2e/test_deep_reasoning_pipeline_e2e.py tests/test_ai_reasoning_6layer_upgrade.py` |

---

## 5. Tri-Vulnerability Self-Critique & Mitigations

1. **Vulnerability 1 (Concurrency / Race Condition):**
   - *Risk:* Running `EvalRunner` or `SemanticEntropyEngine` repo grounding concurrently across CI workers could collide on shared report paths (`reports/eval_report.json`) or experience wall-clock NTP skew during elapsed duration calculation.
   - *Mitigation:* Switch `EvalRunner.evaluate()` elapsed timing strictly to `time.monotonic()`, honor caller-isolated `report_path` / `baseline_path` instances, and ensure `_probe_repo_grounding()` performs strictly read-only, stateless file/AST inspection.
2. **Vulnerability 2 (Boundary / Extreme Resource Pressure):**
   - *Risk:* `_probe_repo_grounding()` scanning the entire repository tree (`1,700+` test files) on every `--prompt` invocation could stall CLI latency or exhaust memory under high concurrency pressure (the exact counter-example surfaced by Layer 4 `ProverVerifierGame`).
   - *Mitigation:* Bound repository grounding strictly to lightweight index manifests (`tools/tools_schema.json`, `skills_index.json`, top-level `AGENTS.md`) and targeted path lookups (`<= 5` candidate files, `< 64 KB` read cap, zero recursive full-repo walk), keeping execution latency under `15ms`.
3. **Vulnerability 3 (Blast Radius / Backward Compatibility):**
   - *Risk:* Changing `TextGradOptimizer.__init__` or `evaluate_loss` signatures, or altering `SemanticEntropyEngine.generate_candidate_hypotheses` outputs for existing keywords (`consensus`, `divergent`, `ambiguous`, `timeout`, `return type`), could break `super_plan_engine.py::calibrate_and_refine_plan` or existing test suites (`fan_in = 23`).
   - *Mitigation:* Add `metric: str = "all"` as a default-preserving keyword parameter, keep all existing keyword branches in `generate_candidate_hypotheses()` first in evaluation order before invoking `_probe_repo_grounding()` on unmatched prompts, and verify all `9` downstream test suites in Milestonegates.

---

## 6. Rollback & State-Migration Matrix (Zero-Downtime Guard)

| Phase | Trigger Scenario | Mitigation / Dual-Mode Fallback | Path-Scoped Rollback Command |
| :--- | :--- | :--- | :--- |
| **M1–M2 (Reasoning Engines)** | Downstream `super_plan_engine.py` or E2E reasoning suite regression | Default-argument preservation on `StepBackEngine` and `SemanticEntropyEngine` | `git restore --source=HEAD --staged --worktree -- tools/reasoning/step_back_engine.py tools/reasoning/self_discover_engine.py tools/reasoning/semantic_entropy.py tools/reasoning/prover_verifier_games.py` |
| **M3 (CoVe & TextGrad)** | Plan calibration loss drift or unexpected gradient shift | Default `metric="all"` preserves legacy invocation contract | `git restore --source=HEAD --staged --worktree -- tools/ai/cove_verifier.py tools/ai/textgrad_optimizer.py` |
| **M4–M5 (EvalRunner, Tests & ADR)** | Mutation score `< 80.0%` or `EvalRunner` baseline retention failure | Restore `eval_runner.py` and purge newly created untracked test/ADR files without touching unrelated workspace edits | `git restore --source=HEAD --staged --worktree -- tools/core/eval_runner.py && rm -f tests/test_ai_reasoning_6layer_upgrade.py docs/adr/ADR-0022-ai-reasoning-6layer-pipeline-upgrade.md` |

---

## 7. Execution Transition & Plan Harvesting

- **Execution Mode:** Single-Agent Sequential (`/solo`) — Execute `M1` -> `M2` -> `M3` -> `M4` -> `M5` sequentially in a single session (`Red -> Blue -> Micro-Mutator >= 80% -> Purple Self-Audit`). Do NOT spawn `swarm` workers or parallel subagents.
- **Clean Context Handoff:** `"Read implementation_plan_ai_reasoning_upgrade.md and execute sequentially via /solo"`
- **Surgical Patch Protocol:** Update only targeted milestone blocks via `edit_file` and append to the Plan Changelog; never regenerate the entire file.
- **Plan Harvesting Hook:** Upon passing all milestones and `verify_all.py --mode hub --tier impact`, run `python3 tools/design/plan_harvester.py --plan implementation_plan_ai_reasoning_upgrade.md --dry-run` to verify `0.0` semantic contract drift alongside `ADR-0022`.

### Recommended Execution Model & Thinking Level
- **Primary Executor Model & Thinking Level (Single-Session Default):** `Gemini 4 Neon (High)` (or `Gemini 4 Hydrogen (High)` if prioritizing faster turnaround)
- **Milestone Escalation Overrides (Optional / `/teamwork` Only):** Under default `/solo`, one session executes all `5` milestones sequentially on the Primary Executor. If `/teamwork` is explicitly invoked later, `M1`–`M4` map to `Pro / Reasoning (High)` and `M5` (ADR documentation & gate run) maps to `Flash (Off)`.
- **Rationale:** Modifying `7` core reasoning/evaluation engines with `fan_in = 23` requires `High` thinking to maintain AST boundary precision, `>= 80%` mutation kill sensitivity, and `100%` backward compatibility across `9` existing test suites in a single zero-regression pass.
