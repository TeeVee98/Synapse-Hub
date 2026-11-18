# Synapse Hub Subsystems Comprehensive Audit & Architecture Report

> **Author Attribution & Copyright:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.  
> **Audit Status:** Authoritative Synthesis & Forensic Review  
> **Working Directory:** `d:\Synapse Hub` (Analysis strictly read-only on repository source)  
> **Report Artifact:** `docs/AUDIT_REPORT.md`  
> **Specification Standard:** 100% UTF-8 No BOM, Clean POM / Flat Architecture, Lean Telemetry  

---

## 1. Executive Summary & Audit Scorecard

### 1.1 Purpose & Audit Scope
Synapse Hub is an enterprise-grade AI-augmented test automation and QA engineering hub designed to power autonomous agents across polyglot stacks (Playwright, Cypress, Appium, Katalon, JMeter, k6, REST/GraphQL APIs). As the platform has expanded, redundant triggers, overlapping responsibilities, unassigned assets, and dead weight have accumulated across its four core subsystems:
1. **Domain Skills (`.agents/skills/`)**: 56 declarative capability packages across 11 functional domain directories.
2. **Tools & CLI Automation (`tools/`)**: 180 tool assets comprising 167 Python modules and 13 supporting configuration/template files.
3. **AI Agents (`.agents/agents/`)**: 9 autonomous agent persona manifests operating under a 5-Stage Swarm Finite State Machine (FSM).
4. **Rules & Governance (`.agents/rules/` and `AGENTS.md`)**: 14 active project-level behavioral invariant rules, root platform invariants, and dynamic stack routing policies (`tools/rules_router.py`).

This audit provides an exhaustive, evidence-backed evaluation of every component across all four subsystems. Every examined asset is classified into **Keep**, **Consolidate/Merge**, **Prune/Deprecate**, or **Restore**, accompanied by exact `file:line` citations, semantic collision measurements, runtime execution forensics, and concrete remediation blueprints.

### 1.2 Enterprise Audit Scorecard

| Subsystem | Total Evaluated | Keep (As-Is / Scoped) | Consolidate / Merge | Prune / Deprecate | Restore Missing | Primary Operational Benefit |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **Skills (`.agents/skills/`)** | 56 | 45 (80.4%) | 8 (14.3%) | 3 (5.3%) | 0 | Eliminates 16 collision warnings; saves ~1,800–2,400 tokens/turn |
| **Tools (`tools/`)** | 180 | 164 (91.1%) | 13 (7.2%) | 3 (1.7%) | 0 | Resolves 2 runtime crashes; identifies 49 high-value unwired CLI tools |
| **AI Agents (`.agents/agents/`)** | 9 | 9 (100.0%)* | 0 (0.0%) | 0 (0.0%) | 0 | Restores strict 5-stage FSM boundaries; removes API scope creep |
| **Rules (`.agents/rules/`)** | 14 active | 10 (71.4%) | 3 (21.4%) | 1 (7.1%) | 1 (New) | Restores missing `api_testing_rules.md`; fixes broken link in `api-engineer` |
| **TOTAL ECOSYSTEM** | **259** | **228 (88.0%)** | **24 (9.3%)** | **7 (2.7%)** | **1** | **Unified, high-signal, zero-collision QA engineering platform** |

*\*Note on Agents: While all 9 agent roles are structurally necessary for the 5-Stage Swarm FSM and are retained, 5 of the 9 agents require immediate refactoring and scoping (`orchestrator`, `pom-crafter`, `api-engineer`, `test-runner`, `perf-engineer`).*

### 1.3 Key Architectural Findings
1. **Zero Critical Safety Violations**: Verification via `tools/skillspector.py` confirmed 0 prompt injection vectors, malicious directives, or privilege escalations (Risk Score: 0/100, Verdict: SAFE). Default `skill_collision_guard.py` threshold (>= 0.75) passed cleanly.
2. **Sub-Critical Semantic Overlap**: Lowering `skill_collision_guard.py` detection threshold to 0.30 uncovered 16 pairwise skill proximity warnings and 5 rule overlaps, primarily concentrated in CI/CD pipelines, mobile testing, and failure healing.
3. **Orphaned Skills**: Exactly 4 skills (`mobile-appium-som`, `mobile-maestro-detox-patterns`, `gitlab-ci-templates`, `jenkins-pipeline-templates`) are completely unassigned to any agent in `.agents/agents/`.
4. **Active Runtime Defects in Tools**:
   - `tools/cldr_l10n_verifier.py:245` crashes immediately with `ValueError: unsupported format character ')'` due to an unescaped `%` character inside an `argparse` `help` parameter.
   - `tools/mcp_server.py:816` enters an unconditional, blocking `sys.stdin.readline()` stdio loop upon execution, causing CLI help and inspection commands to hang indefinitely.
5. **CLI Wiring Gap**: 75 standalone tools are wired to `tools/cli.py`, while 49 fully implemented and tested standalone tools lack CLI subcommand bindings.
6. **Forensic Rule Deletion (`api_testing_rules.md`)**: Commit `e229dfd` deleted `api_testing_rules.md` to arbitrarily maintain a "14 rules standard" after adding `stack-auto-router.md`. This left a dangling 404 reference in `api-engineer.md:30` and stripped the `api` stack of all domain-specific testing rules.
7. **Rule Router Gaps**: 4 out of 14 rules (28.6%), including `lessons-learned.md` (which has `trigger: always_on`), are completely omitted from `tools/rules_router.py`.

---

## 2. Subsystem 1: Skills Audit (`.agents/skills/`)

### 2.1 Ecosystem Inventory & Category Breakdown
The repository contains exactly **56 skills** distributed across 11 domain categories under `.agents/skills/`. Across all 56 skills, 152 files were inspected (all 100% UTF-8 No BOM, 0 empty files, 0 malformed schema files). Only 1 skill contains an executable shell script (`06-healing-and-resilience/failure-autopsy-and-healing/scripts/triage_failures.sh`), while 55 skills provide declarative operational instructions, reference guidelines, and sample fixtures.

| Domain Category | Directory Path | Skill Count | Keep | Consolidate | Prune | Semantic Health & Focus |
|---|---|:---:|:---:|:---:|:---:|---|
| **01-web-automation** | `.agents/skills/01-web-automation/` | 11 | 8 | 2 | 1 | High core utility; minor overlap in mobile and server lifecycles |
| **02-test-design** | `.agents/skills/02-test-design/` | 5 | 5 | 0 | 0 | Excellent segmentation (ADRs, BDD, RBT, Spec Review, ToT) |
| **03-api-and-contracts** | `.agents/skills/03-api-and-contracts/` | 3 | 3 | 0 | 0 | High signal; covers network mocking, OpenAPI matrices, and Pact CDC |
| **04-performance-and-load** | `.agents/skills/04-performance-and-load/` | 3 | 2 | 1 | 0 | Solid k6/CWV coverage; scoreboard skill is misclassified |
| **05-security-and-compliance** | `.agents/skills/05-security-and-compliance/` | 3 | 3 | 0 | 0 | Strong DAST, SkillSpector, and WCAG accessibility standards |
| **06-healing-and-resilience** | `.agents/skills/06-healing-and-resilience/` | 9 | 6 | 3 | 0 | High fragmentation across 3 healing skills and 2 DoD sentinel skills |
| **07-data-and-state** | `.agents/skills/07-data-and-state/` | 3 | 3 | 0 | 0 | Pristine; covers DB seeding, file schemas, and synthetic data |
| **08-code-quality** | `.agents/skills/08-code-quality/` | 7 | 6 | 1 | 0 | Strong; surgical coding is redundant with 7-rung lean code ladder |
| **09-ci-and-devops** | `.agents/skills/09-ci-and-devops/` | 3 | 1 | 0 | 2 | 2 completely orphaned templates (GitLab, Jenkins) |
| **10-agent-orchestration** | `.agents/skills/10-agent-orchestration/` | 5 | 5 | 0 | 0 | Mission-critical multi-agent coordination, memory, and event streams |
| **11-ai-and-prompting** | `.agents/skills/11-ai-and-prompting/` | 4 | 4 | 0 | 0 | Advanced prompt compilation (MIPROv2, ACI, context optimization) |
| **TOTAL** | **11 Categories** | **56** | **45** | **8** | **3** | **45 Keep (80.4%), 8 Consolidate (14.3%), 3 Prune (5.3%)** |

---

### 2.2 Forensic Analysis of Unassigned & Orphaned Skills

A cross-subsystem search between `.agents/skills/` and all agent manifests in `.agents/agents/*.md` identified **4 skills** with zero agent bindings:

```text
Orphan Verification Query:
Select-String -Path .agents/agents/*.md -Pattern "<skill-name>"
```

#### 1. `gitlab-ci-templates` (`.agents/skills/09-ci-and-devops/gitlab-ci-templates/`)
- **Physical Footprint**: 123 lines (`SKILL.md`), 1 example file (`examples/sample_gitlab_ci.yml`).
- **Wiring Evidence**: 0 agent assignments, 0 rule references, 0 tool bindings, 0 document references.
- **Collision Metric**: Proximity score of **0.475** with `github-actions-templates` (the highest collision detected in the entire repository).
- **Forensic Diagnosis**: Synapse Hub standardizes on GitHub Actions (`.github/workflows/`) for its internal CI/CD DoD gates. Maintaining a standalone skill directory for GitLab CI without any agent capable of executing or validating it introduces maintenance drag.
- **Action**: **PRUNE** as a standalone skill. Merge its `.gitlab-ci.yml` template into a unified `ci-cd-pipeline-templates` package.

#### 2. `jenkins-pipeline-templates` (`.agents/skills/09-ci-and-devops/jenkins-pipeline-templates/`)
- **Physical Footprint**: 133 lines (`SKILL.md`), 1 example file (`examples/Jenkinsfile.example`).
- **Wiring Evidence**: 0 agent assignments, 0 rule references, 0 tool bindings, 0 document references.
- **Collision Metric**: Proximity score of **0.343** with `github-actions-templates`.
- **Forensic Diagnosis**: Completely unreferenced legacy enterprise Jenkinsfile template. No active agent references Jenkins pipelines.
- **Action**: **PRUNE** as a standalone skill. Merge `Jenkinsfile.example` into a unified `ci-cd-pipeline-templates` package.

#### 3. `mobile-maestro-detox-patterns` (`.agents/skills/01-web-automation/mobile-maestro-detox-patterns/`)
- **Physical Footprint**: 134 lines (`SKILL.md`), 1 example file (`examples/sample_flow.yaml`).
- **Wiring Evidence**: 0 agent assignments, 0 rule references, 0 tool bindings.
- **Collision Metric**: Proximity score of **0.417** with `mobile-appium-som`.
- **Forensic Diagnosis**: Provides declarative YAML flows for Maestro and Detox. However, Synapse Hub's official mobile standard is the Screen Object Model (SOM) codified in `.agents/rules/mobile_appium_rules.md`. Maestro and Detox are currently unbacked by any test execution tools in `tools/`.
- **Action**: **PRUNE** or consolidate into `mobile-automation-patterns`.

#### 4. `mobile-appium-som` (`.agents/skills/01-web-automation/mobile-appium-som/`)
- **Physical Footprint**: 136 lines (`SKILL.md`), 3 Java Screen Object examples (`BaseScreen.java`, `LoginScreen.java`, `TC_MobileLogin.java`).
- **Wiring Evidence**: 0 agent assignments in `.agents/agents/`. However, it is actively supported by `.agents/rules/mobile_appium_rules.md` and routed via `tools/rules_router.py:113` (`"mobile": ["mobile_appium_rules.md"]`).
- **Forensic Diagnosis**: The skill represents a core capability that was accidentally omitted from `pom-crafter.md` and `test-runner.md` manifests when the 9-agent swarm was instantiated.
- **Action**: **CONSOLIDATE** with `mobile-maestro-detox-patterns` into `mobile-automation-patterns` and assign to `pom-crafter` and `test-runner`.

---

### 2.3 Detailed Skill Consolidation Blueprints

Consolidating the 8 overlapping skills eliminates 100% of the sub-critical proximity warnings, lowers prompt hydration overhead by ~1,800 to ~2,400 tokens per multi-agent session, and provides clean 1-to-1 routing boundaries:

```
Consolidation Flowchart:
[lam-script-generator] ───────────► [clean-pom-crafter]
[playwright-webapp-testing] ──────► [e2e-testing-patterns]
[mobile-maestro-detox-patterns] ──► [mobile-automation-patterns] ◄── [mobile-appium-som]
[lean-impact-scoreboard] ─────────► [repo-quality-audit]
[agentless-qa-repair] ────────────┐
[self-healing-locator] ───────────┴► [failure-autopsy-and-healing]
[antigravity-test-sentinel] ──────► [verification-before-completion]
[surgical-coding-principles] ─────► [lean-code-ladder]
[gitlab-ci-templates] ────────────┐
[jenkins-pipeline-templates] ─────┴► [ci-cd-pipeline-templates] (or github-actions-templates)
```

#### Blueprint 1: Code Generation Consolidation
- **Source Skill**: `lam-script-generator` (170 lines)
- **Target Skill**: `clean-pom-crafter` (177 lines)
- **Rationale**: `lam-script-generator` (Large Action Model script generator) converts user stories and acceptance criteria into Clean POM scripts. This is precisely the core mandate of `clean-pom-crafter`. Having both skills assigned to `pom-crafter` creates duplicate guidance on locator hierarchy and class generation.
- **Implementation**: Absorb `examples/user_story_sample.md` into `clean-pom-crafter/examples/`. Add a dedicated "Story-to-Script Codification" section to `clean-pom-crafter/SKILL.md`.

#### Blueprint 2: Mobile Automation Unification
- **Source Skills**: `mobile-appium-som` (136 lines) + `mobile-maestro-detox-patterns` (134 lines)
- **Target Skill**: `mobile-automation-patterns` (Unified)
- **Rationale**: Merges enterprise Appium Screen Object Model (Java/TypeScript) with declarative mobile patterns (Maestro YAML). Eliminates the 0.417 collision score and resolves the orphaned status of both skills by assigning the unified skill to `pom-crafter` (authoring) and `test-runner` (execution).

#### Blueprint 3: Web Server Lifecycle & E2E Patterns
- **Source Skill**: `playwright-webapp-testing` (160 lines)
- **Target Skill**: `e2e-testing-patterns` (193 lines)
- **Rationale**: `playwright-webapp-testing` focuses exclusively on a single operational recipe: launching a local development server, waiting for port readiness, executing tests, and ensuring guaranteed process group teardown. This is a standard fixture lifecycle pattern that belongs in `e2e-testing-patterns`.
- **Implementation**: Move `examples/server_lifecycle_playwright.py` into `e2e-testing-patterns/examples/`.

#### Blueprint 4: Scoreboard Domain Realignment
- **Source Skill**: `lean-impact-scoreboard` (92 lines)
- **Target Skill**: `repo-quality-audit` (111 lines) in `08-code-quality`
- **Rationale**: `lean-impact-scoreboard` is erroneously categorized under `04-performance-and-load`. Its actual telemetry metrics (code reduction percentages, prompt token savings, and AST mutation kill scores) measure source code quality and engineering efficiency, not runtime application load or latency.

#### Blueprint 5: Closed-Loop Healing Unification
- **Source Skills**: `agentless-qa-repair` (115 lines) + `self-healing-locator` (132 lines)
- **Target Skill**: `failure-autopsy-and-healing` (124 lines)
- **Rationale**: Currently, failure recovery is fragmented across three skills. In runtime reality, `tools/auto_heal.py` and `tools/agentless_patcher.py` execute a unified 3-tier recovery model:
  1. *Tier 1 (Fast)*: Heuristic & AOM locator mutation (`self-healing-locator`).
  2. *Tier 2 (Precise)*: Deterministic 3-phase AST repair (`agentless-qa-repair`).
  3. *Tier 3 (Deep)*: Root-cause triage from JUnit XML and screenshots (`failure-autopsy-and-healing`).
- **Implementation**: Structure `failure-autopsy-and-healing` into a comprehensive 3-tier healing standard. Update `.agents/rules/skill-precedence.md` line 26 to route all failure analysis through this single canonical skill.

#### Blueprint 6: Definition-of-Done Sentinel Unification
- **Source Skill**: `antigravity-test-sentinel` (110 lines)
- **Target Skill**: `verification-before-completion` (146 lines)
- **Rationale**: Both skills enforce the identical behavioral invariant: blocking task completion until fresh CLI test execution outputs are observed. `.agents/rules/skill-precedence.md` line 34 explicitly states: *"Prioritize verification-before-completion (or antigravity-test-sentinel in Antigravity). Do not run duplicate verification gates."*
- **Implementation**: Retire `antigravity-test-sentinel` and adopt `verification-before-completion` as the universal DoD gate standard across all IDE hosts (Antigravity, Cursor, Claude Code, Windsurf).

#### Blueprint 7: Lean Engineering Protocol Unification
- **Source Skill**: `surgical-coding-principles` (134 lines)
- **Target Skill**: `lean-code-ladder` (139 lines)
- **Rationale**: `AGENTS.md` §2 rule 3 already unifies these principles under the normative standard: *"Lean Senior Dev Protocol (7-Rung Ladder & YAGNI): The best code is the code never written. Solve the whole problem with the least new code."* Maintaining two distinct skills for the same mindset creates unnecessary prompt hydration for `pom-crafter`.

#### Blueprint 8: Multi-Platform CI/CD Unification
- **Source Skills**: `gitlab-ci-templates` (123 lines) + `jenkins-pipeline-templates` (133 lines)
- **Target Skill**: `github-actions-templates` (renamed to `ci-cd-pipeline-templates`)
- **Rationale**: Consolidates isolated CI snippets into a single reference library under `orchestrator`, retaining multi-platform examples without maintaining orphaned skill folders.


---

### 2.4 Master Table of All 56 Skills in `.agents/skills/`

The table below itemizes every skill in the repository, evaluating its frontmatter trigger, package contents, agent wiring, and final audit disposition:

| # | Domain Category | Skill Directory Name | Status | Assigned Agent(s) | Merge Target / Action | Rationale & Forensic Evidence |
|---|---|---|:---:|---|---|---|
| 1 | `01-web-automation` | `auth-session-and-cookie-manager` | 🟢 **Keep** | live-explorer, test-runner | *None* | Manages browser authentication sessions, `storageState`, JWT tokens, and multi-role state. 3 package files (`SKILL.md`, `storage_state_sample.json`, matrix). |
| 2 | `01-web-automation` | `bats-testing-patterns` | 🟢 **Keep** | test-runner | *None* | Specialized Bats framework patterns for testing bash scripts and CLI harnesses. 3 package files (`SKILL.md`, `cli_runner_test.bats`, playbook). |
| 3 | `01-web-automation` | `clean-pom-crafter` | 🟢 **Keep** | pom-crafter | *None* | Core architectural standard: Clean POM, Flat Architecture (max 1 level), 6-tier locator hierarchy. Actively wired to `pom-crafter`. |
| 4 | `01-web-automation` | `e2e-testing-patterns` | 🟢 **Keep** | test-runner | *None* | Multi-browser E2E architectures, matrix sharding, and retry governance. 3 package files (`SKILL.md`, `playwright_sharded_config.ts`, playbook). |
| 5 | `01-web-automation` | `katalon-cli-runner` | 🟢 **Keep** | test-runner | *None* | Headless Katalon Runtime Engine (KRE) execution, driver cleanup, and Gradle integration. 5 package files. |
| 6 | `01-web-automation` | `lam-script-generator` | 🟡 **Consolidate** | pom-crafter | `clean-pom-crafter` | Translates user stories to Clean POM scripts. Proximity collision of 0.463 with `review-spec`; redundant with `clean-pom-crafter`. |
| 7 | `01-web-automation` | `mobile-appium-som` | 🟡 **Consolidate** | **NONE (Orphan)** | `mobile-automation-patterns` | Appium Screen Object Model for iOS/Android. Accidentally orphaned from agent manifests; merge with Maestro/Detox and wire to `pom-crafter`/`test-runner`. |
| 8 | `01-web-automation` | `mobile-maestro-detox-patterns` | 🔴 **Prune** | **NONE (Orphan)** | `mobile-automation-patterns` | Declarative Maestro/Detox flows. 0 agent assignments, 0 tool bindings, 0 rule references; 0.417 collision with Appium SOM. |
| 9 | `01-web-automation` | `playwright-live-interaction` | 🟢 **Keep** | live-explorer | *None* | Probes live DOM/AOM and validates locators in <200ms using headless Playwright. 6 package files including advanced superpowers. |
| 10 | `01-web-automation` | `playwright-webapp-testing` | 🟡 **Consolidate** | live-explorer | `e2e-testing-patterns` | Local dev server start, wait, and guaranteed teardown lifecycle. Standard fixture recipe that belongs in `e2e-testing-patterns`. |
| 11 | `01-web-automation` | `web-agent-gym-benchmarking` | 🟢 **Keep** | quality-gatekeeper | *None* | Empirical benchmark harness evaluating web agents and Page Classes with ground-truth DB state. Wired to `browsergym_eval.py`. |
| 12 | `02-test-design` | `architecture-decision-records` | 🟢 **Keep** | orchestrator, pom-crafter | *None* | Standardizes Architecture Decision Records (ADRs) across testing frameworks and refactorings. 2 package files. |
| 13 | `02-test-design` | `gherkin-to-suite` | 🟢 **Keep** | pom-crafter, test-designer | *None* | Compiles Gherkin `.feature` specs into Universal IR test matrices with zero LLM tokens. Wired to `tools/gherkin_suite.py`. |
| 14 | `02-test-design` | `rbt-manual-testing` | 🟢 **Keep** | test-designer | *None* | AI-RBT 6-stage manual test designer, ambiguity grilling, 15-type field validation, and corporate Excel exporter. 3 package files. |
| 15 | `02-test-design` | `review-spec` | 🟢 **Keep** | orchestrator, test-designer | *None* | Goldfish 5-vector pre-flight specification stress-tester. Wired to `tools/goldfish_review.py`. |
| 16 | `02-test-design` | `tot-exploratory-testing` | 🟢 **Keep** | orchestrator, test-designer | *None* | Tree/Graph-of-Thoughts exploratory testing with Beam Search risk scoring. Wired to `tools/tot_exploratory_tester.py`. |
| 17 | `03-api-and-contracts` | `api-network-mocking-interception` | 🟢 **Keep** | api-engineer | *None* | HTTP/GraphQL route stubbing, mock fixtures, and chaos fault injection. Wired to `tools/network_mock_shield.py`. |
| 18 | `03-api-and-contracts` | `api-spec-to-e2e-matrix` | 🟢 **Keep** | api-engineer | *None* | Converts OpenAPI/Swagger specifications into positive, boundary, and negative matrices. Wired to `tools/generate_api_matrix.py`. |
| 19 | `03-api-and-contracts` | `consumer-driven-contract-testing` | 🟢 **Keep** | api-engineer | *None* | Pact and Bidirectional Contract Testing (BDCT) across microservices, preventing payload drift. 2 package files. |
| 20 | `04-performance-and-load` | `backend-load-and-stress-patterns` | 🟢 **Keep** | perf-engineer | *None* | Orchestrates k6, Locust, and JMeter backend load, stress, and spike endurance profiles. Wired to `tools/generate_jmx_plan.py`. |
| 21 | `04-performance-and-load` | `lean-impact-scoreboard` | 🟡 **Consolidate** | quality-gatekeeper | `repo-quality-audit` | Misclassified in performance domain. Measures code reduction, token throughput, and mutant kill rates. Belongs in `08-code-quality`. |
| 22 | `04-performance-and-load` | `web-vitals-and-performance-profiler` | 🟢 **Keep** | perf-engineer, quality-gatekeeper | *None* | Measures Core Web Vitals (LCP, CLS, INP) and network waterfalls via Chrome DevTools Protocol. 3 package files. |
| 23 | `05-security-and-compliance` | `security-dast-sentinel` | 🟢 **Keep** | api-engineer, quality-gatekeeper | *None* | OWASP Top 10, security headers, BOLA/IDOR, and token leakage verification. 5 package files. |
| 24 | `05-security-and-compliance` | `skillspector-security-guard` | 🟢 **Keep** | quality-gatekeeper | *None* | Static security scanner auditing AI skills and MCP configs against NVIDIA SkillSpector threat vectors. Wired to `tools/skillspector.py`. |
| 25 | `05-security-and-compliance` | `wcag-audit-patterns` | 🟢 **Keep** | quality-gatekeeper | *None* | Audits WCAG 2.2 A/AA criteria, keyboard navigation, and ARIA tree compliance. Wired to `tools/wcag_audit.py`. |
| 26 | `06-healing-and-resilience` | `agentless-qa-repair` | 🟡 **Consolidate** | failure-analyst | `failure-autopsy-and-healing` | 3-phase repair flow (localization, synthesis, diff validation). Fragmented duplicate of `failure-autopsy-and-healing`. |
| 27 | `06-healing-and-resilience` | `antigravity-test-sentinel` | 🟡 **Consolidate** | quality-gatekeeper | `verification-before-completion` | Exact duplicate of `verification-before-completion`. Explicitly marked as duplicate in `.agents/rules/skill-precedence.md` line 34. |
| 28 | `06-healing-and-resilience` | `failure-autopsy-and-healing` | 🟢 **Keep** | failure-analyst | *None* | Core diagnostic triage engine from JUnit XML/screenshots and closed-loop healing. Contains `scripts/triage_failures.sh`. |
| 29 | `06-healing-and-resilience` | `flaky-test-sentinel-and-quarantine` | 🟢 **Keep** | perf-engineer, test-runner | *None* | Statistical non-deterministic test detection, flakiness scoring, and quarantine lifecycle. Wired to `tools/flaky_detector.py`. |
| 30 | `06-healing-and-resilience` | `self-healing-locator` | 🟡 **Consolidate** | failure-analyst, live-explorer | `failure-autopsy-and-healing` | Heuristic and AOM locator healing. Subsumed as Tier 1 capability in `failure-autopsy-and-healing`. |
| 31 | `06-healing-and-resilience` | `systematic-debugging` | 🟢 **Keep** | failure-analyst | *None* | 4-phase scientific root-cause protocol (investigate before fixing). High-signal diagnostic methodology. |
| 32 | `06-healing-and-resilience` | `test-driven-development` | 🟢 **Keep** | pom-crafter, test-runner | *None* | Strict RED-GREEN-REFACTOR cycle: watching tests fail before implementing logic. 2 package files. |
| 33 | `06-healing-and-resilience` | `verification-before-completion` | 🟢 **Keep** | quality-gatekeeper | *None* | Canonical Definition of Done verification protocol requiring fresh CLI execution evidence. |
| 34 | `06-healing-and-resilience` | `visual-regression-sentinel` | 🟢 **Keep** | live-explorer | *None* | Pixel and layout shift regression engine with anti-flake masking. Wired to `tools/visual_diff_canvas.py`. |
| 35 | `07-data-and-state` | `db-state-verifier-and-seeder` | 🟢 **Keep** | perf-engineer, pom-crafter, quality-gatekeeper | *None* | Seeds isolated database fixtures and verifies state mutations across SQL and NoSQL engines. |
| 36 | `07-data-and-state` | `file-and-report-validator` | 🟢 **Keep** | api-engineer, failure-analyst, pom-crafter, test-designer | *None* | Validates downloaded/exported files (Excel, CSV, PDF, OpenXML) schemas and tabular integrity. 2 package files. |
| 37 | `07-data-and-state` | `synthetic-test-data-generator` | 🟢 **Keep** | api-engineer, perf-engineer, pom-crafter, test-designer | *None* | Generates idempotent, unique synthetic test data with timestamps to prevent database collision. |
| 38 | `08-code-quality` | `code-refactoring-refactor-clean` | 🟢 **Keep** | quality-gatekeeper | *None* | SOLID and Clean Code refactoring patterns for technical debt reduction. 4 package files. |
| 39 | `08-code-quality` | `graphify-impact-analyzer` | 🟢 **Keep** | orchestrator | *None* | Analyzes change blast radius and scopes impacted tests via AST knowledge graphs. Wired to `tools/test_impact.py`. |
| 40 | `08-code-quality` | `lean-code-ladder` | 🟢 **Keep** | pom-crafter | *None* | 7-rung reuse-first ladder (YAGNI, stdlib-first). Absorbs `surgical-coding-principles` per `AGENTS.md` §2 rule 3. |
| 41 | `08-code-quality` | `repo-quality-audit` | 🟢 **Keep** | orchestrator | *None* | Holistic 6-pillar repository architecture, security, and bloat audit. Wired to `tools/analyze_project.py`. |
| 42 | `08-code-quality` | `senior-code-review` | 🟢 **Keep** | quality-gatekeeper | *None* | 6-pillar pull request review against Clean POM, security, and concurrency standards. Wired to `tools/senior_code_review.py`. |
| 43 | `08-code-quality` | `surgical-coding-principles` | 🟡 **Consolidate** | pom-crafter | `lean-code-ladder` | Minimal change and simplicity principles. Completely subsumed by `lean-code-ladder` and `AGENTS.md` §2 rule 3. |
| 44 | `08-code-quality` | `technical-debt-harvester` | 🟢 **Keep** | pom-crafter, quality-gatekeeper | *None* | Scans and catalogs `shortcut:` comments into a tracked technical debt ledger. Wired to `tools/debt_harvester.py`. |
| 45 | `09-ci-and-devops` | `github-actions-templates` | 🟢 **Keep** | orchestrator | *None* | Production GitHub Actions workflows, matrix sharding, and security action pinning. Expand into `ci-cd-pipeline-templates`. |
| 46 | `09-ci-and-devops` | `gitlab-ci-templates` | 🔴 **Prune** | **NONE (Orphan)** | `github-actions-templates` | Completely orphaned (0 agent assignments, 0 rules, 0 tools). Proximity collision of 0.475 with GitHub Actions. |
| 47 | `09-ci-and-devops` | `jenkins-pipeline-templates` | 🔴 **Prune** | **NONE (Orphan)** | `github-actions-templates` | Completely orphaned (0 agent assignments, 0 rules, 0 tools). Proximity collision of 0.343 with GitHub Actions. |
| 48 | `10-agent-orchestration` | `actor-qa-swarm` | 🟢 **Keep** | orchestrator | *None* | Asynchronous Actor Model message broker and matrix sharding coordinator. Wired to `tools/autogen_qa_broker.py`. |
| 49 | `10-agent-orchestration` | `agent-orchestration-multi-agent-optimize` | 🟢 **Keep** | orchestrator | *None* | Profiles and benchmarks multi-agent test workloads and token throughput. 2 package files. |
| 50 | `10-agent-orchestration` | `event-stream-qa-orchestrator` | 🟢 **Keep** | orchestrator | *None* | Immutable EventStream recording deterministic action/observation timelines with SHA-256 hash chains. Wired to `tools/qa_event_stream.py`. |
| 51 | `10-agent-orchestration` | `persistent-planning-files` | 🟢 **Keep** | orchestrator | *None* | Persists task plans, findings, and progress to disk (`task.md`, `progress.md`, `BRIEFING.md`) across context resets. |
| 52 | `10-agent-orchestration` | `qa-memory-os` | 🟢 **Keep** | orchestrator | *None* | 3-tier memory operating system (Core, Recall, Archival SQLite) preventing context rot. Wired to `tools/test_memory_os.py`. |
| 53 | `11-ai-and-prompting` | `meta-prompt-crafter` | 🟢 **Keep** | orchestrator | *None* | Transforms rough human prompts into production-grade instructions across multiple LLM families. 2 package files. |
| 54 | `11-ai-and-prompting` | `mipro-prompt-compiler` | 🟢 **Keep** | pom-crafter | *None* | MIPROv2 Bayesian teleprompter few-shot compiler tuning prompt instructions against AST mutant kill scores. |
| 55 | `11-ai-and-prompting` | `qa-aci-interface` | 🟢 **Keep** | pom-crafter | *None* | Safe Agent-Computer Interface for 40-50 line code window inspection and surgical AST editing. Wired to `tools/swe_qa_aci.py`. |
| 56 | `11-ai-and-prompting` | `token-and-context-optimizer` | 🟢 **Keep** | orchestrator | *None* | Distills verbose logs and optimizes prompt context to prevent context bloat. Wired to `tools/distill_log.py`. |


---

## 3. Subsystem 2: Tools & CLI Audit (`tools/`)

### 3.1 Overview & Physical Asset Inventory
The `tools/` directory contains **180 physical assets** across 7 subdirectories (`tools/core/`, `tools/heal/`, `tools/lint/`, `tools/mcp/`, `tools/perf/`, `tools/report/`, `tools/templates/jmeter-distributed/`). All 167 Python files were successfully parsed with AST parsers with zero syntax errors. 158 of 160 standalone tools successfully executed `--help` and displayed standard documentation within an 8-second execution budget.

| Asset Category | File Count | Percentage | Operational Role | Health Assessment |
|---|:---:|:---:|---|---|
| **Keep** | **164** | 91.1% | Active CLI subcommands (75), core engine libraries (11), domain modules (29), high-value standalone tools (49) | Robust, high-value, verified AST and runtime health |
| **Consolidate/Merge** | **13** | 7.2% | Duplicate diagnostic tools, redundant file exporters, fragmented assertion tuners | High functional overlap; clear canonical targets identified |
| **Prune/Deprecate** | **3** | 1.7% | Dead one-off evaluation script (1,643 LOC) and committed ephemeral lock files (2) | Dead weight; should be deleted or git-ignored |
| **TOTAL** | **180** | **100.0%** | Complete tools ecosystem inventory | Overall healthy; requires CLI wiring and deduplication |

---

### 3.2 Runtime Execution Defects & Forensic Root Cause Analyses

During live execution probing across all 160 standalone tools, two runtime execution anomalies were uncovered:

#### Defect 1: Format-String Crash in `tools/cldr_l10n_verifier.py` (Line 245)
- **Invocation Command**: `python tools/cldr_l10n_verifier.py --help`
- **Error Stack Trace**:
  ```text
  Traceback (most recent call last):
    File "d:\Synapse Hub\tools\cldr_l10n_verifier.py", line 309, in <module>
      sys.exit(main())
    File "d:\Synapse Hub\tools\cldr_l10n_verifier.py", line 254, in main
      args = parser.parse_args()
    File "C:\Python312\Lib\argparse.py", line 640, in _expand_help
      return self._get_help_string(action) % params
  ValueError: unsupported format character ')' (0x29) at index 58
  ```
- **Forensic Root Cause**: In Python's standard `argparse` library, the `help` string is processed via old-style `%` string formatting to interpolate parameter variables like `%(default)s`. On line 245 of `tools/cldr_l10n_verifier.py`, the argument definition contains:
  ```python
  help="Expansion percentage for pseudo-localization (default: 35%)"
  ```
  The literal `%` followed immediately by the closing parenthesis `)` is interpreted by `argparse` as an invalid format specifier `%)`, causing an immediate unhandled `ValueError` whenever `--help` is triggered or when CLI parsing fails.
- **Actionable Remediation**: Escape the percent sign with a double `%%`:
  ```python
  # tools/cldr_l10n_verifier.py:245
  - help="Expansion percentage for pseudo-localization (default: 35%)"
  + help="Expansion percentage for pseudo-localization (default: 35%%)"
  ```

#### Defect 2: Indefinite Stdio Hang in `tools/mcp_server.py` (Line 816)
- **Invocation Command**: `python tools/mcp_server.py --help`
- **Observed Behavior**: The command produces zero console output, hangs indefinitely, and blocks execution until externally terminated (timed out after 8,000ms).
- **Forensic Root Cause**: Lines 815–816 contain:
  ```python
  if __name__ == "__main__":
      run_stdio_server()
  ```
  `run_stdio_server()` immediately enters a blocking `while True: line = sys.stdin.readline()` event loop awaiting JSON-RPC messages from an MCP client without inspecting `sys.argv` for standard inspection flags like `--help`, `-h`, or `--version`. Consequently, automated discovery agents and health checks invoking `--help` freeze.
- **Actionable Remediation**: Add lightweight argument interception before initiating the stdio event loop:
  ```python
  # tools/mcp_server.py:815
  if __name__ == "__main__":
      if any(arg in sys.argv[1:] for arg in ("--help", "-h")):
          print("Enterprise Model Context Protocol (FastMCP) JSON-RPC Stdio Server.")
          print("Usage: python tools/mcp_server.py (Accepts JSON-RPC 2.0 frames over stdin/stdout)")
          sys.exit(0)
      run_stdio_server()
  ```

---

### 3.3 Redundancy, Duplicate Logic & Dead Code Analysis

Exhaustive code comparison across all 180 assets identified 8 significant redundancy patterns and duplicate implementations:

#### 1. The Environment Doctor Duplication (`synapse_doctor.py` vs `check_env.py`)
- **Evidence**: `tools/synapse_doctor.py` (324 LOC) claims to be the `agent-qa doctor` engine. However, inspecting `tools/cli.py:256` reveals that `cmd_doctor` is exclusively bound to:
  ```python
  # tools/cli.py:256-258
  from check_env import main as check_env_main
  return check_env_main()
  ```
- `tools/check_env.py` (429 LOC) is the official production environment doctor, verifying Python version, Node.js, Playwright browsers, Katalon KRE, Git config, and environment variables. `synapse_doctor.py` is completely unreferenced by the CLI and contains duplicate checks.
- **Remediation**: Port any unique Playwright browser diagnostic routines from `synapse_doctor.py` into `check_env.py`, then deprecate and remove `synapse_doctor.py`.

#### 2. Test Case Excel Export Duplication (`md_to_xlsx.py` vs `template_excel_exporter.py`)
- **Evidence**: `tools/md_to_xlsx.py` (330 LOC) parses markdown tables and formats them into Excel spreadsheets. `tools/template_excel_exporter.py` (514 LOC) is the official template-driven Excel exporter wired to `agent-qa export-excel` (`tools/cli.py:534`).
- `template_excel_exporter.py` already includes fallback logic to the standard 12-column corporate manual testing template when no custom template is provided. `md_to_xlsx.py` represents legacy duplicate code.
- **Remediation**: Consolidate any specialized cell formatting or auto-width algorithms from `md_to_xlsx.py` into `template_excel_exporter.py` and retire `md_to_xlsx.py`.

#### 3. Token Budget Circuit Breaker Duplication (`runaway_stopper.py` vs `tools/core/circuit_breaker.py`)
- **Evidence**: `tools/runaway_stopper.py` (181 LOC) implements hard agent turn limits and token thresholds. `tools/core/circuit_breaker.py` (263 LOC) implements the production `StreamingTokenBudgetSentinel` with real-time token tracking, HTTP 429 backoff, and model fallback cascades.
- Maintaining a disconnected `runaway_stopper.py` in the root tools directory confuses agents attempting to enforce token guardrails.
- **Remediation**: Merge turn-limit heuristics from `runaway_stopper.py` into `tools/core/circuit_breaker.py` and remove `runaway_stopper.py`.

#### 4. Skill Schema vs Manifest Sync Duplication (`sync_skills_manifest.py` vs `validate_skills_schema.py`)
- **Evidence**: `tools/sync_skills_manifest.py` (166 LOC) has 0 unit tests, 0 CLI wiring, and 0 agent references. It duplicates SKILL.md frontmatter parsing logic implemented in `tools/validate_skills_schema.py` (575 LOC).
- **Remediation**: Add a `--sync-manifest` flag to `tools/validate_skills_schema.py` and retire `sync_skills_manifest.py`.

#### 5. Release Packaging Duplication (`package_release.py` vs `hub_publisher.py`)
- **Evidence**: `tools/package_release.py` (350 LOC) builds ZIP and tar.gz release bundles (`dist/synapse-hub-*.zip`). `tools/hub_publisher.py` (709 LOC) is the official end-to-end publishing pipeline wired to `agent-qa publish`.
- **Remediation**: Integrate release packaging as an internal step or `--package` flag in `tools/hub_publisher.py`.

#### 6. Dead One-Off Evaluation Script (`tools/build_consolidated_report.py`)
- **Evidence**: `tools/build_consolidated_report.py` is a massive 1,643-line script hardcoded to merge two historical evaluation reports: `TOP_10_SKILLS_AGENTS_EVALUATION.html` and `TOP_10_PART2_SKILLS_AGENTS_EVALUATION.html`.
- Neither of these HTML files exists in the repository. The script has 0 unit tests, 0 callers, and 0 CLI commands. It represents dead code.
- **Remediation**: Prune from repository or move to historical archives.

#### 7. Committed Ephemeral Lock Files (`tools/repo_map.json.lock`, `tools/repo_map.txt.lock`)
- **Evidence**: Both files are 1-byte ephemeral process lock files accidentally committed to git.
- **Remediation**: Delete both lock files from git and ensure `*.lock` is recorded in `.gitignore`.

#### 8. Test Fixture in Tools Root (`tools/create_mock_docx.py`)
- **Evidence**: `tools/create_mock_docx.py` (107 LOC) exists solely to generate a synthetic `.docx` file for unit testing OpenXML parsing (`tests/fixtures/mock_document.docx`). It is not an operational QA tool.
- **Remediation**: Relocate into `tests/fixtures/` or execute inline during test setup.

#### 9. AI Assertion Optimization Triad Fragmentation
- **Evidence**: Three tightly coupled assertion optimization tools operate in isolation without CLI bindings:
  1. `tools/dspy_qa_signatures.py` (460 LOC): Declarative DSPy assertion signature compiler.
  2. `tools/mipro_assertion_tuner.py` (210 LOC): MIPROv2 Bayesian prompt instruction optimizer.
  3. `tools/textgrad_mutation_optimizer.py` (237 LOC): Mutant-directed textual loss optimizer.
- All three scripts share the identical objective: optimizing test assertions to achieve an AST mutant kill rate >= 80%.
- **Remediation**: Consolidate the triad into a unified assertion optimization module (`tools/assertion_optimizer.py`) exposed via `agent-qa optimize-assertions`.

#### 10. Finite State Machine (FSM) Enforcement Fragmentation
- **Evidence**: `tools/fsm_enforcer.py` (450 LOC) enforces the 5-Stage Swarm FSM transitions, while `tools/fsm_middleware.py` (401 LOC) acts as a runtime proxy interceptor. Neither script is wired to `tools/cli.py`.
- **Remediation**: Expose both through a unified CLI subcommand: `agent-qa fsm [status|advance|validate]`.

---

### 3.4 Standalone Tools Lacking CLI Wiring in `tools/cli.py`

Of the 148 root standalone Python tools, 75 are directly dispatched via `tools/cli.py`. Exactly **49 standalone tools** have complete, verified implementations and unit test suites, but lack user-facing CLI subcommands. 

The table below groups these 49 unwired tools by capability domain and specifies recommended CLI subcommand names:

| # | Tool Script | LOC | Recommended CLI Subcommand | Capability & Impact |
|---|---|:---:|---|---|
| **Security & Penetration Guard** | | | | |
| 1 | `tools/pentest_scope_guard.py` | 944 | `agent-qa pentest-guard` | Layer 1 & 2 DAST safety firewall (SSRF prevention, domain whitelist, rate limiting) |
| 2 | `tools/security_coverage_ledger.py` | 538 | `agent-qa security-ledger` | Cloudflare-compatible mathematical security coverage ledger & audit tracker |
| 3 | `tools/security_scanner.py` | 309 | `agent-qa security-scan` | Multi-layer dependency and secret scanner (pip-audit, npm audit, Shannon entropy) |
| 4 | `tools/generate_sbom.py` | 252 | `agent-qa sbom` | CycloneDX / SPDX Software Bill of Materials generator for supply chain compliance |
| **Database & Environment Sandboxing** | | | | |
| 5 | `tools/db_sandbox.py` | 1008 | `agent-qa db-sandbox` | Ephemeral containerized DB sandboxing (PostgreSQL, MySQL) with automated rollback |
| 6 | `tools/reversible_sandbox.py` | 500 | `agent-qa sandbox` | Reversible execution sandbox with automatic filesystem checkpointing and rollbacks |
| **Enterprise ALM & TMS Integrations** | | | | |
| 7 | `tools/tms_sync_bridge.py` | 834 | `agent-qa tms-sync` | Universal ALM/TMS sync bridge for Jira, Xray, Zephyr, TestRail |
| 8 | `tools/task_memory_manager.py` | 287 | `agent-qa task-memory` | Cross-session task memory persistence and resumption manager |
| 9 | `tools/test_memory_os.py` | 510 | `agent-qa memory-os` | 3-tier hierarchical persistent memory operating system (Core, Recall, Archival SQLite) |
| **Test Generation & Combinatorics** | | | | |
| 10 | `tools/pairwise_generator.py` | 177 | `agent-qa pairwise` | 2-way combinatorial test case generator reducing redundant test matrices by 80–90% |
| 11 | `tools/break_ui_generator.py` | 233 | `agent-qa break-ui` | Adversarial UI chaos generator creating boundary, overflow, and race condition tests |
| 12 | `tools/tot_exploratory_tester.py` | 256 | `agent-qa tot-test` | Non-linear Tree-of-Thoughts exploratory test charter and hypothesis generator |
| **Quality Reporting & Documentation** | | | | |
| 13 | `tools/slide_deck_exporter.py` | 477 | `agent-qa slides` | Pure HTML5/CSS vector 16:9 executive presentation slide deck generator |
| 14 | `tools/diagram_architect.py` | 222 | `agent-qa diagram` | Generates Mermaid/SVG test architecture and workflow diagrams |
| 15 | `tools/coverage_reporter.py` | 245 | `agent-qa coverage` | Enforces calibrated statement and branch coverage floors across suites |
| 16 | `tools/generate_allure_report.py` | 91 | `agent-qa allure` | Generates consolidated Allure HTML test execution reports |
| 17 | `tools/generate_test_reports.py` | 136 | `agent-qa report-summary` | Aggregates multi-suite test execution results into executive summaries |
| **Code Quality, AI Slop & Interoperability** | | | | |
| 18 | `tools/humanize_linter.py` | 445 | `agent-qa humanize` | Anti-AI slop linter detecting robotic cliches in documentation and commit messages |
| 19 | `tools/validate_host_interop.py` | 485 | `agent-qa host-interop` | Cross-host IDE verifier (Antigravity, Cursor, Claude Code, Copilot, Windsurf) |
| 20 | `tools/vcr_cassette_guard.py` | 432 | `agent-qa vcr` | Deterministic network VCR cassette recorder, sanitizer, and orphan detector |
| 21 | `tools/lint_ai_docs.py` | 391 | `agent-qa lint-docs` | Enforces structural conventions, prompt hygiene, and no-BOM across documentation |
| **Autonomous Swarm & Multi-Agent Infra** | | | | |
| 22 | `tools/autogen_qa_broker.py` | 843 | `agent-qa swarm-broker` | Asynchronous Actor Model message broker and work sharding coordinator |
| 23 | `tools/benchmark_swarm_context.py` | 604 | `agent-qa benchmark-swarm` | Profiles token consumption, context rot, and latency across multi-agent swarms |
| 24 | `tools/qa_event_stream.py` | 358 | `agent-qa event-stream` | Replay engine recording action/observation timelines with SHA-256 hash chains |
| 25 | `tools/project_state.py` | 198 | `agent-qa project-state` | Evaluates repository maturity and quality health across 5 lifecycle stages |
| 26 | `tools/skill_vault.py` | 481 | `agent-qa skill-vault` | Lifelong Page Object Model and interaction pattern storage repository |
| 27 | `tools/synapse_observer.py` | 485 | `agent-qa observer` | Cognitive observer logging tradeoff insights (`tag: Heads up`, `learn:`) |
| 28 | `tools/synapse_qa_bench.py` | 190 | `agent-qa qa-bench` | Evaluates tool calling accuracy and parameter conformance |
| **Resilience, Probing & Healing** | | | | |
| 29 | `tools/agentless_patcher.py` | 417 | `agent-qa agentless-patch` | Deterministic 3-stage patch generator for localized test defects |
| 30 | `tools/auto_heal_reflexion.py` | 532 | `agent-qa reflexion` | Multi-trial episodic reflexion engine for complex multi-file test failures |
| 31 | `tools/browsergym_eval.py` | 236 | `agent-qa gym-eval` | Web-agent benchmark evaluator measuring DOM interaction success rates |
| 32 | `tools/chaos_resilience_probe.py` | 362 | `agent-qa chaos-probe` | Fault injection probe testing UI/API resilience against network and DOM delays |
| 33 | `tools/contract_validator.py` | 141 | `agent-qa contract-check` | Swarm data contract and schema validation engine |
| 34 | `tools/distill_skill.py` | 206 | `agent-qa distill-skill` | Dual-model skill distillation compressing verbose instructions |
| 35 | `tools/e2e_flow_prober.py` | 135 | `agent-qa probe-flow` | Probes end-to-end user journeys and identifies unreachable DOM branches |
| 36 | `tools/git_pre_commit_guard.py` | 511 | `agent-qa pre-commit` | Pre-commit architectural guard enforcing BOM, secrets, and test naming standards |
| 37 | `tools/git_worktree_manager.py` | 188 | `agent-qa worktree` | Isolated Git worktree manager for concurrent subagent test runs |
| 38 | `tools/interview_story.py` | 139 | `agent-qa interview-story` | Pocock Grilling ambiguity detector for user stories and acceptance criteria |
| 39 | `tools/mobile_resilience_sentinel.py` | 273 | `agent-qa mobile-guard` | Mobile Appium session watchdog detecting driver crashes and hung emulators |
| 40 | `tools/observability_tester.py` | 235 | `agent-qa observability` | OpenTelemetry and distributed trace assertion harness for API transactions |
| 41 | `tools/payment_interop_simulator.py` | 337 | `agent-qa payment-sim` | Mock payment gateway simulator (Stripe, PayPal, VNPay) with 3DS challenge emulation |
| 42 | `tools/perf/benchmark_perf_runner.py` | 267 | `agent-qa benchmark-runner` | Headless execution runner for performance benchmark suites |
| 43 | `tools/pre_bash_guard.py` | 122 | `agent-qa bash-guard` | Pre-execution safety filter intercepting dangerous shell commands |
| 44 | `tools/repo_map.py` | 551 | `agent-qa repo-map` | Generates compact AST knowledge graphs of repository dependencies |
| 45 | `tools/skill_collision_guard.py` | 304 | `agent-qa skill-guard` | Tier-2 skill routing and collision detection engine |
| 46 | `tools/swe_qa_aci.py` | 369 | `agent-qa aci` | Agent-Computer Interface providing 40-50 line code windows and AST linting |
| 47 | `tools/traffic_session_converter.py` | 259 | `agent-qa traffic-convert` | Converts HAR network recordings into reproducible k6 load scenarios |
| 48 | `tools/validate_skills_schema.py` | 575 | `agent-qa validate-skills` | Validates SKILL.md frontmatter, schema constraints, and triggers |
| 49 | `tools/generate_tool_catalog.py` | 512 | `agent-qa catalog` | Generates machine-readable `tools/TOOL_CATALOG.json` |

---

### 3.5 Master Table of All 180 Tools & Assets in `tools/`

| # | Relative Path | LOC | Category | CLI Command | Status | Notes & Forensic Evidence |
|---|---|:---:|---|---|:---:|---|
| 1 | `tools/.infer_baseline.json` | 46 | Metadata | *(none)* | **Keep** | Configuration baseline file for Meta Infer-style AST linter. |
| 2 | `tools/TOOLS_RUNBOOK.md` | 1795 | Documentation | *(none)* | **Keep** | Comprehensive 1795-line operational runbook for all tools. |
| 3 | `tools/TOOL_CATALOG.json` | 2195 | Metadata | *(none)* | **Keep** | Machine-readable tool catalog schema and metadata. |
| 4 | `tools/__init__.py` | 46 | Package | *(none)* | **Keep** | Package exports and initialization. |
| 5 | `tools/_openapi_parser.py` | 158 | Library | *(none)* | **Keep** | Dedicated internal OpenAPI parsing library called by active tools. |
| 6 | `tools/agent_canary.py` | 528 | Automation | `canary` | **Keep** | Actively wired to CLI subcommand `agent-qa canary`. |
| 7 | `tools/agentless_patcher.py` | 417 | Automation | *(none)* | **Keep** | Functional standalone 3-stage deterministic patch synthesizer. |
| 8 | `tools/ai_eval_sentinel.py` | 403 | Automation | `ai-eval` | **Keep** | Actively wired to CLI subcommand `agent-qa ai-eval`. |
| 9 | `tools/analyze_project.py` | 265 | Automation | `analyze` | **Keep** | Actively wired to CLI subcommand `agent-qa analyze`. |
| 10 | `tools/api_drift_sentinel.py` | 211 | Automation | `contract-drift` | **Keep** | Actively wired to CLI subcommand `agent-qa contract-drift`. |
| 11 | `tools/api_fuzzer.py` | 1080 | Automation | `fuzz-api` | **Keep** | Actively wired to CLI subcommand `agent-qa fuzz-api`. |
| 12 | `tools/ast_cache.py` | 173 | Library | *(none)* | **Keep** | AST Dataflow caching module called by static linters. |
| 13 | `tools/asvs_auditor.py` | 410 | Automation | `asvs` | **Keep** | Actively wired to CLI subcommand `agent-qa asvs`. |
| 14 | `tools/author_integrity.py` | 357 | Automation | `verify-author` | **Keep** | Actively wired to CLI subcommand `agent-qa verify-author`. |
| 15 | `tools/auto_heal.py` | 276 | Automation | `auto-heal` | **Keep** | Actively wired to CLI subcommand `agent-qa auto-heal`. |
| 16 | `tools/auto_heal_reflexion.py` | 532 | Automation | *(none)* | **Keep** | Multi-Trial episodic reflexion engine for complex test failures. |
| 17 | `tools/autogen_qa_broker.py` | 843 | Automation | *(none)* | **Keep** | Asynchronous Actor QA message broker and workload coordinator. |
| 18 | `tools/benchmark_swarm_context.py` | 604 | Automation | *(none)* | **Keep** | Swarm token and context latency benchmarking tool. |
| 19 | `tools/break_ui_generator.py` | 233 | Automation | *(none)* | **Keep** | Adversarial UI chaos generator. Missing CLI binding. |
| 20 | `tools/browser_helpers.js` | 746 | Browser JS | *(none)* | **Keep** | Playwright client-side DOM and visual mark injection helper. |
| 21 | `tools/browsergym_eval.py` | 236 | Automation | *(none)* | **Keep** | BrowserGym Web Agent Benchmark harness. |
| 22 | `tools/bug_reporter.py` | 255 | Automation | `report-bug` | **Keep** | Actively wired to CLI subcommand `agent-qa report-bug`. |
| 23 | `tools/build_consolidated_report.py` | 1643 | Reporting | *(none)* | 🔴 **Prune** | Hardcoded one-off script targeting non-existent HTML files. Dead code. |
| 24 | `tools/bump_version.py` | 416 | Packaging | `release` | **Keep** | Actively wired to CLI subcommand `agent-qa release`. |
| 25 | `tools/cache_resolver.py` | 1223 | Automation | `heal` | **Keep** | Actively wired to CLI subcommand `agent-qa heal`. |
| 26 | `tools/chaos_resilience_probe.py` | 362 | Automation | *(none)* | **Keep** | UI and API chaos fault injection probe. |
| 27 | `tools/check_env.py` | 429 | Automation | `doctor` | **Keep** | Official environment doctor wired to `agent-qa doctor`. |
| 28 | `tools/check_version_sync.py` | 283 | Automation | `check-version` | **Keep** | Actively wired to CLI subcommand `agent-qa check-version`. |
| 29 | `tools/ci_healing_hook.py` | 129 | Automation | `ci-hook` | **Keep** | Actively wired to CLI subcommand `agent-qa ci-hook`. |
| 30 | `tools/cldr_l10n_verifier.py` | 309 | Automation | `cldr` | **Keep** | Active runtime format crash on line 245. Fix requires escaping `%%`. |
| 31 | `tools/cli.py` | 1934 | Orchestrator | *(none)* | **Keep** | Mission-critical CLI orchestrator and Quality Gates DoD engine. |
| 32 | `tools/config_decoupler.py` | 256 | Automation | `decouple-config` | **Keep** | Actively wired to CLI subcommand `agent-qa decouple-config`. |
| 33 | `tools/contract_validator.py` | 141 | Automation | *(none)* | **Keep** | Swarm data contract validator. |
| 34 | `tools/core/__init__.py` | 73 | Core Module | *(none)* | **Keep** | Package exports and initialization. |
| 35 | `tools/core/adapters.py` | 431 | Core Module | *(none)* | **Keep** | Unified adapters across LLM providers and test execution runtimes. |
| 36 | `tools/core/bm25_retriever.py` | 218 | Core Module | *(none)* | **Keep** | BM25 lexical ranker for semantic memory retrieval. |
| 37 | `tools/core/circuit_breaker.py` | 263 | Core Module | *(none)* | **Keep** | Real-time token budget watchdog, rate limiter, and circuit breaker. |
| 38 | `tools/core/cli_runtime.py` | 66 | Core Module | *(none)* | **Keep** | Shared CLI argument normalization and formatting utilities. |
| 39 | `tools/core/file_lock.py` | 348 | Core Module | *(none)* | **Keep** | Cross-platform advisory file lock preventing concurrency race conditions. |
| 40 | `tools/core/i18n.py` | 396 | Core Module | *(none)* | **Keep** | Bilingual English/Vietnamese internationalization subsystem. |
| 41 | `tools/core/memory_bus.py` | 913 | Core Module | *(none)* | **Keep** | Unified event and episodic memory bus for multi-agent coordination. |
| 42 | `tools/core/process_supervisor.py` | 414 | Core Module | *(none)* | **Keep** | Reusable process group supervisor guaranteeing clean subagent teardown. |
| 43 | `tools/core/provider_usage_adapter.py` | 383 | Core Module | *(none)* | **Keep** | Adapters calculating token usage across OpenAI, Anthropic, Gemini. |
| 44 | `tools/core/telemetry.py` | 534 | Core Module | *(none)* | **Keep** | Structured JSON and console telemetry emitter. |
| 45 | `tools/core/token_estimator.py` | 362 | Core Module | *(none)* | **Keep** | Heuristic character-to-token estimator for model context boundaries. |
| 46 | `tools/count_tokens.py` | 1328 | Automation | `tokens` | **Keep** | Actively wired to CLI subcommand `agent-qa tokens`. |
| 47 | `tools/coverage_reporter.py` | 245 | Automation | *(none)* | **Keep** | Statement and branch coverage evaluator. Missing CLI binding. |
| 48 | `tools/create_mock_docx.py` | 107 | Test Fixture | *(none)* | 🟡 **Consolidate** | Test fixture generator. Relocate to `tests/fixtures/`. |
| 49 | `tools/cvss_calculator.py` | 412 | Automation | `cvss` | **Keep** | Actively wired to CLI subcommand `agent-qa cvss`. |
| 50 | `tools/dashboard_generator.py` | 2405 | Automation | `dashboard` | **Keep** | Actively wired to CLI subcommand `agent-qa dashboard`. |
| 51 | `tools/db_sandbox.py` | 1008 | Automation | *(none)* | **Keep** | Zero-pollution ephemeral DB sandbox. Missing CLI binding. |
| 52 | `tools/debt_harvester.py` | 248 | Automation | `debt` | **Keep** | Actively wired to CLI subcommand `agent-qa debt`. |
| 53 | `tools/diagram_architect.py` | 222 | Automation | *(none)* | **Keep** | Mermaid/SVG test architecture visualizer. Missing CLI binding. |
| 54 | `tools/distill_log.py` | 507 | Automation | `distill` | **Keep** | Actively wired to CLI subcommand `agent-qa distill`. |
| 55 | `tools/distill_skill.py` | 206 | Automation | *(none)* | **Keep** | Dual-model prompt distillation tool. |
| 56 | `tools/dspy_qa_signatures.py` | 460 | AI Tuning | *(none)* | 🟡 **Consolidate** | Unify with MIPRO and TextGrad into `tools/assertion_optimizer.py`. |
| 57 | `tools/e2e_flow_prober.py` | 135 | Automation | *(none)* | **Keep** | End-to-end user journey prober. |
| 58 | `tools/etl_data_reconciler.py` | 460 | Automation | `etl` | **Keep** | Actively wired to CLI subcommand `agent-qa etl`. |
| 59 | `tools/export_postman_collection.py` | 948 | Automation | `export-postman` | **Keep** | Actively wired to CLI subcommand `agent-qa export-postman`. |
| 60 | `tools/flaky_detector.py` | 392 | Automation | `flaky` | **Keep** | Actively wired to CLI subcommand `agent-qa flaky`. |
| 61 | `tools/fsm_enforcer.py` | 450 | Orchestration | *(none)* | 🟡 **Consolidate** | Unify with `fsm_middleware.py` and expose as `agent-qa fsm`. |
| 62 | `tools/fsm_middleware.py` | 401 | Orchestration | *(none)* | 🟡 **Consolidate** | Unify with `fsm_enforcer.py` as runtime proxy middleware. |
| 63 | `tools/fuzz_payloads.py` | 200 | Library | *(none)* | **Keep** | Pre-computed edge-case fuzzing payloads for API/UI validation. |
| 64 | `tools/generate_allure_report.py` | 91 | Reporting | *(none)* | **Keep** | Allure HTML report generator. Missing CLI binding. |
| 65 | `tools/generate_api_matrix.py` | 196 | Automation | `api-matrix` | **Keep** | Actively wired to CLI subcommand `agent-qa api-matrix`. |
| 66 | `tools/generate_jmx_plan.py` | 1333 | Automation | `generate-jmx` | **Keep** | Actively wired to CLI subcommand `agent-qa generate-jmx`. |
| 67 | `tools/generate_sbom.py` | 252 | Automation | *(none)* | **Keep** | Software Bill of Materials generator. Missing CLI binding. |
| 68 | `tools/generate_tc_from_story.py` | 206 | Automation | `generate-tc` | **Keep** | Actively wired to CLI subcommand `agent-qa generate-tc`. |
| 69 | `tools/generate_test_reports.py` | 136 | Reporting | *(none)* | **Keep** | Consolidated test report aggregator. Missing CLI binding. |
| 70 | `tools/generate_tool_catalog.py` | 512 | Automation | *(none)* | **Keep** | Tool catalog JSON schema generator. Missing CLI binding. |
| 71 | `tools/gherkin_suite.py` | 758 | Automation | `gherkin` | **Keep** | Actively wired to CLI subcommand `agent-qa gherkin`. |
| 72 | `tools/git_pre_commit_guard.py` | 511 | Automation | *(none)* | **Keep** | Pre-commit architectural guard. Missing CLI binding. |
| 73 | `tools/git_worktree_manager.py` | 188 | Automation | *(none)* | **Keep** | Concurrent git worktree isolation manager. Missing CLI binding. |
| 74 | `tools/goldfish_review.py` | 366 | Automation | `review-spec` | **Keep** | Actively wired to CLI subcommand `agent-qa review-spec`. |
| 75 | `tools/heal/__init__.py` | 31 | Package | *(none)* | **Keep** | Package exports and initialization. |
| 76 | `tools/heal_pr_automator.py` | 223 | Automation | `heal-pr` | **Keep** | Actively wired to CLI subcommand `agent-qa heal-pr`. |
| 77 | `tools/heap_leak_analyzer.py` | 257 | Automation | `heap-leak` | **Keep** | Actively wired to CLI subcommand `agent-qa heap-leak`. |
| 78 | `tools/heuristic_locator_matcher.py` | 354 | Library | *(none)* | **Keep** | 3-layer heuristic locator matcher used by `auto_heal.py`. |
| 79 | `tools/hub_publisher.py` | 709 | Packaging | `publish` | **Keep** | Actively wired to CLI subcommand `agent-qa publish`. |
| 80 | `tools/humanize_linter.py` | 445 | Quality | *(none)* | **Keep** | Anti-AI slop linter. Missing CLI binding. |
| 81 | `tools/infer_linter.py` | 1013 | Quality | `lint` | **Keep** | Actively wired to CLI subcommand `agent-qa lint`. |
| 82 | `tools/init_config.py` | 303 | Automation | `init-config` | **Keep** | Actively wired to CLI subcommand `agent-qa init-config`. |
| 83 | `tools/interview_story.py` | 139 | Automation | *(none)* | **Keep** | Pocock Grilling ambiguity interviewer. Missing CLI binding. |
| 84 | `tools/jira_sync.py` | 566 | Integration | `sync-jira` | **Keep** | Actively wired to CLI subcommand `agent-qa sync-jira`. |
| 85 | `tools/jtl_analyzer.py` | 499 | Automation | `analyze-jtl` | **Keep** | Actively wired to CLI subcommand `agent-qa analyze-jtl`. |
| 86 | `tools/lint/__init__.py` | 33 | Package | *(none)* | **Keep** | Package exports and initialization. |
| 87 | `tools/lint_ai_docs.py` | 391 | Quality | *(none)* | **Keep** | AI documentation convention linter. Missing CLI binding. |
| 88 | `tools/lookup_tc.py` | 168 | Automation | `lookup-tc` | **Keep** | Actively wired to CLI subcommand `agent-qa lookup-tc`. |
| 89 | `tools/lookup_xpath.py` | 170 | Automation | `lookup-xpath` | **Keep** | Actively wired to CLI subcommand `agent-qa lookup-xpath`. |
| 90 | `tools/matrix_sharder.py` | 151 | Automation | `shard` | **Keep** | Actively wired to CLI subcommand `agent-qa shard`. |
| 91 | `tools/mcp/__init__.py` | 21 | Package | *(none)* | **Keep** | Package exports and initialization. |
| 92 | `tools/mcp_docx_server.ps1` | 13 | PowerShell | *(none)* | **Keep** | FastMCP JSON-RPC stdio launcher script for Docx server. |
| 93 | `tools/mcp_docx_server.py` | 851 | MCP Server | `mcp-docx` | **Keep** | Actively wired to CLI subcommand `agent-qa mcp-docx`. |
| 94 | `tools/mcp_excel_server.ps1` | 13 | PowerShell | *(none)* | **Keep** | FastMCP JSON-RPC stdio launcher script for Excel server. |
| 95 | `tools/mcp_excel_server.py` | 444 | MCP Server | `mcp-excel` | **Keep** | Actively wired to CLI subcommand `agent-qa mcp-excel`. |
| 96 | `tools/mcp_server.py` | 816 | MCP Server | `mcp-serve` | **Keep** | Stdio hang on `--help`. Fix requires intercepting help arguments. |
| 97 | `tools/md_to_xlsx.py` | 330 | Exporter | *(none)* | 🟡 **Consolidate** | Merge into `template_excel_exporter.py` which already has 12-col layout. |
| 98 | `tools/mechanical_ui_gate.py` | 245 | Quality | *(none)* | 🟡 **Consolidate** | Integrate contrast/layout checks into `tools/wcag_audit.py`. |
| 99 | `tools/memory_cache.db` | 2615 | Database | *(none)* | **Keep** | Episodic self-healing semantic cache database. |
| 100 | `tools/micro_mutator.py` | 1031 | Quality | `mutate` | **Keep** | Actively wired to CLI subcommand `agent-qa mutate`. |
| 101 | `tools/mipro_assertion_tuner.py` | 210 | AI Tuning | *(none)* | 🟡 **Consolidate** | Unify with DSPy and TextGrad into `tools/assertion_optimizer.py`. |
| 102 | `tools/mobile_resilience_sentinel.py` | 273 | Automation | *(none)* | **Keep** | Mobile session crash watchdog. Missing CLI binding. |
| 103 | `tools/network_mock_shield.py` | 314 | Automation | `mock-shield` | **Keep** | Actively wired to CLI subcommand `agent-qa mock-shield`. |
| 104 | `tools/newman_analyzer.py` | 387 | Automation | `analyze-newman` | **Keep** | Actively wired to CLI subcommand `agent-qa analyze-newman`. |
| 105 | `tools/observability_tester.py` | 235 | Automation | *(none)* | **Keep** | OpenTelemetry transaction assertion harness. Missing CLI binding. |
| 106 | `tools/omni_emitter.py` | 582 | Library | *(none)* | **Keep** | Universal polyglot emitter library for transpiler. |
| 107 | `tools/omni_parser.py` | 453 | Library | *(none)* | **Keep** | Universal polyglot parser library for transpiler. |
| 108 | `tools/omni_transpiler.py` | 171 | Automation | `migrate` | **Keep** | Actively wired to CLI subcommand `agent-qa migrate`. |
| 109 | `tools/openxml_guard.py` | 438 | Library | *(none)* | **Keep** | OpenXML security and protocol defence library. |
| 110 | `tools/output_formatter.py` | 185 | Library | *(none)* | **Keep** | Standardized JSON/table output formatter library. |
| 111 | `tools/package_release.py` | 350 | Packaging | *(none)* | 🟡 **Consolidate** | Merge into `tools/hub_publisher.py` as internal stage. |
| 112 | `tools/pairwise_generator.py` | 177 | Automation | *(none)* | **Keep** | 2-way combinatorial test generator. Missing CLI binding. |
| 113 | `tools/payment_interop_simulator.py` | 337 | Automation | *(none)* | **Keep** | Payment gateway simulator. Missing CLI binding. |
| 114 | `tools/pentest_scope_guard.py` | 944 | Security | *(none)* | **Keep** | DAST safety scope firewall. Missing CLI binding. |
| 115 | `tools/perf/__init__.py` | 27 | Package | *(none)* | **Keep** | Package exports and initialization. |
| 116 | `tools/perf/benchmark_perf_runner.py` | 267 | Automation | *(none)* | **Keep** | Performance benchmark runner. Missing CLI binding. |
| 117 | `tools/pinpoint_failure.py` | 205 | Automation | `pinpoint-failure` | **Keep** | Actively wired to CLI subcommand `agent-qa pinpoint-failure`. |
| 118 | `tools/pre_bash_guard.py` | 122 | Security | *(none)* | **Keep** | Active shell command safety validator. Missing CLI binding. |
| 119 | `tools/pre_push_guard.py` | 306 | Quality | `pre-push` | **Keep** | Actively wired to CLI subcommand `agent-qa pre-push`. |
| 120 | `tools/project_state.py` | 198 | Quality | *(none)* | **Keep** | Project state machine diagnostic tool. Missing CLI binding. |
| 121 | `tools/qa_event_stream.py` | 358 | Orchestration | *(none)* | **Keep** | Immutable QA event stream replay engine. Missing CLI binding. |
| 122 | `tools/regulatory_compliance.py` | 336 | Quality | `compliance` | **Keep** | Actively wired to CLI subcommand `agent-qa compliance`. |
| 123 | `tools/repo_map.json` | 341 | Metadata | *(none)* | **Keep** | Pre-computed AST repository knowledge graph. |
| 124 | `tools/repo_map.json.lock` | 1 | Ephemeral | *(none)* | 🔴 **Prune** | Ephemeral runtime lockfile committed to git repository. |
| 125 | `tools/repo_map.py` | 551 | Automation | *(none)* | **Keep** | Repository AST knowledge graph compiler. Missing CLI binding. |
| 126 | `tools/repo_map.txt` | 81 | Metadata | *(none)* | **Keep** | Text-format AST repository knowledge graph. |
| 127 | `tools/repo_map.txt.lock` | 1 | Ephemeral | *(none)* | 🔴 **Prune** | Ephemeral runtime lockfile committed to git repository. |
| 128 | `tools/report/__init__.py` | 35 | Package | *(none)* | **Keep** | Package exports and initialization. |
| 129 | `tools/reversible_sandbox.py` | 500 | Automation | *(none)* | **Keep** | Reversible execution sandbox. Missing CLI binding. |
| 130 | `tools/rules_router.py` | 1223 | Routing | `rules-router` | **Keep** | Actively wired to CLI subcommand `agent-qa rules-router`. |
| 131 | `tools/runaway_stopper.py` | 181 | Quality | *(none)* | 🟡 **Consolidate** | Redundant turn/token limiter. Merge into `tools/core/circuit_breaker.py`. |
| 132 | `tools/safety_firewall.py` | 440 | Security | `safety-check` | **Keep** | Actively wired to CLI subcommand `agent-qa safety-check`. |
| 133 | `tools/security_coverage_ledger.py` | 538 | Security | *(none)* | **Keep** | Mathematical security coverage ledger. Missing CLI binding. |
| 134 | `tools/security_scanner.py` | 309 | Security | *(none)* | **Keep** | Multi-layer dependency security scanner. Missing CLI binding. |
| 135 | `tools/senior_code_review.py` | 407 | Quality | `review` | **Keep** | Actively wired to CLI subcommand `agent-qa review`. |
| 136 | `tools/setup_project.py` | 803 | Automation | `uninstall` | **Keep** | Actively wired to CLI subcommand `agent-qa uninstall`. |
| 137 | `tools/skill_canonical_digest.py` | 302 | Library | *(none)* | **Keep** | Canonical skill digest generator used by skill indexers. |
| 138 | `tools/skill_collision_guard.py` | 304 | Quality | *(none)* | **Keep** | Skill collision and overlap guard. Missing CLI binding. |
| 139 | `tools/skill_profiles.py` | 287 | Automation | `skills` | **Keep** | Actively wired to CLI subcommand `agent-qa skills`. |
| 140 | `tools/skill_vault.py` | 481 | Automation | *(none)* | **Keep** | Lifelong Page Object repository. Missing CLI binding. |
| 141 | `tools/skillspector.py` | 1283 | Security | `skillspector` | **Keep** | Actively wired to CLI subcommand `agent-qa skillspector`. |
| 142 | `tools/slide_deck_exporter.py` | 477 | Reporting | *(none)* | **Keep** | HTML5 executive slide deck generator. Missing CLI binding. |
| 143 | `tools/slow_test_profiler.py` | 245 | Automation | `slow-tests` | **Keep** | Actively wired to CLI subcommand `agent-qa slow-tests`. |
| 144 | `tools/smart_visual_masker.py` | 135 | Automation | `visual-mask` | **Keep** | Actively wired to CLI subcommand `agent-qa visual-mask`. |
| 145 | `tools/spec_drift_sentinel.py` | 438 | Automation | `drift-check` | **Keep** | Actively wired to CLI subcommand `agent-qa drift-check`. |
| 146 | `tools/swe_qa_aci.py` | 369 | Automation | *(none)* | **Keep** | Agent-Computer Interface for surgical editing. Missing CLI binding. |
| 147 | `tools/synapse_doctor.py` | 324 | Automation | *(none)* | 🟡 **Consolidate** | Unwired duplicate doctor script. Merge unique checks into `check_env.py`. |
| 148 | `tools/synapse_observer.py` | 485 | Quality | *(none)* | **Keep** | Cognitive observer & tradeoff auditor. Missing CLI binding. |
| 149 | `tools/synapse_qa_bench.py` | 190 | Quality | *(none)* | **Keep** | Autonomous tool calling accuracy benchmark. Missing CLI binding. |
| 150 | `tools/sync_agent_rules.py` | 438 | Automation | `sync-rules` | **Keep** | Actively wired to CLI subcommand `agent-qa sync-rules`. |
| 151 | `tools/sync_skills_manifest.py` | 166 | Automation | *(none)* | 🟡 **Consolidate** | Orphaned script. Merge into `tools/validate_skills_schema.py`. |
| 152 | `tools/task_memory_manager.py` | 287 | Automation | *(none)* | **Keep** | Cross-session task memory manager. Missing CLI binding. |
| 153 | `tools/telemetry_correlator.py` | 400 | Automation | `correlate-telemetry` | **Keep** | Actively wired to CLI subcommand `agent-qa correlate-telemetry`. |
| 154 | `tools/template_excel_exporter.py` | 514 | Exporter | `export-excel` | **Keep** | Actively wired to CLI subcommand `agent-qa export-excel`. |
| 155 | `tools/templates/jmeter-distributed/README.md` | 54 | Documentation | *(none)* | **Keep** | Distributed JMeter docker-compose setup runbook. |
| 156 | `tools/templates/jmeter-distributed/docker-compose.yml` | 83 | Template | *(none)* | **Keep** | Distributed JMeter master-worker container cluster template. |
| 157 | `tools/test_impact.py` | 422 | Automation | `impact` | **Keep** | Actively wired to CLI subcommand `agent-qa impact`. |
| 158 | `tools/test_memory_os.py` | 510 | Automation | *(none)* | **Keep** | Hierarchical QA test memory OS. Missing CLI binding. |
| 159 | `tools/textgrad_mutation_optimizer.py` | 237 | AI Tuning | *(none)* | 🟡 **Consolidate** | Unify with DSPy and MIPRO into `tools/assertion_optimizer.py`. |
| 160 | `tools/tmmi_auditor.py` | 172 | Automation | `tmmi` | **Keep** | Actively wired to CLI subcommand `agent-qa tmmi`. |
| 161 | `tools/tms_sync_bridge.py` | 834 | Integration | *(none)* | **Keep** | Universal ALM/TMS sync bridge. Missing CLI binding. |
| 162 | `tools/token_telemetry.py` | 224 | Telemetry | *(none)* | 🟡 **Consolidate** | Merge token logging into `count_tokens.py` or core telemetry. |
| 163 | `tools/tot_exploratory_tester.py` | 256 | Automation | *(none)* | **Keep** | Tree-of-Thoughts exploratory testing engine. Missing CLI binding. |
| 164 | `tools/trace_data_flow.py` | 243 | Automation | `trace-data-flow` | **Keep** | Actively wired to CLI subcommand `agent-qa trace-data-flow`. |
| 165 | `tools/traffic_session_converter.py` | 259 | Automation | *(none)* | **Keep** | HAR traffic to k6 scenario converter. Missing CLI binding. |
| 166 | `tools/trend_analytics.py` | 314 | Automation | `trend` | **Keep** | Actively wired to CLI subcommand `agent-qa trend`. |
| 167 | `tools/ui_server.py` | 403 | Web UI | `ui` | **Keep** | Actively wired to CLI subcommand `agent-qa ui`. |
| 168 | `tools/universal_ir.py` | 491 | Library | *(none)* | **Keep** | Universal Testing Intermediate Representation core schema and AST. |
| 169 | `tools/update_sentinel.py` | 455 | Automation | `update` | **Keep** | Actively wired to CLI subcommand `agent-qa update`. |
| 170 | `tools/validate_groovy_scripts.py` | 176 | Quality | `validate-groovy` | **Keep** | Actively wired to CLI subcommand `agent-qa validate-groovy`. |
| 171 | `tools/validate_host_interop.py` | 485 | Quality | *(none)* | **Keep** | Cross-host IDE interop verifier. Missing CLI binding. |
| 172 | `tools/validate_skills_schema.py` | 575 | Quality | *(none)* | **Keep** | Skill schema and frontmatter validator. Missing CLI binding. |
| 173 | `tools/vcr_cassette_guard.py` | 432 | Automation | *(none)* | **Keep** | Network VCR cassette recorder and sanitizer. Missing CLI binding. |
| 174 | `tools/verify_all.py` | 2015 | Verification | `verify` | **Keep** | Actively wired to CLI subcommand `agent-qa verify`. |
| 175 | `tools/visual_diff_canvas.py` | 146 | Automation | `canvas-diff` | **Keep** | Actively wired to CLI subcommand `agent-qa canvas-diff`. |
| 176 | `tools/visual_som_helper.py` | 553 | Automation | `som` | **Keep** | Actively wired to CLI subcommand `agent-qa som`. |
| 177 | `tools/vpat_exporter.py` | 428 | Reporting | `vpat` | **Keep** | Actively wired to CLI subcommand `agent-qa vpat`. |
| 178 | `tools/watch_mode.py` | 308 | Automation | `watch` | **Keep** | Actively wired to CLI subcommand `agent-qa watch`. |
| 179 | `tools/wcag_audit.py` | 242 | Quality | `wcag-audit` | **Keep** | Actively wired to CLI subcommand `agent-qa wcag-audit`. |
| 180 | `tools/welcome_page.py` | 290 | Web UI | `welcome` | **Keep** | Actively wired to CLI subcommand `agent-qa welcome`. |


---

## 4. Subsystem 3: AI Agents Audit (`.agents/agents/`)

### 4.1 Swarm Finite State Machine (FSM) Alignment
Synapse Hub organizes its autonomous workforce into a 5-Stage Finite State Machine governed by a Single Front-Door orchestrator (`AGENTS.md` §4, `docs/ARCHITECTURE.en.md` §5). All 9 agents defined in `.agents/agents/*.md` correspond to distinct, necessary architectural roles within this lifecycle:

```
5-Stage Finite State Machine (FSM):
┌────────────────────────────────────────────────────────┐
│             Single Front-Door: Orchestrator            │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ Stage 1: Discovery & Design                            │
│ ├─ live-explorer  (DOM/AOM live probing, <200ms CDP)   │
│ └─ test-designer  (AI-RBT, ambiguities, Excel suites)  │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ Stage 2: Code Synthesis                                │
│ ├─ pom-crafter    (Clean POM, Flat Architecture, Som)  │
│ └─ api-engineer   (OpenAPI matrices, CDC pacts, mocks) │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ Stage 3: Headless Execution                            │
│ ├─ test-runner    (CLI execution, Playwright/KRE/Bats) │
│ ├─ perf-engineer  (k6/JMeter load profiles, CWV, APM)  │
│ └─ api-engineer   (REST/GraphQL fuzzing, schema check) │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ Stage 4: Failure Autopsy & Healing                     │
│ └─ failure-analyst (RCA, JUnit XML, Agent Red mutation)│
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ Stage 5: Final Acceptance Definition of Done           │
│ └─ quality-gatekeeper (10 Quality Gates, Air-Gap Audit)│
└────────────────────────────────────────────────────────┘
```

Because every agent occupies an essential station in the 5-Stage FSM, **0 agents are marked for pruning or deprecation**. However, 5 of the 9 agents suffer from operational drift, tool bloat, or role overlap, and require precise scoping and refactoring.

---

### 4.2 Comprehensive Agent Evaluation Matrix

| # | Agent Name | Lines / Bytes | FSM Stage | Status | Tool Wiring Health | Identified Drift & Overlap | Recommended Action |
|---|---|:---:|---|:---:|---|---|---|
| 1 | `orchestrator.md` | 104 / 7,055 | Front-Door | **Keep (Refactor)** | 10 unreferenced frontmatter tools | Directly invokes Stage 1 tools (`interview_story.py`, `goldfish_review.py`), violating Lean Coordination Mode. | Prune 10 dead tools from frontmatter. Delegate requirement interviewing and spec review strictly to `test-designer`. |
| 2 | `live-explorer.md` | 70 / 4,849 | Stage 1 (Discovery) | **Keep** | Clean | Minor: `visual_som_helper.py` in frontmatter is omitted from body text. | Maintain as primary DOM/AOM probing subagent. Preserve CDP idle <200ms and safety firewall hooks. |
| 3 | `test-designer.md` | 73 / 5,674 | Stage 1 (Design) | **Keep** | Clean | Overlapped by orchestrator directly running requirement analysis tools. | Establish exclusive ownership of `interview_story.py`, `goldfish_review.py`, and `rbt-manual-testing`. |
| 4 | `pom-crafter.md` | 112 / 8,126 | Stage 2 (Synthesis) | **Keep (Scope)** | Severe API creep | Frontmatter and body include Postman, Swagger, and API fuzzing tools (`api_fuzzer.py`, `export_postman_collection.py`, etc.). | **Purge all API-specific tools and responsibilities**. Focus exclusively on Clean POM and UI/mobile Page Classes. |
| 5 | `api-engineer.md` | 75 / 6,375 | Stage 2 & Stage 3 | **Keep (Critical)** | Missing rule reference | Line 30 references deleted `.agents/rules/api_testing_rules.md` (404 link). | Re-link to restored `api_testing_rules.md`. Retain as dedicated API and contract engineering subagent. |
| 6 | `test-runner.md` | 67 / 5,103 | Stage 3 (Execution) | **Keep (Refactor)** | FSM bypass | Invokes `ci_healing_hook.py` to heal locators silently inside the runner, bypassing Stage 4 (`failure-analyst`). | Remove in-runner self-healing responsibility. Enforce strict dispatch of JUnit XML execution artifacts to `failure-analyst`. |
| 7 | `perf-engineer.md` | 82 / 7,032 | Stage 3 (Execution) | **Keep (Cleanup)** | External skill leak | Declares `debug-optimize-lcp` and `memory-leak-debugging` in `skills:` list, which do not exist in local `.agents/skills/`. | Clean up external plugin skills from frontmatter `skills:` list, or document them as optional MCP plugin dependencies. |
| 8 | `failure-analyst.md` | 75 / 5,917 | Stage 4 (Healing) | **Keep** | Minor frontmatter gap | 3 frontmatter tools are omitted from body text (`agentless_patcher.py`, `auto_heal_reflexion.py`, `pinpoint_failure.py`). | Retain as primary RCA and auto-healing engine (Agent Red). Harmonize frontmatter tool declarations with body instructions. |
| 9 | `quality-gatekeeper.md` | 87 / 6,558 | Stage 5 (DoD Gate) | **Keep (Critical)** | Clean | Minor: 3 frontmatter tools omitted from body text (`verify_author.py`, `audit_threat_vectors.py`, `wcag_audit.py`). | Retain as air-gapped Definition-of-Done gatekeeper enforcing the 10 Quality Gates. |

---

### 4.3 Specific Agent Scoping & Remediation Blueprints

#### 1. Scope Purification for `pom-crafter.md`
- **Current Issue**: `pom-crafter.md` has accumulated significant API testing responsibilities that belong to `api-engineer.md`. Its frontmatter declares `api_fuzzer.py`, `export_postman_collection.py`, and `fuzz_payloads.py`. Lines 43–44 and 86–88 instruct `pom-crafter` to:
  - *"Detect API Breaking Changes via `tools/api_drift_sentinel.py` before updating UI Page Classes"*
  - *"Intercept and mock unstable 3rd-party APIs via `tools/network_mock_shield.py`"*
  - *"tools/generate_api_matrix.py: Generates boundary and negative matrices from Swagger contracts"*
- **Remediation**:
  1. Remove `api_fuzzer.py`, `export_postman_collection.py`, `fuzz_payloads.py`, `api_drift_sentinel.py`, and `generate_api_matrix.py` from `pom-crafter.md`.
  2. Confine `pom-crafter` strictly to DOM locators, Clean POM Page Classes, and Mobile Screen Object Models (SOM).
  3. When an API contract changes, `pom-crafter` must receive updated mock contracts from `api-engineer` rather than parsing Swagger specs directly.

#### 2. Resolving FSM Bypass in `test-runner.md`
- **Current Issue**: Line 30 states: *"Trigger CI/CD silent self-healing hook via `tools/ci_healing_hook.py` when locator failures occur on runner machines."* Line 36 then states: *"Detect test failures immediately and dispatch JUnit XML execution reports to `failure-analyst`."*
- If the runner heals locators silently during execution, it circumvents Stage 4 failure analysis, obscuring test flakiness and mutating code without audit logs.
- **Remediation**:
  1. Remove `ci_healing_hook.py` and silent healing from `test-runner.md`.
  2. Mandate that `test-runner` executes tests purely headlessly, records artifacts (JUnit XML, video, traces, console logs), and hands off failures strictly to `failure-analyst`.

#### 3. Pruning Frontmatter Bloat & Preserving Lean Mode in `orchestrator.md`
- **Current Issue**:
  - The frontmatter lists 10 tools that are never mentioned or utilized in the body text: `check_version_sync.py`, `config_decoupler.py`, `count_tokens.py`, `dashboard_generator.py`, `dspy_qa_signatures.py`, `qa_event_stream.py`, `test_memory_os.py`, `tot_exploratory_tester.py`, `update_sentinel.py`, and `watch_mode.py`.
  - Body lines 89–90 instruct the orchestrator to execute `tools/interview_story.py` and `tools/goldfish_review.py` directly, violating the orchestrator's own "Lean Coordination Mode" (lines 60–72).
- **Remediation**:
  1. Prune the 10 unreferenced tools from frontmatter.
  2. Delegate requirement ambiguity interviewing and spec review exclusively to `test-designer`.

#### 4. Cleansing External Plugin References in `perf-engineer.md`
- **Current Issue**: The frontmatter `skills:` list declares `debug-optimize-lcp` and `memory-leak-debugging`. These are external Chrome DevTools MCP skills that do not exist inside `.agents/skills/`. In environments lacking the external plugin, agent initialization throws missing-skill warnings.
- **Remediation**: Replace external skill names with local workspace skills (`web-vitals-and-performance-profiler`, `backend-load-and-stress-patterns`) and document Chrome DevTools MCP as an optional external runtime accelerator.

---

## 5. Subsystem 4: Rules Audit (`.agents/rules/` and `AGENTS.md`)

### 5.1 Overview & Physical Token Footprint
The repository maintains **14 rule files** under `.agents/rules/`, plus platform-wide invariants codified in root `AGENTS.md`. The 14 rule files consume 495 lines, 40,900 bytes, and an estimated ~10,225 tokens when fully hydrated.

```
Rule Token Footprint Distribution:
performance_testing_rules.md : 1,167 tokens (██████████████)
cypress_rules.md             :   931 tokens (███████████)
stack-auto-router.md         :   880 tokens (██████████)
security_testing_rules.md    :   837 tokens (██████████)
mandatory-playwright-live.md :   824 tokens (█████████)
mobile_appium_rules.md       :   808 tokens (█████████)
systematic-debugging.md      :   778 tokens (█████████)
skill-precedence.md          :   760 tokens (█████████)
git-push-protocol.md         :   742 tokens (████████)
context-engineering.md       :   734 tokens (████████)
author-integrity-guard.md    :   618 tokens (███████)
lessons-learned.md           :   516 tokens (██████)
communication-style.md       :   370 tokens (████)
graphify.md                  :   255 tokens (███)
TOTAL                        : ~10,225 tokens
```

---

### 5.2 Forensic Investigation: Commit `e229dfd` & The Missing `api_testing_rules.md`

#### Forensic Background
1. In `.agents/agents/api-engineer.md` line 30, the agent manifest mandates:
   ```markdown
   > - **Mandatory Rule:** Adheres strictly to [api_testing_rules.md](../rules/api_testing_rules.md).
   ```
   However, attempting to resolve `.agents/rules/api_testing_rules.md` results in an immediate file-not-found error.
2. Forensic inspection of `git log -S "api_testing_rules.md"` identified commit `e229dfd08dc0db4f15db08a4a88848b2e1d91f91`:
   - **Commit Subject**: `fix(packaging): restore 14 rules standard, synchronize token benchmark, and update router perf cap`
   - **Action**: Deleted `.agents/rules/api_testing_rules.md` (74 lines, 5,420 bytes).
3. **Forensic Root Cause**: Earlier commit `2d0e58e` / `3454238` had introduced `.agents/rules/stack-auto-router.md` to document the router tool, unintentionally raising the rule count from 14 to 15. Because `benchmarks/CONTEXT_TOKEN_BENCHMARK.md` line 29 explicitly codified a fixed benchmark methodology (*"Dynamically enumerates all 14 rules and 56 skills in repository without static per-skill multiplier assumptions"*), commit `e229dfd` deleted `api_testing_rules.md` to force the rule count back to 14.

#### Damaging Consequences of Deletion
- **Broken Reference**: `api-engineer.md` carries a dangling 404 hyperlink.
- **Lost Standards**: The deleted `api_testing_rules.md` contained critical engineering invariants:
  - Google SRE Four Golden Signals (Latency, Traffic, Errors, Saturation).
  - Percentile Tail Latency (P50 < 100ms, P95 < 250ms, P99 < 500ms).
  - Tiered Industry SLAs (Tiers 1–4, from 99.99% core checkout to 99.0% internal analytics).
  - IETF RFC 9110/9112/9113 HTTP protocol semantics and RFC 6585 rate limiting.
- **Router Asymmetry**: `tools/rules_router.py:120` maps `"api": ["systematic-debugging.md"]`. As a result, the `api` stack is the only stack in Synapse Hub without domain-specific testing rules.

#### Actionable Remediation
- **Prune/Deprecate** `stack-auto-router.md` from `.agents/rules/` (relocating its documentation to CLI help and docs).
- **Restore** `api_testing_rules.md` to `.agents/rules/api_testing_rules.md` using the exact historical content from commit `e229dfd^`.
- This simultaneously restores the missing API domain standards, fixes the dangling link in `api-engineer.md`, and perfectly preserves the 14-rule benchmark standard.

---

### 5.3 Analysis of Unrouted Rules in `tools/rules_router.py`

Inspecting `tools/rules_router.py` lines 105–122 reveals the static rule routing table:
```python
CORE_BASE_RULES = [
    "author-integrity-guard.md",
    "communication-style.md",
    "skill-precedence.md",
]

STACK_RULE_MAPPINGS = {
    "playwright": ["mandatory-playwright-live.md", "systematic-debugging.md"],
    "cypress": ["cypress_rules.md", "systematic-debugging.md"],
    "mobile": ["mobile_appium_rules.md", "systematic-debugging.md"],
    "katalon": ["systematic-debugging.md"],
    "selenium": ["systematic-debugging.md"],
    "performance": ["performance_testing_rules.md"],
    "security": ["security_testing_rules.md"],
    "api": ["systematic-debugging.md"],
    "git": ["git-push-protocol.md"],
}
```

**Discovery**: Exactly **4 out of 14 rules (28.6%)** are omitted from both `CORE_BASE_RULES` and `STACK_RULE_MAPPINGS`:
1. `lessons-learned.md` (516 tokens): Contains the critical 8-rule anti-pattern blacklist. Its frontmatter declares `trigger: always_on`, yet the router never injects it into any stack.
   - *Fix*: Add `lessons-learned.md` directly into `CORE_BASE_RULES`.
2. `context-engineering.md` (734 tokens): Codifies observation masking and micro-read principles, but is never routed.
   - *Fix*: Add to `CORE_BASE_RULES` or consolidate with `communication-style.md`.
3. `graphify.md` (255 tokens): Applies only when `graphify-out/` is present.
   - *Fix*: Inject dynamically in `rules_router.py` when `graphify-out/` directory exists.
4. `stack-auto-router.md` (880 tokens): Omitted from router tables and redundant with other rules.
   - *Fix*: Prune from `.agents/rules/`.

---

### 5.4 Cross-Rule Redundancies & Contradictions

#### 1. Swarm FSM Duplication in `mandatory-playwright-live.md`
- **Evidence**: Lines 11–17 of `mandatory-playwright-live.md` define the entire 5-Stage Swarm FSM:
  ```markdown
  - Stage 1: Discover & Design: live-explorer & test-designer
  - Stage 2: Craft: pom-crafter & api-engineer
  - Stage 3: Execute & Observe: test-runner & perf-engineer
  - Stage 4: Autopsy & Heal: failure-analyst
  - Stage 5: Acceptance DoD: quality-gatekeeper
  ```
- **Anomaly**: Header line 9 states: `> ⚠️ Contextual Activation Scope: This rule is activated ONLY when playwright.config.* exists or when running Web / Browser E2E automation.`
- Defining the universal swarm lifecycle inside a Playwright-specific rule file creates an architectural contradiction and wastes ~180 tokens per turn. Root `AGENTS.md` §4 is the single source of truth for the FSM.
- **Remediation**: Strip Section 1 from `mandatory-playwright-live.md` and retain Sections 2–5.

#### 2. Meta-Documentation Duplication in `stack-auto-router.md`
- **Evidence**:
  - Section 3 ("Adaptive Verification Fast Mode vs Full Gate") is a verbatim copy of `systematic-debugging.md` Section 2 ("Verification-First & Definition of Done").
  - Section 5 ("Active Pre-Tool Shell Guard") duplicates Anti-Patterns #7 and #8 from `lessons-learned.md`.
  - The file describes how `rules_router.py` operates rather than prescribing behavioral invariants for QA engineering.
- **Remediation**: Deprecate and remove from `.agents/rules/`.

---

### 5.5 Master Table of All Rules & Final Disposition

| # | Rule File Name | Tokens | Current Router Status | Verdict | Rationale & Forensic Evidence | Actionable Recommendation |
|---|---|:---:|:---:|:---:|---|---|
| 1 | `author-integrity-guard.md` | ~618 | `CORE_BASE_RULES` | 🟢 **Keep** | Protects MIT License attribution and author credit to Thế Vị (@TeeVee98). Essential for IDE bridges. | Maintain as-is in `CORE_BASE_RULES`. |
| 2 | `communication-style.md` | ~370 | `CORE_BASE_RULES` | 🟢 **Keep** | Concise guidelines for Vietnamese chat, English code, status badge, and cognitive observer. | Maintain as-is in `CORE_BASE_RULES`. |
| 3 | `context-engineering.md` | ~734 | **Not Routed** | 🟡 **Consolidate** | Micro-reading and observation masking invariants omitted from router. | Add to `CORE_BASE_RULES` in `rules_router.py` or merge with `communication-style.md`. |
| 4 | `cypress_rules.md` | ~931 | `cypress` stack | 🟢 **Keep** | Tailored Cypress standards: zero static sleep, `cy.intercept`, Clean POM architecture. | Maintain as-is for `cypress` stack. |
| 5 | `git-push-protocol.md` | ~742 | `git` stack | 🟢 **Keep** | Enforces zero push to Hub main; mandates `hub_publisher.py -y` release pipeline. | Maintain as-is for `git` stack. |
| 6 | `graphify.md` | ~255 | **Not Routed** | 🟡 **Consolidate** | Micro-rule (15 lines) active only when `graphify-out/` exists. | Merge into `context-engineering.md` or inject conditionally in router. |
| 7 | `lessons-learned.md` | ~516 | **Not Routed** | 🟢 **Keep (Route)** | Critical 8-rule anti-pattern blacklist with `trigger: always_on`, omitted from router. | **Add to `CORE_BASE_RULES`** in `tools/rules_router.py`. |
| 8 | `mandatory-playwright-live.md` | ~824 | `playwright` stack | 🟡 **Refactor** | Section 1 duplicates Swarm FSM from `AGENTS.md` §4 in a Playwright-only file. | Strip Section 1 (saving ~180 tokens/turn); retain Sections 2–5. |
| 9 | `mobile_appium_rules.md` | ~808 | `mobile` stack | 🟢 **Keep** | Robust mobile Screen Object Model (SOM) and locator hierarchy for iOS and Android. | Maintain as-is for `mobile` stack. |
| 10 | `performance_testing_rules.md` | ~1,167 | `performance` stack | 🟢 **Keep** | Non-functional testing standards: virtual user scaling, p95/p99 latency ceilings, APM telemetry. | Maintain as-is for `performance` stack. |
| 11 | `security_testing_rules.md` | ~837 | `security` stack | 🟢 **Keep** | 5-layer safety gate, target domain allowlisting, and rate limits for DAST scans. | Maintain as-is for `security` stack. |
| 12 | `skill-precedence.md` | ~760 | `CORE_BASE_RULES` | 🟢 **Keep** | Suppression rules (local skills override external plugins) and 1-to-1 dispatch routing. | Maintain as-is in `CORE_BASE_RULES`. |
| 13 | `stack-auto-router.md` | ~880 | **Not Routed** | 🔴 **Prune** | Meta-doc explaining router tool. Duplicates `systematic-debugging.md` and `lessons-learned.md`. Caused deletion of API rule. | **Prune/Deprecate from `.agents/rules/`**. Relocate content to `docs/`. |
| 14 | `systematic-debugging.md` | ~778 | 6 Stacks | 🟢 **Keep** | 4-phase scientific root-cause protocol and Definition-of-Done verification gates. | Maintain as-is across all code stacks. |
| 15 | `api_testing_rules.md` *(Deleted in `e229dfd`)* | ~1,800 | *Formerly `api`* | 🔵 **Restore** | Deleted to maintain arbitrary 14-rule count. Restores Google SRE Golden Signals, P50/P95 SLAs, and RFC 9110. | **Restore to `.agents/rules/api_testing_rules.md`** and re-wire to `api` stack. |

---

## 6. Consolidated Actionable Roadmap & Prioritized Implementation Plan

To safely execute these remediations without disrupting ongoing test automation workflows, work is structured into four sequential phases:

```
Implementation Timeline:
Phase 1: Immediate Critical Fixes (Runtime bugs & rule restoration)
Phase 2: Agent Scoping & Rule De-duplication
Phase 3: Skill & Tool Consolidations
Phase 4: CLI Wiring Expansion & Router Optimization
```

### 6.1 Phase 1: Immediate Critical Fixes (Sprint 1)
- [ ] **Fix Format Crash in `tools/cldr_l10n_verifier.py`**:
  - Replace `35%)` with `35%%)` on line 245.
  - Verify with `python tools/cldr_l10n_verifier.py --help` (must exit code 0).
- [ ] **Fix Stdio Hang in `tools/mcp_server.py`**:
  - Add `sys.argv` inspection for `--help` / `-h` before entering `run_stdio_server()` on line 816.
  - Verify with `python tools/mcp_server.py --help` (must exit cleanly < 500ms).
- [ ] **Restore `api_testing_rules.md` & Prune `stack-auto-router.md`**:
  - Restore `.agents/rules/api_testing_rules.md` from commit `e229dfd^`.
  - Remove `.agents/rules/stack-auto-router.md` and move documentation to `docs/`.
  - Update `tools/rules_router.py:120` to map `"api": ["api_testing_rules.md", "systematic-debugging.md"]`.
  - Fix broken link in `.agents/agents/api-engineer.md:30`.
- [ ] **Fix Router Omission for `lessons-learned.md`**:
  - Add `"lessons-learned.md"` to `CORE_BASE_RULES` in `tools/rules_router.py:105`.

### 6.2 Phase 2: Agent Scoping & Rule De-duplication (Sprint 2)
- [ ] **Purge API Responsibilities from `pom-crafter.md`**:
  - Remove `api_fuzzer.py`, `export_postman_collection.py`, `fuzz_payloads.py`, `generate_api_matrix.py`, `api_drift_sentinel.py`, and `network_mock_shield.py`.
  - Ensure all API test synthesis is handled exclusively by `api-engineer.md`.
- [ ] **Resolve Runner Self-Healing Contradiction in `test-runner.md`**:
  - Remove `ci_healing_hook.py` and silent healing instructions from `test-runner.md`.
  - Enforce strict handoff of failed JUnit XML reports to `failure-analyst.md`.
- [ ] **Cleanse Frontmatter in `orchestrator.md` & `perf-engineer.md`**:
  - Prune 10 unreferenced tools from `orchestrator.md` frontmatter.
  - Delegate requirement interviewing and spec review strictly to `test-designer.md`.
  - Remove external plugin skills (`debug-optimize-lcp`, `memory-leak-debugging`) from `perf-engineer.md`.
- [ ] **Strip FSM Section from `mandatory-playwright-live.md`**:
  - Remove Section 1 (Swarm FSM) from `mandatory-playwright-live.md`, relying exclusively on `AGENTS.md` §4.

### 6.3 Phase 3: Skill & Tool Consolidations (Sprint 3)
- [ ] **Execute 8 Skill Consolidations**:
  - Absorb `lam-script-generator` into `clean-pom-crafter`.
  - Consolidate `mobile-appium-som` and `mobile-maestro-detox-patterns` into `mobile-automation-patterns` and assign to `pom-crafter`/`test-runner`.
  - Absorb `playwright-webapp-testing` into `e2e-testing-patterns`.
  - Move `lean-impact-scoreboard` into `08-code-quality/repo-quality-audit`.
  - Unify `agentless-qa-repair` and `self-healing-locator` under `failure-autopsy-and-healing`.
  - Retire `antigravity-test-sentinel` in favor of `verification-before-completion`.
  - Merge `surgical-coding-principles` into `lean-code-ladder`.
  - Prune `gitlab-ci-templates` and `jenkins-pipeline-templates` as standalone skills; merge templates into `github-actions-templates` (`ci-cd-pipeline-templates`).
- [ ] **Consolidate Redundant Tool Implementations**:
  - Port unique checks from `synapse_doctor.py` into `check_env.py` and deprecate `synapse_doctor.py`.
  - Merge table formatting from `md_to_xlsx.py` into `template_excel_exporter.py` and deprecate `md_to_xlsx.py`.
  - Merge `runaway_stopper.py` heuristics into `tools/core/circuit_breaker.py`.
  - Add `--sync-manifest` to `validate_skills_schema.py` and deprecate `sync_skills_manifest.py`.
  - Delete dead script `tools/build_consolidated_report.py` (1,643 LOC).
  - Delete committed lock files (`tools/repo_map.json.lock`, `tools/repo_map.txt.lock`) and update `.gitignore`.
  - Relocate `tools/create_mock_docx.py` to `tests/fixtures/`.
  - Consolidate AI assertion tuning triad (`dspy_qa_signatures.py`, `mipro_assertion_tuner.py`, `textgrad_mutation_optimizer.py`) into `tools/assertion_optimizer.py`.

### 6.4 Phase 4: CLI Wiring Expansion & Router Optimization (Sprint 4)
- [ ] **Wire High-Value Standalone Tools to `tools/cli.py`**:
  - Register top priority commands in `tools/cli.py`:
    - `agent-qa pentest-guard` (`tools/pentest_scope_guard.py`)
    - `agent-qa db-sandbox` (`tools/db_sandbox.py`)
    - `agent-qa tms-sync` (`tools/tms_sync_bridge.py`)
    - `agent-qa security-ledger` (`tools/security_coverage_ledger.py`)
    - `agent-qa skill-vault` (`tools/skill_vault.py`)
    - `agent-qa slides` (`tools/slide_deck_exporter.py`)
    - `agent-qa host-interop` (`tools/validate_host_interop.py`)
    - `agent-qa security-scan` (`tools/security_scanner.py`)
    - `agent-qa coverage` (`tools/coverage_reporter.py`)
    - `agent-qa pairwise` (`tools/pairwise_generator.py`)
    - `agent-qa humanize` (`tools/humanize_linter.py`)
    - `agent-qa vcr` (`tools/vcr_cassette_guard.py`)
    - `agent-qa fsm` (`tools/fsm_enforcer.py`)
- [ ] **Expand `tools/rules_router.py` Dynamic Skill Resolution**:
  - Expand skill mapping table in `rules_router.py` to route all active consolidated skills dynamically, reducing static frontmatter prompt hydration.

---

### 6.5 Quantitative ROI & Projected Engineering Impact

| Metric / Dimension | Pre-Audit Baseline | Post-Remediation Projected | Measurable Improvement |
|---|:---:|:---:|---|
| **Active Skill Catalog** | 56 skills (11 categories) | 45 unified skills | **19.6% catalog reduction**; 0 unassigned orphans |
| **Skill Collision Warnings** | 16 warnings (score >= 0.30) | 0 warnings | **100% collision elimination** |
| **Prompt Token Overhead** | ~14,172 tokens (agents) + ~10,225 tokens (rules) | ~11,500 tokens (agents) + ~8,800 tokens (rules) | **~4,100 tokens saved per turn (~17% reduction)** |
| **Tool Ecosystem Health** | 2 runtime crashes; 8 duplicate pairs | 0 runtime crashes; 0 duplicates | **100% CLI `--help` pass rate** across all tools |
| **CLI Command Coverage** | 75 tools wired / 49 unwired | 124 tools wired / 0 unwired | **+65.3% increase in accessible CLI capabilities** |
| **FSM Architectural Integrity** | 2 boundary violations (POM API creep, runner bypass) | Strict 5-Stage FSM discipline | **Zero out-of-order execution or silent bypass** |
| **Rule Link Integrity** | 1 broken 404 rule link in `api-engineer.md` | 100% valid cross-references | **Restored Google SRE Golden Signals & SLAs** |

---

## 7. Verification Method & Audit Reproduction Runbook

Every observation, metric, defect, and finding documented in this report can be independently reproduced using the following commands executed from the repository root (`d:\Synapse Hub`):

### 1. Verify Skill Count & Zero Critical Collisions
```powershell
# Verify exactly 56 SKILL.md packages exist
(Get-ChildItem -Path .agents/skills -Recurse -Filter "SKILL.md").Count

# Verify zero critical collisions under default threshold (>= 0.75)
python tools/skill_collision_guard.py

# Reproduce the 16 sub-critical proximity warnings cited in Section 1.3
python tools/skill_collision_guard.py --warn-threshold 0.3 --scan-rules --json
```

### 2. Verify Zero Security Vulnerabilities via SkillSpector
```powershell
# Verify zero prompt injections or malicious directives
python tools/skillspector.py .agents/skills
# Expected Output: Risk Score 0/100 | Severity Band: LOW | Total Findings: 0 | Verdict: SAFE
```

### 3. Verify Orphaned Skills (Zero Agent Manifest References)
```powershell
# Confirm zero agent assignments for gitlab-ci-templates and jenkins-pipeline-templates
Select-String -Path .agents/agents/*.md -Pattern "gitlab-ci-templates"
Select-String -Path .agents/agents/*.md -Pattern "jenkins-pipeline-templates"
# Both return 0 matches
```

### 4. Reproduce Runtime Tool Defects
```powershell
# Reproduce format string crash in cldr_l10n_verifier.py
python tools/cldr_l10n_verifier.py --help
# Expected: ValueError: unsupported format character ')' (0x29) at index 58

# Reproduce blocking stdio hang in mcp_server.py (Ctrl+C to terminate)
python tools/mcp_server.py --help
```

### 5. Verify Broken Reference in `api-engineer.md` & Missing Rule File
```powershell
# Confirm reference in agent manifest
Get-Content ".agents/agents/api-engineer.md" | Select-String "api_testing_rules.md"

# Confirm file does not exist on disk
Test-Path ".agents/rules/api_testing_rules.md" # Returns False

# Inspect commit e229dfd that deleted the rule file
git show e229dfd --stat
```

### 6. Verify Total Tool Asset Count (Exactly 180 Files)
```powershell
python -c "import os; files = [os.path.join(r, f) for r, d, fs in os.walk('tools') for f in fs if '__pycache__' not in r]; print('Total tools files:', len(files))"
# Output: Total tools files: 180
```

### 7. Invalidation Conditions
- If any file in `.agents/skills/` is discovered that is omitted from the 56-skill Master Table, this report is invalidated.
- If any tool in `tools/` is discovered that is omitted from the 180-tool Master Table, this report is invalidated.
- If `python tools/cldr_l10n_verifier.py --help` exits with code 0 without modification, Defect 1 is invalidated.
- If `Test-Path .agents/rules/api_testing_rules.md` returns True, the missing rule finding is invalidated.
