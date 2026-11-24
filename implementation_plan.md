<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Spec-Driven Implementation Plan: Super-Plan 10.0 Upgrade — Deterministic Mechanical Control Pipeline

> **Reference Protocol:** [AGENTS.md §5](AGENTS.md), [.agent/skills/super-plan/SKILL.md](.agent/skills/super-plan/SKILL.md), [standards/qa-process/plan-protocol.md](standards/qa-process/plan-protocol.md), [ai-agents/workflows/super-plan.md](ai-agents/workflows/super-plan.md)
> **Ambiguity Gate Status:** Resolved (Deterministic AST Slicing + Invariant-Driven Fail-Closed Evaluation)
> **Architectural-Impact:** High (Core Planning Engine, Polyglot AST Non-Source Engine, Structural Plan Mutation Sentinel, Path-Scoped Safe Rollback, Semantic Interface Drift Harvester)
> 📝 **Plan Changelog (v1.0 — Super-Plan 10.0 Hardening):**
> - Comprehensive resolution of all 5 adversarial vulnerability vectors identified in the Synapse Hub v4.8.0 audit:
>   1. **Risk-Routing (RiskScore):** Whole-word tokenized matching eliminating substring leaks (`core` in `score`, `auth` in `author`); log2 formula bounded by `math.log2(1 + FAN_CAP)` ($[0, 1.0]$ range); config-driven critical paths from `synapse.config.json`; fail-up to Tier 1 upon call-graph indexer anomaly.
>   2. **Ambiguity Gate:** Purged all 255 Vietnamese characters to satisfy Invariant 16 (English-Only Codebase); context-adaptive recommendations based on task invariants (zero static rubber-stamping); headless mode exits with code 3 (`UNRESOLVED_FORK`) when invariants cannot resolve architectural forks.
>   3. **AST Parser & Structural Anchors:** Unified canonical anchor syntax `path::Symbol#ordinal` + `body_hash`; task-matched symbol selection in `scaffold`; 100% format coverage for non-source files (RFC 6901 JSON Pointers for minified/arrays, PyYAML `compose_all`, Dockerfile multiline stage/directive tracking, Shell heredoc isolation, Markdown ATX headings, TOML tables, Gherkin features, and cryptographic hash fallback).
>   4. **Plan Schema Sentinel & Mechanical Mutator:** Real mechanical plan mutation testing with $\ge 12$ structural mutants (field drop, DAG cycles, race inversions, phantom symbols, overwrite collisions, dangerous rollbacks); elimination of keyword-stuffing false passes; allowlist-based rollback hook validator rejecting `reset --hard`, `clean -fdx`, `rm -rf`, `curl | sh`; path-scoped rollback restoring tracked files and unlinking new untracked files with verified clean `git status`.
>   5. **Plan Harvester & Memory Decay:** Deep semantic contract drift detection using polyglot AST interface signature hashing (`sha256(sig)`); temporal memory decay ($0.9$ factor) for coupling associations in `project_state.json`.

---

## 0. Orthogonal Architectural Tournament (Trade-off Matrix)

| Evaluation Criteria | 🏛️ Branch A: Patchwork Regex Heuristics | 📐 Branch B: 10.0 Deterministic Mechanical Control (Recommended) | ⚡ Branch C: Heavyweight External LLM Multi-Agents |
|---|---|---|---|
| **Core Philosophy** | Ad-hoc regex rules, loose substring matching, static prompt hints | Bounded algebraic formulas, RFC 6901 pointers, AST structure mutants, path-scoped atomic rollback | Spawning multiple external subagent dialogues to review every plan line |
| **Blast Radius** | Smallest diff but leaves deep architectural leaks | Targeted, modular upgrades with 100% backward compatibility for existing plan files | Very High (unbounded token explosion, multi-turn latency > 60s) |
| **False-Pass Elimination** | 30% (keyword-stuffed plans pass 100%; phantom symbols undetected) | **100% (Pre-flight symbol validation, 12 mechanical structural mutants, bounded risk math)** | 75% (LLMs suffer from shared confirmation bias & rubber-stamping) |
| **Non-Source File Support** | Minimal (regex line matching fails on minified JSON, YAML lists, Dockerfile RUNs) | **Universal (RFC 6901 JSON pointer, YAML AST, Shell heredocs, Markdown headings, hash fallback)** | Dependent on LLM context ingestion without physical anchors |
| **Execution Latency SLA** | < 50ms | **Sub-second (< 250ms for AST slicing, routing, and 12-mutant audit)** | Extremely slow (> 15–30s per plan generation) |
| **Selection Verdict** | Rejected (fragile, violates Invariant 2 & 11) | **Selected as Governing Standard** | Rejected (excessive token cost, non-deterministic) |

> **Ruling:** Selected Branch: **[Branch B: 10.0 Deterministic Mechanical Control]**.

---

## 1. Affected Files & Blast Radius

### Target Files & Structural Anchors
| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
| `[MODIFY]` | `tools/design/super_plan_engine.py` (AST: calculate_risk_routing) | Tokenized risk routing, bounded math, config-driven critical paths, fail-closed English Ambiguity Gate |
| `[MODIFY]` | `tools/context/polyglot_ast_parser.py` (AST: parse_polyglot_signatures) | Non-source parsing (RFC 6901 JSON pointer, PyYAML compose, Dockerfile multiline, Shell heredoc, Markdown, TOML) |
| `[MODIFY]` | `tools/lint/plan_schema_sentinel.py` (AST: validate_plan_content) | Symbol pre-flight verification, duplicate file collision guard, allowlist rollback validator |
| `[MODIFY]` | `tools/lint/plan_mutator.py` (AST: run_plan_mutation_audit) | 12 structural plan mutants, eliminating keyword stuffing and unconditional parallel kills |
| `[MODIFY]` | `tools/design/plan_harvester.py` (AST: calibrate_plan_against_git) | Semantic AST interface hashing, memory decay pruning in `project_state.json` |
| `[MODIFY]` | `synapse.config.json` (AST: planning) | Explicit hard and soft critical paths, bounded fan-in cap configuration |
| `[CREATE]` | `tests/test_polyglot_anchors.py` (Overwrite) | Comprehensive test battery for non-source files and symbol pre-flight validation |
| `[MODIFY]` | `tests/test_super_plan_and_harvester.py` (AST: TestSuperPlanAndHarvester) | Regression battery covering 12 plan mutants, tokenized routing, and English ambiguity gate |
| `[MODIFY]` | `standards/qa-process/plan-protocol.md` (AST: rule_body) | Align specification with 12 structural mutants and path-scoped atomic rollback |
| `[MODIFY]` | `ai-agents/workflows/super-plan.md` (AST: workflow_body) | Harmonize stage descriptions and anchor standards across documentation |

### Blast Radius Analysis
- **Direct Callers:** `tools/core/agent_runner.py`, `tools/core/verify_all.py`, developer CLI commands (`agent-qa super-plan`, `python tools/design/super_plan_engine.py`).
- **Downstream Verification:** All existing 16 unit tests in `test_super_plan_and_harvester.py` and 27 tests in `test_super_plan_10_perfection.py` must remain 100% green without regression.
- **Regression Mitigation:** Backward-compatible signatures with default parameters; fallback mechanisms when optional dependencies (`pyyaml`, `tomllib`) are unavailable.

---

## 2. Data Flow & Interface Signatures

> **Anti-Full-Code Invariant:** Define ONLY DTOs, schemas, and function signatures with type contracts.

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

class PlanningTier(str, Enum):
    TIER_0_FAST = "FAST_TRACK"       # RiskScore < 0.35, <= 2 files, 0 critical paths
    TIER_1_STANDARD = "STANDARD"      # 0.35 <= RiskScore < 0.70
    TIER_2_DEEP = "DEEP_SUPER_PLAN"   # RiskScore >= 0.70 or critical path

@dataclass(frozen=True)
class RiskMetricDTO:
    fan_in: int
    cross_boundary: bool
    state_mutation: bool
    history_drift: float
    critical_path: bool = False
    blast_radius: int = 0
    fan_cap: int = 32

    @property
    def risk_score(self) -> float:
        """Computes strictly bounded RiskScore in [0.0, 1.0]."""
        ...

def calculate_risk_routing(
    task: str,
    target_files: Optional[List[str]] = None,
    repo_root: str = "..."
) -> Tuple[PlanningTier, RiskMetricDTO]:
    """Calculates deterministic RiskScore using whole-word token matching and config critical paths."""
    ...

@dataclass(frozen=True)
class AmbiguityQuestionDTO:
    category: str
    question: str
    options: List[str]
    recommended: Optional[str]
    counter_arguments: Dict[str, str]

def check_ambiguities(
    task_description: str,
    invariants: Optional[List[str]] = None,
    repo_root: str = "..."
) -> List[AmbiguityQuestionDTO]:
    """Evaluates task ambiguity in English and infers recommendations from active invariants."""
    ...

@dataclass(frozen=True)
class StructuralAnchorDTO:
    name: str
    kind: str
    signature: str
    line: int
    end_line: int
    anchor: str
    body_hash: Optional[str] = None

def parse_polyglot_signatures(filepath: str, repo_root: Optional[str] = None) -> Dict[str, Any]:
    """Extracts structural anchors across code and non-source formats (JSON, YAML, Dockerfile, Shell, Markdown, TOML)."""
    ...

@dataclass(frozen=True)
class PlanMutationReportDTO:
    total_mutants: int
    killed_mutants: int
    kill_score: float
    passed: bool
    survived_mutations: List[str]
    details: Dict[str, Any]

def run_plan_mutation_audit(plan_content: str, threshold: float = 90.0) -> PlanMutationReportDTO:
    """Applies battery of >= 12 mechanical structural plan mutants and computes Plan Kill Score."""
    ...

def rollback_path_scoped(base_commit: str, declared_modify: List[str], created_files: List[str]) -> bool:
    """Restores tracked files via git restore and safely removes newly created files."""
    ...

def calibrate_plan_against_git(plan_content: str, repo_root: str = "...") -> Dict[str, Any]:
    """Calculates file drift and deep semantic AST interface signature drift."""
    ...
```

---

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Deterministic Bounded Risk Routing
- **Node ID:** `M08` | **depends_on:** `[]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 2):** `tools/design/super_plan_engine.py`, `synapse.config.json`
- **Write Set:** `['tools/design/super_plan_engine.py', 'synapse.config.json']`
- **Typed Interface Manifest:**
  - **consumes:** `[]`
  - **produces:** `[{"contract": "RiskMetricDTO", "fields": {"risk_score": "float", "tier": "PlanningTier"}}]`
  - **invariants:** `["0.0 <= risk_score <= 1.0", "no_substring_leaks", "fail_up_on_missing_graph"]`
- **Goal:**
  1. Tokenize task and file paths using `re.split(r"[^a-z0-9]+", text.lower())`.
  2. Load hard critical paths (`{"auth", "security", "schema", "database", "migration", "payment", "transaction"}`) and soft critical paths (`{"core", "runner", "base_page", "middleware", "invariant"}`) from `synapse.config.json`.
  3. Bounded formula: `blast = min(1.0, math.log2(1 + eff_fan_in) / math.log2(1 + FAN_CAP))` with `FAN_CAP = 32`.
  4. Ensure tasks like "fix typo in the score label" or "update author name" route to Tier 0 Fast-Track (score < 0.35).
  5. In `get_or_build_call_graph` failure handler, fail UP to Tier 1 (`r = max(r, 0.40)`), never silently swallow and drop risk to 0.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside Write Set touched | Rollback: `git checkout -- tools/design/super_plan_engine.py synapse.config.json`
- **Rollback Hook:** `git checkout -- tools/design/super_plan_engine.py synapse.config.json`
- **Pass Gate:** `python3 -m pytest tests/test_super_plan_and_harvester.py -k "risk_routing"`

### Milestone 2: Fail-Closed Ambiguity Gate & Invariant 16 English Enforcement
- **Node ID:** `M09` | **depends_on:** `[M08]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 2):** `tools/design/super_plan_engine.py`, `tests/test_super_plan_and_harvester.py`
- **Write Set:** `['tools/design/super_plan_engine.py', 'tests/test_super_plan_and_harvester.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[{"contract": "RiskMetricDTO"}]`
  - **produces:** `[{"contract": "AmbiguityQuestionDTO", "fields": {"questions": "list", "recommended": "str"}}]`
  - **invariants:** `["english_only_in_engine", "exit_code_3_on_headless_unresolved_fork"]`
- **Goal:**
  1. Translate all Vietnamese strings in `AMBIGUITY_TRIGGERS`, questions, options, counter-arguments to clean, idiomatic English.
  2. Dynamic recommendation: do not default to `options[0]`. Inspect task text and user invariants (e.g. if task mentions "zero new dependency" -> select stdlib; if "postgres" -> select persistent DB).
  3. Headless Mode (`--auto-recommend` / `--non-interactive`): If active task invariants cannot resolve an architectural fork, exit with status code 3 (`UNRESOLVED_FORK`) and emit `[DRAFT-BLOCKED]`, preventing rubber-stamped invalid architectures in unattended CI.
  4. Remove the `< 8 words prompts default question` rule to preserve Tier 0 zero-MCQ fast-track guarantee.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside Write Set touched | Rollback: `git checkout -- tools/design/super_plan_engine.py tests/test_super_plan_and_harvester.py`
- **Rollback Hook:** `git checkout -- tools/design/super_plan_engine.py tests/test_super_plan_and_harvester.py`
- **Pass Gate:** `python3 -m pytest tests/test_super_plan_and_harvester.py -k "ambiguity"`

### Milestone 3: AST Structural Anchors & Symbol Pre-Flight Sensor
- **Node ID:** `M10` | **depends_on:** `[M09]`
- **Compute Tier:** `[Model: Pro | Thinking: High | Best-of-3]`
- **Files Modified (Max 3):** `tools/context/polyglot_ast_parser.py`, `tools/lint/plan_schema_sentinel.py`, `tests/test_polyglot_anchors.py`
- **Write Set:** `['tools/context/polyglot_ast_parser.py', 'tools/lint/plan_schema_sentinel.py', 'tests/test_polyglot_anchors.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[{"contract": "AmbiguityQuestionDTO"}]`
  - **produces:** `[{"contract": "PreflightReportDTO", "fields": {"is_valid": "bool", "missing_symbols": "list"}}]`
  - **invariants:** `["phantom_symbols_rejected", "create_on_existing_file_rejected"]`
- **Goal:**
  1. Unify structural anchor formatting to `path::Symbol#ordinal` with optional body hash anchor `[AST: Symbol | Lxx-Lyy]`.
  2. In `super_plan_engine.py::scaffold_super_plan`, select the AST symbol closest to the task name rather than blindly anchoring `signatures[0]`.
  3. In `plan_schema_sentinel.py::validate_plan_preflight_grounding`: parse referenced symbols and verify they physically exist in the target file on disk via `polyglot_ast_parser`. Reject plans containing phantom signatures.
  4. Reject `[CREATE]` on an existing file on disk unless explicitly marked `(Overwrite)` or `(Replace)`.
  5. Fix line anchor detection in `validate_plan_content` to require anchors specifically on Section 1 target files, not document-wide `any()`.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside Write Set touched | Rollback: `git checkout -- tools/context/polyglot_ast_parser.py tools/lint/plan_schema_sentinel.py tests/test_polyglot_anchors.py`
- **Rollback Hook:** `git checkout -- tools/context/polyglot_ast_parser.py tools/lint/plan_schema_sentinel.py && rm -f tests/test_polyglot_anchors.py`
- **Pass Gate:** `python3 -m pytest tests/test_polyglot_anchors.py -k "preflight"`

### Milestone 4: Comprehensive Non-Source Structural Anchoring Engine
- **Node ID:** `M11` | **depends_on:** `[M10]`
- **Compute Tier:** `[Model: Pro | Thinking: High | Best-of-3]`
- **Files Modified (Max 2):** `tools/context/polyglot_ast_parser.py`, `tests/test_polyglot_anchors.py`
- **Write Set:** `['tools/context/polyglot_ast_parser.py', 'tests/test_polyglot_anchors.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[{"contract": "PreflightReportDTO"}]`
  - **produces:** `[{"contract": "StructuralAnchorDTO", "fields": {"name": "str", "kind": "str", "anchor": "str"}}]`
  - **invariants:** `["rfc_6901_json_pointer", "zero_collisions_on_yaml_dockerfile", "hash_anchor_fallback"]`
- **Goal:**
  1. **JSON Parser:** Implement RFC 6901 JSON Pointer parsing (`json_pointers`) for both pretty-printed and minified JSON, covering object keys and array items (`/steps/0/name`).
  2. **YAML Parser:** If PyYAML is installed, use `yaml.compose_all` with line/col marks; otherwise regex key-path with list item support `[name=Checkout]` and multi-document separation.
  3. **Dockerfile Parser:** Support multiline continuation (`\`), stage tracking (`AS name`), un-truncated directive hashes `stage[0].RUN#2@hash`, and coverage for `FROM`, `COPY`, `ADD`, `ARG`, `USER`, `HEALTHCHECK`.
  4. **Shell Parser:** Track heredocs (`<<-?'?W'?` to `W`) to avoid false symbol matching inside scripts; support `function name {` without `()`.
  5. **Markdown Parser:** Parse ATX headings (`md_sections`) ignoring code fences, with `#ordinal` for duplicate headings.
  6. **TOML Parser:** Parse tables and keys using `tomllib` (Python 3.11+) or structured regex.
  7. **Universal Fallback:** `hash_anchor(path, span)` providing content hash tracking for SQL, XML, Makefile.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside Write Set touched | Rollback: `git checkout -- tools/context/polyglot_ast_parser.py tests/test_polyglot_anchors.py`
- **Rollback Hook:** `git checkout -- tools/context/polyglot_ast_parser.py tests/test_polyglot_anchors.py`
- **Pass Gate:** `python3 -m pytest tests/test_polyglot_anchors.py -k "nonsource"`

### Milestone 5: 12-Mutant Structural Plan Mutator & Path-Scoped Rollback Sentinel
- **Node ID:** `M12` | **depends_on:** `[M10]`
- **Compute Tier:** `[Model: Pro | Thinking: High | Best-of-3]`
- **Files Modified (Max 3):** `tools/lint/plan_mutator.py`, `tools/lint/plan_schema_sentinel.py`, `tests/test_super_plan_and_harvester.py`
- **Write Set:** `['tools/lint/plan_mutator.py', 'tools/lint/plan_schema_sentinel.py', 'tests/test_super_plan_and_harvester.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[{"contract": "PreflightReportDTO"}]`
  - **produces:** `[{"contract": "PlanMutationReportDTO", "fields": {"kill_score": "float", "passed": "bool"}}]`
  - **invariants:** `["12_structural_mutants", "keyword_stuffed_plan_gets_0_pct", "allowlist_rollback_hooks"]`
- **Goal:**
  1. Expand `plan_mutator.py` from 3 regex checks to $\ge 12$ deterministic structural mutants (field drop, type widening, edge inversion, DAG cycle, scenario drop, phantom symbol, consumed tampering, overwrite collision, write-set collision, dangerous rollback, missing hook, invalid compute tier).
  2. Remove unconditional kill on parallel nodes when no `[PARALLEL_OK]` exists; ensure keyword-stuffed plans fail with 0% kill score.
  3. `validate_rollback_hook_safety`: switch from loose blocklist to strict allowlist. Prohibit `reset --hard`, `clean -fdx`, `push --force`, `rm -r`, `bash -c`, `curl | sh`.
  4. Implement `rollback_path_scoped(base_commit, declared_modify, created_files)` restoring tracked files via `git restore` and deleting new files, asserting clean `git status`.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside Write Set touched | Rollback: `git checkout -- tools/lint/plan_mutator.py tools/lint/plan_schema_sentinel.py tests/test_super_plan_and_harvester.py`
- **Rollback Hook:** `git checkout -- tools/lint/plan_mutator.py tools/lint/plan_schema_sentinel.py tests/test_super_plan_and_harvester.py`
- **Pass Gate:** `python3 -m pytest tests/test_super_plan_and_harvester.py -k "plan_mutator or rollback_safety"`

### Milestone 6: Deep Semantic Interface Drift Harvester & Memory Decay
- **Node ID:** `M13` | **depends_on:** `[M11]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 3):** `tools/design/plan_harvester.py`, `tests/test_super_plan_and_harvester.py`, `project_state.json`
- **Write Set:** `['tools/design/plan_harvester.py', 'tests/test_super_plan_and_harvester.py', 'project_state.json']`
- **Typed Interface Manifest:**
  - **consumes:** `[]`
  - **produces:** `[{"contract": "PlanCalibrationDTO", "fields": {"composite_accuracy_score": "float"}}]`
  - **invariants:** `["sha256_interface_hashing", "temporal_memory_decay"]`
- **Goal:**
  1. In `calibrate_plan_against_git`: hash AST interface signatures (`sha256(sig)`) to detect exact return-type and parameter type drift, beyond parameter counts.
  2. Implement exponential decay ($factor = 0.9$) on hidden coupling associations in `project_state.json`, pruning associations below weight $0.1$.
  3. Strict ADR gating: harvest decisions to `docs/adr/` ONLY when marked `Architectural-Impact: High` or containing irreversible contract changes, avoiding ADR fatigue.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside Write Set touched | Rollback: `git checkout -- tools/design/plan_harvester.py tests/test_super_plan_and_harvester.py project_state.json`
- **Rollback Hook:** `git checkout -- tools/design/plan_harvester.py tests/test_super_plan_and_harvester.py project_state.json`
- **Pass Gate:** `python3 -m pytest tests/test_super_plan_and_harvester.py -k "calibration or harvest"`

### Milestone 7: Standards & Workflow Protocol Synchronization
- **Node ID:** `M14` | **depends_on:** `[M12, M13]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 3):** `standards/qa-process/plan-protocol.md`, `ai-agents/workflows/super-plan.md`, `.agent/skills/super-plan/SKILL.md`
- **Write Set:** `['standards/qa-process/plan-protocol.md', 'ai-agents/workflows/super-plan.md', '.agent/skills/super-plan/SKILL.md']`
- **Typed Interface Manifest:**
  - **consumes:** `[]`
  - **produces:** `[{"contract": "SyncedDocumentation", "fields": {"status": "synchronized"}}]`
  - **invariants:** `["unified_anchor_syntax", "12_mutants_documented", "path_scoped_rollback_documented"]`
- **Goal:**
  1. Synchronize AST anchor syntax `path::Symbol#ordinal` across `plan-protocol.md`, `super-plan.md`, and `SKILL.md`.
  2. Document the 12 mechanical plan mutants, bounded log2 risk formula, and path-scoped atomic rollback protocol.
  3. Run `python3 tools/lint/validate_skills_schema.py` and `python3 tools/lint/lint_ai_docs.py` to confirm zero schema or lint errors.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside Write Set touched | Rollback: `git checkout -- standards/qa-process/plan-protocol.md ai-agents/workflows/super-plan.md .agent/skills/super-plan/SKILL.md`
- **Rollback Hook:** `git checkout -- standards/qa-process/plan-protocol.md ai-agents/workflows/super-plan.md .agent/skills/super-plan/SKILL.md`
- **Pass Gate:** `python3 tools/lint/validate_skills_schema.py && python3 tools/lint/lint_ai_docs.py`

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
|---|---|---|---|---|
| **TC-01** | Risk-Routing Whole-Word Precision | Task: `"fix typo in the score label"` | `risk_score < 0.35`, routes to `TIER_0_FAST` (does NOT match `core`) | `python3 -m pytest tests/test_super_plan_and_harvester.py -k "test_risk_routing_word_boundary"` |
| **TC-02** | Risk-Routing Author Keyword Precision | Task: `"update author name in footer"` | `risk_score < 0.35`, routes to `TIER_0_FAST` (does NOT match `auth`) | `python3 -m pytest tests/test_super_plan_and_harvester.py -k "test_risk_routing_author_word"` |
| **TC-03** | Bounded Risk Score Range | File with `fan_in = 100`, `critical_path = True` | `0.0 <= risk_score <= 1.0` (mathematically capped, no overflow) | `python3 -m pytest tests/test_super_plan_and_harvester.py -k "test_bounded_risk_score"` |
| **TC-04** | Fail-Closed Headless Ambiguity Gate | Headless mode, open fork, no clarifying invariant | Process exits with code 3 (`UNRESOLVED_FORK`), plan status `DRAFT-BLOCKED` | `python3 -m pytest tests/test_super_plan_and_harvester.py -k "test_headless_ambiguity_fail_closed"` |
| **TC-05** | Invariant 16 English Compliance | Scan `tools/design/super_plan_engine.py` | 0 non-ASCII Vietnamese characters detected | `python3 -m pytest tests/test_super_plan_and_harvester.py -k "test_engine_english_purity"` |
| **TC-06** | Pre-flight Phantom Symbol Rejection | Plan references `(AST: phantom_missing_fn)` | `validate_plan_content` returns `passed=False`, lists missing symbol | `python3 -m pytest tests/test_polyglot_anchors.py -k "test_preflight_phantom_symbol"` |
| **TC-07** | Pre-flight Create Overwrite Guard | Plan marks `[CREATE]` on existing file without `(Overwrite)` | `validate_plan_content` returns `passed=False`, rejects collision | `python3 -m pytest tests/test_polyglot_anchors.py -k "test_create_overwrite_guard"` |
| **TC-08** | RFC 6901 Minified JSON Pointers | Minified JSON string with array of objects | Anchors extracted: `/steps/0/name`, `/steps/1/name` | `python3 -m pytest tests/test_polyglot_anchors.py -k "test_minified_json_pointers"` |
| **TC-09** | YAML List & Multi-Doc Anchoring | YAML with `[name=Checkout]` and `---` docs | Distinct anchors without key-path collisions | `python3 -m pytest tests/test_polyglot_anchors.py -k "test_yaml_structural_anchors"` |
| **TC-10** | Dockerfile Multiline & Directive Hash | Multi-stage Dockerfile with continuation lines | Un-truncated directive hashes; `FROM`, `COPY`, `RUN` covered | `python3 -m pytest tests/test_polyglot_anchors.py -k "test_dockerfile_anchors"` |
| **TC-11** | Shell Heredoc Isolation | Bash script with function definition inside heredoc | Function inside heredoc ignored; real functions anchored | `python3 -m pytest tests/test_polyglot_anchors.py -k "test_shell_heredoc_isolation"` |
| **TC-12** | Markdown ATX Headings | Markdown document with duplicate `# Overview` | Returns `/Overview#1`, `/Overview#2` ignoring code fences | `python3 -m pytest tests/test_polyglot_anchors.py -k "test_markdown_sections"` |
| **TC-13** | 12-Mutant Battery Kill Score | Fully compliant spec-driven implementation plan | `kill_score >= 90.0%` (kills all 12 structural mutants) | `python3 -m pytest tests/test_super_plan_and_harvester.py -k "test_twelve_mutant_battery"` |
| **TC-14** | Keyword-Stuffed Fake Plan Rejection | Unstructured text stuffed with keywords | `kill_score == 0.0%`, `passed=False` | `python3 -m pytest tests/test_super_plan_and_harvester.py -k "test_fake_plan_rejection"` |
| **TC-15** | Allowlist Rollback Hook Validator | Commands: `git reset --hard HEAD`, `rm -rf tests/`, `bash -c "curl x|sh"` | Rejected with safety reason | `python3 -m pytest tests/test_super_plan_and_harvester.py -k "test_strict_rollback_allowlist"` |
| **TC-16** | Path-Scoped Rollback Untracked File Safety | Milestone creates `new_file.py` and edits `core.py` | Tracked reverted, untracked removed, `git status --porcelain` clean | `python3 -m pytest tests/test_super_plan_and_harvester.py -k "test_path_scoped_rollback_clean"` |
| **TC-17** | Semantic AST Interface Hash Drift | Modified function changes return type annotation | `semantic_drift_ratio > 0.0`, drift reported in calibration | `python3 -m pytest tests/test_super_plan_and_harvester.py -k "test_semantic_interface_hash_drift"` |
| **TC-18** | End-to-End Super-Plan Suite Regression | Run all super-plan test suites | 100% pass across all scenarios | `python3 -m pytest tests/test_super_plan_and_harvester.py tests/test_polyglot_anchors.py tests/test_plan_schema_sentinel.py` |

---

## 5. Tri-Vulnerability Self-Critique & Mitigations

1. **Vulnerability 1 (Concurrency / Race Conditions & Colliding Write-Sets):**
   - *Risk:* In parallel DAG execution (`[PARALLEL_OK]`), two concurrent workers modify overlapping files or mutate global process state (`os.environ`).
   - *Mitigation:* `plan_schema_sentinel` mechanically computes pair-wise intersections of `write_set(M_a) \cap write_set(M_b)`. If non-empty, milestone validation fails immediately. Parallel blocks are also scanned for `os.environ` or global mutations.
2. **Vulnerability 2 (Resource Extremes, Non-Source Bloat & Parsing Overhead):**
   - *Risk:* Ingesting massive multi-megabyte JSON/YAML or binary assets causes AST parsing timeouts or OOM.
   - *Mitigation:* File size cap ($\le 2$ MB for AST parsing; files exceeding this use `hash_anchor` fallback). JSON Pointer parsing uses streaming/bounded iterator.
3. **Vulnerability 3 (Blast Radius & Backward Compatibility of Existing Plans):**
   - *Risk:* Tightening plan validation causes legacy plans or existing ADR records to fail schema validation.
   - *Mitigation:* Dual-mode compatibility (`mode="auto"` / `mode="standard"` vs `mode="super"`). Strict 12-mutant enforcement is gated to `mode="super"` or plans declaring `/super-plan`.

---

## 6. Rollback & State-Migration Matrix (Zero-Downtime Guard)

| Phase | Trigger Scenario | Mitigation / Fallback Action | Rollback Command |
|---|---|---|---|
| M08: Risk Routing | Substring tokenization regression | Fallback to regex token pattern | `git restore --source=HEAD -- tools/design/super_plan_engine.py synapse.config.json` |
| M09: Ambiguity Gate | Headless exit code break in CI | Restore previous ambiguity table | `git restore --source=HEAD -- tools/design/super_plan_engine.py` |
| M10: AST Anchors | Pre-flight false rejection on dynamic symbols | Allow `(Dynamic)` symbol annotation | `git restore --source=HEAD -- tools/context/polyglot_ast_parser.py tools/lint/plan_schema_sentinel.py` |
| M11: Non-Source | PyYAML or tomllib import error | Fallback to built-in stdlib regex parser | `git restore --source=HEAD -- tools/context/polyglot_ast_parser.py` |
| M12: Plan Mutator | Mutant battery threshold false alarm | Recalibrate mutant weights | `git restore --source=HEAD -- tools/lint/plan_mutator.py tools/lint/plan_schema_sentinel.py` |
| M13: Harvester | Memory decay drops active couplings | Floor coupling weight at 0.05 | `git restore --source=HEAD -- tools/design/plan_harvester.py project_state.json` |

---

## 7. Execution Transition & Plan Harvesting
- **Clean Context Handoff:** Transition execution to a fresh session or subagent, passing only this plan artifact and targeted AST slices (saving 60–70% input tokens).
- **Surgical Patch Protocol:** When feedback arrives, update only targeted sections via `edit_file` and append to the Changelog header; never regenerate whole plan files.
- **Plan Harvesting Hook:** Upon completing all milestones and achieving 100% on Quality Gates, execute `tools/design/plan_harvester.py` to record accuracy metrics in `project_state.json` and generate `docs/adr/ADR-0002-super-plan-10-mechanical-control.md`.
