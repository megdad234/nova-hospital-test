# Remove only NOVA Commercial Pharmacy automatic backup schedule.
# Existing backups, database, NOVA Hospital tasks and services are untouched.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$taskName = 'NOVACommercialPharmacyDailyBackup'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}
Write-Host 'COMMERCIAL_BACKUP_TASK_REMOVED_DATA_PRESERVED'
