# Agentless 3-Phase Test Automation Repair Workflow

> **Heritage:** Adapted from **Agentless (Xia et al.)** — eliminates conversational churn and token waste by executing repair through 3 deterministic phases: **Localization**, **Candidate Synthesis**, and **Minimal Diff Validation**.

---

## Phase 1: Failure Localization (0 LLM Tokens)

Parse JUnit XML and trace stack frames to isolate the exact failing line:
```bash
python tools/agentless_patcher.py localize --junit Reports/junit.xml
```

**Result:**
- File: `tests/e2e/test_billing.py`
- Line: `87`
- Failing Expression: `assert invoice['total'] == 120.0`
- Actual State: `invoice['total'] == 120.00000000000001` (IEEE 754 float drift)

---

## Phase 2: Candidate Patch Synthesis

Generate the minimal semantic patch targeting the localized line:
```diff
- assert invoice['total'] == 120.0
+ assert round(invoice['total'], 2) == 120.00
```

---

## Phase 3: Minimal Diff Validation & Rollback Guard

Execute targeted test runner within a reversible sandbox:
```bash
python tools/agentless_patcher.py verify --patch candidate_fix.diff --test-cmd "pytest tests/e2e/test_billing.py"
```

- If test PASSES $\to$ Commit surgical patch.
- If test FAILS $\to$ Instant rollback without residual workspace dirt.
