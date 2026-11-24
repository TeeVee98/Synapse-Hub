# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
"""
tests/test_polyglot_anchors.py — Unit Tests for AST Pre-Flight Sensor & Polyglot Anchors
Part of Synapse Hub — Created by Thế Vị (@TeeVee98) under MIT License.
"""

import unittest
from tools.lint.plan_schema_sentinel import validate_plan_content, verify_plan_ast_grounding
from tools.design.super_plan_engine import scaffold_super_plan
from tools.context.polyglot_ast_parser import (
    parse_json_structural_anchors,
    parse_yaml_structural_anchors,
    parse_dockerfile_structural_anchors,
    parse_shell_structural_anchors,
    parse_markdown_structural_anchors,
    parse_toml_structural_anchors,
    parse_polyglot_signatures,
)


class TestPolyglotAnchorsAndPreflight(unittest.TestCase):
    """Verifies AST preflight sensor, phantom symbol detection, and overwrite guards."""

    def test_preflight_phantom_symbol(self):
        plan = """# Super-Plan: Test Phantom
## 1. Affected Files & Blast Radius
| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
| `[MODIFY]` | `tools/design/super_plan_engine.py` (AST: phantom_nonexistent_xyz_symbol) | Test scope |

## 2. Data Flow & Interface Signatures
- Consumes: None
- Produces: None

## 3. Atomic Milestones (Execution DAG)
### Milestone 1: Step One
- Node ID: M1 | depends_on: []
- Compute Tier: [Model: Flash | Thinking: Off | Temp: 0.1]
- Files Modified (Max 2): tools/design/super_plan_engine.py
- Circuit Breaker: Max Fix Attempts: 2
- Rollback Hook: git checkout -- tools/design/super_plan_engine.py

## 4. Verification Matrix
- Scenario 1: python3 -m pytest tests/test_polyglot_anchors.py
- Scenario 2: Error handling
- Scenario 3: Boundary
- Scenario 4: CLI

## 5. Tri-Vulnerability Self-Critique
- Race: None
- Boundary: Checked
- Blast Radius: Local
"""
        passed, issues, details = validate_plan_content(plan, mode="super")
        self.assertFalse(passed)
        self.assertTrue(any("phantom AST symbol" in iss for iss in issues))
        ast_res = verify_plan_ast_grounding(plan)
        self.assertFalse(ast_res["is_valid"])
        self.assertTrue(any("phantom_nonexistent_xyz_symbol" in sym for sym in ast_res["phantom_symbols"]))

    def test_preflight_valid_symbol(self):
        plan = """# Super-Plan: Test Valid Symbol
## 1. Affected Files & Blast Radius
| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
| `[MODIFY]` | `tools/design/super_plan_engine.py` (AST: calculate_risk_routing) | Core routing logic |

## 2. Data Flow & Interface Signatures
- Consumes: None
- Produces: None

## 3. Atomic Milestones (Execution DAG)
### Milestone 1: Step One
- Node ID: M1 | depends_on: []
- Compute Tier: [Model: Flash | Thinking: Off | Temp: 0.1]
- Files Modified (Max 2): tools/design/super_plan_engine.py
- Circuit Breaker: Max Fix Attempts: 2
- Rollback Hook: git checkout -- tools/design/super_plan_engine.py

## 4. Verification Matrix
- Scenario 1: python3 -m pytest tests/test_polyglot_anchors.py
- Scenario 2: Error handling
- Scenario 3: Boundary
- Scenario 4: CLI

## 5. Tri-Vulnerability Self-Critique
- Race: None
- Boundary: Checked
- Blast Radius: Local
"""
        ast_res = verify_plan_ast_grounding(plan)
        self.assertEqual(ast_res["phantom_symbols"], [])
        self.assertEqual(ast_res["missing_files"], [])
        self.assertTrue(ast_res["is_valid"])

    def test_create_overwrite_guard(self):
        plan = """# Super-Plan: Collision Test
## 1. Affected Files & Blast Radius
| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
| `[CREATE]` | `tools/design/super_plan_engine.py` | Overwrite collision without tag |

## 2. Data Flow & Interface Signatures
- Consumes: None

## 3. Atomic Milestones (Execution DAG)
### Milestone 1: Step One
- Node ID: M1 | depends_on: []
- Compute Tier: [Model: Flash | Thinking: Off | Temp: 0.1]
- Files Modified (Max 2): tools/design/super_plan_engine.py
- Circuit Breaker: Max Fix Attempts: 2
- Rollback Hook: git checkout -- tools/design/super_plan_engine.py

## 4. Verification Matrix
- Scenario 1: python3 -m pytest tests/test_polyglot_anchors.py
- Scenario 2: Error handling
- Scenario 3: Boundary
- Scenario 4: CLI

## 5. Tri-Vulnerability Self-Critique
- Race: None
- Boundary: Checked
- Blast Radius: Local
"""
        passed, issues, details = validate_plan_content(plan, mode="super")
        self.assertFalse(passed)
        self.assertTrue(any("without explicit (Overwrite) tag" in iss for iss in issues))
        ast_res = verify_plan_ast_grounding(plan)
        self.assertIn("tools/design/super_plan_engine.py", ast_res["collision_files"])

    def test_create_with_overwrite_allowed(self):
        plan = """# Super-Plan: Overwrite Allowed
## 1. Affected Files & Blast Radius
| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
| `[CREATE]` | `tools/design/super_plan_engine.py` (Overwrite) | Explicit overwrite permitted |

## 2. Data Flow & Interface Signatures
- Consumes: None

## 3. Atomic Milestones (Execution DAG)
### Milestone 1: Step One
- Node ID: M1 | depends_on: []
- Compute Tier: [Model: Flash | Thinking: Off | Temp: 0.1]
- Files Modified (Max 2): tools/design/super_plan_engine.py
- Circuit Breaker: Max Fix Attempts: 2
- Rollback Hook: git checkout -- tools/design/super_plan_engine.py

## 4. Verification Matrix
- Scenario 1: python3 -m pytest tests/test_polyglot_anchors.py
- Scenario 2: Error handling
- Scenario 3: Boundary
- Scenario 4: CLI

## 5. Tri-Vulnerability Self-Critique
- Race: None
- Boundary: Checked
- Blast Radius: Local
"""
        ast_res = verify_plan_ast_grounding(plan)
        self.assertEqual(ast_res["collision_files"], [])
        self.assertTrue(ast_res["is_valid"])

    def test_scaffold_task_matched_symbol(self):
        scaffold = scaffold_super_plan(
            "Refactor calculate_risk_routing algorithm",
            ["tools/design/super_plan_engine.py"]
        )
        self.assertIn("(AST: calculate_risk_routing)", scaffold)

    def test_nonsource_json_rfc6901_minified_and_pretty(self):
        minified = '{"planning":{"fan_cap":32,"items":[{"id":"step1"}]}}'
        symbols = parse_json_structural_anchors(minified, "dummy.json")
        names = {s["name"] for s in symbols}
        self.assertIn("/planning/fan_cap", names)
        self.assertIn("/planning/items/0/id", names)

    def test_nonsource_yaml_with_list_selectors(self):
        yaml_content = """
name: CI
jobs:
  build:
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      - name: Setup
        run: echo setup
"""
        symbols = parse_yaml_structural_anchors(yaml_content, "ci.yaml")
        names = {s["name"] for s in symbols}
        self.assertTrue(any("Checkout" in n for n in names))
        self.assertTrue(any("Setup" in n for n in names))

    def test_nonsource_dockerfile_multiline_and_stages(self):
        dockerfile = """
FROM python:3.11-slim AS builder
RUN apt-get update && \\
    apt-get install -y curl
WORKDIR /app

FROM python:3.11-slim AS runner
COPY --from=builder /app /app
CMD ["python", "main.py"]
"""
        symbols = parse_dockerfile_structural_anchors(dockerfile, "Dockerfile")
        names = {s["name"] for s in symbols}
        self.assertIn("STAGE:builder", names)
        self.assertIn("STAGE:runner", names)
        # Verify multiline RUN was captured
        run_syms = [s for s in symbols if "RUN" in s["name"]]
        self.assertTrue(len(run_syms) >= 1)
        self.assertEqual(run_syms[0]["line"], 3)
        self.assertEqual(run_syms[0]["end_line"], 4)

    def test_nonsource_shell_heredoc_isolation(self):
        shell_script = """#!/usr/bin/env bash
cat << 'EOF'
fake_func() {
    echo "inside heredoc"
}
EOF

real_func() {
    echo "outside heredoc"
}

function another_func {
    echo "another style"
}
"""
        symbols = parse_shell_structural_anchors(shell_script, "script.sh")
        names = {s["name"] for s in symbols}
        self.assertIn("function:real_func", names)
        self.assertIn("function:another_func", names)
        self.assertNotIn("function:fake_func", names)

    def test_nonsource_markdown_headings(self):
        markdown = """# Main Document
Intro text

```markdown
# Ignored Header Inside Code Block
```

## Section One
Content
"""
        symbols = parse_markdown_structural_anchors(markdown, "doc.md")
        names = {s["name"] for s in symbols}
        self.assertIn("heading:main-document", names)
        self.assertIn("heading:section-one", names)
        self.assertNotIn("heading:ignored-header-inside-code-block", names)

    def test_nonsource_toml_tables(self):
        toml_content = """
[project]
name = "synapse-hub"
version = "4.8.0"

[project.dependencies]
pytest = ">=7.0.0"
"""
        symbols = parse_toml_structural_anchors(toml_content, "pyproject.toml")
        names = {s["name"] for s in symbols}
        self.assertTrue(any("project.name" in n for n in names))
        self.assertTrue(any("project.version" in n for n in names))

    def test_nonsource_polyglot_signatures_dispatch(self):
        res_json = parse_polyglot_signatures("synapse.config.json")
        self.assertTrue(res_json["exists"])
        self.assertEqual(res_json["language"], "json")
        sym_names = {s["name"] for s in res_json["symbols"]}
        self.assertTrue(any("/planning" in n or "planning" in n for n in sym_names))


if __name__ == "__main__":
    unittest.main()
