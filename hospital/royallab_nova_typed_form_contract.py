"""Read-only typed Royal Lab field contract for a specific existing NOVA order item.

No HTML injection, no patient-result writes, no clinical auto-approval.
"""
from hospital.royallab_nova_order_line_resolver import resolve_order_lines
ALLOWED={"number","text","select","select_or_text","select_or_number"}
def source_bool(value):
    """Decode source database boolean values without Python truthiness coercion."""
    if value is True or value == 1 or value in ("True","true","1"):return True
    if value is False or value == 0 or value in ("False","false","0"):return False
    return None
def reviewed_order_form(conn,item_id,source_form):
    if not isinstance(source_form,dict) or not isinstance(source_form.get("fields"),list):
        raise ValueError("Reviewed source form required")
    if source_form.get("review_flags"):
        raise ValueError("Source test has unresolved review flags")
    fields=source_form["fields"]
    resolved=resolve_order_lines(conn,item_id,fields)
    if not resolved["ready"] or len(resolved["source_to_line"])!=len(fields):
        raise ValueError("Incomplete order-line mapping")
    output=[]
    for f in fields:
        if not isinstance(f.get('label'),str) or not f['label'].strip():
            raise ValueError('Missing original analyte name; clinical review required')
        kind=f.get("kind")
        if kind not in ALLOWED:raise ValueError("Unsupported Royal Lab input kind")
        options=f.get("options") or []
        if kind.startswith("select") and not options:raise ValueError("Dropdown has no source options")
        if kind.startswith("select"):
            labels=[o.get("label") for o in options if isinstance(o,dict) and source_bool(o.get("active")) is not False]
            if not labels or any(not isinstance(v,str) or not v.strip() for v in labels) or len(labels)!=len(set(labels)):
                raise ValueError("Invalid or ambiguous source dropdown labels")
        else:labels=[]
        output.append({"source_format_id":str(f["source_format_id"]),
                       "line_id":resolved["source_to_line"][str(f["source_format_id"])],
                       "label":str(f.get("label") or ""),"kind":kind,
                       "unit":str(f.get("unit") or ""),"options":labels,
                       "required":source_bool(f.get("required")) is True})
    return {"item_id":item_id,"mode":"review_only","clinical_approval":False,
            "can_save_patient_results":False,"fields":output}
