$ErrorActionPreference = "Stop"
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
  $Python = "python"
}
& $Python -X utf8 (Join-Path $PSScriptRoot "check_external_backend_ready.py") @args
