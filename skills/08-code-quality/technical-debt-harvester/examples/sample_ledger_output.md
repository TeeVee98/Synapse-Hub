# Sample Technical Debt Ledger

## Example Output
```markdown
# Technical Debt & Shortcut Ledger

> **Ledger Policy:** Deliberate shortcuts prevent over-engineering. Track limits and upgrade triggers so they never rot silently into permanent defects.

- **Repository:** `OrderService`
- **Total Shortcuts:** `2`
- **Missing Upgrade Triggers:** `0` ✅ *(All tracked)*

---

### Tracked Shortcuts
1. `src/services/OrderProcessor.groovy:45`
   - *Shortcut:* In-memory map cache
   - *Ceiling:* 10,000 active orders
   - *Upgrade Trigger:* Migrate to Redis when daily active orders > 10,000
```
