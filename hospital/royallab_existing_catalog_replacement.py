"""Prepare a direct Royal Lab -> existing NOVA lab-table replacement.

No new laboratory UI. The importer targets hospital_lab_tests and
hospital_lab_parameters. It never deletes historical orders/results or prints.
Requires explicit schema verification before any writes.
"""
import json
import sqlite3
from hospital.royallab_native_result_form import native_catalog
from hospital.royallab_nova_parameter_plan import source_code

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
    if "active" not in params:
        raise RuntimeError("NOVA parameter active column missing: result resolver requires active=1")
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
    unsupported_fields = [(t["source_test_id"],f.get("source_format_id")) for t in tests for f in t["fields"] if f.get("kind") in ("unknown","related")]
    if missing_fields or unsupported_fields:
        raise RuntimeError("Royal Lab source has unresolved result formats: missing=%d unsupported=%d" % (len(missing_fields),len(unsupported_fields)))
    duplicate_fields = [t["source_test_id"] for t in tests if len([str(f["source_format_id"]) for f in t["fields"] if f["source_format_id"] is not None]) != len({str(f["source_format_id"]) for f in t["fields"] if f["source_format_id"] is not None})]
    if duplicate_fields:
        raise RuntimeError("Duplicate Royal Lab result format IDs in tests: " + ", ".join(duplicate_fields[:10]))
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
    # Reject unknown NOT NULL columns unless the database itself supplies defaults.
    for table, schema, supplied in (
        (TESTS, tests_schema, {"code","name","active","price"}),
        (PARAMETERS, params_schema, {"test_id","code","name","unit","active"})):
        unsupported = [name for name,row in schema.items()
                       if row[3] and row[4] is None and not row[5] and name not in supplied]
        if unsupported:
            raise RuntimeError("Required columns need explicit NOVA mapping in " +
                               table + ": " + ", ".join(unsupported))
    # Never silently override manually edited clinical catalogue rows.
    existing_royal = conn.execute(
        "SELECT code FROM hospital_lab_tests WHERE code LIKE 'ROYAL-%'").fetchall()
    unexpected = sorted({row[0] for row in existing_royal} - set(plan["new_codes"]))
    if unexpected:
        raise RuntimeError("Unexpected existing ROYAL-prefixed tests: " +
                           ", ".join(unexpected[:10]))
    # Never change active clinical catalogues while a source definition is unresolved.
    conn.execute("SAVEPOINT royal_catalog_replacement")
    try:
        # Never delete old test/parameter IDs: historical lab orders may reference them.
        conn.execute("UPDATE hospital_lab_tests SET active=0 WHERE code NOT LIKE 'ROYAL-%'")
        conn.execute("""CREATE TABLE IF NOT EXISTS royal_lab_nova_parameter_metadata (
            nova_parameter_id INTEGER PRIMARY KEY,
            source_test_id TEXT NOT NULL,
            source_format_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            options_json TEXT NOT NULL,
            numeric_ranges_json TEXT NOT NULL,
            text_ranges_json TEXT NOT NULL
        )""")
        for test in plan["tests"]:
            code = "ROYAL-" + test["source_test_id"]
            row = conn.execute("SELECT id FROM hospital_lab_tests WHERE code=?", (code,)).fetchone()
            if row:
                test_id = row[0]
                conn.execute("UPDATE hospital_lab_tests SET name=?,active=1 WHERE id=?",
                             (test["name"],test_id))
            else:
                if "price" in tests_schema:
                    cur = conn.execute("INSERT INTO hospital_lab_tests(code,name,price,active) VALUES(?,?,0,1)",
                                       (code,test["name"]))
                else:
                    cur = conn.execute("INSERT INTO hospital_lab_tests(code,name,active) VALUES(?,?,1)",
                                       (code,test["name"]))
                test_id = cur.lastrowid
            for index, field in enumerate(test["fields"]):
                sid = field["source_format_id"]
                if sid is None:
                    continue
                param_code = source_code(sid)
                row = conn.execute("SELECT id FROM hospital_lab_parameters WHERE test_id=? AND code=?",
                                   (test_id,param_code)).fetchone()
                if row:
                    conn.execute("UPDATE hospital_lab_parameters SET name=?,unit=?,active=1 WHERE id=?",
                                 (field["label"],field["unit"],row[0]))
                else:
                    conn.execute("INSERT INTO hospital_lab_parameters(test_id,code,name,unit,active) VALUES(?,?,?,?,1)",
                                 (test_id,param_code,field["label"],field["unit"]))
        # Source options/ranges remain attached to original NOVA parameter IDs.
        for test in plan["tests"]:
            code = "ROYAL-" + test["source_test_id"]
            test_id = conn.execute("SELECT id FROM hospital_lab_tests WHERE code=?", (code,)).fetchone()[0]
            for field in test["fields"]:
                if field["source_format_id"] is None:
                    continue
                parameter_id = conn.execute(
                    "SELECT id FROM hospital_lab_parameters WHERE test_id=? AND code=?",
                    (test_id, source_code(field["source_format_id"]))).fetchone()[0]
                conn.execute("""INSERT INTO royal_lab_nova_parameter_metadata
                    (nova_parameter_id,source_test_id,source_format_id,kind,options_json,
                     numeric_ranges_json,text_ranges_json) VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(nova_parameter_id) DO UPDATE SET
                     kind=excluded.kind,options_json=excluded.options_json,
                     numeric_ranges_json=excluded.numeric_ranges_json,
                     text_ranges_json=excluded.text_ranges_json""",
                    (parameter_id,test["source_test_id"],str(field["source_format_id"]),
                     field["kind"],json.dumps(field["options"],ensure_ascii=False),
                     json.dumps(field["numeric_ranges"],ensure_ascii=False),
                     json.dumps(field["text_ranges"],ensure_ascii=False)))
        count = conn.execute("SELECT COUNT(*) FROM hospital_lab_tests WHERE code LIKE 'ROYAL-%' AND active=1").fetchone()[0]
        if count != 367:
            raise RuntimeError("NOVA replacement count mismatch")
        active_legacy = conn.execute(
            "SELECT COUNT(*) FROM hospital_lab_tests WHERE active=1 AND code NOT LIKE 'ROYAL-%'").fetchone()[0]
        if active_legacy:
            raise RuntimeError("Legacy NOVA tests still active after replacement")
        expected_parameters = sum(len(t["fields"]) for t in plan["tests"])
        actual_metadata = conn.execute(
            "SELECT COUNT(*) FROM royal_lab_nova_parameter_metadata").fetchone()[0]
        if actual_metadata != expected_parameters:
            raise RuntimeError("Royal Lab parameter metadata count mismatch: %d != %d" %
                               (actual_metadata,expected_parameters))
        missing_metadata = conn.execute("""SELECT COUNT(*) FROM hospital_lab_parameters p
            JOIN hospital_lab_tests t ON t.id=p.test_id
            LEFT JOIN royal_lab_nova_parameter_metadata m ON m.nova_parameter_id=p.id
            WHERE t.code LIKE 'ROYAL-%' AND m.nova_parameter_id IS NULL""").fetchone()[0]
        if missing_metadata:
            raise RuntimeError("Royal Lab NOVA parameters missing result metadata")
        conn.execute("RELEASE SAVEPOINT royal_catalog_replacement")
    except BaseException:
        conn.execute("ROLLBACK TO SAVEPOINT royal_catalog_replacement")
        conn.execute("RELEASE SAVEPOINT royal_catalog_replacement")
        raise
    return {"active_royal_lab_tests":367,"historical_tests_preserved":True,
            "source_fields_needing_review":plan["source_fields_needing_review"]}
