---
name: graphify-impact-analyzer
description: "Analyze code change blast radius and scope impacted test cases via AST. Use when analyzing the blast radius of code changes via dependency graphs."
category: architecture_and_analysis
version: "2.0.0"
policies:
  network: none
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---
# Graphify Impact Analyzer — AST Knowledge Graph Navigation & Impact Analysis

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Use when analyzing the blast radius of code modifications, executing targeted test impact analysis via AST dependency graphs, or locating impacted test suites after refactoring.
- **Activation Scope:**
  - Code changes in Page Classes, utility helpers, and shared base abstractions.
  - AST knowledge graph queries (`graphify-out/graph.json`).
  - Pre-execution test scoping for CI/CD pipelines to run only affected test cases.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
  - Do NOT execute blind full-corpus regression runs when changes are strictly localized to isolated leaf classes.
  - Do NOT mutate or corrupt the AST graph without running synchronization (`graphify update .`).
  - Do NOT reference non-existent project files or broken visual report paths.
- **Sibling Skill Boundaries:**
  - `repo-quality-audit`: Conducts holistic 6-pillar repository architecture and debt audits.
  - `senior-code-review`: Evaluates code diffs against Clean POM, security, and performance standards.
  - `graphify-impact-analyzer` (this skill): Navigates dependency graphs and computes test impact blast radius.

---

## 3. Ordered Execution Workflow

### Phase 1: AST Knowledge Graph Navigation & Capabilities

1. **Deterministic AST Parsing (Zero API Cost):**
   - Automatically maps files, classes, methods, and test scripts into `graphify-out/graph.json`.
   - Replaces blind, expensive full-corpus grepping with targeted graph traversals.

2. **Automated Test Impact Analysis:**
   - When a Page Class (e.g. `examples/playwright-crm-suite/pages/CustomerPage.ts`) is modified, the impact analyzer computes reverse dependencies in `graphify-out/graph.json`.
   - Pinpoints the exact subset of Test Cases affected, significantly reducing test execution overhead.

3. **God Node & Technical Debt Detection:**
   - Detects over-coupled classes and guides safe, modular refactoring.

### Phase 2: Test Impact Analysis Workflow (`tools/core/test_impact.py`)

Run impact analysis before dispatching test suites:

#### Check Impact of Modified Page Class

<!-- classification: illustrative -->
```bash
# Analyze impact for a specific modified Page Class
synapse impact -f examples/playwright-crm-suite/pages/CustomerPage.ts
```

*Expected Output:*
- Target File: `examples/playwright-crm-suite/pages/CustomerPage.ts`
- Directly Impacted: `examples/playwright-crm-suite/tests/customers.spec.ts`
- Status: Isolated blast radius

#### Automatically Analyze Git Changes

<!-- classification: illustrative -->
```bash
# Analyze impact from current working tree git diff
synapse impact --git-diff
```

#### Output Machine-Readable JSON (For CI/CD Pipelines)

<!-- classification: illustrative -->
```bash
# Export structured blast radius JSON report
synapse impact --git-diff --json
```

See reference schema in `examples/dependency_blast_radius.json`.

### Phase 3: Knowledge Graph Navigation Commands

<!-- classification: illustrative -->
```bash
# Explain a Page Class or Script and its connections
graphify explain "CustomerPage"

# Find shortest dependency path between two classes/scripts
graphify path "CustomerPage" "BasePage"

# Refresh AST graph after code modifications
graphify update .
```

### Phase 4: Visual Artifacts Inspection

- **Interactive Visualizer:** `graphify-out/graph.html`
- **Call-flow Diagrams:** `graphify-out/Agent-Skill-callflow.html`
- **Summary Report:** `graphify-out/GRAPH_REPORT.md`

### Phase 5: One Safety Fact & 5-Level Empirical Proof Ladder

Listing callers via AST grep is only the start; grep misses JSON payloads, DB schemas, wire formats, feature flags, and lifecycle/teardown ordering. For any non-trivial or risky diff:
1. **Name the One Safety Fact:** Identify the single invariant the change's safety depends on (e.g., *"this cleanup only removes expired cache entries"*).
2. **Climb the 5-Level Proof Ladder** (push to Level 4+ instead of stopping at a plausible writeup):
   - *Level 1:* Claimed in prose (insufficient).
   - *Level 2:* Cited exact `file:line` or library source.
   - *Level 3:* Traced the failure path step-by-step showing it cannot reach.
   - *Level 4:* Executed a small test/script calling the real code and failing loud on breakage.
   - *Level 5:* Reproduced/verified inside the running app.
3. **Separate Confirmed Risks from Cleared Paths:** Cite `file:line` for every cleared path and attach the repro/verification command before merge.

---

## 4. Verification Points & DoD

1. **AST Graph Integrity:** `graphify-out/graph.json` exists, parses as valid JSON, and reflects current workspace state.
2. **Blast Radius Accuracy:** Impact analysis accurately identifies callers and dependent test suites of touched files.
3. **Artifact Resolution:** Visualizer files (`graphify-out/Agent-Skill-callflow.html`, `graphify-out/graph.html`) resolve cleanly.
4. **Tool Command Exit Code:** `synapse impact` executes with exit code 0.

---

## 5. Handoff Protocol

- **Deliverables:** Impacted test suite list, blast radius classification report (`examples/dependency_blast_radius.json`), and updated knowledge graph.
- **Next Subagent:** Pass the list of impacted test files to `test-runner` for targeted execution or `quality-gatekeeper` for change validation.
- **Output Format:** JSON list of affected test files and summary markdown.
