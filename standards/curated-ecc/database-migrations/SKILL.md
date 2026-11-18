---
name: database-migrations
description: >
  Reversible, non-locking database migration skill: design schema changes with
  expand-contract pattern, zero-downtime column additions, concurrent index builds,
  and automated rollback scripts. Use for any SQL or NoSQL schema evolution task.
version: 1.0.0
attribution: Adapted from ECC (affaan-m/ecc, Apache 2.0). Extended by Thế Vị (@TeeVee98).
---

# Database Migrations Skill (`database-migrations`)

## Overview

Every database migration must be **reversible, non-locking, and observable**. This skill enforces the Expand-Contract pattern to guarantee zero-downtime deployments and safe rollback paths.

> [!CAUTION]
> Never run a migration that holds an exclusive table lock for more than 1 second in
> production. Locking migrations are a deployment-time incident waiting to happen.

## When to Activate

- Adding, renaming, or dropping columns on tables with > 100k rows.
- Backfilling data while keeping the application live.
- Changing column types or adding NOT NULL constraints.
- Building indexes on large tables.

## The Expand-Contract Pattern

```
Phase 1 — EXPAND (backward compatible, deploy safely)
  ↓ Add new column as NULLABLE (never NOT NULL in one step)
  ↓ Deploy application code that writes BOTH old and new column
  ↓ Verify: dual-write working in production logs

Phase 2 — BACKFILL (batched, never full-table lock)
  ↓ Backfill in batches of 1000-5000 rows with sleep(10ms) between batches
  ↓ Monitor replication lag — pause backfill if lag > 10s

Phase 3 — CONTRACT (remove old column after full cutover)
  ↓ Deploy application code reading only new column
  ↓ Add NOT NULL constraint (safe after backfill is 100% complete)
  ↓ Drop old column in a separate migration
```

## Index Creation Rules

```sql
-- ✅ CORRECT: Non-locking concurrent index (PostgreSQL)
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);

-- ❌ FORBIDDEN: Blocking index creation on large tables
CREATE INDEX idx_users_email ON users(email);  -- Holds AccessShareLock
```

For MySQL/MariaDB, use `ALTER TABLE ... ALGORITHM=INPLACE, LOCK=NONE`.

## Migration File Template

```sql
-- migrations/V{timestamp}__add_user_tier.sql
-- Reversible: YES
-- Locking Risk: NONE (nullable column addition)
-- Estimated duration: < 100ms on 10M row table
-- Rollback: migrations/V{timestamp}__rollback_add_user_tier.sql

-- UP
ALTER TABLE users ADD COLUMN tier VARCHAR(20) NULL DEFAULT 'free';

-- Paired rollback script (always author rollback before running UP)
-- DOWN (in separate rollback file)
-- ALTER TABLE users DROP COLUMN tier;
```

## Rollback Protocol

> [!IMPORTANT]
> Every migration **must** ship with a paired rollback script. Migrations without
> rollback scripts are blocked by the QA Fact-Forcing Gate.

1. Author `V{n}__rollback_{name}.sql` in the same PR as `V{n}__{name}.sql`.
2. Test rollback on a staging snapshot before merge.
3. Record estimated rollback time in migration header comments.

## N+1 Query Detection

After any schema change, run the query analyzer:

```python
# python tools/core/fact_forcing_gate.py --target migrations/ --mode db
```

The gate detects:
- Missing indexes on foreign keys (N+1 risk).
- Full table scans on newly added columns.
- Unbounded `SELECT *` on joined tables.

## Non-Goals

- Do not use ORM auto-migrate in production (`alembic --autogenerate`, `django migrate` without review).
- Do not combine data migration + schema migration in a single transaction on large tables.
