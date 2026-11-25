---
name: lean-code-ladder
description: "Apply a 7-rung reuse-first ladder so every new test-automation code path is the smallest complete change that fully solves the task. Use when adding helpers, Page Class methods, dependencies, or any new code where a shorter existing option might already exist."
category: architecture_and_analysis
version: "1.0.0"
policies:
  network: none
  shell: workspace-sandbox
  filesystem: read-only
---
# Lean Code Ladder — Enterprise Reuse-First Standard

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Apply a 7-rung reuse-first ladder so every new test-automation code path is the smallest complete change that fully solves the task. Use when adding helpers, Page Class methods, dependencies, or any new code where a shorter existing option might already exist.
- **Activation Scope:** Domain workflows for `08-code-quality` involving `lean-code-ladder`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT add speculative wrappers, unrequested options, or 'for later' abstractions (YAGNI).
- Do NOT skip the lower rungs of the 7-rung ladder; use existing code and language stdlib first.
- Do NOT sacrifice validation, trust boundaries, error handling, or security for code brevity.
- **Sibling Skill Boundaries:**
  - surgical-coding-principles limits diff surface; lean-code-ladder dictates what minimal solution level to build.

---

## 3. Ordered Execution Workflow

Specialized skill for minimizing newly written code in test automation projects: solve the whole problem with the least new code, then finish the change completely (callers, fixtures, and the small test that proves it).

---

### The 7-Rung Ladder & Intensity Levels

### Intensity Levels

| Level | Behavior |
|:---:|---|
| **lite** | Build what was asked. Name the smaller/lazier option in one line and let the user pick. |
| **full** | The standard 7-rung ladder rules below. (Default) |
| **ultra** | Deletion before addition: question the request and push back on any part the business need does not strictly justify. |
| **off** | Deactivate lean constraints; standard code synthesis. |

### The 7-Rung Ladder

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

### Reading Order Before Writing

- Read the task and the code it touches. List every place the change must reach: callers, tests, fixtures, config, exports.
- Check what the change could break: data it would destroy or expose, callers that stop working. That is scope. Extra features are not.

### Completeness Rules (Be Lazy About the Solution, Never About the Change)

- Finish every part the task needs, including the callers, tests, and fixtures the change affects.
- No abstraction, wrapper, option, config, or "for later" code nobody asked for. Keep values in the form the platform already gives. Deletion beats addition; keep the structure the codebase already has.
- The shortest working diff wins, once everything it must touch is known. A one-liner that needs decoding is not short.
- Comment only the "why" the code cannot show, in one line.
- Bug fix: grep every caller of the touched function first, then fix the root cause once in the shared code (pair with `systematic-debugging`).
- Code that is moved or merged keeps its error handling and validation.
- Between options of equal size, take the one that is correct on edge cases.
- New non-trivial logic (a branch, loop, parser, money/security path, or a whole new script) leaves one small test or assert-based self-check before it counts as finished; trivial changes need none.
- A shortcut with a known limit gets a code comment: `shortcut: <the limit>, <when to upgrade>`.

### Never Cut (Hard Floor)

The ladder minimizes code, never safety. The following are never removed or skipped in the name of leanness:

- Validation at trust boundaries
- Error handling that prevents data loss
- Security checks (credential handling, authorization assertions)
- Accessibility behavior
- Anything the user explicitly asked for

### Evidence of Leanness

- Run `python3 tools/lint/infer_linter.py` after the change: zero fake-pass findings confirms the lean diff did not trade rigor for brevity.
- Run the affected subset from `python3 tools/core/test_impact.py --git-diff` to prove the shortest diff still reaches everything it had to reach.
- Lean code without its check is unfinished: Gate 8 (`tools/lint/micro_mutator.py`, Mutation Score >= 80%) remains the floor for any assertion logic written on this ladder.

### Worked Comparison

| Situation | Bloated answer | Lean answer |
|---|---|---|
| Need a date picker in a form test | 300-line custom calendar component | Native `<input type="date">` via the existing form helper (Rung 3) |
| Need retry around a flaky API call | New generic retry framework with policy classes | The installed HTTP client's retry option (Rung 4) + one test |
| Need a formatted timestamp in test data | New utility module | One line with the stdlib formatter (Rung 2) |

#### Concrete Code Comparison (Rung 4 vs Bloated Custom Framework)

<!-- classification: illustrative -->
```typescript
// ❌ Bloated (Anti-pattern): Custom 30-line retry wrapper with generic policy classes
class CustomRetryManager {
  async executeWithExponentialBackoff<T>(fn: () => Promise<T>, retries = 3): Promise<T> {
    for (let attempt = 1; attempt <= retries; attempt++) {
      try { return await fn(); }
      catch (err) { if (attempt === retries) throw err; }
    }
    throw new Error('Unreachable retry state');
  }
}

// ✅ Lean (Rung 4 & 5): Native framework / client retry option (One clear line)
// shortcut: fixed retry count of 2; upgrade to exponential backoff if 429 rate limits occur
const response = await page.request.get('/api/v1/health', { maxRetries: 2 });
```

### Boundary vs Sibling Skills (Do Not Confuse)

| Sibling | Owns | Hand-off |
|---|---|---|
| `surgical-coding-principles` | Diff discipline (every line traces to the request) | Canonicalized under `lean-code-ladder`; principles keep diff clean |
| `code-refactoring-refactor-clean` | Deliberate SOLID refactors of existing debt | Refactoring is not ladder work; only new/changed code descends the ladder |
| `clean-pom-crafter` | Page Class architecture and locator tiers | Ladder applies inside and around Page Classes, not to their architecture contract |

### The Four Surgical Principles (Integrated from surgical-coding-principles)

1. **Think Before Coding:** State assumptions explicitly, verify callers, and clarify ambiguity before writing edits.
2. **Simplicity First:** Avoid premature abstractions or speculative flags. The simplest working implementation is best.
3. **Surgical Changes:** Keep diffs tight and scoped. Every modified line must trace directly to the task requirement.
4. **Goal-Driven Execution:** Validate against concrete success criteria and pass quality gates before completing.

### Reference Documentation

- `python3 tools/lint/infer_linter.py` — fake-pass scan for the new logic.
- `python3 tools/core/test_impact.py --git-diff` — confirm the lean diff still covers all impacted tests.
- `python3 tools/lint/micro_mutator.py` — Gate 8 mutation floor (>= 80%) for non-trivial new logic.

### Attribution

Adapted from **ponytail** (https://github.com/DietrichGebert/ponytail) — MIT License, Copyright (c) 2026 DietrichGebert. The lazy-senior ladder, completeness rules, and never-cut floor are re-scoped for enterprise test automation in Synapse Hub; wording, structure, and examples modified.

---

## 4. Verification Points & DoD

1. Solution stops at the lowest rung of the 7-rung ladder that satisfies the requirement.
2. Zero speculative options or unused abstractions added.
3. Deliberate simplifications marked with `shortcut: <limit>, <upgrade>` comments.

---

## 5. Handoff Protocol

- **Deliverables:** Minimal complete code changes, YAGNI audit rationale, and shortcut markers ledger.
- **Next Subagent:** orchestrator
- **Output Format:** 7-rung reuse evaluation notes and minimal-diff implementation patches.
