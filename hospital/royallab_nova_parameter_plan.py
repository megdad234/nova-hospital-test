"""Plan Royal Lab source-format to existing NOVA parameter mapping without writes.

Exact source IDs are stored in the NOVA parameter code, never inferred from labels.
Does not add tests, change prices, create order lines or approve clinical use.
"""
import re

def _inactive(value):
    return value is False or value == 0 or value in ('False','false','0')
def source_code(source_format_id):
    value=str(source_format_id or "").strip()
    if not re.fullmatch(r"[0-9]{1,18}",value):raise ValueError("Invalid Royal Lab format ID")
    return "ROYAL_FMT_"+value

def plan_existing_parameters(conn,test_id,fields):
    if type(test_id) is not int or test_id<=0:raise ValueError("NOVA test ID required")
    if not isinstance(fields,list) or not fields:raise ValueError("Reviewed source fields required")
    rows=conn.execute("SELECT id,code,name,unit FROM hospital_lab_parameters WHERE test_id=?",(test_id,)).fetchall()
    by_code={row[1]:{"parameter_id":row[0],"code":row[1],"name":row[2],"unit":row[3]} for row in rows}
    seen=set();mapped=[];missing=[];blocked=[]
    for field in fields:
        if not isinstance(field,dict):raise ValueError("Invalid source field")
        if _inactive(field.get("active")):
            blocked.append({"source_format_id":str(field.get("source_format_id")),"reason":"inactive_source_analyte"});continue
        sid=field.get("source_format_id")
        if sid is None:
            blocked.append({"source_format_id":None,"reason":"missing_source_format_id"});continue
        code=source_code(sid)
        if code in seen:raise ValueError("Duplicate source format ID")
        seen.add(code)
        if field.get("kind") in ("unknown","related"):
            blocked.append({"source_format_id":str(sid),"reason":"unsupported_format"});continue
        if not str(field.get("label") or "").strip():
            blocked.append({"source_format_id":str(sid),"reason":"missing_label"});continue
        target=by_code.get(code)
        if target:
            if target["name"]!=field["label"] or target["unit"]!=str(field.get("unit") or ""):
                blocked.append({"source_format_id":str(sid),"reason":"existing_parameter_definition_differs"});continue
            mapped.append({"source_format_id":str(sid),**target})
        else:
            missing.append({"source_format_id":str(sid),"code":code,"name":field["label"],"unit":str(field.get("unit") or "")})
    return {"test_id":test_id,"mapped":mapped,"missing":missing,"blocked":blocked,
            "ready":not missing and not blocked,"writes":False,"clinical_approval":False}
