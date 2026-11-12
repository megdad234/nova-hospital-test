"""Show native Royal Lab dropdown metadata in NOVA's existing result lines.

Uses explicit NOVA parameter_id -> original Royal Lab source metadata mapping.
Does not create a new UI or modify save, cashier, printing, or patient data.
"""
import json

def overlay_existing_order_lines(conn, detail):
    if not isinstance(detail,dict) or not isinstance(detail.get("items"),list):
        return detail
    tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "royal_lab_nova_parameter_metadata" not in tables:
        return detail
    result={**detail,"items":[]}
    for item in detail["items"]:
        clone={**item,"lines":[dict(x) for x in item.get("lines",[])]}
        item_id=item.get("id")
        if type(item_id) is not int:
            result["items"].append(clone)
            continue
        row=conn.execute("""SELECT t.code FROM hospital_order_items i
            JOIN hospital_lab_tests t ON t.id=i.test_id WHERE i.id=?""",
            (item_id,)).fetchone()
        if not row or not str(row[0]).startswith("ROYAL-"):
            result["items"].append(clone)
            continue
        for line in clone["lines"]:
            param_id=line.get("parameter_id")
            if type(param_id) is not int:
                continue
            row=conn.execute("""SELECT m.kind,m.options_json,m.numeric_ranges_json,
                  m.text_ranges_json FROM royal_lab_nova_parameter_metadata m
                  JOIN hospital_lab_parameters p ON p.id=m.nova_parameter_id
                  JOIN hospital_order_items i ON i.test_id=p.test_id
                  WHERE i.id=? AND p.id=?""",(item_id,param_id)).fetchone()
            if not row:
                continue
            options=json.loads(row[1])
            line["royal_lab_field"]={
                "kind":row[0],
                "options":[str(x.get("label","")) for x in options
                           if x.get("active") not in (False,0,"False","false","0")
                           and str(x.get("label","")).strip()],
                "numeric_ranges":json.loads(row[2]),
                "text_ranges":json.loads(row[3])}
        result["items"].append(clone)
    return result
