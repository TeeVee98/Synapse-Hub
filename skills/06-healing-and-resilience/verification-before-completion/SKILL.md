---
name: verification-before-completion
description: "Require fresh verification evidence — a command run in the current session with its real output — before any claim that work is complete, fixed, or passing. Use when about to report success, commit, open a PR, or close a task."
category: verification_and_resilience
version: "1.0.0"
policies:
  network: none
  shell: read-only
  filesystem: read-only
---
# Verification Before Completion — Enterprise Evidence Protocol

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Require fresh verification evidence — a command run in the current session with its real output — before any claim that work is complete, fixed, or passing. Use when about to report success, commit, open a PR, or close a task.
- **Activation Scope:** Domain workflows for `06-healing-and-resilience` involving `verification-before-completion`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT declare any task complete without running fresh verification commands.
- Do NOT accept claims of correctness without terminal execution output and exit code 0.
- Do NOT relax assertions or disable test cases to achieve passing status.
- **Sibling Skill Boundaries:**
  - antigravity-test-sentinel enforces gate locks; verification-before-completion establishes the evidence-based Claim -> Evidence verification matrix.

---

## 3. Ordered Execution Workflow

Specialized skill for the evidence discipline behind every success claim in the hub: no completion statement exists without fresh verification output. This is the operational form of the Truth Anchor (No Fake Pass) rule in `AGENTS.md` Section 3.

---

### The Iron Law

<!-- classification: illustrative -->
```text
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If the verification command was not run in the current message turn, the claim cannot be made. "Evidence before claims, always."

### The Gate Function

Run before claiming ANY status or expressing satisfaction:

1. **IDENTIFY** — which command proves this claim?
2. **RUN** — execute the full command, fresh and complete (not a partial rerun, not a memory of an earlier run).
3. **READ** — full output, exit code, failure count.
4. **VERIFY** — does the output actually confirm the claim? If no: state the real status with the evidence. If yes: state the claim WITH the evidence.
5. **ONLY THEN** — make the claim.

Skipping any step is lying, not verifying.

### Claim → Required Evidence Matrix

| Claim | Requires | Not Sufficient |
|---|---|---|
| Tests pass | Test command output in this session: 0 failures | Previous run, "should pass" |
| 10 Quality Gates pass | `python3 tools/core/verify_all.py --mode hub` output: 10/10 | Gates passing last week |
| No fake passes | `python3 tools/lint/infer_linter.py` output: 0 findings | "Assertions look fine" |
| Mutation floor met | `python3 tools/lint/micro_mutator.py` score >= 80% | Tests exist, so "they must kill mutants" |
| Bug fixed | Reproduction test passes now | Code changed, assumed fixed |
| Regression test works | Red-green cycle verified (watched fail, then pass) | Test passes once |
| Subagent finished | Its diff inspected + its claims re-verified independently | Agent reports "success" |
| Requirements met | Line-by-line checklist against the original request | Tests passing |

### Red Flags — STOP

- Using "should", "probably", "seems to", "definitely works"
- Expressing satisfaction before verification ("Perfect!", "Done!")
- About to commit, push, or open a PR without verification in this turn
- Trusting a subagent's success report without independent re-verification
- Relying on a partial check (linter passed, therefore build must pass)
- Thinking "just this once"

### Rationalization Prevention

| Excuse | Reality |
|---|---|
| "Should work now" | RUN the verification. |
| "I'm confident" | Confidence is not evidence. |
| "Just this once" | No exceptions — one unverifiable claim poisons the whole report. |
| "Linter passed" | The linter is not the compiler; linter does not equal build. |
| "Agent said success" | Verify independently; subagent reports are claims, not evidence. |
| "Partial check is enough" | Partial proves nothing about the whole. |
| "Different words, so the rule doesn't apply" | Spirit over letter — paraphrases and implications of success are covered. |

### Key Patterns

**Tests:** run command, quote `N/N pass`, then claim "all tests pass". Never "looks correct".

**Regression (TDD red-green):** write test, run (MUST FAIL), apply fix, run (passes), quote both runs. A regression test without a watched failure is unproven.

**Quality gates:** `python3 tools/core/verify_all.py --mode hub` fresh output with the 10/10 line quoted — required before any "task done" statement in swarm Stage 5.

**Subagent delegation:** agent reports success, orchestrator inspects the diff and re-runs the decisive command before relaying any success upward.

**Requirements:** re-read the original request, build the checklist, verify each item, report gaps or completion — "tests pass, phase complete" without the checklist is insufficient.

### When To Apply

Always before: ANY success or completion claim, ANY positive statement about work state, committing or PR creation, task closure, moving to the next task, delegating to subagents.

Applies to exact phrases, paraphrases, synonyms, and any communication implying completion or correctness.

### Boundary vs Sibling Skills (Do Not Confuse)

| Sibling | Owns | Hand-off |
|---|---|---|
| `antigravity-test-sentinel` | Hard completion blocking until tests and gates pass | The sentinel is the enforcement gate; this skill is the evidence protocol the agent follows to pass it honestly |
| `test-driven-development` | RED-GREEN-REFACTOR cycle | GREEN verification output feeds the evidence quoted here |
| `systematic-debugging` | Root-cause investigation | Phase 4 fix verification uses this protocol for its "fixed" claim |

### Reference Documentation

- `python3 tools/core/verify_all.py --mode hub` — the 10-gate acceptance command for hub work.
- `python3 tools/lint/infer_linter.py` — fake-pass scan required before any "tests are honest" claim.
- [Evidence log example (`evidence_log_example.md`)](examples/evidence_log_example.md): claim/evidence pairing for a swarm task closure.

### Attribution

Adapted from **superpowers** skill `verification-before-completion` (https://github.com/obra/superpowers) — MIT License, Copyright (c) 2025 Jesse Vincent. The Iron Law, gate function, claim-evidence matrix, and rationalization table are re-scoped for enterprise QA automation in Synapse Hub; wording, structure, and hub tooling modified.

---

## 4. Verification Points & DoD

1. Fresh execution evidence collected for every code modification.
2. Test runners execute to completion with 0 failures.
3. Working tree verified clean of unintended side-effects or temporary files.

---

## 5. Handoff Protocol

- **Deliverables:** Verification command output logs, evidence matrix, and Definition of Done sign-off.
- **Next Subagent:** quality-gatekeeper
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
