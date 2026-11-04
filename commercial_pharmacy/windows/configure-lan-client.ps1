# Configure a Windows pharmacy client shortcut for a LAN server.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ServerHost,
  [int]$Port = 18763,
  [Parameter(Mandatory=$true)][string]$ClientExecutable,
  [Parameter(Mandatory=$true)][string]$ShortcutPath
)
$ErrorActionPreference = 'Stop'
if ($ServerHost -notmatch '^[a-zA-Z0-9.-]+$' -or $ServerHost.Contains('..')) { throw 'Invalid LAN server hostname' }
if ($Port -lt 1024 -or $Port -gt 65535 -or $Port -eq 10080) { throw 'Invalid or reserved port' }
if (!(Test-Path -LiteralPath $ClientExecutable -PathType Leaf)) { throw 'Client executable missing' }
$exe = (Resolve-Path -LiteralPath $ClientExecutable).Path
$parent = Split-Path -Parent $ShortcutPath
if (!(Test-Path -LiteralPath $parent -PathType Container)) { throw 'Shortcut destination directory missing' }
$wsh = New-Object -ComObject WScript.Shell
$link = $wsh.CreateShortcut($ShortcutPath)
$link.TargetPath = $exe
$link.Arguments = "--host $ServerHost --port $Port"
$link.WorkingDirectory = Split-Path -Parent $exe
$link.Description = 'NOVA Commercial Pharmacy LAN Client'
$link.Save()
Write-Host 'COMMERCIAL_PHARMACY_LAN_CLIENT_SHORTCUT_CONFIGURED'
