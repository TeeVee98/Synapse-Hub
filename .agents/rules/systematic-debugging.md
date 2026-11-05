---
trigger: always_on
description: Enforce rigorous engineering discipline, systematic debugging without guesswork, and verification before completion.
---

# Systematic Debugging & Verification Discipline

## 1. Zero Guesswork Debugging
- **Evidence Before Action:** Never modify code on assumption. Ground every fix in concrete evidence: failing line & stack trace, screenshot (`Screenshots/FAILED_*.png`), or live DOM state.
- **Surgical Code Preservation:** Touch only the minimal lines required. Never rewrite working methods speculatively.

## 2. Verification-First & Definition of Done
- **Mandatory Verification Gate:** Any claim that a task, fix, or refactoring is complete MUST be verified by running:
  ```bash
  python3 tools/verify_all.py
  ```
  All 10 Quality Gates must return `PASS`. If any gate fails, the task is NOT complete.
- **Targeted Re-Test:** Check impacted test cases via `python3 tools/test_impact.py --git-diff`.
- **Sync Knowledge & Artifacts:** Run `python3 tools/repo_map.py` if Page Classes or helpers change; run `graphify update .` if `graphify-out/` exists.

## 3. Situational Tool Autonomy (Zero-Command Invariant)
Autonomously recognize context and trigger tools on-demand (user never needs to type tool commands):
- **Setup / Audit:** `tools/setup_project.py` (new project); `tools/analyze_project.py` (project audit); `tools/senior_code_review.py` (review diff); `tools/debt_harvester.py` (scan shortcuts).
- **Quality & Gates:** `tools/verify_all.py` (10 Gates DoD); `tools/infer_linter.py` (AST defect & swallowed exception check); `tools/micro_mutator.py --min-score 80` (mutation testing).
- **Failure & Healing:** `tools/pinpoint_failure.py` (0.1s JUnit XML autopsy); `tools/auto_heal_reflexion.py` (Reflexion K=3); `tools/reversible_sandbox.py` (transactional rollback).
- **Context & Safety:** `tools/distill_log.py` (log distillation); `tools/safety_firewall.py` (destructive action guard); `tools/cache_resolver.py` (error memory lookup).

## 4. Cognitive Forcing Functions (System-2 Reasoning)
Before outputting any test script, Universal IR, or Page Class, pass through:
```markdown
<reasoning_protocol>
Step 1 - Boundary & Invariant Extraction: Define system invariants (what must NEVER happen).
Step 2 - Falsification Hypotheses: Propose 3 realistic scenarios where code breaks while tests pass (False Negatives).
Step 3 - Self-Debate: Explain why proposed assertions catch all 3 destructive scenarios.
Step 4 - Emit Code / Universal IR.
</reasoning_protocol>
```

## 5. Adversarial Mutation Threshold
Tests must achieve Mutation Kill Score $\ge 80\%$ via `tools/micro_mutator.py` before approval.
