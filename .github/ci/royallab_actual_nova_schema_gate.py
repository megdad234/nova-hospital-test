"""Audit the REAL extracted NOVA lab schema against direct Royal Lab import.

Uses AST to extract the original lab.SCHEMA literal and executes it in an
in-memory SQLite database only. No application import or patient DB access.
"""
import ast
import json
import pathlib
import sqlite3
from hospital.royallab_existing_catalog_replacement import replacement_plan, replace_catalog

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
        replacement=replace_catalog(db,library,approved=True)
        if replacement["active_royal_lab_tests"]!=367:
            raise RuntimeError("Real NOVA schema import incomplete")
        metadata_count=db.execute("SELECT COUNT(*) FROM royal_lab_nova_parameter_metadata").fetchone()[0]
        if metadata_count<1000:
            raise RuntimeError("Real NOVA schema parameter metadata incomplete")
        replace_catalog(db,library,approved=True)
        if db.execute("SELECT COUNT(*) FROM hospital_lab_tests WHERE code LIKE 'ROYAL-%'").fetchone()[0]!=367:
            raise RuntimeError("Real NOVA schema repeat import duplicated tests")
        return {"source_test_count":len(tests),
                "source_field_count":plan["source_field_count"],
                "actual_nova_test_columns":plan["tests_schema"],
                "actual_nova_parameter_columns":plan["parameters_schema"],
                "clinical_review_flags":sum(bool(t["review_flags"]) for t in tests),
                "real_nova_schema_imported_in_memory":True,
                "imported_parameter_metadata_count":metadata_count,
                "real_patient_db_accessed":False}

if __name__=="__main__":
    import sys
    print(json.dumps(audit(pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path.cwd()),
                     ensure_ascii=False,indent=2))
