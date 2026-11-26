<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Implementation Plan: Synapse Hub v5.1 Apex Architecture Overhaul — Zero-Python Native Node.js Linter, Semantic POM Inheritance/Fixture Graph, 145-Module Strict Mypy Ratchet & Zero-Ceremony Client Mode

> **Super-Plan Metadata:** `Tier 2 (DEEP_SUPER_PLAN)` | `RiskScore = 0.92` (`BlastRadius = 46`, `CrossBoundary = True`, `StateMutation = True`, `HistoryDrift = 0.05`)
> **Execution Mode:** Sequential Single-Agent `/solo` (`M1 -> M2 -> M3 -> M4 -> M5 -> M6 -> M7 -> M8 -> M9 -> M10 -> M11 -> M12`, strictly zero `swarm` workers or parallel subagents)
> **Explicit Out-of-Scope & Immutable Boundaries:**
> - External third-party OSS repository field scraping/cloning is explicitly excluded per user directive (`"trừ việc đi cọ sát nhé"`).
> - `tools/core/author_integrity.py` and all MIT copyright/provenance attributions to **Thế Vị (@TeeVee98)** remain 100% immutable and untouched.
>
> **Governing Rulings (Locked at Stage 2 Ambiguity Gate):**
> - `Ruling 1 (Zero-Python Native Node.js Linter & Auto-Fixer Engine):` Build `bin/native-linter.js` (zero-dependency Node.js >= 18 stdlib engine sharing rule semantics with VS Code & `infer_linter.py`) and wire `bin/agent-qa.js` (`--engine {auto,python,native-js}`) so machines lacking Python (`node:20-alpine`, Frontend laptops) execute `npx @teevee98/synapse-hub lint|fix|doctor|version|help` natively in `< 50ms` without failing — *Cost: maintain a deterministic JS-vs-Python Parity Matrix test suite.*
> - `Ruling 2 (145-Module Core Production Strict Mypy Ratchet + Latent Crash Remediation + Scientific Simulation Labeling):` Eliminate all 100 hidden `arg-type`, `attr-defined`, and `return` static type defects across all 6 core production packages (`tools/core.*`, `tools/lint.*`, `tools/context.*`, `tools/mcp.*`, `tools/alm.*`, `tools/transpiler.*`) plus runtime crash bugs in `mcp_excel_server.py` (`list.get`), `codeact_engine.py` (Windows `os.killpg`), and `benchmark_perf_runner.py` (`sum`), raise global coverage floor `65 -> 70`, and label offline research tiers transparently as `[Simulation/Heuristic]` without breaking Gate 11 — *Cost: 8 sequential surgical milestones (`<= 3` files/node).*
> - `Ruling 3 (Semantic POM Inheritance/Fixture/Barrel Graph + Zero-Ceremony Client Profile):` Upgrade `pom_assertion_indexer.py` & `infer_linter.py` to resolve multi-level class inheritance (`ChildPage extends BasePage`), cross-file Playwright `test.extend<{ fixture: PageClass }>` bindings, and barrel `index.ts` / aliased imports (`import { Page as P }`), while streamlining `init_config.py` and `sync_agent_rules.py` so `--profile starter` runs in `< 2s` with lightweight client rules — *Cost: mtime-keyed graph cache to keep scan latency `< 50ms` P95.*

### Stage 2 Orthogonal Architectural Tournament (Trade-Off Matrix)

| Evaluation Dimension | Branch A: Python-Only CLI + Suppressed Mypy | Branch B (Selected): Native Node.js Fallback + Semantic POM Graph + 145-Module Strict Mypy + Lean Spoke | Branch C: Hard-Delete Research Modules & Rewrite Everything in Node.js |
| :--- | :--- | :--- | :--- |
| **Frontend / Docker Node DX** | Fails immediately on `node:20-alpine` without Python | **Runs `npx synapse-hub lint/fix/doctor` in `< 50ms` pure Node.js with zero Python installed** | Fast in Node, but abandons Python AST/mutation/MCP ecosystem |
| **Enterprise TS Monorepo Accuracy** | Misses inherited `BasePage` methods & `test.extend` fixtures | **Resolves 5-level `extends` chains, `test.extend<Fixtures>`, and `index.ts` barrel aliases** | High rewrite risk across 5 languages |
| **Type Safety & Bug Prevention** | Hides `arg-type`/`attr-defined` crashes across 97% of repo | **Enforces `arg-type`, `attr-defined`, `return` across all 145+ core production modules (`0` errors)** | Breaks Gate 11 & historical test contracts |
| **Spoke Onboarding Ceremony** | Heavy Hub-grade ceremony leaks into starter workflows | **`--profile starter` delivers `< 35`-line client bridge & `< 2s` verification loop** | Loses Hub enterprise governance |

---

## 1. Affected Files & Blast Radius

### New Files to Create (Native JS Engine, Parity & Semantic POM Suites, Type-Safety Guards & ADR)

| Action | Target File & Symbol Anchor | Line Range | Change Purpose & Blast Radius |
| :---: | :--- | :---: | :--- |
| `[CREATE]` | `bin/native-linter.js` | `(New)` | Pure Node.js >= 18 zero-dependency polyglot QA linter, cross-file POM assertion scanner, `--fix` engine, `--json`/`--sarif` formatter, and Node-only `doctor` report (`< 50ms` startup). |
| `[CREATE]` | `tests/test_native_js_python_parity.py` | `(New)` | 4-scenario pytest parity matrix comparing `bin/native-linter.js` vs `infer_linter.py` across Clean POM, 6 defect types, `--fix` edits, and Python-less `PATH` execution. |
| `[CREATE]` | `tests/test_semantic_pom_inheritance_fixtures.py` | `(New)` | 4-scenario pytest suite validating 3-tier `extends` inheritance (`BasePage -> MidPage -> VipPage`), Playwright `test.extend<{ checkout: CheckoutPage }>`, barrel `index.ts` re-exports, and cyclic inheritance safety. |
| `[CREATE]` | `tests/test_zero_ceremony_client_profile.py` | `(New)` | 4-scenario pytest suite validating `--profile starter` config generation, `< 35`-line lightweight client bridge output, zero Hub `tools/` path leaks, and `< 2s` target verification. |
| `[CREATE]` | `tests/test_core_type_safety_and_win32_guards.py` | `(New)` | 4-scenario pytest suite verifying `mcp_excel_server` dict/list row normalization, Windows-safe `codeact_engine` timeout termination, `benchmark_perf_runner` numeric aggregation, and `mypy` zero-error gate across all 6 core packages. |
| `[CREATE]` | `docs/adr/ADR-0024-synapse-hub-apex-native-js-semantic-pom-strict-typing.md` | `(New)` | Tier-2 ADR recording Apex architecture rulings, JS/Python parity receipts, 145-module `mypy` certification, coverage ratchet (`70%`), and transparent `[Simulation/Heuristic]` tier classification. |

### Existing Files to Modify (Grounded AST Structural Anchors)

| Action | Target File & Symbol Anchor | Line Range | Change Purpose & Blast Radius |
| :---: | :--- | :---: | :--- |
| `[MODIFY]` | `bin/agent-qa.js` (AST: main) | `(L61-L185)` | Add `--engine {auto,python,native-js}` flag handling and automatic fallback to `bin/native-linter.js` for `lint`, `fix`, `doctor`, `version`, and `help` when Python >= 3.10 is absent. |
| `[MODIFY]` | `tools/context/pom_assertion_indexer.py` (AST: build_pom_assertion_index) | `(L181-L210, L580-L735)` | Add multi-level class inheritance propagation (`class_parents`), Playwright `test.extend<{ fixture: Class }>` extraction (`fixture_class_bindings`), and barrel `index.ts` export tracking. |
| `[MODIFY]` | `tools/lint/infer_linter.py` (AST: _match_cross_file_assertions) | `(L219-L365)` | Resolve `fixture_class_bindings` for destructured Playwright fixtures (`async ({ checkoutPage }) => ...`) and `import { Page as Alias }` bindings in `_extract_receiver_class_bindings`. |
| `[MODIFY]` | `tools/mcp/mcp_excel_server.py` (AST: read_sheet_rows) | `(L240-L275)` | Fix latent runtime `AttributeError` (`list[str]` `.get`) and `arg-type` mismatch when normalizing tabular sheet rows into `clone_and_export_template`. |
| `[MODIFY]` | `tools/runtime/codeact_engine.py` (AST: CodeActSecurityVisitor) | `(L205-L235)` | Guard POSIX-only `os.killpg` / `os.getpgid` / `signal.SIGKILL` with cross-platform Windows `proc.kill()` fallback on subprocess timeout. |
| `[MODIFY]` | `tools/perf/benchmark_perf_runner.py` (AST: run_benchmark) | `(L120-L145)` | Fix `sum()` mixed `int | str` type bug with explicit `int(...)` coercion and typed return annotations. |
| `[MODIFY]` | `tools/lint/micro_mutator.py` (AST: ScopedMutationReceipt) | `(L535-L580)` | Narrow `ast.AST` node types (`ast.Constant`, `ast.Compare`, `ast.BoolOp`, `ast.BinOp`, `ast.UnaryOp`) to eliminate all 30 `attr-defined` mypy errors. |
| `[MODIFY]` | `tools/lint/mipro_assertion_tuner.py` (AST: MiproAssertionTuner) | `(L1-L160)` | Resolve strict `arg-type`/`return` annotation mismatch under core lint mypy enforcement. |
| `[MODIFY]` | `tools/lint/pre_push_guard.py` (AST: verify_quality_gates) | `(L80-L110)` | Narrow `object` metric value before `float(...)` conversion (`L91`). |
| `[MODIFY]` | `tools/core/verify_all.py` (AST: run_all_gates_detailed) | `(L305-L395)` | Narrow `object` before `.lower()` (`L316`) and type `summary` dictionary passed into `create_receipt` (`L388`). |
| `[MODIFY]` | `tools/core/dod_receipt.py` (AST: create_receipt) | `(L1-L140)` | Align `create_receipt` parameter/return annotations for strict `arg-type` & `return` checking. |
| `[MODIFY]` | `tools/core/gates/gate_07_infer_linter.py` (AST: gate_7_infer_linter) | `(L1-L150)` | Resolve strict `arg-type` / `return` annotation in Gate 7 runner. |
| `[MODIFY]` | `tools/core/agent_runner.py` (AST: execute_agent_run) | `(L1-L180)` | Fix 3 `arg-type`/`attr-defined` type mismatches in subprocess/result handling. |
| `[MODIFY]` | `tools/core/self_evolving_loop.py` (AST: SelfEvolvingLoop) | `(L1-L180)` | Fix 3 `arg-type`/`return` mismatches in `CandidateEdit` / `SelfEvolvingLoop`. |
| `[MODIFY]` | `tools/core/telemetry.py` (AST: TraceContext) | `(L1-L150)` | Fix 2 `arg-type`/`return` mismatches in OpenTelemetry span context serialization. |
| `[MODIFY]` | `tools/core/file_lock.py` (AST: FileLockTimeoutError) | `(L1-L150)` | Fix 2 cross-platform `_win32_lock` / `fcntl` type narrowing annotations. |
| `[MODIFY]` | `tools/core/repo_map.py` (AST: resolve_target_repo) | `(L1-L160)` | Fix `arg-type`/`return` mismatch in repository path resolution. |
| `[MODIFY]` | `tools/core/package_release.py` (AST: collect_package_files) | `(L1-L150)` | Fix `arg-type` path normalization in release archive builder. |
| `[MODIFY]` | `tools/core/memory_bus.py` (AST: UnifiedMemoryBus) | `(L1-L160)` | Fix SQLite row/JSON payload type narrowing in `UnifiedMemoryBus`. |
| `[MODIFY]` | `tools/core/count_tokens.py` (AST: estimate_tokens) | `(L1-L140)` | Fix `arg-type`/`return` type narrowing in token budget calculator. |
| `[MODIFY]` | `tools/context/polyglot_ast_parser.py` (AST: parse_python_ast) | `(L200-L260)` | Fix `attr-defined` AST node attribute narrowing in `parse_python_ast`. |
| `[MODIFY]` | `tools/core/init_config.py` (AST: build_default_config) | `(L101-L220)` | Fix 3 mypy errors, add `gate_11_token_reduction: False` to `starter`/`standard` profiles, and add `ceremony_level: "minimal"` for `< 2s` Spoke execution. |
| `[MODIFY]` | `tools/core/sync_agent_rules.py` (AST: ClientBridgeRuleBundleDTO) | `(L100-L220)` | Add `--profile {starter,standard,enterprise}` generating a concise `< 35`-line Zero-Ceremony Client Bridge when `profile == "starter"`. |
| `[MODIFY]` | `pyproject.toml` (AST: project) | `(L92-L98, L166-L178)` | Raise `[tool.coverage.report] fail_under` from `65` to `70`; permanently enable `arg-type`, `attr-defined`, and `return` checking across `tools.core.*`, `tools.lint.*`, `tools.context.*`, `tools.mcp.*`, `tools.alm.*`, `tools.transpiler.*`, `tools.runtime.codeact_engine`, and `tools.perf.benchmark_perf_runner`. |
| `[MODIFY]` | `tools/core/gates/gate_11_token_reduction.py` (AST: gate_11_token_reduction) | `(L46-L95)` | Emit explicit `tier_classification: {"production_active": 9, "offline_heuristic_simulation": 6}` metadata so simulation tiers are transparently distinguished in JSON/text reports. |
| `[MODIFY]` | `tools/core/cli_specs.json` (AST: registry) | `(L1-L220)` | Prefix offline research simulation lab command descriptions (`cove`, `ai-eval`, `tot-exploratory`, `assertion-optimizer`) with `[Offline Heuristic]` for 100% engineering transparency. |
| `[MODIFY]` | `docs/ARCHITECTURE.md` (AST: file_root) | `(L148-L210)` | Document Zero-Python Native Node.js Linter fallback, Semantic POM Inheritance/`test.extend` Graph, 145-module strict typing, and Production vs Offline Heuristic Simulation boundary table. |

---

## 2. Data Flow & Interface Signatures

```text
npx @teevee98/synapse-hub <cmd> (bin/agent-qa.js)
   ├── Python >= 3.10 Present ──► Full Python Engine (tools/core/cli.py + Semantic POM Graph + 11 Gates)
   └── Python Absent / --engine native-js ──► bin/native-linter.js (< 50ms Pure Node.js Lint / Fix / Doctor)
                                                    ▲
                                                    └── Verified 1:1 by tests/test_native_js_python_parity.py

Page Classes + BasePage Inheritance + fixtures/test.ts (test.extend) + index.ts Barrels
   └──► build_pom_assertion_index() ──► CrossFileAssertionMapDTO (qualified_class_methods + fixture_class_bindings)
                                                    └──► infer_linter.py (_match_cross_file_assertions)
```

> **Anti-Full-Code Invariant:** Only typed DTOs and public function contracts are locked below. Implementation bodies belong strictly to sequential `/solo` execution phases.

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class NativeJsLintParityDTO:
    files_evaluated: int
    js_defect_codes: Tuple[str, ...]
    py_defect_codes: Tuple[str, ...]
    parity_match: bool
    node_startup_ms: float
    ran_without_python_in_path: bool


@dataclass(frozen=True)
class SemanticPomGraphDTO:
    repo_root: str
    inheritance_edges_resolved: int
    playwright_fixtures_bound: Dict[str, str]
    barrel_exports_resolved: int
    qualified_class_methods: Dict[str, Set[str]]


@dataclass(frozen=True)
class CoreTypeSafetyAuditDTO:
    packages_enforced: Tuple[str, ...]
    modules_checked: int
    mypy_errors_count: int
    coverage_floor_pct: float
    win32_timeout_safe: bool
    passed: bool


@dataclass(frozen=True)
class ZeroCeremonyProfileDTO:
    profile: str  # "starter" | "standard" | "enterprise"
    bridge_line_count: int
    hub_paths_leaked: int
    mutation_required: bool
    passed: bool


@dataclass(frozen=True)
class ApexCertificationDTO:
    adr_path: str
    native_js_parity: bool
    semantic_pom_verified: bool
    strict_mypy_errors: int
    all_11_gates_passed: bool


def resolve_class_inheritance_assertions(
    direct_and_call_methods: Dict[str, Set[str]],
    class_parents: Dict[str, Tuple[str, ...]],
    max_inheritance_depth: int = 5,
) -> Dict[str, Set[str]]:
    """Propagates asserted methods down multi-level `extends` class hierarchies without cycle divergence."""
    ...


def extract_playwright_fixture_bindings(
    clean_code: str,
    raw_code: str,
) -> Dict[str, str]:
    """Extracts `fixtureName -> PageClassName` mappings from Playwright `test.extend<...>({...})` modules."""
    ...


def generate_client_bridge_markdown(
    profile: str = "starter",
) -> ZeroCeremonyProfileDTO:
    """Generates a `< 35`-line Zero-Ceremony client AI bridge for `starter` or full governance for `enterprise`."""
    ...
```

---

## 3. Atomic Milestones & Execution DAG

### Milestone 1: Zero-Python Native Node.js Linter & Auto-Fixer (`bin/native-linter.js`)
- **Node ID**: M1
- **depends_on**: []
- **consumes**: []
- **produces**: [{'contract': 'NativeJsLintParityDTO'}]
- **Files Modified**: `bin/native-linter.js`, `bin/agent-qa.js`
- **Write Set**: ['bin/native-linter.js', 'bin/agent-qa.js']
- **Compute Tier**: [Model: Pro | Thinking: High]
- **Scope**: Create `bin/native-linter.js` using pure Node.js >= 18 stdlib (`fs`, `path`) implementing comment/backtick-template lexical stripping, cross-file `pages/` assertion method indexing, per-test-block `FAKE_PASS_NO_ASSERTION`, `UNAWAITED_ASYNC_ASSERTION`, `DANGLING_ASSERTION_NO_MATCHER`, `EXCESSIVE_HARD_DELAY`, `SWALLOWED_EXCEPTION`, `TAUTOLOGICAL_ASSERTION`, Clean POM raw selector detection, `--fix` auto-remediation, `--json` / `--sarif` output, and Node-only `doctor` diagnostics. Update `bin/agent-qa.js` to support `--engine {auto,python,native-js}` and automatically route `lint`, `fix`, `doctor`, `version`, and `help` to `bin/native-linter.js` whenever Python >= 3.10 is absent on `PATH`.
- **Circuit Breaker**: Max Fix Attempts = 2; halt if `node bin/agent-qa.js lint examples/playwright-crm-suite --engine native-js --json` exceeds `150ms` or reports false positives on clean reference suites.
- **Rollback Hook**: `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['bin/agent-qa.js'], created_files=['bin/native-linter.js'])"`

### Milestone 2: JS-vs-Python Linter Parity Matrix & Python-Less `PATH` Certification
- **Node ID**: M2
- **depends_on**: ['M1']
- **consumes**: [{'contract': 'NativeJsLintParityDTO'}]
- **produces**: [{'contract': 'CertifiedNativeJsParityDTO'}]
- **Files Modified**: `tests/test_native_js_python_parity.py`
- **Write Set**: ['tests/test_native_js_python_parity.py']
- **Compute Tier**: [Model: Flash | Thinking: Off]
- **Scope**: Author 4-scenario `tests/test_native_js_python_parity.py` asserting: (a) Positive 1:1 defect-code parity between `node bin/agent-qa.js lint --engine native-js --json` and `infer_linter.py --format json` across Clean POM & 6 defect fixtures + `--fix` idempotency, (b) Negative Python-only subcommand (`mutate`) with Python stripped from `PATH` exits cleanly with clear install guidance while `lint`/`fix`/`doctor`/`version` succeed with exit code `0` under a Python-less `PATH` containing only `node`, (c) Boundary empty files, UTF-8 backticks, and nonexistent paths, (d) CLI `--engine native-js`, `--json`, `--sarif`, `--fix` contracts.
- **Circuit Breaker**: Max Fix Attempts = 2; forbid skipping Python-less `PATH` subprocess verification.
- **Rollback Hook**: `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(created_files=['tests/test_native_js_python_parity.py'])"`

### Milestone 3: Semantic POM Graph — Multi-Level Inheritance (`extends`), Playwright `test.extend<Fixtures>` & Barrel Exports
- **Node ID**: M3
- **depends_on**: ['M2']
- **consumes**: [{'contract': 'CertifiedNativeJsParityDTO'}]
- **produces**: [{'contract': 'SemanticPomGraphDTO'}]
- **Files Modified**: `tools/context/pom_assertion_indexer.py`, `tools/lint/infer_linter.py`, `tests/test_semantic_pom_inheritance_fixtures.py`
- **Write Set**: ['tools/context/pom_assertion_indexer.py', 'tools/lint/infer_linter.py', 'tests/test_semantic_pom_inheritance_fixtures.py']
- **Compute Tier**: [Model: Pro | Thinking: High]
- **Scope**: Extend `pom_assertion_indexer.py` (`CrossFileAssertionMapDTO` with backward-compatible defaulted `fixture_class_bindings: Dict[str, str]` and `class_parents: Dict[str, Tuple[str, ...]]`) to: (1) propagate asserted methods down multi-level `extends` / Python base-class chains (`BasePage -> CheckoutPage -> VipCheckoutPage`, cycle-safe up to depth 5), (2) extract Playwright `test.extend<{ checkoutPage: CheckoutPage }>({ checkoutPage: async ({ page }, use) => use(new CheckoutPage(page)) })` bindings across `fixtures/*.ts` and `index.ts` barrel exports, and (3) wire `fixture_class_bindings` + `import { CheckoutPage as CP }` alias resolution into `infer_linter.py::_extract_receiver_class_bindings`. Certify with 4-scenario `tests/test_semantic_pom_inheritance_fixtures.py`.
- **Circuit Breaker**: Max Fix Attempts = 2; halt if cyclic inheritance (`class A extends B` + `class B extends A`) loops or if P95 benchmark latency exceeds `50ms`.
- **Rollback Hook**: `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['tools/context/pom_assertion_indexer.py', 'tools/lint/infer_linter.py'], created_files=['tests/test_semantic_pom_inheritance_fixtures.py'])"`

### Milestone 4: Remediate Latent Runtime Type Bugs (`mcp_excel_server`, Windows `codeact_engine`, `benchmark_perf_runner`)
- **Node ID**: M4
- **depends_on**: ['M3']
- **consumes**: [{'contract': 'SemanticPomGraphDTO'}]
- **produces**: [{'contract': 'RemediatedRuntimeBugsDTO'}]
- **Files Modified**: `tools/mcp/mcp_excel_server.py`, `tools/runtime/codeact_engine.py`, `tools/perf/benchmark_perf_runner.py`
- **Write Set**: ['tools/mcp/mcp_excel_server.py', 'tools/runtime/codeact_engine.py', 'tools/perf/benchmark_perf_runner.py']
- **Compute Tier**: [Model: Pro | Thinking: High]
- **Scope**: Fix the 3 real runtime crash bugs uncovered by strict `mypy`: (1) normalize `list[list[str]]` vs `list[dict[str, Any]]` row structures in `tools/mcp/mcp_excel_server.py` (`L252`, `L261`) preventing `AttributeError: 'list' object has no attribute 'get'`, (2) guard POSIX-only `os.killpg` / `os.getpgid` / `signal.SIGKILL` in `tools/runtime/codeact_engine.py` (`L219`) with Windows-safe `proc.kill()` fallback, and (3) coerce `int` latency counters before `sum(...)` in `tools/perf/benchmark_perf_runner.py` (`L130`).
- **Circuit Breaker**: Max Fix Attempts = 2; halt if `mypy --enable-error-code arg-type --enable-error-code attr-defined --enable-error-code return` reports any error on these 3 files.
- **Rollback Hook**: `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['tools/mcp/mcp_excel_server.py', 'tools/runtime/codeact_engine.py', 'tools/perf/benchmark_perf_runner.py'])"`

### Milestone 5: Strict Type Hardening Across `tools/lint/*` (`micro_mutator`, `mipro_assertion_tuner`, `pre_push_guard`)
- **Node ID**: M5
- **depends_on**: ['M4']
- **consumes**: [{'contract': 'RemediatedRuntimeBugsDTO'}]
- **produces**: [{'contract': 'TypedLintPackageDTO'}]
- **Files Modified**: `tools/lint/micro_mutator.py`, `tools/lint/mipro_assertion_tuner.py`, `tools/lint/pre_push_guard.py`
- **Write Set**: ['tools/lint/micro_mutator.py', 'tools/lint/mipro_assertion_tuner.py', 'tools/lint/pre_push_guard.py']
- **Compute Tier**: [Model: Pro | Thinking: High]
- **Scope**: Replace untyped `ast.AST` `.value`/`.op` accesses in `tools/lint/micro_mutator.py` (`L545-L572`) with explicit `isinstance` AST node narrowing (eliminating all 30 `attr-defined` errors), resolve the `arg-type`/`return` mismatch in `tools/lint/mipro_assertion_tuner.py`, and narrow `object` metric values before `float(...)` in `tools/lint/pre_push_guard.py` (`L91`) so the entire 27-module `tools/lint/` package passes strict `arg-type`, `attr-defined`, and `return` checking with `0` errors.
- **Circuit Breaker**: Max Fix Attempts = 2; halt if `pytest tests/test_micro_mutator.py` regresses.
- **Rollback Hook**: `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['tools/lint/micro_mutator.py', 'tools/lint/mipro_assertion_tuner.py', 'tools/lint/pre_push_guard.py'])"`

### Milestone 6: Strict Type Hardening Across `tools/core/*` Verification Pipeline (Batch 1)
- **Node ID**: M6
- **depends_on**: ['M5']
- **consumes**: [{'contract': 'TypedLintPackageDTO'}]
- **produces**: [{'contract': 'TypedCoreGatesDTO'}]
- **Files Modified**: `tools/core/verify_all.py`, `tools/core/dod_receipt.py`, `tools/core/gates/gate_07_infer_linter.py`
- **Write Set**: ['tools/core/verify_all.py', 'tools/core/dod_receipt.py', 'tools/core/gates/gate_07_infer_linter.py']
- **Compute Tier**: [Model: Flash | Thinking: Off]
- **Scope**: Fix strict `attr-defined` and `arg-type` mismatches in `tools/core/verify_all.py` (`L316`, `L388`), `tools/core/dod_receipt.py`, and `tools/core/gates/gate_07_infer_linter.py` with zero behavioral regressions to `tests/test_verify_all.py`.
- **Circuit Breaker**: Max Fix Attempts = 2; halt if `pytest tests/test_verify_all.py` fails.
- **Rollback Hook**: `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['tools/core/verify_all.py', 'tools/core/dod_receipt.py', 'tools/core/gates/gate_07_infer_linter.py'])"`

### Milestone 7: Strict Type Hardening Across `tools/core/*` Runtime & Telemetry (Batch 2)
- **Node ID**: M7
- **depends_on**: ['M6']
- **consumes**: [{'contract': 'TypedCoreGatesDTO'}]
- **produces**: [{'contract': 'TypedCoreRuntimeDTO'}]
- **Files Modified**: `tools/core/agent_runner.py`, `tools/core/self_evolving_loop.py`, `tools/core/telemetry.py`
- **Write Set**: ['tools/core/agent_runner.py', 'tools/core/self_evolving_loop.py', 'tools/core/telemetry.py']
- **Compute Tier**: [Model: Flash | Thinking: Off]
- **Scope**: Resolve all `arg-type`, `attr-defined`, and `return` static type errors across `tools/core/agent_runner.py` (3 errors), `tools/core/self_evolving_loop.py` (3 errors), and `tools/core/telemetry.py` (2 errors).
- **Circuit Breaker**: Max Fix Attempts = 2; halt if `pytest tests/test_agent_runner.py` fails.
- **Rollback Hook**: `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['tools/core/agent_runner.py', 'tools/core/self_evolving_loop.py', 'tools/core/telemetry.py'])"`

### Milestone 8: Strict Type Hardening Across `tools/core/*` Infrastructure Utilities (Batch 3)
- **Node ID**: M8
- **depends_on**: ['M7']
- **consumes**: [{'contract': 'TypedCoreRuntimeDTO'}]
- **produces**: [{'contract': 'TypedCoreInfraDTO'}]
- **Files Modified**: `tools/core/file_lock.py`, `tools/core/repo_map.py`, `tools/core/package_release.py`
- **Write Set**: ['tools/core/file_lock.py', 'tools/core/repo_map.py', 'tools/core/package_release.py']
- **Compute Tier**: [Model: Flash | Thinking: Off]
- **Scope**: Resolve cross-platform `arg-type`, `attr-defined`, and `return` static type errors in `tools/core/file_lock.py` (2 errors), `tools/core/repo_map.py` (1 error), and `tools/core/package_release.py` (1 error).
- **Circuit Breaker**: Max Fix Attempts = 2; verify cross-platform Windows/POSIX lock fallback remains intact.
- **Rollback Hook**: `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['tools/core/file_lock.py', 'tools/core/repo_map.py', 'tools/core/package_release.py'])"`

### Milestone 9: Strict Type Hardening Across `tools/core/*` & `tools/context/*` (Batch 4)
- **Node ID**: M9
- **depends_on**: ['M8']
- **consumes**: [{'contract': 'TypedCoreInfraDTO'}]
- **produces**: [{'contract': 'TypedCoreContextDTO'}]
- **Files Modified**: `tools/core/memory_bus.py`, `tools/core/count_tokens.py`, `tools/context/polyglot_ast_parser.py`
- **Write Set**: ['tools/core/memory_bus.py', 'tools/core/count_tokens.py', 'tools/context/polyglot_ast_parser.py']
- **Compute Tier**: [Model: Flash | Thinking: Off]
- **Scope**: Resolve the remaining `arg-type`, `attr-defined`, and `return` mismatches in `tools/core/memory_bus.py` (1 error), `tools/core/count_tokens.py` (1 error), and `tools/context/polyglot_ast_parser.py` (1 error).
- **Circuit Breaker**: Max Fix Attempts = 2; halt if `pytest tests/test_ast_engine.py` fails.
- **Rollback Hook**: `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['tools/core/memory_bus.py', 'tools/core/count_tokens.py', 'tools/context/polyglot_ast_parser.py'])"`

### Milestone 10: Zero-Ceremony Client/Starter Profile (`< 2s` Spoke DX) & `init_config` Type Hardening
- **Node ID**: M10
- **depends_on**: ['M9']
- **consumes**: [{'contract': 'TypedCoreContextDTO'}]
- **produces**: [{'contract': 'ZeroCeremonyProfileDTO'}]
- **Files Modified**: `tools/core/init_config.py`, `tools/core/sync_agent_rules.py`, `tests/test_zero_ceremony_client_profile.py`
- **Write Set**: ['tools/core/init_config.py', 'tools/core/sync_agent_rules.py', 'tests/test_zero_ceremony_client_profile.py']
- **Compute Tier**: [Model: Pro | Thinking: High]
- **Scope**: Fix all 3 mypy errors in `tools/core/init_config.py`, add explicit `"gate_11_token_reduction": False` and `"ceremony_level": "minimal"` to `starter` (and `"standard"` to `standard`) in `build_default_config`, and add `generate_client_bridge_markdown(profile="starter")` + `--profile {starter,standard,enterprise}` in `tools/core/sync_agent_rules.py` emitting a `< 35`-line Zero-Ceremony client rule bundle (Clean POM + Smart Waits + Zero Fake-Pass + native runner, zero heavy Red-Green-Mutation-Purple mandates for `starter` users) while keeping Hub `AGENTS.md` and default `enterprise` bridges 100% backward-compatible. Certify with 4-scenario `tests/test_zero_ceremony_client_profile.py`.
- **Circuit Breaker**: Max Fix Attempts = 2; halt if `python tools/core/sync_agent_rules.py --check` or `tests/test_sync_agent_rules.py` fails.
- **Rollback Hook**: `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['tools/core/init_config.py', 'tools/core/sync_agent_rules.py'], created_files=['tests/test_zero_ceremony_client_profile.py'])"`

### Milestone 11: Permanent 145-Module Strict Mypy Lock, `70%` Coverage Ratchet & Simulation Transparency
- **Node ID**: M11
- **depends_on**: ['M10']
- **consumes**: [{'contract': 'ZeroCeremonyProfileDTO'}, {'contract': 'RemediatedRuntimeBugsDTO'}]
- **produces**: [{'contract': 'CoreTypeSafetyAuditDTO'}]
- **Files Modified**: `pyproject.toml`, `tools/core/gates/gate_11_token_reduction.py`, `tests/test_core_type_safety_and_win32_guards.py`
- **Write Set**: ['pyproject.toml', 'tools/core/gates/gate_11_token_reduction.py', 'tests/test_core_type_safety_and_win32_guards.py']
- **Compute Tier**: [Model: Pro | Thinking: High]
- **Scope**: Update `pyproject.toml` to: (1) raise `[tool.coverage.report] fail_under` from `65` to `70`, and (2) add a permanent `[[tool.mypy.overrides]]` block covering `tools.core.*`, `tools.lint.*`, `tools.context.*`, `tools.mcp.*`, `tools.alm.*`, `tools.transpiler.*`, `tools.runtime.codeact_engine`, and `tools.perf.benchmark_perf_runner` with `arg-type`, `attr-defined`, and `return` strictly enabled (`0` errors across 145+ modules). Update `gate_11_token_reduction.py` to emit explicit `tier_classification` (`production_active: 9`, `offline_heuristic_simulation: 6`). Author 4-scenario `tests/test_core_type_safety_and_win32_guards.py` mechanically locking `mypy` zero-error compliance, Windows `codeact_engine` timeout safety, and `mcp_excel_server` row handling.
- **Circuit Breaker**: Max Fix Attempts = 2; halt if `python -m mypy tools/core tools/lint tools/context tools/mcp tools/alm tools/transpiler` returns non-zero.
- **Rollback Hook**: `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['pyproject.toml', 'tools/core/gates/gate_11_token_reduction.py'], created_files=['tests/test_core_type_safety_and_win32_guards.py'])"`

### Milestone 12: Transparent `[Offline Heuristic]` CLI Labeling, Architecture Docs & ADR-0024 Certification
- **Node ID**: M12
- **depends_on**: ['M11']
- **consumes**: [{'contract': 'CoreTypeSafetyAuditDTO'}, {'contract': 'SemanticPomGraphDTO'}, {'contract': 'CertifiedNativeJsParityDTO'}]
- **produces**: [{'contract': 'ApexCertificationDTO'}]
- **Files Modified**: `tools/core/cli_specs.json`, `docs/ARCHITECTURE.md`, `docs/adr/ADR-0024-synapse-hub-apex-native-js-semantic-pom-strict-typing.md`
- **Write Set**: ['tools/core/cli_specs.json', 'docs/ARCHITECTURE.md', 'docs/adr/ADR-0024-synapse-hub-apex-native-js-semantic-pom-strict-typing.md']
- **Compute Tier**: [Model: Pro | Thinking: High]
- **Scope**: Prefix offline research simulation lab descriptions in `tools/core/cli_specs.json` with `[Offline Heuristic]` so CLI `--help` / `synapse lab --list` never overstates static heuristics as cloud LLM logprobs/SMT solvers; document the Native Node.js Linter fallback, Semantic POM Graph, 145-module strict typing, and Production vs Simulation boundary in `docs/ARCHITECTURE.md`; author `docs/adr/ADR-0024-synapse-hub-apex-native-js-semantic-pom-strict-typing.md` with full Red-Green-Mutation-Purple & 11/11 DoD certification receipts.
- **Circuit Breaker**: Max Fix Attempts = 2; halt if `cli_schema_sentinel.py --check --json`, `lint_ai_docs.py`, or `verify_all.py --mode hub --parallel` fails.
- **Rollback Hook**: `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['tools/core/cli_specs.json', 'docs/ARCHITECTURE.md'], created_files=['docs/adr/ADR-0024-synapse-hub-apex-native-js-semantic-pom-strict-typing.md'])"`

---

## 4. Verification Matrix

| Scenario | Target Subsystem | Command to Execute | Deterministic Expected Result |
| :--- | :--- | :--- | :--- |
| **Positive (Native JS Parity, Semantic POM & Zero-Ceremony Spoke)** | `bin/native-linter.js`, `pom_assertion_indexer`, `infer_linter`, `sync_agent_rules` | `pytest tests/test_native_js_python_parity.py tests/test_semantic_pom_inheritance_fixtures.py tests/test_zero_ceremony_client_profile.py tests/test_core_type_safety_and_win32_guards.py -v` | `100%` tests pass; JS vs Python defect codes match `1:1`; 3-level `extends` + `test.extend<Fixtures>` + barrel `index.ts` yield `0` false positives; `starter` client bridge is `< 35` lines with `0` Hub path leaks. |
| **Negative (Python-Less `PATH`, Cyclic `extends`, Colliding Fixtures)** | `bin/agent-qa.js` without Python, `class A extends B / B extends A`, non-asserting fixture | `pytest tests/test_native_js_python_parity.py tests/test_semantic_pom_inheritance_fixtures.py -k "negative" -v` | With Python stripped from `PATH`, `node bin/agent-qa.js lint` & `fix` & `doctor` exit `0` in `< 150ms`, while Python-only `mutate` exits non-zero with clear guidance; cyclic inheritance terminates without hang; non-asserting `{ stringUtil }` fixture triggers `FAKE_PASS_NO_ASSERTION`. |
| **Boundary (Windows `codeact_engine` Timeout, `mcp_excel_server` List Rows, Empty Inputs)** | `codeact_engine`, `mcp_excel_server`, `native-linter.js` | `pytest tests/test_core_type_safety_and_win32_guards.py tests/test_native_js_python_parity.py -k "boundary" -v` | Timeout kill works on Windows without `os.killpg` `AttributeError`; both `list[str]` and `dict[str, Any]` rows serialize cleanly in `mcp_excel_server`; `0`-byte and backtick-heavy TS files scan cleanly. |
| **Strict 145-Module `mypy`, Live Mutation >= 80% & Full 11-Gate Hub DoD** | All 6 core packages, `cli_schema_sentinel`, `micro_mutator`, `verify_all` | `python -m mypy tools/core tools/lint tools/context tools/mcp tools/alm tools/transpiler tools/runtime/codeact_engine.py tools/perf/benchmark_perf_runner.py` and `python tools/lint/cli_schema_sentinel.py --check --json` and `python tools/core/verify_all.py --mode hub --parallel` | `mypy` exits `0` (`0` errors across ~145 modules); `drift_count == 0`; dynamic mutation score `>= 80.0%` on modified core engines; all `11/11` Hub Quality Gates pass. |

---

## 5. Tri-Vulnerability Self-Critique (Red-Teaming)

1. **Divergence & Concurrency Race Between JS Native Engine and Python Linter (`race_condition`):**
   - *Vector:* Maintaining `bin/native-linter.js` alongside `tools/lint/infer_linter.py` risks rule drift over time, or concurrent `--fix` invocations corrupting target test files.
   - *Mitigation:* Lock an automated cross-runtime Parity Matrix (`tests/test_native_js_python_parity.py`) running both engines over identical polyglot fixtures in CI, and write `--fix` updates atomically per file only when mutated content differs from original source (`idempotent` on second pass).
2. **Cyclic Inheritance, Deep Barrel Exports & Resource Extremes (`boundary_resource`):**
   - *Vector:* Pathological TypeScript monorepos with circular `export * from ...` barrels, cyclic `class A extends B` declarations, or huge `node_modules` trees could cause unbounded recursion or slow `npx` startup beyond `150ms`.
   - *Mitigation:* Enforce visited-set cycle guards and hard caps (`max_inheritance_depth = 5`, `max_files = 2000`, strict `node_modules`/`.git`/`dist` directory pruning) in both `pom_assertion_indexer.py` and `bin/native-linter.js`, bounding memory and keeping P95 file scan latency `< 50ms`.
3. **Backward Compatibility & Downstream Caller Blast Radius (`backward_compat`):**
   - *Vector:* Tightening `mypy` across 145+ modules, adding `fixture_class_bindings` to `CrossFileAssertionMapDTO`, or introducing `--profile starter` client bridges could break existing callers, Hub `sync_agent_rules.py --check`, or Gate 11 checks.
   - *Mitigation:* Append new DTO fields with default factories (`field(default_factory=dict)`), keep default `sync_agent_rules.py` (Hub mode & `enterprise` client mode) byte-identical unless `--profile starter` is requested, preserve all 15 Gate 11 tiers while adding transparent `tier_classification` metadata, and leave `tools/core/author_integrity.py` 100% untouched.

---

## 6. Rollback & State-Migration Matrix

| Milestone | Failure Trigger | Compensating Action | Path-Scoped Rollback Command |
| :---: | :--- | :--- | :--- |
| `M1`–`M2` | JS/Python parity mismatch or `node` CLI regression | Restore `bin/agent-qa.js` and remove `bin/native-linter.js` + parity test | `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['bin/agent-qa.js'], created_files=['bin/native-linter.js', 'tests/test_native_js_python_parity.py'])"` |
| `M3` | Regression in POM assertion resolution or P95 > `50ms` | Restore `pom_assertion_indexer.py` & `infer_linter.py`; remove new test | `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['tools/context/pom_assertion_indexer.py', 'tools/lint/infer_linter.py'], created_files=['tests/test_semantic_pom_inheritance_fixtures.py'])"` |
| `M4`–`M9` | Any existing unit test breaks during strict type narrowing | Path-scoped `git restore` on affected batch of `<= 3` files | `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['tools/mcp/mcp_excel_server.py', 'tools/runtime/codeact_engine.py', 'tools/perf/benchmark_perf_runner.py', 'tools/lint/micro_mutator.py', 'tools/lint/mipro_assertion_tuner.py', 'tools/lint/pre_push_guard.py'])"` |
| `M10` | `sync_agent_rules.py --check` parity failure | Restore `init_config.py` and `sync_agent_rules.py`; remove profile test | `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['tools/core/init_config.py', 'tools/core/sync_agent_rules.py'], created_files=['tests/test_zero_ceremony_client_profile.py'])"` |
| `M11`–`M12` | Strict `mypy` error or Gate 4 / Gate 11 failure | Restore `pyproject.toml`, `gate_11_token_reduction.py`, `cli_specs.json`, `docs/ARCHITECTURE.md`; remove ADR-0024 & guard test | `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(declared_modify=['pyproject.toml', 'tools/core/gates/gate_11_token_reduction.py', 'tools/core/cli_specs.json', 'docs/ARCHITECTURE.md'], created_files=['tests/test_core_type_safety_and_win32_guards.py', 'docs/adr/ADR-0024-synapse-hub-apex-native-js-semantic-pom-strict-typing.md'])"` |

---

## Recommended Execution Model & Thinking Level

- **Primary Executor Model & Thinking Level (Single-Session Default):** `Gemini 4 Neon (High)` *(or `Gemini 4 Carbon (High)`)* running sequentially in a single session via `/solo` (`M1 -> M2 -> M3 -> M4 -> M5 -> M6 -> M7 -> M8 -> M9 -> M10 -> M11 -> M12`).
- **Milestone Escalation Overrides (Optional / `/teamwork` Only):** Under default `/solo`, all 12 milestones execute sequentially in one session on the Primary Executor with zero `swarm` workers. If `/teamwork` is explicitly invoked on disjoint branches, `M1`, `M3`, `M4`, `M5`, `M10`, and `M11` require `Neon (High)` for cross-runtime parity, inheritance/fixture graph resolution, and AST type narrowing, while `M2`, `M6`, `M7`, `M8`, `M9`, and `M12` can run on `Hydrogen (High)`.
- **Rationale:** Remediating 100 static type errors across 21 core files without breaking 2,600+ existing tests and building a zero-dependency Node.js fallback engine with 1:1 Python parity requires high-precision cross-file reasoning (`RiskScore = 0.92`).
