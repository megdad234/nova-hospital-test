"""Read-only Royal Lab catalog API backed by isolated NOVA staging tables.
Never enables clinical use or writes to operational hospital_lab_* tables.
"""
import json
from hospital.royallab_field_adapter import build_fields

def _source(conn,batch_id):
    rows=conn.execute("SELECT payload_json FROM royal_lab_source_tests WHERE batch_id=? ORDER BY source_test_id",(batch_id,)).fetchall()
    analytes=conn.execute("SELECT payload_json FROM royal_lab_source_analytes WHERE batch_id=? ORDER BY source_analyte_id",(batch_id,)).fetchall()
    if len(rows)!=367 or len(analytes)!=1245:
        raise ValueError("Incomplete staged Royal Lab catalog")
    return {"tests":[json.loads(r[0]) for r in rows],"analytes":[json.loads(r[0]) for r in analytes]}

def catalog(conn,batch_id):
    """Return fully sourced field specs for review UI; never clinically approved."""
    mapped=build_fields(_source(conn,batch_id))
    return {"source":"RoyalLabDB.bak","batch_id":batch_id,
        "clinical_approval":False,"production_ready":False,
        "tests":[{"source_test_id":t["source_id"],"name":t["name"],
            "review_flags":t["review_flags"],"enabled_for_clinical_use":False,
            "fields":[{k:f.get(k) for k in ("source_analyte_id","source_format_id","label","kind","types","unit","options","numeric_ranges","text_ranges","required","active")}
                for f in t["fields"]]} for t in mapped["tests"]],
        "detached_analytes":[{"source_test_id":d["source_test_id"],"source_analyte_id":str(d["analyte"]["analyte_id"])}
            for d in mapped["detached_analytes"]],
        "field_kinds":mapped["field_kinds"]}

def test_form(conn,batch_id,source_test_id):
    """Provide a result-entry *preview* definition, never a live result editor."""
    match=[t for t in catalog(conn,batch_id)["tests"] if t["source_test_id"]==str(source_test_id)]
    if not match:raise KeyError("Unknown Royal Lab source test")
    return {"mode":"review_only","can_save_patient_results":False,**match[0]}
