# Technical Debt & Shortcut Ledger

> **Ledger Policy:** Deliberate shortcuts prevent over-engineering. Track limits and upgrade triggers so they never rot silently into permanent defects.

- **Repository:** `.`
- **Total Shortcuts:** `6`
- **Missing Upgrade Triggers:** `0` ✅ *(All tracked)*

---

| Location | Description | Ceiling (Limit) | Upgrade Trigger | Owner | SLA | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `tests/test_debt_harvester.py:43` | simple dict cache | 100 items | migrate to Redis when OOM\n") | @TeeVee98 (Core Hub) | v4.1.0-Sprint | ✅ Tracked |
| `tests/test_debt_harvester.py:48` | skip token refresh |  | auth fails 401\n") | @TeeVee98 (Core Hub) | v4.1.0-Sprint | ✅ Tracked |
| `tests/test_debt_harvester.py:53` | unindexed scan | 500 rows | add index on created_at\n") | @TeeVee98 (Core Hub) | v4.1.0-Sprint | ✅ Tracked |
| `tests/test_synapse_observer.py:120` | Skip regex validation for speed | upgrade when scaling" | upgrade when scaling" | @TeeVee98 (Core Hub) | v4.1.0-Sprint | ✅ Tracked |
| `tests/test_synapse_observer.py:127` | temporary sleep in tests | test suite | when migrating to dynamic wait" | @TeeVee98 (Core Hub) | v4.1.0-Sprint | ✅ Tracked |
| `tests/test_synapse_observer.py:128` | hardcoded api token | test mock | when testing auth integration" | @TeeVee98 (Core Hub) | v4.1.0-Sprint | ✅ Tracked |

### Recommended Action
1. All tracked shortcuts have defined upgrade boundaries. Review them during sprint refactoring cycles.
2. Run `agent-qa debt` in CI to monitor debt accumulation.