# Enterprise Automation - E2E Flow Prober Wrapper
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) { $pythonCmd = Get-Command py -ErrorAction SilentlyContinue }
if (-not $pythonCmd) { $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue }

if ($pythonCmd) {
    & $pythonCmd.Source "$scriptDir\e2e_flow_prober.py" $args
    exit $LASTEXITCODE
} else {
    Write-Error "Python 3 is required to run e2e_flow_prober.py."
    exit 1
}
