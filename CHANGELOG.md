# Changelog

All notable changes to **Synapse-Hub** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [4.8.0](https://github.com/TeeVee98/Synapse-Hub/compare/v4.7.0...v4.8.0) (2026-11-20)


### Features

* **architecture:** elevate synapse-hub with modular sdk, sub-8s fast gates, and som visual fallback ([3af585c](https://github.com/TeeVee98/Synapse-Hub/commit/3af585c248f1e957c8d2e3b9466a95e8df4833de))
* **architecture:** modularize tools into 13 canonical domain packages, prune contrib sprawl, and enforce git-scoped fast gates ([129423d](https://github.com/TeeVee98/Synapse-Hub/commit/129423d05d2f569fb9a0d42cce27557f2f3a69b9))
* **audit:** complete phase 3 & 4 consolidations, tool integrations and cli wiring ([4e55040](https://github.com/TeeVee98/Synapse-Hub/commit/4e55040eae0040b556085f327cb8b26434e792f5))
* **audit:** wire 40 standalone tools into cli, eliminate all orphan skills, and complete full audit remediation ([385b993](https://github.com/TeeVee98/Synapse-Hub/commit/385b993724d13e853a91e78e8b783a76963ac637))
* **autoupdate:** add Antigravity SessionStart lifecycle hook and silent auto-update engine ([78dbf95](https://github.com/TeeVee98/Synapse-Hub/commit/78dbf95d127386a0215906b2c40faca868767a7e))
* **cognitive:** integrate MIPROv2 prompt optimizer, cold-memory auto-hydration, and GoT deep expansion ([b7516df](https://github.com/TeeVee98/Synapse-Hub/commit/b7516df26f283dd1ff6a879c5de5fe200c361f94))
* **core:** elevate DX/UX to 100% and integrate enterprise manual QA capabilities ([ef99d27](https://github.com/TeeVee98/Synapse-Hub/commit/ef99d27c427655188addf2ae22e4707b62034ee2))
* **healing:** add live visual healer, session vault integration, and quarantine trace replay generator ([ab62808](https://github.com/TeeVee98/Synapse-Hub/commit/ab6280896aace601331c78078713c1ea7121a3ca))
* **hub:** 6-sprint QA automation suite - REST API, Web UI CRM, Security DAST, Performance tri-engine, Mobile SOM, CI/CD pipelines + full 10-gate audit remediation v4.7.0 ([fb818ea](https://github.com/TeeVee98/Synapse-Hub/commit/fb818ea72bfd1201148c17a9dd5d54da2ed83c4e))
* **hub:** upgrade to v4.3.0 with 56 skills, cypress rules, and enterprise QA gates ([3454238](https://github.com/TeeVee98/Synapse-Hub/commit/3454238104b3dcbd5d0f43d4c5077013e1924899))
* **manual-qa:** comprehensive manual QA upgrade v4.7.0 ([ff6235f](https://github.com/TeeVee98/Synapse-Hub/commit/ff6235f5dd354bc431b2e3f0e1a6404c61e16a0e))
* **manual-qa:** elevate manual QA to 100/100 zero-review trust with triple-filter gate and TMS exporters ([ca4887d](https://github.com/TeeVee98/Synapse-Hub/commit/ca4887de76e171f927a9de8adc3df63eb5b2212b))
* **niche-testing:** add tools & test suites for chaos, payment interop, mobile resilience, and observability (v4.4.0) ([b22dc6f](https://github.com/TeeVee98/Synapse-Hub/commit/b22dc6f8faee516ef08cf893f58ef3073f8577d0))
* **personas:** distill ECC testing heuristics into 9 core personas and prune unverified agent dump ([73076bb](https://github.com/TeeVee98/Synapse-Hub/commit/73076bb30a3316b902b4c9c0d9274b48a022aa3e))
* **phases-1-2-3:** implement SynapseFlow, SynapseMemory, SynapseGrid, and Federated Knowledge Lake ([a7c9b49](https://github.com/TeeVee98/Synapse-Hub/commit/a7c9b49cebfbc52f34d91635acee2daa5ae6a24a))
* **release:** synchronize remaining version targets and expand bump_version pipeline ([2960572](https://github.com/TeeVee98/Synapse-Hub/commit/2960572e59b71af8f239e8bd3e7d6149fdf4f286))
* **remediation:** complete Tier-S upgrade remediation across Phase 1, 2, and 3 ([eed9f29](https://github.com/TeeVee98/Synapse-Hub/commit/eed9f2936a1370b76dfff7cd3a2132c665e5c6b2))
* **rules:** sync Invariant 7 Skill-First Resolution across AGENTS.md and AI bridges ([99394c2](https://github.com/TeeVee98/Synapse-Hub/commit/99394c2e2f331df835946737cb954eb0323d8e22))
* **verify:** add adaptive ruff linting for target python projects in Gate 7 ([59df99a](https://github.com/TeeVee98/Synapse-Hub/commit/59df99addea30b30dff89c3dfd1b5ceb8fdda263))
* **verify:** integrate automated ruff linter check into Gate 7 ([9484c28](https://github.com/TeeVee98/Synapse-Hub/commit/9484c28f7711d4ff23ae8d9d7e37c68fb8c124ef))


### Bug Fixes

* **aut-api:** resolve book boundary min length test on live backend ([ab5405e](https://github.com/TeeVee98/Synapse-Hub/commit/ab5405e6755869c301803a56bac613ac2e1fd00f))
* **benchmarks:** resolve modular tool import paths in eval_runner for 100% benchmark pass ([09cf531](https://github.com/TeeVee98/Synapse-Hub/commit/09cf53168468354f075d5c23b716928c113a4b09))
* **ci:** add setuptools to lockfile, fix Windows venv paths, and restore NPM_TOKEN fallback ([573521a](https://github.com/TeeVee98/Synapse-Hub/commit/573521a3388bae012e6e8dcd37ecca8f40bf1626))
* **ci:** add wheel package to hermetic lockfiles for wheel packaging tests ([c1d5829](https://github.com/TeeVee98/Synapse-Hub/commit/c1d5829c42204d1247bfa6c60c937a05a75e28fc))
* **ci:** eliminate sdist staging race conditions on parallel runners and streamline root hygiene ([04d4b7b](https://github.com/TeeVee98/Synapse-Hub/commit/04d4b7b6f3a2aecbbc5b82e5f633e679dd3a2a2d))
* **ci:** fix mypy type inference on session mtime in pre_push_guard ([51aebf2](https://github.com/TeeVee98/Synapse-Hub/commit/51aebf2b073d51f94a8d93886e5e662e417117a4))
* **ci:** harden Windows cross-platform runner against socket reset and file locking ([8c41e7e](https://github.com/TeeVee98/Synapse-Hub/commit/8c41e7eb89af7c371f30ec35cee4e8e9cb5c36fa))
* **ci:** increase wheel build file lock timeout to 60s for slow runners ([c12d9b6](https://github.com/TeeVee98/Synapse-Hub/commit/c12d9b6f31b073d51c117fdb691520def80460f9))
* **ci:** resolve Playwright CI headless check, VSCE OIDC flag, and Windows binary encoding ([38830f4](https://github.com/TeeVee98/Synapse-Hub/commit/38830f43ae99b0a55de5188dc495742bb759ddbd))
* **ci:** resolve ruff linting errors and add build package to lockfiles ([56186da](https://github.com/TeeVee98/Synapse-Hub/commit/56186daf3cbb6f8fdf2cb471a29e5e65d077ec05))
* **ci:** resolve windows set_blocking compatibility and grid watchdog race condition ([a860bc1](https://github.com/TeeVee98/Synapse-Hub/commit/a860bc1995843c4c4ce2825bf7bc64ba3ba74c4f))
* **ci:** update modular tool paths in GitHub Actions workflows ([212f71d](https://github.com/TeeVee98/Synapse-Hub/commit/212f71db6eb7bf2d8c60c79da2d79534b29ab3f6))
* **core:** remediate false-passes, checkpoint succession, watchdog hang, and FTS5 indexing v4.6.1 ([25d5571](https://github.com/TeeVee98/Synapse-Hub/commit/25d55717f8b6e3a2e52275b3f7baf27e5cd07eb7))
* **core:** remediate Phase 1 & Phase 2 audit findings on runtime crashes, rules, and agent scoping ([5d7184f](https://github.com/TeeVee98/Synapse-Hub/commit/5d7184f083f3691c3829d72a7b6651a7f2c711ba))
* **core:** resolve audit v4.2.3 findings and bump to v4.2.4 ([81efb52](https://github.com/TeeVee98/Synapse-Hub/commit/81efb52e2a6ff3bea3d36ffced7ab88db8ea9ea8))
* **packaging:** make Pillow import lazy in visual_diff_canvas and prune unverified curated-ecc dump ([121212b](https://github.com/TeeVee98/Synapse-Hub/commit/121212ba64fdd5ffc7c4bcf062f24b155e40bc7d))
* **packaging:** restore 14 rules standard, synchronize token benchmark, and update router perf cap ([e229dfd](https://github.com/TeeVee98/Synapse-Hub/commit/e229dfd08dc0db4f15db08a4a88848b2e1d91f91))
* **repo_map:** synchronize output to tools/repo_map.txt for audit suite compatibility ([e7f2e0f](https://github.com/TeeVee98/Synapse-Hub/commit/e7f2e0fc18939fed02117661c46833467a67a949))
* **tests:** make MCP and Synapse package version assertions dynamic ([70a0a36](https://github.com/TeeVee98/Synapse-Hub/commit/70a0a36957d3c390ac301a23fa453673a04a8cb1))
* **validator:** skip runtime output directories like graphify-out in backtick path validation ([eb1c313](https://github.com/TeeVee98/Synapse-Hub/commit/eb1c313e4e61e53fb7c5d4bdad8155cb11e3e1bc))
* **verify:** eliminate swallowed OSError in has_python_sources to satisfy infer linter ([117c118](https://github.com/TeeVee98/Synapse-Hub/commit/117c118ed89e4c42209bee3bba1748c521571ce3))


### Performance Improvements

* **context:** optimize customization tokens via on-demand triggers and metadata distillation (v4.2.5) ([fd4be4a](https://github.com/TeeVee98/Synapse-Hub/commit/fd4be4a25dbf5091bb9cd0c8468d11711ed4bca6))
* **optimization:** implement token optimization spec v4.4.0 with 2-tier catalogs and scoped rules ([78f2077](https://github.com/TeeVee98/Synapse-Hub/commit/78f2077cee61284a6ab6e946abec6a21ca964e59))
* **verify:** optimize has_python_sources to O(1) candidate scan and pruned walk ([b43e5a7](https://github.com/TeeVee98/Synapse-Hub/commit/b43e5a715b78175c1cc5173ac71357e2ab6b3194))

## [4.7.0] - 2026-11-20

## [4.7.0] - 2026-11-20

### Added
- **Manual QA Cursor Rule (`.cursor/rules/manual-qa.mdc`)**: 6 core rules dedicated to Manual QA, ISO/IEC/IEEE 29119-3 standards, zero-speculative language enforcement, pre-delivery linting, on-demand checklist querying, and mandatory practical edge cases (whitespace trim baseline & payment redirect resilience).
- **`manual-qa` Profile in `skills_manifest.json`**: Standardized profile for manual testing workflows (`review-spec`, `rbt-manual-testing`, `gherkin-to-suite`, `tot-exploratory-testing`, `manual-qa-and-rtm-bridge`) while preserving backwards compatibility for `enterprise-rbt`.
- **On-Demand 0-Token Checklist Query Tool (`tools/manual/checklist_query.py`)**: Stdlib-only query engine for `field_validation_checklist.md` supporting 25 field types and 8 invariants (including `payment-ui-latency`) with `--list`, `--fields`, `--invariants`, and `--format` flags; registered via CLI subcommand `checklist`.
- **Context-Aware Linter Profiles & Semantic Rules in `tools/lint/manual_tc_linter.py`**: Added `--profile` (`default`, `crud`, `auth-payment`, `api-integration`, `ui-readonly`), inline comment support (`<!-- synapse-linter-profile: ... -->`), and mandatory semantic rules S1-S3 with `--strict-semantic` flag.
- **ISO/IEC/IEEE 29119-3 Exit Report & SBTM Charter**: Extended `testing/manual/manual-qa-and-rtm-bridge/SKILL.md` with Section 5 (Execution Summary, Defect Breakdown, DRE/leakage metrics, Residual Risks, Sign-off matrix) and Section 6 (SBTM Charter Sheet with task breakdown percentages and debrief records).
- **BRD Mode in Specification Reviewer (`tools/orchestration/goldfish_review.py`)**: Added `--mode brd` re-weighting vectors to Comprehension (25%), Business Rules (25%), Assertion Rigor (25%), and Boundary Coverage (25%), exempting teardown hooks and DOM PageClass/selector requirements for business requirements.
- **Invariant 8 & Whitespace Baseline in `field_validation_checklist.md`**: Added `payment-ui-latency` covering Slow Network double-click, browser interrupt during payment redirect, session TTL, and explicit whitespace & trim() baselines across text inputs.
- **Shift-Left Inquiries in `requirement/workflows/analyze_requirement_document.md`**: Added default Q&A register inquiries for Whitespace & Trim policy and Payment UI Latency & redirect interrupts.
- **Katalon Architecture Separation**: Extracted Katalon Studio reference guide (`automation/shared-utils/clean-pom-crafter/references/katalon_pom.md`) and Angular/PrimeNG preset (`references/angular_primeng_preset.md`), establishing framework-agnostic universal Clean POM.

### Changed
- **Scope Isolation for Automation Invariants**: Clarified Clean POM and Smart Waits rules in `AGENTS.md`, `.cursor/rules/agents.mdc`, and AI bridges as applying to automation code only and exempting Manual QA markdown specs.
- **Canonical Lockfile Dual-Parity**: Maintained byte-for-byte dual parity between `skills-lock.json` (canonical) and `.skill-lock.json` (compatibility mirror) with synchronized canonical SHA-256 digests.
- **Audit Remediation (Groups A, B, C)**: Fully reconciled tool paths across documentation, refined Skill-First Hard Blocker with Inquiry exemption, expanded k6 globs, standardized 6-tier locator hierarchy, and eliminated machine-specific absolute paths.

## [4.6.5] - 2026-11-20

### Changed
- Maintenance & version release v4.6.5.

## [4.6.4] - 2026-11-19

### Changed
- Maintenance & version release v4.6.4.

## [4.6.3] - 2026-11-19

### Changed
- Maintenance & version release v4.6.3.

## [4.6.2] - 2026-11-19

### Changed
- Maintenance & version release v4.6.2.

## [4.6.1] - 2026-11-19

### Changed
- Maintenance & version release v4.6.1.

## [4.6.0] - 2026-11-19

### Changed
- Maintenance & version release v4.6.0.

## [4.5.1] - 2026-11-19

### Changed
- Maintenance & version release v4.5.1.

## [4.5.0] - 2026-11-17

### Changed
- Maintenance & version release v4.5.0.

## [4.4.3] - 2026-11-17

### Changed
- Maintenance & version release v4.4.3.

## [4.4.2] - 2026-11-17

### Changed
- Maintenance & version release v4.4.2.

## [4.4.1] - 2026-11-17

### Changed
- Maintenance & version release v4.4.1.

## [4.4.0] - 2026-11-17

### Changed
- Maintenance & version release v4.4.0.

## [4.3.1] - 2026-11-17

### Changed
- Maintenance & version release v4.3.1.

## [4.3.0] - 2026-11-16

### Changed
- Maintenance & version release v4.3.0.

## [4.2.5] - 2026-11-16

### Changed
- Maintenance & version release v4.2.5.

## [4.2.4] - 2026-11-16

### Changed
- Maintenance & version release v4.2.4.

## [4.2.3] - 2026-11-16

### Fixed
- **CI Parallel Runner Race Conditions:** Eliminated transient sdist build collision on parallel runners in `tools/verify_all.py`, `scripts/package_dist.py`, and `tools/package_release.py` by excluding `*.egg-info` and `synapse_hub-*` staging trees.
- **Repository Hygiene & File Nesting:** Streamlined root filesystem by relocating community docs to `.github/` and enabling IDE file nesting via `.vscode/settings.json`.

## [4.2.2] - 2026-11-16

### Changed
- Maintenance & version release v4.2.2.

## [4.2.1] - 2026-11-15

### Changed
- Maintenance & version release v4.2.1.

## [4.2.0] - 2026-11-15

### Changed
- Maintenance & version release v4.2.0.

## [Unreleased]

## [4.1.5] - 2026-11-15

### Added
- **Release Packaging Parity & Distribution Resources:** Added full routing and hydration support to Python wheel (`.whl`), packaging `.agents` skills, rules, agents, workflows, and `skills_manifest.json` with 100% parity to npm tarball.
- **Dynamic CLI Registry & Command List:** Implemented `get_registered_commands()` introspecting registered subparsers directly from registry; added `agent-qa help --json` and `agent-qa help --markdown` for dynamic command documentation; eliminated brittle static test counts and command counts.
- **Direct CLI & API Consent Boundaries:** Mandated `--confirm` flag (or `SYNAPSE_FORCE_PURGE=1`) for destructive database purge in `tools/db_sandbox.py audit --apply`, enforced explicit consent validation in `ApiFuzzer.execute_request(..., dry_run=False)` prior to socket dispatch, and implemented socket-level IP binding against DNS rebinding / TOCTOU.
- **Canonical Skill Folder Content Digest:** Unified canonical SHA-256 tree hashing in `tools/skill_canonical_digest.py` across generator, validator, and CI, ensuring byte-level deterministic locking without in-place modification during verification.
- **Unclassified Workspace Task Routing & Token Floor:** Preserved task-specific primary skills and task rules when `task_type` is explicitly specified on unclassified workspaces, with structured `TokenCapExceededError` on boundary starvations and content-digest cache invalidation.
- **Scientific Token Engineering & Clean Benchmark Reporting:** Standardized measurement taxonomy (`static_estimate`, `synthetic`, `provider_reported_input_tokens`, `provider_reported_output_tokens`), clean JSON benchmark stdout, and `ProviderUsageAdapter`.
- **Quality Metrics & CI Semantics:** Separated Line Coverage (>= 60.00%) and Branch Coverage (>= 50.00%), Gate 8 valid mutant denominator without counting timeouts as killed or giving fake 100% on empty mutants, and Gate 10 SLA performance provenance metadata with staleness detection.
- **Ecosystem Evidence & Multi-Host Interoperability Sentinel:** Validated 53 skills under pinned Agent Skills reference schema with progressive disclosure, verified 7 host agent platforms with concrete runtime discovery evidence, expanded QC/QA benchmark to 45 challenges across 11 failure domains with paired comparison, and eliminated ungrounded superlative ranking claims.

### Fixed
- **Cross-Platform UTF-8 Stdio & Path Handling:** Configured UTF-8 encoding across stdout/stderr streams and resolved Windows path separators and temporary directory handling in `tools/mcp_server.py`, `tools/validate_skills_schema.py`, and `tests/test_packaging_parity.py`.

## [4.1.4] - 2026-11-14

### Added
- **Attribution & License Integrity Guard:** Mandated full MIT license headers and author attribution (`Thế Vị (@TeeVee98)`) across 178 codebase files.
- **Enterprise Audit Report:** Published `AUDIT_REPORT.md` providing comprehensive root cause analyses and remediation matrices across P0-P2 findings.
- **Dynamic Token Baseline Enumeration:** Automated dynamic enumeration of all 53 skills and 13 rules in `tools/core/token_estimator.py` without hardcoded static multipliers.
- **Out-of-Scope Isolation Invariant:** Formalized protocol in `AGENTS.md` and `.agents/rules/systematic-debugging.md` forbidding ad-hoc modifications or dummy bypasses on unrelated files when verification fails.
- **Hardened Anti-Fake-Pass Sentinel (Gate 7):** Upgraded `tools/infer_linter.py` to detect and block dummy exception suppressions (`_ = err`, `_ = False`, `const _ = e;`) across Python, TypeScript, and Groovy test suites.

## [4.1.3] - 2026-11-14

### Added
- **Hard-Capped Token Budget Invariant:** Enforced strict mathematical hard cap (`count_tokens(output) <= token_budget`) across all budget tiers in `tools/distill_log.py`, reserving metadata envelopes and handling low-budget fallbacks (`BUDGET_BELOW_MINIMUM`).
- **Synchronized Exact BPE Token Benchmark:** Resolved CLI path resolution discrepancy in `tools/benchmark_swarm_context.py`, synchronizing Track 1 (2,396 -> 423 tokens, 82.35%) and Track 2 empirical measurements to match native `cl100k_base` execution down to single tokens.
- **Benchmark Drift Sentinel:** Implemented regression test `test_benchmark_report_drift_sentinel` in `tests/test_benchmark_context.py` ensuring committed documentation matches live runner execution.
- **Explicit Tokenizer Scope Disclosure:** Documented `cl100k_base` BPE scope and engine metadata across benchmark reports and CLI outputs.

## [4.1.2] - 2026-11-14

### Added
- **Hardened Anti-Fake-Pass Sentinel (Gate 7):** Upgraded `tools/infer_linter.py` to detect and block dummy exception suppressions (`_ = err`, `_ = False`, `const _ = e;`) across Python, TypeScript, and Groovy test suites.
- **Out-of-Scope Isolation & Stop-and-Report Invariant:** Formalized behavioral protocol in `AGENTS.md` and `.agents/rules/systematic-debugging.md` forbidding ad-hoc modifications or workarounds on unrelated files when verification fails.
- **Legacy Debt Baseline:** Generated `tools/.infer_baseline.json` freezing existing internal tool debt to enforce diff-aware strict verification on new code.
- **Log Distiller Conflicting Signals Detection:** Flagged runner exit code 0 paired with failure traces as `⚠️ CONFLICTING_SIGNALS` in `tools/distill_log.py`.
- **Dynamic Token Baseline Enumeration:** Automated dynamic enumeration of all 53 skills and 13 rules in `tools/core/token_estimator.py` without hardcoded static multipliers.

## [4.1.1] - 2026-11-13

### Changed
- Synchronized metric parameters, tool counts (121 internal tools), test counts (880+ passing), and 10 Quality Gates DoD across all bilingual markdown documentation and README files.
- Regenerated AST tool catalog (`docs/TOOL_CATALOG.md` and `tools/TOOL_CATALOG.json`) indexing all 121 enterprise CLI and auxiliary tools.
- Updated version references across VS Code extension documentation, downstream Spoke pinning guides, and architecture specifications.

## [4.1.0] - 2026-11-13

### Changed
- Maintenance & version release v4.1.0.

## [4.0.0] - 2026-11-13

### Changed
- Maintenance & version release v4.0.0.

## [3.10.0] - 2026-11-13

### Changed
- Maintenance & version release v3.10.0.

## [3.9.1] - 2026-11-13

### Changed
- Maintenance & version release v3.9.1.

## [3.9.0] - 2026-11-13

### Changed
- Maintenance & version release v3.9.0.

## [3.8.5] - 2026-11-12

### Changed
- Maintenance & version release v3.8.5.

## [3.8.4] - 2026-11-12

### Changed
- Maintenance & version release v3.8.4.

## [3.8.3] - 2026-11-12

### Changed
- Maintenance & version release v3.8.3.

## [3.8.2] - 2026-11-12

### Changed
- Maintenance & version release v3.8.2.

## [3.8.1] - 2026-11-12

### Changed
- Maintenance & version release v3.8.1.

## [3.8.0] - 2026-11-12

### Changed
- Maintenance & version release v3.8.0.

## [3.7.2] - 2026-11-09

### Changed
- Maintenance & version release v3.7.2.

## [3.7.1] - 2026-11-09

### Changed
- Maintenance & version release v3.7.1.

## [3.7.0] - 2026-11-09

### Changed
- Maintenance & version release v3.7.0.

## [Unreleased]

### Added
- **Dedicated API & Contract Engineer Subagent (`api-engineer`)**: Introduced 9th specialized subagent profile dedicated to OpenAPI 3.x matrices, Pact Consumer-Driven Contract (CDC) testing, schema drift detection, Newman CLI execution, and network route mocking (`.agents/agents/api-engineer.md`). Completely decoupled API test creation from `pom-crafter` and API CLI runs from `test-runner`.
- **Complete Decoupling of 9 Subagents & Tools**: Strictly segmented subagent roles and tooling across the 4 Pillars of QA Intelligence (Manual $\rightarrow$ `test-designer`, Web UI $\rightarrow$ `pom-crafter`, API $\rightarrow$ `api-engineer`, Functional Execution $\rightarrow$ `test-runner`, Performance $\rightarrow$ `perf-engineer`, Autopsy $\rightarrow$ `failure-analyst`, Gatekeeping $\rightarrow$ `quality-gatekeeper`, Probing $\rightarrow$ `live-explorer`, Lead $\rightarrow$ `orchestrator`).
- **Dedicated Test Designer & Manual QA Subagent (`test-designer`)**: Introduced 8th specialized subagent profile dedicated to requirement ambiguity audits, AI-RBT risk matrices, 15-field validation checklists, and 12-column Excel test suite generation (`.agents/agents/test-designer.md`). Decoupled manual testing from `pom-crafter`.
- **Dedicated Performance Engineer Subagent (`perf-engineer`)**: Introduced 7th specialized subagent profile orchestrating JMeter, k6, Locust load profiles, real-time telemetry streaming, and APM bottleneck correlation (`.agents/agents/perf-engineer.md`).
- **FSM Integration**: Registered `test-designer` as an authorized discovery actor in FSM Stage 1 `DISCOVERY`, `api-engineer` in Stage 2 `CODE_SYNTHESIS` and Stage 3 `HEADLESS_EXEC`, and `perf-engineer` in Stage 3 `HEADLESS_EXEC` (`tools/fsm_enforcer.py`).
- **Tool Catalog Ownership**: Assigned dedicated tool ownership across all 9 subagents (`tools/generate_tool_catalog.py`), eliminating cross-agent role overloading.
- **Ecosystem Showcase Updates**: Synchronized `README.md`, `README.en.md`, `templates/welcome.html.tmpl`, `reports/WELCOME.html`, `tools/dashboard_generator.py`, and `reports/PROJECT_DASHBOARD.html` to showcase all 9 specialized subagent profiles.

## [3.6.0] - 2026-11-09

### Changed
- Maintenance & version release v3.6.0.

## [3.5.1] - 2026-11-09

### Changed
- Maintenance & version release v3.5.1.

## [3.5.0] - 2026-11-09

### Changed
- Maintenance & version release v3.5.0.

## [3.4.0] - 2026-11-09

### Changed
- Maintenance & version release v3.4.0.

## [3.3.0] - 2026-11-08

### Changed
- Maintenance & version release v3.3.0.

## [3.2.4] - 2026-11-08

### Changed
- Universal version bump to v3.2.4 across all 18 polyglot manifests, configs, and tool entrypoints.
- Integrated `tools/ui_server.py` into atomic version bumper (`tools/bump_version.py`).

### Security & Hardening
- Complete verification of 10 DoD Quality Gates and zero critical defects across active test suites.
- Production-grade package distribution integrity and cross-platform runtime guarantees.

## [3.2.3] - 2026-11-06

### Added
- Interactive QA Mission Control Web UI dashboard (`tools/ui_server.py`).
- Jira TMS Synchronization Bridge (`tools/tms_sync_bridge.py`).
- Quality Trends Analytics engine (`tools/trend_analytics.py`).
- Docker all-in-one container image & compose orchestration.
- VS Code Extension integration (`editors/vscode`).
- Bilingual CLI internationalization engine (`tools/core/i18n.py`).

### Security
- Fixed Path Traversal vulnerability on Mission Control `/reports/` endpoint.
- Restricted CORS headers to localhost/127.0.0.1 origins with spoofing prevention.
- Enforced Hub-Spoke workspace isolation to eliminate client data leakage into Hub root.

### Fixed
- Added `--target` argument support to project bootstrap CLI (`tools/setup_project.py`).
- Fixed silent pass vulnerability in generated Git pre-push hook.
- Added strict `NO_COLOR`, `TERM=dumb`, and `isatty` compliance suppressing ANSI escapes.
- Excluded `.lock` files from npm package distribution (`package.json`).
- Synchronized documentation skill count to 53 standardized QA skills.

## [3.2.2] - 2026-11-06

### Changed
- Maintenance & version release v3.2.2.

## [3.2.1] - 2026-11-06

### Changed
- Maintenance & version release v3.2.1.

## [3.2.0] - 2026-11-05

### Changed
- Maintenance & version release v3.2.0.

## [3.1.2] - 2026-11-05

### Changed
- Maintenance & version release v3.1.2.

## [3.1.1] - 2026-11-05

### Changed
- Maintenance & version release v3.1.1.

## [3.1.0] - 2026-11-05

### Added
- **Cognitive Observer & Tradeoff Sentinel (`tools/synapse_observer.py`):** Anthropic Claude Code observer pattern with high-bar tradeoff detection, anti-nagging memory, file-aware diff parsing, and inner-whitespace sleep detection.
- **Anti-AI Slop & Tone Linter (`tools/humanize_linter.py`):** Lints and swaps 53 AI buzzwords, 16 cliches, and em-dash misuse with CommonMark stateful code fence and inline backtick masking.
- **Enterprise Security Coverage Ledger (`tools/security_coverage_ledger.py`):** Cloudflare mathematical coverage ledger (Surface × Boundary × Subsystem × Attack Class) with RFC 3986 percent-encoding and 19-field schema in Python 3.
- **AI & Multi-Agent Security Hunting Guides:** Added `references/AI-AND-LLM.md` and `references/ATTACK-CLASSES.md` to `security-dast-sentinel`.
- **Anti-Junk Test Protocol:** 4-question Authoring Gate and junk pattern blacklist integrated into `clean-pom-crafter` and `senior-code-review`.
- **Markdown Export:** Added `--output-md` / `-o` export functionality to `tools/senior_code_review.py`.

## [3.0.1] - 2026-11-04

### Fixed
- **Security (MCP Path Traversal):** Enforced `_validate_safe_path()` on `tools/mcp_server.py` endpoints (`_handle_resolve_visual_som_coordinates`, `_handle_compile_gherkin_suite`, `_handle_report_alm_defect`) to prevent directory traversal and arbitrary file reads.
- **Security (SQL Injection):** Sanitized transaction savepoint identifiers in `tools/db_sandbox.py` with alphanumeric regex.
- **Reliability (DB Sandbox):** Replaced hardcoded `users` table query in `tools/db_sandbox.py` with dynamic schema table inspection.
- **Reliability (Process Timeouts):** Added explicit 30s-120s execution timeouts to `subprocess.run` calls in `reversible_sandbox.py`, `senior_code_review.py`, `test_impact.py`, `generate_allure_report.py`, and `bump_version.py`.
- **Git Hygiene:** Replaced broad `git add -A` with tracked-only staging `git add -u` in `tools/bump_version.py` to guard untracked scratch files.
- **Performance:** Added vendor and artifact exclusions (`claude-ecosystem-repos`, `graphify-out`, `.synapse`, `reports`) to `tools/skillspector.py` `SKIP_DIRS`, slashing scan times to ~2s.
- **Documentation:** Fixed script reference in `docs/research/agent_skill_training_analysis.md` to point to `tools/textgrad_mutation_optimizer.py`.

## [3.0.0] - 2026-11-04

### Changed
- Maintenance & version release v3.0.0.

## [2.9.0] - 2026-11-04

### Changed
- Maintenance & version release v2.9.0.

## [2.7.0] - 2026-11-04

### Added
- **Comprehensive Project Audit & Remediation Deliverable (`PROJECT_AUDIT_REPORT.md`):** Complete survey of 51 skills, 101 tool scripts, operational rules, and agent personas with zero unhandled defects.
- **9 New Autonomous Agent Skills (Catalog expanded to 51 skills):**
  - `actor-qa-swarm`: Asynchronous Actor Model message broker and matrix sharding coordinator.
  - `agentless-qa-repair`: Agentless 3-phase automated repair flow (localization, synthesis, minimal diff).
  - `event-stream-qa-orchestrator`: SHA-256 hash-chained deterministic action/observation timeline.
  - `mipro-prompt-compiler`: MIPROv2 Bayesian teleprompter optimizer against AST mutation kill scores.
  - `qa-aci-interface`: Safe Agent-Computer Interface for 40-50 line code windows and surgical edits.
  - `qa-memory-os`: 3-tier hierarchical memory OS (Core blocks, Recall step logs, Archival semantic store).
  - `review-spec`: Stateless zero-context Elephant-Goldfish specification stress-testing engine (`goldfish_review.py`).
  - `tot-exploratory-testing`: Tree-of-Thoughts exploratory testing engine with Beam Search risk scoring.
  - `web-agent-gym-benchmarking`: Empirical benchmark harness for web agents and Page Classes (<200ms latency budget).
- **Shared OpenAPI Specification Parser (`tools/_openapi_parser.py`):** Unified schema loader, `$ref` resolver, endpoint extractor, and boundary scenario synthesizer across API testing tools.

### Fixed
- **4 CLI Runtime Defects Resolved:**
  - `tools/pinpoint_failure.py`: Enforced UTF-8 stdout/stderr encoding on Windows consoles (`cp1252`), added standard `-h`/`--help` flag.
  - `tools/project_state.py`: Intercepted `--help` flag to prevent directory-creation collisions (`--help\PROJECT_STATE.md`).
  - `tools/db_sandbox.py`: Added zero-argument command guard to print help cleanly instead of raising `AttributeError`.
  - `tools/reversible_sandbox.py`: Implemented missing `stack_size()` method on `ExecutionSandbox`.
- **Legacy Path Prefixes Cleaned:** Sanitized 15 occurrences of `~/.zcode` across 6 skill manifests to portable relative invocations.
- **Decoupled Proprietary Page Classes:** Replaced hardcoded project classes in `triage_failures.sh` with dynamic AST lookup via `tools/repo_map.txt`.
- **Output Hygiene:** Fixed `api-spec-to-e2e-matrix` output target from `tools/` to `reports/`.

### Changed
- **Rule & Swarm Harmonization:** Decoupled `quality-gatekeeper` (Stage 5 Air-Gap Sentinel) from `failure-analyst` in `.agents/rules/mandatory-playwright-live.md`, removed phantom documentation persona, and generalized polyglot test runners.
- **Git Push Protocol Alignment:** Eliminated automated git push instructions from `PROJECT_HEALTH_REPORT.md` and `tools/TOOLS_RUNBOOK.md`, enforcing explicit two-step user confirmation protocol.
- **10 Quality Gates Standardized:** Integrated Author attribution pre-flight, Gate 8 (Mutation score), and Gate 9 (Skill collision guard) into `tools/analyze_project.py` and across all bridge configurations.
- **Mobile Appium Formalized:** Marked `.agents/rules/mobile_appium_rules.md` as an on-demand enterprise extension module.
- **Tool & Skill Consolidations:** Unified `--reflexion` flag into `tools/auto_heal.py` and `--ci-hook` into `tools/heal_pr_automator.py`.

## [2.6.2] - 2026-11-04

### Changed
- Maintenance & version release v2.6.2.

## [2.6.1] - 2026-11-04

### Changed
- Maintenance & version release v2.6.1.

## [2.6.0] - 2026-11-04

### Added
- **8 Autonomous AI/QA Tools:**
  - `auto_heal_reflexion.py`: Noah Shinn Reflexion loop (K=3) for iterative test failure healing.
  - `textgrad_mutation_optimizer.py`: TextGrad mutation loss optimizer for strengthening assertions.
  - `reversible_sandbox.py`: LIFO undo rollback stack for safe mutations.
  - `skill_vault.py`: Lifelong library for verified Clean POM interaction primitives.
  - `interview_story.py`: Systematic requirement grilling for ambiguous user stories.
  - `dspy_qa_signatures.py`: Stanford DSPy typed signatures for QA pipelines.
  - `synapse_qa_bench.py`: Function calling and tool-use evaluation benchmark.
  - `skill_collision_guard.py`: Semantic collision detection across skill triggers.
- **New Standard Specification (`agentskills.json`):** Formal AI agent skill ecosystem manifest.
- **Integration Test Suite:** P0, P1, P2 integration tests validating multi-turn tool calling and end-to-end deliverables.

### Changed
- **Rules Token Footprint Optimization:** Streamlined 5 core rule files (`systematic-debugging.md`, `context-engineering.md`, `skill-precedence.md`, `mobile_appium_rules.md`, `performance_testing_rules.md`) saving ~5,400 tokens (34% payload reduction) while preserving 100% of invariants.
- **Central Memory Sync:** Synchronized `AGENTS.md` and rule definitions to global Antigravity plugin.

---

## [2.5.0] - 2026-11-03

### Added
- **Lean Senior Dev & Ponytail Integration:** Ported core capabilities from Ponytail v5.3 into Synapse-Hub, implementing the 7-Rung Ladder (`lean-code-ladder`), `shortcut:` comment tracking, and anti-bloat principles.
- **4 New Standardized Skills (Catalog expanded 38 -> 42):**
  - `senior-code-review`: 6-pillar code review engine (Bugs, Security, Scale, Tests, Speed, Bloat).
  - `repo-quality-audit`: Whole-codebase quality audit with "Fix this first" prioritization.
  - `technical-debt-harvester`: Harvests and tracks `shortcut:` markers across repos into structured ledgers.
  - `lean-impact-scoreboard`: Empirical benchmarking scoreboard measuring code, token, and time reductions.
- **2 New CLI Tools & Commands (Subcommands expanded 51 -> 53):**
  - `agent-qa debt` (`tools/debt_harvester.py`): Scans and reports technical debt markers across polyglot comments.
  - `agent-qa review` (`tools/senior_code_review.py`): Automated 6-pillar Git diff inspection.
- **Claude Code Slash Commands:** 12 modular slash commands in `commands/` (`synapse-*` and `ponytail-*`).

### Changed
- **Optimized `AGENTS.md` Context Footprint:** Compacted root rule specification from ~3.8k tokens down to ~1.2k tokens (68% token reduction) while preserving 100% of core QA invariants and integrating the 7-Rung Ladder.
- **Markdown Rules & Agent Ecosystem Audit:** Standardized and synchronized all 5 Markdown tiers (Root Bridges, Core Rules, Swarm Agents, Skills, and Tool Runbooks).
- **Subagent Capabilities Expansion:** Granted `senior-code-review` and `technical-debt-harvester` to `quality-gatekeeper`, and `repo-quality-audit` to `orchestrator`.
- **Tools Runbook & CLI Reference:** Sequenced tool numbering 0–31 in `TOOLS_RUNBOOK.md` and added full CLI reference documentation for `debt` and `review`.

---

## [2.4.3] - 2026-11-03

### Fixed
- **NPM Trusted Publishing (OIDC) (`publish_npm.yml`):** Removed conflicting `NODE_AUTH_TOKEN` and pre-configured `.npmrc` to allow tokenless authentication via GitHub Actions OIDC Trusted Publishing.
- **Unit test runner output (`test_author_integrity.py`):** Captured stdout/stderr in intentional missing-license test to eliminate confusing error banners during test runs.
- **Global Plugin Installation (`setup_project.py`, `update_sentinel.py`):** Added automatic sync of `LICENSE` and `NOTICE` to `~/.gemini/config/plugins/synapse-hub`.
- **Environment Doctor (`check_env.py`):** Added standalone host environment detection and polyglot framework support (Playwright, Cypress, Pytest, Katalon).

---

## [2.4.2] - 2026-11-03

### Fixed
- **Python 3.9–3.11 f-string compatibility (`output_formatter.py`):** Extracted ANSI escapes to class constants, removing backslashes from inside f-string expressions.
- **GitHub Composite Action security (`action.yml`):** Replaced direct string interpolation in shell script with safe `env:` variables and Bash array quoting (`"${ARGS[@]}"`) to eliminate injection risks.
- **MCP Server Path Traversal (`mcp_server.py`):** Enforced `_validate_safe_path` on `spec_path` argument in `fuzz_api` handler.
- **Dynamic Version Assertions (`tests/test_borrow_wave2.py`, `tests/test_mcp_excel_server.py`):** Replaced hardcoded version strings with dynamic regex and `SERVER_VERSION` attribute constants.
- **Optional dependencies in tests (`test_tools.py`):** Added dynamic `skipUnless` guard on `test_md_to_xlsx_conversion` when `openpyxl` is not present.
- **Documentation & Catalog Sync:** Corrected heading sequence in `docs/ARCHITECTURE.md`, supplied `docs/schemas/synapse.config.schema.json`.

### Added
- **AI Agent Rules Sync CI Check (`validate_skills.yml`):** Added automated verification step checking `AGENTS.md` against IDE bridge files.
- **Host-Scoped API Fuzzing (`api_fuzzer.py`):** Added `SYNAPSE_ALLOW_PROD_HOSTS` to support host-specific allowlisting instead of global bypass.
- **Pure Stdlib Runtime Decoupling (`requirements.txt`, `requirements-extras.txt`):** Decoupled optional dependencies `Pillow` and `openpyxl` into extras.
- **Nomenclature & Package Architecture Guide (`docs/ARCHITECTURE.md`):** Documented component naming conventions across NPM, PyPI, and MCP registries.

---

## [2.4.1] - 2026-11-02

### Added
- **27 Golden Unit Tests (Coverage Expanded to 201 Tests):**
  - `tests/test_spec_drift_sentinel.py` (8 tests): Validates spec criteria extraction, code assertion matching, and Deficit/Scope drift calculation.
  - `tests/test_goldfish_review.py` (6 tests): Validates 5-vector zero-context spec audit, vague assertion penalties, and dynamic data enforcement.
  - `tests/test_mcp_excel_server.py` (6 tests): Validates JSON-RPC 2.0 stdio server, `list_excel_sheets`, and stdlib `.xlsx` row parsing.
  - `tests/test_sync_agent_rules.py` (7 tests): Validates AI bridge generation and non-drift checks.
- **5 CLI Commands Added to Central Dispatcher (`tools/cli.py`):**
  - `api-matrix`: Generates positive, boundary, and negative test matrix from OpenAPI/Swagger.
  - `canvas-diff`: HTML5 Canvas visual regression comparison and blank-screen detector.
  - `validate-groovy`: Pre-check validator for Groovy scripts and keywords syntax balance.
  - `check-version`: Verifies universal version synchronization across 10 manifest and code targets.
  - `mcp-excel`: Launches Model Context Protocol Excel stdio server.
- **Complete Subagent Skill Coverage:** Assigned all 38 standardized skills across subagents (0 orphan skills).

### Fixed
- **Swallowed Exceptions Remediated:** Narrowed 140+ generic `except Exception: pass` blocks across core tools (`verify_all.py`, `dashboard_generator.py`, `count_tokens.py`, `update_sentinel.py`) to precise exception classes (`OSError`, `json.JSONDecodeError`, `ET.ParseError`, `UnicodeDecodeError`).
- **Version & Metadata Drift Aligned:** Resolved legacy `2.3.0` strings across `docs/ARCHITECTURE.md`, `mcp_excel_server.py`, and `update_sentinel.py`.
- **Line Ending Normalization:** Enforced LF line endings for `dist/omni-qc` in `.gitattributes`.
- **Dependabot Actions Updates:** Enabled periodic security PRs for GitHub Actions dependencies.

---

## [2.4.0] - 2026-11-02

### Added
- **Skill 38 (`meta-prompt-crafter`):** Meta-prompt engineering skill transforming rough human ideas into production-ready prompts for ChatGPT, Gemini, Claude, Midjourney, and Coding AIs. Includes 3-step pipeline, 7-part architecture, and complete demonstrable examples.
- **Elephant-Goldfish Zero-Contamination Architecture:**
  - `tools/goldfish_review.py`: Cold 0-context spec reviewer detecting 5 ambiguity patterns (vague criteria, missing error handling, untyped schemas, unstated roles, magic numbers).
  - `tools/spec_drift_sentinel.py`: AST-based spec-to-code alignment sentinel identifying deficit (missed acceptance criteria) and scope creep (unspecified tests).
  - Protocol added to `.agents/rules/context-engineering.md` as Pillar 6.
- **Blazo Observability & Health Guardrails:**
  - Action Loop Detection in `tools/safety_firewall.py`: Sliding window 2-3 step cycle detection halting repetitive agent loops.
  - Watch Mode Sentinel & Inactivity Watchdog in `tools/watch_mode.py`: Real-time incremental TUI monitor with ANSI badges and automatic hang protection.
  - Error Fingerprinting in `tools/cache_resolver.py` & `tools/bug_reporter.py`: Deterministic DJB2 32-bit hex fingerprinting grouping recurrent defects.
  - 5-Stage Stepper & Step Inspector in `tools/dashboard_generator.py`: Interactive execution timeline reporting OpenTelemetry GenAI semantic convention attributes.
  - OpenTelemetry GenAI Spans & ResourceMetrics export in `tools/count_tokens.py` (`--otel`) and `tools/telemetry_correlator.py` (`--otel`).
- **Standardized Root Contributing Guide:** Added root-level `CONTRIBUTING.md` aligned with `docs/CONTRIBUTING.md` documenting 170+ unit test suite execution.

### Changed
- **Professional Vietnamese Linguistic Polish:** Replaced literal/awkward translations across Welcome page (`templates/welcome.html.tmpl`, `reports/WELCOME.html`) and Executive Dashboard (`tools/dashboard_generator.py`, `reports/PROJECT_DASHBOARD.html`) with natural, professional IT/QA terminology.
- **Catalog & Manifest Sync:** Expanded catalog to 38 standardized skills across `skills_manifest.json`, `docs/ARCHITECTURE.md`, `README.md`, `README.en.md`, and CLI commands.

---

## [2.3.0] - 2026-10-31

### Added
- **Single Core Value Proposition:** Finalized focus on *"The Complete QA Intelligence Hub for AI Agents: Empowering Testers Across Manual, Automation, API, and Performance."*
- **7 Adopted Skills (Catalog Expanded to 37):** Integrated and re-scoped skills from vetted open-source projects in the Claude ecosystem, each rewritten to hub standards (frontmatter, examples, Boundary sections) with full attribution:
  - `surgical-coding-principles` (adapted from andrej-karpathy-skills, MIT) - disciplined minimal-diff coding behavior.
  - `lean-code-ladder` (adapted from ponytail, MIT) - 7-rung reuse-first ladder with a never-cut safety floor.
  - `persistent-planning-files` (adapted from planning-with-files, MIT) - disk-backed 3-file planning with a completion gate.
  - `playwright-webapp-testing` (adapted from anthropics/skills webapp-testing, Apache-2.0) - managed server lifecycle for local Playwright runs.
  - `test-driven-development`, `systematic-debugging`, `verification-before-completion` (adapted from superpowers, MIT) - RED-GREEN-REFACTOR, four-phase root-cause discipline, and the evidence protocol.
- **Swarm Persona Enhancements:** all six `.agents/agents/*.md` profiles gained a Persona Enhancements section and new skill bindings cherry-picked from wshobson/agents (MIT).
- **Public Comparison Matrix:** Added in-depth comparison table contrasting Synapse Hub with ESLint Playwright, Stryker Mutator, Allure Report, and Healenium.
- **Known Limitations Section:** Documented system boundaries (AST syntactic mutation heuristic, headless browser requirement, human domain knowledge invariant).
- **Environment Diagnostic Command:** Added `agent-qa doctor` / `npx @teevee98/synapse-hub doctor` for instant 1-click prerequisite auditing.
- **Encoding Integrity Guard (Gate 1):** Upgraded Gate 1 in `verify_all.py` to scan for both UTF-8 No BOM and Mojibake character corruption.
- **Dedicated Python Package:** Created `tools/__init__.py` to allow standard package imports and PEP 621 packaging without `sys.path` hacks.
- **Explicit `--insecure` Flag:** Replaced hardcoded `ssl.CERT_NONE` with explicit `--insecure` CLI parameters across `api_fuzzer.py` and `check_env.py`.
- **Runtime Behavioral Tests:** Replaced static string assertions with Node.js in-context execution tests for `tools/browser_helpers.js`.
- **Attribution & Provenance:** NOTICE entries 16-21 record source repositories, authors, licenses, and modification notes for every adoption.
- **External Tooling Guide:** `docs/adopted-ecosystem-tools.md` documents vetted install/config snippets for ecosystem tools that stay external.

### Changed
- `skills_manifest.json` catalog expanded to 37 entries; categories updated; README/README.en catalogs and counts synced.
- Excluded entrypoint guards (`if __name__ == "__main__":` and `if TYPE_CHECKING:`) from `micro_mutator.py` to eliminate trivial mutations.
- Isolated all test fixtures and temporary artifacts in `tempfile.TemporaryDirectory()`, eliminating test file pollution in the repository root.
- Configured code coverage threshold (`fail_under = 40` baseline for lightweight environments, with a target of 80% for full runner stacks) in `pyproject.toml` and multi-OS matrix CI.

### Fixed
- Fixed corrupted Vietnamese character encoding (mojibake) in `.agents/skills/self-healing-locator/SKILL.md` and `.agents/skills/api-spec-to-e2e-matrix/SKILL.md`.
- Fixed defensive `localStorage` lookup in `tools/browser_helpers.js` to prevent `ReferenceError` in restricted window contexts.

---

## [2.2.0] - 2026-10-28

### Added
- Multi-Agent Swarm system featuring 6 specialized agent profiles (`orchestrator`, `live-explorer`, `pom-crafter`, `test-runner`, `failure-analyst`, `quality-gatekeeper`).
- Large Action Model (LAM) parser compiling user stories into Clean POM page classes (`tools/generate_tc_from_story.py`).
- 9 Quality Gates Definition-of-Done (DoD) verification pipeline (`tools/verify_all.py`).

---

## [2.1.0] - 2026-10-15

### Added
- Meta Infer-style static defect & fake-pass linter (`tools/infer_linter.py`).
- Real-time CLI log distillation reducing log context bloat by 95% (`tools/distill_log.py`).
- Central Agent Memory SQLite cache (`~/.agent_memory/global_cache.db`).

---

## [2.0.0] - 2026-09-01

### Added
- Initial standalone architecture decoupling Synapse Hub from target spoke projects.
- Universal AI bridges for Cursor (`.cursorrules`), Claude Code (`CLAUDE.md`), and Windsurf (`.windsurfrules`).
