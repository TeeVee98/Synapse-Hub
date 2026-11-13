# Sample Repo Quality Audit Walkthrough

## Overview
This walkthrough demonstrates a repo-wide quality audit identifying high-impact risks with "Fix this first" prioritization.

## Example Command
```bash
agent-qa audit . --output REPO_QUALITY_AUDIT.md
```

## Sample Output Findings
1. **Critical:** In-memory queue without persistent backoff under concurrent load (`WorkerPool.groovy:142`).
   - *Fix:* Introduce Redis-backed queue or bounded worker pool.
2. **Medium:** Unbounded mock API responses causing potential memory bloat (`MockServer.groovy:89`).
   - *Fix:* Enforce pagination or bounded payload limits.
