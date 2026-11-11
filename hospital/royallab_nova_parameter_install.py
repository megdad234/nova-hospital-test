"""Explicit, reviewed Royal Lab parameter insertion into an existing NOVA test.

Never creates tests, changes prices or references, or edits existing parameter rows.
Must be invoked only after operator approval on a disposable or backed-up database.
"""
from royallab_nova_parameter_plan import plan_existing_parameters
def install_reviewed_parameters(conn,test_id,fields,approved=False):
    if approved is not True:raise PermissionError("Explicit reviewed import approval required")
    plan=plan_existing_parameters(conn,test_id,fields)
    if plan["blocked"]:raise ValueError("Unresolved source fields; insertion blocked")
    if not plan["missing"]:return {"inserted":0,"existing":len(plan["mapped"]),"clinical_approval":False}
    # Preserve current operational catalog; only allow insertion into an existing test.
    if not conn.execute("SELECT 1 FROM hospital_lab_tests WHERE id=?",(test_id,)).fetchone():
        raise ValueError("Existing NOVA test required")
    # Every new parameter is inactive until laboratory validation.
    conn.execute("SAVEPOINT royallab_parameter_import")
    try:
     for idx,row in enumerate(plan["missing"]):
        conn.execute("""INSERT INTO hospital_lab_parameters
          (test_id,code,name,unit,reference_all,reference_male,reference_female,sort_order,active)
          VALUES (?,?,?,?,'','','',?,0)""",
          (test_id,row["code"],row["name"],row["unit"],100000+len(plan["mapped"])+idx))
     conn.execute("RELEASE SAVEPOINT royallab_parameter_import")
    except Exception:
     conn.execute("ROLLBACK TO SAVEPOINT royallab_parameter_import")
     conn.execute("RELEASE SAVEPOINT royallab_parameter_import")
     raise
    return {"inserted":len(plan["missing"]),"existing":len(plan["mapped"]),
            "active":False,"clinical_approval":False}
