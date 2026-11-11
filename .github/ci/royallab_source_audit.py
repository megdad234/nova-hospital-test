"""Read-only inspection of original NOVA laboratory source archive."""
import zipfile, pathlib, ast, json, re
root=pathlib.Path(__file__).resolve().parents[2]
archive=root/"NOVA_Hospital_GitHub_Ready_Source.zip"
assert archive.is_file(), "Missing original NOVA source archive"
report={"archive":archive.name,"files":{},"lab_related_files":[],"potential_schema_tables":[]}
with zipfile.ZipFile(archive) as z:
 for entry in z.infolist():
  name=entry.filename
  if re.search(r"(^|/)(lab|lab_catalog|test_lab_complete)(\.py|/)",name,re.I):
   report["lab_related_files"].append({"path":name,"bytes":entry.file_size})
  if name in ("hospital/lab.py","hospital/lab_catalog.py","hospital/server.py","hospital/core.py"):
   raw=z.read(entry).decode("utf-8-sig")
   item={"bytes":len(raw),"classes":[],"functions":[],"api_routes":[],"tables":[]}
   try:
    tree=ast.parse(raw)
    item["functions"]=[n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    item["classes"]=[n.name for n in ast.walk(tree) if isinstance(n,ast.ClassDef)]
   except SyntaxError as exc:item["syntax_error"]=str(exc)
   item["tables"]=sorted(set(re.findall(r"hospital_lab_[a-z_]+",raw)))
   item["api_routes"]=sorted(set(re.findall(r"['\"][^'\"]*(?:lab|result|report)[^'\"]*['\"]",raw,re.I)))[:100]
   report["files"][name]=item
out=root/"docs/royallab_nova_source_audit.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
