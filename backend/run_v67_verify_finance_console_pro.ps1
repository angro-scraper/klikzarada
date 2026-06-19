
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (Test-Path ".\.venv\Scripts\Activate.ps1") { . .\.venv\Scripts\Activate.ps1 }
python ".\v67_verify_finance_console_pro.py"
