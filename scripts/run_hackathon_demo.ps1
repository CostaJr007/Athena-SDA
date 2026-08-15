# Athena-SDA — one-shot hackathon demo (Windows)
# Starts the sidecar (Groq + Tavily graph Q&A) and the mission board.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $Root) { $Root = (Resolve-Path "$PSScriptRoot\..").Path }
Set-Location $Root

if (Test-Path "$Root\.env") {
  Get-Content "$Root\.env" | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $k, $v = $_.Split('=', 2)
    if ($k -and -not [string]::IsNullOrWhiteSpace($v)) {
      Set-Item -Path "Env:$($k.Trim())" -Value $v.Trim()
    }
  }
}

$pyExe = "python"
$pyArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
  $pyExe = "py"
  $pyArgs = @("-3.12")
}

Write-Host "Athena-SDA hackathon demo"
Write-Host "  Groq   : $(if ($env:GROQ_API_KEY) { 'configured' } else { 'missing — local fallback' })"
Write-Host "  Tavily : $(if ($env:TAVILY_API_KEY) { 'configured' } else { 'missing — no web cites' })"
Write-Host ""
Write-Host "Sidecar  http://127.0.0.1:8787/api/health"
Write-Host "Board    http://127.0.0.1:3000"
Write-Host ""

$sidecarCmd = @($pyArgs + @("$Root\scripts\serve_granite_explain.py")) -join " "
$sidecar = Start-Process -FilePath $pyExe -ArgumentList ($pyArgs + @("$Root\scripts\serve_granite_explain.py")) -WorkingDirectory $Root -PassThru -WindowStyle Minimized

Start-Sleep -Seconds 2
Set-Location "$Root\src\frontend"
try {
  npm run dev
} finally {
  if (-not $sidecar.HasExited) {
    Stop-Process -Id $sidecar.Id -Force -ErrorAction SilentlyContinue
  }
}
