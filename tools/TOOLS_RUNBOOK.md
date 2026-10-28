# TOOLS RUNBOOK — Automated Tools Handbook for AI Agents

> **Standard reference guide for AI Agents (Google Antigravity, Cursor, Claude Code, Windsurf)**  
> Every script in the `tools/` directory has an explicit purpose, CLI syntax, and mandatory dispatch trigger. Guessing syntax is strictly prohibited.

---

## 1. SITUATIONAL TOOL DISPATCH MATRIX

| Practical Agent Context | Required Tool | Typical Execution Command |
| :--- | :--- | :--- |
| **Starting task / Querying Page Class methods** | `tools/repo_map.py` | `python tools/repo_map.py` (Reads `tools/repo_map.txt`) |
| **Pre-Commit / Completing Task** | `tools/verify_all.py` | `python tools/verify_all.py` |
| **After creating/editing Test Script (Fake-Pass scan)**| `tools/infer_linter.py` | `python tools/infer_linter.py` |
| **After modifying Page Class (Impact Analysis)** | `tools/test_impact.py` | `python tools/test_impact.py --git-diff` |
| **When Test FAILS (Pinpoint line & error in 0.1s)** | `tools/pinpoint_failure.py` | `python tools/pinpoint_failure.py` |
| **When CLI/Gradle logs are verbose (Observation Masking)**| `tools/distill_log.py` | `python tools/distill_log.py <path_to_log>` |
| **When encountering UI error / Overlay / Stale Element**| `tools/cache_resolver.py` | `python tools/cache_resolver.py query "<error_msg>"` |
| **Generating test scripts from Natural Language Story** | `tools/generate_tc_from_story.py`| `python tools/generate_tc_from_story.py "<story>"` |
| **Generating E2E matrix from OpenAPI/Swagger** | `tools/generate_api_matrix.py` | `python tools/generate_api_matrix.py --spec <swagger.json>` |
| **Auditing Web Accessibility (WCAG 2.2)** | `tools/wcag_audit.py` | `python tools/wcag_audit.py <path_to_html_or_url>` |
| **Checking DB data leaks (Taint Analysis)** | `tools/trace_data_flow.py` | `python tools/trace_data_flow.py` |
| **Detecting Canvas / GIS Map visual regression** | `tools/visual_diff_canvas.py` | `python tools/visual_diff_canvas.py --baseline <b> --actual <a>` |
| **Canary Self-Healing Audit** | `tools/agent_canary.py` | `python tools/agent_canary.py --run` |
| **Lookup XPath Locator in cached memory** | `tools/lookup_xpath.py` | `python tools/lookup_xpath.py "<keyword>"` |
| **Lookup Test Case metadata** | `tools/lookup_tc.py` | `python tools/lookup_tc.py "<keyword_or_id>"` |
| **Linting Markdown documentation quality** | `tools/lint_ai_docs.py` | `python tools/lint_ai_docs.py` |

---

## 2. DETAILED TOOL USAGE

### 1. `tools/generate_api_matrix.py`
- **Purpose:** Ingests OpenAPI / Swagger JSON schemas and automatically computes comprehensive E2E test matrices: Positive, Boundary Value (min/max length, special characters, XSS payloads), and Negative (invalid types, missing required fields).
- **CLI Syntax:**
  ```bash
  # Generate Markdown matrix
  python tools/generate_api_matrix.py --spec path/to/swagger.json --format md -o api_matrix.md

  # Generate JSON matrix
  python tools/generate_api_matrix.py --spec path/to/swagger.json --format json -o api_matrix.json

  # Generate sample matrix using built-in schema
  python tools/generate_api_matrix.py --sample
  ```

---

### 2. `tools/wcag_audit.py`
- **Purpose:** Automated Web Accessibility auditor checking WCAG 2.2 Level A and AA criteria (missing alt tags, unlabeled form controls, table header structure, heading hierarchy gaps H1-H6, empty action buttons).
- **CLI Syntax:**
  ```bash
  # Audit local HTML snapshot
  python tools/wcag_audit.py path/to/page.html -o wcag_report.md

  # Audit live URL directly
  python tools/wcag_audit.py https://staging.example.com/dashboard --url -o wcag_report.md
  ```

---

### 3. `tools/verify_all.py`
- **Purpose:** Supreme Definition of Done (DoD) verification gate running all 7 Quality Gates prior to completing tasks or git commits.
- **CLI Syntax:**
  ```bash
  python tools/verify_all.py
  ```

---

### 4. `tools/infer_linter.py`
- **Purpose:** AST static code analyzer detecting Fake-Pass anti-patterns (test cases without assertions or containing empty try-catch blocks swallowing errors).
- **CLI Syntax:**
  ```bash
  python tools/infer_linter.py
  ```

---

### 5. `tools/test_impact.py`
- **Purpose:** Analyzes `git diff` against codebase dependency graphs to identify the exact subset of affected test cases, preventing redundant suite execution.
- **CLI Syntax:**
  ```bash
  python tools/test_impact.py --git-diff
  ```

---

### 6. `tools/pinpoint_failure.py`
- **Purpose:** Extracts failing line numbers, exception names, and stack traces from JUnit XML reports in 0.1s without opening heavy files.
- **CLI Syntax:**
  ```bash
  python tools/pinpoint_failure.py
  ```

---

### 7. `tools/distill_log.py`
- **Purpose:** Distills verbose CLI / KRE / Gradle logs by 95%, extracting only actionable exceptions, failing lines, and file pointers to prevent token degradation.
- **CLI Syntax:**
  ```bash
  python tools/distill_log.py path/to/execution.log
  ```

---

### 8. `tools/cache_resolver.py`
- **Purpose:** Queries SQLite error cache (`tools/memory_cache.db`) via cosine similarity or pattern match for 0-token instant defect resolution.
- **CLI Syntax:**
  ```bash
  python tools/cache_resolver.py query "ElementClickInterceptedException"
  python tools/cache_resolver.py add --pattern "Timeout waiting for primeNG" --fix "BasePage.waitForAngular()"
  ```

---

### 9. `tools/generate_tc_from_story.py`
- **Purpose:** Large Action Model (LAM) parser converting natural language acceptance criteria into Clean POM script scaffolds.
- **CLI Syntax:**
  ```bash
  python tools/generate_tc_from_story.py "User navigates to login, inputs valid credentials, and verifies dashboard table loaded"
  ```

---

### 10. `tools/visual_diff_canvas.py`
- **Purpose:** Pixel-level and SSIM perceptual comparison for GIS / Canvas elements lacking standard DOM locators.
- **CLI Syntax:**
  ```bash
  python tools/visual_diff_canvas.py --baseline baseline.png --actual actual.png --diff diff.png
  ```
