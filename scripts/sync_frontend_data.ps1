# Thin wrapper — canonical sync is scripts/sync_frontend_data.py
param([switch]$Quiet)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$argsList = @((Join-Path $Root "scripts\sync_frontend_data.py"))
if ($Quiet) { $argsList += "--quiet" }
& $py @argsList
exit $LASTEXITCODE
