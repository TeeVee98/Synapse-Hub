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
  All 11 Quality Gates must return `PASS`. If any gate fails, the task is NOT complete.
- **Targeted Re-Test:** Check impacted test cases via `python3 tools/test_impact.py --git-diff`.
- **Sync Knowledge & Artifacts:** Run `python3 tools/repo_map.py` if Page Classes or helpers change; run `graphify update .` if `graphify-out/` exists.

## 3. Situational Tool Autonomy (Zero-Command Invariant)
Autonomously trigger tools on-demand per `AGENTS.md` Section 3.4 (Setup: `setup_project.py`/`analyze_project.py`; Quality: `verify_all.py`/`infer_linter.py`/`micro_mutator.py`; Healing: `pinpoint_failure.py`/`auto_heal_reflexion.py`/`reversible_sandbox.py`; Context: `distill_log.py`/`safety_firewall.py`). Never expect user to memorize CLI syntax.

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
