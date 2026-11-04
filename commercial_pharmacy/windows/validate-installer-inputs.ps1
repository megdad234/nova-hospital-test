# Check commercial Windows packaging inputs without changing installed software.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$SourceRoot)
$ErrorActionPreference = 'Stop'
$binaryDir = Join-Path $SourceRoot 'dist\commercial'
foreach ($name in @('NOVACommercialPharmacy.exe', 'NOVACommercialPharmacyServer.exe')) {
  $file = Join-Path $binaryDir $name
  if (!(Test-Path -LiteralPath $file -PathType Leaf)) { throw "Missing commercial executable: $name" }
  $stream = [System.IO.File]::OpenRead($file)
  try {
    if ($stream.ReadByte() -ne 77 -or $stream.ReadByte() -ne 90) { throw "Invalid PE executable: $name" }
  } finally {
    $stream.Dispose()
  }
}
Write-Host 'COMMERCIAL_EXECUTABLE_INPUTS_PRESENT_RUNTIME_NOT_VERIFIED'
