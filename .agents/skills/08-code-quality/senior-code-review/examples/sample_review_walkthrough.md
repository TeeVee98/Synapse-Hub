# Sample Senior Code Review Walkthrough

Below is a representative senior code review performed on an API and test diff.

```markdown
# Senior Developer Quality & Lean Code Review

- **Files Changed:** `3`
- **Findings:** `2` (1 Must fix, 1 Should fix, 0 Nice to have)

### 🚨 Must Fix (Blockers)

#### 1. Swallowed Database Exception (`src/services/billing.py:84`)
- **What this is:** Try-catch block around payment transaction commit.
- **Problem:** When the gateway returns a network error, the exception is caught with `pass`, silently failing the invoice without alerting the user or reverting the database transaction.
- **Fix:** Rethrow `PaymentGatewayException` and rollback the active DB transaction.
- **If we skip it:** Invoices will appear as paid in UI while payments actually failed.

### ⚠️ Should Fix (Reliability & Scale)

#### 2. Static Sleep in Async Test (`tests/test_billing.py:32`)
- **What this is:** `time.sleep(3)` placed after dispatching webhook.
- **Problem:** Static wait causes test flakiness on slower CI runners and wastes 3 seconds on fast local runs.
- **Fix:** Replace with `await waitForCondition(isWebhookReceived, timeout=5000)`.
- **If we skip it:** CI pipeline will intermittently fail on high queue load.

### Verdict
❌ **Action Required:** Resolve 1 blocker before merging.
```
