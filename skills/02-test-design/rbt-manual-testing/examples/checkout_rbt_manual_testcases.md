<!-- synapse-linter-profile: auth-payment -->
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
| `TC-CHK-005` | Checkout | High (P2) | Browser Interrupt & UI Latency resilience during payment gateway redirect | User in checkout flow redirecting to 3DS payment gateway | 1. Simulate Slow 3G network latency (3000ms delay)<br>2. Click 'Place Order'<br>3. Immediately press browser Back or F5 refresh while redirect is pending | Button shows loading indicator and disabled state; transaction remains in 'Pending' state for safe reconcile without duplicate charge or page crash | High | Network: Slow 3G latency (3000ms delay) | Yes | E2E Playwright | `@Security`, `@Resilience`, `@Latency`, `@BrowserInterrupt` |
| `TC-CHK-006` | Checkout | Medium (P3) | Whitespace-only string rejection and leading/trailing whitespace trim validation | User on shipping & payment details step | 1. Enter whitespace-only string '   ' into required Delivery Instructions<br>2. Enter promo code with leading and trailing spaces '  SAVE20  '<br>3. Submit form | Whitespace-only string rejected with validation error; promo code automatically trimmed before validation | Medium | Instructions: `   `, Promo: `  SAVE20  ` | Yes | UI Validation | `@Boundary`, `@Whitespace`, `@Trim` |
