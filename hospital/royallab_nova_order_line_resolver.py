"""Resolve reviewed Royal Lab format IDs to NOVA order-result line IDs.

Read-only; strict code and test ownership, never matches by translated labels.
"""
from royallab_nova_parameter_plan import source_code
def resolve_order_lines(conn,item_id,fields):
    if type(item_id) is not int or item_id<=0:raise ValueError("Order item required")
    item=conn.execute("SELECT test_id FROM hospital_order_items WHERE id=?",(item_id,)).fetchone()
    if not item:raise ValueError("Order item not found")
    if not isinstance(fields,list) or not fields:raise ValueError("Source fields required")
    rows=conn.execute("""SELECT l.id,l.code,l.parameter_id,p.test_id,p.active
      FROM hospital_lab_lines l LEFT JOIN hospital_lab_parameters p ON p.id=l.parameter_id
      WHERE l.item_id=?""",(item_id,)).fetchall()
    by_code={}
    for row in rows:
        if row[1] in by_code:raise ValueError("Duplicate result code in order")
        by_code[row[1]]=row
    mapping={};unresolved=[];seen=set()
    for field in fields:
        if not isinstance(field,dict):raise ValueError("Invalid source field")
        sid=field.get("source_format_id")
        if sid is None:unresolved.append({"source_format_id":None,"reason":"missing_format_id"});continue
        code=source_code(sid)
        if code in seen:raise ValueError("Duplicate source format")
        seen.add(code)
        if field.get("kind") in ("unknown","related"):
            unresolved.append({"source_format_id":str(sid),"reason":"unsupported_format"});continue
        row=by_code.get(code)
        if not row or row[2] is None or row[3]!=item[0] or row[4]!=1:
            unresolved.append({"source_format_id":str(sid),"reason":"missing_or_inactive_order_line"});continue
        mapping[str(sid)]=int(row[0])
    return {"item_id":item_id,"source_to_line":mapping,"unresolved":unresolved,
            "ready":not unresolved,"writes":False,"clinical_approval":False}
