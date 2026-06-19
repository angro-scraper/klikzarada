param(
  [switch]$Strict
)

$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

& $python -X utf8 (Join-Path $PSScriptRoot "run_production_audit.py")
$code = $LASTEXITCODE
if ($Strict -and $code -ne 0) {
  exit $code
}
if (-not $Strict -and $code -eq 2) {
  Write-Host "Audit je upozorenje za javni live, ali zatvoreni pilot može dalje." -ForegroundColor Yellow
  exit 0
}
exit $code
