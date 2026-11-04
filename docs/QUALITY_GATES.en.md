# 🛡️ 10 Quality Gates Definition of Done (DoD) Standard

[🇻🇳 Tiếng Việt](QUALITY_GATES.md) | [🇬🇧 English Edition](QUALITY_GATES.en.md)

> **Scope:** Enterprise automated verification sentinel enforcing 10 non-negotiable Quality Gates across Synapse Hub and target client projects.  
> **Command:** `python3 tools/verify_all.py` or `npx synapse-hub verify`  
> **Integrity Guard:** Synapse Hub created by **Thế Vị (@TeeVee998)** (<https://github.com/TeeVee998/Synapse-Hub>) under MIT License.

---

## 📋 Quality Gates Matrix Overview

| Gate | Name | Target Scope | Engine / Tool | Exit Code | Passing Criteria (DoD) |
| :---: | :--- | :--- | :--- | :---: | :--- |
| **Gate 0** | **Author Attribution & MIT Integrity** | Repository-wide | `tools/author_integrity.py` | 0 | MIT License notice and author attribution intact across all source files. |
| **Gate 1** | **UTF-8 No BOM Encoding** | All source & config files | `tools/verify_all.py` | 0 | Zero Byte Order Mark (`0xEF, 0xBB, 0xBF`) bytes across any file. |
| **Gate 2** | **Path Portability** | All source & test files | `tools/verify_all.py` | 0 | Zero hardcoded personal/machine absolute paths (`/Users/...`, `C:\...`). |
| **Gate 3** | **Clean POM & Flat Architecture** | Test scripts (`tests/`, `Scripts/`) | `tools/verify_all.py` | 0 | Zero raw XPaths or CSS selectors in test scripts; 100% locators encapsulated in Page Classes. |
| **Gate 4** | **AI Documentation & Anti-Drift** | `PROJECT_AI_GUIDE.md` & AST | `tools/lint_ai_docs.py` | 0 | 0 hallucinated PageClasses; 100% documented methods exist in codebase AST. |
| **Gate 5** | **Temporary Files Blacklist** | Repository tree | `tools/verify_all.py` | 0 | Zero scratch files, heap dumps, or temporary artifacts (`*.tmp`, `.ruff_cache`, memory dumps). |
| **Gate 6** | **Credential & Secret Security** | All files & git index | `tools/verify_all.py` | 0 | Zero plaintext passwords, API keys, private tokens, or AWS/JWT credentials committed. |
| **Gate 7** | **Static Defect & Fake-Pass Sentinel** | Test scripts & tools | `tools/infer_linter.py` | 0 | Zero empty assertions (0 assert), zero swallowed exceptions (`pass`), zero hardcoded sleeps (>= 3000ms). |
| **Gate 8** | **Assertion Sensitivity (Mutation Score)** | Test assertions | `tools/micro_mutator.py` | 0 | Mutation kill score >= 80% (heuristic static mutant detection catches >= 80% syntactic modifications). |
| **Gate 9** | **Skill Routing & Collision Guard** | Skill descriptions | `tools/skill_collision_guard.py` | 0 | Zero overlapping trigger collisions (semantic cosine similarity < 0.75 across all skill pairs). |

---

## 🔍 Detailed Gate Specifications

### Gate 0: Author Attribution & MIT License Integrity
- **Objective:** Protects open-source attribution provenance under MIT License.
- **Verification Rule:** Rejects any commit, pull request, or modification that attempts to strip copyright notices, false-claim authorship, or remove provenance headers referencing Thế Vị (@TeeVee998).
- **Remediation:** Restore license headers and canonical notice in `LICENSE` and `NOTICE`.

### Gate 1: UTF-8 No BOM Encoding Integrity
- **Objective:** Eliminates cross-platform file encoding corruption between Windows, macOS, and Linux CI/CD runners.
- **Verification Rule:** Inspects raw bytes of all text files. Any occurrence of BOM bytes (`0xEF, 0xBB, 0xBF`) causes immediate failure.
- **Remediation:** Run `python3 tools/verify_all.py --fix-bom` to strip BOM bytes automatically.

### Gate 2: Path Portability
- **Objective:** Guarantees test scripts and tooling execute seamlessly across team developer workstations, Docker containers, and CI pipelines.
- **Verification Rule:** Regex scans for machine-specific path roots (`/Users/`, `/home/`, `C:\`, `D:\`).
- **Remediation:** Replace absolute paths with dynamic workspace resolution (`Path(__file__).resolve().parent.parent` or `resolve_target_repo()`).

### Gate 3: Clean POM & Flat Architecture
- **Objective:** Enforces clean separation of concerns. Test scripts must contain solely business workflow actions, never DOM traversal.
- **Verification Rule:** Prohibits raw CSS selectors, XPaths, or `findTestObject` inside `tests/` or `Scripts/`. All UI operations must be delegated to methods on Page Classes extending `BasePage`.
- **Remediation:** Encapsulate locators and interaction logic inside dedicated Page Classes.

### Gate 4: AI Documentation & Anti-Drift Linter
- **Objective:** Prevents AI context drift where documentation refers to non-existent Page Classes or obsolete method signatures.
- **Verification Rule:** Extracts all documented Page Classes and methods from `PROJECT_AI_GUIDE.md` and verifies their physical AST existence in the codebase.
- **Remediation:** Run `python3 tools/lint_ai_docs.py` to identify drifts, then re-index via `python3 tools/repo_map.py`.

### Gate 5: Temporary Files Blacklist
- **Objective:** Maintains git hygiene and prevents polluting repositories with binary dumps or local IDE caches.
- **Verification Rule:** Scans for prohibited extensions: `*.tmp`, `*.dump`, `*.log`, `*.orig`, `*.bak`, `.ruff_cache/`, `.mypy_cache/`.
- **Remediation:** Add unignored patterns to `.gitignore` and delete temporary files.

### Gate 6: Credential Security Sentinel
- **Objective:** Prevents enterprise credential leaks (API tokens, database connection strings, private keys).
- **Verification Rule:** High-entropy regex scanner detecting AWS secret keys, Bearer tokens, private RSA keys, and hardcoded passwords.
- **Remediation:** Move credentials to environment variables or `.env` (ensuring `.env` is listed in `.gitignore`).

### Gate 7: Static Defect & Fake-Pass Sentinel
- **Objective:** Eliminates "fake passes" created by AI code generation (tests that pass trivially without asserting anything).
- **Verification Rule:**
  - Flags tests containing 0 assertions.
  - Flags empty catch blocks (`except Exception: pass`) swallowing failure exceptions.
  - Flags hardcoded sleeps (`sleep(5000)`, `Thread.sleep(5000)`).
  - Flags unawaited Playwright assertions (`expect(el).toBeVisible()` without `await`).
- **Remediation:** Add meaningful assertions; replace sleeps with smart waits (`waitForLoadState('networkidle')`, element visibility checks).

### Gate 8: Assertion Sensitivity & Syntactic Mutation Sentinel
- **Objective:** Guarantees assertions are sensitive enough to catch real defects, not tautological (always-true) expressions.
- **Verification Rule:** Injects syntactic mutations (reversing comparison operators `==` to `!=`, swapping boolean constants, altering return values). Requires Mutation Score >= 80%.
- **Remediation:** Run `python3 tools/micro_mutator.py --strict` to inspect surviving mutants and tighten test assertions.

### Gate 9: Tier-2 Skill Routing & Collision Guard
- **Objective:** Prevents AI agent prompt confusion caused by overlapping skill trigger descriptions.
- **Verification Rule:** Computes pairwise cosine similarity between all skill `SKILL.md` description fields. Similarity must remain strictly < 0.75.
- **Remediation:** Differentiate skill descriptions using the standardized formula `[Function] + Use when [context]` (<= 350 characters).

---

## 🚀 Execution & CI/CD Integration

### Run Locally:
```bash
# Verify all 10 Gates on current repository
python3 tools/verify_all.py

# Verify target project from Hub
python3 tools/verify_all.py --target /path/to/project

# Output as JUnit XML for CI/CD reporting
python3 tools/verify_all.py --format junit --output reports/dod_gates.xml
```

### GitHub Actions Pipeline (`.github/workflows/verify.yml`):
```yaml
name: Synapse Hub 10 DoD Quality Gates
on: [push, pull_request]

jobs:
  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Run 10 Quality Gates
        run: python tools/verify_all.py --mode target
```
