"""Reconcile incorrect original Royal Lab G.T.T TestID 240 with user-supplied lab form.

The recovered source's only result analyte for G.T.T (240) is mislabeled ALP.
The photographed Al Sharq Hospital GTT with urine glucose form explicitly has
fasting, 1-hour and 2-hour BLOOD and URINE glucose columns, plus glucose load,
specimen, method, interpretation and comments. This module retains the source
as historical provenance and preserves all existing order lines / patient data.

Only new NOVA orders use the 11 worksheet-described fields; no diagnostic
ranges, glucose dose or result defaults are created. The regular NOVA draft
and independent result-approval process still applies.
"""
import json

SOURCE_TEST_ID = "240"
SOURCE_NAME = "G.T.T"
SOURCE_BAD_FIELD = "ALP"
SOURCE_CODE = "ROYAL-240"
PARAM_PREFIX = "ROYAL_GTT_240_"
LEGACY_FORM_PROVENANCE = "Al Sharq Hospital GTT with urine glucose paper form (user photo 2026-11-13)"
URINE_CHOICES = ("Negative", "Trace", "+1", "+2", "+3", "+4")

FIELDS = (
    ("glucose_load", "Glucose Load", "number", "g", ()),
    ("specimen", "Specimen", "select", "", ("Plasma", "Serum")),
    ("method", "Method", "text", "", ()),
    ("blood_fasting", "Fasting (0 hour) - Blood Glucose", "number", "mg/dL", ()),
    ("urine_fasting", "Fasting (0 hour) - Urine Glucose", "select", "", URINE_CHOICES),
    ("blood_one_hour", "1 Hour - Blood Glucose", "number", "mg/dL", ()),
    ("urine_one_hour", "1 Hour - Urine Glucose", "select", "", URINE_CHOICES),
    ("blood_two_hours", "2 Hours - Blood Glucose", "number", "mg/dL", ()),
    ("urine_two_hours", "2 Hours - Urine Glucose", "select", "", URINE_CHOICES),
    ("interpretation", "Interpretation", "text", "", ()),
    ("comments", "Comments", "text", "", ()),
)


def _source_confirmed(catalog):
    """Fail closed if the pinned Royal Lab source changes from known bad GTT."""
    candidates = [test for test in catalog if str(test.get("source_test_id")) == SOURCE_TEST_ID]
    if len(candidates) != 1:
        raise ValueError("Original G.T.T TestID 240 identity missing or duplicated")
    test = candidates[0]
    if test.get("name", "").strip().casefold() != SOURCE_NAME.casefold():
        raise ValueError("Unexpected original G.T.T name; do not override source")
    fields = test.get("fields")
    if not isinstance(fields, list) or len(fields) != 1 or fields[0].get("label", "").strip() != SOURCE_BAD_FIELD:
        raise ValueError("Original G.T.T source no longer has the documented ALP defect; manual reconciliation required")
    if not str(fields[0].get("source_format_id") or "").strip():
        raise ValueError("Original G.T.T defective analyte has no source format identity")
    return fields[0]


def reconcile_in_existing_nova(conn, catalog, param_schema):
    """Called INSIDE existing catalogue SAVEPOINT after its original metadata.

    No orders/results, source library, prices, test identities, pharmacy or
    print templates are ever updated.
    """
    source_field = _source_confirmed(catalog)
    row = conn.execute("SELECT id,name FROM hospital_lab_tests WHERE code=?", (SOURCE_CODE,)).fetchone()
    if not row or row[1].strip().casefold() != SOURCE_NAME.casefold():
        raise RuntimeError("NOVA G.T.T has changed identity; cannot safely fix its form")
    test_id = row[0]
    from hospital.royallab_nova_parameter_plan import source_code
    bad_code = source_code(source_field["source_format_id"])
    bad_rows = conn.execute(
        "SELECT id,name FROM hospital_lab_parameters WHERE test_id=? AND code=?",
        (test_id, bad_code),
    ).fetchall()
    if len(bad_rows) != 1 or str(bad_rows[0][1]).strip() != SOURCE_BAD_FIELD:
        raise RuntimeError("Unexpected source ALP parameter for G.T.T; stop before modifying results")
    # Only deactivate original defective parameter for FUTURE order lines.
    # Existing order-line snapshots and parameter IDs are not deleted.
    conn.execute("UPDATE hospital_lab_parameters SET active=0 WHERE id=?", (bad_rows[0][0],))
    present = set()
    supports_sort = "sort_order" in param_schema
    for pos, (key,label,kind,unit,values) in enumerate(FIELDS, 1):
        code = PARAM_PREFIX + key
        present.add(code)
        rows = conn.execute(
            "SELECT id,name,unit FROM hospital_lab_parameters WHERE test_id=? AND code=?",
            (test_id, code),
        ).fetchall()
        if len(rows)>1:
            raise RuntimeError("Duplicate NOVA GTT parameter code")
        if rows:
            param_id,existing_label,existing_unit = rows[0]
            if existing_label != label or existing_unit != unit:
                raise RuntimeError("Existing reviewed GTT field changed; protect manual edits")
            conn.execute("UPDATE hospital_lab_parameters SET active=1 WHERE id=?", (param_id,))
        else:
            columns = ["test_id", "code", "name", "unit", "active"]
            values_sql = [test_id, code, label, unit, 1]
            if supports_sort:
                columns.append("sort_order")
                values_sql.append(pos)
            cur=conn.execute(
                "INSERT INTO hospital_lab_parameters("+",".join(columns)+") VALUES("+
                ",".join("?" for _ in columns)+")", values_sql,
            )
            param_id = cur.lastrowid
        options = [{"id":str(i+1), "label":value, "active":True}
                   for i,value in enumerate(values)]
        conn.execute("""INSERT INTO royal_lab_nova_parameter_metadata
                (nova_parameter_id,source_test_id,source_format_id,
                 kind,options_json,numeric_ranges_json,text_ranges_json)
              VALUES(?,?,?,?,?,?,?)
              ON CONFLICT(nova_parameter_id) DO UPDATE SET
                 kind=excluded.kind,options_json=excluded.options_json,
                 numeric_ranges_json=excluded.numeric_ranges_json,
                 text_ranges_json=excluded.text_ranges_json""",
                     (param_id,SOURCE_TEST_ID,"PHOTO_GTT_240_"+key,kind,
                      json.dumps(options,ensure_ascii=False),"[]","[]"))
    # Reject accidental extra active fields not part of the form; do not hide
    # independently created entries silently.
    others = conn.execute(
        "SELECT code FROM hospital_lab_parameters WHERE test_id=? AND active=1",
        (test_id,),
    ).fetchall()
    if {x[0] for x in others} != present:
        raise RuntimeError("Unexpected live GTT fields; preserve user work and require review")
    conn.execute("""CREATE TABLE IF NOT EXISTS royal_lab_nova_gtt_photo_provenance (
        source_test_id TEXT PRIMARY KEY,
        original_analyte_name TEXT NOT NULL,
        replacement_origin TEXT NOT NULL,
        decision TEXT NOT NULL
    )""")
    conn.execute("""INSERT OR REPLACE INTO royal_lab_nova_gtt_photo_provenance
        (source_test_id,original_analyte_name,replacement_origin,decision)
        VALUES(?,?,?,?)""", (SOURCE_TEST_ID,SOURCE_BAD_FIELD,
                            LEGACY_FORM_PROVENANCE,"future_orders_only"))
    return len(FIELDS)
