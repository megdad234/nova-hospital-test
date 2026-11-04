param([string]$SourceRoot, [string]$PythonExecutable)
$ErrorActionPreference = 'Stop'
if (!(Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) { throw 'Python runtime missing' }
if (!(Test-Path -LiteralPath (Join-Path $SourceRoot 'pharmacy/server_host.py') -PathType Leaf)) { throw 'Server source missing' }
& $PythonExecutable -m commercial_pharmacy.launch --source-root $SourceRoot --preflight-only
if ($LASTEXITCODE -ne 0) { throw 'Standalone source preflight failed' }
Write-Host 'SOURCE_PREFLIGHT_ONLY'
