"""Fix G.T.T (original Royal Lab TestID 240) using the hospital's photographed form.

The original Royal Lab export incorrectly links G.T.T to a single ALP analyte.
This hospital-specific correction is attached to the SAME ROYAL-240 test, not
a second billable test. Historical ALP lines/values are never overwritten.
No glucose loading dose, diagnosis rule, reference range or price is invented.
"""
import json
import sqlite3
from decimal import Decimal, InvalidOperation
from hospital.nova_lab_local_tests import gtt_urine_template

TEST_CODE="ROYAL-240"
PREFIX="NOVA_GTT_"
FORM=tuple(gtt_urine_template()["fields"])
EXPECTED={PREFIX+f["key"] for f in FORM}
META_DDL="""CREATE TABLE IF NOT EXISTS nova_gtt_royal240_field_metadata(
    nova_parameter_id INTEGER PRIMARY KEY,
    field_key TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    options_json TEXT NOT NULL,
    evidence TEXT NOT NULL DEFAULT 'Al Sharq Hospital GTT urine glucose paper form'
)"""
MIGRATED_DDL="""CREATE TABLE IF NOT EXISTS nova_gtt_royal240_migrated_items(
    item_id INTEGER PRIMARY KEY,
    migrated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)"""


def _tables(c):
    return {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _cols(c,t):
    return {r[1] for r in c.execute("PRAGMA table_info("+t+")")}


def install(c):
    """Idempotent migration after Royal Lab source import and before new orders."""
    if not isinstance(c,sqlite3.Connection):
        raise TypeError("NOVA SQLite connection required")
    if not {"hospital_lab_tests","hospital_lab_parameters"}.issubset(_tables(c)):
        raise RuntimeError("Original NOVA lab tables unavailable")
    row=c.execute("SELECT id FROM hospital_lab_tests WHERE code=?",(TEST_CODE,)).fetchone()
    if row is None:
        raise RuntimeError("Original ROYAL-240 G.T.T test not installed")
    tid=row[0]
    paramschema=_cols(c,"hospital_lab_parameters")
    if not {"id","code","test_id","name","unit","active"}.issubset(paramschema):
        raise RuntimeError("NOVA original parameters schema incompatible")
    old=c.execute("""SELECT id,code,name FROM hospital_lab_parameters
        WHERE test_id=? AND code LIKE 'ROYAL_FMT_%'""",(tid,)).fetchall()
    if len(old)!=1 or str(old[0][2]).strip().upper()!="ALP":
        raise RuntimeError("G.T.T original ALP source identity differs; no automatic replacement")
    unrelated={r[0] for r in c.execute("""SELECT code FROM hospital_lab_parameters
        WHERE test_id=? AND code LIKE 'NOVA_GTT_%'""",(tid,))}-EXPECTED
    if unrelated:
        raise RuntimeError("Unknown G.T.T override fields: do not overwrite staff changes")
    c.execute("SAVEPOINT nova_gtt_photo_fix")
    try:
        c.execute(META_DDL)
        c.execute(MIGRATED_DDL)
        # Deactivate ONLY for future snapshots. Its row and historical values stay.
        c.execute("UPDATE hospital_lab_parameters SET active=0 WHERE id=?",(old[0][0],))
        for index,field in enumerate(FORM):
            code=PREFIX+field["key"]
            existing=c.execute("""SELECT id,name,unit FROM hospital_lab_parameters
                WHERE test_id=? AND code=?""",(tid,code)).fetchone()
            if existing:
                pid=existing[0]
                if existing[1]!=field["label"] or existing[2]!=field["unit"]:
                    raise RuntimeError("Existing reviewed G.T.T field changed; protecting it")
                c.execute("UPDATE hospital_lab_parameters SET active=1 WHERE id=?",(pid,))
            else:
                columns=["test_id","code","name","unit","active"]
                values=[tid,code,field["label"],field["unit"],1]
                if "sort_order" in paramschema:
                    columns.append("sort_order")
                    values.append(index)
                if "reference_all" in paramschema:
                    columns.append("reference_all")
                    values.append("")
                pid=c.execute("INSERT INTO hospital_lab_parameters("+
                    ",".join(columns)+") VALUES("+",".join("?" for _ in columns)+")",
                    values).lastrowid
            c.execute("""INSERT INTO nova_gtt_royal240_field_metadata
                (nova_parameter_id,field_key,kind,options_json) VALUES(?,?,?,?)
                ON CONFLICT(nova_parameter_id) DO UPDATE SET
                  field_key=excluded.field_key,kind=excluded.kind,
                  options_json=excluded.options_json""",
                (pid,field["key"],field["kind"],
                 json.dumps(field["options"],ensure_ascii=False)))
        _backfill_blank_preexisting_orders(c,tid)
        c.execute("RELEASE SAVEPOINT nova_gtt_photo_fix")
    except BaseException:
        c.execute("ROLLBACK TO SAVEPOINT nova_gtt_photo_fix")
        c.execute("RELEASE SAVEPOINT nova_gtt_photo_fix")
        raise
    return {"original_test":TEST_CODE,"new_result_fields":len(FORM),
            "source_alp_retained":True,"patient_values_modified":False}


def _backfill_blank_preexisting_orders(c,tid):
    required={"hospital_order_items","hospital_lab_lines","hospital_lab_revisions"}
    if not required.issubset(_tables(c)):
        return 0
    if not {"id","test_id","result_status","result_version","result_text"}.issubset(
            _cols(c,"hospital_order_items")):
        return 0
    params=c.execute("""SELECT id,code,name,unit FROM hospital_lab_parameters
        WHERE test_id=? AND active=1 AND code LIKE ?
        ORDER BY sort_order,id""",(tid,PREFIX+"%")).fetchall()
    if [x[1] for x in params]!=[PREFIX+f["key"] for f in FORM]:
        raise RuntimeError("G.T.T result form order or definition incomplete")
    migrated=0
    items=c.execute("""SELECT id,result_status,result_version,result_text
        FROM hospital_order_items WHERE test_id=?""",(tid,)).fetchall()
    for item_id,status,version,legacy_text in items:
        if status in ("approved","published") or (version or 0)>0 or str(legacy_text or "").strip():
            continue
        if c.execute("SELECT 1 FROM hospital_lab_revisions WHERE item_id=? LIMIT 1",
                     (item_id,)).fetchone():
            continue
        existing=c.execute("SELECT code,value FROM hospital_lab_lines WHERE item_id=?",
                           (item_id,)).fetchall()
        if not existing or any(str(row[1] or "").strip() for row in existing):
            # New orders without lines use normal NOVA snapshot_item(); stored
            # results are NEVER migrated or rewritten.
            continue
        for pid,code,label,unit in params:
            c.execute("""INSERT OR IGNORE INTO hospital_lab_lines
                (item_id,parameter_id,code,name,unit,reference_range,value)
                VALUES(?,?,?,?,?,'','')""",(item_id,pid,code,label,unit))
        c.execute("INSERT OR IGNORE INTO nova_gtt_royal240_migrated_items(item_id) VALUES(?)",
                  (item_id,))
        migrated+=1
    return migrated


def overlay_order_detail(c,detail):
    """Provide typed GTT inputs and hide ALP only on safely migrated old orders."""
    if not isinstance(detail,dict) or not isinstance(detail.get("items"),list):
        return detail
    if not {"nova_gtt_royal240_field_metadata","hospital_order_items"}.issubset(_tables(c)):
        return detail
    result={**detail,"items":[]}
    for old in detail["items"]:
        item={**old,"lines":[dict(x) for x in old.get("lines",[])]}
        item_id=item.get("id")
        if type(item_id) is not int:
            result["items"].append(item)
            continue
        owner=c.execute("""SELECT t.code FROM hospital_order_items i
            JOIN hospital_lab_tests t ON t.id=i.test_id WHERE i.id=?""",
            (item_id,)).fetchone()
        if not owner or owner[0]!=TEST_CODE:
            result["items"].append(item)
            continue
        migrated=bool(c.execute("SELECT 1 FROM nova_gtt_royal240_migrated_items WHERE item_id=?",
                                (item_id,)).fetchone())
        rows=[]
        for line in item["lines"]:
            code=str(line.get("code") or "")
            if (migrated and code.startswith("ROYAL_FMT_")
                    and str(line.get("name") or "").strip().upper()=="ALP"
                    and not str(line.get("value") or "").strip()):
                # ALP's original line remains in the database for audit, but
                # never resurfaces even after new GTT findings are saved.
                continue
            if code.startswith(PREFIX):
                meta=c.execute("""SELECT m.kind,m.options_json
                    FROM nova_gtt_royal240_field_metadata m
                    JOIN hospital_lab_parameters p ON p.id=m.nova_parameter_id
                    JOIN hospital_order_items i ON i.test_id=p.test_id
                    WHERE i.id=? AND p.code=? AND p.active=1""",
                    (item_id,code)).fetchone()
                if meta:
                    line["royal_lab_field"]={"kind":meta[0],
                                             "options":json.loads(meta[1])}
            rows.append(line)
        item["lines"]=rows
        result["items"].append(item)
    return result


def validate_save_payload(c,data):
    """Validate GTT numbers and documented dropdowns before original NOVA save."""
    if not isinstance(data,dict) or type(data.get("item_id")) is not int:
        return
    if "nova_gtt_royal240_field_metadata" not in _tables(c):
        return
    item_id=data["item_id"]
    owner=c.execute("""SELECT t.code FROM hospital_order_items i
        JOIN hospital_lab_tests t ON t.id=i.test_id WHERE i.id=?""",
        (item_id,)).fetchone()
    if not owner or owner[0]!=TEST_CODE:
        return
    values=data.get("values")
    if not isinstance(values,list):
        raise ValueError("G.T.T requires structured result values")
    for entry in values:
        if not isinstance(entry,dict) or type(entry.get("line_id")) is not int:
            raise ValueError("Invalid G.T.T result line")
        line=c.execute("""SELECT code FROM hospital_lab_lines
            WHERE id=? AND item_id=?""",(entry["line_id"],item_id)).fetchone()
        if not line:
            raise ValueError("G.T.T result line does not belong to this order")
        if not str(line[0]).startswith(PREFIX):
            raise ValueError("Historical ALP is not a G.T.T result")
        metadata=c.execute("""SELECT m.kind,m.options_json
            FROM nova_gtt_royal240_field_metadata m
            JOIN hospital_lab_parameters p ON p.id=m.nova_parameter_id
            JOIN hospital_order_items i ON i.test_id=p.test_id
            WHERE i.id=? AND p.code=? AND p.active=1""",
            (item_id,line[0])).fetchone()
        if not metadata:
            raise ValueError("Unreviewed G.T.T result field")
        value=entry.get("value")
        if value is None or value=="":
            continue
        if not isinstance(value,str) or len(value)>4000:
            raise ValueError("Invalid G.T.T value")
        if metadata[0]=="select":
            if value not in json.loads(metadata[1]):
                raise ValueError("G.T.T result not in documented dropdown")
        if metadata[0]=="number":
            try:
                num=Decimal(value.strip())
            except (InvalidOperation,ValueError):
                raise ValueError("Numeric G.T.T result required") from None
            if not num.is_finite() or num<0:
                raise ValueError("G.T.T numeric result must be finite and nonnegative")
