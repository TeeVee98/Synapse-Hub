---
description: Generate manual test cases using 6-stage Risk-Based Testing pipeline.
skills:
  - rbt-manual-testing
---

# /generate_manual_testcases_rbt — 6-Stage AI-RBT Manual Test Generation

Execute the structured 6-stage **AI-Driven Risk-Based Testing (AI-RBT)** pipeline defined in `.agents/skills/02-test-design/rbt-manual-testing/SKILL.md`.

## Execution Rules & Pipeline Checkpoints

- **Execution Mode:** FULL RBT (strictly sequential, never combine stages in a single pass).
- **Mandatory Checkpoints:** The agent **MUST PAUSE** for user feedback at:
  - **Stage 2 Checkpoint:** Present numbered Ambiguity Q&A (`Q1, Q2...`) with assumptions, and wait for confirmation.
  - **Stage 4 Checkpoint:** Present Traceability Matrix (RTM) and High-Level Scenarios for user review.

---

## 6-Stage Pipeline Steps

### Stage 1: Context & Framing
1. Ingest project description, business domain, target persona, and release milestones (MVP vs Full).
2. Confirm understanding and proceed to Stage 2.

### Stage 2: Analysis & Ambiguity Q&A
1. Map Happy Paths, Alternate Paths, and Exception Paths.
2. Identify requirement ambiguities, contradictions, or missing validation rules.
3. Emit a structured Q&A table (`Q1, Q2...`) with proposed assumptions.
4. 🛑 **PAUSE — Await user confirmation before proceeding.**

### Stage 3: System Decomposition
1. Break down features into Modules -> Sub-modules -> UI components.
2. Document cross-module dependencies and shared state.

### Stage 4: Traceability Matrix (RTM) & Gap Analysis
1. Map requirement identifiers (`REQ-xxx`) to high-level test scenarios.
2. Highlight missing coverage gaps and non-functional scenarios.
3. 🛑 **PAUSE — Await user review of scenario coverage.**

### Stage 5: Detailed Test Case Generation & Risk Scoring
1. Assign Risk Levels (`High`, `Medium`, `Low`) based on business impact.
2. Apply test design techniques: Equivalence Partitioning (EP), Boundary Value Analysis (BVA), Decision Tables, State Transitions.
3. Apply the **Field-Level Validation Checklist (25 Field Types)**: generate isolated validation test cases for each input field (do not merge fields).
4. Include non-functional scenarios: Double Submit, Race Conditions, Network Drops, Browser Back/Refresh.

### Stage 6: Template Mapping & Deliverable Packaging
1. Assemble all test cases into the standard 12-column Markdown specification:
   ```markdown
   | TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |
   ```
2. Verify all test cases from Stage 5 are preserved without truncation.
3. Inform user they can export to styled Excel or TMS via:
   <!-- classification: illustrative -->
   ```bash
   agent-qa export-excel path/to/test_cases.md -o output.xlsx
   python tools/contrib/xray_exporter.py path/to/test_cases.md -o xray.csv
   python tools/contrib/testrail_exporter.py path/to/test_cases.md -o testrail.csv
   ```
