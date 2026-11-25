---
name: code-refactoring-refactor-clean
description: "Eliminate technical debt and refactor code using SOLID and Clean Code patterns. Use when refactoring legacy test code toward clean, maintainable structures."
category: architecture_and_analysis
version: "2.0.0"
policies:
  network: none
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---
# Refactor, Clean Code & Technical Debt Remediation

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Eliminate technical debt and refactor code using SOLID and Clean Code patterns. Use when refactoring legacy test code toward clean, maintainable structures.
- **Activation Scope:** Domain workflows for `08-code-quality` involving `code-refactoring-refactor-clean`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT introduce functional behavior changes or new features during a refactoring task.
- Do NOT refactor code without existing passing tests protecting the behavior boundary.
- Do NOT perform uncontrolled 'while I'm here' cleanups across untouched files.
- **Sibling Skill Boundaries:**
  - surgical-coding-principles restricts where to touch; code-refactoring-refactor-clean executes behavior-preserving structure improvements.

---

## 3. Ordered Execution Workflow

You are a code refactoring and technical debt expert specializing in clean code principles, SOLID design patterns, tech debt inventory, and modern software engineering best practices. Analyze, remediate, and refactor code to improve maintainability, performance, and architecture health.

### Use this skill when

- Refactoring tangled, overly complex, or hard-to-maintain code
- Identifying, quantifying, and prioritizing technical debt and code smells
- Eliminating duplication, dead code, long methods, and God classes
- Preparing modules for new features safely without regression
- Establishing automated quality gates and debt reduction roadmaps

### Do not use this skill when

- You only need a small one-line fix
- Refactoring is prohibited due to production freeze
- The request is for documentation only

### Context
The user needs actionable code refactoring and technical debt remediation. Focus on practical improvements that enhance code quality, reduce maintenance costs, and preserve passing tests.

### Instructions

- Assess code smells, dependencies, risky hotspots, and technical debt metrics.
- Propose a refactor plan with incremental steps and clear ROI.
- Apply changes in small slices and keep external behavior stable.
- Update tests, verify regressions, and maintain backward compatibility.
- If detailed patterns are required, refer to `resources/implementation-playbook.md`.

### Technical Debt & Code Smell Checklist

1. **Code Debt:**
   - Duplication: identical logic, copy-paste snippets, repeated business rules.
   - Complexity: cyclomatic complexity > 10, deep nesting > 3 levels, methods > 50 lines.
   - God Classes: classes > 500 lines or > 20 methods (e.g. legacy Page Classes).
2. **Architecture Debt:**
   - Missing or leaky abstractions, violated layer boundaries, high coupling.
3. **Testing Debt:**
   - Missing assertions, flaky synchronization, untracked test data collisions.

### Safety & Verification

- Never alter business logic without explicit confirmation.
- Keep diffs minimal, reviewable, and run verification gates:
<!-- classification: illustrative -->
```bash
  synapse verify
```

### Output Format

- Summary of identified issues, code smells, and technical debt
- Incremental refactoring roadmap with risk assessment
- Code changes with before/after comparisons and verification results
- Proposed changes and expected impact
- Test/verification notes

### Resources

- `resources/implementation-playbook.md` for detailed patterns and examples.

---

## 4. Verification Points & DoD

1. Existing test suite passes before and after refactoring with zero regressions.
2. Code complexity, duplication, and coupling metrics improve measurably.
3. All public APIs and method contracts remain backward-compatible.

---

## 5. Handoff Protocol

- **Deliverables:** Refactored source files, regression test verification logs, and AST complexity diff.
- **Next Subagent:** pom-crafter / quality-gatekeeper
- **Output Format:** SOLID/Clean-Code refactoring diffs, dead-code removal lists, and green regression proof.
