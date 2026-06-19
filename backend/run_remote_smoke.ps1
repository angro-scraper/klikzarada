param(
  [string]$BaseUrl,
  [string]$AdminPin,
  [switch]$Strict
)

$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

$argsList = @("-X", "utf8", (Join-Path $PSScriptRoot "run_remote_smoke.py"))
if ($BaseUrl) { $argsList += @("--base-url", $BaseUrl) }
if ($AdminPin) { $argsList += @("--admin-pin", $AdminPin) }
if ($Strict) { $argsList += "--strict" }

& $python @argsList
exit $LASTEXITCODE
