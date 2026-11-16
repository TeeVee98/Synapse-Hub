# Field-Level Validation Checklist (15 Input Field Types)

Comprehensive boundary values, negative test vectors, and security edge cases across all standard web and enterprise input fields.

## 15-Field Matrix

| Field Type | Positive Verification | Boundary & Negative Checks (BVA) | Security & Edge Cases |
| :--- | :--- | :--- | :--- |
| **1. Text (Name, Title)** | Valid length, Unicode support | Empty, leading/trailing whitespace, `Max`, `Max+1` | XSS `<script>`, SQLi `' OR 1=1--`, HTML tags, surrogate emojis |
| **2. Email** | Standard format (`user@domain.com`) | Missing `@`, missing TLD, multiple `@`, spaces | Max 254 characters, Internationalized Domain Names (IDN) |
| **3. Phone** | Standard E.164 or national format | Letters, symbols, too short/long, negative numbers | Leading `+`, spaces, dashes, country code mismatches |
| **4. Password** | Complexity requirements met (Upper, lower, digit, symbol) | Missing criteria, `Min-1`, excessive length | Spaces in password, clipboard paste blocking/support |
| **5. Number (Quantity, Price)** | Integer/float within valid range | Alpha chars, negative values, 0 (if disallowed), decimals | Integer overflow (> 2^31-1), thousands separator formats |
| **6. Date / Datetime** | Valid date format (`YYYY-MM-DD` / `DD/MM/YYYY`) | Invalid calendar dates (Feb 30), leap year checks | Past vs future boundary restrictions, manual input vs picker |
| **7. Date Range** | `StartDate <= EndDate` | `StartDate > EndDate`, single date selected | Same-day range, date span exceeding system max limit |
| **8. Dropdown / Select** | Select valid option, search filter | Unselected mandatory field, empty options list | Async loading delays, large option lists (> 1,000 items) |
| **9. Multi-Select** | Select multiple items, deselect individual | Exceeding max selection limit, Select All | Search filter within list, badge dismissal ("x" click) |
| **10. Checkbox / Radio** | Toggle check/uncheck, switch radio option | Unchecked mandatory consent (Terms of Service) | Rapid toggle spam, disabled read-only state |
| **11. Textarea (Notes, Bio)** | Multi-line text with line breaks | Exceeding character limit, whitespace-only input | Control characters (CRLF, tabs), rich-text paste injection |
| **12. File Upload** | Allowed file format & size limits | Disallowed extension (`.exe`), 0-byte file, oversized file | Special characters in filename, mime-type spoofing |
| **13. OTP / MFA Code** | Valid unexpired code entry | Invalid code, expired code, partial length | Rate limiting (max attempts), resend cooldown timer |
| **14. Range Slider** | Drag slider between Min and Max | Snap-to values, boundary values (`Min`, `Max`) | Keyboard navigation (Arrow keys, Home, End, PageUp/Down) |
| **15. Rich Text Editor** | Bold, italic, bullet lists formatting | Image paste, rich content pasted from external apps | Dangerous HTML tags sanitization, raw character count |

## Non-Functional & Resilience Invariants

### 1. Concurrency & Race Condition Verification
- **Double Submit / Rapid Click:** Trigger submit/pay/create twice within <300ms (UI click or duplicate POST) -> verify only 1 record/charge is created and button disables or backend rejects duplicate.
- **Resource Contention (Last-Item / Overselling):** Two concurrent sessions claim the last available stock/slot/voucher at the exact same timestamp -> verify exactly 1 succeeds and 1 receives a clear conflict error (`409 Conflict` / out-of-stock message), with zero negative balance/stock.
- **Stale State / Optimistic Locking:** User A and User B open the same record; User A saves first, then User B saves outdated data -> verify system blocks silent overwrite (version/ETag check) or prompts merge/refresh.
- **Retry & Idempotency:** Simulate network timeout after server commits, then retry with the same `Idempotency-Key` -> verify server returns the original result without creating duplicate records.

### 2. Data Integrity & Database Safety
- **Atomicity & Rollback:** Simulate a failure mid-transaction (e.g., balance deducted / stock decremented, then order creation fails) -> verify full DB rollback with zero orphaned records or balance drift.
- **3-Tier Consistency (UI ↔ API ↔ DB):** After save/update, reload UI (F5), call GET API, and verify DB state -> confirm 100% match across UTF-8 Vietnamese text, currency rounding, and timezone formatting.
- **Referential Integrity / Soft Delete:** Delete or archive a parent record referenced by child data (e.g., product linked to existing orders) -> verify historical child records remain intact and render without errors.
- **Partial Update Safety & Audit Trail:** Update a single field (e.g., display name) -> verify unrelated fields are not wiped/reset (`PATCH` vs `PUT`), `created_at` stays immutable, and `updated_at` / audit log updates accurately.

### 3. Network & Session Resilience
- **Network Interruption:** Connection drops mid-transaction; slow 3G timeout handling.
- **Browser Navigation:** Browser Back/Forward or page refresh during multi-step wizards without data loss.
