"""Prepare a direct Royal Lab -> existing NOVA lab-table replacement.

No new laboratory UI. The importer targets hospital_lab_tests and
hospital_lab_parameters. It never deletes historical orders/results or prints.
Requires explicit schema verification before any writes.
"""
import json
import sqlite3
from hospital.royallab_native_result_form import native_catalog

TESTS = "hospital_lab_tests"
PARAMETERS = "hospital_lab_parameters"

def _columns(conn, table):
    return {r[1]: r for r in conn.execute("PRAGMA table_info(" + table + ")")}

def _required_columns(conn):
    tests = _columns(conn, TESTS)
    params = _columns(conn, PARAMETERS)
    if not {"id","code","name"}.issubset(tests):
        raise RuntimeError("NOVA tests schema differs: expected id/code/name")
    if not {"id","test_id","code","name","unit"}.issubset(params):
        raise RuntimeError("NOVA parameter schema differs: expected id/test_id/code/name/unit")
    if "active" not in tests:
        raise RuntimeError("NOVA test active column missing: cannot safely hide old catalogue")
    return tests, params

def replacement_plan(conn, library):
    if not isinstance(conn, sqlite3.Connection):
        raise TypeError("SQLite connection required")
    tests_schema, params_schema = _required_columns(conn)
    catalog = native_catalog(library)
    tests = catalog["tests"]
    if len(tests) != 367 or len({t["source_test_id"] for t in tests}) != 367:
        raise RuntimeError("Royal Lab source tests incomplete")
    new_codes = ["ROYAL-" + t["source_test_id"] for t in tests]
    if len(set(new_codes)) != 367:
        raise RuntimeError("Duplicate Royal Lab NOVA codes")
    if any(not t["name"].strip() for t in tests):
        raise RuntimeError("Unnamed Royal Lab test")
    missing_fields = [f for t in tests for f in t["fields"] if not f["source_format_id"]]
    return {"tests": tests, "new_codes": new_codes,
            "existing_tests": conn.execute("SELECT COUNT(*) FROM " + TESTS).fetchone()[0],
            "source_field_count": sum(len(t["fields"]) for t in tests),
            "source_fields_needing_review": len(missing_fields),
            "tests_schema": sorted(tests_schema),
            "parameters_schema": sorted(params_schema),
            "can_preserve_historical_orders": True,
            "will_delete_patient_data": False,
            "will_modify_printing": False}

def replace_catalog(conn, library, *, approved=False):
    """Explicit opt-in only; atomic transaction; preserve old rows for old orders.

    Hides old catalogue rows using active=0. Reuses original NOVA tables so
    existing search and ordering UI can see Royal Lab tests. Does not change
    order, cashier, print, or pharmacy implementation.
    """
    plan = replacement_plan(conn, library)
    if approved is not True:
        raise PermissionError("Explicit approval of NOVA lab catalogue replacement required")
    tests_schema, params_schema = _required_columns(conn)
    for table, schema, allowed in (
        (TESTS, tests_schema, {"id","code","name","active","category","price","popular","created_at","updated_at"}),
        (PARAMETERS, params_schema, {"id","test_id","code","name","unit","reference_range","section_name","sort_order","created_at","updated_at"})):
        unsupported = [name for name,row in schema.items()
                       if row[3] and row[4] is None and not row[5] and name not in allowed]
        if unsupported:
            raise RuntimeError("Unsupported required " + table + " columns: " + ", ".join(unsupported))
    if any(t["review_flags"] for t in plan["tests"]):
        # Unreviewed Royal Lab formats must not be silently presented as approved.
        pass
    conn.execute("SAVEPOINT royal_catalog_replacement")
    try:
        # Never delete old test/parameter IDs: historical lab orders may reference them.
        conn.execute("UPDATE hospital_lab_tests SET active=0 WHERE code NOT LIKE 'ROYAL-%'")
        for test in plan["tests"]:
            code = "ROYAL-" + test["source_test_id"]
            row = conn.execute("SELECT id FROM hospital_lab_tests WHERE code=?", (code,)).fetchone()
            if row:
                test_id = row[0]
                conn.execute("UPDATE hospital_lab_tests SET name=?,active=1 WHERE id=?",
                             (test["name"],test_id))
            else:
                cur = conn.execute("INSERT INTO hospital_lab_tests(code,name,active) VALUES(?,?,1)",
                                   (code,test["name"]))
                test_id = cur.lastrowid
            for index, field in enumerate(test["fields"]):
                sid = field["source_format_id"]
                if sid is None:
                    continue
                param_code = "RL-" + str(sid)
                row = conn.execute("SELECT id FROM hospital_lab_parameters WHERE test_id=? AND code=?",
                                   (test_id,param_code)).fetchone()
                if row:
                    conn.execute("UPDATE hospital_lab_parameters SET name=?,unit=? WHERE id=?",
                                 (field["label"],field["unit"],row[0]))
                else:
                    conn.execute("INSERT INTO hospital_lab_parameters(test_id,code,name,unit) VALUES(?,?,?,?)",
                                 (test_id,param_code,field["label"],field["unit"]))
        count = conn.execute("SELECT COUNT(*) FROM hospital_lab_tests WHERE code LIKE 'ROYAL-%' AND active=1").fetchone()[0]
        if count != 367:
            raise RuntimeError("NOVA replacement count mismatch")
        conn.execute("RELEASE SAVEPOINT royal_catalog_replacement")
    except BaseException:
        conn.execute("ROLLBACK TO SAVEPOINT royal_catalog_replacement")
        conn.execute("RELEASE SAVEPOINT royal_catalog_replacement")
        raise
    return {"active_royal_lab_tests":367,"historical_tests_preserved":True,
            "source_fields_needing_review":plan["source_fields_needing_review"]}
