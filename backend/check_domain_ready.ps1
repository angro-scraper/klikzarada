param(
  [Parameter(Mandatory = $true)]
  [string]$Domain,
  [string]$ExpectedIp,
  [switch]$Strict
)

$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

$argsList = @("-X", "utf8", (Join-Path $PSScriptRoot "check_domain_ready.py"), $Domain)
if ($ExpectedIp) { $argsList += @("--expected-ip", $ExpectedIp) }
if ($Strict) { $argsList += "--strict" }

& $python @argsList
exit $LASTEXITCODE
