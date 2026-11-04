param([string]$SourceRoot, [string]$PythonExecutable)
$ErrorActionPreference = 'Stop'
if (!(Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) { throw 'Python runtime missing' }
if (!(Test-Path -LiteralPath $SourceRoot -PathType Container)) { throw 'Commercial source root missing' }
if (!(Test-Path -LiteralPath (Join-Path $SourceRoot 'pharmacy/server_host.py') -PathType Leaf)) { throw 'Server source missing' }
Push-Location $SourceRoot
try {
  & $PythonExecutable -m commercial_pharmacy.launch --source-root $SourceRoot --data-dir (Join-Path $env:TEMP "NOVACommercialPharmacyPreflight") --preflight-only
  if ($LASTEXITCODE -ne 0) { throw "Standalone source preflight failed" }
} finally { Pop-Location }
Write-Host 'SOURCE_PREFLIGHT_ONLY'
