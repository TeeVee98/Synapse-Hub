---
trigger: always_on
description: Context-aware progressive stack router and token-minimal rule/skill loader.
profiles: [core, full]
---

# Context-Aware Stack Router & Token-Minimal Loader (Boost B2)

> Added to Synapse-Hub `.agents/rules/` to minimize token consumption (~4,000 tokens/turn) and provide universal cross-project applicability.

## 1. Lazy-Loading Rules & Skills (Load Only What the Project Needs)
At session initialization, AI agents **scan the workspace root to a maximum depth of 2 levels** (or execute automated routing via `python tools/rules_router.py` / `agent-qa rules-router`) and load exclusively the rule and skill subset matching the active project stack (do NOT load all 56 skills or irrelevant platform rules):

* **Web / API (`playwright.config.*`, `cypress.config.*`, `openapi.*`, `pytest`, `jest`):** Load only `mandatory-playwright-live.md` (if using Playwright) + `clean-pom-crafter` + `api-network-mocking-interception`.
* **Mobile (`appium`, `*.xcodeproj`, `build.gradle`):** Load only `mobile_appium_rules.md` + `clean-pom-crafter` (following SOM standard). Omit `mandatory-playwright-live.md`.
* **Performance (`k6`, `*.jmx`, `locustfile.py`):** Load only `performance_testing_rules.md` + `backend-load-and-stress-patterns`.
* **Security (`burp`, `zap`, `nuclei`, pentest/DAST):** Load only `security_testing_rules.md` + `security-dast-sentinel` + `skillspector-security-guard`.

## 2. Token-Minimal Progressive Router (`tools/rules_router.py`)
AI agents can trigger the automated router to inspect and obtain the minimal configuration:
```bash
python tools/rules_router.py --summary
# Output: [RULES-ROUTER] Stacks: playwright,git | Rules: 5 | Saved: 2,635 tokens/turn (40.5%)
```

## 3. Adaptive Verification (Fast Mode vs Full Gate)
* **Fast Mode (Quick fixes / authoring 1–2 test cases):** Perform static validation (0 hard sleeps, 0 secrets, verified `assert` statements) and execute the native test runner for **strictly the modified file**, achieving `Exit Code 0`.
* **Full Gate (PR Finalization / Release Acceptance):**
  * If the project contains `tools/verify_all.py` (full Synapse-Hub environment): execute `python3 tools/verify_all.py`.
  * If the target is an external repository without `tools/verify_all.py`: execute the complete test suite using the project's native command defined in `package.json` / `pyproject.toml` / `Makefile`, followed by credential leak scanning.

## 4. Hierarchical Monorepo Scoping (Supabase & vLLM Standard)
In monorepos containing multiple packages/apps (`apps/*`, `services/*`, `packages/*`), agents **ALWAYS** resolve localized subproject scope via path-matching (`python tools/rules_router.py --paths <file>` or `monorepo_scope.json`):
* Root invariants (`AGENTS.md`) are ALWAYS inherited and can NEVER be overridden.
* Subproject-specific rules (e.g. `apps/studio/AGENTS.md`) are loaded dynamically, reducing token footprint by 50%–65%.
* Token-Saver Invariant (Svelte Standard): Subproject rule files PREFER concise declarations (< 50 lines).

## 5. Active Pre-Tool Shell Guard (Oven Bun Standard)
Before executing shell commands, agents PREFER validating commands through `python tools/pre_bash_guard.py "<command>"`:
* **NEVER** run business test runners (`playwright test`, `cypress run`, `mvn test`) in Synapse-Hub root (Lesson Learned #7 & #8).
* **NEVER** execute destructive deletion commands (`rm -rf /`, `rmdir /s /q C:\`).
* **NEVER** force-push (`git push -f`) to protected branches (`main`, `master`, `develop`).
