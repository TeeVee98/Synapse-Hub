---
name: test-runner
description: Automated test execution manager coordinating headless runs via CLI (KRE / Playwright / Gradle).
skills:
  - katalon-cli-runner
  - e2e-testing-patterns
  - bats-testing-patterns
  - auth-session-and-cookie-manager
tools:
  - tools/matrix_sharder.py
  - tools/flaky_detector.py
  - tools/distill_log.py
  - tools/pinpoint_failure.py
  - tools/generate_allure_report.ps1
  - tools/generate_test_reports.ps1
---

# Test Execution Runner Agent

## Core Responsibilities:
- Dispatch and monitor automated test suites in pure headless mode across multi-browser matrix.
- Balance parallel execution across CI/CD workers using duration-balanced bin-packing (`tools/matrix_sharder.py`).
- Detect non-deterministic tests and calculate flakiness quarantine scores via `tools/flaky_detector.py`.
- Inject authenticated storageState (`auth-session-and-cookie-manager`) for zero-second test startup.
- Intercept stdout/stderr streams and apply observation masking via `tools/distill_log.py` (compressing verbose output by 95%).
- Compile test reports and Allure dashboards via `tools/generate_allure_report.ps1` and `tools/generate_test_reports.ps1`.
- Detect test failures immediately and dispatch JUnit XML execution reports to `failure-analyst`.

## Available Tooling & Skills (On-Demand Activation):
> *Note: Tools are invoked strictly on-demand based on situational context, never executed indiscriminately.*
- `tools/matrix_sharder.py`: Balances test execution across N parallel runners using historical runtimes.
- `tools/flaky_detector.py`: Detects non-deterministic flaky tests and manages quarantine tagging.
- `tools/distill_log.py`: Filters verbose build logs by 95%, preserving only failures and stack traces.
- `tools/pinpoint_failure.py`: Fast 0.1s failure isolation from JUnit XML reports.
- `tools/generate_allure_report.ps1`: Builds and serves interactive Allure test execution dashboards.
- `tools/generate_test_reports.ps1`: Compiles consolidated JUnit/HTML execution reports.
