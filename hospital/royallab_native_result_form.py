"""Royal Lab-native result form contract, independent of NOVA's old test catalogue.

No name matching, no old NOVA order dependencies, no clinical auto-approval.
Source IDs are retained for every field and every option.
"""
from hospital.royallab_field_adapter import build_fields

def native_catalog(library):
    mapped=build_fields(library)
    return {"source":"RoyalLabDB.bak","test_count":len(mapped["tests"]),
            "tests":[{"source_test_id":t["source_id"],"name":t["name"],
                      "review_flags":list(t["review_flags"]),
                      "fields":[{"source_analyte_id":f["source_analyte_id"],
                                 "source_format_id":f["source_format_id"],
                                 "label":f["label"],"kind":f["kind"],
                                 "unit":f.get("unit") or "",
                                 "required":f.get("required"),
                                 "active":f.get("active"),
                                 "options":[{"id":o["id"],"label":o["label"],
                                             "active":o.get("active"),
                                             "is_normal":o.get("is_normal"),
                                             "order":o.get("order")}
                                            for o in f.get("options",[])],
                                 "numeric_ranges":f.get("numeric_ranges",[]),
                                 "text_ranges":f.get("text_ranges",[]),
                                 "types":f.get("types",[])}
                                for f in t["fields"]]}
                     for t in mapped["tests"]],
            "detached_analytes":mapped["detached_analytes"],
            "field_kinds":mapped["field_kinds"],"uses_old_nova_test_matching":False}

def native_test_form(catalog,source_test_id):
    if not isinstance(catalog,dict) or not isinstance(catalog.get("tests"),list):
        raise ValueError("Royal Lab catalog required")
    matches=[t for t in catalog["tests"] if t["source_test_id"]==str(source_test_id)]
    if len(matches)!=1:raise ValueError("Unknown or ambiguous Royal Lab test ID")
    return matches[0]

def validate_result_values(test_form,values):
    """Check input types and closed choices; never invent medical normality."""
    if not isinstance(values,dict):raise ValueError("Result values must be keyed by source format ID")
    fields=test_form.get("fields")
    if not isinstance(fields,list):raise ValueError("Invalid test form")
    known={f["source_format_id"]:f for f in fields if f["source_format_id"] is not None}
    if len(known)!=len([f for f in fields if f["source_format_id"] is not None]):
        raise ValueError("Duplicate source format IDs")
    if len({str(key) for key in values})!=len(values):
        raise ValueError("Duplicate normalized result format IDs")
    if len({str(key) for key in known})!=len(known):
        raise ValueError("Duplicate normalized source format IDs")
    values={str(key):value for key,value in values.items()}
    known={str(key):field for key,field in known.items()}
    if set(values)-set(known):raise ValueError("Unknown Royal Lab result format")
    if any(not isinstance(f,dict) for f in fields):raise ValueError("Invalid source field definition")
    out={}
    for sid,value in values.items():
        f=known[sid];kind=f["kind"]
        if kind in ("unknown","related"):raise ValueError("Unsupported Royal Lab result format")
        if f.get("active") in (False,0,"False","false","0"):raise ValueError("Inactive source field cannot receive results")
        if value is None or value=="":out[sid]=None;continue
        if isinstance(value,bool):raise ValueError("Boolean is not a valid result")
        if kind=="select":
            ids={str(o["id"]) for o in f["options"] if o.get("active") not in (False,0,"False","false","0")}
            if str(value) not in ids:raise ValueError("Result is not a listed source option")
            out[sid]=str(value)
        elif kind=="number":
            import decimal
            try:n=decimal.Decimal(str(value))
            except decimal.InvalidOperation:raise ValueError("Invalid numeric result")
            if not n.is_finite():raise ValueError("Non-finite numeric result")
            out[sid]=str(n)
        elif kind=="select_or_number":
            import decimal
            labels={str(o["id"]) for o in f["options"] if o.get("active") not in (False,0,"False","false","0")}
            if str(value) not in labels:
                try:n=decimal.Decimal(str(value))
                except decimal.InvalidOperation:raise ValueError("Invalid numeric or source option result")
                if not n.is_finite():raise ValueError("Non-finite numeric result")
            out[sid]=str(value)
        elif kind in ("text","select_or_text"):
            if not isinstance(value,(str,int,float)):raise ValueError("Invalid result value")
            if isinstance(value,float):
                import math
                if not math.isfinite(value):raise ValueError("Non-finite result value")
            if kind=="select_or_text":
                option_ids={str(o["id"]) for o in f.get("options",[]) if o.get("active") not in (False,0,"False","false","0")}
                if str(value) in option_ids:
                    out[sid]=str(value)
                    continue
            out[sid]=str(value)
        else:raise ValueError("Unsupported result kind")
    return out
