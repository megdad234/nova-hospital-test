"""Fix the EXISTING NOVA ROYAL-240 G.T.T result form using the user-supplied paper.

The recovered Royal Lab TestID 240 has exactly one erroneous ALP analyte.
This is a documented hospital-specific correction, NOT a fabricated Royal Lab
ResultFormat. Exact existing test identity, order price and historic results
are retained; original Royal Lab source records are not modified.
"""
import json
import sqlite3
from decimal import Decimal, InvalidOperation
from hospital.nova_lab_local_tests import gtt_urine_template

TARGET_CODE = "ROYAL-240"
PREFIX = "NOVA_GTT_"
SCHEMA = """CREATE TABLE IF NOT EXISTS nova_gtt_royal240_field_metadata (
    nova_parameter_id INTEGER PRIMARY KEY,
    field_key TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    options_json TEXT NOT NULL,
    evidence TEXT NOT NULL DEFAULT 'Al Sharq Hospital paper GTT with urine glucose'
)"""
# No invented reference values or glucose dose.
FIELDS = tuple(gtt_urine_template()["fields"])
EXPECTED_CODES = {PREFIX + f["key"] for f in FIELDS}


def _tables(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}


def _columns(conn, table):
    return {r[1] for r in conn.execute("PRAGMA table_info(" + table + ")")}


def install(conn):
    """Idempotent clinical-template migration; never modify paid order amounts."""
    if not isinstance(conn, sqlite3.Connection):
        raise TypeError("NOVA SQLite connection required")
    if not {"hospital_lab_tests", "hospital_lab_parameters"}.issubset(_tables(conn)):
        raise RuntimeError("NOVA laboratory schema not initialized")
    test = conn.execute("SELECT id FROM hospital_lab_tests WHERE code=?",
                        (TARGET_CODE,)).fetchone()
    if not test:
        raise RuntimeError("Original Royal Lab G.T.T TestID 240 missing")
    test_id = test[0]
    cols = _columns(conn, "hospital_lab_parameters")
    if not {"id", "test_id", "code", "name", "unit", "active"}.issubset(cols):
        raise RuntimeError("Original NOVA parameter schema incompatible")
    # This exact source contains ALP as its only current linked result.
    # Refuse to overwrite an unexpected repaired/edited source form.
    old = conn.execute("""SELECT id,code,name FROM hospital_lab_parameters
        WHERE test_id=? AND code LIKE 'ROYAL_FMT_%'""", (test_id,)).fetchall()
    if len(old) != 1 or str(old[0][2]).strip().upper() != "ALP":
        raise RuntimeError("G.T.T original ALP source definition changed; manual review required")
    existing = conn.execute("""SELECT code FROM hospital_lab_parameters
        WHERE test_id=? AND code LIKE 'NOVA_GTT_%'""", (test_id,)).fetchall()
    unexpected = {r[0] for r in existing} - EXPECTED_CODES
    if unexpected:
        raise RuntimeError("Unexpected hospital-specific G.T.T fields; migration refused")
    conn.execute("SAVEPOINT nova_gtt_royal240_fix")
    try:
        conn.execute(SCHEMA)
        # Disable the incorrect ALP parameter only for FUTURE snapshots, retain
        # its row, source metadata, history and any existing order-line values.
        conn.execute("UPDATE hospital_lab_parameters SET active=0 WHERE id=?",
                     (old[0][0],))
        for index, field in enumerate(FIELDS):
            code = PREFIX + field["key"]
            row = conn.execute("""SELECT id,name,unit FROM hospital_lab_parameters
                WHERE test_id=? AND code=?""", (test_id,code)).fetchone()
            if row:
                parameter_id = row[0]
                if row[1] != field["label"] or row[2] != field["unit"]:
                    raise RuntimeError("G.T.T template was edited; refusing silent overwrite")
                conn.execute("UPDATE hospital_lab_parameters SET active=1 WHERE id=?",
                             (parameter_id,))
            else:
                names=["test_id","code","name","unit","active"]
                values=[test_id,code,field["label"],field["unit"],1]
                if "sort_order" in cols:
                    names.append("sort_order")
                    values.append(index)
                if "reference_all" in cols:
                    names.append("reference_all")
                    values.append("")
                sql=("INSERT INTO hospital_lab_parameters (" + ",".join(names) +
                     ") VALUES (" + ",".join("?" for _ in names) + ")")
                parameter_id=conn.execute(sql,values).lastrowid
            conn.execute("""INSERT INTO nova_gtt_royal240_field_metadata
                (nova_parameter_id,field_key,kind,options_json)
                VALUES(?,?,?,?)
                ON CONFLICT(nova_parameter_id) DO UPDATE SET
                    field_key=excluded.field_key, kind=excluded.kind,
                    options_json=excluded.options_json""",
                (parameter_id,field["key"],field["kind"],
                 json.dumps(field["options"],ensure_ascii=False)))
        _backfill_unreported_orders(conn,test_id)
        conn.execute("RELEASE SAVEPOINT nova_gtt_royal240_fix")
    except BaseException:
        conn.execute("ROLLBACK TO SAVEPOINT nova_gtt_royal240_fix")
        conn.execute("RELEASE SAVEPOINT nova_gtt_royal240_fix")
        raise
    return {"test_code":TARGET_CODE, "corrected_fields":len(FIELDS),
            "original_alp_retained_inactive":True, "patient_values_overwritten":False}


def _backfill_unreported_orders(conn,test_id):
    """Add empty new form lines ONLY to untouched existing G.T.T requests.

    No changes to existing lines, revision history or approved/draft results.
    In-flight patient requests never require cancellation or another payment.
    """
    needed={"hospital_order_items","hospital_lab_lines","hospital_lab_revisions"}
    if not needed.issubset(_tables(conn)):
        return
    items=_columns(conn,"hospital_order_items")
    if not {"id","test_id","result_version","result_status","result_text"}.issubset(items):
        raise RuntimeError("Cannot safely identify unreported NOVA G.T.T items")
    params=conn.execute("""SELECT id,code,name,unit
        FROM hospital_lab_parameters
        WHERE test_id=? AND code LIKE 'NOVA_GTT_%' AND active=1
        ORDER BY sort_order,id""",(test_id,)).fetchall()
    if len(params)!=len(FIELDS):
        raise RuntimeError("Incomplete new NOVA G.T.T field definitions")
    item_rows=conn.execute("""SELECT id,result_status,result_version,result_text
        FROM hospital_order_items WHERE test_id=?""",(test_id,)).fetchall()
    for item_id,status,version,result_text in item_rows:
        if status in ("approved","published") or (version or 0)>0 or str(result_text or "").strip():
            continue
        if conn.execute("SELECT 1 FROM hospital_lab_revisions WHERE item_id=? LIMIT 1",
                        (item_id,)).fetchone():
            continue
        prior=conn.execute("""SELECT code,value FROM hospital_lab_lines
            WHERE item_id=?""",(item_id,)).fetchall()
        if not prior or any(str(row[1] or "").strip() for row in prior):
            # No lines -> original snapshot_item will create the full corrected form.
            # Nonempty -> preserve as a real historical / in-progress finding.
            continue
        for param_id,code,name,unit in params:
            conn.execute("""INSERT OR IGNORE INTO hospital_lab_lines
                (item_id,parameter_id,code,name,unit,reference_range,value)
                VALUES(?,?,?,?,?,'','')""",(item_id,param_id,code,name,unit))


def overlay_order_detail(conn,detail):
    """Render correct existing G.T.T rows with dropdowns, keep old findings."""
    if not isinstance(detail,dict) or not isinstance(detail.get("items"),list):
        return detail
    if "nova_gtt_royal240_field_metadata" not in _tables(conn):
        return detail
    out={**detail,"items":[]}
    for original in detail["items"]:
        item={**original,"lines":[dict(x) for x in original.get("lines",[])]}
        item_id=item.get("id")
        if type(item_id) is not int:
            out["items"].append(item)
            continue
        row=conn.execute("""SELECT t.code,i.result_version,i.result_status
            FROM hospital_order_items i JOIN hospital_lab_tests t ON t.id=i.test_id
            WHERE i.id=?""",(item_id,)).fetchone()
        if not row or row[0]!=TARGET_CODE:
            out["items"].append(item)
            continue
        historic = (row[1] or 0)>0 or row[2] in ("approved","published")
        historic |= bool(conn.execute("""SELECT 1 FROM hospital_lab_revisions
            WHERE item_id=? LIMIT 1""",(item_id,)).fetchone())
        if any(str(x.get("value") or "").strip() for x in item["lines"]
               if str(x.get("code") or "").startswith("ROYAL_FMT_")):
            historic=True
        safe_lines=[]
        for line in item["lines"]:
            code=str(line.get("code") or "")
            # Only hide the wrong *empty* ALP result from a never-revised order.
            # The original line remains in the DB for provenance/auditing.
            if not historic and code.startswith("ROYAL_FMT_") and not str(line.get("value") or "").strip():
                continue
            if code.startswith(PREFIX):
                meta=conn.execute("""SELECT f.kind,f.options_json FROM
                    nova_gtt_royal240_field_metadata f
                    JOIN hospital_lab_parameters p ON p.id=f.nova_parameter_id
                    JOIN hospital_order_items i ON i.test_id=p.test_id
                    WHERE i.id=? AND p.code=? AND p.active=1""",
                    (item_id,code)).fetchone()
                if meta:
                    line["royal_lab_field"]={"kind":meta[0],"options":json.loads(meta[1])}
            safe_lines.append(line)
        item["lines"]=safe_lines
        out["items"].append(item)
    return out


def validate_save_payload(conn,data):
    """Preserve original paid-order version checks and validate GTT values."""
    if not isinstance(data,dict) or type(data.get("item_id")) is not int:
        return
    if "nova_gtt_royal240_field_metadata" not in _tables(conn):
        return
    item_id=data["item_id"]
    row=conn.execute("""SELECT t.code FROM hospital_order_items i
        JOIN hospital_lab_tests t ON t.id=i.test_id
        WHERE i.id=?""",(item_id,)).fetchone()
    if not row or row[0]!=TARGET_CODE:
        return
    values=data.get("values")
    if not isinstance(values,list):
        raise ValueError("G.T.T must contain structured result values")
    for entry in values:
        if not isinstance(entry,dict) or type(entry.get("line_id")) is not int:
            raise ValueError("Invalid G.T.T result line")
        line=conn.execute("""SELECT l.code,l.value
            FROM hospital_lab_lines l WHERE l.id=? AND l.item_id=?""",
            (entry["line_id"],item_id)).fetchone()
        if not line:
            raise ValueError("G.T.T result line does not belong to this patient order")
        code=line[0]
        if not code.startswith(PREFIX):
            # Existing historical ALP data is read-only and never a new G.T.T result.
            raise ValueError("Original ALP is not a valid G.T.T result field")
        meta=conn.execute("""SELECT f.kind,f.options_json
            FROM nova_gtt_royal240_field_metadata f
            JOIN hospital_lab_parameters p ON p.id=f.nova_parameter_id
            JOIN hospital_order_items i ON i.test_id=p.test_id
            WHERE i.id=? AND p.code=? AND p.active=1""",
            (item_id,code)).fetchone()
        if not meta:
            raise ValueError("Unreviewed G.T.T result field")
        v=entry.get("value")
        if v is None or v=="":
            continue
        if not isinstance(v,str) or len(v)>4000:
            raise ValueError("Invalid G.T.T result value")
        if meta[0]=="select" and v not in json.loads(meta[1]):
            raise ValueError("G.T.T result is not a documented dropdown option")
        if meta[0]=="number":
            try:
                n=Decimal(v.strip())
            except (ValueError,InvalidOperation):
                raise ValueError("G.T.T numeric result required") from None
            if not n.is_finite() or n<0:
                raise ValueError("G.T.T numeric result must be finite and nonnegative")
