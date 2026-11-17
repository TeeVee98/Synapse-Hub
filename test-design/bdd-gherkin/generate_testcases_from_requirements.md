---
description: Rapid single-pass generation of structured test cases from requirements.
skills:
  - rbt-manual-testing
---

# /generate_testcases_from_requirements — Rapid Single-Pass Test Generation

Generates structured test cases in a single pass without pausing for multi-stage checkpoints. Best for isolated forms, standalone dialogs, or well-defined user stories.

## Workflow Pipeline

1. **Ingest Requirements:** Read the provided requirement text, user story, or acceptance criteria.
2. **Path Identification:** Map Happy Paths, Negative Paths, and Boundary Value scenarios.
3. **Field Validation:** Identify all form input fields and apply the **15-Field Validation Checklist** from `rbt-manual-testing`:
   - Text, Email, Phone, Password, Number, Date, Date Range, Dropdown, Multi-Select, Checkbox/Radio, Textarea, File Upload, OTP/MFA, Range Slider, Rich Text.
4. **Standard 12-Column Output:** Emit complete test cases formatted in the standard Markdown table with automation metadata (`Automatable`, `Auto Type`, `@Tags`).
5. **Excel Export Command:** Recommend the user convert the markdown table to Excel via:
   ```bash
   agent-qa export-excel path/to/cases.md -o cases.xlsx
   ```
