# Fail-closed runtime payload check; does not register a service or change NOVA Hospital.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$InstallRoot)
$ErrorActionPreference = 'Stop'
if (!(Test-Path -LiteralPath $InstallRoot -PathType Container)) { throw 'Commercial install root missing' }
$required = @(
  'NOVACommercialPharmacy.exe',
  'NOVACommercialPharmacyServer.exe',
  'runtime/python.exe',
  'pharmacy/app.py',
  'pharmacy/server_host.py',
  'pharmacy/static/index.html',
  'pharmacy/static/app.js'
)
foreach ($name in $required) {
  if (!(Test-Path -LiteralPath (Join-Path $InstallRoot $name) -PathType Leaf)) {
    throw "Commercial runtime bundle incomplete: $name"
  }
}
$python = Join-Path $InstallRoot 'runtime/python.exe'
$source = Join-Path $InstallRoot 'pharmacy/server_host.py'
& $python -c 'import ast,sys; ast.parse(open(sys.argv[1],encoding="utf-8").read())' $source
if ($LASTEXITCODE -ne 0) { throw 'Commercial server syntax verification failed' }
Write-Host 'COMMERCIAL_RUNTIME_BUNDLE_STRUCTURE_PASSED_NOT_FULLY_TESTED'
