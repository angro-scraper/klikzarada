
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (Test-Path ".\.venv\Scripts\Activate.ps1") { . .\.venv\Scripts\Activate.ps1 }
python ".\v68_verify_finance_reports.py"
