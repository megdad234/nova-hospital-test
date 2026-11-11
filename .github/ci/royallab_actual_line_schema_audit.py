"""Audit real lab line schema, grouping and printing after Batch04."""
import pathlib,zipfile
root=pathlib.Path(__file__).resolve().parents[2]
with zipfile.ZipFile(root/"NOVA_Hospital_GitHub_Ready_Source.zip") as z:
 lines=z.read("hospital/lab.py").decode("utf-8-sig").splitlines()
 for a,b in ((19,96),(200,270),(375,390)):
  print("ORIGINAL_LAB",a,b)
  for i in range(a-1,min(b,len(lines))):print(f"{i+1}: {lines[i][:500]}")
for name in (".github/ci/nova_batch04_lab_reception.py",):
 print("PATCH",name)
 for i,line in enumerate((root/name).read_text(encoding="utf-8").splitlines(),1):
  if any(term in line for term in ("section_name","lab-print","printReport","lab.report","report(")):
   print(f"{i}: {line[:650]}")
