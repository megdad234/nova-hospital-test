"""Audit the REAL extracted NOVA lab schema against direct Royal Lab import.

Uses AST to extract the original lab.SCHEMA literal and executes it in an
in-memory SQLite database only. No application import or patient DB access.
"""
import ast
import json
import pathlib
import sqlite3
from hospital.royallab_existing_catalog_replacement import replacement_plan

def schema_from_source(source):
    module=ast.parse(source)
    matches=[]
    for node in module.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id=="SCHEMA":
                    matches.append(ast.literal_eval(node.value))
    if len(matches)!=1 or not isinstance(matches[0],str):
        raise RuntimeError("Original NOVA lab SCHEMA literal not uniquely available")
    return matches[0]

def audit(root):
    root=pathlib.Path(root)
    schema=schema_from_source((root/"hospital/lab.py").read_text(encoding="utf-8"))
    library=json.loads((root/"hospital/royallab_source/nova_lab_library.json").read_text(encoding="utf-8-sig"))
    with sqlite3.connect(":memory:") as db:
        db.executescript(schema)
        # Schema-only preflight: source catalogue must fit the real tables.
        plan=replacement_plan(db,library)
        tests=plan["tests"]
        return {"source_test_count":len(tests),
                "source_field_count":plan["source_field_count"],
                "actual_nova_test_columns":plan["tests_schema"],
                "actual_nova_parameter_columns":plan["parameters_schema"],
                "clinical_review_flags":sum(bool(t["review_flags"]) for t in tests),
                "real_patient_db_accessed":False}

if __name__=="__main__":
    import sys
    print(json.dumps(audit(pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path.cwd()),
                     ensure_ascii=False,indent=2))
