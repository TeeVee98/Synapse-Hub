# Sample Spec Review (Goldfish Protocol)

Representative output of `python tools/goldfish_review.py` evaluating a draft specification for an e-commerce checkout flow.

```markdown
# 🔍 Goldfish Specification Review Report
Target Spec: `specs/checkout_flow.md`
Timestamp: 2026-11-04 15:30:00

## Scorecard: 85/100 (APPROVED)

1. Comprehension & System Boundaries: 20/20
   - Actor: Authenticated Buyer.
   - Preconditions: Active cart with >= 1 item, valid shipping address.
   - Target Scope: Payment step through Order Confirmation modal.

2. Dynamic Data & Idempotent Teardown: 18/20
   - Dynamic order ID with `AUTO_${Date.now()}`.
   - Teardown: DB order status updated to `CANCELLED_TEST` via API hook.

3. Assertion Rigor: 22/25
   - Explicit confirmation message and total amount match.
   - Anti-Fake Pass check: database order record mutation verified.

4. Boundary & Negative Scenarios: 15/20
   - Invalid credit card number and expired CVV covered.
   - Recommendation: Add test case for network timeout during 3D Secure redirect.

5. Implementation Target: 10/15
   - Target Page: `CheckoutPage.ts`, `OrderConfirmationPage.ts`.

Verdict: PASS (Ready for POM Codification)
```
