# Configure automatic commercial-pharmacy backups only.
# Run as administrator after verifying the standalone Python environment.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$PythonExe,
  [Parameter(Mandatory=$true)][string]$SourceRoot,
  [string]$DataDir = "$env:ProgramData\NOVACommercialPharmacy",
  [int]$Hour = 2,
  [int]$Retain = 30
)
$ErrorActionPreference = 'Stop'
if ($Hour -lt 0 -or $Hour -gt 23) { throw 'Hour must be 0 through 23' }
if ($Retain -lt 1 -or $Retain -gt 365) { throw 'Retain must be 1 through 365' }
if (!(Test-Path -LiteralPath $PythonExe -PathType Leaf)) { throw 'Python executable missing' }
if (!(Test-Path -LiteralPath (Join-Path $SourceRoot 'commercial_pharmacy\cli.py') -PathType Leaf)) {
  throw 'Commercial pharmacy CLI source missing'
}
$taskName = 'NOVACommercialPharmacyDailyBackup'
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
  throw 'Backup task already exists; refusing to overwrite'
}
$exe = (Resolve-Path -LiteralPath $PythonExe).Path
$root = (Resolve-Path -LiteralPath $SourceRoot).Path
if ($exe.Contains('"') -or $root.Contains('"') -or $DataDir.Contains('"')) { throw 'Invalid path quotation' }
$arguments = '-m commercial_pharmacy.cli --data-dir "{0}" backup-auto --retain {1}' -f $DataDir, $Retain
$action = New-ScheduledTaskAction -Execute $exe -Argument $arguments -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours($Hour))
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description 'Independent NOVA Commercial Pharmacy SQLite backup; never touches NOVA Hospital.' | Out-Null
Write-Host "COMMERCIAL_BACKUP_TASK_CREATED $taskName"
