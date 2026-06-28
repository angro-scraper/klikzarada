param(
  [int]$Minutes = 15,
  [string]$TaskName = "KlikZarada Automation Engine"
)

$ErrorActionPreference = "Stop"

$Backend = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
$Script = Join-Path $Backend "scripts\run_automation_once_v11824.py"

if (!(Test-Path $Python)) {
  Write-Host "Python venv nije pronađen: $Python"
  Write-Host "Prvo pokreni:"
  Write-Host "python -m venv .venv"
  Write-Host ".\.venv\Scripts\Activate.ps1"
  Write-Host "pip install -r requirements.txt"
  exit 1
}

$Action = New-ScheduledTaskAction -Execute $Python -Argument "`"$Script`"" -WorkingDirectory $Backend
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $Minutes)
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null

Write-Host "OK: Windows Task Scheduler zadatak instaliran."
Write-Host "Task: $TaskName"
Write-Host "Interval: $Minutes minuta"
Write-Host "Backend: $Backend"
