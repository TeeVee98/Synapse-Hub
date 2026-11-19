# Field-Level Validation Checklist (25 Input Field Types) & Resilience Protocols

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.  
> **Standard Compliance:** Aligned with **ISO/IEC/IEEE 29119-4** (Test Techniques), **ISTQB CTAL-TAE v2.0**, and **OWASP ASVS v4.0 / Web Security Testing Guide (WSTG)**.

Comprehensive boundary values, 3-value Boundary Value Analysis (BVA), negative test vectors, security edge cases, and non-functional resilience protocols across all standard web, mobile, and enterprise input fields.

---

## 1. 25-Field Validation Matrix

| # | Field Type | Positive Verification | Boundary & Negative Checks (3-Value BVA) | Security, Injection & Enterprise Edge Cases |
| :- | :--- | :--- | :--- | :--- |
| **1** | **Text (Name, Title)** | Valid length, Unicode support (Vietnamese accented), allowed special chars (`-`, `.`) | Empty, whitespace-only, `Min-1`, `Min`, `Min+1`, `Max-1`, `Max`, `Max+1` | XSS `<script>`, SQLi `' OR 1=1--`, HTML tags, surrogate emojis (4-byte), NFC/NFD Unicode normalization drift |
| **2** | **Email** | Standard format (`user@domain.com`), subdomains, tagged alias (`user+tag@domain.com`) | Missing `@`, missing domain, multiple `@`, trailing spaces, `Min-1`, `Max 254 chars`, `255 chars` | SQLi in local part, header injection (`\r\nBcc:`), Internationalized Domain Names (IDN/Punycode), display spoofing |
| **3** | **Phone** | E.164 (`+84901234567`), national formats with spaces/dashes, extension | Alpha characters, symbols, too short (`Min-1`), too long (`Max+1`), all zeros (`0000000000`) | Leading `+` handling, country code mismatch, virtual VoIP numbers, script injection via SMS payload |
| **4** | **Password** | Complexity met (Upper, lower, digit, special character), passphrase | Missing 1 criteria, `Min-1`, `Min`, `Max-1`, `Max`, `Max+1`, common dictionary passwords | Whitespace handling (leading/trailing vs internal), clipboard paste support/blocking, shoulder-surfing masking toggle |
| **5** | **Number (Quantity, Price)** | Valid integer/float, decimals within precision limit | Alpha chars, negative numbers, `0` (if disallowed), decimals on integer-only, `Min-1`, `Max+1` | Integer overflow (> 2^31-1 or > 2^53-1 in JS), scientific notation (`1e6`), localized thousand separators (`1,000.00` vs `1.000,00`) |
| **6** | **Date / Datetime** | Valid date format (`YYYY-MM-DD`, `DD/MM/YYYY`), manual typing & picker | Invalid calendar dates (Feb 29 non-leap year, Feb 30, April 31), format mismatch, partial entry | Historical epoch boundary (1970-01-01), Year 2038 problem (Unix 32-bit), client vs server timezone drift, daylight saving shift |
| **7** | **Date Range** | `StartDate <= EndDate`, single-day range | `StartDate > EndDate`, single date missing, date span exceeding system max limit (e.g. > 90 days) | Leap day spans, overlapping date bookings, retroactive date entry on immutable periods |
| **8** | **Dropdown / Select** | Select valid option, search filter within dropdown | Unselected mandatory field, disabled options selected via keyboard | Async loading delays (stale options), large option lists (> 10,000 items), tamper option value via DevTools inspection |
| **9** | **Multi-Select** | Select multiple items, deselect individual, reorder | Exceeding max selection limit, 0 items selected on mandatory, Select All on massive sets | Search filter desynchronization, badge dismissal ("x" click) focus trap, duplicate selection payload injection |
| **10** | **Checkbox / Radio** | Toggle check/uncheck, switch radio option group | Mandatory consent unchecked (Terms of Service), radio group with no option selected | Rapid toggle spam (<100ms), disabled read-only state tampering, conflicting mutual exclusions |
| **11** | **Textarea (Notes, Bio)** | Multi-line text with explicit line breaks (`\n`) | Exceeding character limit, whitespace-only input, `Min-1`, `Max+1` | Control characters (CRLF injection, null byte `\0`), rich-text paste injection, base64 payload paste |
| **12** | **File Upload** | Allowed file format & MIME type, file size within limit | Disallowed extension (`.exe`, `.sh`, `.php`), 0-byte file, oversized file (`Max+1MB`) | Double extension (`file.pdf.exe`), MIME-type spoofing (`Content-Type: image/png` with PHP payload), path traversal filename (`../../etc/passwd`), SVG XSS payload |
| **13** | **OTP / MFA Code** | Valid unexpired code entry (6 digits) | Invalid code, expired code, partial length (5 digits), non-digits | Rate limiting (max 3-5 failed attempts -> lockout), brute-force throttling, resend cooldown timer tampering, clipboard auto-read hijacking |
| **14** | **Range Slider** | Drag slider between `Min` and `Max`, discrete step intervals | Snap-to values outside step, boundary values (`Min`, `Max`), keyboard arrow keys | Touch drag out-of-bounds, floating point precision drift (`0.1 + 0.2 = 0.30000000000000004`), DOM value manipulation |
| **15** | **Rich Text Editor (Basic WYSIWYG)** | Bold, italic, underline, bullet lists formatting | Exceeding character limit (raw text vs HTML tags count), empty editor with hidden `<p><br></p>` | Script tag injection, malicious iframe embedding, CSS injection (`style="behavior:url(...)"`), paste from Microsoft Word retaining proprietary XML tags |
| **16** | **Advanced WYSIWYG & Table Editor** | Insert tables, merge cells, embed verified images, blockquotes | Nested tables > 5 levels, table with 100+ columns, empty cells on mandatory columns | Image upload via base64 data URI causing DB packet explosion (>16MB), SVG XML external entity (XXE), markdown parsing bypass |
| **17** | **Geo Location & Address Autocomplete** | Select valid address from map/autocomplete, auto-populate Lat/Lng | Geolocation permission denied by browser, unlisted address, manual edit after autocomplete | Foreign country coordinates, reverse geocoding API timeout/failure, injection via street address query |
| **18** | **Digital Signature Pad (Canvas)** | Smooth vector signature drawn via mouse/touch, clear button | Blank canvas submitted, single dot / micro-stroke (<5px), signature cleared but state marked valid | Exported image payload size exceeds DB limit, tampering signature base64 data, touch latency causing jagged stroke drops |
| **19** | **Biometric Authentication Token (WebAuthn/FIDO2)** | Successful TouchID / FaceID / Passkey authorization | User cancels biometric prompt, biometric sensor timeout, device lacks hardware authenticator | Fallback to secondary PIN/Password mechanism, replay attack with stale WebAuthn assertion, credential ID cloning |
| **20** | **Camera / Barcode / QR Code Scanner** | Accurate barcode/QR decode from live camera stream or image upload | Camera permission blocked, blurry/torn/glared barcode, unsupported barcode format (e.g. Code 39 vs QR) | Malformed QR payload (SQLi/XSS in scanned text), camera hijacked by virtual software, EXIF rotation flip on image upload |
| **21** | **Multi-Currency & Exchange Rate Formatter** | Input currency with correct symbol/ISO code, automatic decimal formatting | Negative currency, exceeding decimal precision (e.g. JPY 0 decimals vs USD 2 vs BHD 3), `Min-1`, `Max+1` | Floating point currency rounding errors (banker's rounding vs round-up), dynamic FX exchange rate drift mid-transaction, currency mismatch attack |
| **22** | **Auto-reading SMS / OTP Input** | Full SMS text pasted from clipboard automatically parsed to 6 digits | SMS containing multiple numbers (order ID + OTP), SMS text in unsupported language | Clipboard permission denied, countdown timer bypass by altering local system clock, OTP replay across sessions |
| **23** | **Color Picker / Hex Code** | Valid hex format (`#RRGGBB`, `#RGB`), color palette swatch pick | Invalid hex characters (`#GGGGGG`), missing `#`, lowercase vs uppercase | Alpha channel transparency exploit (`#RRGGBBAA`), WCAG 2.2 color contrast failure against background, CSS injection |
| **24** | **Tag & Tokenized Chip Input** | Add tag via Enter/Comma, delete chip via "x" or Backspace | Duplicate tag entry, exceeding max tags limit, tag length boundary (`Max+1`) | Tags containing commas/quotes escaping delimiters, XSS via tag name rendering, bulk paste of 500 tags causing UI freeze |
| **25** | **Cron Expression & Recurring Schedule** | Standard 5-field/6-field cron expression, visual schedule picker | Invalid cron syntax, out-of-range fields (e.g. minute 61, month 13), leap year Feb 29 schedule | High-frequency execution DDoS (`* * * * * *`), daylight saving time (DST) skip/duplicate hour, UTC vs local timezone drift |

---

## 2. Advanced Non-Functional & Resilience Invariants

### 1. Unicode Normalization & IME Vietnamese Composing Protocol
- **NFC (Precomposed) vs NFD (Decomposed):**
  - Verify that user input using different typing engines (Unikey, EVKey, OpenKey, macOS Telex, iOS/Android native) is normalized to **Unicode NFC** before database persistence.
  - *Test Vector:* Input `Hòa bình` (NFC: `U+0048 U+00F2 U+0061...`) and `Hoà bình` (NFD: `U+0048 U+006F U+0300 U+0061...`) -> verify search query matches both identically.
- **Dead-Key & IME Intermediate Composing:**
  - Verify auto-formatting fields (phone, currency, credit card masking) do NOT swallow intermediate composing characters or misplace cursor position when users type accented Vietnamese (e.g. `aa` -> `â`, `s` -> `á`).

### 2. 4-Byte Surrogate Pairs UTF-8 & Emoji Safety
- **Database Truncation Prevention:**
  - Input multi-byte surrogate pair emojis (`👨‍👩‍👧‍👦`, `🏦`, `🚀`, `𠮷` - rare CJK).
  - *Verification:* Confirm the database schema supports `utf8mb4` (not MySQL legacy 3-byte `utf8`). Ensure characters after the emoji are NOT silently truncated and server does not throw unhandled 500 errors.

### 3. Clipboard Paste Special & Invisible Control Characters
- **Hidden Character Cleansing:**
  - Paste text copied from external software (PDF, Microsoft Word, Excel tables) containing invisible control characters:
    - Zero-Width Space: `\u200B`
    - Byte Order Mark (BOM): `\uFEFF`
    - Non-Breaking Space (NBSP): `\u00A0`
    - Soft Hyphen: `\u00AD`
  - *Verification:* System must either transparently sanitize/strip control characters or validate cleanly without throwing unparseable regex errors.

### 4. Multi-Tab State Drift & Stepper Navigation
- **Concurrent Tab Mutation (Lost Update Guard):**
  - Open Record A on Tab 1 and Tab 2 simultaneously.
  - On Tab 2, change status to `Inactive` or delete Record A and save.
  - On Tab 1, click "Save" with stale data.
  - *Verification:* System must block silent overwrite via Optimistic Locking (`409 Conflict`, `ETag`, or version token) and prompt user to refresh.
- **Stepper Wizard Leapfrogging:**
  - In a multi-step wizard (`/step-1` to `/step-4`), manually edit the browser URL to `/step-3` without completing required fields in `/step-1`.
  - *Verification:* System must redirect back to the earliest incomplete step with a clear banner notification.

### 5. Permission / RBAC Resilience
- **Horizontal Privilege Escalation (IDOR):**
  - User A (Tenant 1) alters URL parameter `/api/clients/101` to `/api/clients/102` (Tenant 2).
  - *Verification:* Strict `403 Forbidden` or `404 Not Found`. Zero leakage of Tenant 2 data.
- **Dynamic Role Revocation in Real-Time:**
  - Admin revokes User A's delete permission while User A has the delete confirmation modal open. User A clicks "Confirm Delete".
  - *Verification:* Backend checks authorization statefully at request time; returns `403 Forbidden` and updates UI. Token expiration must not allow unauthorized actions.

### 6. Integration, Asynchronous & Queue Backpressure
- **Out-of-Order Webhook / Delayed IPN:**
  - Simulate payment gateway webhook arriving *before* checkout completion API finishes, or IPN arriving 30 minutes late.
  - *Verification:* System maintains idempotency via transaction reference ID. Zero duplicate charges, zero negative balances, order transitions cleanly to `Paid`.
- **Queue Worker Backpressure & Timeout:**
  - Submit asynchronous batch job (e.g. export 50,000 records). Simulate delayed queue consumer.
  - *Verification:* UI shows progress polling indicator with graceful timeout (>60s) providing an asynchronous email download link instead of an endless spinner.

### 7. Device & Viewport Distortion (Mobile Virtual Keyboard)
- **Dynamic Viewport Height (`dvh`):**
  - On mobile devices (iOS Safari / Android Chrome), focus on input fields at the bottom of the viewport.
  - *Verification:* Virtual keyboard must not obscure the input field or the sticky "Submit" action button. Modal must remain scrollable.
- **Breakpoint Cumulative Layout Shift (CLS):**
  - Verify DataTable multi-column views at transition breakpoints (768px tablet, 1024px iPad landscape, 375px mobile). Action buttons must remain visible and dropdown menus must not clip off-screen.

### 8. Data Lifecycle & Soft-Delete Cascading
- **Aggregation Leakage Guard:**
  - Soft-delete a customer entity (`is_deleted = 1`).
  - *Verification:* Historical financial reports must retain historical revenue calculations, but operational search, autocomplete, and active counts must exclude the soft-deleted entity with zero `NullPointerException` crashes.
- **Historical Snapshot Immutability:**
  - Change product unit price or tax rate.
  - *Verification:* Invoices and orders generated prior to the change must remain 100% immutable and not recalculate dynamically.

### 9. Fault Injection & Gateway Chaos
- **Edge Proxy 502/503/504 Handling:**
  - Intercept API responses with Nginx/Cloudflare HTML error pages instead of JSON.
  - *Verification:* Frontend Single Page App (SPA) must not crash into a White Screen of Death (WSOD); must catch JSON parse failure and display a friendly retry banner.
- **Truncated JSON Stream:**
  - Simulate premature socket termination during large data transfers.
  - *Verification:* Client handles partial chunked stream termination gracefully without corrupting local application state.
