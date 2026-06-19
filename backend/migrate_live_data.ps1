param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("export", "validate", "import")]
  [string]$Command,
  [string]$Input,
  [string]$Output,
  [string]$DatabaseUrl,
  [switch]$ReplaceExisting,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

$argsList = @("-X", "utf8", (Join-Path $PSScriptRoot "migrate_live_data.py"), $Command)
if ($Input) { $argsList += @("--input", $Input) }
if ($Output) { $argsList += @("--output", $Output) }
if ($DatabaseUrl) { $argsList += @("--database-url", $DatabaseUrl) }
if ($ReplaceExisting) { $argsList += "--replace-existing" }
if ($DryRun) { $argsList += "--dry-run" }

& $python @argsList
exit $LASTEXITCODE
