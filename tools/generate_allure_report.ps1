# Enterprise Automation - Allure Report Generator Wrapper
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) { $pythonCmd = Get-Command py -ErrorAction SilentlyContinue }
if (-not $pythonCmd) { $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue }

if ($pythonCmd) {
    & $pythonCmd.Source "$scriptDir\generate_allure_report.py" $args
    exit $LASTEXITCODE
} else {
    Write-Error "Python 3 is required to run generate_allure_report.py."
    exit 1
}
