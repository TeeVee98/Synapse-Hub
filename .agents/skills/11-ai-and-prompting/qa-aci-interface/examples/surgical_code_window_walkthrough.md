# Agent-Computer Interface (ACI) — 40-Line Surgical Editing Protocol

> **Purpose:** Prevent context blowout by restricting code inspections and edits to 40-50 line surgical windows with pre-commit AST verification.

---

## 1. The Context Blowout Anti-Pattern

Monolithic test files (e.g. 3,500-line Page Classes) exhaust agent context windows when read entirely. ACI enforces:
1. Querying `repo_map.txt` first to locate exact function boundaries.
2. Reading only lines `L120-L160` instead of the full file.
3. Performing surgical in-place replacement.
4. Verifying syntax immediately with `ast.parse()` or language compiler.

---

## 2. ACI Surgical Edit Execution

```bash
# 1. Inspect exact method window
python tools/swe_qa_aci.py read --file pages/OrderPage.py --start 80 --end 125

# 2. Perform surgical patch
python tools/swe_qa_aci.py edit \
  --file pages/OrderPage.py \
  --target "time.sleep(5)" \
  --replacement "self.page.waitForSelector('.order-card', state='visible')"

# 3. Verify AST integrity before commit
python tools/infer_linter.py --file pages/OrderPage.py --strict
```

---

## 3. Pre-Commit Safety Check

The ACI engine automatically rejects patches that introduce:
- Syntax errors or brace mismatches.
- Swallowed exception handlers (`except: pass`).
- Hardcoded machine-specific absolute paths (`/Users/admin/...`).
