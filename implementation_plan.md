<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Implementation Plan: Synapse-Hub 10/10 Audit Remediation & Tri-State Quality Gate Overhaul

> **Changelog (v1 -> v2):**
> - Replaced prior P0–P2 draft with full 7-domain 10/10 Audit Remediation Blueprint anchored to empirical findings in `synapse_hub_audit.md`.
> - Locked Stage 2 Ambiguity Gate Rulings (Tri-State Quality Gates with zero synthetic masquerade, 57-skill preservation with anti-boilerplate & trigger precision, and sequential `/solo` execution).
> - Added single-source SLA profiles with baseline regression delta gating, `shlex` AST-style `pre_bash_guard` hardening (16/16 vectors), agent-neutral `testing/manual/manual_testing_rules.md`, and `solo_runner.py` modularization.

> **Super-Plan Metadata:** `Tier 2 (DEEP_SUPER_PLAN)` | `RiskScore = 0.91` (`CrossBoundary = True`, `HardCritical = True`, `FanCap = 32`)
> **Execution Mode:** Sequential Single-Agent `/solo` (`M1` -> `M11`, strictly `0` `swarm` workers or parallel subagents)
> **Governing Rulings (Locked at Stage 2 Ambiguity Gate):**
> - `Ruling 1 (Tri-State Honest Quality Gates):` Introduce `PASS / HEURISTIC_PASS / SKIPPED / FAIL` semantics across `verify_all.py` and `GateResult` — disable synthetic `LOCAL_CPU_JSON_SERIALIZE` masquerading in `gate_10_perf_sla.py` (`SKIPPED_NO_LOAD_ARTIFACT` in Hub mode, fail-closed in Client mode and on `jtl_analyzer` import errors), emit `[PARTIAL PASS - FAST TIER]` without cryptographic DoD receipts on `--tier fast`, separate Gate 11's 6 simulation tiers as `[INFO / SIMULATION]`, and remove bogus UI gate claims — cost if wrong: requires updating legacy gate test assertions (~2 test files).
> - `Ruling 2 (57-Skill Contract + Zero Boilerplate + Agent-Neutral Manual Rules):` Preserve all 57 skill IDs for 100% compatibility with wheel packaging and 6 test suites, sort `skills_index.json` by domain without `".."` truncation, fix misassigned `stack_triggers`, replace 44/57 copy-pasted Handoff lines with domain-specific deliverables enforced by `validate_skills_schema.py`, and add canonical `testing/manual/manual_testing_rules.md` — cost if wrong: maintains 57 skill folders on disk rather than shrinking directory count.
> - `Ruling 3 (Defense-in-Depth Guard, Single-Source SLA/Rules & Modularity):` Upgrade `pre_bash_guard.py` via `shlex` tokenization and recursive shell-wrapper unwrapping to block all 16 bypass vectors, unify pentest allowlists in `pentest_scope_guard.py`, establish `synapse.config.json::performance.sla_profiles` as single source of truth, and extract `solo_contracts.py` from `solo_runner.py` — cost if wrong: slightly higher upfront refactor scope across 11 sequential milestones.

### Stage 2 Orthogonal Architectural Tournament (Trade-Off Matrix)

| Dimension | Branch A: Minimalist Patch | Branch B (Selected): Clean Tri-State & Single-Source Architecture | Branch C: Strict Hard-Fail & Physical Skill Merge |
| :--- | :--- | :--- | :--- |
| **Quality Gate Truthfulness** | Rename print strings only | Tri-State DTO (`PASS`/`HEURISTIC_PASS`/`SKIPPED`/`FAIL`), zero synthetic JTL masquerade, fail-closed imports, fast-tier partial guard | Hard-fail Gate 10 in Hub CI unless live HTTP server spins up on every commit |
| **Skill & Rule Governance** | Manual one-off edits | Dynamic `AGENTS.md` sync enforced in Gate 4 + sorted 57-skill index + mechanical anti-boilerplate lint + `manual_testing_rules.md` | Delete ~15 skill folders (breaks 6 test suites, wheel checks, and client configs) |
| **Security Guard** | Add 5 more regexes | `shlex` tokenizer + flag normalization + recursive `bash -c` unwrap + pipe exfil detector | OS container mandatory wrapper (breaks zero-dep Windows/macOS CLI portability) |
| **Audit Target Score** | ~7.8 / 10 | **10.0 / 10 across all 7 categories** | ~8.5 / 10 (high regression blast radius) |

---

## 1. Affected Files & Blast Radius

| Action | Target File & AST Structural Anchor | Line Range | Change Purpose & Blast Radius |
| :---: | :--- | :---: | :--- |
| `[MODIFY]` | `tools/core/gates/base.py` (AST: GateResult) | `L88-L142` | Add Tri-State status constants (`PASS`, `HEURISTIC_PASS`, `SKIPPED_NO_LOAD_ARTIFACT`, `SKIPPED_BY_CONFIG`, `FAIL`) and `verification_tier` metadata on `GateResult`. |
| `[MODIFY]` | `tools/core/verify_all.py` (AST: run_all_gates_detailed) | `L260-L372` | Report `heuristic` and `skipped` counts accurately; emit `[PARTIAL PASS - FAST TIER: Regression Suite Not Run]` and withhold DoD receipts when `fast=True`. |
| `[MODIFY]` | `tools/core/gates/gate_09_collisions.py` (AST: gate_9_skill_collision) | `L60-L102` | Only run `mechanical_ui_gate.py` when frontend UI sources exist; validate `skills_index.json` domain sorting, non-truncated summaries, and trigger hygiene. |
| `[MODIFY]` | `tools/core/gates/gate_10_perf_sla.py` (AST: gate_10_performance_sla) | `L54-L282` | Default `auto_benchmark_fallback=False`; reject synthetic `local://benchmark` JTLs; return `SKIPPED_NO_LOAD_ARTIFACT` in HUB mode without real artifacts; fail-closed on `jtl_analyzer` import error; add baseline P95 regression delta check. |
| `[MODIFY]` | `tools/core/gates/gate_08_mutation.py` (AST: gate_8_micro_mutator) | `L220-L310` | Record `status="HEURISTIC_PASS"` in static AST mode vs `PASS` in dynamic execution mode with explicit banner distinction. |
| `[MODIFY]` | `tools/core/gates/gate_11_token_reduction.py` (AST: gate_11_token_reduction) | `L275-L470` | Gate `passed` strictly on 9 `PRODUCTION_ACTIVE_TIERS` and label 6 `RESEARCH_SIMULATION_TIERS` as `[INFO / SIMULATION]` rather than `"VERIFIED"`. |
| `[MODIFY]` | `synapse.config.json` (L1-L85) | `L1-L85` | Set `auto_benchmark_fallback: false`; define canonical `performance.sla_profiles` (`smoke`, `read_api`, `search_api`, `write_checkout`, `web_cwv_slow4g`) and `max_p95_regression_pct: 15.0`. |
| `[MODIFY]` | `testing/performance/performance_testing_rules.md` (L15-L82) | `L15-L82` | Align all SLA tiers to `synapse.config.json::performance.sla_profiles` and codify Baseline Regression Delta gating (`<= 15%` P95 drift). |
| `[MODIFY]` | `skills/04-performance-and-load/backend-load-and-stress-patterns/SKILL.md` (L40-L157) | `L40-L157` | Align Archetype SLA table to `synapse.config.json::performance.sla_profiles` and set performance-specific Handoff deliverables. |
| `[MODIFY]` | `tools/lint/pre_bash_guard.py` (AST: validate_shell_command) | `L43-L165` | Replace naive regex checks with `shlex` tokenization, flag normalization, recursive `bash -c`/`sh -c`/`eval` unwrapping, pipe exfil & `curl|sh` blocking, position-independent `git push --force`, and `pip`/`uv`/`poetry` Rule 9 guards. |
| `[MODIFY]` | `tools/security/pentest_scope_guard.py` (AST: PentestScopeGuard) | `L320-L520` | Load canonical `synapse.config.json::security.allowed_pentest_hosts` as fallback/ceiling and prevent env vars from smuggling production domains. |
| `[MODIFY]` | `skills/05-security-and-compliance/security-dast-sentinel/SKILL.md` (L85-L179) | `L85-L179` | Remove phantom `SYNAPSE_ALLOW_PROD_FUZZ=1` bypass claim, align OWASP Top 10 DoD scope honestly, and tailor security Handoff format. |
| `[MODIFY]` | `AGENTS.md` (L1-L101) | `L1-L101` | Replace stale hardcoded tool/test counts with canonical registry paths, refine KV-cache engineering description, and add risk-proportionality for Invariants 15 & 17. |
| `[MODIFY]` | `tools/core/sync_agent_rules.py` (AST: sync_all) | `L245-L792` | Propagate updated `AGENTS.md` sections cleanly across all IDE bridge templates without hardcoded count drift. |
| `[MODIFY]` | `tools/lint/lint_ai_docs.py` (AST: lint_docs) | `L224-L450` | Enforce `sync_agent_rules.sync_all(check_only=True)` bridge parity inside Gate 4 and verify all `tools/.../*.py` paths across `skills/` and `examples/`. |
| `[CREATE]` | `testing/manual/manual_testing_rules.md` (New) | `L1-L95` | Create agent-neutral Manual QA specification standard (12/13-column ISO 29119-3, mandatory `@REQ-xxx`/`REQ ID` RTM, QUICK-mode exit criteria, edge cases). |
| `[MODIFY]` | `tools/lint/manual_tc_linter.py` (AST: STANDARD_12_COLUMNS) | `L38-L520` | Add `check_quick_exit_criteria` (Happy + Negative + Boundary + RTM `@REQ-xxx` verification) in strict semantic mode. |
| `[MODIFY]` | `tools/core/rules_router.py` (AST: prune_payload_to_cap) | `L124-L240` | Register `manual_testing_rules.md` in `STACK_RULE_MAPPINGS["manual"]` and `TASK_TYPE_CONFIGS["manual"]` for universal agent routing. |
| `[MODIFY]` | `skills/02-test-design/rbt-manual-testing/SKILL.md` (L1-L275) | `L1-L275` | Anchor to `testing/manual/manual_testing_rules.md`, define explicit QUICK-mode exit criteria, and customize Manual Test Matrix Handoff. |
| `[MODIFY]` | `skills/02-test-design/manual-qa-and-rtm-bridge/SKILL.md` (L1-L206) | `L1-L206` | Deduplicate design-time RTM rules to `manual_testing_rules.md`, focusing on execution, bug triage, CTAL-TAE scoring, and release sign-off. |
| `[MODIFY]` | `skills_index.json` (L1-L61) | `L1-L61` | Sort all 57 skills by domain (`01`..`11`), expand all `".."` truncated summaries, and fix misrouted `stack_triggers`. |
| `[MODIFY]` | `tools/lint/validate_skills_schema.py` (AST: classify_code_blocks) | `L93-L580` | Add mechanical anti-boilerplate Handoff lint (`< 5` identical `Output Format:` across skills) and `skills_index.json` integrity check. |
| `[CREATE]` | `tools/orchestration/solo_contracts.py` (New) | `L1-L360` | Extract `SignedRedReceipt`, HMAC helpers, `MicroContextExtractor`, and `AstTautologyAnalyzer` out of `solo_runner.py` to reduce monolith size. |
| `[MODIFY]` | `tools/orchestration/solo_runner.py` (AST: SignedRedReceipt) | `L75-L565` | Delegate receipt signing, micro-context extraction, and AST tautology checks to `solo_contracts.py` with 100% backward-compatible re-exports. |
| `[MODIFY]` | `benchmarks/CONTEXT_TOKEN_BENCHMARK.md` (L1-L120) | `L1-L120` | Regenerate empirical token benchmark table after rule/skill updates so `test_benchmark_report_drift_sentinel` passes 100%. |
| `[MODIFY]` | `tests/test_verify_all.py` (AST: TestVerifyAllGates) | `L119-L215` | Update Gate 10 HUB-mode empty-dir test to assert `SKIPPED_NO_LOAD_ARTIFACT` without synthetic JTL generation and verify fast-mode partial banner. |
| `[MODIFY]` | `tests/test_hub_perfection_remediation.py` (AST: test_m6_gate_10_hub_vs_client_fail_closed) | `L205-L276` | Align M6 Gate 10 assertions with zero-synthetic-masquerade HUB skip semantics and baseline regression delta checks. |
| `[CREATE]` | `tests/test_audit_10_of_10_excellence.py` (New) | `L1-L340` | Comprehensive 4-scenario battery falsifying all 11 gates, 16 `pre_bash_guard` vectors, SLA profiles, Manual QA exit criteria, and 57-skill routing. |
| `[CREATE]` | `docs/adr/ADR-0022-tri-state-gates-and-hub-10-overhaul.md` (New) | `L1-L90` | Architectural Decision Record documenting Tri-State verification gates, defense-in-depth shell guard, and single-source SLA/rule governance. |

---

## 2. Data Flow & Interface Signatures

```python
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

@dataclass(frozen=True)
class AuditRemediationConfigDTO:
    """Root configuration locking Stage 2 rulings for sequential /solo execution."""
    repo_root: str
    disable_synthetic_perf_fallback: bool
    preserve_57_skills: bool

@dataclass(frozen=True)
class TriStateGateSummaryDTO:
    """Honest verification summary distinguishing full DoD vs partial fast-tier runs."""
    total: int
    passed: int
    heuristic: int
    skipped: int
    failed: int
    verification_completeness: str

@dataclass(frozen=True)
class PerfSlaEvaluationDTO:
    """Gate 10 evaluation receipt with baseline regression delta and skip transparency."""
    status: str
    passed: bool
    p95_ms: float
    regression_delta_pct: float
    reason: str

@dataclass(frozen=True)
class UnifiedSlaProfileDTO:
    """Canonical single-source SLA tier threshold loaded from synapse.config.json."""
    profile_name: str
    p95_ms: float
    p99_ms: float
    max_error_rate_pct: float
    max_p95_regression_pct: float

@dataclass(frozen=True)
class ShellGuardVerdictDTO:
    """Tokenized shell command security verdict covering chained, piped, and nested invocations."""
    allowed: bool
    violation_code: str
    reason: str
    inspected_segments: int

@dataclass(frozen=True)
class RuleSingleSourceParityDTO:
    """ Synchronization and Gate-4 anti-drift verification contract for IDE rule bridges."""
    canonical_source: str
    bridges_verified: int
    in_sync: bool

@dataclass(frozen=True)
class ManualQaExitCriteriaDTO:
    """QUICK and FULL mode coverage exit criteria receipt for ISO 29119-3 test suites."""
    has_happy_path: bool
    has_negative_path: bool
    has_boundary_case: bool
    rtm_coverage_pct: float
    passed: bool

@dataclass(frozen=True)
class SkillCatalogQualityDTO:
    """57-skill catalog hygiene receipt verifying zero boilerplate, sorting, and trigger accuracy."""
    skill_count: int
    truncated_summaries: int
    max_duplicate_handoffs: int
    domain_sorted: bool

@dataclass(frozen=True)
class ModularityHygieneDTO:
    """Hub runtime hygiene receipt tracking solo_runner LOC reduction and benchmark parity."""
    solo_runner_loc: int
    stale_build_purged: bool
    benchmark_in_sync: bool

# Core Signatures (Anti-Full-Code — Signatures Only)
def normalize_and_inspect_shell(command: str, cwd: Optional[str] = None) -> ShellGuardVerdictDTO: ...
def evaluate_baseline_regression(current_p95: float, baseline_p95: float, max_regression_pct: float) -> Tuple[bool, float]: ...
def check_quick_exit_criteria(rows: List[Dict[str, str]], require_rtm: bool = True) -> ManualQaExitCriteriaDTO: ...
def check_handoff_boilerplate_diversity(skill_files: List[str], max_identical: int = 4) -> Tuple[bool, List[str]]: ...
```

---

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Tri-State Gate Engine, Fast-Tier Partial Guard & UI Gate Fix
- **Node ID:** M1-TRISTATE-GATE-CORE
- **depends_on:** []
- **Compute Tier:** [Model: Pro | Thinking: High | Temp: 0.1]
- **Files Modified:** `tools/core/gates/base.py`, `tools/core/verify_all.py`, `tools/core/gates/gate_09_collisions.py`
- **Write Set:** ['tools/core/gates/base.py', 'tools/core/verify_all.py', 'tools/core/gates/gate_09_collisions.py']
- **consumes:** [{'contract': 'AuditRemediationConfigDTO'}]
- **produces:** [{'contract': 'TriStateGateSummaryDTO'}]
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: <= 3 files
- **Rollback Hook:** git restore tools/core/gates/base.py tools/core/verify_all.py tools/core/gates/gate_09_collisions.py

### Milestone 2: Gate 10 Zero-Masquerade & Fail-Closed Import + Gate 8/11 Honesty
- **Node ID:** M2-GATES-8-10-11-HONESTY
- **depends_on:** ['M1-TRISTATE-GATE-CORE']
- **Compute Tier:** [Model: Pro | Thinking: High | Temp: 0.1]
- **Files Modified:** `tools/core/gates/gate_10_perf_sla.py`, `tools/core/gates/gate_08_mutation.py`, `tools/core/gates/gate_11_token_reduction.py`
- **Write Set:** ['tools/core/gates/gate_10_perf_sla.py', 'tools/core/gates/gate_08_mutation.py', 'tools/core/gates/gate_11_token_reduction.py']
- **consumes:** [{'contract': 'TriStateGateSummaryDTO'}]
- **produces:** [{'contract': 'PerfSlaEvaluationDTO'}]
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: <= 3 files
- **Rollback Hook:** git restore tools/core/gates/gate_10_perf_sla.py tools/core/gates/gate_08_mutation.py tools/core/gates/gate_11_token_reduction.py

### Milestone 3: Single-Source Performance SLA Profiles & Baseline Regression Delta
- **Node ID:** M3-PERF-SLA-SINGLE-SOURCE
- **depends_on:** ['M2-GATES-8-10-11-HONESTY']
- **Compute Tier:** [Model: Pro | Thinking: High | Temp: 0.1]
- **Files Modified:** `synapse.config.json`, `testing/performance/performance_testing_rules.md`, `skills/04-performance-and-load/backend-load-and-stress-patterns/SKILL.md`
- **Write Set:** ['synapse.config.json', 'testing/performance/performance_testing_rules.md', 'skills/04-performance-and-load/backend-load-and-stress-patterns/SKILL.md']
- **consumes:** [{'contract': 'PerfSlaEvaluationDTO'}]
- **produces:** [{'contract': 'UnifiedSlaProfileDTO'}]
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: <= 3 files
- **Rollback Hook:** git restore synapse.config.json testing/performance/performance_testing_rules.md skills/04-performance-and-load/backend-load-and-stress-patterns/SKILL.md

### Milestone 4: Tokenized Pre-Bash Security Guard (16/16 Vectors) & Pentest Scope Unification
- **Node ID:** M4-SECURITY-GUARD-HARDENING
- **depends_on:** ['M3-PERF-SLA-SINGLE-SOURCE']
- **Compute Tier:** [Model: Pro | Thinking: High | Temp: 0.1]
- **Files Modified:** `tools/lint/pre_bash_guard.py`, `tools/security/pentest_scope_guard.py`, `skills/05-security-and-compliance/security-dast-sentinel/SKILL.md`
- **Write Set:** ['tools/lint/pre_bash_guard.py', 'tools/security/pentest_scope_guard.py', 'skills/05-security-and-compliance/security-dast-sentinel/SKILL.md']
- **consumes:** [{'contract': 'UnifiedSlaProfileDTO'}]
- **produces:** [{'contract': 'ShellGuardVerdictDTO'}]
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: <= 3 files
- **Rollback Hook:** git restore tools/lint/pre_bash_guard.py tools/security/pentest_scope_guard.py skills/05-security-and-compliance/security-dast-sentinel/SKILL.md

### Milestone 5: Single-Source AGENTS.md Calibration & Gate-4 Bridge Drift Enforcement
- **Node ID:** M5-RULES-SINGLE-SOURCE
- **depends_on:** ['M4-SECURITY-GUARD-HARDENING']
- **Compute Tier:** [Model: Pro | Thinking: High | Temp: 0.1]
- **Files Modified:** `AGENTS.md`, `tools/core/sync_agent_rules.py`, `tools/lint/lint_ai_docs.py`
- **Write Set:** ['AGENTS.md', 'tools/core/sync_agent_rules.py', 'tools/lint/lint_ai_docs.py']
- **consumes:** [{'contract': 'ShellGuardVerdictDTO'}]
- **produces:** [{'contract': 'RuleSingleSourceParityDTO'}]
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: <= 3 files
- **Rollback Hook:** git restore AGENTS.md tools/core/sync_agent_rules.py tools/lint/lint_ai_docs.py

### Milestone 6: Agent-Neutral Manual QA Rules, Mandatory RTM & QUICK Exit Criteria
- **Node ID:** M6-MANUAL-QA-EXCELLENCE
- **depends_on:** ['M5-RULES-SINGLE-SOURCE']
- **Compute Tier:** [Model: Pro | Thinking: High | Temp: 0.1]
- **Files Modified:** `testing/manual/manual_testing_rules.md`, `tools/lint/manual_tc_linter.py`, `tools/core/rules_router.py`
- **Write Set:** ['testing/manual/manual_testing_rules.md', 'tools/lint/manual_tc_linter.py', 'tools/core/rules_router.py']
- **consumes:** [{'contract': 'RuleSingleSourceParityDTO'}]
- **produces:** [{'contract': 'ManualQaExitCriteriaDTO'}]
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: <= 3 files
- **Rollback Hook:** git restore tools/lint/manual_tc_linter.py tools/core/rules_router.py && rm -f testing/manual/manual_testing_rules.md

### Milestone 7: Manual QA Skill Deduplication & Broken Skill Example References
- **Node ID:** M7-MANUAL-SKILLS-AND-REFS
- **depends_on:** ['M6-MANUAL-QA-EXCELLENCE']
- **Compute Tier:** [Model: Flash | Thinking: Off | Temp: 0.1]
- **Files Modified:** `skills/02-test-design/rbt-manual-testing/SKILL.md`, `skills/02-test-design/manual-qa-and-rtm-bridge/SKILL.md`, `skills/01-web-automation/bats-testing-patterns/examples/cli_runner_test.bats`
- **Write Set:** ['skills/02-test-design/rbt-manual-testing/SKILL.md', 'skills/02-test-design/manual-qa-and-rtm-bridge/SKILL.md', 'skills/01-web-automation/bats-testing-patterns/examples/cli_runner_test.bats']
- **consumes:** [{'contract': 'ManualQaExitCriteriaDTO'}]
- **produces:** [{'contract': 'ManualQaExitCriteriaDTO'}]
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: <= 3 files
- **Rollback Hook:** git restore skills/02-test-design/rbt-manual-testing/SKILL.md skills/02-test-design/manual-qa-and-rtm-bridge/SKILL.md skills/01-web-automation/bats-testing-patterns/examples/cli_runner_test.bats

### Milestone 8: 57-Skill Index Sorting, Trigger Overhaul & Anti-Boilerplate Schema Gate
- **Node ID:** M8-SKILLS-CATALOG-AND-BOILERPLATE
- **depends_on:** ['M7-MANUAL-SKILLS-AND-REFS']
- **Compute Tier:** [Model: Pro | Thinking: High | Temp: 0.1]
- **Files Modified:** `skills_index.json`, `tools/lint/validate_skills_schema.py`, `skills/02-test-design/gherkin-to-suite/examples/suite_report_sample.json`
- **Write Set:** ['skills_index.json', 'tools/lint/validate_skills_schema.py', 'skills/02-test-design/gherkin-to-suite/examples/suite_report_sample.json']
- **consumes:** [{'contract': 'ManualQaExitCriteriaDTO'}]
- **produces:** [{'contract': 'SkillCatalogQualityDTO'}]
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: <= 3 files
- **Rollback Hook:** git restore skills_index.json tools/lint/validate_skills_schema.py skills/02-test-design/gherkin-to-suite/examples/suite_report_sample.json

### Milestone 9: Hub Runtime Modularity (`solo_contracts.py`) & Benchmark Drift Synchronization
- **Node ID:** M9-HUB-MODULARITY-AND-BENCHMARK
- **depends_on:** ['M8-SKILLS-CATALOG-AND-BOILERPLATE']
- **Compute Tier:** [Model: Pro | Thinking: High | Temp: 0.1]
- **Files Modified:** `tools/orchestration/solo_contracts.py`, `tools/orchestration/solo_runner.py`, `benchmarks/CONTEXT_TOKEN_BENCHMARK.md`
- **Write Set:** ['tools/orchestration/solo_contracts.py', 'tools/orchestration/solo_runner.py', 'benchmarks/CONTEXT_TOKEN_BENCHMARK.md']
- **consumes:** [{'contract': 'SkillCatalogQualityDTO'}]
- **produces:** [{'contract': 'ModularityHygieneDTO'}]
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: <= 3 files
- **Rollback Hook:** git restore tools/orchestration/solo_runner.py benchmarks/CONTEXT_TOKEN_BENCHMARK.md && rm -f tools/orchestration/solo_contracts.py

### Milestone 10: Align Legacy Gate Tests & Author 10/10 Falsification Test Suite
- **Node ID:** M10-VERIFICATION-BATTERY
- **depends_on:** ['M9-HUB-MODULARITY-AND-BENCHMARK']
- **Compute Tier:** [Model: Pro | Thinking: High | Temp: 0.1]
- **Files Modified:** `tests/test_verify_all.py`, `tests/test_hub_perfection_remediation.py`, `tests/test_audit_10_of_10_excellence.py`
- **Write Set:** ['tests/test_verify_all.py', 'tests/test_hub_perfection_remediation.py', 'tests/test_audit_10_of_10_excellence.py']
- **consumes:** [{'contract': 'ModularityHygieneDTO'}]
- **produces:** [{'contract': 'ModularityHygieneDTO'}]
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: <= 3 files
- **Rollback Hook:** git restore tests/test_verify_all.py tests/test_hub_perfection_remediation.py && rm -f tests/test_audit_10_of_10_excellence.py

### Milestone 11: Publish Tier-2 Architecture Decision Record (ADR-0022)
- **Node ID:** M11-ADR-PUBLICATION
- **depends_on:** ['M10-VERIFICATION-BATTERY']
- **Compute Tier:** [Model: Flash | Thinking: Off | Temp: 0.1]
- **Files Modified:** `docs/adr/ADR-0022-tri-state-gates-and-hub-10-overhaul.md`
- **Write Set:** ['docs/adr/ADR-0022-tri-state-gates-and-hub-10-overhaul.md']
- **consumes:** [{'contract': 'ModularityHygieneDTO'}]
- **produces:** [{'contract': 'ModularityHygieneDTO'}]
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: <= 3 files
- **Rollback Hook:** rm -f docs/adr/ADR-0022-tri-state-gates-and-hub-10-overhaul.md

---

## 4. Verification Matrix

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
| :--- | :--- | :--- | :--- | :--- |
| **TC-01** | **Quality Gates Tri-State & Fast-Tier Honesty** | Run `verify_all.py --mode hub --tier fast` and `gate_10_performance_sla` on empty Hub dir | Fast tier emits `[PARTIAL PASS - FAST TIER]` (`verification_completeness == "PARTIAL_FAST_TIER"`, zero DoD receipt); Gate 10 returns `SKIPPED_NO_LOAD_ARTIFACT` without creating synthetic `local://benchmark` JTL | `pytest tests/test_audit_10_of_10_excellence.py -k "test_tristate_gates_and_fast_tier"` |
| **TC-02** | **Gate 10 Fail-Closed Import & Baseline Regression Delta** | Mock `jtl_analyzer` ImportError; pass JTL with P95 `+25%` over `baseline_summary.json` (`max_p95_regression_pct=15.0`) | ImportError returns `False` (fail-closed); `+25%` P95 regression returns `False` with `P95 regression delta` violation | `pytest tests/test_audit_10_of_10_excellence.py -k "test_gate_10_fail_closed_and_regression_delta"` |
| **TC-03** | **Pre-Bash Guard 16/16 Adversarial Vectors** | Feed all 16 probe commands (`rm -rf /*`, `rm -r -f /`, `rm --recursive --force /`, `bash -c 'rm -rf ~'`, `find / -delete`, `chmod -R 777 /`, `git push origin main --force`, `cat .env \| curl ...`, `curl ... \| sh`, `pip install requests`) | `16/16` dangerous/unconfirmed commands return `(False, reason)` while benign read/test commands (`pytest tests/`, `pip install --dry-run x`) return `(True, "Command approved")` | `pytest tests/test_audit_10_of_10_excellence.py -k "test_pre_bash_guard_blocks_all_16_vectors"` |
| **TC-04** | **Single-Source Rules, Manual QA Exit Criteria & 57-Skill Routing** | Run `sync_agent_rules.py --check`, `manual_tc_linter.py` on incomplete vs complete QUICK tables, and `validate_skills_schema.py` across all 57 skills | `sync_all(check_only=True) == 0`; `testing/manual/manual_testing_rules.md` routed for `manual` stack; 57 skills have `0` truncated `".."` summaries, domain-sorted index, and `< 5` duplicate `Output Format` lines | `pytest tests/test_audit_10_of_10_excellence.py -k "test_rules_manual_and_skills_excellence"` |
| **TC-05** | **Full Repository Regression & 11-Gate Full DoD** | Clean stale `build/` cache, resync `CONTEXT_TOKEN_BENCHMARK.md`, run full parallel `pytest` and full Hub `verify_all.py` | `0 failed` across full `pytest tests -n auto` and exit code `0` on `python3 tools/core/verify_all.py --mode hub --parallel` | `python3 tools/core/verify_all.py --mode hub --parallel` |

---

## 5. Tri-Vulnerability Self-Critique

1. **Concurrency & Race Condition Mitigation:** Parallel gate execution (`verify_all.py --parallel`) uses `ThreadLocalStdoutProxy` and `_METRICS_LOCK` (`set_gate_metric`); disabling Gate 10's on-the-fly synthetic `perf_results.jtl` disk write eliminates file-write race conditions when concurrent test workers (`pytest -n auto`) inspect `reports/perf/` simultaneously, making Gate 10 strictly idempotent and read-only.
2. **Boundary & Extreme Resource Handling:** `pre_bash_guard.py` handles malformed/unbalanced quotes in `shlex.split` by failing closed (`False`) on syntax obfuscation or bounding recursive `bash -c` unwrapping depth (`max_depth=4`) to prevent stack overflow on deeply nested adversarial strings; `gate_10_perf_sla.py` guards against division-by-zero when `baseline_p95 <= 0` and rejects empty/corrupt JTL files cleanly.
3. **Backward Compatibility & Caller Blast Radius:** All 57 skill IDs, directory paths, and `GateResult` boolean return signatures (`gate_fn(...) -> bool`) remain 100% backward-compatible for existing callers; `solo_runner.py` re-exports every symbol moved to `solo_contracts.py` (`SignedRedReceipt`, `MicroContextExtractor`, `AstTautologyAnalyzer`, `compute_red_receipt_hmac`) so downstream test suites and CLI scripts experience zero import breakage.

---

## 6. Recommended Execution Model & Thinking Level

- **Primary Executor Model & Thinking Level (Single-Session `/solo` Default):** `Gemini 4 Carbon (High)` (or `Gemini 4 Neon (High)`).
- **Milestone Escalation Overrides (Optional / `/teamwork` Only):** `/solo` executes `M1` through `M11` sequentially in one session on the Primary Executor; under explicit `/teamwork`, boilerplate/doc sync nodes (`M7`, `M11`) can step down to `Gemini 4 Hydrogen (Medium)`.
- **Rationale:** Modifying security shell parsers (`shlex` wrapper unwrapping), Tri-State quality gate semantics, and cross-repo invariant synchronization carries high regression sensitivity (`RiskScore = 0.91`), justifying High reasoning depth to achieve zero-defect 10/10 verification on the first pass.
