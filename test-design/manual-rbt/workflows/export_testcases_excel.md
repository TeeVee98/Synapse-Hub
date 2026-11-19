---
description: Convert Markdown test cases into styled Excel (.xlsx) spreadsheets.
skills:
  - rbt-manual-testing
---

# /export_testcases_excel — Test Case Exporter (Excel, Jira Xray & TestRail)

Converts any Markdown Test Case document or artifact into enterprise-ready artifacts: professional Excel workbooks (`.xlsx`), Jira Xray import files (CSV/JSON), and TestRail suites (CSV/XML).

---

## Execution Commands

### 1. Export to Styled Excel Workbook
<!-- classification: illustrative -->
```bash
# Export with default name (input.xlsx)
agent-qa export-excel path/to/test_cases.md

# Export with custom destination and worksheet title
agent-qa export-excel path/to/test_cases.md -o output_name.xlsx --sheet-name "Regression Suite"
```

### 2. Export to Jira Xray (CSV / JSON)
<!-- classification: illustrative -->
```bash
# Export to Jira Xray CSV
python tools/contrib/xray_exporter.py path/to/test_cases.md -o xray_testcases.csv --format csv

# Export to Jira Xray JSON (Xray Cloud API ready)
python tools/contrib/xray_exporter.py path/to/test_cases.md -o xray_payload.json --format json --test-exec-key "PROJ-102"
```

### 3. Export to TestRail (CSV / XML)
<!-- classification: illustrative -->
```bash
# Export to TestRail Multi-Step CSV
python tools/contrib/testrail_exporter.py path/to/test_cases.md -o testrail_cases.csv --format csv

# Export to TestRail Suite XML
python tools/contrib/testrail_exporter.py path/to/test_cases.md -o testrail_suite.xml --format xml --section-name "Regression Suite"
```

## Features of Exported Workbooks

- **Navy Blue Header:** Dark blue fill (`#1F4E78`), bold white text, vertically centered.
- **Frozen Header:** Top row frozen (`A2`) for continuous scrolling.
- **AutoFilter:** Filter dropdowns automatically enabled on all columns.
- **Color-Coded Status Badges:**
  - `Risk Level`: High (Soft Red), Medium (Soft Yellow), Low (Soft Green).
  - `Priority`: Critical/High (Soft Red/Orange), Medium (Soft Yellow), Low (Soft Green).
  - `Automatable`: Yes (Soft Green), Partial (Soft Yellow), No (Soft Gray).
- **Auto-Formatting:** Multi-line `<br>` tags converted to true Excel newlines with text wrapping and optimized column widths.
