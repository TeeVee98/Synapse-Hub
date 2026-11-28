# Client Support & Host Interoperability Matrix

> **Synapse Hub Enterprise QA Automation Platform**  
> **Author:** Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>  
> **License:** MIT License  
> **Last Updated:** 2026-11-28  

This document derives all client and runtime support claims strictly from versioned, reproducible verification evidence. Any combination without live execution evidence is explicitly marked `Configuration Only` or `Pending` rather than `Verified`.

---

## 1. Evidence-Backed Host & Runtime Support Matrix

| Client Host / Runtime | Support State | Version | Evidence Date | Run Reference | Verified Scope & Caveats |
| :--- | :---: | :--- | :---: | :--- | :--- |
| **Node.js / NPX CLI (`@teevee98/synapse-hub`)** | **Verified** | `4.11.0` (Node >= 18) | `2026-11-28` | `tests/test_packaging_parity.py`, `tests/test_model_registry.py`, `tests/test_support_claims.py` | Clean npm tarball packing, 18-model registry parity, setup CLI execution, and upgrade skill-byte preservation |
| **Python CLI (`synapse-hub`)** | **Verified** | `4.11.0` (Python >= 3.10) | `2026-11-28` | `tests/test_packaging_parity.py`, `tests/test_model_registry.py`, `tests/test_support_claims.py` | Clean wheel parity for 57 domain skills, `solo`/`review`/`super-plan`, and 18-model packaged registry resolution |
| **Google Antigravity** | **Configuration Only** | `4.11.0` | `2026-11-28` | `tools/core/sync_agent_rules.py`, `docs/CLIENT_SUPPORT_MATRIX.md` | Static bridge (`skills/`, `.agent/skills/`, `plugin.json`, `agentskills.json`); full IDE session pending supervised receipt |
| **OpenAI Codex** | **Configuration Only** | `4.11.0` | `2026-11-28` | `tests/test_codex_discovery_evidence.py`, `tests/test_support_claims.py` | File deployment (`AGENTS.md`, `.codex/config.toml`, `.agents/skills/`) verified; live Codex transcript required to promote to `Verified` |
| **Claude Code** | **Configuration Only** | `4.11.0` | `2026-11-28` | `tools/core/sync_agent_rules.py` | Generated `CLAUDE.md` and `.claude/commands/*`; unsupervised live IDE transcript pending |
| **Cursor IDE** | **Configuration Only** | `4.11.0` | `2026-11-28` | `tools/core/sync_agent_rules.py` | Generated `.cursorrules` and `.cursor/rules/synapse-qa.mdc`; live Composer session pending |
| **GitHub Copilot** | **Configuration Only** | `4.11.0` | `2026-11-28` | `tools/core/sync_agent_rules.py` | Generated `.github/copilot-instructions.md` and `.github/instructions/*.instructions.md`; live IDE check pending |
| **Windsurf** | **Configuration Only** | `4.11.0` | `2026-11-28` | `tools/core/sync_agent_rules.py` | Generated `.windsurfrules`; live Cascade session pending |
| **Accessibility Screen-Reader Support** | **Pending** | `4.11.0` | `2026-11-28` | `docs/accessibility-pilot.md`, `examples/playwright-crm-suite/tests/accessibility.spec.ts` | Automated Chromium keyboard journey passes; support claim remains pending supervised VoiceOver/NVDA reviewer receipt |
| **OpenCode / Goose / Devin / Cline** | **Unverified / Experimental** | `N/A` | `2026-11-27` | `N/A` | Experimental fallback via generic `AGENTS.md` workspace ingestion; untested |

---

## 2. Reproducible Documented Smoke Commands

Run the following documented commands from a clean client workspace before claiming support on a target platform:

```bash
node bin/agent-qa.js --help
node bin/agent-qa.js setup --ide codex
python3 tools/core/cli.py --help
```

- Single source of truth for agent rules is `AGENTS.md` (synchronized via `python tools/core/sync_agent_rules.py`).
- Template bridges (`templates/ai_bridges/*`) deployed to client repositories omit Synapse-Hub-only CLI commands and target native test runners (`npm test`, `pytest`).
