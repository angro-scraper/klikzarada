$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

& $python -X utf8 (Join-Path $PSScriptRoot "build_static_landing_package.py")
exit $LASTEXITCODE
