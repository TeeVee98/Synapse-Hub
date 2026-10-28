---
name: graphify-impact-analyzer
description: >-
  AST Knowledge Graph exploration, Architecture Navigation, and Zero-Waste Test Impact Analysis
  across multi-module test cases using Graphify and tools/test_impact.py.
---

# Graphify & Test Impact Analyzer â€” Codebase Architecture Navigation

Specialized skill for zero-token architecture exploration, dependency mapping, and automated Test Impact Analysis across multi-module test suites.

---

## 1. Core Architectural Pillars

1. **Deterministic AST Parsing (Zero API Cost):**
   - Automatically maps all 698 files, 1,189 nodes, 2,085 edges, and 392 communities into `graphify-out/graph.json`.
   - Replaces blind, expensive full-corpus grepping with targeted graph traversals.

2. **Automated Test Impact Analysis (Zero Waste):**
   - When any Page Class in `Keywords/dmit/pages/` is modified, the impact analyzer computes reverse dependencies in `graph.json`.
   - Pinpoints the exact subset of Test Cases affected out of 259 TCs, reducing CI/CD execution time by up to 95%.

3. **God Node & Technical Debt Detection:**
   - Detects over-coupled classes (e.g. `DataMiningPage.groovy` with 17+ edges) and guides safe, modular refactoring.

---

## 2. Test Impact Analysis Workflow (`tools/test_impact.py`)

Run impact analysis before dispatching test suites:

### 2.1. Check Impact of Modified Page Class
```bash
python3 tools/test_impact.py -f Keywords/dmit/pages/CommonCategoryPage.groovy
```
*Output:*
- Target File: `Keywords/dmit/pages/CommonCategoryPage.groovy`
- Directly Impacted: **12 / 259 TCs** (TC-17 to TC-28)
- Skipped: **247 TCs**
- Time Saved: **95.4%**

### 2.2. Automatically Analyze Git Changes
```bash
python3 tools/test_impact.py --git-diff
```

### 2.3. Output Machine-Readable JSON (For CI/CD Pipelines)
```bash
python3 tools/test_impact.py --git-diff --json
```

---

## 3. Knowledge Graph CLI Navigation Commands

| Command | Purpose | Example |
|---|---|---|
| `graphify explain "<Node>"` | Explain a Page Class or Script and its connections | `graphify explain "DataMiningPage"` |
| `graphify path "<A>" "<B>"` | Find shortest path between two classes/scripts | `graphify path "LoginPage" "BasePage"` |
| `graphify query "<Concept>"` | Query a concept or test case subgraph | `graphify query "TC-247"` |
| `graphify update .` | Refresh AST graph after code modifications (No LLM needed) | `graphify update .` |

---

## 4. Visual Artifacts

- **2D/3D Interactive Visualizer:** `graphify-out/graph.html`
- **Call-flow & Mermaid Diagrams:** `graphify-out/callflow.html`
- **Architectural Summary Report:** `graphify-out/GRAPH_REPORT.md`

---

## 5. Agent Operational Guardrails

1. **Before modifying any Page Class:** Run `python3 tools/test_impact.py -f <path>` to identify dependent Test Cases.
2. **After modifying code:** Run `graphify update .` to keep the knowledge graph synchronized.
3. **DoD Compliance:** Always verify that all changes pass `python3 tools/verify_all.py`.
