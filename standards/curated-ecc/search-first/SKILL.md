---
name: search-first
description: >
  Research-before-coding workflow skill: mandate a structured search phase before
  any code is authored, ensuring existing solutions, relevant tests, and architectural
  patterns are discovered before new code is synthesized. Use at the start of any
  non-trivial implementation task.
version: 1.0.0
attribution: Adapted from ECC (affaan-m/ecc, Apache 2.0). Extended by Thế Vị (@TeeVee98).
---

# Search-First Skill (`search-first`)

## Overview

The Search-First protocol enforces a **mandatory research phase** before any code synthesis begins. It prevents duplicate implementations, ensures new code integrates with existing patterns, and dramatically reduces the time spent debugging integration failures.

> [!IMPORTANT]
> The Synapse Hub 7-Rung Lean Dev Ladder (AGENTS.md §2 Rule 2) mandates:
> 1. Does the solution need to exist? (YAGNI) → 2. Is it already in the codebase?
> This skill operationalizes Rung 2: systematic codebase discovery before implementation.

## When to Activate

- Starting any implementation task estimated at > 30 minutes of coding.
- Before writing a new Page Class, test script, or tool utility.
- Before adding an external dependency (`pip install X`, `npm install X`).
- When debugging a failure that could be caused by existing code interactions.

## Search-First Protocol

```
Phase 1 — CODEBASE ARCHAEOLOGY (read-only, < 10 min)
  ↓ Search for existing implementations of the target functionality
  ↓ Identify all test files exercising the relevant area
  ↓ Locate the base classes / shared fixtures the new code should extend
  ↓ Document: "What already exists that I must not duplicate?"

Phase 2 — PATTERN ALIGNMENT (read-only, < 5 min)
  ↓ Identify the naming conventions in the target area (camelCase, snake_case)
  ↓ Identify the error handling pattern (exceptions vs. return codes vs. Result types)
  ↓ Identify the logging / reporting pattern for this module
  ↓ Document: "What patterns must my new code conform to?"

Phase 3 — DEPENDENCY CHECK (read-only, < 5 min)
  ↓ Check if the required functionality exists in Python stdlib / Node stdlib
  ↓ Check if it exists in already-installed project dependencies
  ↓ Only if NOT found in either: evaluate adding a new dependency
  ↓ Document: "Do I need a new dependency? If yes, justify."

Phase 4 — SYNTHESIS (write phase begins)
  ↓ Author code that integrates with existing patterns (Phases 1-3 findings)
  ↓ Extend existing base classes — do not reimplement from scratch
  ↓ Reuse existing test fixtures — do not create duplicate data factories
```

## Search Commands

```bash
# Find all files implementing a pattern (e.g., existing BasePage subclasses)
grep -r "class.*BasePage" Pages/ --include="*.ts" -l

# Find all tests exercising a specific method
grep -r "loginPage\." tests/ --include="*.ts" -l

# Find imports of a module across the codebase
grep -r "from tools.core.fact_forcing_gate" --include="*.py"

# Check if a dependency is already installed
python -c "import <package>" 2>/dev/null && echo "INSTALLED" || echo "NOT FOUND"

# Count existing implementations before adding a new one
grep -r "class.*Retriever" tools/ --include="*.py" | wc -l
```

## Anti-Duplication Checklist

Before writing any new class or function, answer:

- [ ] Does a function in `tools/` already do 80%+ of this?
- [ ] Is there a base class in `Pages/` I should be extending?
- [ ] Is there an existing test fixture in `tests/fixtures/` I should reuse?
- [ ] Does Python stdlib have this (`pathlib`, `hashlib`, `sqlite3`, `subprocess`)?
- [ ] Am I about to implement a custom parser for a standard format (JSON, YAML, TOML)?

If ANY box is checked → stop synthesis and reuse/extend existing code.

## Skill Trigger Keywords

This skill activates automatically when the task involves:
- `implement`, `create`, `write`, `build`, `add` (new code keywords)
- `fix`, `debug`, `investigate` (may reveal existing code interactions)
- `install`, `add dependency`, `npm install`, `pip install`

## Non-Goals

- Do not use Search-First as an excuse to delay implementation indefinitely (time-box each phase).
- Do not search for more than 20 minutes total before beginning synthesis.
- Trivial fixes (< 15 LOC, single-file typo/rename) may skip phases 1-3.
