"""Inspect lab print CSS anchors and prior patch interference; read only."""
import pathlib,zipfile
root=pathlib.Path(__file__).resolve().parents[2]
with zipfile.ZipFile(root/"NOVA_Hospital_GitHub_Ready_Source.zip") as z:
 names=[n for n in z.namelist() if n.startswith("hospital/static/") and n.endswith(".css")]
 for name in names:
  data=z.read(name).decode("utf-8-sig")
  lines=data.splitlines()
  hits=[i for i,line in enumerate(lines) if any(term in line for term in ("lab-print","printing-lab","@page","print-patient","print-head","print-test"))]
  if not hits:continue
  print("CSS",name,"total",len(lines),"hits",len(hits))
  for i in hits[:60]:
   for j in range(max(0,i-1),min(len(lines),i+2)):print(str(j+1)+": "+lines[j][:1000])
for path in sorted((root/".github"/"ci").glob("nova_*.py")):
 content=path.read_text(encoding="utf-8")
 if any(t in content for t in ("lab-print","printing-lab","print-patient")):
  print("PATCH_TOUCH",path.name)
  for i,line in enumerate(content.splitlines(),1):
   if any(t in line for t in ("lab-print","printing-lab","print-patient")):print(str(i)+": "+line[:600])
