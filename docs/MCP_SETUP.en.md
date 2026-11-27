# Model Context Protocol (MCP) Server Setup Guide — Synapse Hub

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Introduction

Synapse Hub provides a standard **Model Context Protocol (MCP)** server (JSON-RPC 2.0 stdio), enabling AI coding assistants (Cursor, Claude Code, Windsurf, Google Antigravity, GitHub Copilot) to directly invoke automated QA testing tools, semantic AST linters, and quality verification gates.

### Core 5 MCP Tools (Tier-S Standard):

| Tool Name | Capability Description | Input Parameters |
|---|---|---|
| `synapse_lint` | Runs static defect sentinel and AST analyzer catching fake passes, static sleeps, empty catches. | `target_path`: file or directory path. |
| `synapse_verify` | Validates the 10 Definition-of-Done (DoD) Quality Gates with pre-flight integrity check. | `repo_path`: repository root path (default: CWD). |
| `synapse_mutate` | Executes AST micro-mutation testing measuring test assertion sensitivity against bugs. | `test_file`: test file path, `sample_rate`: sample rate (0.0-1.0). |
| `synapse_distill_logs` | Distills noisy test logs (>500 lines) into a token-efficient root cause summary. | `log_path`: path to log file. |
| `synapse_security_scan` | Audits Python/NPM dependencies and credentials in fail-closed strict mode. | `repo_path`: repository directory, `strict`: boolean (default: true). |

---

## 2. 1-Minute Quick Setup Guides

### 2.1 Cursor IDE (`.cursor/mcp.json`)

Create or update `.cursor/mcp.json` in your project root or user config:

```json
{
  "mcpServers": {
    "synapse-hub": {
      "command": "node",
      "args": ["bin/agent-qa.js", "mcp"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

*Or invoke Python directly:*

```json
{
  "mcpServers": {
    "synapse-hub": {
      "command": "python",
      "args": ["tools/mcp/mcp_server.py"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

---

### 2.2 Claude Desktop (`claude_desktop_config.json`)

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "synapse-hub": {
      "command": "python",
      "args": ["D:/Synapse Hub/tools/mcp/mcp_server.py"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

---

### 2.3 Windsurf (`~/.codeium/windsurf/mcp_config.json`)

```json
{
  "mcpServers": {
    "synapse-hub": {
      "command": "npx",
      "args": ["@teevee98/synapse-hub", "mcp"]
    }
  }
}
```

---

### 2.4 Google Antigravity

In plugin manifest or IDE settings (`antigravity.config.json`):

```json
{
  "mcpServers": {
    "synapse-hub": {
      "command": "python",
      "args": ["tools/mcp/mcp_server.py"]
    }
  }
}
```

---

### 2.5 OpenAI Codex (`.codex/config.toml` / `~/.codex/config.toml`)

**Option 1 — 1-click project bootstrap (recommended):**
Run inside any target project to automatically generate `AGENTS.md`, `.codex/config.toml` (MCP), and export Synapse skills into `.agents/skills/`:

```bash
npx @teevee98/synapse-hub setup --target . --ide codex
```

**Option 2 — Manual configuration in `~/.codex/config.toml` (Client Mode via `npx`):**

```toml
[mcp_servers.synapse-hub]
command = "npx"
args = ["-y", "@teevee98/synapse-hub", "mcp"]
# Windows note: if Codex cannot resolve `npx` on PATH, set command = "npx.cmd"

[mcp_servers.synapse-hub.env]
PYTHONIOENCODING = "utf-8"
SYNAPSE_MODE = "client"
```

*Or register via Codex CLI / run directly from a local Hub checkout:*

```bash
codex mcp add synapse-hub -- npx -y @teevee98/synapse-hub mcp
```

```toml
# Local Synapse Hub repository (.codex/config.toml):
[mcp_servers.synapse-hub]
command = "python"
args = ["tools/mcp/mcp_server.py"]

[mcp_servers.synapse-hub.env]
PYTHONIOENCODING = "utf-8"
SYNAPSE_MODE = "hub"
```

---

## 3. Verifying Connection

Run the following commands to confirm MCP server availability:

```bash
# Verify via Node CLI launcher
node bin/agent-qa.js mcp --help

# Verify via Python engine
python tools/mcp/mcp_server.py --help
```
