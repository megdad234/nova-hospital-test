[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ExecutablePath,[int]$Port=18763,[switch]$OpenLanFirewall,[switch]$ServiceAwareExecutableConfirmed)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent (Resolve-Path -LiteralPath $ExecutablePath).Path
$nssm=Join-Path $root 'nssm.exe'
$python=Join-Path $root 'runtime/python.exe'
$entry=Join-Path $root 'pharmacy/server_host.py'
$name='NOVACommercialPharmacyServer'
if (!(Test-Path $nssm) -or !(Test-Path $python) -or !(Test-Path $entry)) { throw 'Missing independent commercial NSSM/runtime/server payload' }
if ($Port -lt 1024 -or $Port -gt 65535 -or $Port -eq 8765 -or $Port -eq 10080) { throw 'Invalid commercial port' }
$svc=Get-Service $name -ErrorAction SilentlyContinue
if ($svc) {
  $config=Get-CimInstance Win32_Service -Filter "Name='$name'"
  if ($config.PathName -notmatch 'nssm.exe') {
    if ($svc.Status -ne 'Stopped') { Stop-Service $name -ErrorAction Stop }
    & sc.exe delete $name | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not migrate previous commercial service' }
    Start-Sleep -Seconds 3
    if (Get-Service $name -ErrorAction SilentlyContinue) { throw 'Old service pending deletion; reboot before retrying migration' }
    $svc=$null
  }
}
if (!$svc) {
  & $nssm install $name $python $entry
  if ($LASTEXITCODE -ne 0) { throw 'NSSM registration failed' }
}
& $nssm set $name AppDirectory $root
if ($LASTEXITCODE -ne 0) { throw 'NSSM working directory failed' }
& $nssm set $name AppEnvironmentExtra "NOVA_COMMERCIAL_PORT=$Port"
if ($LASTEXITCODE -ne 0) { throw 'NSSM port configuration failed' }
& $nssm set $name Start SERVICE_AUTO_START
& $nssm set $name AppExit Default Restart
& $nssm set $name DisplayName 'NOVA Commercial Pharmacy Server'
if ($OpenLanFirewall -and !(Get-NetFirewallRule -DisplayName 'NOVA Commercial Pharmacy LAN' -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -DisplayName 'NOVA Commercial Pharmacy LAN' -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -Profile Private | Out-Null
}
$svc=Get-Service $name -ErrorAction Stop
if ($svc.Status -ne 'Running') { Start-Service $name -ErrorAction Stop }
(Get-Service $name).WaitForStatus('Running',[TimeSpan]::FromSeconds(30))
$ready=$false
for($i=0;$i -lt 40;$i++){
  try { if((Invoke-WebRequest "http://127.0.0.1:$Port/" -TimeoutSec 2).StatusCode -eq 200){$ready=$true;break} } catch { Start-Sleep -Seconds 1 }
}
if (!$ready) { throw 'NSSM service running but commercial HTTP not ready' }
Write-Host 'COMMERCIAL_NSSM_HTTP_READY'
