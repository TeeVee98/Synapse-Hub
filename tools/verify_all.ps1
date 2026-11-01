# Enterprise Single-Command DoD Verification Wrapper (Windows PowerShell)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) { $pythonCmd = Get-Command py -ErrorAction SilentlyContinue }
if (-not $pythonCmd) { $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue }

if ($pythonCmd) {
    & $pythonCmd.Source "$scriptDir\verify_all.py" $args
    exit $LASTEXITCODE
} else {
    Write-Error "Python 3 is required to run verify_all. Please install Python from https://python.org"
    exit 1
}
