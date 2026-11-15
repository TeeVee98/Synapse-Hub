# Example: Meta-Prompt Crafter Output Template

> This example demonstrates the 7-Part Production Prompt synthesized from a rough human request:  
> *"Write a prompt for Claude to generate edge-case test data for a payment checkout form."*

---

## Synthesized Prompt for Claude 3.5 Sonnet / ChatGPT

```markdown
You are a Principal QA Automation Engineer and Security Specialist with 10+ years of experience in financial technology and PCI-DSS compliance.

### Context & Goal
I am building and testing an enterprise checkout flow. The application processes credit card payments, digital wallets, and promotional discount codes. I need a comprehensive matrix of synthetic test data targeting boundary conditions and security invariants.

### Instructions & Tasks
1. Generate test cases covering the following input fields:
   - Cardholder Name (Unicode, accents, SQLi, XSS vectors, max-length 100 chars)
   - Credit Card Number (Valid Luhn test numbers, invalid lengths, expired prefixes, expired test cards)
   - Expiration Date (Past dates, current month boundary, invalid months 13/26, 5+ years in future)
   - CVV/CVC (3-digit Visa/MC, 4-digit Amex, non-numeric strings, injection payloads)
   - Billing Zip / Postal Code (US 5-digit, ZIP+4, alphanumeric UK/Canada, SQL injection)

2. For each test vector, provide:
   - `Field`: The target input under test
   - `Test Vector Value`: The exact literal value to inject
   - `Category`: [Positive Boundary | Negative Boundary | Security / Sanitization | Malformed]
   - `Expected Behavior`: Exact HTTP response code or UI error message expected
   - `Risk Justification`: Why this edge case breaks typical frontend or backend validation

### Constraints & Invariants
- DO NOT use real customer data or live credit card numbers. Use only standardized test ranges (e.g., Stripe / PayPal sandbox test cards).
- Format the response as a clean Markdown table.
- Do not abbreviate or use `// ...` placeholders.
```
