---
name: db-state-verifier-and-seeder
description: "Seed isolated test fixtures and assert database mutations across SQL and NoSQL. Use when seeding, verifying, or cleaning database state around tests."
category: verification_and_resilience
version: "2.0.0"
policies:
  network: localhost-only
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---
# Database State Verifier & Seeder Skill

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Seed isolated test fixtures and assert database mutations across SQL and NoSQL. Use when seeding, verifying, or cleaning database state around tests.
- **Activation Scope:** Domain workflows for `07-data-and-state` involving `db-state-verifier-and-seeder`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT execute destructive DB mutations (DROP, PURGE, TRUNCATE) without explicit granular consent grants.
- Do NOT use static hardcoded primary keys that cause database unique constraint collisions.
- Do NOT leave residual test data in databases; pair seeding with automated teardown cleanup.
- **Sibling Skill Boundaries:**
  - synthetic-test-data-generator generates data payloads; db-state-verifier-and-seeder seeds and validates database state across SQL/NoSQL stores.

---

## 3. Ordered Execution Workflow

> **Target:** Eliminate shallow UI-only validations by asserting exact backend database mutations (PostgreSQL, MySQL, Oracle, MongoDB, Redis) and providing isolated, idempotent fixture seeding.

---

### Core Principles

1. **Dual-Layer Assertion (UI + DB):**
   - Asserting a green UI toast is insufficient for transactional operations. Test suites must query the persistence layer to ensure records are properly inserted with correct foreign keys and audit fields (`created_at`, `created_by`).
2. **Transaction Isolation & Fast Rollback:**
   - Whenever possible, seed data inside transactional boundaries or maintain automated deletion queues tied to entity unique codes.
3. **Zero Plaintext Connection Credentials:**
   - All connection strings must be sourced strictly from environment variables (`DB_HOST`, `DB_USER`, `DB_PASS`).

---

### Standard SQL Query & State Assertion Patterns

### Pattern A: PostgreSQL / MySQL Record Persistence Assertion
<!-- classification: illustrative -->
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

### Pattern B: Idempotent SQL Teardown Cleanup
<!-- classification: illustrative -->
```python
def teardown_test_entity(unique_code: str):
    conn = psycopg2.connect(...)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM business_entities WHERE code = %s", (unique_code,))
    conn.commit()
    conn.close()
```

---

### Standard NoSQL Patterns (MongoDB & Redis)

### Pattern C: MongoDB Document Mutation & JSON Schema Assertion
<!-- classification: illustrative -->
```python
import os
from pymongo import MongoClient

def assert_mongo_document_persisted(order_id: str, expected_item_count: int):
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    db = client[os.getenv("MONGO_DB", "orders_db")]
    collection = db["customer_orders"]

    doc = collection.find_one({"orderId": order_id})
    assert doc is not None, f"MongoDB error: Order {order_id} not found!"
    assert len(doc.get("items", [])) == expected_item_count, f"Item count mismatch in doc: {doc}"
    assert doc.get("paymentStatus") == "CONFIRMED", "Payment status is not CONFIRMED"

    # Cleanup teardown
    collection.delete_one({"orderId": order_id})
    client.close()
    print(f"[PASS] Verified and cleaned MongoDB document: {order_id}")
```

### Pattern D: Redis Cache Expiry & Invalidation Verification
<!-- classification: illustrative -->
```python
import os
import redis

def assert_cache_invalidated(cache_key: str):
    r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    val = r.get(cache_key)
    assert val is None, f"Cache leak error: Key '{cache_key}' should have been invalidated after mutation!"
    print(f"[PASS] Verified Redis cache eviction for key: {cache_key}")
```

---

### Zero-Pollution DB Sandbox & Ephemeral Teardown (`tools/db_sandbox.py`)

To eliminate cascading flakiness and orphan test junk in parallel CI runs, agents utilize deterministic DB Sandbox operations:

### 1. Transaction Savepoint Rollback Context
Wrap E2E test data creation inside transactional savepoints:
<!-- classification: illustrative -->
```bash
python tools/db_sandbox.py rollback-test --db-path "path/to/db.sqlite"
```
*Guarantees zero leftover records: state is automatically rolled back to pristine baseline upon test completion.*

### 2. Ephemeral Snapshot & Instant Restore (< 0.5s) [DESTRUCTIVE]
> ⚠️ **Warning [DESTRUCTIVE]:** Database restore drops existing tables/objects and repopulates from snapshot (e.g. `pg_restore --clean --if-exists`). Zero-pollution guarantee is conditional upon isolated sandbox containers and valid snapshots; never execute against staging or production databases. Requires explicit `--confirm` (or setting `SYNAPSE_FORCE_RESTORE=1`).
<!-- classification: illustrative -->
```bash
# Before test suite runs: capture pristine database baseline
python tools/db_sandbox.py snapshot --id pristine_baseline

# After suite execution: restore clean database (requires explicit --confirm)
python tools/db_sandbox.py restore --id pristine_baseline --confirm
```

### 3. Taint Pollution Audit & Cascading Purge
Scan all tables for orphan records carrying test prefixes (`AUTO_`, `TEST_`). By default, `audit` runs in **safe dry-run preview** mode:
<!-- classification: illustrative -->
```bash
# Preview orphan records without deleting (safe default):
python tools/db_sandbox.py audit

# Explicitly apply destructive purge:
python tools/db_sandbox.py audit --apply
```

---

## 4. Verification Points & DoD

1. Database seed data uses dynamic unique identifiers to eliminate collisions.
2. State assertions verify record existence, column values, and relational integrity.
3. Teardown routines remove test-generated records cleanly upon completion.

---

## 5. Handoff Protocol

- **Deliverables:** Database seeding scripts, state assertion queries, and teardown cleanup hooks.
- **Next Subagent:** api-engineer / test-runner
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
