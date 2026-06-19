$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

& $python -X utf8 (Join-Path $PSScriptRoot "check_live_release.py")
exit $LASTEXITCODE
