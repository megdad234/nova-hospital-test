"""Check whether staged Royal Lab field specs can be safely mapped to NOVA.
This is a preflight only. It never modifies patient results or operational tables.
"""
from collections import Counter
from royallab_catalog_preview import catalog

SUPPORTED={"number","text","select","select_or_text","select_or_number"}

def integration_preflight(conn,batch_id):
    data=catalog(conn,batch_id)
    flags=Counter()
    total=0
    blocked=0
    for test in data["tests"]:
        for field in test["fields"]:
            total+=1
            kind=field.get("kind")
            # A synthetic text fallback is structurally valid but not a clinically
            # verified source result format; retain the preflight review block.
            if str(field.get("source_format_id", "")).startswith("ANALYTE-"):
                blocked+=1
                flags["unsupported:unknown"]+=1
            if kind not in SUPPORTED:
                blocked+=1
                flags["unsupported:"+str(kind)]+=1
            if kind in ("select","select_or_text","select_or_number") and not field.get("options"):
                blocked+=1
                flags["missing_dropdown_options"]+=1
            if kind in ("number","select_or_number") and not field.get("unit"):
                flags["numeric_unit_missing_review"]+=1
    return {"batch_id":batch_id,"source_test_count":len(data["tests"]),
        "source_field_count":total,"blocked_field_issues":blocked,
        "review_flags":dict(flags),
        "may_enable_live_entry":False,
        "next_step":"Map existing NOVA lab persistence and report renderer, then clinical review"}
