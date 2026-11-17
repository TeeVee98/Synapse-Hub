---
name: file-and-report-validator
description: "Validate downloaded and uploaded files (Excel, CSV, PDF) schemas and tabular integrity. Use when validating exported files or reports against a schema."
category: verification_and_resilience
version: "2.0.0"
policies:
  network: none
  shell: read-only
  filesystem: read-only
---
# File & Report Validator Skill

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Validate downloaded and uploaded files (Excel, CSV, PDF) schemas and tabular integrity. Use when validating exported files or reports against a schema.
- **Activation Scope:** Domain workflows for `07-data-and-state` involving `file-and-report-validator`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT assert only file download existence; validate internal content structure and data integrity.
- Do NOT store downloaded test files in uncontrolled directories; use isolated temporary sandboxes.
- Do NOT parse large PDF/Excel files without proper error handling and resource cleanup.
- **Sibling Skill Boundaries:**
  - db-state-verifier validates databases; file-and-report-validator validates downloaded report files (PDF, XLSX, CSV, JSON).

---

## 3. Ordered Execution Workflow

> **Target:** Eliminate superficial testing of file exports and imports by inspecting and asserting exact file contents, schemas, formulas, and values across Excel, CSV, and PDF formats.

---

### Core Principles

1. **Verify Binary Contents, Not Just Download Events:**
   - Catching the browser `download` event is insufficient. The downloaded file must be opened, parsed, and its tabular records cross-referenced against expected database or UI table states.
2. **Schema & Header Conformance:**
   - Assert exact column headers, cell data formats (dates, currencies, numeric precision), and sheet names.
3. **Idempotent File Lifecycle:**
   - Store temporary test downloads in a sandboxed scratch folder and purge them during teardown.

---

### Standard Playwright Download Handling

<!-- classification: illustrative -->
```typescript
import { test, expect } from '@playwright/test';
import path from 'path';

test('export and verify financial report', async ({ page }) => {
  const downloadPromise = page.waitForEvent('download');
  await page.click('button#export-excel');
  const download = await downloadPromise;

  const savePath = path.join('temp_downloads', download.suggestedFilename());
  await download.saveAs(savePath);

  expect(download.suggestedFilename()).toMatch(/^Report_\d{8}\.xlsx$/);
});
```

---

### Deep Content Inspection Recipes (Python)

### Pattern A: Excel (.xlsx / .xls) Schema & Data Assertion
<!-- classification: illustrative -->
```python
import pandas as pd

def validate_excel_report(file_path: str, expected_min_rows: int = 1):
    df = pd.read_excel(file_path)
    
    # 1. Assert header schema
    expected_headers = ["ID", "Customer Name", "Total Amount", "Status"]
    assert list(df.columns) == expected_headers, f"Header mismatch: {df.columns}"
    
    # 2. Assert row counts and non-empty values
    assert len(df) >= expected_min_rows, f"Expected at least {expected_min_rows} rows, got {len(df)}"
    assert not df["ID"].isnull().any(), "Found NULL values in ID column"
    print(f"[PASS] Successfully verified {len(df)} rows in {file_path}")
```

### Pattern B: CSV Chunk Streaming (For Big Data Exports > 100k Rows)
<!-- classification: illustrative -->
```python
import csv

def validate_large_csv_stream(file_path: str, expected_header: list):
    row_count = 0
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == expected_header, f"CSV Header mismatch: {header}"
        for row in reader:
            row_count += 1
            assert len(row) == len(header), f"Malformed row at line {row_count}"
    print(f"[PASS] Verified {row_count} streamed CSV rows without memory overflow.")
```

### Pattern C: PDF Document Text & Metadata Extraction
<!-- classification: illustrative -->
```python
import pypdf

def assert_pdf_contains_text(pdf_path: str, expected_keywords: list):
    reader = pypdf.PdfReader(pdf_path)
    assert len(reader.pages) > 0, "PDF is empty (0 pages)!"

    full_text = "\n".join([page.extract_text() or "" for page in reader.pages])
    for kw in expected_keywords:
        assert kw in full_text, f"PDF assertion failed: Keyword '{kw}' missing in {pdf_path}"
    print(f"[PASS] Verified keywords {expected_keywords} across {len(reader.pages)} PDF pages.")
```

---

### ISO/IEC 25012 Data Quality & DAMA-DMBOK ETL Reconciliation
- Audit datasets against ISO 25012 characteristics (Completeness, Consistency, Accuracy, Currentness SLA) via `tools/etl_data_reconciler.py --quality-audit <file>`.
- Reconcile Source vs Target ETL migration files (row count, dropped key deltas, mutated values, aggregate sum balance) via `agent-qa etl --reconcile --source src.csv --target tgt.csv --key id --gate`.

---

## 4. Verification Points & DoD

1. Downloaded file format, MIME type, and byte size verified.
2. Deep content inspection validates specific text strings, cell coordinates, and row counts.
3. ETL data migrations and report exports reconciled with zero dropped records (`tools/etl_data_reconciler.py --gate`).
4. Downloaded test files cleaned up from temporary sandbox upon test completion.

---

## 5. Handoff Protocol

- **Deliverables:** File validation test scripts, parsing helpers, and download integrity reports.
- **Next Subagent:** quality-gatekeeper
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
