"""Audit Windows packaging inclusion of Royal Lab order overlay modules."""
from pathlib import Path
import zipfile
root=Path(__file__).resolve().parents[2]
with zipfile.ZipFile(root/'NOVA_Hospital_GitHub_Ready_Source.zip') as z:
 for name in ('windows/build-windows.ps1','windows/nova-hospital.spec','hospital/gateway.py'):
  if name not in z.namelist():continue
  lines=z.read(name).decode('utf-8-sig').splitlines()
  print('FILE',name)
  for i,line in enumerate(lines):
   if any(x in line.lower() for x in ('pyinstaller','hidden-import','collect-submodules','hospital.gateway','hospital/','hospital\\','add-data','--onefile','--onedir','import hospital')):
    print(f'{i+1}: {line[:260]}')
