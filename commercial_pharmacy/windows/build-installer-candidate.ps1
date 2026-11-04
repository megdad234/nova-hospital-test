# Build an explicitly UNVERIFIED candidate; never publish as a final installer.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$SourceRoot,
  [Parameter(Mandatory=$true)][string]$InnoCompiler
)
$ErrorActionPreference = 'Stop'
if (!(Test-Path -LiteralPath $InnoCompiler -PathType Leaf)) { throw 'Inno Setup compiler missing' }
& (Join-Path $PSScriptRoot 'validate-installer-inputs.ps1') -SourceRoot $SourceRoot

$spec = Join-Path $PSScriptRoot 'commercial-pharmacy-installer.iss'
Push-Location $PSScriptRoot
try {
  & $InnoCompiler $spec
  if ($LASTEXITCODE -ne 0) { throw 'Inno Setup candidate build failed' }
} finally {
  Pop-Location
}
Write-Host 'COMMERCIAL_INSTALLER_CANDIDATE_ONLY_RELEASE_GATE_REQUIRED'
