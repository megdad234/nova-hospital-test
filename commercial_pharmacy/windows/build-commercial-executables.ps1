[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$SourceRoot)
$ErrorActionPreference = 'Stop'
Push-Location $SourceRoot
try {
  python -m PyInstaller --noconfirm --clean --onefile --name NOVACommercialPharmacy --distpath dist\commercial commercial_pharmacy\windows_client_entry.py
  if ($LASTEXITCODE -ne 0) { throw 'Client build failed' }
  python -m PyInstaller --noconfirm --clean --onefile --name NOVACommercialPharmacyServer --hidden-import servicemanager --hidden-import win32timezone --distpath dist\commercial commercial_pharmacy\windows_server_entry.py
  if ($LASTEXITCODE -ne 0) { throw 'Server build failed' }
} finally { Pop-Location }
Write-Host 'COMMERCIAL_BUILD_CANDIDATE_ONLY'
