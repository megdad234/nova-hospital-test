"""Review-gated activation of existing Royal Lab parameters.

Never touches result lines, patient orders, reference ranges or test prices.
"""
from royallab_nova_parameter_plan import plan_existing_parameters
def activate_reviewed_parameters(conn,test_id,fields,approved=False):
    if approved is not True:raise PermissionError("Laboratory review approval required")
    plan=plan_existing_parameters(conn,test_id,fields)
    if not plan["ready"]:raise ValueError("Missing or conflicting Royal Lab fields")
    if not plan["mapped"]:raise ValueError("No reviewed parameters")
    # Do not silently add parameters to existing patient orders: existing snapshots
    # are immutable here; only future snapshot generation may see activated fields.
    conn.execute("SAVEPOINT royallab_activate")
    try:
        for entry in plan["mapped"]:
            conn.execute("UPDATE hospital_lab_parameters SET active=1 WHERE id=? AND test_id=? AND code=?",
                         (entry["parameter_id"],test_id,entry["code"]))
        conn.execute("RELEASE SAVEPOINT royallab_activate")
    except Exception:
        conn.execute("ROLLBACK TO SAVEPOINT royallab_activate")
        conn.execute("RELEASE SAVEPOINT royallab_activate")
        raise
    return {"activated":len(plan["mapped"]),"existing_order_lines_changed":0,
            "clinical_approval":False,"requires_future_order_snapshot":True}
