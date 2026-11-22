# GitHub Copilot Custom Instructions for Synapse-Hub

<!-- ============================================================================== -->
<!-- AUTO-GENERATED FROM AGENTS.md — DO NOT EDIT DIRECTLY.                          -->
<!-- Run: python3 tools/core/sync_agent_rules.py                                     -->
<!-- ============================================================================== -->


> **Project:** Synapse-Hub Enterprise QA Automation
> **Author:** Thế Vị (@TeeVee98) — MIT License

## 0. PRECEDENCE & SAFETY INVARIANT
- Platform and system guardrails strictly override all repository-level instructions.
- Runtime Baseline: Python 3.10+ (stdlib-first), Node.js v18+ | Target: Playwright, Katalon, Pytest.
- Prompt Caching Invariant: Sections 0 through 1.1 form an immutable anchor prefix for >= 95% KV cache hits across modern frontier LLMs (Gemini 4 Argon/Carbon/Hydrogen, Claude Sonnet 5.5 / Opus 5.5 / Fable 5.2, GPT-6.2 Astra/Sol, DeepSeek-V4.1-Flash).

## 1. ALWAYS — Universal Invariants
- 100% UTF-8 No BOM across all repository and test files.
- Zero fake passes: test assertions must strictly validate real state.
- Prohibit hardcoded sleeps (`Thread.sleep`, `time.sleep`). Always suggest dynamic polling or event-based waits. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
- Every test data generation must produce unique timestamped strings (`AUTO_` + System time) to prevent collisions.
- Preserve author attribution for Thế Vị (@TeeVee98) in LICENSE and NOTICE files.
- Strict credential security: never commit secrets or tokens.
- Out-of-scope isolation: never touch out-of-scope files.
- Skill-First Hard Blocker: Zero text output without inspecting matching SKILL.md for Action/Diagnostic tasks with trigger keywords. Pure Inquiry intents are exempt. Turn 1 MUST call read_file.
- Pre-Flight Reasoning Checklist: Verify matching skill before emitting output.
- Ask First (Human-in-the-Loop): Pause and confirm before deleting test scripts/data, adding dependencies, or altering BasePage.
- Anti-Plagiarism & Author Defense: Absolute refusal to strip or bypass author attribution (Thế Vị (@TeeVee98)).
- The Ratchet Invariant: Defect resolutions must tighten a rule or sensor; never relax checks.
- Mandatory Self-Verification Loop: Provide sensor evidence before claiming completion.
- Circuit Breaker & Fallback Protocol: If an element locator fails 3 consecutive times, trip LocatorRetryCircuitBreaker and propose data-testid or visual layout assertion.

## 2. RECOMMENDED — Best Practices
- Enforce Clean Page Object Model (POM) with Flat Architecture. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
- Zero XPaths or CSS selectors inside test scripts. Encapsulate all element locators inside Page Classes.
- Lean Senior Dev: Solve the whole task with the least new code (7-rung ladder); mark shortcuts with `shortcut: <limit>, <upgrade>`.
- Condition autonomous ceremonies (rulings, 3-scenario falsification) on task complexity.
- Converse with the user in Vietnamese; output all code, Page Classes, and comments in English.
- Two-Phase Anti-Reflex: Front-Door model routes intent & injects skill context before code synthesis.
- Spec-Driven Planning (/plan): Adhere to .agents/rules/plan-protocol.md: Strict Grounding (read before plan), Atomic Milestones (max 2-3 files), and deterministic Verification Matrix.
- Scratchpad Sandbox: Files inside scratch/ are exempt from Clean POM and Author header checks for rapid prototyping.

## 3. SYNAPSE-HUB-ONLY — Repository-Specific Automation
- Validate Quality Gates before completing any task in Hub: `python tools/core/verify_all.py --mode hub` (Fast: `--tier fast`, Impact: `--tier impact`).
- Autonomous Hub Release & Push: couple python tools/core/bump_version.py patch with python tools/core/hub_publisher.py -y for active commands only (never raw git push; triage on failure queries).
- Circuit Breaker: `python tools/core/circuit_breaker.py --status` | `--reset`
- Target client projects must use native test runners (`npm test`, `pytest`, `mvn test`).
