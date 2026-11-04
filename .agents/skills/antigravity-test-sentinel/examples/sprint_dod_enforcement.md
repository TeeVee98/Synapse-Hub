# Sprint Definition of Done (DoD) Sentinel Enforcement

> **Policy:** No feature branch, bug fix, or refactoring PR may merge without passing all active DoD gates.

---

## 1. Zero-Command Local Verification

Before handing off code to reviewers or pushing to remote, AI agents automatically execute:

```bash
python tools/verify_all.py --mode hub
```

Expected output:
```text
======================================================================
[ALL QUALITY GATES PASSED - 100% DoD COMPLIANT]
   Repository is 100% compliant, secure, and ready for execution/CI/CD.
======================================================================
```

---

## 2. Gate Failure Escalation Protocol

| Failed Gate | Immediate Remediation | Non-Negotiable Boundary |
| :--- | :--- | :--- |
| **Gate 1 (UTF-8 BOM)** | Re-encode file to UTF-8 without BOM; verify with `tools/verify_all.py`. | Reject PR automatically; zero BOM tolerated. |
| **Gate 3 (Clean POM)** | Move raw XPath/CSS selectors from test script into Page Class. | Zero raw selectors inside `tests/` or `Scripts/`. |
| **Gate 6 (Credentials)** | Remove hardcoded passwords or keys; move to `.env` or CI secret. | Never bypass; zero plain secrets on disk. |
| **Gate 7 (Static Linter)** | Remove empty catch blocks (`except: pass`); add valid asserts. | Zero fake-passes allowed. |
| **Gate 8 (Mutator >= 80%)** | Add downstream assertions validating mutated return state. | Mutation score $< 80\%$ blocks completion. |

---

## 3. CI/CD Pre-Push Hook Integration

Inside `.git/hooks/pre-push`:
```bash
#!/bin/sh
python3 tools/verify_all.py --mode hub
if [ $? -ne 0 ]; then
    echo "❌ [DoD BLOCKED] Cannot push until all 10 Quality Gates pass."
    exit 1
fi
```
