# Sample Technical Debt Ledger

Representative output from `agent-qa debt`:

```markdown
# Technical Debt & Shortcut Ledger

> **Ledger Policy:** Deliberate shortcuts prevent over-engineering. Track limits and upgrade triggers so they never rot silently into permanent defects.

- **Repository:** `order-service`
- **Total Shortcuts:** `3`
- **Missing Upgrade Triggers:** `1` ⚠️ *(Action Required)*

---

| Location | Description | Ceiling (Limit) | Upgrade Trigger | Status |
| :--- | :--- | :--- | :--- | :--- |
| `src/cache.py:24` | In-memory Python dictionary cache | 1,000 active sessions | Migrate to Redis when worker count > 2 | ✅ Tracked |
| `src/auth.py:89` | Synchronous token verification | Max 50 req/sec | Switch to async JWKS cache under high load | ✅ Tracked |
| `src/pdf.py:14` | Hardcoded paper margin 10px | Not specified | None | ⚠️ `no-trigger` |

### Recommended Action
1. Review the `1` shortcut tagged `no-trigger` above and define concrete upgrade conditions.
2. Run `agent-qa debt` in CI to monitor debt accumulation.
```
