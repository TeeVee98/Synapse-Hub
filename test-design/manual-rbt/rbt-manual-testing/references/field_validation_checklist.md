# Field-Level Validation Checklist (25 Input Field Types) & Resilience Protocols

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.  
> **Standard Compliance:** Aligned with **ISO/IEC/IEEE 29119-4** (Test Techniques), **ISTQB CTAL-TAE v2.0**, and **OWASP ASVS v4.0 / Web Security Testing Guide (WSTG)**.

Comprehensive boundary values, 3-value Boundary Value Analysis (BVA), negative test vectors, security edge cases, and non-functional resilience protocols across all standard web, mobile, and enterprise input fields.

---

## 1. 25-Field Validation Matrix

| # | Field Type | Positive Verification | Boundary & Negative Checks (3-Value BVA) | Security, Injection & Enterprise Edge Cases |
| :- | :--- | :--- | :--- | :--- |
| **1** | **Text (Name, Title)** | Valid length, Unicode support (Vietnamese accented), allowed special chars (`-`, `.`) | Empty, whitespace-only string (`"   "`) blocked on required fields; leading/trailing whitespace (`"  abc  "`) `trim()` validation (evaluated before/after `minlength`/`maxlength`, DB persistence verification without trailing spaces); consecutive multiple internal spaces; non-breaking space (`\u00A0`); `Min-1`, `Min`, `Min+1`, `Max-1`, `Max`, `Max+1` | XSS `<script>`, SQLi `' OR 1=1--`, HTML tags, surrogate emojis (4-byte), NFC/NFD Unicode normalization drift |
| **2** | **Email** | Standard format (`user@domain.com`), subdomains, tagged alias (`user+tag@domain.com`) | Missing `@`, missing domain, multiple `@`, leading/trailing whitespace (`"  user@domain.com  "`) auto-trimmed, whitespace-only (`"   "`) blocked, `Min-1`, `Max 254 chars`, `255 chars` | SQLi in local part, header injection (`\r\nBcc:`), Internationalized Domain Names (IDN/Punycode), display spoofing |
| **3** | **Phone** | E.164 (`+84901234567`), national formats with spaces/dashes, extension | Alpha characters, symbols, leading/trailing spaces auto-trimmed, whitespace-only (`"   "`) blocked, too short (`Min-1`), too long (`Max+1`), all zeros (`0000000000`) | Leading `+` handling, country code mismatch, virtual VoIP numbers, script injection via SMS payload |
| **4** | **Password** | Complexity met (Upper, lower, digit, special character), passphrase | Missing 1 criteria, `Min-1`, `Min`, `Max-1`, `Max`, `Max+1`, whitespace-only (`"   "`) blocked, leading/trailing whitespace handling (retained for entropy or trimmed with clear policy), common dictionary passwords | Whitespace handling (leading/trailing vs internal), clipboard paste support/blocking, shoulder-surfing masking toggle |
| **5** | **Number (Quantity, Price)** | Valid integer/float, decimals within precision limit | Alpha chars, negative numbers, `0` (if disallowed), decimals on integer-only, `Min-1`, `Max+1` | Integer overflow (> 2^31-1 or > 2^53-1 in JS), scientific notation (`1e6`), localized thousand separators (`1,000.00` vs `1.000,00`) |
| **6** | **Date / Datetime** | Valid date format (`YYYY-MM-DD`, `DD/MM/YYYY`), manual typing & picker | Invalid calendar dates (Feb 29 non-leap year, Feb 30, April 31), format mismatch, partial entry | Historical epoch boundary (1970-01-01), Year 2038 problem (Unix 32-bit), client vs server timezone drift, daylight saving shift |
| **7** | **Date Range** | `StartDate <= EndDate`, single-day range | `StartDate > EndDate`, single date missing, date span exceeding system max limit (e.g. > 90 days) | Leap day spans, overlapping date bookings, retroactive date entry on immutable periods |
| **8** | **Dropdown / Select** | Select valid option, search filter within dropdown | Unselected mandatory field, disabled options selected via keyboard | Async loading delays (stale options), large option lists (> 10,000 items), tamper option value via DevTools inspection |
| **9** | **Multi-Select** | Select multiple items, deselect individual, reorder | Exceeding max selection limit, 0 items selected on mandatory, Select All on massive sets | Search filter desynchronization, badge dismissal ("x" click) focus trap, duplicate selection payload injection |
| **10** | **Checkbox / Radio** | Toggle check/uncheck, switch radio option group | Mandatory consent unchecked (Terms of Service), radio group with no option selected | Rapid toggle spam (<100ms), disabled read-only state tampering, conflicting mutual exclusions |
| **11** | **Textarea (Notes, Bio)** | Multi-line text with explicit line breaks (`\n`) | Exceeding character limit, whitespace-only input (`"   "`) blocked on required fields, leading/trailing whitespace `trim()` verification, consecutive multiple internal spaces, non-breaking space (`\u00A0`), `Min-1`, `Max+1` | Control characters (CRLF injection, null byte `\0`), rich-text paste injection, base64 payload paste |
| **12** | **File Upload** | Allowed file format & MIME type, file size within limit | Disallowed extension (`.exe`, `.sh`, `.php`), 0-byte file, oversized file (`Max+1MB`) | Double extension (`file.pdf.exe`), MIME-type spoofing (`Content-Type: image/png` with PHP payload), path traversal filename (`../../etc/passwd`), SVG XSS payload |
| **13** | **OTP / MFA Code** | Valid unexpired code entry (6 digits) | Invalid code, expired code, partial length (5 digits), non-digits, leading/trailing whitespace (`" 123456 "`) auto-trimmed, whitespace-only (`"   "`) blocked | Rate limiting (max 3-5 failed attempts -> lockout), brute-force throttling, resend cooldown timer tampering, clipboard auto-read hijacking |
| **14** | **Range Slider** | Drag slider between `Min` and `Max`, discrete step intervals | Snap-to values outside step, boundary values (`Min`, `Max`), keyboard arrow keys | Touch drag out-of-bounds, floating point precision drift (`0.1 + 0.2 = 0.30000000000000004`), DOM value manipulation |
| **15** | **Rich Text Editor (Basic WYSIWYG & Advanced WYSIWYG & Table Editor)** | Bold, italic, underline, bullet/numbered lists formatting, tables, embed verified images, blockquotes | Exceeding character limit (raw text vs HTML tags count), empty editor with hidden `<p><br></p>`, nested tables > 5 levels, table with 100+ columns | Script tag injection, malicious iframe embedding, CSS injection (`style="behavior:url(...)"`), paste from Microsoft Word retaining proprietary XML tags, SVG XXE, image upload via base64 data URI causing DB packet explosion (>16MB) |
| **16** | **Geo Location & Address Autocomplete** | Select valid address from map picker or autocomplete dropdown; auto-populate street, city, country, postal code, and valid coordinates (`-90.0 <= Lat <= 90.0`, `-180.0 <= Lng <= 180.0`); sync manual map pin drag | Lat boundaries (3-value BVA): `Min-1` (-90.000001°), `Min` (-90.000000°), `Min+1` (-89.999999°), `Max-1` (89.999999°), `Max` (90.000000°), `Max+1` (90.000001°); Lng boundaries: `Min-1` (-180.000001°), `Min` (-180.000000°), `Min+1` (-179.999999°), `Max-1` (179.999999°), `Max` (180.000000°), `Max+1` (180.000001°); GPS permission denied/blocked, unlisted address query (0 results), manual text edit after autocomplete without re-verifying geocode, reverse geocoding API timeout | Address query injection (SQLi `' OR 1=1--`, XSS `<img src=x onerror=alert(1)>`, prototype pollution via map JSON); GPS coordinate spoofing, cross-border jurisdiction boundary check, external geocoding API rate limiting and quota exhaustion, graceful fallback to manual address input on map service outage |
| **17** | **Digital Signature Pad (Canvas)** | Capture smooth vector signature via touch, mouse, or stylus pen on HTML5 Canvas; real-time stroke rendering with variable velocity/pressure; clear/undo resets canvas; exports lossless PNG/SVG and compliant base64 data URI string | Stroke count boundaries (3-value BVA): `Min-1` (0 points / blank canvas submitted), `Min` (minimal stroke threshold e.g. single 5px stroke / 10 sample points), `Min+1` (valid compact signature), `Max-1` (high complexity vector), `Max` (max vector stroke limit), `Max+1` (excessive stroke overflow); canvas cleared via UI button but form state remains valid; 1px micro-click rejected as empty; strokes drawn outside canvas viewport boundaries | Base64 payload size overflow attacking backend memory (>2MB-10MB base64 string injection); script injection in SVG export (`<svg onload=alert(1)>`); tampering client-side hidden input value with arbitrary image URI; biometric/time-stamped cryptographic signature sealing (PKCS#7/CAdES) integrity tamper detection |
| **18** | **Biometric / WebAuthn (Biometric Authentication Token)** | Successful passkey or biometric hardware authorization (Touch ID, Face ID, Windows Hello, Android Biometrics) via W3C WebAuthn / FIDO2 challenge-response; returns valid public-key credential assertion and JWT authentication token | Challenge timeout boundaries (3-value BVA): `Min-1` (expired challenge nonce), `Min` (valid immediate prompt response), `Min+1` (normal response), `Max-1` (59s grace period), `Max` (60s timeout limit), `Max+1` (client timeout expired); failed sensor attempts: `Min` (1 fail), `Max-1` (4 failed attempts), `Max` (5th attempt), `Max+1` (lockout triggered); user explicit cancellation of OS modal; device lacks biometric sensor (`window.PublicKeyCredential` undefined) -> graceful non-blocking fallback to PIN/password/TOTP | Replay attack with captured/stale WebAuthn assertion payload; origin mismatch / phishing cross-domain credential assertion injection; credential ID cloning; man-in-the-middle challenge manipulation; tamper detection of authenticator transport extensions (USB, NFC, BLE) |
| **19** | **Camera / Barcode / QR Scanner (Camera / Barcode / QR Code Scanner)** | Real-time camera feed stream initialization via `navigator.mediaDevices.getUserMedia`; rapid and accurate detection & decoding of 1D barcodes (EAN-13, UPC-A, Code 128) and 2D QR codes; successful fallback to uploaded image file parsing | Resolution and dimension boundaries (3-value BVA): blurry, torn, skewed, low-contrast, or glared barcode; image dimension boundaries: `Min-1` (10x10px too small to decode), `Min` (valid low-res 100x100px), `Min+1` (101x101px), `Max-1` (4K UHD), `Max` (8K image), `Max+1` (50MP oversized file); scan buffer timeout (30s continuous scanning with no code detected); camera permission denied/blocked; camera hardware in use by another application (`NotReadableError`); unsupported barcode format (Aztec); partial code truncated at frame edge | Malicious scanned QR payload containing SQLi (`' UNION SELECT...`), XSS (`javascript:...`), command injection, or malicious deep-link URLs; EXIF orientation metadata flip on image file upload; virtual camera device stream hijacking/spoofing; buffer overflow via ultra-dense binary QR codes (Version 40 QR with maximum binary payload) |
| **20** | **Currency & FX (Multi-Currency & Dynamic FX) (Multi-Currency & Exchange Rate Formatter)** | Currency input with ISO-4217 currency code selector (`USD`, `EUR`, `VND`, `JPY`, `GBP`), dynamic exchange rate lookup, automatic thousand grouping and decimal formatting per locale (e.g. `1,250.50 USD` vs `1.250,50 EUR` vs `1.250.000 VND`) | Amount boundaries (3-value BVA): `Min-1` (-0.01 or negative when disallowed), `Min` (0.00 or minimum transaction amount), `Min+1` (0.01), `Max-1` (9,999,999.99), `Max` (10,000,000.00), `Max+1` (10,000,000.01); decimal precision boundaries by currency: 0 decimals for JPY/VND (reject `.5`), 2 decimals for USD/EUR, 3 decimals for BHD/KWD/OMR; input with 4+ decimals tested against rounding rules (banker's round half-even vs round-up) | Dynamic FX rate drift: exchange rate updates between cart review and final payment confirmation (slippage tolerance check e.g. >2% delta warning/re-quote); currency mismatch exploit (submitting amount in JPY with USD currency tag); floating-point IEEE-754 precision loss (`0.1 + 0.2 != 0.3`); integer overflow on high-denomination currencies (VND trillions) |
| **21** | **Credit Card / IBAN / Masked Input** | Standard 13-19 digit card PAN input with automatic card network detection (Visa, Mastercard, Amex, JCB, Discover); automated Luhn mod-10 checksum validation; MM/YY expiry validation (future unexpired month); 3-4 digit CVV/CVC; international IBAN input with ISO 13616 mod-97 verification and country-specific format mask (e.g. DE, GB, FR, VN); visual display masking displaying only last 4 digits (`•••• •••• •••• 1234`) | PAN length boundaries (3-value BVA): `Min-1` (11 digits), `Min` (12/13 digits), `Min+1` (14 digits), `Max-1` (18 digits), `Max` (19 digits), `Max+1` (20 digits); expiry month boundaries: `Min-1` (current month - 1 expired), `Min` (current month/year), `Min+1` (next month), `Max-1` (current year + 19 years), `Max` (current year + 20 years), `Max+1` (current year + 21); CVV length boundaries: `Min-1` (2 digits), `Min` (3 digits), `Max` (4 digits Amex), `Max+1` (5 digits); invalid Luhn check digit; expired card; invalid IBAN checksum (mod-97 != 1); spaces and dashes stripping; non-numeric keystrokes blocked | PCI-DSS compliance guard: strict prevention of raw CVV/CVC or full unmasked PAN storage in browser localStorage, cookies, DOM dataset, or client-side telemetry logs; clipboard copy paste handling (stripping card data from clipboard history where possible); auto-formatting input mask not swallowing IME/dead-key events; carding / bin-attack velocity throttling |
| **22** | **Async Autocomplete / Typeahead** | Server-side debounced search query (300ms debounce SLA); minimum trigger length (>= 2 characters); displays dropdown with matching results and substring match `<mark>` highlighting; keyboard navigation (Arrow Down/Up, Enter to select, Escape to dismiss); mouse hover and click selection | Character trigger length boundaries (3-value BVA): `Min-1` (1 character - no async query fired), `Min` (2 characters - async search triggered), `Min+1` (3 characters), `Max-1` (99 characters), `Max` (100 characters), `Max+1` (101 characters); result list pagination boundaries: `Min-1` (0 results - empty state message), `Min` (1 result), `Min+1` (2 results), `Max-1` (9 items), `Max` (10/20 max items), `Max+1` (overflow paging); rapid typing bursts triggering multiple requests; rapid clearing of input via Backspace/Clear button while pending requests are inflight | Out-of-order response race conditions: slow network response for older query ("ca") arrives after fast response for newer query ("cat") -> system must cancel stale requests via `AbortController` or token check and display only newest result; XSS injection in query string rendered in highlight tags; SQLi/NoSQLi in query parameter; client DoS via unbounded query spam |
| **23** | **Cron Expression & Recurring Schedule** | Standard 5-field (Linux crontab: `min hour dom month dow`) or 6-field (Quartz: `sec min hour dom month dow year`) cron string parsing; bidirectional visual recurrence schedule builder (Daily, Weekly, Monthly, Interval); human-readable schedule translation ("Runs every Monday at 09:00 UTC"); next 5 execution timestamps preview table | Field range boundaries (3-value BVA): Minute: `Min-1` (-1), `Min` (0), `Min+1` (1), `Max-1` (58), `Max` (59), `Max+1` (60); Hour: `Min-1` (-1), `Min` (0), `Min+1` (1), `Max-1` (22), `Max` (23), `Max+1` (24); Day-of-month: `Min-1` (0), `Min` (1), `Min+1` (2), `Max-1` (30), `Max` (31), `Max+1` (32); Month: `Min-1` (0), `Min` (1 / JAN), `Min+1` (2), `Max-1` (11), `Max` (12 / DEC), `Max+1` (13); Day-of-week: `Min` (0 or 1), `Max` (6 or 7); invalid syntax (missing fields, illegal special characters `@!#%`); conflicting Day-of-Month and Day-of-Week definitions (`?` vs `*`) | High-frequency denial-of-service schedule (`* * * * *` or `*/1 * * * * *` executing every second, swamping backend workers) -> system enforces minimum execution interval (e.g. >= 5 minutes for non-admin tenants); Daylight Saving Time (DST) shift handling (spring forward 1 missing hour, fall back 1 duplicate hour); leap year boundary (schedule targeting Feb 29 on non-leap years); server vs tenant timezone ambiguity |
| **24** | **JSON / Code / Formula Editor** | Multi-line rich code / formula editor (Monaco, CodeMirror, Ace) with syntax highlighting, line numbers, bracket matching, auto-indentation, and AST schema validation; formula evaluation engine (Excel-like formulas `=SUM()`, `=IF()`, `=VLOOKUP()`); JSON prettify/format and minify actions; valid AST structure output | Document size / line count boundaries (3-value BVA): `Min-1` (0 bytes / empty document on mandatory field), `Min` (1 valid character or `{}`), `Min+1` (2 valid tokens), `Max-1` (99,999 lines / 1.9MB), `Max` (100,000 lines / 2MB limit), `Max+1` (payload exceeding editor buffer limit); malformed syntax (unclosed brackets `{"a": 1`, trailing commas in strict JSON, invalid token, syntax error line/column gutter badge); invalid formula syntax (`=SUM(` or unknown function name `=FOOBAR()`) | Formula injection / CSV formula injection (`=cmd|' /C calc'!A0`, `@SUM(...)`, `-2+3+cmd|...`); JavaScript sandbox breakout (prototype pollution via `__proto__`, `constructor`, `Function()`, `eval()`); circular dependency detection in formula graphs (Cell A1 `=B1`, Cell B1 `=A1` -> detects cycle and emits `#CYCLE!` without stack overflow); memory exhaustion via deeply nested JSON objects (>100 levels) |
| **25** | **Inline Editable Data Grid** | Interactive spreadsheet/table data grid with keyboard navigation (Tab/Shift-Tab, Arrow keys, Enter to edit, Escape to cancel); inline cell editing across diverse column types (text, number, date, dropdown); dirty cell/row change tracking indicators; batch save/commit and undo/redo operations; clipboard block copy/paste from external spreadsheets (Microsoft Excel / Google Sheets) | Grid dimension boundaries (3-value BVA): `Min-1` (0 rows / empty grid on required dataset), `Min` (1 row), `Min+1` (2 rows), `Max-1` (9,999 rows with virtual scrolling), `Max` (10,000 rows buffer limit), `Max+1` (row limit exceeded); cell character length: `Min-1`, `Min`, `Min+1`, `Max-1`, `Max`, `Max+1`; required cell left blank upon row commit; datatype mismatch during cell edit (typing alpha text in numeric column); navigation away from page with unsaved dirty cells triggering browser unload confirmation dialog | Massive clipboard block paste buffer overflow (pasting 50,000 cells at once causing DOM freezing) -> virtualization and chunked ingestion guard; multi-user concurrent cell edits (optimistic row locking with version token to prevent overwriting peer edits); XSS payload rendering within grid cells; column sorting/filtering tampering SQL injection |

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

### 8. UI Latency, Payment Redirect & Browser Interrupt Resilience
- **Slow Network Double-Click & Button Disable Guard:**
  - Mô phỏng mạng chậm (Slow 3G / độ trễ 3–5 giây), bấm liên tiếp nút "Thanh toán" / "Xác nhận" (`≥ 2` lần trong 500ms).
  - *Verification:* UI phải chuyển nút sang trạng thái `disabled` + loading indicator ngay ở lần bấm đầu tiên; chỉ gửi đúng 1 request duy nhất kèm `Idempotency-Key`; không tạo đơn trùng và không trừ tiền 2 lần.
- **Browser Interrupt lúc Redirect cổng thanh toán (Back / F5 / Close Tab):**
  - Bấm nút **Back** trình duyệt, nhấn **F5/Refresh**, hoặc **đóng tab** ngay giữa lúc chuyển hướng sang cổng thanh toán (VNPay/MoMo/Stripe/3DS) hoặc khi đang chờ callback trả về.
  - *Verification:* Giao dịch giữ trạng thái `Pending` để đối soát (reconcile) an toàn, không crash trang, không cho thanh toán lặp trên cùng mã đơn đã xử lý.
- **Payment Session TTL & Timeout Recovery:**
  - Giữ màn hình thanh toán vượt quá thời gian hết hạn (TTL) rồi mới bấm xác nhận.
  - *Verification:* Hệ thống từ chối bằng mã/thông báo lỗi xác định và không trừ tiền.

### 9. Data Lifecycle & Soft-Delete Cascading
- **Aggregation Leakage Guard:**
  - Soft-delete a customer entity (`is_deleted = 1`).
  - *Verification:* Historical financial reports must retain historical revenue calculations, but operational search, autocomplete, and active counts must exclude the soft-deleted entity with zero `NullPointerException` crashes.
- **Historical Snapshot Immutability:**
  - Change product unit price or tax rate.
  - *Verification:* Invoices and orders generated prior to the change must remain 100% immutable and not recalculate dynamically.

### 10. Fault Injection & Gateway Chaos
- **Edge Proxy 502/503/504 Handling:**
  - Intercept API responses with Nginx/Cloudflare HTML error pages instead of JSON.
  - *Verification:* Frontend Single Page App (SPA) must not crash into a White Screen of Death (WSOD); must catch JSON parse failure and display a friendly retry banner.
- **Truncated JSON Stream:**
  - Simulate premature socket termination during large data transfers.
  - *Verification:* Client handles partial chunked stream termination gracefully without corrupting local application state.

---

## 3. Extended Specializations & Backward Compatibility Index

To preserve backward compatibility with legacy test suites and specialized domain requirements, the following input specializations are mapped and subsumed under the 25 primary enterprise types:

- **Advanced WYSIWYG & Table Editor**: Subsumed under **#15 Rich Text Editor (Basic WYSIWYG & Advanced WYSIWYG & Table Editor)** and **#24 JSON / Code / Formula Editor**. Covers complex multi-level nested tables, cell merging, blockquotes, code blocks, and markdown/HTML source toggling.
- **Auto-reading SMS / OTP Input**: Subsumed under **#13 OTP / MFA Code** and **#22 Async Autocomplete / Typeahead**. Covers native WebOTP API integration, clipboard auto-read permissions, multi-number SMS extraction, and cross-device syncing.
- **Color Picker / Hex Code**: Subsumed under **#8 Dropdown / Select** and Custom Enterprise Inputs. Covers RGB/RGBA/HSL/HEX format parsing, eyedropper API integration, alpha-channel transparency, and WCAG 2.2 color contrast compliance.
- **Tag & Tokenized Chip Input**: Subsumed under **#9 Multi-Select** and **#22 Async Autocomplete / Typeahead**. Covers chip tokenization on Enter/Comma, chip deletion via Backspace/click, token deduplication, and bulk chip paste parsing.

