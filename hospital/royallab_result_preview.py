"""Strict review-only result validator for Royal Lab preview fields.
Does not write patient results or alter NOVA lab operations.
"""
from decimal import Decimal,InvalidOperation

def validate_preview(form,values):
    if form.get("mode")!="review_only" or form.get("can_save_patient_results") is not False:
        raise ValueError("Royal Lab preview safety contract required")
    if not isinstance(values,dict):raise ValueError("Values must be a dictionary")
    fields=form.get("fields",[])
    keys=[str(f["source_format_id"]) if f.get("source_format_id") is not None else "analyte:"+str(f["source_analyte_id"]) for f in fields]
    if len(set(keys))!=len(keys):raise ValueError("Ambiguous field identifiers; cannot validate")
    unknown=set(values)-set(keys)
    if unknown:raise ValueError("Unknown field identifiers: "+", ".join(sorted(unknown)))
    result={}
    for key,f in zip(keys,fields):
        value=values.get(key)
        if value is None or value=="":
            result[key]={"status":"empty","value":None}
            continue
        kind=f.get("kind","unknown")
        if kind in ("unknown","related"):
            result[key]={"status":"requires_review","value":value}
            continue
        if not isinstance(value,(str,int,float)):
            result[key]={"status":"invalid","reason":"unsupported_value_type"}
            continue
        text=str(value).strip()
        options={str(o.get("label","")).strip() for o in f.get("options",[]) if isinstance(o,dict) and o.get("label") is not None and o.get("active") not in (False,0,"False","false","0")}
        if kind in ("select","select_or_text","select_or_number") and text in options:
            result[key]={"status":"valid_option","value":text}
        elif kind=="select":
            result[key]={"status":"invalid","reason":"option_not_in_source"}
        elif kind in ("number","select_or_number"):
            try:
                numeric=Decimal(text)
                if not numeric.is_finite():raise InvalidOperation
                result[key]={"status":"valid_number","value":str(numeric),"unit":f.get("unit") or ""}
            except (InvalidOperation,ValueError):
                result[key]={"status":"invalid","reason":"not_a_finite_number"}
        elif kind in ("text","select_or_text"):
            result[key]={"status":"valid_text","value":text}
        else:
            result[key]={"status":"requires_review","value":text}
    return {"mode":"review_only","can_save_patient_results":False,"results":result,
            "all_valid":all(x["status"].startswith("valid") or x["status"]=="empty" for x in result.values())}
