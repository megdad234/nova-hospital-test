"""Audit the REAL extracted NOVA lab schema against direct Royal Lab import.

Uses AST to extract the original lab.SCHEMA literal and executes it in an
in-memory SQLite database only. No application import or patient DB access.
"""
import ast
import json
import pathlib
import sqlite3
import sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
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
    core_source=(root/"hospital/core.py").read_text(encoding="utf-8")
    core_module=ast.parse(core_source)
    core_schemas=[]
    for node in core_module.body:
        if isinstance(node,(ast.Assign,ast.AnnAssign)):
            try:
                value=ast.literal_eval(node.value)
            except (ValueError,TypeError,SyntaxError):
                continue
            if isinstance(value,str) and "CREATE TABLE IF NOT EXISTS hospital_lab_tests" in value:
                core_schemas.append(value)
    if len(core_schemas)!=1:
        raise RuntimeError("Cannot uniquely identify real NOVA core schema containing hospital_lab_tests: "+str(len(core_schemas)))
    core_schema=core_schemas[0]
    library=json.loads((root/"hospital/royallab_source/nova_lab_library.json").read_text(encoding="utf-8-sig"))
    with sqlite3.connect(":memory:") as db:
        db.executescript(core_schema)
        db.executescript(schema)
        for p in (root/'hospital').glob('*.py'):
            body=p.read_text(encoding='utf-8-sig')
            pos=body.find('CREATE TABLE IF NOT EXISTS hospital_lab_tests')
            if pos>=0: print('NOVA_TEST_DDL_SOURCE',p.name,repr(body[max(0,pos-100):pos+1100]),flush=True)
        for table in ('hospital_lab_tests','hospital_lab_parameters','hospital_lab_lines'):
            print('NOVA_REAL_SCHEMA',table,list(db.execute('PRAGMA table_info('+table+')')),flush=True)
        # Print actionable source-specific review cases before the strict gate.
        from hospital.royallab_native_result_form import native_catalog
        native=native_catalog(library)
        review=[]
        for test in native["tests"]:
            for field in test["fields"]:
                if field["source_format_id"] is None or field["kind"] in ("unknown","related"):
                    review.append({"test_id":test["source_test_id"],
                                   "test_name":test["name"],
                                   "analyte_id":field["source_analyte_id"],
                                   "label":field["label"],
                                   "format_id":field["source_format_id"],
                                   "kind":field["kind"],
                                   "types":field["types"]})
        print("ROYAL_REVIEW_COUNTS",json.dumps({
            "missing_format_id":sum(x["format_id"] is None for x in review),
            "unknown_kind":sum(x["kind"]=="unknown" for x in review),
            "related_kind":sum(x["kind"]=="related" for x in review),
            "affected_tests":len({x["test_id"] for x in review}),
            "total_review_rows":len(review)},ensure_ascii=False),flush=True)
        for entry in review:
            print("ROYAL_REVIEW_CASE",json.dumps(entry,ensure_ascii=False),flush=True)
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
