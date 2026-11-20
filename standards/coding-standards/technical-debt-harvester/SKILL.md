---
name: technical-debt-harvester
description: "Harvest shortcut: comments into a tracked technical debt ledger. Use when auditing code compromises, tracking deferred refactorings, or scanning for shortcut markers."
category: architecture_and_analysis
version: "1.0.0"
policies:
  network: none
  shell: read-only
  filesystem: read-only
---
# Technical Debt Harvester — Pragmatic Shortcut & Deferral Tracker

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Harvest shortcut: comments into a tracked technical debt ledger. Use when auditing code compromises, tracking deferred refactorings, or scanning for shortcut markers.
- **Activation Scope:** Domain workflows for `08-code-quality` involving `technical-debt-harvester`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT hide or disguise technical shortcuts; mark every deliberate simplification explicitly.
- Do NOT leave shortcut comments without stating the operational limit and upgrade trigger.
- Do NOT alter code behavior when harvesting or indexing debt markers.
- **Sibling Skill Boundaries:**
  - lean-code-ladder allows pragmatic shortcuts; technical-debt-harvester tracks, catalogs, and schedules debt retirement.

---

## 3. Ordered Execution Workflow

Harvest deliberate shortcut comments (`shortcut: <limit>, <when to upgrade>`) across the entire repository into a structured Markdown ledger so pragmatic compromises do not silently rot into permanent defects.

---

### The Shortcut Comment Standard

When writing lean code or taking a pragmatic shortcut under time or scope constraints, leave an inline comment specifying the **ceiling (limit)** and the **upgrade trigger**:

<!-- classification: illustrative -->
```python
# Format:
# shortcut: <the limit>, <when to upgrade>

# Examples:
# shortcut: max 100 items in memory, migrate to Redis if active sessions exceed 1,000
# shortcut: SQLite database, switch to PostgreSQL when concurrent writers > 5
```

Any shortcut comment that omits an upgrade trigger is classified as `no-trigger` and flagged for review.

---

### Supported Comment Syntaxes

The harvester automatically detects markers across all common language comment styles:
- `# shortcut:` (Python, Bash, Ruby, YAML)
- `// shortcut:` (TypeScript, JavaScript, Java, Groovy, C++, Go, Rust, C#)
- `/* shortcut: ... */` (CSS, Multi-line blocks)
- `-- shortcut:` (SQL, Lua)
- `<!-- shortcut: ... -->` (HTML, XML, Markdown)

*(Also backwards compatible with older `ponytail:` comments).*

---

### Automation CLI

<!-- classification: illustrative -->
```bash
# Scan working directory and display ledger
python3 tools/core/debt_harvester.py

# Save output to Markdown file
python3 tools/core/debt_harvester.py --output DEBT_LEDGER.md

# Output in JSON format for CI tooling
python3 tools/core/debt_harvester.py --json

# Scan with custom keyword
python3 tools/core/debt_harvester.py --keyword "DEBT:"
```

Or via the unified CLI:
<!-- classification: illustrative -->
```bash
agent-qa debt
agent-qa debt --output DEBT_LEDGER.md
```

---

### Attribution

Adapted from **ponytail-debt** (https://github.com/DietrichGebert/ponytail) — MIT License, Copyright (c) 2026 DietrichGebert. Re-architected with native Python tooling for Synapse Hub.

---

## 4. Verification Points & DoD

1. All deliberate simplifications adhere to `shortcut: <the limit>, <when to upgrade>` syntax.
2. Automated debt scan parses all active shortcuts across the repository.
3. Debt ledger prioritizes items by operational risk and upgrade urgency.

---

## 5. Handoff Protocol

- **Deliverables:** Technical debt inventory report, shortcut registry ledger, and retirement roadmap.
- **Next Subagent:** quality-gatekeeper
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
