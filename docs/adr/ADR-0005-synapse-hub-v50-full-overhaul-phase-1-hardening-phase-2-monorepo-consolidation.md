<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0005: Synapse Hub v5.0 Full Overhaul (Phase 1 Hardening + Phase 2 Monorepo Consolidation)

- **Status:** Accepted (DoD Certified)
- **Date:** 2026-11-24
- **Source Plan:** `implementation_plan.md`
- **Deciders:** Synapse Hub Autonomous Agent Core & Engineering Team

---

## Context & Problem Statement
### Target Files & Structural Anchors

| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
| `[MODIFY]` | `tools/reasoning/formal_contract_verifier.py` (AST: FormalContractVerifier) | Replace `eval()` and `exec()` with deterministic safe `ast.NodeVisitor` predicate and pure AST symbolic boundary evaluator |
| `[MODIFY]` | `bin/agent-qa.js` (AST: main) | Remove `--py` arbitrary flag bypass and enforce strict subcommand allowlist before spawning Python |
| `[MODIFY]` | `package.json` (AST: version) | Rewire internal npm scripts (`test`, `precommit`, `bump`, `release`) from `--py` to direct `python3` / authorized subcommands |
| `[MODIFY]` | `tools/core/sync_agent_rules.py` (AST: generate_claude_md) | Split `CLIENT_INVARIANTS_MD` vs `HUB_INVARIANTS_MD` so client bridges contain zero Hub `tools/` paths and scope MIT attribution strictly to Synapse Hub files |
| `[MODIFY]` | `tools/core/setup_project.py` (AST: ensure_synapse_config) | Standardize generated client config to `synapse.config.json`, gate `~/.gemini` global injection behind explicit `--global` flag, and fix skill sync source path |
| `[MODIFY]` | `tools/lint/infer_linter.py` (AST: strip_comments_and_strings) | Make comment/string lexer language-aware: support JS/TS backtick template literals and disable `#` line-comment stripping on `.ts`/`.js`/`.java`/`.groovy` |
| `[MODIFY]` | `tools/core/verify_all.py` (AST: run_all_gates) | Eliminate thread-unsafe `sys.stdout` monkey-patching inside `ThreadPoolExecutor` and standardize lowercase `reports/` directory |
| `[MODIFY]` | `tools/core/gates/base.py` (AST: BaseGate) | Pass explicit stream/buffer context into `GateResult` execution to support lock-free `--parallel` static gate runs |
| `[MODIFY]` | `tools/lint/micro_mutator.py` (AST: resolve_scoped_test_cmd) | Execute dynamic mutants inside `tempfile.TemporaryDirectory` shadow workspace, fix JS/TS backtick quote/comment scanner, and remove hardcoded `HAS_`/`fmt_`/`logger` score gaming |
| `[MODIFY]` | `tools/core/sync_skills_manifest.py` (AST: sync_manifest) | Scan unified `skills/<domain>/<skill-id>/SKILL.md` tree (with legacy path fallback during migration), embed physical `"path"` in `skills_index.json`, and raise summary cap to 100 chars |
| `[MODIFY]` | `tools/core/skill_router.py` (AST: evaluate_skill_first_trigger) | Resolve `skill_md_path` directly from `skills_index.json` (0-hop Turn-1 lookup), prioritize explicit `INQUIRY` framing over broad verbs, and rank multi-skill domain matches by `stack_triggers` |
| `[MODIFY]` | `skills_index.json` (AST: skills) | Populate canonical `"path"` and 100-char disambiguated `"summary"` across all 59 consolidated skills |
| `[MODIFY]` | `tools/lint/invariant_checker.py` (AST: check_rule_11_ratchet) | Upgrade Potemkin `os.path.isfile` checks into real mechanical sensors (Rule 7 index-path parity, Rule 16 code/rule scan exemptions, duplicate lockfile guard) |
| `[MODIFY]` | `tools/core/cli.py` (AST: cmd_verify) | Refactor 2,917-LOC manual wrapper monolith into a compact declarative lazy-import `SUBCOMMAND_REGISTRY` separating Core QA commands from Contrib extensions |
| `[MODIFY]` | `tools/__init__.py` (AST: resolve_tool_path) | Register all 20 subpackages cleanly and retire brittle `_TOOL_DOMAIN_MAP` import-hook debt once `pyproject.toml` points directly to `tools.core.cli:main` |
| `[MODIFY]` | `pyproject.toml` (AST: project) | Fix `[project.scripts]` entrypoint to `tools.core.cli:main`, update `package-data` for unified `skills/`, and re-enable core `mypy` checks on `tools/core` & `tools/lint` |
| `[MODIFY]` | `AGENTS.md` (AST: L1-L130) | Update Project Map to unified `skills/`, align Tier-0 exemptions across Invariants 14/15/17, and collapse 14-step ceremony into 2-step `verify --changed` workflow |
| `[MODIFY]` | `tools/design/super_plan_engine.py` (AST: check_ambiguities) | Decouple ambiguity trigger keywords from resolution `keyword_maps` so generic nouns (`database`, `cache`) fail-closed (`exit 3`) in `--auto-recommend` mode unless concrete tech is specified |
| `[DELETE]` | `.skill-lock.json` (AST: file_root) | Purge byte-for-byte duplicate lockfile (retaining canonical `skills_index.json` / `skills_manifest.json`) |
| `[MODIFY]` | `tests/test_formal_contract_verifier.py` (AST: test_verify_valid_contract_holds) | Add RCE exploit regression vectors (`__subclasses__`, top-level side effects, 0-arg & 3-arg contracts) |
| `[MODIFY]` | `tests/test_sync_agent_rules.py` (AST: TestSyncAgentRules) | Assert client bridge templates (`is_template=True`) contain zero `tools/` paths and zero client-code `@TeeVee98` license mandates |
| `[MODIFY]` | `tests/test_infer_linter.py` (AST: TestInferLinter8Cases) | Add Playwright TS backtick `` `#submit-btn` `` unawaited `expect`, apostrophe-in-template, and dangling `expect` test cases |
| `[MODIFY]` | `tests/test_verify_all.py` (AST: TestVerifyAllGates) | Add concurrent 6-thread `run_all_gates(..., parallel=True, output_format="json")` stdout integrity test |
| `[MODIFY]` | `tests/test_micro_mutator.py` (AST: test_syntactic_mutant_generation_operators) | Verify target file `mtime`/inode on working tree remains untouched during dynamic mutation and simulated `TimeoutExpired` |
| `[MODIFY]` | `tests/test_skills_schema.py` (AST: TestSkillsSchema) | Fix vacuous `SKILLS_DIR.glob` loop so all 59 unified skills assert non-empty frontmatter parity |
| `[MODIFY]` | `tests/test_cli_smoke.py` (AST: TestCLISmokeMatrix) | Verify `--py` rejection in `bin/agent-qa.js` and declarative dispatch parity across `tools.core.cli:main` |

### Blast Radius & Downstream Dependencies
- **Direct Callers (`FanIn = 201`):** `bin/agent-qa.js`, GitHub Actions CI workflows (`.github/workflows/*`), `tools/orchestration/solo_runner.py`, and all 236 pytest suites under `tests/`.
- **Backward Compatibility Guarantee:** All Python function names (`evaluate_target`, `run_all_gates`, `FormalContractVerifier.verify_module_contracts`, `evaluate_skill_first_trigger`) keep identical parameter defaults and return dict keys; legacy skill paths are resolved via fallback alias lookup in `resolve_tool_path` / `skill_router.py` if referenced externally.

---

---

## Decision Drivers & Invariants
- Grounding Principle: "Read First – Plan Later" (AGENTS.md §5).
- Zero Fake-Passes Invariant & Deterministic Verification Matrix.
- Execution DAG with Milestone Circuit Breakers & Clean Context Handoff.

---

## Considered Options & Architectural Decision
> **Anti-Full-Code Invariant:** Only typed DTOs, registries, and function contracts are locked below. Implementation bodies belong strictly to execution phases.

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import io


@dataclass(frozen=True)
class SafeAstPredicateResultDTO:
    evaluated: bool
    value: bool
    is_safe: bool
    error_reason: Optional[str] = None


@dataclass(frozen=True)
class ClientBridgeRuleBundleDTO:
    mode: str  # "hub" | "client"
    content: str
    hub_paths_leaked: int
    config_file: str


@dataclass(frozen=True)
class PolyglotLexerTokenStreamDTO:
    language: str
    clean_code: str
    preserved_line_count: int


@dataclass(frozen=True)
class ThreadSafeGateExecutionDTO:
    gate_key: str
    passed: bool
    captured_log: str
    duration_sec: float


@dataclass(frozen=True)
class IsolatedMutationRunDTO:
    target_file: str
    shadow_dir: str
    mutation_score: float
    working_tree_untouched: bool


@dataclass(frozen=True)
class SkillIndexEntryDTO:
    id: str
    domain: str
    path: str
    stack_triggers: List[str]
    summary: str


@dataclass(frozen=True)
class InvariantAuditReportDTO:
    status: str
    rules_checked: int
    violations_count: int


@dataclass(frozen=True)
class DeclarativeCliRouteDTO:
    subcommand: str
    module_path: str
    entrypoint: str
    tier: str  # "core" | "contrib"


@dataclass(frozen=True)
class OverhaulReleaseGateDTO:
    all_gates_passed: bool
    tests_passed: int
    plan_kill_score: float


def evaluate_ast_predicate_safe(predicate: str, context: Dict[str, Any]) -> SafeAstPredicateResultDTO:
    """Evaluates boolean/arithmetic contract expressions strictly via ast.parse whitelist without eval()."""
    ...


def strip_comments_and_strings(
    source_code: str,
    preserve_newlines: bool = True,
    file_ext: str = ".py",
) -> str:
    """Strips comments and string literals (including JS/TS backtick templates) scoped by file extension."""
    ...


def execute_gate_isolated(
    gate_key: str,
    gate_fn: Any,
    repo_root: str,
    mode: str,
    buffer: io.StringIO,
) -> ThreadSafeGateExecutionDTO:
    """Executes a static DoD gate writing exclusively to an isolated StringIO stream without mutating sys.stdout."""
    ...


def evaluate_mutants_in_temp_workspace(
    abs_path: str,
    code: str,
    mutants: List[Dict[str, Any]],
    test_cmd: str,
    timeout: float = 60.0,
) -> Tuple[List[Dict[str, Any]], float]:
    """Runs dynamic mutants inside tempfile.TemporaryDirectory using PYTHONPATH shadow resolution."""
    ...
```

---

---

## Vulnerability Self-Critique & Mitigation Strategies
1. **Vulnerability 1 (Concurrency & Race Condition):**
   - *Vector:* Parallel static gates in `verify_all.py --parallel` previously mutated process-global `sys.stdout` and shared `LAST_GATE_METRICS` dict across 6 threads, while `micro_mutator.py` mutated tracked files in-place where concurrent IDE watchers or test runners caused race conditions.
   - *Mitigation:* Isolate gate logs per thread via thread-local buffers + `threading.Lock()` around `LAST_GATE_METRICS` (`M4`), and execute all dynamic mutations inside an ephemeral `tempfile.TemporaryDirectory` (`M5`) with strictly disjoint `Write Set` declarations across parallel milestones `M1`–`M4`.
2. **Vulnerability 2 (Boundary & Resource Extremes):**
   - *Vector:* Malicious or deeply nested AST expressions in `Requires:` docstrings, 0-parameter / 3+-parameter functions in `FormalContractVerifier`, apostrophes/hashes inside multiline TypeScript backtick strings, or mutant infinite loops timing out after 60s.
   - *Mitigation:* Enforce bounded AST node-count (`<= 64` nodes) and zero `ast.Call` execution in `evaluate_ast_predicate_safe` (`M1`), bounded `timeout` in `subprocess.run` with automatic `TemporaryDirectory` context-manager cleanup (`M5`), and extension-aware state machine lexing (`M3`).
3. **Vulnerability 3 (Backward Compatibility & Blast Radius):**
   - *Vector:* Moving 59 `SKILL.md` files into `skills/` or shrinking `tools/core/cli.py` and `tools/__init__.py` could break hardcoded path references in existing tests, CI workflows, or `pip install -e .` entrypoints (`FanIn = 201`).
   - *Mitigation:* Preserve `_ToolsDomainRedirectFinder` dynamic subpackage lookup across all 20 `tools/` subpackages (`M8`), update `skills_manifest.json` + `skills_index.json` atomically via `sync_skills_manifest.py` (`M6`), and maintain 100% CLI subcommand & function signature parity verified by `test_cli_contracts.py` and `test_cli_schema_sentinel.py`.

---

## 6. Rollback & State-Migration Matrix (Zero-Downtime Guard)

| Phase | Trigger Scenario | Mitigation / Dual-Mode Fallback | Path-Scoped Rollback Command |
|---|---|---|---|
| **Phase 1 (`M1`–`M5`)** | Unit test regression in security, linter, or mutator | Dual-read config (`synapse.config.json` -> `.synapse.json` fallback); default `file_ext=".py"` preserved | `git checkout -- tools/reasoning/formal_contract_verifier.py bin/agent-qa.js package.json tools/core/sync_agent_rules.py tools/core/setup_project.py tools/lint/infer_linter.py tools/core/verify_all.py tools/core/gates/base.py tools/lint/micro_mutator.py` |
| **Phase 2 (`M6`–`M9`)** | Skill path link breakage or CLI dispatch mismatch | `skill_router.py` checks `skills_index.json` `path` first with fallback scan; dynamic domain resolver in `tools/__init__.py` | `git checkout -- tools/core/sync_skills_manifest.py tools/core/skill_router.py skills_index.json tools/lint/invariant_checker.py tools/core/cli.py tools/__init__.py pyproject.toml AGENTS.md tools/design/super_plan_engine.py` |

---

## 7. Execution Transition & Plan Harvesting
- **Clean Context Handoff:** Upon approval, execute DAG waves in topological order: **Wave 1 (Parallel `M1`, `M2`, `M3`, `M4`)** -> **Wave 2 (`M5`, `M6`)** -> **Wave 3 (`M7`)** -> **Wave 4 (`M8`)** -> **Wave 5 (`M9`)**.
- **Solo-Swarm Verification per Wave:** Run targeted Red -> Green -> Scoped Tempdir Mutation (`>= 80%`) -> Adversarial Self-Audit (`--purple`) per milestone.
- **Plan Harvesting Hook:** After `M9` passes all 11 Hub DoD Quality Gates, run `python3 tools/design/plan_harvester.py` to record semantic contract hashes and persist architectural ADR `docs/adr/ADR-0005-v5-monorepo-and-sandbox-overhaul.md`.

---

## Consequences & Guarantees
- **Positive:** Sealed interface contracts, zero-regression blast radius, idempotent execution.
- **Negative / Constraints:** Strict adherence to atomic milestone budget (<= 3 files) and type contracts.
---

## Plan Calibration & Drift Analysis
- **Plan File Accuracy Score:** 12.6%
- **Plan File Drift Ratio:** 0.874
- **Semantic Contract Accuracy Score:** 28.6%
- **Semantic Contract Drift Ratio:** 0.714
- **Composite Plan Accuracy Score:** 20.6%
- **Unplanned Files (187):** `.cursor/rules/manual-qa.mdc`, `.cursor/rules/synapse-qa.mdc`, `.windsurfrules`, `CLAUDE.md`, `benchmarks/CONTEXT_TOKEN_BENCHMARK.md`, `project_state.json`, `skills-lock.json`, `skills/01-web-automation/auth-session-and-cookie-manager/SKILL.md`, `skills/01-web-automation/auth-session-and-cookie-manager/examples/multi_role_auth_matrix.md`, `skills/01-web-automation/auth-session-and-cookie-manager/examples/storage_state_sample.json`, `skills/01-web-automation/bats-testing-patterns/SKILL.md`, `skills/01-web-automation/bats-testing-patterns/examples/cli_runner_test.bats`, `skills/01-web-automation/bats-testing-patterns/resources/implementation-playbook.md`, `skills/01-web-automation/clean-pom-crafter/SKILL.md`, `skills/01-web-automation/clean-pom-crafter/examples/standard_test_case.groovy`, `skills/01-web-automation/clean-pom-crafter/references/angular_primeng_preset.md`, `skills/01-web-automation/clean-pom-crafter/references/katalon_pom.md`, `skills/01-web-automation/clean-pom-crafter/references/pom_patterns.groovy`, `skills/01-web-automation/e2e-testing-patterns/SKILL.md`, `skills/01-web-automation/e2e-testing-patterns/examples/playwright_sharded_config.ts`, `skills/01-web-automation/e2e-testing-patterns/resources/implementation-playbook.md`, `skills/01-web-automation/katalon-cli-runner/SKILL.md`, `skills/01-web-automation/katalon-cli-runner/examples/headless_kre_exec.sh`, `skills/01-web-automation/katalon-cli-runner/references/groovy-patterns.md`, `skills/01-web-automation/katalon-cli-runner/references/katalon-api.md`, `skills/01-web-automation/katalon-cli-runner/references/runner_commands.md`, `skills/01-web-automation/lam-script-generator/SKILL.md`, `skills/01-web-automation/lam-script-generator/examples/user_story_sample.md`, `skills/01-web-automation/mobile-appium-som/SKILL.md`, `skills/01-web-automation/mobile-appium-som/examples/BaseScreen.java`, `skills/01-web-automation/mobile-appium-som/examples/LoginScreen.java`, `skills/01-web-automation/mobile-appium-som/examples/TC_MobileLogin.java`, `skills/01-web-automation/mobile-maestro-detox-patterns/SKILL.md`, `skills/01-web-automation/mobile-maestro-detox-patterns/examples/sample_flow.yaml`, `skills/01-web-automation/playwright-live-interaction/SKILL.md`, `skills/01-web-automation/playwright-live-interaction/examples/live_probe_script.js`, `skills/01-web-automation/playwright-live-interaction/references/advanced_superpowers.md`, `skills/01-web-automation/playwright-live-interaction/references/compact_accessibility_snapshots.md`, `skills/01-web-automation/playwright-live-interaction/references/recipes.md`, `skills/01-web-automation/playwright-live-interaction/references/swarm_orchestration.md`, `skills/01-web-automation/playwright-webapp-testing/SKILL.md`, `skills/01-web-automation/playwright-webapp-testing/examples/server_lifecycle_playwright.py`, `skills/01-web-automation/web-agent-gym-benchmarking/SKILL.md`, `skills/01-web-automation/web-agent-gym-benchmarking/examples/benchmark_report_sample.json`, `skills/01-web-automation/web-agent-gym-benchmarking/examples/enterprise_tasks_suite.json`, `skills/02-test-design/architecture-decision-records/SKILL.md`, `skills/02-test-design/architecture-decision-records/examples/0001-record-architecture-decisions.md`, `skills/02-test-design/gherkin-to-suite/SKILL.md`, `skills/02-test-design/gherkin-to-suite/examples/checkout.feature`, `skills/02-test-design/gherkin-to-suite/examples/suite_report_sample.json`, `skills/02-test-design/manual-qa-and-rtm-bridge/SKILL.md`, `skills/02-test-design/manual-qa-and-rtm-bridge/examples/sample_bug_and_rtm.json`, `skills/02-test-design/rbt-manual-testing/SKILL.md`, `skills/02-test-design/rbt-manual-testing/examples/checkout_rbt_manual_suite.md`, `skills/02-test-design/rbt-manual-testing/examples/checkout_rbt_manual_testcases.md`, `skills/02-test-design/rbt-manual-testing/references/field_validation_checklist.md`, `skills/02-test-design/review-spec/SKILL.md`, `skills/02-test-design/review-spec/examples/pocock_grilling_decision_rubric.md`, `skills/02-test-design/review-spec/examples/sample_spec_review.md`, `skills/02-test-design/tot-exploratory-testing/SKILL.md`, `skills/02-test-design/tot-exploratory-testing/examples/payment_gateway_tot_tree.json`, `skills/02-test-design/tot-exploratory-testing/examples/tot_graph_sample.json`, `skills/03-api-and-contracts/api-network-mocking-interception/SKILL.md`, `skills/03-api-and-contracts/api-network-mocking-interception/examples/network_route_stub.json`, `skills/03-api-and-contracts/api-spec-to-e2e-matrix/SKILL.md`, `skills/03-api-and-contracts/api-spec-to-e2e-matrix/examples/sample_openapi.json`, `skills/03-api-and-contracts/consumer-driven-contract-testing/SKILL.md`, `skills/03-api-and-contracts/consumer-driven-contract-testing/examples/order_service_pact.json`, `skills/04-performance-and-load/backend-load-and-stress-patterns/SKILL.md`, `skills/04-performance-and-load/backend-load-and-stress-patterns/examples/k6_load_test_sample.js`, `skills/04-performance-and-load/backend-load-and-stress-patterns/references/k6_load_template.js`, `skills/04-performance-and-load/backend-load-and-stress-patterns/references/performance_test_plan_29119.md`, `skills/04-performance-and-load/lean-impact-scoreboard/SKILL.md`, `skills/04-performance-and-load/lean-impact-scoreboard/examples/sample_benchmark_gain.md`, `skills/04-performance-and-load/lean-impact-scoreboard/examples/sample_scoreboard.md`, `skills/04-performance-and-load/web-vitals-and-performance-profiler/SKILL.md`, `skills/04-performance-and-load/web-vitals-and-performance-profiler/examples/cwv_budget_policy.json`, `skills/04-performance-and-load/web-vitals-and-performance-profiler/examples/playwright_cwv_profiler_fixture.ts`, `skills/05-security-and-compliance/security-dast-sentinel/SKILL.md`, `skills/05-security-and-compliance/security-dast-sentinel/examples/dast_scan_config.json`, `skills/05-security-and-compliance/security-dast-sentinel/references/AI-AND-LLM.md`, `skills/05-security-and-compliance/security-dast-sentinel/references/ATTACK-CLASSES.md`, `skills/05-security-and-compliance/security-dast-sentinel/references/dast_recipes.ts`, `skills/05-security-and-compliance/skillspector-security-guard/SKILL.md`, `skills/05-security-and-compliance/skillspector-security-guard/examples/audit_threat_vectors_report.json`, `skills/05-security-and-compliance/skillspector-security-guard/examples/safe_mcp_config.json`, `skills/05-security-and-compliance/wcag-audit-patterns/SKILL.md`, `skills/05-security-and-compliance/wcag-audit-patterns/examples/wcag_compliance_checklist.json`, `skills/05-security-and-compliance/wcag-audit-patterns/resources/implementation-playbook.md`, `skills/06-healing-and-resilience/agentless-qa-repair/SKILL.md`, `skills/06-healing-and-resilience/agentless-qa-repair/examples/healing_report_sample.json`, `skills/06-healing-and-resilience/agentless-qa-repair/examples/three_phase_repair_workflow.md`, `skills/06-healing-and-resilience/antigravity-test-sentinel/SKILL.md`, `skills/06-healing-and-resilience/antigravity-test-sentinel/examples/dod_gate_policy.json`, `skills/06-healing-and-resilience/antigravity-test-sentinel/examples/sprint_dod_enforcement.md`, `skills/06-healing-and-resilience/failure-autopsy-and-healing/SKILL.md`, `skills/06-healing-and-resilience/failure-autopsy-and-healing/examples/closed_loop_healing_walkthrough.md`, `skills/06-healing-and-resilience/failure-autopsy-and-healing/examples/sample_junit_failure.xml`, `skills/06-healing-and-resilience/failure-autopsy-and-healing/references/healing_matrix.md`, `skills/06-healing-and-resilience/failure-autopsy-and-healing/references/qa_investigation_protocol.md`, `skills/06-healing-and-resilience/failure-autopsy-and-healing/scripts/triage_failures.sh`, `skills/06-healing-and-resilience/flaky-test-sentinel-and-quarantine/SKILL.md`, `skills/06-healing-and-resilience/flaky-test-sentinel-and-quarantine/examples/quarantine_registry.json`, `skills/06-healing-and-resilience/self-healing-locator/SKILL.md`, `skills/06-healing-and-resilience/self-healing-locator/examples/aom_diff_sample.json`, `skills/06-healing-and-resilience/systematic-debugging/SKILL.md`, `skills/06-healing-and-resilience/systematic-debugging/examples/four_phase_case.md`, `skills/06-healing-and-resilience/test-driven-development/SKILL.md`, `skills/06-healing-and-resilience/test-driven-development/examples/red_green_refactor_qa.md`, `skills/06-healing-and-resilience/verification-before-completion/SKILL.md`, `skills/06-healing-and-resilience/verification-before-completion/examples/evidence_log_example.md`, `skills/06-healing-and-resilience/visual-regression-sentinel/SKILL.md`, `skills/06-healing-and-resilience/visual-regression-sentinel/examples/visual_mask_rules.json`, `skills/07-data-and-state/db-state-verifier-and-seeder/SKILL.md`, `skills/07-data-and-state/db-state-verifier-and-seeder/examples/db_fixture_seed.json`, `skills/07-data-and-state/file-and-report-validator/SKILL.md`, `skills/07-data-and-state/file-and-report-validator/examples/sample_export_schema.json`, `skills/07-data-and-state/synthetic-test-data-generator/SKILL.md`, `skills/07-data-and-state/synthetic-test-data-generator/examples/idempotent_data_recipe.json`, `skills/08-code-quality/code-refactoring-refactor-clean/SKILL.md`, `skills/08-code-quality/code-refactoring-refactor-clean/examples/refactored_page_sample.groovy`, `skills/08-code-quality/code-refactoring-refactor-clean/examples/refactored_playwright_pom.ts`, `skills/08-code-quality/code-refactoring-refactor-clean/resources/implementation-playbook.md`, `skills/08-code-quality/graphify-impact-analyzer/SKILL.md`, `skills/08-code-quality/graphify-impact-analyzer/examples/dependency_blast_radius.json`, `skills/08-code-quality/lean-code-ladder/SKILL.md`, `skills/08-code-quality/lean-code-ladder/examples/ladder_walkthrough.md`, `skills/08-code-quality/repo-quality-audit/SKILL.md`, `skills/08-code-quality/repo-quality-audit/examples/sample_audit_walkthrough.md`, `skills/08-code-quality/repo-quality-audit/examples/sample_repo_audit.md`, `skills/08-code-quality/senior-code-review/SKILL.md`, `skills/08-code-quality/senior-code-review/examples/sample_review_walkthrough.md`, `skills/08-code-quality/surgical-coding-principles/SKILL.md`, `skills/08-code-quality/surgical-coding-principles/examples/surgical_vs_scope_creep.md`, `skills/08-code-quality/technical-debt-harvester/SKILL.md`, `skills/08-code-quality/technical-debt-harvester/examples/sample_debt_ledger.md`, `skills/08-code-quality/technical-debt-harvester/examples/sample_ledger_output.md`, `skills/09-ci-and-devops/github-actions-templates/SKILL.md`, `skills/09-ci-and-devops/github-actions-templates/examples/matrix_test_pipeline.yml`, `skills/09-ci-and-devops/gitlab-ci-templates/SKILL.md`, `skills/09-ci-and-devops/gitlab-ci-templates/examples/sample_gitlab_ci.yml`, `skills/09-ci-and-devops/jenkins-pipeline-templates/SKILL.md`, `skills/09-ci-and-devops/jenkins-pipeline-templates/examples/Jenkinsfile.example`, `skills/10-agent-orchestration/actor-qa-swarm/SKILL.md`, `skills/10-agent-orchestration/actor-qa-swarm/examples/broker_sharding_sample.json`, `skills/10-agent-orchestration/agent-orchestration-multi-agent-optimize/SKILL.md`, `skills/10-agent-orchestration/agent-orchestration-multi-agent-optimize/examples/swarm_workload_config.json`, `skills/10-agent-orchestration/event-stream-qa-orchestrator/SKILL.md`, `skills/10-agent-orchestration/event-stream-qa-orchestrator/examples/timeline_sample.jsonl`, `skills/10-agent-orchestration/persistent-planning-files/SKILL.md`, `skills/10-agent-orchestration/persistent-planning-files/examples/task_plan_example.md`, `skills/10-agent-orchestration/qa-memory-os/SKILL.md`, `skills/10-agent-orchestration/qa-memory-os/examples/archival_memory_sample.json`, `skills/11-ai-and-prompting/meta-prompt-crafter/SKILL.md`, `skills/11-ai-and-prompting/meta-prompt-crafter/examples/qa_prompt_template.md`, `skills/11-ai-and-prompting/mipro-prompt-compiler/SKILL.md`, `skills/11-ai-and-prompting/mipro-prompt-compiler/examples/compiled_module_sample.json`, `skills/11-ai-and-prompting/mipro-prompt-compiler/examples/dspy_assertion_optimizer_case.md`, `skills/11-ai-and-prompting/qa-aci-interface/SKILL.md`, `skills/11-ai-and-prompting/qa-aci-interface/examples/surgical_code_window_walkthrough.md`, `skills/11-ai-and-prompting/qa-aci-interface/examples/surgical_edit_sample.json`, `skills/11-ai-and-prompting/token-and-context-optimizer/SKILL.md`, `skills/11-ai-and-prompting/token-and-context-optimizer/examples/distilled_log_sample.txt`, `skills/11-ai-and-prompting/token-and-context-optimizer/references/context_engineering_guide.md`, `templates/ai_bridges/CLAUDE.md`, `templates/ai_bridges/copilot-instructions.md`, `templates/ai_bridges/cursor_synapse_qa.mdc`, `templates/ai_bridges/windsurfrules`, `tests/test_audit_remediation_e2e.py`, `tests/test_borrow_wave2.py`, `tests/test_manual_qa_phase1.py`, `tests/test_p0_p1_audit_fixes.py`, `tests/test_package_release.py`, `tests/test_packaging_parity.py`, `tests/test_skill_hash_lock.py`, `tests/test_tool_catalog.py`, `tools/core/circuit_breaker.py`, `tools/core/count_tokens.py`, `tools/core/gates/gate_10_perf_sla.py`, `tools/core/skill_canonical_digest.py`, `tools/lint/validate_skills_schema.py`, `tools/manual/checklist_query.py`, `tools/orchestration/senior_code_review.py`, `tools/orchestration/solo_runner.py`, `tools/perf/benchmark_perf_runner.py`, `tests/test_gemini4_models.py`, `tools/core/cli_specs.json`

