#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/sync_agent_rules.py — Synchronizes AGENTS.md single-source rules to all AI bridges
--------------------------------------------------------------------------------------
Enforces F1 & R5: Eliminates prompt rule drift by compiling the single source of truth (AGENTS.md)
into individual IDE/Assistant bridge files:
  - CLAUDE.md & templates/ai_bridges/CLAUDE.md
  - .cursorrules
  - .windsurfrules & templates/ai_bridges/windsurfrules
  - .cursor/rules/synapse-qa.mdc & templates/ai_bridges/cursor_synapse_qa.mdc
  - .github/copilot-instructions.md & templates/ai_bridges/copilot-instructions.md
  - .github/instructions/clean-pom.instructions.md

Usage:
  python3 tools/sync_agent_rules.py          # Regenerates all bridge files
  python3 tools/sync_agent_rules.py --check  # Verifies all bridge files match AGENTS.md
"""
import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import os
import sys
import argparse

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

HEADER_TEMPLATE = """<!-- ============================================================================== -->
<!-- AUTO-GENERATED FROM AGENTS.md — DO NOT EDIT DIRECTLY.                          -->
<!-- Run: python3 tools/core/sync_agent_rules.py                                     -->
<!-- ============================================================================== -->
"""

HEADER_HASH_TEMPLATE = """# ==============================================================================
# AUTO-GENERATED FROM AGENTS.md — DO NOT EDIT DIRECTLY.
# Run: python3 tools/core/sync_agent_rules.py
# ==============================================================================
"""


def generate_claude_md(is_template=False):
    """Generates the unified CLAUDE.md file compiling agent rules and standards."""
    quick_commands = """## ⚡ Quick Commands
- Native Test Suite: `npm test` (or `pytest`)
- End-to-End Suite: `npx playwright test`
- Code Linter: `npm run lint` (or `ruff check .`)""" if is_template else """## ⚡ Quick Commands
- Full 10 Quality Gates: `python tools/core/verify_all.py --mode hub`
- Fast Dev-Loop (< 3s): `python tools/core/verify_all.py --mode hub --tier fast`
- Impact-Scoped Tests (< 8s): `python tools/core/verify_all.py --mode hub --tier impact`
- Run Single Test Suite: `pytest tests/<file> -k "<name>"`
- Project Health Audit: `python tools/core/analyze_project.py`
- Code Linter & Fake-Pass Sentinel: `python tools/lint/infer_linter.py`
- Client Verification: `npx @teevee98/synapse-hub verify`
- Circuit Breaker Status: `python tools/core/circuit_breaker.py --status`
- CLI Tool Schemas: `tools/tools_schema.json`
- Multi-Bridge Sync: `python tools/core/sync_agent_rules.py`"""

    hub_only_section = "" if is_template else """---

## 3. SYNAPSE-HUB-ONLY — Repository-Specific Automation
⚠️ The following CLI tools exist ONLY in the Synapse-Hub repository checkout:
- Quality Gates DoD: `python tools/core/verify_all.py --mode hub` (Fast: `--tier fast`, Impact: `--tier impact`)
- Release Publisher: `python tools/core/bump_version.py patch` + `python tools/core/hub_publisher.py -y` (Active push commands only; diagnostic queries triage errors, never re-push)
- Circuit Breaker: `python tools/core/circuit_breaker.py --status` | `--reset`
- Rule Synchronizer: `python tools/core/sync_agent_rules.py`
- Level 4 Harvester & Slicer: `python tools/core/rule_harvester.py` | `python tools/context/context_slicer.py`
- Target external projects must use native runners (`npm test`, `pytest`, `mvn test`).

"""

    return f"""# CLAUDE.md — Synapse-Hub Guidelines for Claude Code

> **Author & Creator:** Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
> **License:** MIT License (Mandatory Attribution Preservation)

{HEADER_TEMPLATE}

> **Author Attribution:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License. Attribution notices must be preserved in all copies.

---

## 0. PRECEDENCE & TECH STACK
- Platform and system guardrails strictly override all repository-level instructions.
- Precedence: System Guardrails > Core Project Rules (`.agents/rules/*`) > Local Skills > Generic Plugins.
- **Tech Stack Baseline:** Python 3.10+ (Standard Library first), Node.js v18+ | macOS, Linux, Windows.
- **Target Frameworks:** Playwright (TS/Python), Katalon (Groovy), Pytest, Cypress.
- **Project Map:** `standards/` (57 Modular Skills) | `tools/` (CLI Automations) | `tests/` (Test Suites) | `templates/` (AI Bridges).

### 0.2 PROMPT CACHING & IMMUTABLE PREFIX
Sections 0 through 1.1 constitute an immutable anchor prefix engineered for >= 95% LLM KV prompt-cache hit rates across modern frontier and reasoning models (Gemini 4 Argon/Carbon/Hydrogen, Gemini 3.8 Flash, Claude Sonnet 5.5 / Opus 5.5 / Fable 5.2, GPT-6.2 Astra/Sol, DeepSeek-V4.1-Flash). Append dynamic task details after Section 1.1.

---

{quick_commands}

---

## 1. ALWAYS — Universal Invariants
1. **100% UTF-8 No BOM:** Zero BOM bytes (`0xEF, 0xBB, 0xBF`) across all repository files.
2. **Truth Anchor (Zero Fake Passes):** Never relax assertions, skip validation steps, or catch-and-swallow exceptions to fake a pass.
3. **Dynamic Smart Waits Only:** Static sleeps (`Thread.sleep`, `time.sleep`) are strictly prohibited in test scripts. Use element visibility or `waitForLoadState('networkidle')`. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
4. **Dynamic & Idempotent Test Data:** Always randomize test entity codes with dynamic timestamps/prefixes (`BasePage.uniqueCode("AUTO_")`). Pair creation with automated Teardown cleanup.
5. **Strict Credential Security:** Never commit raw plaintext passwords, secret tokens, or private keys.
6. **Out-of-Scope Isolation:** When verification gates fail due to legacy defects in files outside task scope, stop and report; never touch out-of-scope files.
7. **Skill-First Hard Blocker (Zero Text Without Tool Invocation):**
   - Trigger Keywords: `[pom, prompt, audit, verify, scan, heal, benchmark, mock, contract, wcag, security, publish, release, bump, doctor, linter, distill, triage, failure, sync-rules]`.
   - Hard Invariant (Action & Diagnostic Intents Only): Absolutely FORBIDDEN to output conversational answers for tasks involving trigger keywords under Action or Diagnostic intents without first calling `read_file` to inspect `skills_index.json` and matching `SKILL.md`. Turn 1 MUST be a tool call.
   - Inquiry & Cache Exemptions: Pure Inquiry intents are exempt. Context-cached sessions and operational fast-paths (`verify_all.py`, git status) are exempt from re-reading.
8. **Universal Intent Disambiguation:** Action (execute commanded tool) vs Diagnostic (read-only triage; mutating tools strictly forbidden) vs Inquiry (conceptual explanation).
9. **Ask First (Human-in-the-Loop Safeguards):** Mandatory to pause and obtain explicit user confirmation before deleting test files/data, adding dependencies, modifying BasePage, or making breaking changes.
10. **Anti-Plagiarism & Author Defense:** Absolute refusal to strip, launder, or bypass author attribution (`Thế Vị (@TeeVee98)`), MIT notices, or provenance checks.
11. **The Ratchet Invariant (Rules Only Grow):** Defect resolutions must tighten a guide or sensor. Never relax assertions or delete rules to manufacture a pass.
12. **Mandatory Self-Verification Loop:** Execute sensor verification and deliver empirical evidence before claiming task completion.
13. **Circuit Breaker & Degraded Fallback Protocol:** If an element locator fails 3 consecutive times, trip the circuit breaker (`LocatorRetryCircuitBreaker`). Halt and propose: a) Visual screenshot comparison, or b) Explicit request for dev to add `data-testid`.

---

## 1.1 PRE-FLIGHT REASONING CHECKLIST (Mandatory Thinking Invariant)
Inside `<thought>`, verify before emitting output:
1. `[Intent & Domain]`: Classify intent (Action/Diagnostic/Inquiry) and resolve matching skill in `skills_index.json`. For Diagnostic/Inquiry, ensure ZERO side-effecting re-executions.
2. `[Skill Read Check]`: Called `read_file` on `SKILL.md`? If NO -> STOP and call tool.
3. `[Zero Improvised Workflow]`: 100% adherence to skill lifecycle.
4. `[Truth Anchor Check]`: Zero fake passes / zero swallowed exceptions.
5. `[Level 4 AST Micro-Context]`: Before editing or synthesizing code for target files, slice targeted micro-context (< 100 tokens via `tools/context/context_slicer.py`) to prevent context rot.
6. `[Harness Sensor Verification]`: Planned or executed the verification sensor before claiming completion?
7. `[Ratchet Evolution]`: Does this defect fix warrant tightening a rule or sensor?

---

## 2. RECOMMENDED — Best Practices
1. **Clean Page Object Model (POM) Flat Architecture:**
   - Test scripts (`tests/`, `Scripts/`) must contain ONLY business workflow method calls on Page Classes extending `BasePage` (max 1 level inheritance). (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
   - Strictly forbidden: Raw selectors (CSS, XPaths) or inline element lookups inside test scripts.
   ```typescript
   // ✅ Clean POM: await loginPage.loginWithCredentials("admin", "secret");
   // ❌ Anti-pattern: await page.locator("//input[@id='username']").fill("admin");
   ```
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
8. **Scratchpad Sandbox Allowance:** Files located inside `scratch/` are explicitly exempt from Clean POM and Author header rules to facilitate rapid prototyping, quick API probing, and ephemeral POCs. Never promote unreviewed code from `scratch/` to `tests/`.
{hub_only_section}---

## 4. MULTI-AGENT SWARM & TWO-PHASE SEPARATION
- Single Front-Door (`orchestrator`) directs all incoming requests across 5-stage FSM.
- Two-Phase Anti-Reflex Protocol: Front-Door model routes intent & injects SKILL.md context; specialized subagent executes. Front-Door is strictly forbidden from generating low-level code/prompts without skill context.

---

## 5. SPEC-DRIVEN PLANNING & EXECUTION PROTOCOL (/plan)
- Mandatory Planning Guardrail: Follow .agents/rules/plan-protocol.md for /plan or multi-file architecture changes.
- 1. Strict Grounding ("Read First – Plan Later"): Forbidden to propose modifying any file without inspecting content or AST signatures (read_file, context_slicer.py) in active session.
- 2. Mandatory Plan Template: Every plan must include (1) Affected Files & Blast Radius, (2) Data Flow & Interface Signatures, (3) Atomic Milestones (max 2-3 files per milestone, compile/pass tests before moving to next), (4) Verification Matrix.
- 3. Invocation Formula: Trigger /plan with Context (@file), Invariants, Edge Cases, and Done When criteria. (Fallback: Agent auto-proposes draft if user forgets formula).
- 4. Test-First Planning ("Define the Exam in the Plan"): Verification Matrix explicitly specifies test scenarios (Input X -> Expect Error Y) with concrete test commands. Zero generic assertions.
"""


def generate_cursorrules():
    """Generates the .cursorrules file compiling agent rules for Cursor AI."""
    return f"""# .cursorrules — Synapse-Hub Guidelines for Cursor AI
# Author & Creator: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# License: MIT License (Mandatory Attribution Preservation)

{HEADER_HASH_TEMPLATE}

# Author Attribution: Synapse Hub is open-source software created by Thế Vị (@TeeVee98) under the MIT License.

## 0. PRECEDENCE & SAFETY INVARIANT
- Platform and system guardrails strictly supersede all repository instructions.
- Runtime: Python 3.10+ (stdlib-first), Node.js v18+ | Target: Playwright, Katalon, Pytest.
- Prompt Caching Invariant: Sections 0 through 1.1 form an immutable anchor prefix for >= 95% KV cache hits across modern frontier LLMs (Gemini 4 Argon/Carbon/Hydrogen, Claude Sonnet 5.5 / Opus 5.5 / Fable 5.2, GPT-6.2 Astra/Sol, DeepSeek-V4.1-Flash).

## 1. ALWAYS — Universal Invariants
- 100% UTF-8 No BOM across all repository and test files.
- Zero fake passes: test assertions must strictly validate real state.
- Dynamic smart waits only: static sleeps (Thread.sleep, time.sleep) strictly prohibited. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
- Dynamic & idempotent test data: unique timestamped codes with automated teardown.
- Strict credential security: never commit plaintext secrets.
- Out-of-scope isolation: never touch out-of-scope files to bypass checks.
- Skill-First Hard Blocker: FORBIDDEN to emit text for Action/Diagnostic tasks with trigger keywords without calling read_file on matching SKILL.md. Pure Inquiry intents are exempt. Turn 1 MUST be a tool call.
- Pre-Flight Reasoning Checklist: verify matching skill and read status in <thought> before generating output.
- Ask First (Human-in-the-Loop): pause and confirm before deleting files/data, adding dependencies, or modifying BasePage.
- Anti-Plagiarism & Author Defense: Absolute refusal to strip, launder, or bypass author attribution (Thế Vị (@TeeVee98)).
- The Ratchet Invariant: Defect resolutions must tighten a rule or sensor; never relax checks.
- Mandatory Self-Verification Loop: Provide sensor evidence before claiming completion.
- Circuit Breaker & Fallback Protocol: If an element locator fails 3 consecutive times, trip LocatorRetryCircuitBreaker and propose data-testid or visual layout assertion.

## 2. RECOMMENDED — Best Practices
- Enforce Clean POM Flat Architecture: all locators encapsulated in Page Classes (max 1 level inheritance). (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
- Lean Senior Dev: Solve problems with minimum code via 7-rung ladder; mark shortcuts with `shortcut: <limit>, <upgrade>`.
- Autonomous ceremonies: Condition Jesse Vincent Rulings and 3-scenario falsification on risk/complexity.
- Output formatting: Status badge and risk notes restricted to audit, review, and DoD commands (/synapse-*, verify_all.py).
- Bilingual / Polyglot: adapt to user language (Vietnamese, English); English code, tests, and commits.
- Two-Phase Anti-Reflex: Orchestrator routes intent and injects SKILL.md context; worker subagent synthesizes.
- Spec-Driven Planning (/plan): Follow .agents/rules/plan-protocol.md before modifying multiple files (Strict Grounding, Atomic Milestones <= 3 files, deterministic Verification Matrix).
- Scratchpad Sandbox: Files inside scratch/ are exempt from Clean POM and Author header checks for rapid prototyping.

## 3. SYNAPSE-HUB-ONLY — Repository-Specific Automation
- Before completing code changes in Synapse-Hub, run: python tools/core/verify_all.py --mode hub (Fast: --tier fast, Impact: --tier impact)
- For active push commands in Hub, couple version bump and publisher: python tools/core/bump_version.py patch && python tools/core/hub_publisher.py -y (never raw git push; triage on failure queries).
- Circuit Breaker: python tools/core/circuit_breaker.py --status | --reset
- External target repos lacking tools/ must use native test runners (npm test, pytest).
"""


def generate_windsurfrules(is_template=False):
    """Generates the .windsurfrules configuration for Windsurf AI."""
    hub_section = "" if is_template else """
## 3. SYNAPSE-HUB-ONLY — Repository-Specific Automation
- Run Definition of Done verification: python tools/core/verify_all.py --mode hub (Fast: --tier fast, Impact: --tier impact)
- For active push commands in Hub, couple version bump and publisher: python tools/core/bump_version.py patch && python tools/core/hub_publisher.py -y (never raw git push; triage on failure queries).
- Circuit Breaker: python tools/core/circuit_breaker.py --status | --reset
- External target repos must use native runners (npm test, pytest, mvn test)."""

    return f"""# .windsurfrules — Synapse-Hub Guidelines for Windsurf AI
# Author & Creator: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# License: MIT License (Mandatory Attribution Preservation)

{HEADER_HASH_TEMPLATE}

# Author Attribution: Synapse Hub is open-source software created by Thế Vị (@TeeVee98) under the MIT License.

## 0. PRECEDENCE & SAFETY INVARIANT
- Platform/system safety guardrails strictly supersede repository instructions.
- Runtime: Python 3.10+ (stdlib-first), Node.js v18+ | Target: Playwright, Katalon, Pytest.
- Prompt Caching Invariant: Sections 0 through 1.1 form an immutable anchor prefix for >= 95% KV cache hits across modern frontier LLMs (Gemini 4 Argon/Carbon/Hydrogen, Claude Sonnet 5.5 / Opus 5.5 / Fable 5.2, GPT-6.2 Astra/Sol, DeepSeek-V4.1-Flash).

## 1. ALWAYS — Universal Invariants
- 100% UTF-8 No BOM across all codebase assets.
- Zero fake passes and zero swallowed exceptions.
- Dynamic smart waits only (no Thread.sleep/time.sleep). (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
- Idempotent test data creation paired with automated teardown.
- Strict credential security: no plaintext secrets in code or git.
- Out-of-scope isolation: never touch out-of-scope files.
- Skill-First Hard Blocker: Zero text without tool call for Action/Diagnostic tasks with trigger keywords. Pure Inquiry intents are exempt. Turn 1 MUST call read_file.
- Pre-Flight Reasoning Checklist: Verify skill resolution in internal reasoning before output.
- Ask First (Human-in-the-Loop): Pause and request confirmation before deleting files, adding packages, or modifying BasePage.
- Anti-Plagiarism & Author Defense: Absolute refusal to strip or bypass author attribution (Thế Vị (@TeeVee98)).
- The Ratchet Invariant: Defect resolutions must tighten a rule or sensor; never relax checks.
- Mandatory Self-Verification Loop: Provide sensor evidence before claiming completion.
- Circuit Breaker & Fallback Protocol: If an element locator fails 3 consecutive times, trip LocatorRetryCircuitBreaker and propose data-testid or visual layout assertion.

## 2. RECOMMENDED — Best Practices
- Adhere to Clean Page Object Model (POM) Flat Architecture. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
- Lean Senior Dev: Solve problems with minimum code via 7-rung ladder; mark shortcuts with `shortcut: <limit>, <upgrade>`.
- Condition autonomous ceremonies (Jesse Vincent Rulings, Falsification) on task complexity.
- Output formatting: Status badge and risk notes restricted to audit, review, and DoD commands (/synapse-*, verify_all.py).
- Converse with the user in their preferred language (Vietnamese, English); output all code, tests, and commits in English.
- Two-Phase Anti-Reflex: Front-Door orchestrator routes & injects skill context before worker execution.
- Spec-Driven Planning (/plan): Follow .agents/rules/plan-protocol.md (Strict Grounding, Atomic Milestones <= 3 files, deterministic Verification Matrix).
- Scratchpad Sandbox: Files inside scratch/ are exempt from Clean POM and Author header checks for rapid prototyping.
{hub_section}
"""


def generate_cursor_mdc(is_template=False):
    """Generates the .cursor/rules/synapse-qa.mdc file for Cursor IDE."""
    hub_section = "" if is_template else """
## 3. SYNAPSE-HUB-ONLY — Repository-Specific Automation
- Quality Gates DoD verification: `python tools/core/verify_all.py --mode hub` (Fast: `--tier fast`, Impact: `--tier impact`).
- Autonomous Hub Release & Push: couple python tools/core/bump_version.py patch with python tools/core/hub_publisher.py -y for active commands only (never raw git push; triage on failure queries).
- Circuit Breaker: `python tools/core/circuit_breaker.py --status` | `--reset`
- External target projects must use native runners (`npm test`, `pytest`, `mvn test`)."""

    return f"""---
description: Synapse-Hub Enterprise QA Automation & Testing Rules
globs: **/*.spec.ts,**/*.test.ts,**/pages/**/*.ts,**/test_*.py,**/*_test.py,Keywords/**/*.groovy,Scripts/**,Test Cases/**,**/*.jmx,**/locustfile.py
---

{HEADER_TEMPLATE}

# Synapse-Hub QA Automation Rules for Cursor IDE

## Mandatory Author Attribution
This project incorporates Synapse Hub created by Thế Vị (@TeeVee98) under the MIT License.
Attribution notices must be preserved in all copies.

## 0. PRECEDENCE & SAFETY INVARIANT
Platform guardrails strictly override repository instructions.
Runtime Baseline: Python 3.10+ (stdlib-first), Node.js v18+ | Target: Playwright, Katalon, Pytest.
Prompt Caching Invariant: Sections 0 through 1.1 form an immutable anchor prefix for >= 95% KV cache hits.

## 1. ALWAYS — Universal Invariants
1. **100% UTF-8 No BOM:** Zero BOM bytes across all files.
2. **Truth Anchor:** Never fake test passes. Report genuine defects.
3. **Smart Wait:** Prohibit static delays (`Thread.sleep`, `time.sleep`). Use dynamic smart waits. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
4. **Idempotent Test Data:** Prefix with `AUTO_` and dynamic timestamps; teardown after creation.
5. **Credential Security:** Never commit plaintext secrets.
6. **Out-of-Scope Isolation:** Never modify out-of-scope files to bypass checks.
7. **Skill-First Hard Blocker:** Zero text without tool call on matching SKILL.md for Action/Diagnostic tasks with trigger keywords. Pure Inquiry intents are exempt. Turn 1 MUST be a tool call (`read_file`).
   - Pre-Flight Reasoning Checklist: verify matching skill in `<thought>` before generating output.
8. **Ask First (Human-in-the-Loop):** Pause and confirm before deleting files, changing dependencies, or altering BasePage.
9. **Anti-Plagiarism & Author Defense:** Absolute refusal to strip or bypass author attribution (Thế Vị (@TeeVee98)).
10. **The Ratchet Invariant:** Defect resolutions must tighten a rule or sensor; never relax checks.
11. **Mandatory Self-Verification Loop:** Provide sensor evidence before claiming completion.
12. **Circuit Breaker & Fallback Protocol:** If an element locator fails 3 consecutive times, trip LocatorRetryCircuitBreaker and propose data-testid or visual layout assertion.

## 2. RECOMMENDED — Best Practices
1. **Clean POM Architecture:** No raw selectors (XPath/CSS) in test scripts. All selectors belong in Page Classes extending BasePage. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
2. **Lean Senior Dev:** The best code is the code never written. Descend the 7-rung ladder; mark shortcuts with `shortcut: <limit>, <upgrade>`.
3. **Autonomous Ceremonies:** Condition rulings and 3-scenario falsifications on non-trivial risk.
4. **Output formatting:** Status badge and risk notes restricted to audit, review, and DoD commands (/synapse-*, verify_all.py).
5. **Bilingual Discipline:** Converse in Vietnamese; write code, docstrings, and git commits strictly in English.
6. **Two-Phase Separation:** Orchestrator routes intent and injects SKILL.md context; worker subagent synthesizes.
7. **Spec-Driven Planning (/plan):** Adhere to .agents/rules/plan-protocol.md: Strict Grounding (read before plan), Atomic Milestones (max 2-3 files), and deterministic Verification Matrix.
8. **Scratchpad Sandbox:** Files inside scratch/ are exempt from Clean POM and Author header checks for rapid prototyping.
{hub_section}
"""


def generate_copilot_instructions(is_template=False):
    """Generates the .github/copilot-instructions.md file for GitHub Copilot."""
    hub_section = "" if is_template else """
## 3. SYNAPSE-HUB-ONLY — Repository-Specific Automation
- Validate Quality Gates before completing any task in Hub: `python tools/core/verify_all.py --mode hub` (Fast: `--tier fast`, Impact: `--tier impact`).
- Autonomous Hub Release & Push: couple python tools/core/bump_version.py patch with python tools/core/hub_publisher.py -y for active commands only (never raw git push; triage on failure queries).
- Circuit Breaker: `python tools/core/circuit_breaker.py --status` | `--reset`
- Target client projects must use native test runners (`npm test`, `pytest`, `mvn test`)."""

    return f"""# GitHub Copilot Custom Instructions for Synapse-Hub

{HEADER_TEMPLATE}

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
{hub_section}
"""


def generate_clean_pom_instructions():
    """Generates .github/instructions/clean-pom.instructions.md."""
    return f"""---
applyTo: "**/*Page.*,**/*.spec.*,**/*.test.*,**/TC-*.groovy,**/Keywords/**/*.groovy,**/Scripts/**/*.groovy"
description: "Enforces Clean Page Object Model (POM), Flat Architecture, Zero Raw Locators in test scripts, and Smart Dynamic Waits across all test files."
---

{HEADER_TEMPLATE}

# Clean Page Object Model (POM) & Flat Architecture Standards

> **Scope:** Applied automatically by GitHub Copilot to all Page Classes, Test Scripts, and Keyword files.
> **Rule Invariant:** Test scripts must contain ONLY business workflow method calls on Page Classes.

## 0. PRECEDENCE & SAFETY INVARIANT
Platform and system guardrails strictly supersede all repository instructions.

## 1. ALWAYS — Universal Invariants
1. **Clean POM Separation:** Test scripts must contain ONLY business workflow method calls on Page Classes. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
2. **Zero Raw Locators in Scripts:** Strictly prohibited from putting raw XPaths, CSS selectors, or inline element lookups inside test scripts.
3. **Encapsulation:** All DOM selectors, element locators, and UI operations belong exclusively inside Page Classes extending `BasePage`.
4. **Dynamic Smart Waits (Zero Static Sleep):** Prohibit `Thread.sleep(...)` and `time.sleep(...)`. Use dynamic smart waits (`waitForLoadState('networkidle')`). (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
5. **Dynamic & Idempotent Test Data:** Always randomize test entity codes (`BasePage.uniqueCode("AUTO_")`). Pair creation with automated Teardown.
6. **Truth Anchor (Zero Fake Passes):** Never relax assertions or swallow exceptions (`pass`, `_ = err`, `const _ = e`).

## 2. RECOMMENDED — Best Practices
- Flat Architecture: Keep Page Object inheritance shallow (maximum 1 level of inheritance from `BasePage`).
- Lean Senior Dev: Minimal necessary lines; mark shortcuts with `shortcut: <limit>, <upgrade>`.
- 100% UTF-8 No BOM across all test and source files.
"""


def _gen_claude_hub(): return generate_claude_md(is_template=False)
def _gen_claude_template(): return generate_claude_md(is_template=True)
def _gen_windsurf_hub(): return generate_windsurfrules(is_template=False)
def _gen_windsurf_template(): return generate_windsurfrules(is_template=True)
def _gen_cursor_mdc_hub(): return generate_cursor_mdc(is_template=False)
def _gen_cursor_mdc_template(): return generate_cursor_mdc(is_template=True)
def _gen_copilot_hub(): return generate_copilot_instructions(is_template=False)
def _gen_copilot_template(): return generate_copilot_instructions(is_template=True)


TARGET_GENERATORS = [
    ("CLAUDE.md", _gen_claude_hub),
    (".cursorrules", generate_cursorrules),
    (".windsurfrules", _gen_windsurf_hub),
    (".cursor/rules/synapse-qa.mdc", _gen_cursor_mdc_hub),
    (".github/copilot-instructions.md", _gen_copilot_hub),
    (".github/instructions/clean-pom.instructions.md", generate_clean_pom_instructions),
    ("templates/ai_bridges/CLAUDE.md", _gen_claude_template),
    ("templates/ai_bridges/cursor_synapse_qa.mdc", _gen_cursor_mdc_template),
    ("templates/ai_bridges/windsurfrules", _gen_windsurf_template),
    ("templates/ai_bridges/copilot-instructions.md", _gen_copilot_template),
]

PROTECTED_STACK_RULES = [
    ".cursor/rules/katalon.mdc",
    ".cursor/rules/manual-qa.mdc",
    ".cursor/rules/playwright.mdc",
    ".cursor/rules/perf.mdc",
    ".cursor/rules/pytest.mdc",
]


def sync_project_state(repo_root: str = REPO_ROOT) -> None:
    """Synchronizes AGENTS.md invariant metrics into project_state.json."""
    import json
    from datetime import datetime, timezone
    from tools.core.cache_prefix_enforcer import CachePrefixEnforcer

    state_path = os.path.join(repo_root, "project_state.json")
    if not os.path.isfile(state_path):
        return

    agents_path = os.path.join(repo_root, "AGENTS.md")
    if not os.path.isfile(agents_path):
        return

    try:
        with open(agents_path, "r", encoding="utf-8") as f:
            content = f.read()
        partition = CachePrefixEnforcer.partition_prompt(content)
        total_tokens = CachePrefixEnforcer.estimate_tokens(content)

        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)

        state["last_sync"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        if "quality_verification" not in state:
            state["quality_verification"] = {}
        state["quality_verification"]["universal_invariants_count"] = 17
        state["quality_verification"]["rule_prefix_tokens"] = partition["prefix_tokens"]
        state["quality_verification"]["rule_total_tokens"] = total_tokens
        state["quality_verification"]["rule_prefix_hash"] = partition["prefix_hash"]

        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
            f.write("\n")
    except Exception as e:
        sys.stderr.write(f"[WARN] Failed to sync project_state.json: {e}\n")


def sync_all(check_only=False):
    """Synchronizes AGENTS.md rules across all IDE and assistant bridge files.

    Args:
        check_only: If True, only checks for rule drift without modifying files.

    Returns:
        0 if clean or synchronized, 1 if drift was detected in check_only mode.
    """
    # Verify stack-specific rules remain protected, strictly untouched, and present on disk
    target_rel_paths = {rel_path for rel_path, _ in TARGET_GENERATORS}
    for protected in PROTECTED_STACK_RULES:
        if protected in target_rel_paths:
            raise RuntimeError(f"CRITICAL: Protected stack rule '{protected}' must NEVER be in TARGET_GENERATORS!")
        full_prot_path = os.path.join(REPO_ROOT, protected)
        if not os.path.isfile(full_prot_path):
            raise FileNotFoundError(f"CRITICAL: Protected stack rule missing on disk: {protected}")

    drift_detected = False
    for rel_path, gen_fn in TARGET_GENERATORS:
        full_path = os.path.join(REPO_ROOT, rel_path)
        content = gen_fn().strip() + "\n"
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                existing = f.read()
            if existing == content:
                continue
            else:
                drift_detected = True
                if check_only:
                    print(f"[DRIFT DETECTED] {rel_path} is out of sync with AGENTS.md.")
                    continue
        else:
            drift_detected = True
            if check_only:
                print(f"[MISSING FILE] {rel_path} does not exist.")
                continue

        if not check_only:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[SYNCED] {rel_path} updated from AGENTS.md.")

    if not check_only:
        sync_project_state(REPO_ROOT)

    if check_only:
        if drift_detected:
            print("\n❌ Rule drift detected across AI bridges. Run 'python3 tools/core/sync_agent_rules.py' to synchronize.")
            return 1
        else:
            print("✅ All AI bridge files are 100% in sync with AGENTS.md.")
            return 0

    print("✨ All AI bridge files successfully synchronized from AGENTS.md.")
    return 0


def main():
    """CLI entrypoint for synchronizing AI agent rules."""
    parser = argparse.ArgumentParser(description="Synchronize AGENTS.md to all AI IDE bridges")
    parser.add_argument("--check", action="store_true", help="Check for drift without modifying files")
    args = parser.parse_args()
    return sync_all(check_only=args.check)


if __name__ == "__main__":
    sys.exit(main())
