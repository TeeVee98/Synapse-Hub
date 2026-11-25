# GitHub Copilot Custom Instructions for Synapse-Hub

<!-- ============================================================================== -->
<!-- AUTO-GENERATED FROM AGENTS.md — DO NOT EDIT DIRECTLY.                          -->
<!-- Run: python3 tools/core/sync_agent_rules.py                                     -->
<!-- [CACHE-ANCHOR: ROOT-PREFIX-v4.8]                                               -->
<!-- ============================================================================== -->


> **Project:** Synapse-Hub Enterprise QA Automation
> **Author:** Thế Vị (@TeeVee98) — MIT License

## 0. PRECEDENCE & SAFETY INVARIANT
- Platform and system guardrails strictly override all repository-level instructions.
- Runtime Baseline: Python 3.10+ (stdlib-first), Node.js v18+ | Target: Playwright, Katalon, Pytest.
- Prompt Caching Invariant: Sections 0 through 1.1 form an immutable anchor prefix for >= 95% KV cache hits across modern frontier and reasoning LLMs with context caching (Gemini, Claude, GPT, DeepSeek).

## 1. ALWAYS — Universal Invariants
- Mandatory across all workspaces, test scripts, and runtime environments:
- **100% UTF-8 No BOM:** Zero BOM bytes (`0xEF, 0xBB, 0xBF`) across all repo/test files (`.groovy`, `.java`, `.ts`, `.py`, `.json`, `.md`).
- **Truth Anchor (Zero Fake Passes):** Never relax assertions, skip validation steps, write empty tests (0 asserts), or catch-and-swallow exceptions (`pass`, dummy suppression `_ = err` or `_ = False`, `const _ = e`). Report AUT defects honestly.
- **Dynamic Smart Waits Only:** Static sleeps (`Thread.sleep`, `time.sleep`, `waitForTimeout`) strictly prohibited in test scripts. Use web-first assertions (`expect(locator).toBeVisible()`). For page navigation and asynchronous hydration, use bounded explicit event waits (`waitForURL`, `waitForResponse`); avoid unconditional `waitForLoadState('networkidle')` which is flaky under continuous background polling or websockets. *(Automation code only; exempt for Manual QA specs)*.
- **Dynamic & Idempotent Test Data:** Always randomize test entity codes with dynamic timestamps/prefixes (`BasePage.uniqueCode("AUTO_")`, `DataGenerator`) to eliminate DB collisions. Pair creation with automated Teardown cleanup.
- **Strict Credential Security:** Never commit raw plaintext passwords, secret tokens, private keys, or cloud credentials. Inject secrets via environment variables or fixtures.
- **Out-of-Scope Isolation & Stop-and-Report:** When verification gates fail due to legacy defects in files outside task scope, never modify those files or write bypasses. Stop, report with evidence, and ask user.
- **Skill-First Hard Blocker (Context-Aware Intent & Scope Routing):** Action/Diagnostic intents modifying code or running audits within skill-managed domains MUST call `read_file` on `skills_index.json` and matching `SKILL.md` in Turn 1 before conversational text. Mechanically evaluated via `tools/core/skill_router.py`. Pure Inquiry, read-only diagnostic surveys, and single-line micro-fixes outside skill domains are exempt.
- **Universal Intent Disambiguation:** Action (execute commanded tool) vs Diagnostic (read-only inspection; zero mutating tools) vs Inquiry (conceptual explanation).
- **Ask First (Human-in-the-Loop Safeguards):** Pause and obtain user confirmation before deleting test scripts/data, changing dependencies (`package.json`/`pyproject.toml`), modifying shared `BasePage`, or breaking schemas.
- **Author Attribution & Provenance Invariant:** Mandatory attribution crediting Thế Vị (@TeeVee98) under the MIT License must be preserved across all codebase files, package manifests, and distributions. Physical provenance integrity is mechanically enforced via `tools/core/author_integrity.py` and CI/CD release provenance gates.
- **The Ratchet Invariant (Monotonic Quality Ratchet):** Every defect resolution or post-mortem MUST tighten a Guide or Sensor. Relaxing assertions or removing rules to manufacture a pass is strictly prohibited.
- **Mandatory Self-Verification Loop (Empirical Verification Principle):** Before marking any task complete, the agent MUST execute the designated Sensor (tests, linter, or quality gate) and provide fresh empirical evidence. Zero claims without proof.
- **Circuit Breaker & Path-Scoped Rollback Hygiene Protocol:** If locator, test action, or tool call fails 2 consecutive times on same target (`synapse.config.json::circuit_breaker.max_fix_attempts`), trip `LocatorRetryCircuitBreaker`. Blind loops (> 2) forbidden. Execute safe, path-scoped rollback (`git checkout -- <target_files>` or `tools/lint/plan_schema_sentinel.py::rollback_path_scoped` and safe removal of untracked created files). Blanket destructive commands (`git reset --hard`, `git clean -f`) strictly prohibited. Verify clean `git status` for touched files, and emit Escalation Report proposing screenshot diff or requesting dev `data-testid`. Zero half-broken edits on disk.
- **Anti-Premature Done & 4-Scenario Battery:** Strictly forbid claiming completion ("done/xong") without raw terminal proof across 4 scenarios: a) Positive, b) Negative (handled errors without crash), c) Boundary (empty/null), d) Scope-appropriate verification: CLI flags (`--json`, `--gate`, `--output`) for CLI tools, or Exception Handling & Edge-Case Resilience for libraries/subsystems. Skill edits: `validate_skills_schema.py` & `lint_ai_docs.py`; code edits: `infer_linter.py`.
- **Autonomous Solo Mandate (Risk-Proportionate Test & Mutation Verification):** For runtime logic modifications on `planning.critical_paths` or spanning `> 2` files (excluding pure documentation, typos, read-only diagnostics exempt under Invariant 7, and Tier-0 non-critical micro-fixes `<= 2` files covered by passing unit tests), autonomously execute the 4-phase verification pipeline (`tools/orchestration/solo_runner.py` / `.agent/skills/solo/SKILL.md`): a) Red test failure certification (`--red`), b) Green implementation verification (`--green`), c) Live dynamic mutation score >= 80.0% (`--mutation`), and d) Quality Gates verification (`verify_all.py`). Attach forensic execution receipts (Red, Green, Mutation) in delivery report.
- **English-Only Codebase & Rules (Bilingual Discipline Invariant):** All codebase files, test scripts, Page Classes, docstrings, commits, and rule files (`AGENTS.md`, `standards/*`, `testing/*`, `.cursor/rules/*`) must remain strictly in English to prevent semantic drift and optimize LLM KV cache hit rates. Whitelists localization test assets and end-user guides (`README.md`, `*.vi.md`). Non-English diacritics forbidden outside author attribution (`Thế Vị (@TeeVee98)`). Enforced via `python tools/lint/invariant_checker.py --rule 16`.
- **Mandatory Adversarial Self-Audit (Risk-Proportionate Adversarial Review Invariant):** Before declaring ANY non-trivial implementation on `planning.critical_paths` or `> 2` runtime files complete (for Tier-0 micro-fixes `<= 2` files with dedicated passing unit tests, perform a concise contrarian diff check without ceremony bloat; pure documentation, typos, and read-only diagnostics are exempt), autonomously assume the persona of an independent adversarial reviewer / senior security auditor without user prompting. Execute `tools/orchestration/solo_runner.py --purple` and probe 4 contrarian crash vectors: a) Null/None/KeyError payloads, b) Logic boundary anomalies & cross-line regex slips, c) Tautological/fake assertions, d) Downstream caller breakage via `call_graph_indexer.py`. Embed explicit "Adversarial Code Audit Receipt" in delivery report. Premature completion without receipt is strictly prohibited.

---

## 1.1 PRE-FLIGHT REASONING CHECKLIST
Verify before emitting any token in final response across 3 Cognitive Pillars:
- **Pillar A (Context Alignment & Grounding):**
  1. `[Intent & Skill]`: Classify intent (Action/Diagnostic/Inquiry); call `read_file` on `skills_index.json` / matching `SKILL.md` if triggered.
  2. `[Step-Back Abstraction]`: Formulate governing architectural invariant (CAP, idempotency, event-loop) before coding.
  3. `[Truth Anchor & AST Micro-Context]`: Real assertions only; slice micro-context (< 100 tokens via `context_slicer.py`).
- **Pillar B (Empirical Harness & Verification):**
  4. `[Harness Sensor Verification]`: Execute designated verification sensor (tests/linter) with fresh empirical proof before claiming done.
  5. `[4-Scenario Battery]`: Tested Positive, Negative, Boundary, CLI flags with raw terminal proof?
  6. `[Autonomous Solo-Swarm]`: Certified Red failure receipt, Green passing status, live mutation score >= 80% without user babysitting (exempt for Tier-0 micro-fixes <= 2 files with dedicated tests)?
- **Pillar C (Adversarial Safety & Hygiene):**
  7. `[Adversarial Self-Audit]`: Assumed auditor persona, executed `--purple`, probed 4 contrarian crash vectors, and embedded Adversarial Audit Receipt?
  8. `[Workspace Hygiene & Context Alert]`: Clean git status verified (no broken speculative edits); proactively alert `/compact` if session context is bloated?

## 2. RECOMMENDED — Best Practices
- Enforce Clean Page Object Model (POM) with Flat Architecture. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
- Zero XPaths or CSS selectors inside test scripts. Encapsulate all element locators inside Page Classes.
- Lean Senior Dev: Solve the whole task with the least new code (7-rung ladder); mark shortcuts with `shortcut: <limit>, <upgrade>`.
- Condition autonomous ceremonies (rulings, 3-scenario falsification) on task complexity.
- Converse with the user in Vietnamese; output all code, Page Classes, and comments in English.
- Execution Mode (`/solo` vs `/teamwork`): Default to sequential Single-Agent `/solo` in one session; strictly FORBIDDEN to spawn `swarm` workers or parallel subagents unless `/teamwork` or parallel workers are explicitly requested.
- Spec-Driven Planning (/plan & /super-plan): Read target files before proposing edits, split work into atomic milestones (<= 3 files), verify with concrete test commands, and default handoffs to `/solo`.
- Test-First Verification: Certify Red -> Green transitions and perform an adversarial edge-case self-audit before completion.
- Scratchpad Sandbox: Files inside scratch/ are exempt from Clean POM and Author header checks for rapid prototyping.

## 3. SYNAPSE-HUB-ONLY — Repository-Specific Automation
- Validate Quality Gates before completing any task in Hub: `python tools/core/verify_all.py --mode hub` (Fast: `--tier fast`, Impact: `--tier impact`).
- Autonomous Hub Release & Push: couple python tools/core/bump_version.py patch with python tools/core/hub_publisher.py -y for active commands only (never raw git push; triage on failure queries).
- Circuit Breaker: `python tools/core/circuit_breaker.py --status` | `--reset`
- Target client projects must use native test runners (`npm test`, `pytest`, `mvn test`).
