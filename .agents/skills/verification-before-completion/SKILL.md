---
name: verification-before-completion
description: "Require fresh verification evidence — a command run in the current session with its real output — before any claim that work is complete, fixed, or passing. Use when about to report success, commit, open a PR, or close a task."
---

# Verification Before Completion — Enterprise Evidence Protocol

Specialized skill for the evidence discipline behind every success claim in the hub: no completion statement exists without fresh verification output. This is the operational form of the Truth Anchor (No Fake Pass) rule in `AGENTS.md` Section 3.

---

## 1. The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If the verification command was not run in the current message turn, the claim cannot be made. "Evidence before claims, always."

## 2. The Gate Function

Run before claiming ANY status or expressing satisfaction:

1. **IDENTIFY** — which command proves this claim?
2. **RUN** — execute the full command, fresh and complete (not a partial rerun, not a memory of an earlier run).
3. **READ** — full output, exit code, failure count.
4. **VERIFY** — does the output actually confirm the claim? If no: state the real status with the evidence. If yes: state the claim WITH the evidence.
5. **ONLY THEN** — make the claim.

Skipping any step is lying, not verifying.

## 3. Claim → Required Evidence Matrix

| Claim | Requires | Not Sufficient |
|---|---|---|
| Tests pass | Test command output in this session: 0 failures | Previous run, "should pass" |
| 11 Quality Gates pass | `python3 tools/verify_all.py --mode hub` output: 11/11 | Gates passing last week |
| No fake passes | `python3 tools/infer_linter.py` output: 0 findings | "Assertions look fine" |
| Mutation floor met | `python3 tools/micro_mutator.py` score >= 80% | Tests exist, so "they must kill mutants" |
| Bug fixed | Reproduction test passes now | Code changed, assumed fixed |
| Regression test works | Red-green cycle verified (watched fail, then pass) | Test passes once |
| Subagent finished | Its diff inspected + its claims re-verified independently | Agent reports "success" |
| Requirements met | Line-by-line checklist against the original request | Tests passing |

## 4. Red Flags — STOP

- Using "should", "probably", "seems to", "definitely works"
- Expressing satisfaction before verification ("Perfect!", "Done!")
- About to commit, push, or open a PR without verification in this turn
- Trusting a subagent's success report without independent re-verification
- Relying on a partial check (linter passed, therefore build must pass)
- Thinking "just this once"

## 5. Rationalization Prevention

| Excuse | Reality |
|---|---|
| "Should work now" | RUN the verification. |
| "I'm confident" | Confidence is not evidence. |
| "Just this once" | No exceptions — one unverifiable claim poisons the whole report. |
| "Linter passed" | The linter is not the compiler; linter does not equal build. |
| "Agent said success" | Verify independently; subagent reports are claims, not evidence. |
| "Partial check is enough" | Partial proves nothing about the whole. |
| "Different words, so the rule doesn't apply" | Spirit over letter — paraphrases and implications of success are covered. |

## 6. Key Patterns

**Tests:** run command, quote `N/N pass`, then claim "all tests pass". Never "looks correct".

**Regression (TDD red-green):** write test, run (MUST FAIL), apply fix, run (passes), quote both runs. A regression test without a watched failure is unproven.

**Quality gates:** `python3 tools/verify_all.py --mode hub` fresh output with the 11/11 line quoted — required before any "task done" statement in swarm Stage 5.

**Subagent delegation:** agent reports success, orchestrator inspects the diff and re-runs the decisive command before relaying any success upward.

**Requirements:** re-read the original request, build the checklist, verify each item, report gaps or completion — "tests pass, phase complete" without the checklist is insufficient.

## 7. When To Apply

Always before: ANY success or completion claim, ANY positive statement about work state, committing or PR creation, task closure, moving to the next task, delegating to subagents.

Applies to exact phrases, paraphrases, synonyms, and any communication implying completion or correctness.

## 8. Boundary vs Sibling Skills (Do Not Confuse)

| Sibling | Owns | Hand-off |
|---|---|---|
| `antigravity-test-sentinel` | Hard completion blocking until tests and gates pass | The sentinel is the enforcement gate; this skill is the evidence protocol the agent follows to pass it honestly |
| `test-driven-development` | RED-GREEN-REFACTOR cycle | GREEN verification output feeds the evidence quoted here |
| `systematic-debugging` | Root-cause investigation | Phase 4 fix verification uses this protocol for its "fixed" claim |

## 9. Reference Documentation

- `python3 tools/verify_all.py --mode hub` — the 9-gate acceptance command for hub work.
- `python3 tools/infer_linter.py` — fake-pass scan required before any "tests are honest" claim.
- [Evidence log example (`evidence_log_example.md`)](examples/evidence_log_example.md): claim/evidence pairing for a swarm task closure.

## 10. Attribution

Adapted from **superpowers** skill `verification-before-completion` (https://github.com/obra/superpowers) — MIT License, Copyright (c) 2025 Jesse Vincent. The Iron Law, gate function, claim-evidence matrix, and rationalization table are re-scoped for enterprise QA automation in Synapse Hub; wording, structure, and hub tooling modified.
