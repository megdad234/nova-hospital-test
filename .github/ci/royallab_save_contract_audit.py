"""Verify Royal Lab draft bridge matches the real original NOVA save_values API.
Read-only source contract audit; no operational database is opened.
"""
import ast,pathlib,zipfile
root=pathlib.Path(__file__).resolve().parents[2]
with zipfile.ZipFile(root/"NOVA_Hospital_GitHub_Ready_Source.zip") as z:
    source=z.read("hospital/lab.py").decode("utf-8-sig")
tree=ast.parse(source)
fn=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="save_values"),None)
assert fn is not None,"NOVA save_values missing"
assert [a.arg for a in fn.args.args]==["c","actor","data"],"NOVA save_values signature changed"
text=ast.get_source_segment(source,fn)
required=["item_id","values","expected_version","publish","source","reason","line_id","value",
          "BEGIN IMMEDIATE","hospital_lab_lines","hospital_lab_revisions","result_version",
          "paid","completed","ROLLBACK"]
missing=[s for s in required if s not in text]
assert not missing,"NOVA lab contract changed: "+repr(missing)
assert "source not in ('manual','csv')" in text,"Allowed source contract changed"
assert "publish=data.get('publish') is True" in text,"Publish guard changed"
assert "len(values)>120" in text,"Result limit changed"
print("NOVA source save_values signature and bridge contract: verified")
print("Existing payment, version, revision, transaction, source and publish guards: verified")
