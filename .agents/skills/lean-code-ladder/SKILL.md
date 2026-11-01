---
name: lean-code-ladder
description: "Apply a 7-rung reuse-first ladder so every new test-automation code path is the smallest complete change that fully solves the task. Use when adding helpers, Page Class methods, dependencies, or any new code where a shorter existing option might already exist."
---

# Lean Code Ladder — Enterprise Reuse-First Standard

Specialized skill for minimizing newly written code in test automation projects: solve the whole problem with the least new code, then finish the change completely (callers, fixtures, and the small test that proves it).

---

## 1. The 7-Rung Ladder

Before writing any new code, descend the ladder and take the **first rung that fully works**:

| Rung | Question | Action |
|:---:|---|---|
| 0 | Does it need to exist? | Skip features, options, and flexibility nobody asked for; name what you skipped in one line. A vague request gets the smallest version that does the core job. |
| 1 | Already in the codebase? | A helper, Page Class method, or fixture exists? Use it the way the surrounding code does. |
| 2 | Standard library? | Use the language stdlib unless the project has its own equivalent. |
| 3 | Platform / framework native? | A built-in of the test framework beats a hand-rolled widget (e.g. Playwright auto-waiting, `expect` web-first assertions). |
| 4 | Installed dependency? | Use it. Never add a new dependency for a few lines. |
| 5 | One line? | Can it be one line a reader gets at a glance? Then one line. |
| 6 | Minimum new code | Write the minimum that works, and no more. |

## 2. Reading Order Before Writing

- Read the task and the code it touches. List every place the change must reach: callers, tests, fixtures, config, exports.
- Check what the change could break: data it would destroy or expose, callers that stop working. That is scope. Extra features are not.

## 3. Completeness Rules (Be Lazy About the Solution, Never About the Change)

- Finish every part the task needs, including the callers, tests, and fixtures the change affects.
- No abstraction, wrapper, option, config, or "for later" code nobody asked for. Keep values in the form the platform already gives. Deletion beats addition; keep the structure the codebase already has.
- The shortest working diff wins, once everything it must touch is known. A one-liner that needs decoding is not short.
- Comment only the "why" the code cannot show, in one line.
- Bug fix: grep every caller of the touched function first, then fix the root cause once in the shared code (pair with `systematic-debugging`).
- Code that is moved or merged keeps its error handling and validation.
- Between options of equal size, take the one that is correct on edge cases.
- New non-trivial logic (a branch, loop, parser, money/security path, or a whole new script) leaves one small test or assert-based self-check before it counts as finished; trivial changes need none.
- A shortcut with a known limit gets a code comment: `shortcut: <the limit>, <when to upgrade>`.

## 4. Never Cut (Hard Floor)

The ladder minimizes code, never safety. The following are never removed or skipped in the name of leanness:

- Validation at trust boundaries
- Error handling that prevents data loss
- Security checks (credential handling, authorization assertions)
- Accessibility behavior
- Anything the user explicitly asked for

## 5. Evidence of Leanness

- Run `python3 tools/infer_linter.py` after the change: zero fake-pass findings confirms the lean diff did not trade rigor for brevity.
- Run the affected subset from `python3 tools/test_impact.py --git-diff` to prove the shortest diff still reaches everything it had to reach.
- Lean code without its check is unfinished: Gate 8 (`tools/micro_mutator.py`, Mutation Score >= 80%) remains the floor for any assertion logic written on this ladder.

## 6. Worked Comparison

| Situation | Bloated answer | Lean answer |
|---|---|---|
| Need a date picker in a form test | 300-line custom calendar component | Native `<input type="date">` via the existing form helper (Rung 3) |
| Need retry around a flaky API call | New generic retry framework with policy classes | The installed HTTP client's retry option (Rung 4) + one test |
| Need a formatted timestamp in test data | New utility module | One line with the stdlib formatter (Rung 2) |

## 7. Boundary vs Sibling Skills (Do Not Confuse)

| Sibling | Owns | Hand-off |
|---|---|---|
| `surgical-coding-principles` | Diff discipline (every line traces to the request) | The ladder chooses the solution shape; surgical principles keep the diff clean |
| `code-refactoring-refactor-clean` | Deliberate SOLID refactors of existing debt | Refactoring is not ladder work; only new/changed code descends the ladder |
| `clean-pom-crafter` | Page Class architecture and locator tiers | Ladder applies inside and around Page Classes, not to their architecture contract |

## 8. Reference Documentation

- `python3 tools/infer_linter.py` — fake-pass scan for the new logic.
- `python3 tools/test_impact.py --git-diff` — confirm the lean diff still covers all impacted tests.
- `python3 tools/micro_mutator.py` — Gate 8 mutation floor (>= 80%) for non-trivial new logic.

## 9. Attribution

Adapted from **ponytail** (https://github.com/DietrichGebert/ponytail) — MIT License, Copyright (c) 2026 DietrichGebert. The lazy-senior ladder, completeness rules, and never-cut floor are re-scoped for enterprise test automation in Synapse Hub; wording, structure, and examples modified.
