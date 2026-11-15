---
name: verify
description: Execute 10 Quality Gates to verify complete codebase integrity and enforce deterministic safety boundaries before handoff.
trigger: /verify
---

# Workflow: verify

## 1. Pre-execution Safety Hook (Mandatory Action Firewall)
Before dispatching any UI interaction (`click`, `fill`, `submit`, `drop`) down to a live Playwright or CDP browser context, the command or code must be piped through `tools/safety_firewall.py --dry-run`:

```bash
# Verify single action safety clearance
python tools/safety_firewall.py --action click --selector "<selector>" --text "<text>" --dry-run

# Or pipe code snippet directly
python tools/safety_firewall.py --code "page.click('<selector>')" --dry-run
```
*If safety firewall reports BLOCKED, execution halts immediately unless explicitly forced via `--force` or `ALLOW_DESTRUCTIVE=1`.*

---

## 2. Hard Quality Gates Verification (10 DoD Gates)
Execute all 10 Quality Gates (Gate 1: UTF-8 No BOM, Gate 2: Path Portability, Gate 3: Clean POM, Gate 4: AI Docs Linter, Gate 5: Temporary Files Blacklist, Gate 6: Credential Security, Gate 7: AST Defect Sentinel & Pytest, Gate 8: Syntactic Micro-Mutation Testing, Gate 9: Skill Routing & Collision Guard, and Gate 10: Performance & SLA Sentinel) with pre-flight engine integrity check:

```bash
python tools/verify_all.py
```

### Gate 8 Hard Rejection Rule:
- Any new or updated test case must achieve an AST Mutation Score of **$\ge 80\%$** via `tools/micro_mutator.py`.
- If `mutation_score < 80%`, the Gatekeeper strictly rejects the test suite (anti-tautology and anti-fake-pass policy).

If any gate returns `FAIL`, pause execution and resolve defects completely before proceeding.
