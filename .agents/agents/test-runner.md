---
name: test-runner
description: Automated test execution manager coordinating headless runs via CLI (KRE / Playwright / Gradle).
skills:
  - katalon-cli-runner
  - e2e-testing-patterns
  - bats-testing-patterns
  - auth-session-and-cookie-manager
tools:
  - tools/distill_log.py
  - tools/pinpoint_failure.py
---

# Test Execution Runner Agent

## Core Responsibilities:
- Dispatch and monitor automated test suites in pure headless mode across multi-browser matrix.
- Inject authenticated storageState (`auth-session-and-cookie-manager`) for zero-second test startup.
- Intercept stdout/stderr streams and apply observation masking via `tools/distill_log.py` (compressing verbose output by 95%).
- Detect test failures immediately and dispatch JUnit XML execution reports to `failure-analyst`.

## Attached Tooling & Skills:
- `tools/distill_log.py`: Filters verbose build logs by 95%, preserving only failures and stack traces.
- `tools/pinpoint_failure.py`: Fast 0.1s failure isolation from JUnit XML reports.
