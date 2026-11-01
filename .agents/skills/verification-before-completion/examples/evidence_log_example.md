# Example: Claim/Evidence Log for a Swarm Task Closure

Task: "Fix the flaky export test and get the suite green."
Subagent: test-runner -> failure-analyst -> quality-gatekeeper (Stage 5).

## Claim 1: "The flaky root cause is fixed"

| Field | Value |
|---|---|
| Claim | Export timeout root cause fixed via condition-based job poll |
| Evidence command | `npx playwright test tests/e2e/TC-220_export.spec.ts --repeat-each=10` |
| Fresh output (this turn) | `10 passed (94.2s)` |
| Verdict | Claim SUPPORTED — quoted with the output |

## Claim 2: "The full suite is green"

| Field | Value |
|---|---|
| Claim | Project suite green after the fix |
| Evidence command | `npm test` (the project command, not one file) |
| Fresh output (this turn) | `Tests: 2 failed, 214 passed` |
| Verdict | Claim REFUTED — report states 2 failures in TC-118/TC-140 with
  distilled failure blocks (tools/distill_log.py). Work is NOT done. |

The 2 failures were pre-existing and not caused by the fix — still reported
by name. A red test scrolled past unmentioned is a report falsified by
omission.

## Claim 3 (after the second fix cycle): "Task complete, 9/9 gates"

| Field | Value |
|---|---|
| Evidence commands | `npm test` -> `Tests: 216 passed`; then
  `python3 tools/verify_all.py --mode hub` |
| Fresh output (this turn) | `Gate 0..8: PASS — 9/9 gates` and mutation score
  `0.86 (>= 0.80)` |
| Requirement checklist | Original request re-read; both requested items
  (stabilize export test; suite green) verified line by line |
| Verdict | "Task complete" claim MADE — with all evidence attached |

## Anti-pattern (rejected)

> "All good, the suite is green now, ready to merge."

No command, no output, no turn — this is a claim without evidence. Under the
Iron Law it is not verification, it is a guess wearing a checkmark.
