---
name: verify
description: Execute 7 Quality Gates to verify complete codebase integrity before handoff.
trigger: /verify
---

# Workflow: verify

Execute 7 Quality Gates (UTF-8 No BOM, No Inline XPath, UniqueCode Idempotence, Meta Infer, Clean POM, AST Linter):

```bash
python tools/verify_all.py
```

If any gate returns FAIL, pause execution and resolve defects completely before proceeding.
