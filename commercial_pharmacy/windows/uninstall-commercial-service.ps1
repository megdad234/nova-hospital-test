# Remove only the independent commercial pharmacy Windows service.
# Does not remove pharmacy data, backups, or NOVA Hospital.
[CmdletBinding()]
param([switch]$RemoveLanFirewallRule)
$ErrorActionPreference = 'Stop'
$serviceName = 'NOVACommercialPharmacyServer'
$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($service) {
  if ($service.Status -ne 'Stopped') {
    Stop-Service -Name $serviceName -ErrorAction Stop
    $service.WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
  }
  & sc.exe delete $serviceName
  if ($LASTEXITCODE -ne 0) { throw 'Failed to remove commercial pharmacy service' }
}
if ($RemoveLanFirewallRule) {
  $rule = Get-NetFirewallRule -DisplayName 'NOVA Commercial Pharmacy LAN' -ErrorAction SilentlyContinue
  if ($rule) { $rule | Remove-NetFirewallRule }
}
Write-Host 'COMMERCIAL_PHARMACY_SERVICE_REMOVED_HOSPITAL_UNTOUCHED'
