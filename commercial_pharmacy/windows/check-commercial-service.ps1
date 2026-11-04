[CmdletBinding()]
param([int]$Port = 18763)
$ErrorActionPreference = 'Stop'
if ($Port -eq 10080 -or $Port -lt 1024 -or $Port -gt 65535) { throw 'Reserved port' }
$service = Get-Service -Name 'NOVACommercialPharmacyServer' -ErrorAction SilentlyContinue
[pscustomobject]@{
  Product = 'NOVACommercialPharmacy'
  ServiceInstalled = ($null -ne $service)
  ServiceStatus = if ($service) { $service.Status.ToString() } else { 'NotInstalled' }
  Port = $Port
  Listening = (@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue).Count -gt 0)
} | ConvertTo-Json
