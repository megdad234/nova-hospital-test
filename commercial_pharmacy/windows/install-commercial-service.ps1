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
# Resolve the dedicated runtime from the installed commercial package itself.
# No machine-wide environment variables are required for a standard installation.
$installedRoot = Split-Path -Parent (Resolve-Path -LiteralPath $ExecutablePath).Path
$runtimeRoot = [Environment]::GetEnvironmentVariable('NOVA_COMMERCIAL_SOURCE_ROOT', 'Machine')
if (-not $runtimeRoot) { $runtimeRoot = $installedRoot }
$runtimePython = [Environment]::GetEnvironmentVariable('NOVA_COMMERCIAL_PYTHON', 'Machine')
if (-not $runtimePython) { $runtimePython = Join-Path $runtimeRoot 'runtime/python.exe' }
if (!(Test-Path -LiteralPath (Join-Path $runtimeRoot 'pharmacy/server_host.py') -PathType Leaf)) { throw 'Commercial server source missing' }
if (!(Test-Path -LiteralPath $runtimePython -PathType Leaf)) { throw 'Dedicated commercial Python runtime missing' }
$serviceName = 'NOVACommercialPharmacyServer'
$displayName = 'NOVA Commercial Pharmacy Server'
if (-not (Test-Path -LiteralPath $ExecutablePath -PathType Leaf)) {
  throw 'Commercial pharmacy server executable is missing'
}
if ($Port -lt 1024 -or $Port -gt 65535 -or $Port -eq 10080) {
  throw 'Invalid or hospital-reserved commercial pharmacy port'
}
if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
  Stop-Service -Name $serviceName -ErrorAction SilentlyContinue
  & sc.exe delete $serviceName | Out-Null
  Start-Sleep -Seconds 2
  if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) { throw 'Previous commercial service is still registered; retry after reboot' }
}
$nssm = Join-Path $installedRoot 'nssm.exe'
if (!(Test-Path -LiteralPath $nssm -PathType Leaf)) { throw 'Bundled NSSM service manager missing; refusing broken installation' }
$fullExe = (Resolve-Path -LiteralPath $runtimePython).Path
$entry = Join-Path $runtimeRoot 'pharmacy/server_host.py'
& $nssm install $serviceName $fullExe $entry
if ($LASTEXITCODE -ne 0) { throw 'NSSM commercial service registration failed' }
& $nssm set $serviceName AppDirectory $runtimeRoot
& $nssm set $serviceName AppEnvironmentExtra "NOVA_COMMERCIAL_PORT=$Port"
& $nssm set $serviceName Start SERVICE_AUTO_START
& $nssm set $serviceName DisplayName $displayName
& $nssm set $serviceName AppExit Default Restart
& $nssm set $serviceName AppStdout (Join-Path $env:ProgramData 'NOVACommercialPharmacy\logs\service-out.log')
& $nssm set $serviceName AppStderr (Join-Path $env:ProgramData 'NOVACommercialPharmacy\logs\service-error.log')
New-Item -ItemType Directory -Force -Path (Join-Path $env:ProgramData 'NOVACommercialPharmacy\logs') | Out-Null
$firewallRuleCreated = $false
try {
  if ($OpenLanFirewall) {
    $ruleName = 'NOVA Commercial Pharmacy LAN'
    if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
      New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -Profile Private | Out-Null
      $firewallRuleCreated = $true
    }
  }
  Start-Service -Name $serviceName -ErrorAction Stop
  (Get-Service -Name $serviceName).WaitForStatus('Running',[TimeSpan]::FromSeconds(30))
  $ready = $false
  for ($i=0; $i -lt 30; $i++) {
    try {
      $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -TimeoutSec 3
      if ($response.StatusCode -eq 200) { $ready = $true; break }
    } catch { Start-Sleep -Seconds 1 }
  }
  if (!$ready) { throw 'Commercial service did not become HTTP-ready' }
} catch {
  if ($firewallRuleCreated) { Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue }
  & $nssm stop $serviceName confirm | Out-Null
  & $nssm remove $serviceName confirm | Out-Null
  throw "Commercial pharmacy service failed readiness; rolled back: $_"
}
Write-Host "COMMERCIAL_PHARMACY_NSSM_HTTP_READY $serviceName"
