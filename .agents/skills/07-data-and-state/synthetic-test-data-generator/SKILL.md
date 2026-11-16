---
name: synthetic-test-data-generator
description: "Generate idempotent, boundary-value synthetic test data with unique runtime timestamps. Use when generating idempotent, unique test data for creation tests."
category: verification_and_resilience
version: "2.0.0"
policies:
  network: none
  shell: none
  filesystem: workspace-sandbox
---
# Synthetic Test Data Generator & Edge-Case Fuzzing Skill

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Generate idempotent, boundary-value synthetic test data with unique runtime timestamps. Use when generating idempotent, unique test data for creation tests.
- **Activation Scope:** Domain workflows for `07-data-and-state` involving `synthetic-test-data-generator`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT use real customer PII or production credentials for test data.
- Do NOT generate static repetitive values that hide edge-case bugs.
- Do NOT generate unconstrained fuzzer payloads without containment and boundary checks.
- **Sibling Skill Boundaries:**
  - db-state-verifier-and-seeder seeds databases; synthetic-test-data-generator synthesizes realistic, dynamic, and fuzz test payloads.

---

## 3. Ordered Execution Workflow

> **Target:** Eliminate database collisions, race conditions in parallel testing, and stale fixture dependencies by dynamically generating valid, boundary-value, and edge-case fuzzing datasets.

---

### Core Principles

1. **Idempotence & Unique Prefixing:**
   - Every generated string or identifier must contain an execution timestamp or UUID prefix (`AUTO_1719500000_...`) to allow parallel test executions without unique-key database collisions.
2. **Boundary Value Testing (BVT):**
   - Automatically cover equivalence partitions:
     - Null / Empty / Whitespace-only strings.
     - Max length limits (e.g. 255 chars, 1,024 chars, 10,000 chars text blocks).
     - Special characters, emojis, SQL injection probe strings (`' OR '1'='1' -- `), XSS polyglots (`<img src=x onerror=console.warn('qa_xss')>`).
     - Negative numbers, extreme floats, zero, boundary integer limits (`2^31 - 1`, `2^63 - 1`, `Number.MAX_SAFE_INTEGER`).
3. **Domain-Specific Constraints:**
   - Tax IDs, phone numbers, email RFC formats, and GIS coordinates (e.g., non-overlapping closed polygons).
4. **PII Safety Invariant:**
   - Never copy or mirror real customer production data (PII) into test fixtures. All synthesized entities must use purely artificial data with identifiable prefixes (`AUTO_`, `PERF_AUTO_`, `AUTO_RACE_`) paired with automated teardown cleanup hooks.
5. **Vietnam Locale Standards:**
   - Support national telecom prefixes (`03x`, `05x`, `07x`, `08x`, `09x`), 12-digit Citizen Identity Card (CCCD) format, full UTF-8 Vietnamese diacritics, and VND currency conventions (`100.000 ₫` / `100.000 VND`).

---

### Standard Generation Recipes

### Recipe A: Dynamic Unique Entity Names
<!-- classification: illustrative -->
```typescript
export class TestDataFactory {
  static uniqueName(prefix: string = 'AUTO'): string {
    const timestamp = Date.now().toString(36).toUpperCase();
    const randomSuffix = Math.random().toString(36).substring(2, 6).toUpperCase();
    return `${prefix}_${timestamp}_${randomSuffix}`;
  }

  static validEmail(prefix: string = 'tester'): string {
    return `${prefix}.${Date.now()}@example-testing.com`;
  }
}
```

### Recipe B: Boundary Value String Suite
<!-- classification: illustrative -->
```json
{
  "boundaryStrings": [
    "",
    "   ",
    "A",
    "A".repeat(255),
    "A".repeat(1024),
    "Tiếng Việt có dấu: Cà phê sữa đá & Trắc nghiệm chất lượng",
    "Special chars: !@#$%^&*()_+{}|:\"<>?~`-=[]\\;',./",
    "Unicode emojis: 🚀🔥⚡🧪✨",
    "XSS probe: <img src=x onerror=alert('qa')>",
    "SQLi probe: ' OR '1'='1' -- "
  ]
}
```

### Recipe C: GeoJSON / GIS Valid Non-Overlapping Polygons
<!-- classification: illustrative -->
```typescript
export function generateValidPolygon(centerLat = 21.0285, centerLng = 105.8542, offset = 0.005) {
  // Generates closed 5-point polygon bounding box
  return [
    [centerLng - offset, centerLat - offset],
    [centerLng + offset, centerLat - offset],
    [centerLng + offset, centerLat + offset],
    [centerLng - offset, centerLat + offset],
    [centerLng - offset, centerLat - offset] // Close ring
  ];
}
```

### Recipe D: Vietnamese Locale Test Data
<!-- classification: illustrative -->
```typescript
export class VietnamDataFactory {
  static validPhone(): string {
    const prefixes = ['032', '038', '039', '056', '070', '079', '081', '085', '090', '091', '098'];
    const prefix = prefixes[Math.floor(Math.random() * prefixes.length)];
    const suffix = Math.floor(1000000 + Math.random() * 9000000).toString().substring(0, 7);
    return `${prefix}${suffix}`;
  }

  static validCCCD(): string {
    // 12-digit format: 001 (Hanoi) + 0 (male, 20th century) + 98 (birth year) + 6 random digits
    const province = '001';
    const genderCentury = '0';
    const birthYear = '98';
    const randomSeq = Math.floor(100000 + Math.random() * 900000).toString();
    return `${province}${genderCentury}${birthYear}${randomSeq}`;
  }

  static formattedVND(amount: number): string {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  }
}
```

---

### Edge-Case Fuzzing & Input Sanitization Suite (`tools/fuzz_payloads.py`)

Transform functional tests into input sanitization and robustness validation by executing edge-case fuzzing vectors:

<!-- classification: illustrative -->
```bash
# Query CLI catalog for specific field vectors
python tools/fuzz_payloads.py --field username --type string
python tools/fuzz_payloads.py --category sqli --json
```

### Recipe D: Harmless SQLi Polyglot Sanity
<!-- classification: illustrative -->
```typescript
export const SQLI_FUZZ_PROBES = [
  "' OR '1'='1' -- ",
  "SLEEP(0)/*'/*\"/*--",
  "1' UNION SELECT NULL, NULL, NULL -- ",
  "admin' -- ",
  "'; WAITFOR DELAY '0:0:0'--"
];
// Assertion: Application must return HTTP 400 or sanitize safely; MUST NEVER throw 500 SQLException.
```

### Recipe E: Unicode BiDi & RTL Trojan Source Vectors
<!-- classification: illustrative -->
```typescript
export const BIDI_FUZZ_PROBES = [
  "\u202E\u0041\u0042\u0043_AUTO_TX", // Right-to-Left Override (RLO)
  "AUTO\u200B\u200C\u200D_DATA",       // Zero-Width Space & Joiner
  "\uFEFFAUTO_USER",                   // In-string Byte Order Mark (BOM)
  "USER_مرحبا_بالعالم_2026"            // Mixed Latin/Arabic BiDi text
];
// Assertion: Database persistence and frontend display must not corrupt visual hierarchy or inject Trojan Source spoofing.
```

### Recipe F: Multi-Byte Emoji Surrogate Pairs & ZWJ Sequences
<!-- classification: illustrative -->
```typescript
export const EMOJI_FUZZ_PROBES = [
  "👨‍👩‍👧‍👦_QA_RECORD",      // Complex Zero-Width Joiner family sequence
  "🏳️‍🌈_FLAG_TAG",          // Multi-code point flag sequence
  "\uD83D\uDE00\uD83D",     // Unpaired surrogate boundary test
  "🔥🚀⚡🧪✨"               // 4-byte high-plane UTF-8 characters
];
// Assertion: Backend UTF-8 MB4 column encoding must persist without truncation or 1366 Incorrect string value error.
```

### Recipe G: Extreme Length Buffer Stress ($10^4$ Characters)
<!-- classification: illustrative -->
```typescript
export const BUFFER_STRESS_PAYLOADS = [
  "A".repeat(10000),         // 10,000 chars text block
  "X".repeat(1024),          // Standard 1KB boundary
  '{"test": [' + Array(500).fill('1').join(',') + ']}' // Repetitive JSON nesting
];
// Assertion: API must reject with 400/413 Payload Too Large; frontend form controls must enforce max-length clipping.
```

---

### Teardown & Lifecycle Integration
- Every test generating persistent records with `synthetic-test-data-generator` **MUST** register the generated ID into a teardown queue to clean up after test execution completes.

---

## 4. Verification Points & DoD

1. Generated data includes realistic edge cases (Unicode, boundary lengths, special characters).
2. Entity codes use dynamic timestamped prefixes (`BasePage.uniqueCode()`).
3. Zero PII or real credentials generated in test datasets.

---

## 5. Handoff Protocol

- **Deliverables:** Synthetic data factories, fuzz payload dictionaries, and test data fixture files.
- **Next Subagent:** pom-crafter / api-engineer
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
