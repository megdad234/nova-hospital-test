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
from decimal import Decimal, InvalidOperation

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
    # Historical unreported order items already have their initial ALP snapshot,
    # so NOVA's ensure_order_lines() will not add the corrected fields to them.
    # Backfill only untouched items; never revise signed or saved results.
    _backfill_unreported_orders(conn,test_id,param_schema)
    return len(FIELDS)


def _columns(conn, table):
    return {r[1] for r in conn.execute("PRAGMA table_info(" + table + ")")}


def _tables(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}


def _backfill_unreported_orders(conn, test_id, param_schema):
    """Add the correct blank GTT lines to old paid requests that never had results.

    The original ALP line remains IN THE DATABASE. Historical findings,
    approved reports, result revisions, prices and audit trails are untouched.
    """
    if not {"hospital_order_items","hospital_lab_lines",
            "hospital_lab_revisions"}.issubset(_tables(conn)):
        return 0
    items=_columns(conn,"hospital_order_items")
    needed={"id","test_id","result_status","result_version","result_text"}
    if not needed.issubset(items):
        # Lightweight source-audit fixtures lack the complete runtime schema.
        return 0
    params=conn.execute("""SELECT id,code,name,unit FROM hospital_lab_parameters
        WHERE test_id=? AND active=1 AND code LIKE ?
        ORDER BY sort_order,id""",(test_id,PARAM_PREFIX+"%")).fetchall()
    expected=[PARAM_PREFIX+field[0] for field in FIELDS]
    if [p[1] for p in params]!=expected:
        raise RuntimeError("The G.T.T corrected fields are incomplete or out of order")
    count=0
    for item_id,status,version,old_text in conn.execute(
        """SELECT id,result_status,result_version,result_text
           FROM hospital_order_items WHERE test_id=?""",(test_id,)).fetchall():
        if status in ("approved","published") or (version or 0)>0 or str(old_text or "").strip():
            continue
        if conn.execute("""SELECT 1 FROM hospital_lab_revisions
             WHERE item_id=? LIMIT 1""",(item_id,)).fetchone():
            continue
        prior=conn.execute("SELECT code,value FROM hospital_lab_lines WHERE item_id=?",
                           (item_id,)).fetchall()
        # No prior lines: original NOVA snapshot_item() can create the new form.
        # Any saved finding: preserve this legacy record without intervention.
        if not prior or any(str(row[1] or "").strip() for row in prior):
            continue
        for param_id,code,label,unit in params:
            conn.execute("""INSERT OR IGNORE INTO hospital_lab_lines
                (item_id,parameter_id,code,name,unit,reference_range,value)
                VALUES(?,?,?,?,?,'','')""",(item_id,param_id,code,label,unit))
        count+=1
    return count


def overlay_order_detail(conn, detail):
    """Keep the old ALP in archived records; hide only blank mislinked ALP.

    The 11 current fields already receive their types from NOVA's existing
    Royal Lab result metadata overlay. This function is presentation-only.
    """
    if not isinstance(detail,dict) or not isinstance(detail.get("items"),list):
        return detail
    if "hospital_order_items" not in _tables(conn):
        return detail
    out={**detail,"items":[]}
    for original in detail["items"]:
        item={**original, "lines":[dict(x) for x in original.get("lines",[])]}
        item_id=item.get("id")
        if type(item_id) is not int:
            out["items"].append(item)
            continue
        row=conn.execute("""SELECT t.code,i.result_status,i.result_version,i.result_text
            FROM hospital_order_items i
            JOIN hospital_lab_tests t ON t.id=i.test_id
            WHERE i.id=?""",(item_id,)).fetchone()
        if not row or row[0]!=SOURCE_CODE:
            out["items"].append(item)
            continue
        historical=(row[1] in ("approved","published") or (row[2] or 0)>0
                    or bool(str(row[3] or "").strip()))
        if "hospital_lab_revisions" in _tables(conn):
            historical |= bool(conn.execute("""SELECT 1 FROM hospital_lab_revisions
                WHERE item_id=? LIMIT 1""",(item_id,)).fetchone())
        if any(str(line.get("value") or "").strip() for line in item["lines"]):
            historical=True
        if not historical:
            # All original-result snapshots are preserved in SQLite, only the
            # incorrect ALP is omitted from the unreported staff UI/PDF.
            item["lines"]=[line for line in item["lines"]
                if not (str(line.get("code") or "").startswith("ROYAL_FMT_")
                        and str(line.get("name") or "").upper()=="ALP")]
        out["items"].append(item)
    return out


def validate_save_payload(conn,data):
    """Validate current GTT typed values before NOVA's original save workflow.

    Uses exact order-item and parameter identity, not display-name matching.
    NOVA itself retains payment, version, review and publication checks.
    """
    if not isinstance(data,dict) or type(data.get("item_id")) is not int:
        return
    if "hospital_order_items" not in _tables(conn):
        return
    item_id=data["item_id"]
    row=conn.execute("""SELECT t.code FROM hospital_order_items i
        JOIN hospital_lab_tests t ON t.id=i.test_id
        WHERE i.id=?""",(item_id,)).fetchone()
    if not row or row[0]!=SOURCE_CODE:
        return
    values=data.get("values")
    if not isinstance(values,list):
        raise ValueError("G.T.T requires structured result values")
    for entry in values:
        if not isinstance(entry,dict) or type(entry.get("line_id")) is not int:
            raise ValueError("Invalid G.T.T result line")
        line=conn.execute("""SELECT l.code FROM hospital_lab_lines l
            WHERE l.id=? AND l.item_id=?""",
            (entry["line_id"],item_id)).fetchone()
        if not line:
            raise ValueError("G.T.T line does not belong to the selected order")
        code=str(line[0])
        if not code.startswith(PARAM_PREFIX):
            raise ValueError("Historical ALP is not part of current G.T.T results")
        meta=conn.execute("""SELECT m.kind,m.options_json
            FROM royal_lab_nova_parameter_metadata m
            JOIN hospital_lab_parameters p ON p.id=m.nova_parameter_id
            JOIN hospital_order_items i ON i.test_id=p.test_id
            WHERE i.id=? AND p.code=? AND p.active=1""",
            (item_id,code)).fetchone()
        if not meta:
            raise ValueError("Unreviewed G.T.T field")
        value=entry.get("value")
        if value is None or value=="":
            continue
        if not isinstance(value,str) or len(value)>4000:
            raise ValueError("Invalid G.T.T value")
        if meta[0]=="select":
            labels=[opt.get("label") for opt in json.loads(meta[1])
                    if isinstance(opt,dict)
                    and opt.get("active") not in (False,0,"False","false","0")]
            if value not in labels:
                raise ValueError("Result not in documented G.T.T dropdown")
        elif meta[0]=="number":
            try:
                n=Decimal(value.strip())
            except (InvalidOperation,ValueError):
                raise ValueError("Numeric G.T.T result required") from None
            if not n.is_finite() or n<0:
                raise ValueError("Finite nonnegative G.T.T numeric result required")
