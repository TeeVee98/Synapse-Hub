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

## 9. ponytail (DietrichGebert/ponytail) — MIT

Lazy senior developer plugin for Claude Code and agentic coding workflows.

- **Provenance:** Created by DietrichGebert (<https://github.com/DietrichGebert/ponytail>) under the MIT License.
- **Hub Inspiration:** Core concepts adapted into Synapse-Hub include the 7-rung reuse ladder (`lean-code-ladder`), technical debt harvesting (`technical-debt-harvester` & `tools/debt_harvester.py`), 6-pillar code review (`senior-code-review` & `tools/senior_code_review.py`), and whole-repo audit (`repo-quality-audit`).
- **Hub Adaptations:** Re-scoped specifically for enterprise automated testing suites, Clean POM architecture, and 0-token AST verification.

## 10. superpowers (obra/superpowers) — MIT

Discipline and rigor framework created by Jesse Vincent (<https://github.com/obra/superpowers>).
- **Adopted Patterns:** Subagent Driven Development contracts (`subagent-driven-dev`), ephemeral git worktree isolation (`using-git-worktrees` & `tools/git_worktree_manager.py`), verification before completion, and systematic debugging.

## 11. gstack (garrytan/gstack) — MIT

Virtual C-Suite engineering team created by Garry Tan (<https://github.com/garrytan/gstack>).
- **Adopted Patterns:** Runaway Stopper sentinel (`runaway-stopper` & `tools/runaway_stopper.py`) preventing runaway loops and context window exhaustion, and Chief Security Officer review (`cso-security-audit`).
- **Hub Enforcement:** Enforced 100% Pure Headless browser invariant (rejecting GUI browser launches).

## 12. ui-ux-pro-max (nextlevelbuilder/ui-ux-pro-max-skill) — MIT

Design intelligence framework created by NextLevelBuilder (<https://github.com/nextlevelbuilder/ui-ux-pro-max-skill>).
- **Adopted Patterns:** BM25 local catalog indexing (`ui-ux-design-intelligence`) to select studio color palettes and typographic scales in < 400 tokens without polluting context.

## 13. caveman (JuliusBrussee/caveman) — MIT

Terse token optimizer created by Julius Brussee (<https://github.com/JuliusBrussee/caveman>).
- **Adopted Patterns:** Caveman shrink token compression integrated into `tools/distill_log.py` (--shrink) to reduce log/catalog tokens by 33-65% while keeping 100% stack traces and failure details.

## 14. taste-skill (Leonxlnx/taste-skill) — MIT

Mechanical design and finish gate created by Leonxlnx (<https://github.com/Leonxlnx/taste-skill>).
- **Adopted Patterns:** Mechanical layout, contrast, and fold-cut gate (`mechanical-finish-gate` & `tools/mechanical_ui_gate.py`) integrated into Quality Gate 9.

## 15. diagram-design (cathrynlavery/diagram-design) — MIT

Standalone SVG/HTML diagram architecture created by Cathryn Lavery (<https://github.com/cathrynlavery/diagram-design>).
- **Adopted Patterns:** Self-contained SVG+HTML architecture and flow generation (`self-contained-diagram-architect` & `tools/diagram_architect.py`) eliminating Mermaid dependencies and rendering failures.

## 16. hallmark (Nutlope/hallmark) — MIT

Together AI anti-slop design system created by Hassan El Mghari (<https://github.com/Nutlope/hallmark>).
- **Adopted Patterns:** Mechanical anti-slop checks integrated into `tools/humanize_linter.py` and `tools/mechanical_ui_gate.py`.


