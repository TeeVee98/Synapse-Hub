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
import re
import sys
import argparse
import json
from dataclasses import dataclass
from typing import Any, Dict

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))


@dataclass(frozen=True)
class ClientBridgeRuleBundleDTO:
    """Typed summary of a generated AI bridge rule bundle for Hub or Client mode."""
    mode: str
    content: str
    hub_paths_leaked: int
    config_file: str


@dataclass(frozen=True)
class ZeroCeremonyProfileDTO:
    """Typed summary of a profile-scoped Client AI bridge (`starter`, `standard`, `enterprise`)."""
    profile: str
    bridge_line_count: int
    hub_paths_leaked: int
    mutation_required: bool
    passed: bool
    content: str = ""


STARTER_CLIENT_BRIDGE_MD = """<!-- SYNAPSE-HUB ZERO-CEREMONY CLIENT BRIDGE (Profile: starter) -->
<!-- Attribution: Synapse Hub by Thế Vị (@TeeVee98) | MIT License -->

# QA Automation Rules (Starter Profile)

1. **Clean POM:** Keep locators inside Page Classes; call semantic methods from test specs.
2. **Dynamic Smart Waits:** Never use static sleeps (`waitForTimeout`, `time.sleep`, `Thread.sleep`); use web-first assertions (`await expect(locator).toBeVisible()`).
3. **Zero Fake-Pass (Truth Anchor):** Every test must execute real non-tautological assertions; never swallow errors in empty `catch`/`except` blocks.
4. **Credential Security:** Never hardcode passwords, tokens, or secrets; inject via environment variables.
5. **UTF-8 No BOM & English Code:** Keep source and test files UTF-8 without BOM in clear English.
6. **Fast Empirical Verification:** Before claiming done, run your native runner (`npm test`, `npx playwright test`, `pytest`) or `npx @teevee98/synapse-hub lint`.
"""

STANDARD_CLIENT_BRIDGE_MD = """<!-- SYNAPSE-HUB CLIENT BRIDGE (Profile: standard) -->
<!-- Attribution: Synapse Hub by Thế Vị (@TeeVee98) | MIT License -->

# QA Automation Rules (Standard Profile)

1. **Clean POM:** Encapsulate locators inside Page Classes (<= 1 inheritance level) and avoid raw XPath in test specs.
2. **Dynamic Smart Waits:** Forbid static sleeps (`waitForTimeout`, `time.sleep`, `Thread.sleep`); use web-first assertions and explicit event waits.
3. **Zero Fake-Pass (Truth Anchor):** Require real assertions in every test block; never relax assertions or swallow exceptions.
4. **Dynamic Test Data & Teardown:** Randomize entity codes and clean up created test records.
5. **Credential Security:** Inject secrets exclusively via environment variables or fixtures.
6. **UTF-8 No BOM & English Code:** Keep codebase, tests, and comments in English UTF-8 without BOM.
7. **Verification Loop:** Run native test suites (`npm test`, `npx playwright test`, `pytest`) plus `npx @teevee98/synapse-hub lint` before handoff.
"""

_HUB_PATH_LEAK_RE = re.compile(r"tools/(?:core|lint|orchestration|design|context|report)/")


def generate_client_bridge_markdown(profile: str = "starter") -> ZeroCeremonyProfileDTO:
    """Generates a `< 35`-line Zero-Ceremony client AI bridge for `starter` or full governance for `enterprise`."""
    normalized = (profile or "").strip().lower()
    if normalized not in ("starter", "standard", "enterprise"):
        raise ValueError(f"Unsupported profile '{profile}'. Expected one of: starter, standard, enterprise.")

    if normalized == "starter":
        content = STARTER_CLIENT_BRIDGE_MD.strip() + "\n"
        mutation_required = False
    elif normalized == "standard":
        content = STANDARD_CLIENT_BRIDGE_MD.strip() + "\n"
        mutation_required = False
    else:
        content = generate_claude_md(is_template=True).strip() + "\n"
        mutation_required = True

    line_count = len(content.splitlines())
    leaked = len(_HUB_PATH_LEAK_RE.findall(content))
    passed = (leaked == 0) and (line_count < 35 if normalized == "starter" else line_count > 0)
    return ZeroCeremonyProfileDTO(
        profile=normalized,
        bridge_line_count=line_count,
        hub_paths_leaked=leaked,
        mutation_required=mutation_required,
        passed=passed,
        content=content,
    )


@dataclass(frozen=True)
class RuleAstBundleDTO:
    """Parsed canonical rule sections dynamically extracted from AGENTS.md."""
    invariants_markdown: str
    invariants_bullets: str
    checklist_markdown: str
    invariant_count: int


HEADER_TEMPLATE = """<!-- ============================================================================== -->
<!-- AUTO-GENERATED FROM AGENTS.md — DO NOT EDIT DIRECTLY.                          -->
<!-- Run: python3 tools/core/sync_agent_rules.py                                     -->
<!-- [CACHE-ANCHOR: ROOT-PREFIX-v4.8]                                               -->
<!-- ============================================================================== -->
"""

HEADER_HASH_TEMPLATE = """# ==============================================================================
# AUTO-GENERATED FROM AGENTS.md — DO NOT EDIT DIRECTLY.
# Run: python3 tools/core/sync_agent_rules.py
# [CACHE-ANCHOR: ROOT-PREFIX-v4.8]
# ==============================================================================
"""

CLIENT_HEADER_TEMPLATE = """<!-- ============================================================================== -->
<!-- SYNAPSE-HUB CLIENT AI BRIDGE TEMPLATE (Client Mode)                            -->
<!-- Update via: npx @teevee98/synapse-hub setup                                     -->
<!-- [CACHE-ANCHOR: CLIENT-PREFIX-v5.0]                                             -->
<!-- ============================================================================== -->
"""

CLIENT_HEADER_HASH_TEMPLATE = """# ==============================================================================
# SYNAPSE-HUB CLIENT AI BRIDGE TEMPLATE (Client Mode)
# Update via: npx @teevee98/synapse-hub setup
# [CACHE-ANCHOR: CLIENT-PREFIX-v5.0]
# ==============================================================================
"""


CLIENT_INVARIANTS_MD = """1. **100% UTF-8 No BOM:** Zero BOM bytes (`0xEF, 0xBB, 0xBF`) across all repo/test files (`.groovy`, `.java`, `.ts`, `.py`, `.json`, `.md`).
2. **Truth Anchor (Zero Fake Passes):** Never relax assertions, skip validation steps, write empty tests (0 asserts), or catch-and-swallow exceptions (`pass`, dummy suppression `_ = err` or `_ = False`, `const _ = e`). Report AUT defects honestly.
3. **Dynamic Smart Waits Only:** Static sleeps (`Thread.sleep`, `time.sleep`, `waitForTimeout`) strictly prohibited in test scripts. Use web-first assertions (`expect(locator).toBeVisible()`). For page navigation and asynchronous hydration, use bounded explicit event waits (`waitForURL`, `waitForResponse`); avoid unconditional `waitForLoadState('networkidle')`. *(Automation code only; exempt for Manual QA specs)*.
4. **Dynamic & Idempotent Test Data:** Always randomize test entity codes with dynamic timestamps/prefixes (`BasePage.uniqueCode("AUTO_")`, `DataGenerator`) to eliminate DB collisions. Pair creation with automated Teardown cleanup.
5. **Strict Credential Security:** Never commit raw plaintext passwords, secret tokens, private keys, or cloud credentials. Inject secrets via environment variables or fixtures.
6. **Out-of-Scope Isolation & Stop-and-Report:** When verification gates fail due to legacy defects in files outside task scope, never modify those files or write bypasses. Stop, report with evidence, and ask user.
7. **Skill-First Context Routing:** Before modifying test code or running audits, read `PROJECT_AI_GUIDE.md` and applicable local QA skill standards first. Pure conceptual inquiries and single-line micro-fixes are exempt.
8. **Universal Intent Disambiguation:** Action (execute commanded tool) vs Diagnostic (read-only inspection; zero mutating tools) vs Inquiry (conceptual explanation).
9. **Ask First (Human-in-the-Loop Safeguards):** Pause and obtain user confirmation before deleting test scripts/data, changing dependencies (`package.json`/`pyproject.toml`), modifying shared `BasePage`, or breaking schemas.
10. **License & Provenance Respect:** Preserve Synapse-Hub MIT License attribution in Synapse-Hub template/plugin files (`Thế Vị (@TeeVee98)`), and never alter your organization's existing license or copyright headers.
11. **The Ratchet Invariant (Monotonic Quality Ratchet):** Every defect resolution or post-mortem should tighten a test assertion, lint rule, or guard. Relaxing assertions to manufacture a pass is strictly prohibited.
12. **Mandatory Self-Verification Loop (Empirical Verification Principle):** Before marking any task complete, execute the project's native test runner (`npm test`, `npx playwright test`, `pytest`) or `npx @teevee98/synapse-hub verify` and provide fresh empirical output.
13. **Circuit Breaker & Path-Scoped Rollback Hygiene Protocol:** If a locator, test action, or command fails 2 consecutive times on the same target (`synapse.config.json::circuit_breaker.max_fix_attempts`), stop blind retry loops, revert only touched files (`git checkout -- <target_files>`), never run `git reset --hard`, and report the root cause.
14. **Anti-Premature Done & 4-Scenario Battery:** Do not claim completion without terminal proof covering: a) Positive path, b) Negative/error handling, c) Boundary/empty inputs, d) Integration or CLI/API contract checks.
15. **Test-First Verification (Red -> Green -> Audit):** For non-trivial runtime logic changes (`> 2` files), confirm new tests fail before the fix (Red), pass after the fix (Green), and pass the project's lint/quality checks.
16. **English-Only Codebase & Rules:** Keep code, test scripts, Page Classes, docstrings, and commit messages in clear English while conversing in the user's preferred language.
17. **Mandatory Adversarial Self-Audit:** Before declaring non-trivial changes complete, review your own diff critically for null/None/KeyError edge cases, logic boundary slips, tautological assertions, and broken callers."""

CLIENT_INVARIANTS_BULLETS = "\n".join(
    f"- **{line.split('. **', 1)[1]}" if ". **" in line else f"- {line}"
    for line in CLIENT_INVARIANTS_MD.splitlines()
)

CLIENT_CHECKLIST_MD = """Verify before emitting your final response:
- **Context & Grounding:** Read `PROJECT_AI_GUIDE.md` and target files before editing; use real assertions only.
- **Empirical Verification:** Execute native test runners (`npm test`, `pytest`, `npx playwright test`) or `npx @teevee98/synapse-hub verify` and share fresh terminal evidence.
- **Adversarial Safety & Hygiene:** Audit edge cases (nulls, boundaries, error paths) and confirm clean `git status` with no broken edits left behind."""

CLIENT_SUPER_PLAN_MD = """1. **Strict Grounding ("Read First – Plan Later"):** Always read target files and existing symbols before proposing edits.
2. **Structured Plan:** List Affected Files & Blast Radius, Interfaces/Data Flow, Atomic Milestones (`<= 3` files per milestone with rollback hook), and Verification Matrix (concrete test commands).
3. **Test-First Sequential Execution (`/solo` vs `/teamwork`):** Default to sequential Single-Agent `/solo` execution in one session (no `swarm` workers or parallel subagents unless `/teamwork` is explicitly invoked); define failing scenarios upfront and verify with native test runners (`npm test`, `pytest`, `npx playwright test`) or `npx @teevee98/synapse-hub verify`."""


CANONICAL_INVARIANTS_MD = """1. **100% UTF-8 No BOM:** Zero BOM bytes (`0xEF, 0xBB, 0xBF`) across all repo/test files (`.groovy`, `.java`, `.ts`, `.py`, `.json`, `.md`).
2. **Truth Anchor (Zero Fake Passes):** Never relax assertions, skip validation steps, write empty tests (0 asserts), or catch-and-swallow exceptions (`pass`, dummy suppression `_ = err` or `_ = False`, `const _ = e`). Report AUT defects honestly.
3. **Dynamic Smart Waits Only:** Static sleeps (`Thread.sleep`, `time.sleep`, `waitForTimeout`) strictly prohibited in test scripts. Use web-first assertions (`expect(locator).toBeVisible()`). For page navigation and asynchronous hydration, use bounded explicit event waits (`waitForURL`, `waitForResponse`); avoid unconditional `waitForLoadState('networkidle')`. *(Automation code only; exempt for Manual QA specs)*.
4. **Dynamic & Idempotent Test Data:** Always randomize test entity codes with dynamic timestamps/prefixes (`BasePage.uniqueCode("AUTO_")`, `DataGenerator`) to eliminate DB collisions. Pair creation with automated Teardown cleanup.
5. **Strict Credential Security:** Never commit raw plaintext passwords, secret tokens, private keys, or cloud credentials. Inject secrets via environment variables or fixtures.
6. **Out-of-Scope Isolation & Stop-and-Report:** When verification gates fail due to legacy defects in files outside task scope, never modify those files or write bypasses. Stop, report with evidence, and ask user.
7. **Skill-First Hard Blocker (Context-Aware Intent & Scope Routing):** Action/Diagnostic intents modifying code or running audits within skill-managed domains MUST call `read_file` on `skills_index.json` and matching `SKILL.md` in Turn 1 before conversational text. Mechanically evaluated via `tools/core/skill_router.py`. Pure Inquiry, read-only diagnostic surveys, and single-line micro-fixes outside skill domains are exempt.
8. **Universal Intent Disambiguation:** Action (execute commanded tool) vs Diagnostic (read-only inspection; zero mutating tools) vs Inquiry (conceptual explanation).
9. **Ask First (Human-in-the-Loop Safeguards):** Pause and obtain user confirmation before deleting test scripts/data, changing dependencies (`package.json`/`pyproject.toml`), modifying shared `BasePage`, or breaking schemas.
10. **Author Attribution & Provenance Invariant:** Mandatory attribution crediting Thế Vị (@TeeVee98) under the MIT License must be preserved across all codebase files, package manifests, and distributions. Physical provenance integrity is mechanically enforced via `tools/core/author_integrity.py` and CI/CD release provenance gates.
11. **The Ratchet Invariant (Monotonic Quality Ratchet):** Every defect resolution or post-mortem MUST tighten a Guide or Sensor. Relaxing assertions or removing rules to manufacture a pass is strictly prohibited.
12. **Mandatory Self-Verification Loop (Empirical Verification Principle):** Before marking any task complete, the agent MUST execute the designated Sensor (tests, linter, or quality gate) and provide fresh empirical evidence. Zero claims without proof.
13. **Circuit Breaker & Path-Scoped Rollback Hygiene Protocol:** If locator, test action, or tool call fails 2 consecutive times on same target (`synapse.config.json::circuit_breaker.max_fix_attempts`), trip `LocatorRetryCircuitBreaker`. Blind loops (> 2) forbidden. Execute safe, path-scoped rollback (`git checkout -- <target_files>` or `tools/lint/plan_schema_sentinel.py::rollback_path_scoped` and safe removal of untracked created files). Blanket destructive commands (`git reset --hard`, `git clean -f`) strictly prohibited. Verify clean `git status` for touched files, and emit Escalation Report proposing screenshot diff or requesting dev `data-testid`. Zero half-broken edits on disk.
14. **Anti-Premature Done & 4-Scenario Battery:** Strictly forbid claiming completion ("done/xong") without raw terminal proof across 4 scenarios: a) Positive, b) Negative (handled errors without crash), c) Boundary (empty/null), d) Scope-appropriate verification: CLI flags (`--json`, `--gate`, `--output`) for CLI tools, or Exception Handling & Edge-Case Resilience for libraries/subsystems. Skill edits: `validate_skills_schema.py` & `lint_ai_docs.py`; code edits: `infer_linter.py`.
15. **Autonomous Solo Mandate (Deterministic Test & Mutation Verification):** For any runtime logic code modification or feature implementation (excluding pure documentation, typos, or read-only diagnostic inspections exempt under Invariant 7, and Tier-0 micro-fixes <= 2 files with dedicated passing unit tests), autonomously execute the 4-phase verification pipeline (`tools/orchestration/solo_runner.py` / `.agent/skills/solo/SKILL.md`): a) Red test failure certification (`--red`), b) Green implementation verification (`--green`), c) Syntactic/AST mutation score >= 80.0% (`--mutation`), and d) Quality Gates verification (`verify_all.py`). Attach forensic execution receipts (Red, Green, Mutation) in delivery report.
16. **English-Only Codebase & Rules (Bilingual Discipline Invariant):** All codebase files, test scripts, Page Classes, docstrings, commits, and rule files (`AGENTS.md`, `standards/*`, `testing/*`, `.cursor/rules/*`) must remain strictly in English to prevent semantic drift and optimize LLM KV cache hit rates. Whitelists localization test assets and end-user guides (`README.md`, `*.vi.md`). Non-English diacritics forbidden outside author attribution (`Thế Vị (@TeeVee98)`). Enforced via `python tools/lint/invariant_checker.py --rule 16`.
17. **Mandatory Adversarial Self-Audit (Adversarial Review Invariant):** Before declaring ANY non-trivial implementation complete (exempt for pure documentation, typos, read-only diagnostics, and Tier-0 micro-fixes <= 2 files with dedicated passing unit tests, aligned with Invariant 15), autonomously assume the persona of an independent adversarial reviewer / senior security auditor without user prompting. Execute `tools/orchestration/solo_runner.py --purple` and probe 4 contrarian crash vectors: a) Null/None/KeyError payloads, b) Logic boundary anomalies & cross-line regex slips, c) Tautological/fake assertions, d) Downstream caller breakage via `call_graph_indexer.py`. Embed explicit "Adversarial Code Audit Receipt" in delivery report. Premature completion without receipt is strictly prohibited."""

CANONICAL_CHECKLIST_MD = """Verify before emitting any token in final response across 3 Cognitive Pillars:
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
  8. `[Workspace Hygiene & Context Alert]`: Clean git status verified (no broken speculative edits); proactively alert `/compact` if session context is bloated?"""

CANONICAL_SUPER_PLAN_MD = """> **Mandatory Planning Guardrail (Autonomous Super-Plan Routing):** Whenever planning, roadmapping, architectural design, or `/plan` or `/super-plan` is invoked, automatically activate the **Spec-Driven Super-Plan Pipeline** (`.agent/skills/super-plan/SKILL.md` / `tools/design/super_plan_engine.py`). Depth adapts via **Dynamic Risk-Routing** (RiskScore):
> - **Tier 0 (Fast-Track Micro-Plan, <= 2 files):** Instant < 10s turnaround, single DAG milestone with AST anchors, zero MCQ interruptions.
> - **Tier 1 (Standard Plan, 3-5 files):** Execution DAG, concrete interfaces, typed manifests, and standard verification matrix.
> - **Tier 2 (Deep Architectural Super-Plan, >= 6 files):** Full 5-stage closed loop: AST Recon -> Ambiguity Gate (<= 3 MCQs with Counter-Arguments) -> Execution DAG + Typed Manifests -> Mechanical Mutation Sentinel -> Self-Healing DAG & Plan Harvesting to `docs/adr/`.

1. **Strict Grounding ("Read First – Plan Later"):** Strictly FORBIDDEN to propose modifying any file without first reading its current contents or inspecting symbols (`read_file`, `context_slicer.py`, `polyglot_ast_parser.py`). Zero blind guessing.
2. **Mandatory 4-Section Plan Template:** Every plan must strictly contain: Affected Files & Blast Radius (`[MODIFY]`/`[CREATE]`/`[DELETE]` with structural anchors `::Symbol`), Data Flow & Interfaces, Atomic Milestones (Execution DAG <= 3 files/milestone, `depends_on`, Circuit Breaker, Rollback Hook), and Verification Matrix (concrete test commands). Full specification template in `.agent/skills/super-plan/SKILL.md`.
3. **Formula ("Invariants + Constraints"):** Trigger `/plan` or `/super-plan` using: Context, Invariants, Edge cases, Done when. (See `.agent/skills/super-plan/SKILL.md`).
4. **Test-First Planning & Single-Agent `/solo` Default:** Verification Matrix explicitly enumerates deterministic test scenarios (`Input X -> Expect Error Y`). Default plan execution and handoffs to sequential Single-Agent `/solo` (`.agent/skills/solo/SKILL.md`, NO `swarm` workers or parallel subagents); only emit or parallelize `[PARALLEL_OK]` milestones when the user explicitly invokes `/teamwork`."""


CANONICAL_INVARIANTS_BULLETS = "\n".join(
    f"- **{line.split('. **', 1)[1]}" if ". **" in line else f"- {line}"
    for line in CANONICAL_INVARIANTS_MD.splitlines()
)


def _to_bullet_invariants(md_text: str) -> str:
    """Converts numbered Markdown invariants into bulleted invariants."""
    return "\n".join(
        f"- **{line.split('. **', 1)[1]}" if ". **" in line else f"- {line}"
        for line in md_text.splitlines()
        if line.strip()
    )


def extract_agents_md_sections(agents_md_path: str = os.path.join(REPO_ROOT, "AGENTS.md")) -> RuleAstBundleDTO:
    """Dynamically parses Section 1 (Universal Invariants) and Section 1.1 (Checklist) from AGENTS.md."""
    invariants_md = CANONICAL_INVARIANTS_MD
    checklist_md = CANONICAL_CHECKLIST_MD

    if agents_md_path and os.path.isfile(agents_md_path):
        try:
            with open(agents_md_path, "r", encoding="utf-8") as fh:
                raw = fh.read()

            m_inv = re.search(
                r"^##\s+1\.\s+ALWAYS\s+—\s+Universal\s+Invariants\s*\n(.*?)(?=\n---|\n##\s+)",
                raw,
                re.MULTILINE | re.DOTALL,
            )
            if m_inv and m_inv.group(1).strip():
                invariants_md = m_inv.group(1).strip()

            m_chk = re.search(
                r"^##\s+1\.1\s+PRE-FLIGHT\s+REASONING\s+CHECKLIST[^\n]*\n(.*?)(?=\n---|\n##\s+)",
                raw,
                re.MULTILINE | re.DOTALL,
            )
            if m_chk and m_chk.group(1).strip():
                checklist_md = m_chk.group(1).strip()
        except OSError as exc:
            sys.stderr.write(f"[WARN] Unable to read {agents_md_path}: {exc}\n")

    bullets = _to_bullet_invariants(invariants_md)
    inv_count = len(re.findall(r"^\d+\.\s+\*\*", invariants_md, re.MULTILINE))
    if inv_count == 0:
        inv_count = len([ln for ln in invariants_md.splitlines() if ln.strip()])

    return RuleAstBundleDTO(
        invariants_markdown=invariants_md,
        invariants_bullets=bullets,
        checklist_markdown=checklist_md,
        invariant_count=inv_count,
    )


def build_client_bridge_bundle(mode: str = "client") -> ClientBridgeRuleBundleDTO:
    """Builds a Hub or Client rule bundle and audits for Hub-internal path leakage."""
    is_client = (mode != "hub")
    content = generate_claude_md(is_template=is_client)
    leaked = len(re.findall(r"tools/(?:core|lint|orchestration|design|context|report)/", content))
    return ClientBridgeRuleBundleDTO(
        mode="client" if is_client else "hub",
        content=content,
        hub_paths_leaked=leaked,
        config_file="synapse.config.json",
    )


def generate_claude_md(is_template=False):
    """Generates the unified CLAUDE.md file compiling agent rules and standards."""
    header = CLIENT_HEADER_TEMPLATE if is_template else HEADER_TEMPLATE
    hub_bundle = None if is_template else extract_agents_md_sections()
    invariants = CLIENT_INVARIANTS_MD if is_template else hub_bundle.invariants_markdown
    checklist = CLIENT_CHECKLIST_MD if is_template else hub_bundle.checklist_markdown
    super_plan = CLIENT_SUPER_PLAN_MD if is_template else CANONICAL_SUPER_PLAN_MD
    project_map = (
        "- **Project Config:** `synapse.config.json` | `PROJECT_AI_GUIDE.md` | Native Test Suites (`tests/`)."
        if is_template
        else "- **Project Map:** `skills/` (57 Modular Skills, `skills_index.json`) | `tools/` (CLI Automations, `tools/TOOL_CATALOG.json`) | `tests/` (Automated Pytest Suites) | `templates/` (AI Bridges)."
    )
    telemetry_cmd = "npx @teevee98/synapse-hub verify" if is_template else "/synapse-audit, /synapse-review, verify_all.py"

    quick_commands = """## ⚡ Quick Commands
- Native Test Suite: `npm test` (or `pytest`)
- End-to-End Suite: `npx playwright test`
- Synapse Quality Gates: `npx @teevee98/synapse-hub verify`
- Code Linter: `npm run lint` (or `ruff check .`)""" if is_template else """## ⚡ Quick Commands
- Full 11 Quality Gates: `python tools/core/verify_all.py --mode hub`
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

{header}

> **Author Attribution:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License. Attribution notices must be preserved in Synapse-Hub copies.

---

## 0. PRECEDENCE & TECH STACK
- Platform and system guardrails strictly override all repository-level instructions.
- Precedence: System Guardrails > Core Project Rules (`standards/*`, `testing/*`) > Local Skills > Generic Plugins.
- **Tech Stack Baseline:** Python 3.10+ (Standard Library first), Node.js v18+ | macOS, Linux, Windows.
- **Target Frameworks:** Playwright (TS/Python), Katalon (Groovy), Pytest, Cypress.
{project_map}

### 0.2 PROMPT CACHING & IMMUTABLE PREFIX ARCHITECTURE
Sections 0 through 1.1 constitute an immutable anchor prefix engineered for >= 95% LLM KV prompt-cache hit rates across modern frontier and reasoning LLMs with context caching (Gemini, Claude, GPT, DeepSeek). Append dynamic task details after Section 1.1.

---

{quick_commands}

---

## 1. ALWAYS — Universal Invariants
{invariants}

---

## 1.1 PRE-FLIGHT REASONING CHECKLIST (Mandatory Pre-Action Analysis)
{checklist}

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
   - Explicit Architectural Rulings (`Ruling: <decision> — <rationale> — <cost if wrong>`): Mandatory for architectural forks, breaking changes, or non-trivial tradeoffs. Omit for trivial doc/typo fixes.
   - Three-Scenario Empirical Falsification (Nominal, Degradation, Boundary): Mandatory before certifying core test cases or complex locators.
4. **Bilingual & Polyglot Communication & Gated Telemetry:**
   - Fluently adapt conversationally to user language (Vietnamese, English, etc.); default to English for international contributors.
   - Status badge and risk notes are restricted to audit, review, and quality-gate commands ({telemetry_cmd}).
   - Codebase files, test scripts, Page Classes, docstrings, and commits strictly in English.
   - Read English versions (`*.en.md`) when bilingual docs exist to preserve tokens.
8. **Scratchpad Sandbox Allowance:** Files located inside `scratch/` are explicitly exempt from Clean POM and Author header rules to facilitate rapid prototyping, quick API probing, and ephemeral POCs. Never promote unreviewed code from `scratch/` to `tests/`.
{hub_only_section}---

## 4. EXECUTION MODE: SINGLE-AGENT (/solo) vs /teamwork
- **Default (`/solo` — Single-Agent Sequential):** Execute milestones sequentially in one active session (`Red -> Blue -> Purple`). It is **STRICTLY FORBIDDEN** to spawn `swarm` workers or parallel subagents when executing via `/solo` or when the user did not explicitly invoke `/teamwork` or request parallel workers.
- **Opt-In (`/teamwork` — Multi-Worker Parallel):** Only when explicitly invoked by the user, the Front-Door (`orchestrator`) routes intent and injects skill context before parallel worker execution on disjoint `[PARALLEL_OK]` milestones.

---

## 5. SPEC-DRIVEN PLANNING & EXECUTION PROTOCOL (/plan & /super-plan)
{super_plan}
"""


def generate_cursorrules():
    """Generates the .cursorrules file compiling agent rules for Cursor AI."""
    hub_bundle = extract_agents_md_sections()
    return f"""# .cursorrules — Synapse-Hub Guidelines for Cursor AI
# Author & Creator: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# License: MIT License (Mandatory Attribution Preservation)

{HEADER_HASH_TEMPLATE}

# Author Attribution: Synapse Hub is open-source software created by Thế Vị (@TeeVee98) under the MIT License.

## 0. PRECEDENCE & SAFETY INVARIANT
- Platform and system guardrails strictly supersede all repository instructions.
- Runtime: Python 3.10+ (stdlib-first), Node.js v18+ | Target: Playwright, Katalon, Pytest.
- Prompt Caching Invariant: Sections 0 through 1.1 form an immutable anchor prefix for >= 95% KV cache hits across modern frontier and reasoning LLMs with context caching (Gemini, Claude, GPT, DeepSeek).

## 1. ALWAYS — Universal Invariants
{hub_bundle.invariants_bullets}

---

## 1.1 PRE-FLIGHT REASONING CHECKLIST
{hub_bundle.checklist_markdown}

## 2. RECOMMENDED — Best Practices
- Enforce Clean POM Flat Architecture: all locators encapsulated in Page Classes (max 1 level inheritance). (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
- Lean Senior Dev: Solve problems with minimum code via 7-rung ladder; mark shortcuts with `shortcut: <limit>, <upgrade>`.
- Autonomous ceremonies: Condition Explicit Architectural Rulings (`Ruling: <decision> — <rationale> — <cost if wrong>`) and 3-scenario falsification (Nominal, Degradation, Boundary) on risk/complexity.
- Output formatting: Status badge and risk notes restricted to audit, review, and DoD commands (/synapse-*, verify_all.py).
- Bilingual / Polyglot: adapt to user language (Vietnamese, English); English code, tests, and commits.
- Execution Mode (`/solo` vs `/teamwork`): Default to sequential Single-Agent `/solo` in one session (`Red -> Blue -> Purple`); strictly FORBIDDEN to spawn `swarm` workers or parallel subagents unless `/teamwork` or parallel workers are explicitly requested.
- Spec-Driven Planning (/plan & /super-plan): Follow standards/qa-process/plan-protocol.md and .agent/skills/super-plan/SKILL.md (Strict Grounding, Atomic Milestones <= 3 files, 12 plan mutation vectors, self-healing execution, `/solo` sequential default).
- Autonomous Solo Verification: Execute 4-phase verification (Red, Green, Mutation >= 80%, and Adversarial Audit) in a single session without spawning `swarm` workers.
- Scratchpad Sandbox: Files inside scratch/ are exempt from Clean POM and Author header checks for rapid prototyping.

## 3. SYNAPSE-HUB-ONLY — Repository-Specific Automation
- Before completing code changes in Synapse-Hub, run: python tools/core/verify_all.py --mode hub (Fast: --tier fast, Impact: --tier impact)
- For active push commands in Hub, couple version bump and publisher: python tools/core/bump_version.py patch && python tools/core/hub_publisher.py -y (never raw git push; triage on failure queries).
- Circuit Breaker: python tools/core/circuit_breaker.py --status | --reset
- External target repos lacking tools/ must use native test runners (npm test, pytest).
"""


def generate_windsurfrules(is_template=False):
    """Generates the .windsurfrules configuration for Windsurf AI."""
    header = CLIENT_HEADER_HASH_TEMPLATE if is_template else HEADER_HASH_TEMPLATE
    hub_bundle = None if is_template else extract_agents_md_sections()
    invariants_bullets = CLIENT_INVARIANTS_BULLETS if is_template else hub_bundle.invariants_bullets
    checklist = CLIENT_CHECKLIST_MD if is_template else hub_bundle.checklist_markdown
    telemetry_cmd = "npx @teevee98/synapse-hub verify" if is_template else "/synapse-*, verify_all.py"
    hub_section = "" if is_template else """
## 3. SYNAPSE-HUB-ONLY — Repository-Specific Automation
- Run Definition of Done verification: python tools/core/verify_all.py --mode hub (Fast: --tier fast, Impact: --tier impact)
- For active push commands in Hub, couple version bump and publisher: python tools/core/bump_version.py patch && python tools/core/hub_publisher.py -y (never raw git push; triage on failure queries).
- Circuit Breaker: python tools/core/circuit_breaker.py --status | --reset
- External target repos must use native runners (npm test, pytest, mvn test)."""

    return f"""# .windsurfrules — Synapse-Hub Guidelines for Windsurf AI
# Author & Creator: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# License: MIT License (Mandatory Attribution Preservation)

{header}

# Author Attribution: Synapse Hub is open-source software created by Thế Vị (@TeeVee98) under the MIT License.

## 0. PRECEDENCE & SAFETY INVARIANT
- Platform/system safety guardrails strictly supersede repository instructions.
- Runtime: Python 3.10+ (stdlib-first), Node.js v18+ | Target: Playwright, Katalon, Pytest.
- Prompt Caching Invariant: Sections 0 through 1.1 form an immutable anchor prefix for >= 95% KV cache hits across modern frontier and reasoning LLMs with context caching (Gemini, Claude, GPT, DeepSeek).

## 1. ALWAYS — Universal Invariants
{invariants_bullets}

---

## 1.1 PRE-FLIGHT REASONING CHECKLIST
{checklist}

## 2. RECOMMENDED — Best Practices
- Adhere to Clean Page Object Model (POM) Flat Architecture. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
- Lean Senior Dev: Solve problems with minimum code via 7-rung ladder; mark shortcuts with `shortcut: <limit>, <upgrade>`.
- Condition autonomous ceremonies (Explicit Architectural Rulings, 3-scenario falsification) on task complexity.
- Output formatting: Status badge and risk notes restricted to audit, review, and DoD commands ({telemetry_cmd}).
- Converse with the user in their preferred language (Vietnamese, English); output all code, tests, and commits in English.
- Execution Mode (`/solo` vs `/teamwork`): Default to sequential Single-Agent `/solo` in one session; strictly FORBIDDEN to spawn `swarm` workers or parallel subagents unless `/teamwork` or parallel workers are explicitly requested.
- Spec-Driven Planning (/plan & /super-plan): Read target files before proposing edits, group work into atomic milestones (<= 3 files), define concrete verification commands, and default handoffs to `/solo`.
- Test-First Verification: Certify failing tests before fixes (Red -> Green) and self-audit edge cases before completion.
- Scratchpad Sandbox: Files inside scratch/ are exempt from Clean POM and Author header checks for rapid prototyping.
{hub_section}
"""


def generate_cursor_mdc(is_template=False):
    """Generates the .cursor/rules/synapse-qa.mdc file for Cursor IDE."""
    header = CLIENT_HEADER_TEMPLATE if is_template else HEADER_TEMPLATE
    hub_bundle = None if is_template else extract_agents_md_sections()
    invariants = CLIENT_INVARIANTS_MD if is_template else hub_bundle.invariants_markdown
    checklist = CLIENT_CHECKLIST_MD if is_template else hub_bundle.checklist_markdown
    telemetry_cmd = "npx @teevee98/synapse-hub verify" if is_template else "/synapse-*, verify_all.py"
    hub_section = "" if is_template else """
## 3. SYNAPSE-HUB-ONLY — Repository-Specific Automation
- Quality Gates DoD verification: `python tools/core/verify_all.py --mode hub` (Fast: `--tier fast`, Impact: `--tier impact`).
- Autonomous Hub Release & Push: couple python tools/core/bump_version.py patch with python tools/core/hub_publisher.py -y for active commands only (never raw git push; triage on failure queries).
- Circuit Breaker: `python tools/core/circuit_breaker.py --status` | `--reset`
- External target projects must use native runners (`npm test`, `pytest`, `mvn test`)."""

    return f"""---
description: Synapse-Hub Enterprise QA Automation & Testing Rules
globs: **/*.spec.ts,**/*.test.ts,**/pages/**/*.ts,**/test_*.py,**/*_test.py,Keywords/**/*.groovy,Scripts/**,Test Cases/**,**/*.jmx,**/locustfile.py
alwaysApply: true
---

{header}

# Synapse-Hub QA Automation Rules for Cursor IDE

## Mandatory Author Attribution
This project incorporates Synapse Hub created by Thế Vị (@TeeVee98) under the MIT License.
Attribution notices must be preserved in Synapse-Hub copies.

## 0. PRECEDENCE & SAFETY INVARIANT
Platform guardrails strictly override repository instructions.
Runtime Baseline: Python 3.10+ (stdlib-first), Node.js v18+ | Target: Playwright, Katalon, Pytest.
Prompt Caching Invariant: Sections 0 through 1.1 form an immutable anchor prefix for >= 95% KV cache hits across modern frontier and reasoning LLMs with context caching (Gemini, Claude, GPT, DeepSeek).

## 1. ALWAYS — Universal Invariants
{invariants}

---

## 1.1 PRE-FLIGHT REASONING CHECKLIST
{checklist}

## 2. RECOMMENDED — Best Practices
1. **Clean POM Architecture:** No raw selectors (XPath/CSS) in test scripts. All selectors belong in Page Classes extending BasePage. (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
2. **Lean Senior Dev:** The best code is the code never written. Descend the 7-rung ladder; mark shortcuts with `shortcut: <limit>, <upgrade>`.
3. **Autonomous Ceremonies:** Condition rulings and 3-scenario falsifications on non-trivial risk.
4. **Output formatting:** Status badge and risk notes restricted to audit, review, and DoD commands ({telemetry_cmd}).
5. **Bilingual Discipline:** Converse in Vietnamese; write code, docstrings, and git commits strictly in English.
6. **Execution Mode (`/solo` vs `/teamwork`):** Default to sequential Single-Agent `/solo` in one session; strictly FORBIDDEN to spawn `swarm` workers or parallel subagents unless `/teamwork` or parallel workers are explicitly requested.
7. **Spec-Driven Planning (/plan & /super-plan):** Strict Grounding (read before planning), Atomic Milestones <= 3 files, explicit verification commands, and sequential `/solo` default.
8. **Test-First Verification:** Confirm Red -> Green transitions and run an adversarial edge-case audit before completion.
9. **Scratchpad Sandbox:** Files inside scratch/ are exempt from Clean POM and Author header checks for rapid prototyping.
{hub_section}
"""


def generate_copilot_instructions(is_template=False):
    """Generates the .github/copilot-instructions.md file for GitHub Copilot."""
    header = CLIENT_HEADER_TEMPLATE if is_template else HEADER_TEMPLATE
    hub_bundle = None if is_template else extract_agents_md_sections()
    invariants_bullets = CLIENT_INVARIANTS_BULLETS if is_template else hub_bundle.invariants_bullets
    checklist = CLIENT_CHECKLIST_MD if is_template else hub_bundle.checklist_markdown
    hub_section = "" if is_template else """
## 3. SYNAPSE-HUB-ONLY — Repository-Specific Automation
- Validate Quality Gates before completing any task in Hub: `python tools/core/verify_all.py --mode hub` (Fast: `--tier fast`, Impact: `--tier impact`).
- Autonomous Hub Release & Push: couple python tools/core/bump_version.py patch with python tools/core/hub_publisher.py -y for active commands only (never raw git push; triage on failure queries).
- Circuit Breaker: `python tools/core/circuit_breaker.py --status` | `--reset`
- Target client projects must use native test runners (`npm test`, `pytest`, `mvn test`)."""

    return f"""# GitHub Copilot Custom Instructions for Synapse-Hub

{header}

> **Project:** Synapse-Hub Enterprise QA Automation
> **Author:** Thế Vị (@TeeVee98) — MIT License

## 0. PRECEDENCE & SAFETY INVARIANT
- Platform and system guardrails strictly override all repository-level instructions.
- Runtime Baseline: Python 3.10+ (stdlib-first), Node.js v18+ | Target: Playwright, Katalon, Pytest.
- Prompt Caching Invariant: Sections 0 through 1.1 form an immutable anchor prefix for >= 95% KV cache hits across modern frontier and reasoning LLMs with context caching (Gemini, Claude, GPT, DeepSeek).

## 1. ALWAYS — Universal Invariants
{invariants_bullets}

---

## 1.1 PRE-FLIGHT REASONING CHECKLIST
{checklist}

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
4. **Dynamic Smart Waits (Zero Static Sleep):** Prohibit `Thread.sleep(...)`, `time.sleep(...)`, and `waitForTimeout(...)`. Use web-first assertions (`expect(locator).toBeVisible()`) and explicit event waits (`waitForURL`, `waitForResponse`). (Applies to automation code only; exempt for Manual QA Markdown specs and test cases).
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


def generate_slash_workflow_markdown(workflow: str, ide: str = "claude") -> str:
    """Generates Hub/Enterprise slash command or workflow Markdown for /super-plan, /solo, and /review."""
    wf = (workflow or "").strip().lower()
    if wf not in ("super-plan", "solo", "review"):
        raise ValueError(f"Unsupported slash workflow '{workflow}'. Expected 'super-plan', 'solo', or 'review'.")
    target_ide = (ide or "claude").strip().lower()
    if target_ide not in ("claude", "windsurf"):
        raise ValueError(f"Unsupported IDE target '{ide}'. Expected 'claude' or 'windsurf'.")

    frontmatter = (
        f"---\ndescription: Synapse-Hub /{wf} workflow (Single-Agent Spec-Driven Control Plane)\n---\n\n"
        if target_ide == "windsurf"
        else ""
    )
    if wf == "super-plan":
        return f"""{frontmatter}{HEADER_TEMPLATE}
# /super-plan — Spec-Driven Planning Pipeline (v2.0)

> **Attribution:** Synapse Hub by Thế Vị (@TeeVee98) | MIT License
> **Canonical Skill:** `.agent/skills/super-plan/SKILL.md`
> **Unified CLI:** `agent-qa super-plan` (or `python3 tools/design/super_plan_engine.py`)

## Workflow Steps
1. **Risk-Routing & AST Grounding:** Read target files and run `agent-qa super-plan route --task "<task>" --files <files...> --json`.
2. **Ambiguity Gate:** Run `agent-qa super-plan ambiguity-check --task "<task>" --json` and resolve architectural forks before drafting.
3. **Execution DAG & Typed Manifests:** Generate `implementation_plan.md` with `<= 3`-file atomic milestones, `depends_on`, `Write Set`, `Rollback Hook`, and `Pass Gate`. Default execution mode is Single-Agent sequential `/solo` (no `swarm` workers unless `/teamwork` is explicitly requested).
4. **Mechanical Validation & 12-Mutant Red-Teaming:** Run `agent-qa lint-plan --file implementation_plan.md --mode super` and `agent-qa plan-mutate --file implementation_plan.md --threshold 90.0`.
5. **Clean Handoff:** Hand off `implementation_plan.md` to `/solo` (`agent-qa solo --from-plan implementation_plan.md`).
"""

    if wf == "review":
        return f"""{frontmatter}{HEADER_TEMPLATE}
# /review — Closed-Loop Post-Code Adversarial Reviewer (v2.0)

> **Attribution:** Synapse Hub by Thế Vị (@TeeVee98) | MIT License
> **Canonical Skill:** `.agent/skills/review/SKILL.md`
> **Unified CLI:** `agent-qa review` (or `python3 tools/orchestration/senior_code_review.py`)

## Strict Read-Only Diagnostic Boundary
- Operate strictly in read-only DIAGNOSTIC mode. Never auto-edit user source code or tests during `/review`.
- Re-verify HMAC signatures, post-Red `test_tree_hash`, AST contracts, and downstream callers directly from disk truth.

## Workflow Steps
1. **Plan-vs-Solo Closed-Loop Audit:** Reconcile diffs and `/solo` forensic receipts against the approved Super-Plan:
   `agent-qa review --plan implementation_plan.md --strict-solo --json`
2. **Milestone-Scoped Audit:** Scope reconciliation to a single milestone write set and receipt:
   `agent-qa review --plan implementation_plan.md --milestone M1 --strict --json`
3. **Ad-Hoc Diff / PR Review (6-Pillar AST + 4-Angle `simplify`):**
   `agent-qa review --staged` (or `agent-qa review --branch main --output-md reports/code_review.md --verify-cove`)
4. **Verdict & Signed Receipt:** Inspect `reports/code_review_receipt.json` (`APPROVED` / `APPROVED_WITH_NOTES` / `CHANGES_REQUESTED`) and hand any `Must fix` blockers back to `/solo`.
"""

    return f"""{frontmatter}{HEADER_TEMPLATE}
# /solo — Single-Agent 4-Pillar Verification Loop (v2.0)

> **Attribution:** Synapse Hub by Thế Vị (@TeeVee98) | MIT License
> **Canonical Skill:** `.agent/skills/solo/SKILL.md`
> **Unified CLI:** `agent-qa solo` (or `python3 tools/orchestration/solo_runner.py`)

## Strict Single-Agent Execution Boundary
- Execute milestones sequentially (`M1 -> M2 -> ...`) within one active session (`Red -> Blue -> Purple`).
- Strictly FORBIDDEN to spawn `swarm` workers or parallel subagents unless the user explicitly invokes `/teamwork`.

## Workflow Steps
1. **Pre-Execution 3-Line Contract:** State Goal, Won't Do, and Done When.
2. **Phase 1 (Red QA):** Write 4-scenario failing tests and certify:
   `agent-qa solo --red --milestone M1 --require-four-scenarios --test-cmd "python3 -m pytest tests/<target>.py"`
   (Use `--recertify-red` when updating Red tests with cryptographic lineage.)
3. **Phase 2 (Blue Dev):** Implement minimal complete code without weakening Red assertions and certify:
   `agent-qa solo --green --milestone M1 --test-cmd "python3 -m pytest tests/<target>.py"`
4. **Phase 3 (Purple Auditor):** Run live mutation (`>= 80%`) and Purple audit (standalone `--purple` auto-runs `/review --strict-solo`; pass `--milestone <ID>` for milestone receipts or `--no-review` to opt out):
   `agent-qa solo --mutation --target <source.py> --test-cmd "python3 -m pytest tests/<target>.py" --threshold 80.0`
   `agent-qa solo --purple --json`
5. **Closed-Loop Plan Execution & Auto-`/review`:** Execute validated plan DAGs end-to-end with Scope Guard, `decisions.tsv`, and automatic post-`/solo` `/review` reconciliation (`--no-review` to opt out):
   `agent-qa solo --from-plan implementation_plan.md --json`
6. **Phase 4 (Automatic `/review` Handoff):** After standalone `/solo` finishes Phase 3, `solo_runner.py --purple` automatically runs `/review --strict-solo` (pass `--milestone <ID>` for milestone receipts, or `--no-review` at CLI to opt out); when invoking `/review` directly in standalone mode, run `agent-qa review --plan <plan.md> --strict-solo --json` or `agent-qa review --staged --strict-solo --json` (add `--milestone <ID>` if using milestone receipts) before reporting done.
"""


def _gen_claude_cmd_super_plan(): return generate_slash_workflow_markdown("super-plan", ide="claude")
def _gen_claude_cmd_solo(): return generate_slash_workflow_markdown("solo", ide="claude")
def _gen_claude_cmd_review(): return generate_slash_workflow_markdown("review", ide="claude")
def _gen_windsurf_wf_super_plan(): return generate_slash_workflow_markdown("super-plan", ide="windsurf")
def _gen_windsurf_wf_solo(): return generate_slash_workflow_markdown("solo", ide="windsurf")
def _gen_windsurf_wf_review(): return generate_slash_workflow_markdown("review", ide="windsurf")


SLASH_WORKFLOW_GENERATORS = [
    (".claude/commands/super-plan.md", _gen_claude_cmd_super_plan),
    (".claude/commands/solo.md", _gen_claude_cmd_solo),
    (".claude/commands/review.md", _gen_claude_cmd_review),
    (".windsurf/workflows/super-plan.md", _gen_windsurf_wf_super_plan),
    (".windsurf/workflows/solo.md", _gen_windsurf_wf_solo),
    (".windsurf/workflows/review.md", _gen_windsurf_wf_review),
]


def sync_slash_workflows(repo_root: str = REPO_ROOT, check_only: bool = False) -> bool:
    """Synchronizes /super-plan, /solo, and /review slash workflows for Claude Code and Windsurf."""
    drift = False
    for rel_path, gen_fn in SLASH_WORKFLOW_GENERATORS:
        full_path = os.path.join(repo_root, rel_path)
        content = gen_fn().strip() + "\n"
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as fh:
                if fh.read() == content:
                    continue
            drift = True
            if check_only:
                print(f"[DRIFT DETECTED] {rel_path} is out of sync with AGENTS.md.")
                continue
        else:
            drift = True
            if check_only:
                print(f"[MISSING FILE] {rel_path} does not exist.")
                continue
        if not check_only:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as fh:
                fh.write(content)
            print(f"[SYNCED] {rel_path} updated from AGENTS.md.")
    return drift


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
    ".cursor/rules/security.mdc",
]

BANNED_MDC_WAIT_RE = re.compile(
    r"waitForLoadState\(\s*['\"]networkidle['\"]\s*\)|waitForTimeout\s*\(",
    re.IGNORECASE,
)
NEGATION_HINT_RE = re.compile(
    r"\b(?:avoid|never|forbid|prohibit|ban|zero|anti-pattern|do\s+not)\b",
    re.IGNORECASE,
)


def sync_project_state(repo_root: str = REPO_ROOT) -> None:
    """Synchronizes AGENTS.md invariant metrics and KV-cache baseline into project_state.json."""
    import json
    from datetime import datetime, timezone
    from tools.core.cache_prefix_enforcer import CachePrefixEnforcer
    from tools.core.kv_cache_sentinel import evaluate_cache_hit_rate, load_telemetry_config

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
        telemetry_cfg = load_telemetry_config(repo_root)
        kv_min_pct = float((telemetry_cfg or {}).get("min_kv_cache_hit_rate_pct", 85.0))
        cached_tokens = partition["prefix_tokens"] if partition.get("is_cache_eligible") else 0
        kv_audit = evaluate_cache_hit_rate(
            input_tokens=total_tokens,
            cached_tokens=cached_tokens,
            min_pct=kv_min_pct,
            provider="synapse-rules",
            model="agents-md",
        )

        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)

        state["last_sync"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        if "quality_verification" not in state:
            state["quality_verification"] = {}
        state["quality_verification"]["universal_invariants_count"] = 17
        state["quality_verification"]["rule_prefix_tokens"] = partition["prefix_tokens"]
        state["quality_verification"]["rule_total_tokens"] = total_tokens
        state["quality_verification"]["rule_prefix_hash"] = partition["prefix_hash"]
        state["quality_verification"]["kv_cache_min_pct"] = kv_min_pct
        state["quality_verification"]["kv_cache_baseline_pct"] = kv_audit.cache_hit_rate_pct
        state["quality_verification"]["kv_cache_baseline_passed"] = kv_audit.passed

        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
            f.write("\n")
    except Exception as e:
        sys.stderr.write(f"[WARN] Failed to sync project_state.json: {e}\n")


def assemble_cached_rule_payload(
    repo_root: str = REPO_ROOT,
    dynamic_suffix: str = "",
    provider: str = "gemini",
) -> Dict[str, Any]:
    """Assembles a KV-cache-optimized rule prompt payload via ContextCachingProxy."""
    from tools.core.cache_proxy import ContextCachingProxy

    rule_text = ""
    for candidate in ("AGENTS.md", "CLAUDE.md"):
        candidate_path = os.path.join(repo_root, candidate)
        if os.path.isfile(candidate_path):
            with open(candidate_path, "r", encoding="utf-8") as f:
                rule_text = f.read()
            break

    if dynamic_suffix:
        boundary_marker = "<!-- DYNAMIC_PROMPT_BOUNDARY -->"
        anchor = "## 1.1 PRE-FLIGHT REASONING CHECKLIST"
        has_anchor_split = anchor in rule_text and "\n---\n" in rule_text[rule_text.find(anchor):]
        stripped_rule = rule_text.rstrip()
        if boundary_marker in rule_text or has_anchor_split:
            prompt_text = f"{stripped_rule}\n{dynamic_suffix}" if stripped_rule else dynamic_suffix
        else:
            prompt_text = (
                f"{stripped_rule}\n{boundary_marker}\n{dynamic_suffix}"
                if stripped_rule
                else f"{boundary_marker}\n{dynamic_suffix}"
            )
    else:
        prompt_text = rule_text

    return ContextCachingProxy.assemble_prompt_payload(
        prompt_text=prompt_text,
        provider=provider,
        repo_root=repo_root,
    )


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
        with open(full_prot_path, "r", encoding="utf-8") as pf:
            for lno, pline in enumerate(pf, 1):
                if BANNED_MDC_WAIT_RE.search(pline) and not NEGATION_HINT_RE.search(pline):
                    if check_only:
                        print(f"[DRIFT DETECTED] {protected}:{lno} contains banned wait anti-pattern contradicting AGENTS.md.")
                        drift_detected = True
                    else:
                        raise RuntimeError(f"CRITICAL: Protected rule '{protected}:{lno}' contradicts AGENTS.md Invariant 3!")

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
        sync_slash_workflows(repo_root=REPO_ROOT, check_only=False)
        sync_project_state(REPO_ROOT)

    if check_only:
        if os.path.isfile(os.path.join(REPO_ROOT, ".agent", "skills", "review", "SKILL.md")):
            if sync_slash_workflows(repo_root=REPO_ROOT, check_only=True):
                drift_detected = True
        agents_path = os.path.join(REPO_ROOT, "AGENTS.md")
        from tools.lint.lint_cache_prefix import run_prefix_lint

        prefix_ok, prefix_issues = run_prefix_lint(agents_path)
        if not prefix_ok:
            for issue in prefix_issues:
                print(f"[PREFIX LINT FAIL] AGENTS.md: {issue}")
            drift_detected = True

        if drift_detected:
            print("\n❌ Rule drift or prefix budget violation detected. Run 'python3 tools/core/sync_agent_rules.py' to synchronize.")
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
    parser.add_argument(
        "--profile",
        choices=["starter", "standard", "enterprise"],
        default=None,
        help="Generate a profile-scoped client AI bridge (starter=<35 lines zero-ceremony)",
    )
    parser.add_argument("--out", default=None, help="Optional destination path when used with --profile")
    parser.add_argument("--json", action="store_true", help="Emit JSON output when used with --profile")
    args = parser.parse_args()

    if args.profile:
        dto = generate_client_bridge_markdown(profile=args.profile)
        if args.out:
            out_dir = os.path.dirname(os.path.abspath(args.out))
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(dto.content)
        if args.json:
            print(
                json.dumps(
                    {
                        "profile": dto.profile,
                        "bridge_line_count": dto.bridge_line_count,
                        "hub_paths_leaked": dto.hub_paths_leaked,
                        "mutation_required": dto.mutation_required,
                        "passed": dto.passed,
                        "content": dto.content,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            print(dto.content, end="")
        return 0 if dto.passed else 1

    return sync_all(check_only=args.check)


if __name__ == "__main__":
    sys.exit(main())
