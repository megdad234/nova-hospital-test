# Standalone commercial pharmacy Windows service registration.
# Requires a built and verified commercial server executable.
# Does not create, stop, delete or reconfigure the NOVA Hospital service.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExecutablePath,
  [int]$Port = 18763,
  [switch]$OpenLanFirewall,
  [switch]$ServiceAwareExecutableConfirmed
)
$ErrorActionPreference = 'Stop'
if (-not $ServiceAwareExecutableConfirmed) {
  throw 'A Windows Service Control Manager-aware executable must be built and tested before registration; generic Python/EXE cannot be registered with sc.exe'
}
$serviceName = 'NOVACommercialPharmacyServer'
$displayName = 'NOVA Commercial Pharmacy Server'
if (-not (Test-Path -LiteralPath $ExecutablePath -PathType Leaf)) {
  throw 'Commercial pharmacy server executable is missing'
}
if ($Port -lt 1024 -or $Port -gt 65535 -or $Port -eq 10080) {
  throw 'Invalid or hospital-reserved commercial pharmacy port'
}
if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
  throw 'Commercial pharmacy service already exists; refusing overwrite'
}
$fullExe = (Resolve-Path -LiteralPath $ExecutablePath).Path
if ($fullExe -match '[\x00-\x1f]') { throw 'Invalid executable path' }
$binaryPath = ('"{0}" --service --port {1}' -f $fullExe, $Port)
& sc.exe create $serviceName binPath= $binaryPath start= auto DisplayName= $displayName
if ($LASTEXITCODE -ne 0) { throw 'Windows service registration failed' }
& sc.exe description $serviceName 'Independent NOVA Commercial Pharmacy server; no NOVA Hospital service dependency.'
if ($LASTEXITCODE -ne 0) { throw 'Windows service description failed' }
if ($OpenLanFirewall) {
  $ruleName = 'NOVA Commercial Pharmacy LAN'
  if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -Profile Private | Out-Null
  }
}
Start-Service -Name $serviceName -ErrorAction Stop
$service = Get-Service -Name $serviceName -ErrorAction Stop
$service.WaitForStatus("Running", [TimeSpan]::FromSeconds(30))
Write-Host "COMMERCIAL_PHARMACY_SERVICE_RUNNING $serviceName"
