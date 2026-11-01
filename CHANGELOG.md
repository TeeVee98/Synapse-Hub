# Changelog

All notable changes to **Synapse-Hub** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed
- **Python 3.9–3.11 f-string compatibility (`output_formatter.py`):** Extracted ANSI escapes to class constants, removing backslashes from inside f-string expressions.
- **GitHub Composite Action security (`action.yml`):** Replaced direct string interpolation in shell script with safe `env:` variables and Bash array quoting (`"${ARGS[@]}"`) to eliminate injection risks.
- **MCP Server Path Traversal (`mcp_server.py`):** Enforced `_validate_safe_path` on `spec_path` argument in `fuzz_api` handler.
- **Optional dependencies in tests (`test_tools.py`):** Added dynamic `skipUnless` guard on `test_md_to_xlsx_conversion` when `openpyxl` is not present.
- **Documentation & Catalog Sync:** Reconciled `skills_manifest.json` full profile description to 37 skills, corrected heading sequence in `docs/ARCHITECTURE.md`, and supplied `docs/schemas/synapse.config.schema.json`.

### Added
- **Universal Version Sync Sentinel (`tools/check_version_sync.py`):** Added automated 8-target version validator integrated into both CI and release workflows.
- **Zero `shell=True` Security Test:** Added AST verification test ensuring zero subprocess execution with `shell=True` in tooling code.
- **Opt-in Global Setup:** Made `setup_project.py` default to local-only configuration, requiring explicit `--global` flag to touch `~/.gemini/config/plugins`.
- **Protected NPM Cleanup Workflow:** Added explicit confirmation requirement and environment protection in `cleanup_npm_versions.yml`.

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
