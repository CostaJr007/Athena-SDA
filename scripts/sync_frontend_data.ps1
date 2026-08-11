# Athena-SDA — sync latest ML alert artifacts into the frontend public/ folder (Windows).
# Run after: python scripts/run_anomaly_monitor.py run-daily
param(
  [switch]$Quiet
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Src = Join-Path $Root "data\alerts"
$Dst = Join-Path $Root "src\frontend\public\data"
New-Item -ItemType Directory -Force -Path $Dst | Out-Null

function Copy-IfExists {
  param([string]$Name)
  $from = Join-Path $Src $Name
  if (Test-Path -LiteralPath $from) {
    Copy-Item -LiteralPath $from -Destination (Join-Path $Dst $Name) -Force
    if (-not $Quiet) { Write-Host "  + $Name" }
  } else {
    if (-not $Quiet) { Write-Host "  - missing $Name (skipped)" }
  }
}

Write-Host "Sync frontend data -> $Dst"
Copy-IfExists "risk_report_latest.json"
Copy-IfExists "anomalies_latest.json"
Copy-IfExists "proximity_latest.json"
Copy-IfExists "walkforward_summary.json"
Copy-IfExists "feature_ablation_latest.json"
Copy-IfExists "paper_validation_latest.json"

# Walk-forward per-event curves (event replay UI, patent 265 temporal tiles)
$WfSrc = Join-Path $Src "walkforward"
$WfDst = Join-Path $Dst "walkforward"
if (Test-Path -LiteralPath $WfSrc) {
  New-Item -ItemType Directory -Force -Path $WfDst | Out-Null
  Get-ChildItem -LiteralPath $WfSrc -Filter "wf_*.json" -File | Copy-Item -Destination $WfDst -Force
  if (-not $Quiet) {
    $n = (Get-ChildItem -LiteralPath $WfDst -File).Count
    Write-Host "  + walkforward/ ($n event curves)"
  }
}

$RDir = Join-Path $Src "reports"
$RDst = Join-Path $Root "src\frontend\public\reports"
if (Test-Path -LiteralPath $RDir) {
  New-Item -ItemType Directory -Force -Path $RDst | Out-Null
  Get-ChildItem -LiteralPath $RDir -File | Copy-Item -Destination $RDst -Force
  if (-not $Quiet) {
    $n = (Get-ChildItem -LiteralPath $RDst -File).Count
    Write-Host "  + reports/ ($n files)"
  }
}
Write-Host "Done."
