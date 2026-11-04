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
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONPATH = $InstallRoot
Push-Location $InstallRoot
try {
  & $python -m commercial_pharmacy.launch --source-root $InstallRoot --data-dir (Join-Path $env:TEMP 'NOVACommercialBundlePreflight') --preflight-only
  if ($LASTEXITCODE -ne 0) { throw 'Bundled Python cannot launch commercial source preflight' }
  & $python -c 'import importlib.util,sys; required=("flask",); missing=[name for name in required if importlib.util.find_spec(name) is None]; print("MISSING_RUNTIME_IMPORTS="+",".join(missing)); sys.exit(2 if missing else 0)'
  if ($LASTEXITCODE -ne 0) { throw 'Bundled Python lacks required Flask runtime' }
} finally {
  Pop-Location
}
Write-Host 'COMMERCIAL_RUNTIME_BUNDLE_STRUCTURE_PASSED_NOT_FULLY_TESTED'
