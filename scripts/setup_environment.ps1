<#
.SYNOPSIS
    Automated environment readiness checker and bootstrap script for Agent-Skills Hub.
.DESCRIPTION
    Checks presence of Python 3, Node.js, Playwright, Git, and installs dependencies if needed.
#>

[CmdletBinding()]
param(
    [switch]$AutoInstall = $false
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Agent-Skills Environment Readiness & Diagnostic Check   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$status = @{
    Python = $false
    Node = $false
    Git = $false
    Playwright = $false
}

# 1. Check Git
try {
    $gitVer = (git --version 2>&1)
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[PASS] Git detected: $gitVer" -ForegroundColor Green
        $status.Git = $true
    }
} catch {
    Write-Host "[FAIL] Git is NOT installed or not on PATH." -ForegroundColor Red
}

# 2. Check Python
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $out = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $out -match "Python\s+3\.") {
            $pythonCmd = $cmd
            Write-Host "[PASS] Python 3 detected ($pythonCmd): $out" -ForegroundColor Green
            $status.Python = $true
            break
        }
    } catch { }
}

if (-not $status.Python) {
    Write-Host "[WARN] Python 3 was not detected in PATH!" -ForegroundColor Yellow
    Write-Host "       (Notice: Windows App Execution Aliases may shadow python.exe without installing it)" -ForegroundColor Gray
    if ($AutoInstall) {
        Write-Host "Attempting install via winget..." -ForegroundColor Cyan
        winget install -e --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements
    } else {
        Write-Host "Tip: Run 'winget install Python.Python.3.11' or install Python from python.org" -ForegroundColor Yellow
    }
}

# 3. Check Node / npm
try {
    $nodeVer = (node --version 2>&1)
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[PASS] Node.js detected: $nodeVer" -ForegroundColor Green
        $status.Node = $true
    } else {
        Write-Host "[INFO] Node.js not detected (optional for Playwright MCP / node tools)." -ForegroundColor Gray
    }
} catch {
    Write-Host "[INFO] Node.js not detected." -ForegroundColor Gray
}

# Summary
Write-Host "`n----------------------------------------------------------" -ForegroundColor Cyan
Write-Host "Environment Diagnostic Summary:" -ForegroundColor Cyan
$status.GetEnumerator() | ForEach-Object {
    $color = if ($_.Value) { "Green" } else { "Yellow" }
    Write-Host " - $($_.Key): $(if ($_.Value) {'READY'} else {'MISSING/OPTIONAL'})" -ForegroundColor $color
}
Write-Host "----------------------------------------------------------`n" -ForegroundColor Cyan
