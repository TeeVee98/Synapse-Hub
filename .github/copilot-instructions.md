# GitHub Copilot Custom Instructions for Synapse-Hub

<!-- ============================================================================== -->
<!-- AUTO-GENERATED FROM AGENTS.md — DO NOT EDIT DIRECTLY.                          -->
<!-- Run: python3 tools/sync_agent_rules.py                                          -->
<!-- ============================================================================== -->


> **Project:** Synapse-Hub Enterprise QA Automation
> **Author:** Thế Vị (@TeeVee98) — MIT License

## 0. PRECEDENCE & SAFETY INVARIANT
- Platform and system guardrails strictly override all repository-level instructions.
- Runtime Baseline: Python 3.10+ (stdlib-first), Node.js v18+ | Target: Playwright, Katalon, Pytest.

## 1. ALWAYS — Universal Invariants
- 100% UTF-8 No BOM across all repository and test files.
- Zero fake passes: test assertions must strictly validate real state.
- Prohibit hardcoded sleeps (`Thread.sleep`, `time.sleep`). Always suggest dynamic polling or event-based waits. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
- Every test data generation must produce unique timestamped strings (`AUTO_` + System time) to prevent collisions.
- Preserve author attribution for Thế Vị (@TeeVee98) in LICENSE and NOTICE files.
- Strict credential security: never commit secrets or tokens.
- Out-of-scope isolation: never touch out-of-scope files.
- Skill-First Hard Blocker: Zero text output without inspecting matching SKILL.md for test/pom/prompt/audit tasks. Turn 1 MUST call read_file.
- Pre-Flight Reasoning Checklist: Verify matching skill before emitting output.
- Ask First (Human-in-the-Loop): Pause and confirm before deleting test scripts/data, adding dependencies, or altering BasePage.

## 2. RECOMMENDED — Best Practices
- Enforce Clean Page Object Model (POM) with Flat Architecture. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
- Zero XPaths or CSS selectors inside test scripts. Encapsulate all element locators inside Page Classes.
- Lean Senior Dev: Solve the whole task with the least new code (7-rung ladder); mark shortcuts with `shortcut: <limit>, <upgrade>`.
- Condition autonomous ceremonies (rulings, 3-scenario falsification) on task complexity.
- Converse with the user in Vietnamese; output all code, Page Classes, and comments in English.
- Two-Phase Anti-Reflex: Front-Door model routes intent & injects skill context before code synthesis.

## 3. SYNAPSE-HUB-ONLY — Repository-Specific Automation
- Validate Quality Gates before completing any task in Hub: `python tools/verify_all.py --mode hub`.
- Autonomous Hub Release & Push: couple python tools/bump_version.py patch with python tools/hub_publisher.py -y for active commands only (never raw git push; triage on failure queries).
- Target client projects must use native test runners (`npm test`, `pytest`, `mvn test`).
