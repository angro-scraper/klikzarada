param(
  [string]$OutputDir
)

$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

$argsList = @("-X", "utf8", (Join-Path $PSScriptRoot "build_adriahost_package.py"))
if ($OutputDir) { $argsList += @("--output-dir", $OutputDir) }

& $python @argsList
exit $LASTEXITCODE
