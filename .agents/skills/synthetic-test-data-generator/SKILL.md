---
name: synthetic-test-data-generator
description: Generate robust, idempotent, and boundary-value synthetic test data (strings, numbers, emails, addresses, enterprise contracts, GIS coordinates) for automated test suites.
---

# Synthetic Test Data Generator Skill

> **Target:** Eliminate database collisions, race conditions in parallel testing, and stale fixture dependencies by dynamically generating valid and boundary-value datasets.

---

## 1. Core Principles

1. **Idempotence & Unique Prefixing:**
   - Every generated string or identifier must contain an execution timestamp or UUID prefix (`AUTO_1719500000_...`) to allow parallel test executions without unique-key database collisions.
2. **Boundary Value Testing (BVT):**
   - Automatically cover equivalence partitions:
     - Null / Empty / Whitespace-only strings.
     - Max length limits (e.g. 255 chars, 10,000 chars text blocks).
     - Special characters, emojis, SQL injection probe strings (`' OR '1'='1`), XSS payloads (`<script>alert(1)</script>`).
     - Negative numbers, extreme floats, zero, boundary integer limits (`2^31 - 1`, `2^63 - 1`).
3. **Domain-Specific Constraints:**
   - Tax IDs, phone numbers, email RFC formats, and GIS coordinates (e.g., non-overlapping closed polygons).

---

## 2. Standard Generation Recipes

### Recipe A: Dynamic Unique Entity Names
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

---

## 3. Teardown & Lifecycle Integration
- Every test generating persistent records with `synthetic-test-data-generator` **MUST** register the generated ID into a teardown queue to clean up after test execution completes.
