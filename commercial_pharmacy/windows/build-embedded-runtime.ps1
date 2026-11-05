[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Destination)
$ErrorActionPreference = 'Stop'
$version = '3.12.10'
$zip = Join-Path $env:RUNNER_TEMP 'nova-commercial-python-embed.zip'
$uri = "https://www.python.org/ftp/python/$version/python-$version-embed-amd64.zip"
if (Test-Path $Destination) { throw 'Dedicated runtime destination already exists' }
New-Item -ItemType Directory -Path $Destination | Out-Null
Invoke-WebRequest -Uri $uri -OutFile $zip
Expand-Archive -LiteralPath $zip -DestinationPath $Destination
$pth = Join-Path $Destination 'python312._pth'
if (!(Test-Path $pth)) { throw 'Embedded Python path configuration missing' }
$lines = Get-Content $pth
$lines = @($lines | Where-Object { $_ -ne '#import site' }) + @('..','../pharmacy','Lib/site-packages','import site')
Set-Content -LiteralPath $pth -Value $lines -Encoding ascii
$packages = Join-Path $Destination 'Lib/site-packages'
New-Item -ItemType Directory -Path $packages -Force | Out-Null
python -m pip install --disable-pip-version-check --target $packages flask requests openpyxl
if ($LASTEXITCODE -ne 0) { throw 'Dedicated runtime dependencies failed to install' }
& (Join-Path $Destination 'python.exe') -c 'import flask,requests,openpyxl,sqlite3; print("COMMERCIAL_EMBEDDED_RUNTIME_READY")'
if ($LASTEXITCODE -ne 0) { throw 'Embedded runtime dependency import failed' }
Write-Host 'DEDICATED_EMBEDDED_RUNTIME_CANDIDATE_READY'
