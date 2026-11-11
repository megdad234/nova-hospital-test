"""Inspect original NOVA report payload and print entry points without touching pharmacy."""
import pathlib,zipfile,ast
root=pathlib.Path(__file__).resolve().parents[2]
with zipfile.ZipFile(root/"NOVA_Hospital_GitHub_Ready_Source.zip") as z:
 for name in ("hospital/lab.py","hospital/core.py"):
  src=z.read(name).decode("utf-8-sig")
  lines=src.splitlines()
  print("\nSOURCE:",name)
  if name.endswith("lab.py"):
   tree=ast.parse(src)
   for n in tree.body:
    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in ("report","order_lab_detail","settings"):
     print("\nFUNCTION",n.name)
     for i in range(n.lineno-1,min(n.end_lineno,len(lines))):
      print(f"{i+1}: {lines[i][:240]}")
  else:
   terms=("lab/report","lab_report","lab.report","تقرير جزئي","partial","print_lab")
   hits=[i for i,line in enumerate(lines) if any(t in line for t in terms)]
   for i in hits[:35]:
    a=max(0,i-2);b=min(len(lines),i+4)
    print("\nCONTEXT",i+1)
    for j in range(a,b):print(f"{j+1}: {lines[j][:220]}")
