"""Review-gated activation of existing Royal Lab parameters.

Never touches result lines, patient orders, reference ranges or test prices.
"""
from royallab_nova_parameter_plan import plan_existing_parameters
def activate_reviewed_parameters(conn,test_id,fields,approved=False):
    if approved is not True:raise PermissionError("Laboratory review approval required")
    plan=plan_existing_parameters(conn,test_id,fields)
    if not plan["ready"]:raise ValueError("Missing or conflicting Royal Lab fields")
    if not plan["mapped"]:raise ValueError("No reviewed parameters")
    # NOVA ensure_order_lines can lazily snapshot old orders. Refuse activation
    # while any existing order item for this test lacks its own result snapshot.
    pending=conn.execute("""SELECT i.id FROM hospital_order_items i
      WHERE i.test_id=? AND NOT EXISTS
      (SELECT 1 FROM hospital_lab_lines l WHERE l.item_id=i.id) LIMIT 1""",(test_id,)).fetchone()
    if pending:raise ValueError("Existing unsnapshotted order items must be reviewed before activation")
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
