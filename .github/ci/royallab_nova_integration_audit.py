"""Audit existing NOVA lab persistence and print entry points before any integration.
Read-only AST/text inspection of original source archive, no modifications.
"""
import ast,json,pathlib,re,zipfile
root=pathlib.Path(__file__).resolve().parents[2]
archive=root/"NOVA_Hospital_GitHub_Ready_Source.zip"
paths=["hospital/lab.py","hospital/lab_catalog.py","hospital/server.py","hospital/core.py"]
report={"archive":archive.name,"files":{},"integration_status":"audit_only"}
with zipfile.ZipFile(archive) as z:
 for path in paths:
  if path not in z.namelist():continue
  src=z.read(path).decode("utf-8-sig")
  tree=ast.parse(src)
  functions=[]
  for node in ast.walk(tree):
   if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and re.search("lab|result|save|print|report|revision|sample|parameter",node.name,re.I):
    functions.append({"name":node.name,"line":node.lineno,"args":[a.arg for a in node.args.args]})
  relevant=[]
  lines=src.splitlines()
  for i,line in enumerate(lines):
   if re.search(r"hospital_lab_(?:tests|parameters|lines|revisions|samples|settings)|lab.*(?:save|print|report)|(?:save|print|report).*lab",line,re.I):
    relevant.append({"line":i+1,"text":line.strip()[:220]})
  report["files"][path]={"functions":functions,"references":relevant[:250]}
out=root/"docs/royallab_nova_integration_points.json"
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"audit":"complete","paths":list(report["files"]),"function_counts":{p:len(x["functions"]) for p,x in report["files"].items()},"reference_counts":{p:len(x["references"]) for p,x in report["files"].items()}},indent=2))
