"""Extract focused original NOVA lab code excerpts for integration review.
Read-only; output is bounded and contains source code only, no patient data.
"""
import ast,pathlib,zipfile
root=pathlib.Path(__file__).resolve().parents[2]
with zipfile.ZipFile(root/"NOVA_Hospital_GitHub_Ready_Source.zip") as z:
 src=z.read("hospital/lab.py").decode("utf-8-sig")
lines=src.splitlines()
tree=ast.parse(src)
for node in tree.body:
 if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
  name=node.name
  if isinstance(node,ast.ClassDef):
   print("CLASS",name,"line",node.lineno)
   children=[x for x in node.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))]
  else:children=[node]
  for fn in children:
   if any(word in fn.name.lower() for word in ("save","result","print","report","lab","revision","sample","parameter")):
    print("\nFUNCTION",fn.name,"lines",fn.lineno,"-",fn.end_lineno)
    for i in range(fn.lineno-1,min(fn.end_lineno,fn.lineno+42)):
     print(f"{i+1}: {lines[i][:180]}")
