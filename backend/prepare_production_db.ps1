param(
  [string]$DatabaseUrl,
  [switch]$Create,
  [switch]$SeedPilot,
  [switch]$RequirePostgres,
  [switch]$RequireProductionDb
)

$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

$argsList = @("-X", "utf8", (Join-Path $PSScriptRoot "prepare_production_db.py"))
if ($DatabaseUrl) { $argsList += @("--database-url", $DatabaseUrl) }
if ($Create) { $argsList += "--create" }
if ($SeedPilot) { $argsList += "--seed-pilot" }
if ($RequirePostgres) { $argsList += "--require-postgres" }
if ($RequireProductionDb) { $argsList += "--require-production-db" }

& $python @argsList
exit $LASTEXITCODE
