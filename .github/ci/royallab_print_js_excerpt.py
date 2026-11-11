"""Show bounded original printReport JavaScript and report data fields."""
import pathlib,zipfile
p=pathlib.Path(__file__).resolve().parents[2]/"NOVA_Hospital_GitHub_Ready_Source.zip"
with zipfile.ZipFile(p) as z:
 for name in ("hospital/static/app.js","hospital/gateway.py","hospital/lab.py"):
  lines=z.read(name).decode("utf-8-sig").splitlines()
  print("FILE",name)
  if name.endswith("app.js"):
   for i in range(43,min(59,len(lines))):print(f"{i+1}: {lines[i][:13000]}")
  elif name.endswith("gateway.py"):
   for i in range(169,181):print(f"{i+1}: {lines[i][:350]}")
  else:
   for i in range(245,253):print(f"{i+1}: {lines[i][:350]}")
