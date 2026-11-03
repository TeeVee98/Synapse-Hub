# Changelog

All notable changes to **Synapse-Hub** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **Environment Diagnostic Command:** Added `agent-qa doctor` / `npx synapse-hub doctor` for instant 1-click prerequisite auditing.
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
