# CLAUDE.md — Synapse-Hub Guidelines for Claude Code

> **Author & Creator:** Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
> **License:** MIT License (Mandatory Attribution Preservation)

<!-- ============================================================================== -->
<!-- AUTO-GENERATED FROM AGENTS.md — DO NOT EDIT DIRECTLY.                          -->
<!-- Run: python3 tools/sync_agent_rules.py                                          -->
<!-- ============================================================================== -->


> **Author Attribution:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License. Attribution notices must be preserved in all copies.

---

## ⚡ Quick Commands
- Verify 10 Quality Gates: `python tools/verify_all.py --mode hub` (or `npx @teevee98/synapse-hub verify`)
- Project Health Audit: `python tools/analyze_project.py`
- Code Linter & Fake-Pass Sentinel: `python tools/infer_linter.py`
- Verify Author Attribution: `python tools/author_integrity.py`
- Skill Security Audit: `python tools/skillspector.py --scan-skills`
- Multi-Bridge Sync: `python tools/sync_agent_rules.py`

---

## 0. PRECEDENCE & SAFETY INVARIANT
- Platform and system guardrails strictly override all repository-level instructions.
- Precedence: System Guardrails > Core Project Rules (`.agents/rules/*`) > Local Skills > Generic Plugins.

---

## 1. ALWAYS — Universal Invariants
1. **100% UTF-8 No BOM:** Zero BOM bytes (`0xEF, 0xBB, 0xBF`) across all repository files.
2. **Truth Anchor (Zero Fake Passes):** Never relax assertions, skip validation steps, or catch-and-swallow exceptions to fake a pass.
3. **Dynamic Smart Waits Only:** Static sleeps (`Thread.sleep`, `time.sleep`) are strictly prohibited in test scripts. Use element visibility or `waitForLoadState('networkidle')`.
4. **Dynamic & Idempotent Test Data:** Always randomize test entity codes with dynamic timestamps/prefixes (`BasePage.uniqueCode("AUTO_")`). Pair creation with automated Teardown cleanup.
5. **Strict Credential Security:** Never commit raw plaintext passwords, secret tokens, or private keys.
6. **Out-of-Scope Isolation:** When verification gates fail due to legacy defects in files outside task scope, stop and report; never touch out-of-scope files.
7. **Skill-First Hard Blocker (Zero Text Without Tool Invocation):**
   - Trigger Keywords: `[test, pom, page class, prompt, review, audit, verify, scan, heal, design, benchmark, mock, contract, load, wcag, api, security, push, publish, release, bump, version, doctor, env, linter, log, distill, triage, failure, sync-rules]`.
   - Hard Invariant: Absolutely FORBIDDEN to output conversational answers without first calling `read_file` to inspect `skills_index.json` and matching `SKILL.md`. Turn 1 MUST be a tool call.
8. **Universal Intent Disambiguation:** Action (execute commanded tool) vs Diagnostic (read-only triage; mutating tools strictly forbidden) vs Inquiry (conceptual explanation).

---

## 1.1 PRE-FLIGHT REASONING CHECKLIST (Mandatory Thinking Invariant)
Inside `<thought>`, verify before emitting output:
1. `[Intent & Domain]`: Classify intent (Action/Diagnostic/Inquiry) and resolve matching skill in `skills_index.json`. For Diagnostic/Inquiry, ensure ZERO side-effecting re-executions.
2. `[Skill Read Check]`: Called `read_file` on `SKILL.md`? If NO -> STOP and call tool.
3. `[Zero Improvised Workflow]`: 100% adherence to skill lifecycle.
4. `[Truth Anchor Check]`: Zero fake passes / zero swallowed exceptions.

---

## 2. RECOMMENDED — Best Practices
1. **Clean Page Object Model (POM) Flat Architecture:**
   - Test scripts (`tests/`, `Scripts/`) must contain ONLY business workflow method calls on Page Classes.
   - Strictly forbidden: Raw XPaths, CSS selectors, or `findTestObject` inside test scripts.
   - All locators and DOM operations belong in Page Classes extending `BasePage`. Keep inheritance flat (max 1 level).
2. **Lean Senior Dev Protocol (7-Rung Ladder & YAGNI):**
   - The best code is the code never written. Solve the whole problem with the least new code.
   - Descend the 7-rung ladder: 1. Need to exist? 2. Already in codebase? 3. Standard library? 4. Platform native? 5. Installed dependency? 6. One clear line? 7. Minimum working code.
   - Deliberate simplifications get an inline comment: `shortcut: <the limit>, <when to upgrade>`.
3. **Risk-Conditioned Autonomous Ceremonies:**
   - Jesse Vincent Rulings (`Ruling:`): Mandatory for architectural forks, breaking changes, or non-trivial tradeoffs. Omit for trivial doc/typo fixes.
   - Addy Osmani Falsification (3 failure scenarios): Mandatory before certifying core test cases or complex locators.
4. **Bilingual & Polyglot Communication & Gated Telemetry:**
   - Fluently adapt conversationally to user language (Vietnamese, English, etc.); default to English for international contributors.
   - Status badge and risk notes are restricted to audit, review, and quality-gate commands (/synapse-audit, /synapse-review, verify_all.py).
   - Codebase files, test scripts, Page Classes, docstrings, and commits strictly in English.
   - Read English versions (`*.en.md`) when bilingual docs exist to preserve tokens.

---

## 4. MULTI-AGENT SWARM & TWO-PHASE SEPARATION
- Single Front-Door (`orchestrator`) directs all incoming requests across 5-stage FSM.
- Two-Phase Anti-Reflex Protocol: Front-Door model routes intent & injects SKILL.md context; specialized subagent executes. Front-Door is strictly forbidden from generating low-level code/prompts without skill context.
---

## 3. SYNAPSE-HUB-ONLY — Repository-Specific Automation
⚠️ The following CLI tools exist ONLY in the Synapse-Hub repository checkout:
- Quality Gates DoD: `python tools/verify_all.py --mode hub`
- Release Publisher: `python tools/bump_version.py patch` + `python tools/hub_publisher.py -y` (Active push commands only; diagnostic queries triage errors, never re-push)
- Rule Synchronizer: `python tools/sync_agent_rules.py`
- Target external projects must use native runners (`npm test`, `pytest`, `mvn test`).
