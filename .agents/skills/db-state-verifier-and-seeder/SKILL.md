---
name: db-state-verifier-and-seeder
description: Verify database records, seed isolated test fixtures, and assert database mutations (SQL/NoSQL) directly. Use on-demand when testing backend state mutations or DB consistency.
---

# Database State Verifier & Seeder Skill

> **Target:** Eliminate shallow UI-only validations by asserting exact backend database mutations (PostgreSQL, MySQL, Oracle, MongoDB) and providing isolated fixture seeding.

---

## 1. Core Principles

1. **Dual-Layer Assertion (UI + DB):**
   - Asserting a green UI toast is insufficient for transactional operations. Test suites must query the persistence layer to ensure records are properly inserted with correct foreign keys and audit fields (`created_at`, `created_by`).
2. **Transaction Isolation & Fast Rollback:**
   - Whenever possible, seed data inside transactional boundaries or maintain automated deletion queues tied to entity unique codes.
3. **Zero Plaintext Connection Credentials:**
   - All connection strings must be sourced strictly from environment variables (`DB_HOST`, `DB_USER`, `DB_PASS`).

---

## 2. Standard Database Query & State Assertion Patterns

### Pattern A: Asserting Record Mutation via Direct SQL Query
```python
import os
import psycopg2

def assert_record_created(unique_code: str, expected_status: str = "ACTIVE"):
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "qa_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", "")
    )
    cursor = conn.cursor()
    cursor.execute("SELECT id, status, is_deleted FROM business_entities WHERE code = %s", (unique_code,))
    row = cursor.fetchone()
    
    assert row is not None, f"Database assertion failed: Record with code {unique_code} not found!"
    assert row[1] == expected_status, f"Expected status {expected_status}, but found {row[1]}"
    assert row[2] is False, "Record flagged as deleted prematurely"
    
    conn.close()
    print(f"[PASS] Verified database persistence for code: {unique_code}")
```

### Pattern B: Idempotent DB Teardown Cleanup
```python
def teardown_test_entity(unique_code: str):
    conn = psycopg2.connect(...)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM business_entities WHERE code = %s", (unique_code,))
    conn.commit()
    conn.close()
```
