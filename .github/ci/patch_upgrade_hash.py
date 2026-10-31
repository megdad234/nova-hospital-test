#!/usr/bin/env python3
"""Provide SHA256 verification in bundled Windows PowerShell scripts using .NET.
Applies only to the extracted NOVA Windows installer scripts on the CI runner.
Never changes clinical databases or the original pharmacy application.
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
HASH_HELPER = r'''function Get-NovaSHA256([string]$Path) {
  $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
  $hasher = [System.Security.Cryptography.SHA256]::Create()
  try {
    return ([System.BitConverter]::ToString($hasher.ComputeHash($stream))).Replace('-', '')
  } finally {
    $stream.Dispose()
    $hasher.Dispose()
  }
}
'''

for filename, expected in [('preflight-upgrade.ps1', 6), ('recover-failed-upgrade.ps1', 1)]:
    p = root / 'windows' / filename
    original = p.read_text(encoding='utf-8')
    if 'function Get-NovaSHA256' in original:
        raise SystemExit(f'Already patched: {p}')
    patched, count = re.subn(
        r'\(Get-FileHash(?:\s+-LiteralPath)?\s+([^\s)]+)\s+-Algorithm\s+SHA256\)\.Hash',
        r'(Get-NovaSHA256 \1)',
        original,
    )
    if count != expected:
        raise SystemExit(f'Unsafe expected {expected} old calls in {filename}; saw {count}')
    sentinel = "$ErrorActionPreference = 'Stop'\n"
    if patched.count(sentinel) != 1:
        raise SystemExit(f'Unexpected PowerShell setup: {filename}')
    patched = patched.replace(sentinel, sentinel + HASH_HELPER, 1)
    if 'Get-FileHash' in patched:
        raise SystemExit(f'Old cmdlet remains in {filename}')
    compile("assert True", filename, "exec")
    p.write_text(patched, encoding='utf-8')
    print(f'NOVA_PS_HASH_FALLBACK_APPLIED: {filename} ({count} calls)')
