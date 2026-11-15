# Enterprise MCP Excel Server Wrapper
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) { $pythonCmd = Get-Command py -ErrorAction SilentlyContinue }
if (-not $pythonCmd) { $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue }

if ($pythonCmd) {
    & $pythonCmd.Source "$scriptDir\mcp_excel_server.py" $args
    exit $LASTEXITCODE
} else {
    Write-Error "Python 3 is required to run mcp_excel_server.py."
    exit 1
}
