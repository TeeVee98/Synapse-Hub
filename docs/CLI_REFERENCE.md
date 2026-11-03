# Agent-QA CLI & Tools Reference Manual

The `agent-skills` Hub provides a unified CLI utility `agent-qa` (and direct python scripts in `tools/`) to execute quality gates, linting, impact analysis, and log distillation.

---

## 1. Unified CLI Entrypoint (`agent-qa`)

When installed via `pip install -e .`, the `agent-qa` command is globally accessible:

```bash
agent-qa <command> [options]
```

### Supported Commands (53 Subcommands)

#### A. Core Quality & DoD Gates
| Command | Subsystem | Description | Example |
| :--- | :--- | :--- | :--- |
| `verify` | Quality Sentinel | Executes all 9 Quality Gates DoD validation | `synapse-hub verify` |
| `lint` | Static Analysis | Polyglot heuristic & static AST defect scanner with baseline & suppression | `synapse-hub lint ./tests` |
| `mutate` | Mutation Sentinel | Syntactic micro-mutator checking assertion sensitivity | `synapse-hub mutate ./tests --min-score 80` |
| `watch` | HUD Sentinel | Incremental live file watcher for real-time quality feedback | `synapse-hub watch` |
| `wcag-audit` | Accessibility | WCAG 2.2 accessibility conformance and contrast auditor | `synapse-hub wcag-audit ./reports/WELCOME.html` |
| `trace-data-flow` | Data Flow | Taint analysis tracing test data lifecycles to detect DB leaks | `synapse-hub trace-data-flow ./tests` |
| `verify-author` | Provenance Guard | Validates canonical author attribution watermark | `synapse-hub verify-author` |
| `debt` | Technical Debt | Harvests `shortcut:` annotations across repo into markdown ledger | `synapse-hub debt` |
| `review` | Senior Review | 6-pillar code change review (Bugs, Security, Scale, Tests, Speed, Bloat) | `synapse-hub review` |

#### B. Diagnostics, Onboarding & Visual Landing
| Command | Subsystem | Description | Example |
| :--- | :--- | :--- | :--- |
| `doctor` | Environment Audit | 1-click diagnostic for Node.js, Python, Chrome, Git | `synapse-hub doctor` |
| `welcome` | Visual Landing | Launches interactive bilingual landing page in browser | `synapse-hub welcome` |
| `setup` | Project Setup | Bootstraps project, generates AI Guide & AI Bridges | `synapse-hub setup --local-only` |
| `uninstall` | Clean Removal | Cleanly removes AI Bridges, hooks, and local configurations | `synapse-hub uninstall` |
| `sync-rules` | AI Bridge Sync | Synchronizes AGENTS.md rules across all IDE assistants | `synapse-hub sync-rules` |
| `version` | Hub Metadata | Displays installed Hub version and catalog summary | `synapse-hub version` |
| `update` | Auto-Update | 1-click upgrade engine syncing latest upstream changes | `synapse-hub update` |
| `clean` | Artifact Janitor | Cleans up temporary artifacts, cache files, and logs | `synapse-hub clean` |

#### C. Self-Healing, Triage & Token Optimization
| Command | Subsystem | Description | Example |
| :--- | :--- | :--- | :--- |
| `heal` | Semantic Memory | Queries zero-token semantic error memory cache | `synapse-hub heal query "StaleElement"` |
| `auto-heal` | Closed-Loop | Autonomous test healing engine parsing JUnit failures | `synapse-hub auto-heal` |
| `heal-pr` | PR Automator | Creates automated Git branch and PR with healing patch | `synapse-hub heal-pr --branch heal/fix-login` |
| `distill` | Token Optimizer | Filters verbose CLI/Gradle/CI logs by 95% | `synapse-hub distill build.log` |
| `pinpoint-failure` | Failure Autopsy | Parses JUnit XML reports and locates exact failing lines in 0.1s | `synapse-hub pinpoint-failure report.xml` |
| `flaky` | Quarantine | Detects non-deterministic flaky tests and manages quarantine | `synapse-hub flaky --detect` |
| `lookup-tc` | TC Index | Searches test cases by ID, tag, priority, or flow name | `synapse-hub lookup-tc TC-101` |
| `lookup-xpath` | Selector Cache | Queries cached resilient XPath & AOM element locators | `synapse-hub lookup-xpath "Submit"` |
| `impact` | AST Knowledge | Analyzes blast radius of git code changes | `synapse-hub impact --git-diff` |
| `canary` | Resilience Arena | Injects failure vectors to test autonomous recovery MTTR | `synapse-hub canary --run` |
| `report-bug` | Bug Triage | Generates structured Markdown/Jira defect reports from RCA | `synapse-hub report-bug --junit report.xml` |
| `ci-hook` | CI Integration | CI/CD hook executing automated triage on build failure | `synapse-hub ci-hook --log ci.log` |
| `tokens` | Token Counter | Measures prompt tokens across files and subagent contexts | `synapse-hub tokens path/to/prompt.md` |

#### D. API, Performance & Security Testing
| Command | Subsystem | Description | Example |
| :--- | :--- | :--- | :--- |
| `fuzz-api` | Security Fuzzer | Non-production API security, boundary, and chaos fuzzer | `synapse-hub fuzz-api --spec openapi.json` |
| `contract-drift` | Drift Sentinel | Detects breaking changes and schema drift in API specs | `synapse-hub contract-drift --baseline v1.json --current v2.json` |
| `generate-jmx` | Load Testing | Compiles User Story / API specs into Apache JMeter JMX plan | `synapse-hub generate-jmx --threads 50` |
| `analyze-jtl` | Load Analysis | Parses JMeter JTL execution logs and asserts SLA thresholds | `synapse-hub analyze-jtl results.jtl` |
| `analyze-newman` | Postman Audit | Analyzes Newman execution JSON reports for API quality | `synapse-hub analyze-newman newman_run.json` |
| `export-postman` | Collection Gen | Exports API specification into Postman Collection v2.1 | `synapse-hub export-postman --spec swagger.json` |
| `mock-shield` | Route Mocking | Generates Playwright network route mocks from API specs | `synapse-hub mock-shield --spec openapi.json` |
| `skillspector` | AI Security | Audits AI Agent skills and MCP configs for prompt injection | `synapse-hub skillspector --dir .agents/skills` |
| `safety-check` | Firewall Guard | Dry-run code snippet analysis for destructive UI actions | `synapse-hub safety-check --snippet "btn.click()"` |

#### E. Code Generation, Transpilation & Formatting
| Command | Subsystem | Description | Example |
| :--- | :--- | :--- | :--- |
| `generate-tc` | Story Compiler | Compiles natural language user stories into Clean POM test cases | `synapse-hub generate-tc story.md` |
| `export-excel` | Excel Reporter | Converts Markdown test cases to standard 12-column Excel | `synapse-hub export-excel` |
| `gherkin` | BDD Compiler | Compiles Gherkin .feature specs into executable suites | `synapse-hub gherkin specs/checkout.feature` |
| `transpile` | Omni Transpiler | Transpiles test code between Playwright, Pytest, Katalon | `synapse-hub transpile tests/spec.ts --to pytest` |
| `omni-scan` | Engine Scanner | Scans polyglot repositories for test framework presence | `synapse-hub omni-scan` |
| `shard` | Matrix Sharder | Partitions test suites across parallel CI runners | `synapse-hub shard ./tests --runners 4` |
| `visual-mask` | Visual Sentinel | Computes anti-flake coordinate masks for visual testing | `synapse-hub visual-mask screenshot.png` |
| `som` | Vision Testing | Visual Set-of-Marks helper for interactive elements | `synapse-hub som screen.png` |
| `decouple-config`| Config Isolator | Decouples environment variables and credentials from code | `synapse-hub decouple-config config.groovy` |
| `correlate-telemetry` | Correlator | Correlates browser traces, HTTP logs, and server logs | `synapse-hub correlate-telemetry --trace trace.zip` |
| `dashboard` | Project HUD | Generates standalone HTML5 executive health dashboard | `synapse-hub dashboard` |
| `analyze` | Health Audit | Comprehensive 5-in-1 repository health and DoD audit | `synapse-hub analyze` |
| `mcp-serve` | MCP Server | Launches Model Context Protocol (MCP) server over stdio | `synapse-hub mcp-serve` |

---

## 2. Direct Python Scripts Runbook

If running without global package installation, tools can be executed directly via Python:

### 2.1. Verify 9 Quality Gates (Gate 0 - Gate 8)
```bash
# Auto-detect mode (default: detects Hub vs Target Test Project)
python tools/verify_all.py

# Explicit mode selection
python tools/verify_all.py --mode hub      # QA Hub integrity validation
python tools/verify_all.py --mode target   # Target automation suite validation
```
- **Operational Modes:**
  - `--mode hub`: Validates QA Hub assets, skills, tools integrity, zero BOM, path portability, and universal credential security across repository files without requiring target test scripts.
  - `--mode target`: Enforces target automation suite standards including Clean POM across test scripts and credential encryption.
- **Gate 0:** Author Attribution & Provenance Guard (preserves MIT author notice).
- **Gate 1:** 100% UTF-8 No BOM check across all scripts, markdown, and config files.
- **Gate 2:** Path Portability (zero absolute host/machine directory paths).
- **Gate 3:** Clean POM & Flat Architecture (zero raw XPaths/CSS in test scripts).
- **Gate 4:** AI Docs & Artifacts Anti-Drift check (zero hallucinated tools/classes).
- **Gate 5:** Temporary file and properties artifact cleanup.
- **Gate 6:** Credential Security & Secret Scanner (zero hardcoded plaintext passwords or API tokens).
- **Gate 7:** Static Defect & AST Fake-Pass Sentinel.
- **Gate 8:** Syntactic Micro-Mutation Sentinel (Requires Mutation Score >= 80%).

### 2.2. AST Fake-Pass Sentinel
```bash
python tools/infer_linter.py
```

### 2.3. Semantic Memory Cache & Negative Feedback Blacklist
```bash
# Initialize database with seed solutions and forbidden anti-patches
python tools/cache_resolver.py init

# Query pre-tested patches AND retrieve blacklisted anti-patches (0 tokens)
python tools/cache_resolver.py query --error "ElementClickInterceptedException"

# Learn a verified working solution (Positive Memory)
python tools/cache_resolver.py learn --error "Timeout" --cause "Slow API" --patch "waitForNetworkIdle()" --symptom "Spinner"

# Record a failed bug fix attempt into blacklist (Negative Memory)
python tools/cache_resolver.py record-failed --error "StaleElement" --patch "sleep(5000)" --reason "Still fails under network latency"
```

### 2.4. Log Distiller
```bash
python tools/distill_log.py execution.log
```

### 2.5. Technical Debt Harvester
```bash
python tools/debt_harvester.py --scan
python tools/debt_harvester.py --scan ./src --output DEBT_LEDGER.md
```

### 2.6. Senior Code Reviewer (6 Pillars)
```bash
python tools/senior_code_review.py
python tools/senior_code_review.py --staged
```

---

## 3. Standard Exit Code Specification & Terminal Environment

Synapse Hub adheres to deterministic, standardized UNIX exit codes across all CLI tools:

| Exit Code | Constant Name | Description | Typical Remediation |
| :---: | :--- | :--- | :--- |
| **`0`** | `EXIT_SUCCESS` | Operation passed; all Quality Gates satisfied; 0 critical defects. | Proceed to next pipeline stage or commit. |
| **`1`** | `EXIT_FAILURE` | Quality Gate rejection; test execution failure; linter defect found. | Review failing check details; fix unasserted or swallowed code. |
| **`2`** | `EXIT_USAGE_ERROR` | Invalid CLI arguments; unknown subcommand; syntax error. | Check command syntax via `--help`. |
| **`3`** | `EXIT_SECURITY_BLOCK` | Destructive action blocked by safety firewall; secret token leak; MIT license modified. | Review security violation; set `ALLOW_DESTRUCTIVE=1` if intentional. |
| **`4`** | `EXIT_ENVIRONMENT_ERROR` | Incompatible runtime; missing required tool (e.g. Python < 3.9). | Install recommended runtime (Python 3.10+, Node 20+). |

### Terminal Environment Standards:
- **`NO_COLOR` Support:** In accordance with [no-color.org](https://no-color.org), setting the `NO_COLOR` environment variable automatically suppresses all ANSI color escape sequences.
- **`--quiet` / `-q` Flag:** Pass `-q` or `--quiet` to suppress informational banners and output only critical verdicts or machine-readable results.
- **Machine-Readable Formats:** Use `--format json`, `--format sarif`, or `--format junit` for clean, parseable pipeline outputs.
