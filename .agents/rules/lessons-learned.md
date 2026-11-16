---
trigger: always_on
description: Critical anti-patterns, past mistakes, and strict avoidance rules (capped < 40 lines).
---

# Agent Anti-Pattern Blacklist & Failure Prevention

> **Policy:** Hot-memory lessons learned. Hard-capped at **Max 8 rules (< 40 lines, ~150 tokens)**.
> When table exceeds 8 rows, consolidate similar rules into higher-order invariants or archive to `~/.agent_memory/global_cache.db`.

| # | Mistake / Anti-Pattern | Root Cause | Mandatory Avoidance Rule |
|---|---|---|---|
| **1** | **XPath parsed as method** | Regex matched `String TXT = "...("`. | In Groovy, `=` before `(` denotes variable/constant, never method. |
| **2** | **GIS coordinate collision** | Hardcoded coordinates `(100, 200)`. | Randomize coordinates via dynamic bounding box/offset randomizer. |
| **3** | **`ElementClickIntercepted`** | Clicked while backdrop overlay was fading. | Wait for overlay detachment or bypass via JS dispatch (`clickJS`). |
| **4** | **Context blowout** | Read monolithic 4,000+ line Page Class. | Never read large files whole; query `tools/repo_map.txt` or read 20-50 lines. |
| **5** | **Flaky timing on CI** | `Thread.sleep` failed under network lag. | Replace with Smart Wait: Angular `isStable()` and CDP `Network Idle 0`. |
| **6** | **DB polluted with test junk** | Created entities without deletion. | Every data creation test case must execute idempotent teardown cleanup. |
| **7** | **CLI ran on Hub instead of target** | Defaulted to CWD=Hub without checking workspaces. | **Synapse-Hub is read-only hub, never CLI target.** Identify target workspace; outputs land there. |
| **8** | **Target test pollution on Hub** | Committed target tests inside Hub repo. | **Synapse-Hub holds 0 business tests.** All page classes/specs reside in target workspace. |

- **Feedback Cache:** On failed fix, persist via `agent-qa heal record-failed` to prevent repeat patches.
- **Overflow Policy:** Consolidate related patterns into a single invariant; offload edge cases to SQLite `~/.agent_memory/global_cache.db`.
