"""Read-only audit of original NOVA order-detail endpoint for Royal Lab integration."""
import pathlib,zipfile
p=pathlib.Path(__file__).resolve().parents[2]/'NOVA_Hospital_GitHub_Ready_Source.zip'
with zipfile.ZipFile(p) as z:
 for name in ('hospital/gateway.py','hospital/core.py','hospital/lab.py'):
  lines=z.read(name).decode('utf-8-sig').splitlines()
  print('FILE',name)
  if name=='hospital/gateway.py':
   print('GATEWAY_IMPORTS',[(i+1,line[:200]) for i,line in enumerate(lines[:50]) if 'import ' in line])
  hits=[i for i,line in enumerate(lines) if ('/api/hospital/order/' in line or 'def order_detail(' in line or 'order_lab_detail(' in line or "lab/values" in line)]
  for i in hits[:12]:
   for j in range(max(0,i-2),min(len(lines),i+9)):
    print(f'{j+1}: {lines[j][:600]}')
