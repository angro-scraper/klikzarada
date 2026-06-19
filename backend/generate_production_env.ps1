param(
  [string]$Domain,
  [string]$DatabaseUrl,
  [string]$Output,
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

$argsList = @("-X", "utf8", (Join-Path $PSScriptRoot "generate_production_env.py"))
if ($Domain) { $argsList += @("--domain", $Domain) }
if ($DatabaseUrl) { $argsList += @("--database-url", $DatabaseUrl) }
if ($Output) { $argsList += @("--output", $Output) }
if ($Force) { $argsList += "--force" }

& $python @argsList
exit $LASTEXITCODE
