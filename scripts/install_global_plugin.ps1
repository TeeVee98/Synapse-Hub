# Enterprise Synapse-Hub Global Antigravity Plugin Installer (Windows)
# ======================================================================
# Mounts Synapse-Hub directly into Google Antigravity's Global Plugin Directory.
# Once installed, all 57 skills and 9 subagents are active across all projects automatically.

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path "$ScriptDir\.."

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "   SYNAPSE-HUB: ANTIGRAVITY GLOBAL PLUGIN 1-CLICK INSTALLER           " -ForegroundColor Cyan
Write-Host "======================================================================`n" -ForegroundColor Cyan

# Preflight Validation Guard
Write-Host "[Preflight] Checking repository integrity..." -ForegroundColor Yellow
$SkillsSrc = if (Test-Path "$RepoRoot\skills") { "$RepoRoot\skills" } else { "$RepoRoot\.agents\skills" }
$AgentsSrc = if (Test-Path "$RepoRoot\ai-agents") { "$RepoRoot\ai-agents" } else { "$RepoRoot\.agents\agents" }
$RequiredPaths = @(
    $SkillsSrc,
    $AgentsSrc,
    "$RepoRoot\tools"
)
foreach ($p in $RequiredPaths) {
    if (-not (Test-Path $p)) {
        Write-Error "❌ [PREFLIGHT FAILED] Mandatory source path missing: $p"
        exit 1
    }
}
$SkillsCount = (Get-ChildItem -Path $SkillsSrc -Directory -Recurse -Depth 1 | Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") }).Count
$AgentsCount = (Get-ChildItem -Path $AgentsSrc -File -Filter "*.md" -Recurse).Count
Write-Host "  [OK] Verified source integrity: $SkillsCount skills, $AgentsCount agent/workflow profiles.`n" -ForegroundColor Green

$PluginsDir = "$HOME\.gemini\config\plugins"
$TargetPluginDir = "$PluginsDir\synapse-hub"

if (-not (Test-Path $PluginsDir)) {
    Write-Host "[1/5] Creating Antigravity plugins directory: $PluginsDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $PluginsDir -Force | Out-Null
} else {
    Write-Host "[1/5] Antigravity plugins directory verified: $PluginsDir" -ForegroundColor Green
}

# Ensure clean target directory
if (-not (Test-Path $TargetPluginDir)) {
    Write-Host "[2/5] Creating plugin bundle directory: $TargetPluginDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $TargetPluginDir -Force | Out-Null
} else {
    Write-Host "[2/5] Plugin bundle directory exists: $TargetPluginDir" -ForegroundColor Green
}

# 1. Copy plugin.json, agents_manifest.json & README.md
Write-Host "[3/5] Copying plugin manifest (plugin.json)..." -ForegroundColor Yellow
Copy-Item "$RepoRoot\plugin.json" "$TargetPluginDir\plugin.json" -Force
if (Test-Path "$RepoRoot\agents_manifest.json") {
    Copy-Item "$RepoRoot\agents_manifest.json" "$TargetPluginDir\agents_manifest.json" -Force
}
if (Test-Path "$RepoRoot\README.md") {
    Copy-Item "$RepoRoot\README.md" "$TargetPluginDir\README.md" -Force
}

# 2. Setup skills, agents, commands, and tools via NTFS Junctions (Instant, zero duplication)
Write-Host "[4/5] Linking skills, agents, commands, and rules into Global Plugin..." -ForegroundColor Yellow

$SkillsLink = "$TargetPluginDir\skills"
$AgentsLink = "$TargetPluginDir\ai-agents"
$CommandsLink = "$TargetPluginDir\commands"
$ToolsLink = "$TargetPluginDir\tools"
$RulesDir = "$TargetPluginDir\rules"

# Skills Junction
if (Test-Path $SkillsLink) {
    (Get-Item $SkillsLink).Delete()
}
New-Item -ItemType Junction -Path $SkillsLink -Target $SkillsSrc | Out-Null
Write-Host "  • Linked skills  : $SkillsLink -> $SkillsSrc" -ForegroundColor Green

# Agents Junction
if (Test-Path $AgentsLink) {
    (Get-Item $AgentsLink).Delete()
}
New-Item -ItemType Junction -Path $AgentsLink -Target $AgentsSrc | Out-Null
Write-Host "  • Linked agents  : $AgentsLink -> $AgentsSrc" -ForegroundColor Green

# Commands Junction
if (Test-Path "$RepoRoot\commands") {
    if (Test-Path $CommandsLink) {
        (Get-Item $CommandsLink).Delete()
    }
    New-Item -ItemType Junction -Path $CommandsLink -Target "$RepoRoot\commands" | Out-Null
    Write-Host "  • Linked commands: $CommandsLink -> $RepoRoot\commands" -ForegroundColor Green
}

# Tools Junction
if (Test-Path $ToolsLink) {
    (Get-Item $ToolsLink).Delete()
}
New-Item -ItemType Junction -Path $ToolsLink -Target "$RepoRoot\tools" | Out-Null
Write-Host "  • Linked tools   : $ToolsLink -> $RepoRoot\tools" -ForegroundColor Green

# Rules directory & client-safe AGENTS.md
if (-not (Test-Path $RulesDir)) {
    New-Item -ItemType Directory -Path $RulesDir -Force | Out-Null
}
$RulesSrc = if (Test-Path "$RepoRoot\templates\ai_bridges\CLAUDE.md") { "$RepoRoot\templates\ai_bridges\CLAUDE.md" } else { "$RepoRoot\AGENTS.md" }
Copy-Item $RulesSrc "$RulesDir\AGENTS.md" -Force
Write-Host "  • Deployed rules : $RulesDir\AGENTS.md" -ForegroundColor Green

# 3. Initialize SQLite Cache
Write-Host "`n[5/5] Initializing Central Agent Memory (SQLite Cache)..." -ForegroundColor Yellow
try {
    python "$RepoRoot\tools\core\cache_resolver.py" init
} catch {
    Write-Host "  (Notice: cache_resolver init will run when Python is invoked)" -ForegroundColor DarkGray
}

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "  🎉 SUCCESS: Synapse-Hub is now installed as a GLOBAL PLUGIN!        " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "• Location : $TargetPluginDir" -ForegroundColor White
Write-Host "• Skills   : $SkillsCount Standardized QA Skills" -ForegroundColor White
Write-Host "• Agents   : $AgentsCount Swarm Subagent Profiles" -ForegroundColor White
Write-Host "`n👉 Antigravity will now automatically load Synapse-Hub across ALL projects" -ForegroundColor Yellow
Write-Host "   without needing to add Synapse-Hub as a workspace folder!" -ForegroundColor Yellow
Write-Host "======================================================================`n" -ForegroundColor Cyan
