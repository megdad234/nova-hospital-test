"""Print original NOVA lab save prerequisites for isolated database test design."""
import pathlib,zipfile
root=pathlib.Path(__file__).resolve().parents[2]
with zipfile.ZipFile(root/"NOVA_Hospital_GitHub_Ready_Source.zip") as z:
 src=z.read("hospital/lab.py").decode("utf-8-sig").splitlines()
for a,b in [(1,105),(200,275),(273,325)]:
 print("\n=== original lab.py lines",a,"-",b,"===")
 for i in range(a-1,min(b,len(src))):
  print(f"{i+1}: {src[i][:220]}")
