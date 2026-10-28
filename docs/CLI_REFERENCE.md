# Agent-QA CLI & Tools Reference Manual

The `agent-skills` Hub provides a unified CLI utility `agent-qa` (and direct python scripts in `tools/`) to execute quality gates, linting, impact analysis, and log distillation.

---

## 1. Unified CLI Entrypoint (`agent-qa`)

When installed via `pip install -e .`, the `agent-qa` command is globally accessible:

```bash
agent-qa <command> [options]
```

### Supported Commands

| Command | Subsystem | Description | Example |
| :--- | :--- | :--- | :--- |
| `verify` | Quality Sentinel | Executes all 7 Quality Gates DoD validation | `agent-qa verify` |
| `lint` | Static Analysis | AST-level fake-pass and zero-assertion scanner | `agent-qa lint` |
| `heal` | Self-Healing | Queries zero-token semantic error memory cache | `agent-qa heal query "StaleElement"` |
| `distill` | Token Optimizer | Filters verbose CLI/Gradle logs by 95% | `agent-qa distill build.log` |
| `impact` | AST Knowledge | Analyzes impact of code changes | `agent-qa impact --git-diff` |
| `canary` | Resilience Arena | Injects failure vectors to test autonomous recovery | `agent-qa canary --run` |
| `version` | Hub Metadata | Displays installed Hub version and catalog summary | `agent-qa version` |

---

## 2. Direct Python Scripts Runbook

If running without global package installation, tools can be executed directly via Python:

### 2.1. Verify 7 Quality Gates
```bash
python tools/verify_all.py
```
- **Gate 1:** 100% UTF-8 No BOM check across all scripts and page classes.
- **Gate 2:** Strict Clean POM compliance (zero raw XPaths/CSS in test scripts).
- **Gate 3:** Dynamic test data validation (verifies `uniqueCode` usage).
- **Gate 4:** Path portability check (flags absolute host directory paths).
- **Gate 5:** Documentation anti-drift check.
- **Gate 6:** Temporary file and properties artifact cleanup.
- **Gate 7:** Truth Anchor verification (no fake passes or skipped assertions).

### 2.2. AST Fake-Pass Sentinel
```bash
python tools/infer_linter.py
```

### 2.3. Semantic Memory Cache Resolver
```bash
python tools/cache_resolver.py init
python tools/cache_resolver.py query "ElementClickInterceptedException"
```

### 2.4. Log Distiller
```bash
python tools/distill_log.py execution.log
```
