param(
  [string]$TaskName = "KlikZarada Automation Engine"
)

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
  Write-Host "Task ne postoji: $TaskName"
  exit 0
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "OK: Task obrisan: $TaskName"
