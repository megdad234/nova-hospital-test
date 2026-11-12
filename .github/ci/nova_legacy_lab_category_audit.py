"""Read-only probe of ORIGINAL pre-patch NOVA lab category labels in extracted ZIP.

No database access or output of private patient data. Used to retain the English
category names in the existing NOVA picker rather than invent new translations.
"""
import ast
import json
import pathlib
import re

root = pathlib.Path(__file__).resolve().parents[2]
path = root / "hospital" / "lab_catalog.py"
if not path.is_file():
    raise SystemExit("NOVA original lab_catalog.py not extracted")
source=path.read_text(encoding="utf-8-sig")
tree=ast.parse(source,filename=str(path))
categories=set()
dict_samples=[]
for node in ast.walk(tree):
    if not isinstance(node,ast.Dict):
        continue
    members={}
    for k,v in zip(node.keys,node.values):
        if isinstance(k,ast.Constant) and isinstance(k.value,str):
            key=k.value.lower()
            if isinstance(v,ast.Constant) and isinstance(v.value,str):
                members[key]=v.value
    if "category" in members:
        categories.add(members["category"])
        if len(dict_samples)<12:
            dict_samples.append({x:y for x,y in members.items() if x in ("category","name","code")})
# Original NOVA uses positional tuples in TESTS: code, label, category, ...
for stmt in tree.body:
    if not isinstance(stmt,(ast.Assign,ast.AnnAssign)):
        continue
    targets=stmt.targets if isinstance(stmt,ast.Assign) else [stmt.target]
    if not any(isinstance(t,ast.Name) and t.id=="TESTS" for t in targets):
        continue
    if isinstance(stmt.value,(ast.List,ast.Tuple)):
        for entry in stmt.value.elts:
            if isinstance(entry,(ast.Tuple,ast.List)) and len(entry.elts)>=3:
                cat=entry.elts[2]
                if isinstance(cat,ast.Constant) and isinstance(cat.value,str):
                    categories.add(cat.value)
                    if len(dict_samples)<20:
                        display=entry.elts[1]
                        label=display.value if isinstance(display,ast.Constant) else None
                        dict_samples.append({"category":cat.value,"label":label})
for match in re.finditer(r"""['"]category['"]\s*:\s*['"]([^'"\r\n]{1,100})['"]""",source,re.I):
    categories.add(match.group(1))
print("NOVA_ORIGINAL_CATEGORIES="+json.dumps(sorted(categories),ensure_ascii=False))
print("NOVA_ORIGINAL_CATEGORY_SAMPLES="+json.dumps(dict_samples,ensure_ascii=False))
print("NOVA_LAB_SOURCE_HEAD="+json.dumps(source[:8000].splitlines()[:115],ensure_ascii=False))
if not categories:
    raise SystemExit("Cannot identify any original NOVA category labels; do not overwrite them")
