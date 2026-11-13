---
name: qa-memory-os
description: "Hierarchical 3-tier memory operating system for test automation: Core Memory blocks, Recall step logs, and Archival semantic store with AUT version scoping. Use when managing long-term test session state, auth tokens, and preventing context rot."
---

# QA Test Memory OS Skill — Hierarchical Persistent Memory

> **Paradigm Attribution:** Inspired by **Letta AI / UC Berkeley SkyLab (MemGPT & MemFS)**.  
> **Core Principle:** Replace flat SQLite caches with a disciplined 3-tier memory operating system. Eliminate memory rot across application versions by tagging locator mutations and flaky histories with explicit AUT release versions.

---

## 1. The 3-Tier Architecture

```mermaid
flowchart TD
    subgraph MemoryOS["Hierarchical QA Test Memory OS (.agent_memory/qa_memory.db)"]
        Core["Tier 1: Core Memory Block<br/>Fast Key-Value JSON: AUT URL, Token Expiry, Feature Flags"]
        Recall["Tier 2: Recall Memory Log<br/>Sequential chronological timeline of execution steps"]
        Archival["Tier 3: Archival Semantic Store<br/>Cross-sprint locator mutations scoped by AUT version (v2.1 vs v2.2)"]
    end
    
    Clean["Hygiene & GC Daemon<br/>Secret scrubbing (zero passwords/tokens) & DB size < 50MB"]
    Core --> Clean
    Recall --> Clean
    Archival --> Clean
```

1. **Tier 1 — Core Memory (`core_memory`):**
   - Immediate in-context state: non-sensitive session metadata (token hash reference, expiration timestamp, user role, storage state path, AUT base URL).
   - Enables **Zero-Second Auth**: reuse active authenticated contexts without repeating UI login forms.
   - **Credential Hygiene Invariant:** Never store raw plaintext JWTs, passwords, or session cookies directly in memory logs or DB tables; store strictly non-sensitive metadata (e.g. SHA-256 fingerprint reference, expiry, role).

2. **Tier 2 — Recall Memory (`recall_memory`):**
   - Sequential audit log of subagent actions, navigation events, and errors.
   - Rotates or prunes records older than 30 days to save disk space.

3. **Tier 3 — Archival Memory (`archival_memory`):**
   - Permanent knowledge base of healed locators and historical flaky failure patterns.
   - **AUT Version Scoping (`aut_version`):** Queries can filter by release (e.g. `aut_version="v2.1"`). When the web app upgrades to `v2.2`, obsolete `v2.1` mutations are ignored, completely eliminating false cache hits (Memory Rot).

---

## 2. CLI Tool Usage

Autonomous commands via `tools/test_memory_os.py`:

```bash
# 1. Initialize memory OS database
python tools/test_memory_os.py init --db-path .agent_memory/qa_memory.db

# 2. Update active session state in Core Memory
python tools/test_memory_os.py update-core \
  --block auth_state \
  --data '{"token_expiry": "2026-11-05T00:00:00Z", "storage_state": "storage_state.json"}'

# 3. Store locator mutation in Archival Memory scoped by version
python tools/test_memory_os.py archival-insert \
  --key LOCATOR_MUTATION \
  --payload '{"page": "CheckoutPage", "old": "#submit-btn", "new": "button[data-testid=submit]"}' \
  --aut-version "v2.1" \
  --tags "checkout,submit,button"

# 4. Search archival memory with semantic token matching
python tools/test_memory_os.py archival-search \
  --query "Checkout submit button locator history" \
  --aut-version "v2.1" \
  --top-k 3 \
  --json

# 5. Run garbage collection and secret scrubbing
python tools/test_memory_os.py gc --scrub-secrets --max-age-days 30
```

---

## 3. Session Lifecycle & Teardown Protocol

```mermaid
flowchart LR
    A["Provision<br/>(One-time login)"] --> B["Validate<br/>(Check expiry & role)"]
    B --> C["Execute Tests<br/>(Inject non-sensitive state)"]
    C --> D["Teardown & Cleanup<br/>(Scrub tokens & delete state)"]
```

1. **Provisioning:** Generate authenticated session via setup fixture; record only non-sensitive metadata (`token_hash_ref`, `token_expiry`, `role`, `storage_state`) in Core Memory.
2. **In-Flight Validation:** Inspect token expiry epoch before test runs; trigger token refresh if expired.
3. **Automated Teardown & Invalidation:** On test completion or run failure, run GC cleanup to scrub session artifacts, delete ephemeral storage files, and invalidate cached tokens.

---

## 4. Strict Operating Invariants

- **Zero Plaintext Secrets:** Automatic regex masking for passwords, bearer tokens, and private keys (`[MASKED_SECRET]`). Only non-sensitive metadata (hash reference, expiry timestamp, role) may be persisted.
- **Session Cleanup Protocol:** Ephemeral storage state files and expired memory blocks must be purged during teardown via GC daemon (`tools/test_memory_os.py gc --scrub-secrets`).
- **Memory File Ceiling:** DB size strictly maintained under **50MB**.
- **Version Isolation:** Never apply archival locator patches across different incompatible AUT major versions.
