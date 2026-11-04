# Verify a complete standalone pharmacy runtime payload without starting any service.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$InstallRoot)
$ErrorActionPreference = 'Stop'
$required = @(
  'runtime/python.exe',
  'pharmacy/app.py',
  'pharmacy/server_host.py',
  'pharmacy/static/app.js',
  'pharmacy/static/index.html',
  'commercial_pharmacy/launch.py',
  'commercial_pharmacy/runtime_isolation.py'
)
foreach ($relative in $required) {
  $path = Join-Path $InstallRoot $relative
  if (!(Test-Path -LiteralPath $path -PathType Leaf)) {
    throw "Commercial runtime payload missing: $relative"
  }
}
if (Test-Path -LiteralPath (Join-Path $InstallRoot 'hospital_reference')) { throw 'Hospital reference source must not ship in standalone pharmacy runtime' }
$python = Join-Path $InstallRoot 'runtime/python.exe'
$source = Join-Path $InstallRoot 'pharmacy/server_host.py'
$env:PYTHONNOUSERSITE = '1'
Push-Location $InstallRoot
try {
  & $python -m commercial_pharmacy.launch --source-root $InstallRoot --preflight-only
  if ($LASTEXITCODE -ne 0) { throw 'Commercial source preflight failed' }
} finally { Pop-Location }
Write-Host 'COMMERCIAL_RUNTIME_PAYLOAD_PREFLIGHT_PASSED_NOT_ACCEPTANCE'
