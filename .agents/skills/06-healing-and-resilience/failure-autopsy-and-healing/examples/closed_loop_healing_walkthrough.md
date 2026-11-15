# Closed-Loop Failure Autopsy & Autonomous Healing Walkthrough

> **Scenario:** End-to-end checkout test fails in CI runner due to locator drift on the order confirmation button.

---

## 1. Fast Failure Pinpoint (0.1s from JUnit XML)

```bash
python tools/pinpoint_failure.py Reports/junit.xml
```

**Diagnostic Output:**
```text
❌ Failing Test Case : Tests/E2E_Checkout_Order.ts:42
📍 Failing Line      : await page.locator("button#submit-v2").click()
⚠️ Exception Caught  : TimeoutError: locator.click: Timeout 5000ms exceeded waiting for locator("button#submit-v2")
```

---

## 2. Reflexion Verbal Diagnosis & AOM Heuristic Match

The Failure Analyst initiates reflection:
- **Reflexion:** *"Static ID selector `#submit-v2` did not appear within timeout window. Adjustment: Fallback to Accessibility role/name or dynamic data-testid."*
- **Heuristic Matcher:** Layer 1 semantic matching finds live element matching role `button` with label `"Confirm Order"`.

---

## 3. Autonomous Patch Synthesis & Verification

`pom-crafter` applies the surgical patch to `CheckoutPage.ts`:
```diff
- await page.locator("button#submit-v2").click();
+ await page.getByRole("button", name: "Confirm Order").click();
+ await page.waitForLoadState("networkidle");
```

Targeted re-test:
```bash
python tools/auto_heal.py --execute --target-test "Tests/E2E_Checkout_Order.ts"
```

**Verdict:**
```text
✅ [TRIAL 1 SUCCESS] Patch verified passing in 1.4s!
💾 Recorded 2-line practical lesson to SQLite episodic memory.
```
