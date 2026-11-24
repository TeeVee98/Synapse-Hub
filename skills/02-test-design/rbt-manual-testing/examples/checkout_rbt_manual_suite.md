# Example AI-RBT Manual Test Suite: E-Commerce Checkout

## 1. Risk Assessment Matrix (P x I)

| Feature / Journey | Probability (1-5) | Impact (1-5) | Risk Score (P x I) | Tier | Testing Focus |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Payment Gateway Integration (Stripe/PayPal) | 4 | 5 | 20 | Critical (P1) | Idempotency, 3D Secure, Network timeout, Webhook retry |
| Promo Code & Discount Application | 3 | 4 | 12 | High (P2) | Boundary dates, Concurrent usage, Negative cart values |
| Shipping Address Form & Validation | 2 | 3 | 6 | Medium (P3) | XSS, Max length, International postal formats |

## 2. Requirement Clarification & Ambiguity Log

| ID | Ambiguity / Gap | Question to Product Owner | Impact / Default Assumption |
| :--- | :--- | :--- | :--- |
| AMB-01 | Discount expiration timezone not specified | Does promo code expire at 23:59 UTC or local user time? | Assumed UTC midnight to prevent premature expiration errors. |
| AMB-02 | Handling partial payment failure during multi-card checkout | Should the entire order roll back or allow secondary payment? | Assumed atomic rollback: no charge without full authorization. |

## 3. Comprehensive Manual Test Case Matrix (ISO 29119-3 12-Column Standard)

| TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TC-CHK-001` | Checkout | Critical (P1) | Successful Credit Card payment with 3DS authorization | User logged in, Cart has 1 item ($45.00), at /checkout URL | 1. Navigate to /checkout<br>2. Fill shipping details<br>3. Enter 3DS test card<br>4. Click 'Place Order'<br>5. Authorize OTP popup with code 123456 | Order confirmed with HTTP 200, confirmation page shows unique Order ID #ORD-9281, receipt email queued, cart emptied (badge count = 0) | Critical | Card: `4000001234567890`, Exp: `12/28`, CVC: `123`, OTP: `123456` | Yes | E2E Playwright | `@E2E`, `@Payment`, `@3DS` |
| `TC-CHK-002` | Checkout | Critical (P1) | Idempotency under double-submit click on 'Place Order' | User on final payment step with valid payment details pre-filled | 1. Rapidly double-click 'Place Order' button within 100ms | Button enters disabled state on first click; exactly 1 payment transaction charged, duplicate transaction rejected with HTTP 409 or ignored via Idempotency-Key | Critical | Idempotency-Key: `uuid-v4-9812-adfe`, Cart Total: `$45.00` | Yes | API / E2E | `@Security`, `@Concurrency`, `@Idempotency` |
| `TC-CHK-003` | Checkout | High (P2) | Expired coupon code validation | User on payment step with $100.00 cart value | 1. Enter coupon code `SUMMER2020`<br>2. Click 'Apply Coupon' button | Inline error displayed: 'Mã giảm giá đã hết hạn sử dụng', cart total remains exactly $100.00 without discount deduction | High | Coupon: `SUMMER2020` (Expired: `2020-08-31`) | Yes | UI Functional | `@Regression`, `@PromoCode` |
| `TC-CHK-004` | Checkout | Medium (P3) | XSS payload injection in Delivery Instructions field | User on shipping step, Delivery Instructions field visible | 1. Enter payload `<script>alert('xss')</script>` in Delivery Instructions<br>2. Complete order submission<br>3. Navigate to order history details page | Payload safely HTML-escaped as literal text; zero script execution, CSP policy blocks inline script eval | Medium | Delivery Instructions: `<script>alert('xss')</script>` | Yes | Security / DAST | `@Security`, `@XSS`, `@Sanitization` |
