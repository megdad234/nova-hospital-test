[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$SourceRoot)
$ErrorActionPreference = 'Stop'
Push-Location $SourceRoot
try {
  python -m PyInstaller --noconfirm --clean --onedir --name NOVACommercialPharmacy --distpath dist\client commercial_pharmacy\desktop_client.py
  if ($LASTEXITCODE -ne 0) { throw 'Client build failed' }
  python -m PyInstaller --noconfirm --clean --onedir --name NOVACommercialPharmacyServer --distpath dist\server commercial_pharmacy\windows_service.py
  if ($LASTEXITCODE -ne 0) { throw 'Server build failed' }
} finally { Pop-Location }
Write-Host 'COMMERCIAL_BUILD_CANDIDATE_ONLY'
