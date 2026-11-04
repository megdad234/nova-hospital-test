# Assemble a candidate only from an audited extracted source and an explicit Python runtime.
# This does not install services or modify NOVA Hospital.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$SourceStage,
  [Parameter(Mandatory=$true)][string]$PythonRuntimeDirectory,
  [Parameter(Mandatory=$true)][string]$Destination,
  [Parameter(Mandatory=$true)][string]$LaunchersDirectory
)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $SourceStage).Path
$runtime = (Resolve-Path -LiteralPath $PythonRuntimeDirectory).Path
if (!(Test-Path (Join-Path $source 'pharmacy/app.py') -PathType Leaf)) { throw 'Audited pharmacy app missing' }
if (!(Test-Path (Join-Path $source 'pharmacy/server_host.py') -PathType Leaf)) { throw 'Audited pharmacy server missing' }
if (!(Test-Path (Join-Path $source 'EXTRACTION_MANIFEST.json') -PathType Leaf)) { throw 'Extraction evidence missing' }
if (!(Test-Path (Join-Path $source 'COMMERCIAL_RUNTIME_PREFLIGHT.json') -PathType Leaf)) { throw 'Runtime preflight evidence missing' }
if (!(Test-Path (Join-Path $source 'HOSPITAL_COUPLING_BLOCKERS.json') -PathType Leaf)) { throw 'Hospital coupling evidence missing' }
if (!(Test-Path (Join-Path $source 'commercial_pharmacy/launch.py') -PathType Leaf)) { throw 'Commercial launcher source missing' }
if (!(Test-Path (Join-Path $source 'commercial_pharmacy/runtime_isolation.py') -PathType Leaf)) { throw 'Commercial isolation source missing' }
$blockers = Get-Content -LiteralPath (Join-Path $source 'HOSPITAL_COUPLING_BLOCKERS.json') -Raw | ConvertFrom-Json
if ($blockers.standalone_network_and_schema_clear -ne $true -or @($blockers.unresolved).Count -gt 0) {
  throw 'Hospital coupling blockers unresolved; refuse standalone packaging'
}
if (!(Test-Path (Join-Path $runtime 'python.exe') -PathType Leaf)) { throw 'Dedicated Python runtime missing' }
if (!(Test-Path -LiteralPath $LaunchersDirectory -PathType Container)) { throw 'Commercial launcher directory missing' }
foreach ($name in @('NOVACommercialPharmacy.exe','NOVACommercialPharmacyServer.exe')) {
  if (!(Test-Path -LiteralPath (Join-Path $LaunchersDirectory $name) -PathType Leaf)) { throw "Commercial launcher missing: $name" }
}
$destinationFull = [System.IO.Path]::GetFullPath($Destination)
foreach ($protected in @($source, $runtime, (Resolve-Path -LiteralPath $LaunchersDirectory).Path)) {
  $protectedFull = [System.IO.Path]::GetFullPath($protected).TrimEnd('\')
  if ($destinationFull.Equals($protectedFull, [System.StringComparison]::OrdinalIgnoreCase) -or $destinationFull.StartsWith($protectedFull + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Destination must not be inside source, runtime or launcher directories'
  }
}
if (Test-Path -LiteralPath $Destination) { throw 'Destination must not already exist' }
$manifest = Get-Content -LiteralPath (Join-Path $source 'EXTRACTION_MANIFEST.json') -Raw | ConvertFrom-Json
if ($manifest.status -ne 'SOURCE_SNAPSHOT_ONLY_NOT_INSTALLABLE') { throw 'Unexpected source extraction manifest status' }
if (Test-Path -LiteralPath (Join-Path $source 'pharmacy/commercial_pharmacy.sqlite3')) { throw 'Source snapshot contains a database file' }
New-Item -ItemType Directory -Path $Destination | Out-Null
Copy-Item -LiteralPath (Join-Path $source 'pharmacy') -Destination (Join-Path $Destination 'pharmacy') -Recurse
Copy-Item -LiteralPath (Join-Path $source 'commercial_pharmacy') -Destination (Join-Path $Destination 'commercial_pharmacy') -Recurse
Copy-Item -LiteralPath $runtime -Destination (Join-Path $Destination 'runtime') -Recurse
foreach ($name in @('NOVACommercialPharmacy.exe','NOVACommercialPharmacyServer.exe')) {
  $exe = Join-Path $LaunchersDirectory $name
  if (!(Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Launcher missing: $name" }
  Copy-Item -LiteralPath $exe -Destination (Join-Path $Destination $name)
}
& (Join-Path $PSScriptRoot 'check-runtime-payload.ps1') -InstallRoot $Destination
if ($LASTEXITCODE -ne 0) { throw 'Runtime payload preflight failed' }
Write-Host 'COMMERCIAL_PAYLOAD_ASSEMBLED_CANDIDATE_NOT_RELEASE_APPROVED'
