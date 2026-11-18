---
name: canary-watch
description: >
  Post-deploy canary monitoring skill: define, run, and gate synthetic smoke checks
  against production or staging endpoints immediately after deployment. Use to catch
  regressions before real user traffic is affected.
version: 1.0.0
attribution: Adapted from ECC (affaan-m/ecc, Apache 2.0). Extended by Thế Vị (@TeeVee98).
---

# Canary Watch Skill (`canary-watch`)

## Overview

A canary check is a lightweight, targeted synthetic probe executed **immediately after deployment**, before traffic is shifted. If any canary fails, the deployment is auto-rolled back or held at the previous version.

> [!IMPORTANT]
> Canary checks are not a replacement for load testing or full E2E regression suites.
> They are the first-line fast-fail gate (< 30s total) for deployment safety.

## When to Activate

- After every production or staging deployment (CI/CD gate).
- When a hotfix is deployed and full E2E would take too long.
- As a liveness probe in blue-green or canary traffic-shifting deployments.
- Validating that a new microservice replica is healthy before receiving traffic.

## Canary Check Categories

| Category | SLA | Description |
|----------|-----|-------------|
| Health endpoint | < 500ms | `GET /health` or `/ping` returns 200 |
| Auth smoke | < 1s | Login flow returns valid session token |
| Critical read | < 1s | Key read path returns expected data shape |
| Write smoke | < 2s | A sentinel write completes and is verifiable |
| Dependency probe | < 1s | DB, cache, and queue connectivity verified |

## Implementation Template

```python
# tools/orchestration/canary_watch.py
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98)
# SPDX-License-Identifier: MIT
"""Lightweight post-deploy canary smoke verifier."""

from __future__ import annotations
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import List, Callable


@dataclass
class CanaryCheck:
    name: str
    fn: Callable[[], bool]
    sla_ms: int = 2000


def http_ok(url: str, timeout: int = 5) -> bool:
    """Returns True if URL responds with 2xx within timeout."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, OSError):
        return False


def run_canaries(checks: List[CanaryCheck]) -> bool:
    """Run all canary checks. Returns True only if ALL pass within SLA."""
    all_passed = True
    for check in checks:
        start = time.monotonic()
        passed = check.fn()
        elapsed_ms = int((time.monotonic() - start) * 1000)
        sla_ok = elapsed_ms <= check.sla_ms
        status = "PASS" if (passed and sla_ok) else "FAIL"
        print(f"[{status}] {check.name}: {elapsed_ms}ms (SLA: {check.sla_ms}ms)")
        if not (passed and sla_ok):
            all_passed = False
    return all_passed


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000"
    checks = [
        CanaryCheck("health-endpoint", lambda: http_ok(f"{base_url}/health"), sla_ms=500),
        CanaryCheck("readiness-endpoint", lambda: http_ok(f"{base_url}/ready"), sla_ms=500),
    ]
    success = run_canaries(checks)
    sys.exit(0 if success else 1)
```

## CI/CD Integration

```yaml
# .github/workflows/deploy.yml
- name: Canary Watch
  run: python tools/orchestration/canary_watch.py ${{ env.DEPLOY_URL }}
  timeout-minutes: 2
  # Fail the deployment pipeline immediately on any canary failure
```

## Rollback Trigger

If `canary_watch.py` exits with code `1`:
1. Trigger rollback: redeploy previous stable image tag.
2. Alert on-call channel with canary failure details.
3. Lock the failing deployment from receiving further traffic.
4. File an autopsy issue with `tools/report/pinpoint_failure.py` output.

## Non-Goals

- Canary checks are **not** load tests (use k6 for performance validation).
- Do not add more than 10 canary checks per deployment (keep total runtime < 30s).
- Do not use canary checks as a substitute for pre-merge integration tests.
