---
name: file-and-report-validator
description: Validate uploaded and downloaded enterprise files (Excel .xlsx/.xls, CSV, PDF) for correct schemas, row counts, and data integrity. Use on-demand when testing export/import workflows.
---

# File & Report Validator Skill

> **Target:** Eliminate superficial testing of file exports and imports by inspecting and asserting exact file contents, schemas, and values.

---

## 1. Core Principles

1. **Verify Binary Contents, Not Just Download Events:**
   - Catching browser `download` event is insufficient. The downloaded file must be opened, parsed, and its tabular records cross-referenced against expected database or UI table states.
2. **Schema & Header Conformance:**
   - Assert exact column headers, cell data formats (dates, currencies, numeric precision), and sheet names.
3. **Idempotent File Lifecycle:**
   - Store temporary test downloads in a sandboxed scratch folder and purge them during teardown.

---

## 2. Standard Playwright Download Handling & Inspection

### Pattern A: Intercepting and Saving Downloaded Files
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

### Pattern B: Python Script for Tabular Data Validation
Agent can run lightweight Python validation against downloaded `.xlsx` or `.csv`:

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
