---
trigger: on_demand
description: Canonical agent-neutral Manual QA, RBT Test Case Design, RTM Traceability, and QUICK-Mode Exit Criteria (ISO/IEC/IEEE 29119-3).
profiles: [manual-qa, enterprise-rbt, full]
---

# Manual QA & RBT Test Design Invariants (ISO/IEC/IEEE 29119-3)

> **Scope:** Universal agent-neutral rule governing Manual QA specification design, Requirement Traceability Matrix (RTM) linkage, and release exit criteria across Antigravity, Claude Code, Cursor, GitHub Copilot, and Windsurf.
> **Enforcement Sensor:** `python tools/lint/manual_tc_linter.py <file> [--profile <profile>] [--strict-semantic]`

---

## 1. Canonical Table Schema & Mandatory RTM Linkage
1. **ISO/IEC/IEEE 29119-3 12/13-Column Contract:** Every manual test case table MUST adhere to the canonical 12-column schema (`TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags`) or the explicit 13-column RTM variant inserting `REQ ID` immediately after `TC ID`.
2. **100% Requirement Traceability (`@REQ-xxx` / `REQ ID`):** Every test case row MUST link back to an explicit requirement identifier either via a populated `REQ ID` column or via `@REQ-<id>` inside `Tags`. Orphan test cases without requirement linkage fail strict RTM audits.
3. **Automation Rule Isolation:** Automation-only code invariants (`Clean POM Flat Architecture`, `Smart Waits Only`, Page Class selector checks) do NOT apply to Manual QA Markdown specifications.

---

## 2. Deterministic Oracles & Hard Ambiguity Checkpoints
1. **Zero Speculative Oracles:** Expected Results and Test Steps MUST be single-valued, observable, and deterministic. Hedging or branching phrases (`"OR"` for unverified behavior, `"if applicable"`, `"works properly"`, `"as expected"`, `"valid data"`) are strictly prohibited.
2. **Ambiguity & Assumptions Log:** Every manual test suite document MUST include a non-empty `## Ambiguity & Assumptions Log` section recording requirement gaps and explicit working assumptions.
3. **Hard Stop on Contradictions:** When core business rules or acceptance criteria conflict, halt at Stage 2 (Ambiguity Q&A Register) and request stakeholder clarification rather than inventing requirements.

---

## 3. QUICK-Mode & FULL-Mode Coverage Exit Criteria
1. **QUICK-Mode Minimum Coverage Gate (`check_quick_exit_criteria`):** Even in rapid single-screen QUICK mode, a test suite is incomplete unless it contains ALL 4 baseline pillars:
   - At least **1 Happy Path** scenario verifying nominal acceptance criteria.
   - At least **1 Negative Path** scenario verifying deterministic rejection (HTTP `4xx` / inline validation error).
   - At least **1 Boundary / Edge** scenario (`Min-1`, `Min`, `Max`, `Max+1`, or empty/whitespace trim).
   - **100% RTM Tagging** (`@REQ-xxx` or `REQ ID`) across authored test cases.
2. **FULL RBT Golden Ratio:** Enterprise modules target context-aware risk distributions (`40% Happy / 40% Negative / 20% Security & Resilience` default; `25% / 45% / 30%` for `auth-payment`).

---

## 4. Mandatory Empirical Edge Cases
1. **Text Input Whitespace & Trim Hygiene:**
   - Reject whitespace-only strings (`"   "`) on required fields.
   - Verify leading/trailing `trim()` behavior against `minlength`/`maxlength` boundaries and database persistence.
   - Handle consecutive internal spaces and non-breaking spaces (`\u00A0`) on paste.
2. **Financial & State-Mutating Transaction Resilience:**
   - **Double-Submit Guard:** Rapid double-click under Slow 3G latency immediately disables the submit trigger, attaches `Idempotency-Key`, and prevents duplicate charges.
   - **Browser Interrupts:** Pressing Browser Back, Refresh (`F5`), or closing the tab during payment gateway redirect preserves safe `Pending` reconciliation state without duplicate debits.
   - **Session TTL Expiration:** Submitting an expired checkout/OTP session fails gracefully with deterministic re-authentication guidance.
