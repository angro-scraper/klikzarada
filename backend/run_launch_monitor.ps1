param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [switch]$StrictPublicLive,
  [switch]$NoWrite
)

$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

$argsList = @("-X", "utf8", (Join-Path $PSScriptRoot "run_launch_monitor.py"), "--base-url", $BaseUrl)
if ($StrictPublicLive) { $argsList += "--strict-public-live" }
if ($NoWrite) { $argsList += "--no-write" }

& $python @argsList
exit $LASTEXITCODE
