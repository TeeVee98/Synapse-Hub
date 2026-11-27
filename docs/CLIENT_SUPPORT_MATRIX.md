# Client Support & Host Interoperability Matrix

> **Synapse Hub Enterprise QA Automation Platform**  
> **Author:** Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>  
> **License:** MIT License  
> **Last Updated:** 2026-11-24  

This document formalizes AI client and IDE host compatibility, distinguishing fully verified integration targets from experimental or unverified environments.

---

## 1. Comprehensive Host Support Matrix

| Client Host | Classification | Discovery / Hook Path | Scope / Capabilities | Limitations / Caveats |
| :--- | :---: | :--- | :--- | :--- |
| **Google Antigravity** | **Verified** | `skills/*/SKILL.md`<br/>`.agents/skills/*/SKILL.md`<br/>`plugin.json`<br/>`agentskills.json` | Subagents, custom tools, rules router, MCP servers, episodic memory | Requires Antigravity environment |
| **Claude Code** | **Verified** | `CLAUDE.md`<br/>`templates/ai_bridges/CLAUDE.md` | Workspace instructions, CLI command execution, tool calls | In-context prompt adherence only; single agent loop |
| **Cursor IDE** | **Verified** | `.cursorrules`<br/>`.cursor/rules/synapse-qa.mdc` | Glob-matched file rules (`globs: **/*`), inline assistant, Composer | No background multi-agent swarm; single workspace |
| **GitHub Copilot** | **Verified** | `.github/copilot-instructions.md`<br/>`.github/instructions/*.instructions.md` | Path-specific instructions (`applyTo:`), Copilot Chat, CLI assistance | Chat and inline code suggestions only; no tool orchestration |
| **Windsurf** | **Verified** | `.windsurfrules`<br/>`templates/ai_bridges/windsurfrules` | Cascade engine directives, scratchpad, agent pair-programming | Single-agent chat flow |
| **OpenAI Codex** | **Verified** | `AGENTS.md`<br/>`.codex/config.toml`<br/>`.agents/skills/*/SKILL.md`<br/>`templates/ai_bridges/AGENTS.md`<br/>`templates/ai_bridges/codex_config.toml` | Workspace `AGENTS.md` directives, MCP stdio server (`synapse-hub`), native `.agents/skills/` discovery, CLI/shell verification | Client repos require `npx @teevee98/synapse-hub setup --ide codex` (or `--ide all`) and trusted `.codex/config.toml` |
| **Node.js / NPX CLI** | **Verified** | `bin/agent-qa.js`<br/>`package.json` | Global CLI execution (`agent-qa`, `npx @teevee98/synapse-hub`) | Requires Node.js >= 18.0.0 |
| **Python CLI** | **Verified** | `tools/core/cli.py`<br/>`pyproject.toml` | Full toolsuite execution (`agent-qa`, `synapse-hub`) | Requires Python >= 3.10 |
| **OpenCode** | **Unverified / Experimental** | In-context prompt injection | Code generation & execution traces | Experimental; no standardized repository hook specification |
| **Goose** | **Unverified / Experimental** | Generic agent instructions | Task automation via MCP | Unverified CLI profile |
| **Devin / Cline** | **Unverified / Experimental** | Workspace instructions fallback | Autonomous web/CLI workflows | Unverified host configuration |

---

## 2. Integration Tiers & Host Requirements

### Tier A: Native Multi-Agent & Rule Routing (Verified)
- **Google Antigravity:** Full support for 57 QA skills, subagent swarm orchestrator, rules routing, and MCP servers.
- **Node.js & Python CLIs:** Production package distributions supporting hermetic standalone execution.

### Tier B: Synchronized IDE & CLI Agent Bridges (Verified)
- **OpenAI Codex, Claude Code, Cursor IDE, Windsurf, GitHub Copilot:**
  - Synchronized via `python tools/core/sync_agent_rules.py`.
  - Single source of truth is `AGENTS.md`.
  - Scope isolation: Template bridges deployed to client projects (`templates/ai_bridges/*`) omit Synapse-Hub-only CLI tools and reference project-native runners (`npm test`, `pytest`) and `npx @teevee98/synapse-hub`.
  - For **OpenAI Codex**, `npx @teevee98/synapse-hub setup --ide codex` (or `--ide all`) also deploys `.codex/config.toml` (MCP server) and exports Synapse skills into `.agents/skills/` for native progressive-disclosure skill routing.

### Tier C: Unverified / Experimental Hosts
- Host platforms that lack dedicated configuration hook formats (such as OpenCode, Goose, Devin, Cline) rely on prompt fallback or generic workspace ingestion.
- These hosts must be tested on a case-by-case basis before relying on autonomous execution.
