#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Unit Tests for tools/lint/plan_schema_sentinel.py (Spec-Driven Planning Sentinel)
--------------------------------------------------------------------------------
Validates:
  1. Complete compliant plan passes 100%.
  2. Missing any of the 4 mandatory sections fails.
  3. Milestone exceeding 3-file budget fails.
  4. Vague generic phrases in verification matrix fail.
  5. Built-in plan template satisfies all checks.
"""

import unittest
from tools.lint.plan_schema_sentinel import validate_plan_content, lint_plan_file


class TestPlanSchemaSentinel(unittest.TestCase):

    def test_compliant_plan_passes(self):
        plan_text = """
# Plan: Feature X
## 1. Affected Files & Blast Radius
- `src/core.py`
- `tests/test_core.py`

## 2. Data Flow & Interface Signatures
```python
def process(x: int) -> bool: ...
```

## 3. Atomic Milestones
### Milestone 1: Core Logic
- Edit `src/core.py` and `tests/test_core.py`
Pass: `pytest tests/test_core.py`

## 4. Verification Matrix
| Input | Expected | Command |
|---|---|---|
| `x=1` | `True` | `pytest tests/test_core.py` |
"""
        passed, issues, details = validate_plan_content(plan_text, "test_plan.md")
        self.assertTrue(passed, f"Expected pass but got issues: {issues}")
        self.assertEqual(len(issues), 0)

    def test_missing_mandatory_sections_fails(self):
        incomplete_plan = """
# Plan: Incomplete
## 1. Affected Files
- `src/core.py`
"""
        passed, issues, _ = validate_plan_content(incomplete_plan, "incomplete.md")
        self.assertFalse(passed)
        self.assertTrue(any("data_flow" in issue for issue in issues))
        self.assertTrue(any("atomic_milestones" in issue for issue in issues))
        self.assertTrue(any("verification_matrix" in issue for issue in issues))

    def test_milestone_budget_exceeded_fails(self):
        bloated_milestone = """
# Plan: Bloated
## 1. Affected Files
- Files listed

## 2. Data Flow & Interface Signatures
Types here

## 3. Atomic Milestones
### Milestone 1: Giant Refactor
Modifies `src/a.py`, `src/b.py`, `src/c.py`, `src/d.py`, `src/e.py`

## 4. Verification Matrix
Command: `pytest tests/`
Input: x -> Expected: y
"""
        passed, issues, _ = validate_plan_content(bloated_milestone, "bloated.md")
        self.assertFalse(passed)
        self.assertTrue(any("violates Atomic Milestone budget" in issue for issue in issues))

    def test_forbidden_generic_assertions_fail(self):
        generic_plan = """
# Plan: Lazy Testing
## 1. Affected Files
- `src/a.py`

## 2. Data Flow & Interface Signatures
Signature

## 3. Atomic Milestones
### Milestone 1
`src/a.py`

## 4. Verification Matrix
We will write unit tests to verify the feature works properly.
`pytest tests/`
"""
        passed, issues, _ = validate_plan_content(generic_plan, "generic.md")
        self.assertFalse(passed)
        self.assertTrue(any("Forbidden generic test description" in issue for issue in issues))

    def test_template_compliance(self):
        import os
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates",
            "test-plan",
            "spec-driven-plan-template.md"
        )
        passed, issues, _ = lint_plan_file(template_path)
        self.assertTrue(passed, f"Built-in template failed validation: {issues}")


if __name__ == "__main__":
    unittest.main()
