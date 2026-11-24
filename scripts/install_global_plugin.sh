#!/bin/bash
# Enterprise Synapse-Hub Global Antigravity Plugin Installer (macOS / Linux)
# ======================================================================
# Mounts Synapse-Hub directly into Google Antigravity's Global Plugin Directory.
# Once installed, all 57 skills and 9 subagents are active across all projects automatically.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo "======================================================================"
echo "   SYNAPSE-HUB: ANTIGRAVITY GLOBAL PLUGIN 1-CLICK INSTALLER           "
echo "======================================================================"
echo ""

# Preflight Validation Guard
echo "[Preflight] Checking repository integrity..."
SKILLS_SRC="$REPO_ROOT/skills"
[ ! -d "$SKILLS_SRC" ] && SKILLS_SRC="$REPO_ROOT/.agents/skills"
if [ ! -d "$SKILLS_SRC" ]; then
    echo "❌ [PREFLIGHT FAILED] Missing skills directory in $REPO_ROOT"
    exit 1
fi

AGENTS_SRC="$REPO_ROOT/ai-agents"
[ ! -d "$AGENTS_SRC" ] && AGENTS_SRC="$REPO_ROOT/.agents/agents"
if [ ! -d "$AGENTS_SRC" ]; then
    echo "❌ [PREFLIGHT FAILED] Missing ai-agents directory in $REPO_ROOT"
    exit 1
fi

if [ ! -d "$REPO_ROOT/tools" ]; then
    echo "❌ [PREFLIGHT FAILED] Missing tools directory in $REPO_ROOT"
    exit 1
fi

SKILLS_COUNT=$(find "$SKILLS_SRC" -mindepth 2 -maxdepth 2 -type d | wc -l | tr -d ' ')
[ "$SKILLS_COUNT" -eq 0 ] && SKILLS_COUNT=$(find "$SKILLS_SRC" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
AGENTS_COUNT=$(find "$AGENTS_SRC" -maxdepth 2 -type f -name "*.md" | wc -l | tr -d ' ')
echo "  [OK] Verified source integrity: $SKILLS_COUNT skills, $AGENTS_COUNT agent/workflow profiles."

PLUGINS_DIR="$HOME/.gemini/config/plugins"
TARGET_PLUGIN_DIR="$PLUGINS_DIR/synapse-hub"

mkdir -p "$PLUGINS_DIR"
mkdir -p "$TARGET_PLUGIN_DIR"

echo "[1/4] Copying plugin manifest..."
cp "$REPO_ROOT/plugin.json" "$TARGET_PLUGIN_DIR/plugin.json"
[ -f "$REPO_ROOT/agents_manifest.json" ] && cp "$REPO_ROOT/agents_manifest.json" "$TARGET_PLUGIN_DIR/agents_manifest.json"
[ -f "$REPO_ROOT/README.md" ] && cp "$REPO_ROOT/README.md" "$TARGET_PLUGIN_DIR/README.md"

echo "[2/4] Symlinking skills, agents, commands, and tools..."
ln -sfn "$SKILLS_SRC" "$TARGET_PLUGIN_DIR/skills"
ln -sfn "$AGENTS_SRC" "$TARGET_PLUGIN_DIR/ai-agents"
[ -d "$REPO_ROOT/commands" ] && ln -sfn "$REPO_ROOT/commands" "$TARGET_PLUGIN_DIR/commands"
ln -sfn "$REPO_ROOT/tools" "$TARGET_PLUGIN_DIR/tools"

mkdir -p "$TARGET_PLUGIN_DIR/rules"
if [ -f "$REPO_ROOT/templates/ai_bridges/CLAUDE.md" ]; then
    cp "$REPO_ROOT/templates/ai_bridges/CLAUDE.md" "$TARGET_PLUGIN_DIR/rules/AGENTS.md"
else
    cp "$REPO_ROOT/AGENTS.md" "$TARGET_PLUGIN_DIR/rules/AGENTS.md"
fi

echo "[3/4] Initializing Central Agent Memory (SQLite Cache)..."
python3 "$REPO_ROOT/tools/core/cache_resolver.py" init 2>/dev/null || python "$REPO_ROOT/tools/core/cache_resolver.py" init 2>/dev/null || true

echo ""
echo "======================================================================"
echo "  🎉 SUCCESS: Synapse-Hub is now installed as a GLOBAL PLUGIN!        "
echo "======================================================================"
echo "• Location : $TARGET_PLUGIN_DIR"
echo "• Skills   : $SKILLS_COUNT Standardized QA Skills"
echo "• Agents   : $AGENTS_COUNT Swarm Subagent Profiles"
echo ""
echo "👉 Antigravity will now automatically load Synapse-Hub across ALL projects"
echo "   without needing to add Synapse-Hub as a workspace folder!"
echo "======================================================================"
echo ""
