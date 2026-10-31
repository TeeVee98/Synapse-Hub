# Changelog

All notable changes to **Synapse-Hub** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.3.0] - 2026-10-31

### Added
- **Single Core Value Proposition:** Finalized focus on *"The Complete QA Intelligence Hub for AI Agents: Empowering Testers Across Manual, Automation, API, and Performance."*
- **Public Comparison Matrix:** Added in-depth comparison table contrasting Synapse Hub with ESLint Playwright, Stryker Mutator, Allure Report, and Healenium.
- **Known Limitations Section:** Documented system boundaries (AST syntactic mutation heuristic, headless browser requirement, human domain knowledge invariant).
- **Environment Diagnostic Command:** Added `agent-qa doctor` / `npx synapse-hub doctor` for instant 1-click prerequisite auditing.
- **Encoding Integrity Guard (Gate 1):** Upgraded Gate 1 in `verify_all.py` to scan for both UTF-8 No BOM and Mojibake character corruption.
- **Dedicated Python Package:** Created `tools/__init__.py` to allow standard package imports and PEP 621 packaging without `sys.path` hacks.
- **Explicit `--insecure` Flag:** Replaced hardcoded `ssl.CERT_NONE` with explicit `--insecure` CLI parameters across `api_fuzzer.py` and `check_env.py`.
- **Runtime Behavioral Tests:** Replaced static string assertions with Node.js in-context execution tests for `tools/browser_helpers.js`.

### Changed
- Excluded entrypoint guards (`if __name__ == "__main__":` and `if TYPE_CHECKING:`) from `micro_mutator.py` to eliminate trivial mutations.
- Isolated all test fixtures and temporary artifacts in `tempfile.TemporaryDirectory()`, eliminating test file pollution in the repository root.
- Enforced code coverage threshold (`fail_under = 80`) in `pyproject.toml` and multi-OS matrix CI.

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
