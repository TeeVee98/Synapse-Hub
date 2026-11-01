# Adopted Ecosystem Tools Guide

Companion guide to the seven skills adopted from the open-source Claude ecosystem (see `NOTICE`, entries 16-21). The items below are **external tools that are recommended but NOT copied into this repository** — they run outside the hub, so this page records only vetted install/config snippets and the token-discipline rules that apply when using them.

> **Rule:** any tool here is activated on-demand only (Zero-Command Autoproactivity, `AGENTS.md` Section 3). Never install or run one blindly, and never paste API keys into committed files (Gate 6).

## 1. github-mcp (github/github-mcp-server) — MIT

Official MCP server exposing GitHub (issues, PRs, Actions, security) to agents. Primary hub use: `orchestrator` / `failure-analyst` filing bug tickets and reading CI failures.

```bash
# Local via Docker, read-only, minimal toolsets (token discipline)
claude mcp add github \
  -e GITHUB_PERSONAL_ACCESS_TOKEN \
  -- docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN \
  ghcr.io/github/github-mcp-server \
  --read-only --toolsets "repos,issues,pull_requests,actions"
```

- Use a minimum-scope PAT; prefer the `--read-only` flag for agent sessions.
- Enable only the toolsets a task needs — every loaded toolset costs context.

## 2. playwright-mcp (microsoft/playwright-mcp) — Apache-2.0

Browser control over the accessibility tree (~78 tools). Primary hub use: `live-explorer` fallback when scripted helpers are not enough.

```bash
claude mcp add playwright -- npx @playwright/mcp@latest \
  --headless --caps "testing,network"
```

- Enable capability flags selectively (`--caps`); the full surface is a context hog.
- Snapshot mode is the main token cost: prefer `browser_find`/targeted probes over full-page snapshots, and disable snapshots for pure action sequences.
- The hub's `playwright-live-interaction` skill and `tools/browser_helpers.js` remain the default; MCP is the agentic-loop complement (long stateful browser sessions).

## 3. cc-switch (farion1231/cc-switch) — MIT

Desktop app managing provider/API configs for many AI coding tools at once.

- Relevant hub fit: its Skills-sync panel targets `~/.agents/skills`, matching this hub's layout; its usage dashboard tracks quota/token consumption per provider — useful against the manual telemetry footer.
- Install from the project releases; run fully local. Cloud sync (WebDAV/S3) is optional and off by default.

## 4. claude-hud (jarrodwatts/claude-hud) — MIT

Statusline HUD showing context usage, 5h/7-day quota, cache hit rate, and cost.

```bash
/plugin marketplace add jarrodwatts/claude-hud
/claude-hud:setup
```

- Automates the observation half of the hub's telemetry footer (quota, cache hit, token totals) without touching prompts or model behavior.

## 5. repomix (yamadashy/repomix) — MIT

Packs a repository into one AI-friendly file with per-file token counts.

```bash
npx repomix --compress        # tree-sitter skeleton pack, fewer tokens
```

- Hub use: onboarding artifacts for subagents, external audits. Secretlint integration aligns with Gate 6 (credential security).
- Run from the target project root; output is generated locally (`repomix-output.xml`), and `tools/repo_map.*` remains the hub's own compressed alternative.

## 6. graphify (Graphify-Labs/graphify) — Apache-2.0

Builds a queryable knowledge graph of a directory (tree-sitter AST, ~40 languages including Groovy).

- Hub use: maps Katalon `.groovy` suites and `tools/*.py` the hub's own AST tooling does not cover end-to-end; `graph.json` feeds blast-radius analysis alongside `tools/test_impact.py` and the `graphify-impact-analyzer` skill.
- Fully local for code (no LLM calls); run `graphify install` to register the skill with your agent host.

## 7. firecrawl (firecrawl/firecrawl) — AGPL-3.0

Web scraping/search API returning LLM-ready markdown. Recommended via **cloud tier + API key**, not self-host (the AGPL monorepo stack is heavy and license-incompatible to embed in this MIT repo — same policy as NOTICE entry 3).

```bash
npx firecrawl-mcp   # with FIRECRAWL_API_KEY set in the environment
```

- Hub use: Stage 1 Discovery data gathering for `live-explorer` when the target data lives outside the browser under test.

## 8. claude-code-router (musistudio/claude-code-router) — MIT

Local model gateway (default `127.0.0.1:3456`) with routing, retry, failover, and per-request token/cost logs.

- **Security note:** it is a man-in-the-middle for API keys — run strictly local, never expose the port, and audit its config before pointing production credentials at it.
- Hub use: route mechanical subagent work to cheaper models while keeping strong models for synthesis/review; its request logs match the hub telemetry fields (token in/out, cost).
