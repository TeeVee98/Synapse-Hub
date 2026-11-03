---
name: technical-debt-harvester
description: "Harvest shortcut: comments into a tracked debt ledger so deliberate compromises do not rot into forgotten tech debt."
category: architecture_and_analysis
version: "1.0.0"
---

# Technical Debt Harvester — Pragmatic Shortcut & Deferral Tracker

Harvest deliberate shortcut comments (`shortcut: <limit>, <when to upgrade>`) across the entire repository into a structured Markdown ledger so pragmatic compromises do not silently rot into permanent defects.

---

## 1. The Shortcut Comment Standard

When writing lean code or taking a pragmatic shortcut under time or scope constraints, leave an inline comment specifying the **ceiling (limit)** and the **upgrade trigger**:

```python
# Format:
# shortcut: <the limit>, <when to upgrade>

# Examples:
# shortcut: max 100 items in memory, migrate to Redis if active sessions exceed 1,000
# shortcut: SQLite database, switch to PostgreSQL when concurrent writers > 5
```

Any shortcut comment that omits an upgrade trigger is classified as `no-trigger` and flagged for review.

---

## 2. Supported Comment Syntaxes

The harvester automatically detects markers across all common language comment styles:
- `# shortcut:` (Python, Bash, Ruby, YAML)
- `// shortcut:` (TypeScript, JavaScript, Java, Groovy, C++, Go, Rust, C#)
- `/* shortcut: ... */` (CSS, Multi-line blocks)
- `-- shortcut:` (SQL, Lua)
- `<!-- shortcut: ... -->` (HTML, XML, Markdown)

*(Also backwards compatible with older `ponytail:` comments).*

---

## 3. Automation CLI

```bash
# Scan working directory and display ledger
python3 tools/debt_harvester.py

# Save output to Markdown file
python3 tools/debt_harvester.py --output DEBT_LEDGER.md

# Output in JSON format for CI tooling
python3 tools/debt_harvester.py --json

# Scan with custom keyword
python3 tools/debt_harvester.py --keyword "DEBT:"
```

Or via the unified CLI:
```bash
agent-qa debt
agent-qa debt --output DEBT_LEDGER.md
```

---

## 4. Attribution

Adapted from **ponytail-debt** (https://github.com/DietrichGebert/ponytail) — MIT License, Copyright (c) 2026 DietrichGebert. Re-architected with native Python tooling for Synapse Hub.
