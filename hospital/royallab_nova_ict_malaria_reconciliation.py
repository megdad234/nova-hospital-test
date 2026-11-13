"""Repair ONLY the existing Royal Lab malaria ICT assay: TestID 14.

Proven from RoyalLabDB.bak: TestID 14, analyte 165, ResultFormatID 30,
original *inactive* result format with two active choices: Positive, Negative.
NOVA's original snapshot_item falls back to an unlabeled free-text RESULT
when all parameters are inactive. This narrowly scoped, photo-requested
hospital override re-enables exact existing source format metadata for
future paid orders; only untouched fallback order lines are backfilled.
The source library, old result values, all other assays, bills and print code
are not altered. Malaria RDT kit species and invalid-line logic are unknown;
never infer a Pf/Pan result or report an invalid cassette as Negative.
"""
import json
from hospital.royallab_nova_parameter_plan import source_code

SOURCE_ID="14"
SOURCE_ANALYTE_ID="165"
SOURCE_FORMAT_ID="30"
SOURCE_NAME="Ict fof malaria"
FIELD_NAME="I.C.T for Malaria"
DISPLAY_NAME="ICT for Malaria"
CODE="ROYAL-14"
PARAM_CODE=source_code(SOURCE_FORMAT_ID)
OPTIONS=("Positive","Negative")
OPTION_IDS=("131","132")
SCHEMA="""CREATE TABLE IF NOT EXISTS royal_lab_nova_ict_malaria_provenance(
    source_test_id TEXT PRIMARY KEY,
    source_analyte_id TEXT NOT NULL,
    source_format_id TEXT NOT NULL,
    original_source_inactive INTEGER NOT NULL,
    explicit_hospital_form_override INTEGER NOT NULL,
    original_source_name TEXT NOT NULL,
    confirmed_options_json TEXT NOT NULL
)"""
MIGRATION_SCHEMA="""CREATE TABLE IF NOT EXISTS royal_lab_nova_ict_malaria_migrated_items(
    item_id INTEGER PRIMARY KEY,
    migrated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)"""


def _tables(c):
    return {r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}


def _cols(c,table):
    return {r[1] for r in c.execute("PRAGMA table_info("+table+")")}


def _proven_source(catalog):
    # A different rapid kit, a changed source relation, or a source that's
    # since been reactivated requires new review: never invent a mapping.
    matching=[t for t in catalog if str(t.get("source_test_id"))==SOURCE_ID]
    if len(matching)!=1 or matching[0].get("name","").strip().casefold()!=SOURCE_NAME.casefold():
        raise ValueError("Original malaria ICT TestID 14 name/identity changed")
    fields=matching[0].get("fields")
    if not isinstance(fields,list) or len(fields)!=1:
        raise ValueError("Original malaria ICT result format is no longer unique")
    field=fields[0]
    if (str(field.get("source_analyte_id"))!=SOURCE_ANALYTE_ID
            or str(field.get("source_format_id"))!=SOURCE_FORMAT_ID
            or str(field.get("label") or "").strip().casefold()!=FIELD_NAME.casefold()):
        raise ValueError("Original malaria ICT analyte or ResultFormat ID changed")
    if field.get("active") not in (False,0,"False","false","0"):
        raise ValueError("Unexpected original malaria ICT active state; no override")
    opts=[x for x in field.get("options",[]) if
          x.get("active") not in (False,0,"False","false","0")]
    labels=[str(x.get("label") or "").strip() for x in opts]
    ids=[str(x.get("id") or "").strip() for x in opts]
    if labels!=list(OPTIONS) or ids!=list(OPTION_IDS):
        # Order is checked too, ensuring the source-derived choices
        # were not accidentally imported from the other malaria assay.
        raise ValueError("Original malaria ICT documented options differ")
    if field.get("kind") not in ("select","select_or_text","select_or_number"):
        raise ValueError("Original malaria ICT does not supply selectable options")
    return field


def reconcile_in_existing_nova(c,catalog):
    """Inside replace_catalog's SAVEPOINT after all original fields/metadata.

    Returns one supported clinical result field. No additional billable test.
    The inactivity in the recovered source is recorded, never falsified.
    """
    original=_proven_source(catalog)
    row=c.execute("SELECT id,name FROM hospital_lab_tests WHERE code=?",(CODE,)).fetchone()
    if not row or row[1].strip().casefold()!=SOURCE_NAME.casefold():
        raise RuntimeError("NOVA RoyalLab-14 identity differs; stop")
    test_id=row[0]
    rows=c.execute("""SELECT id,name,active FROM hospital_lab_parameters
        WHERE test_id=? AND code=?""",(test_id,PARAM_CODE)).fetchall()
    if len(rows)!=1 or rows[0][1].strip().casefold()!=FIELD_NAME.casefold():
        raise RuntimeError("Expected original malaria ICT parameter missing")
    existing=c.execute("""SELECT code FROM hospital_lab_parameters
        WHERE test_id=? AND active=1 AND code<>?""",(test_id,PARAM_CODE)).fetchall()
    if existing:
        raise RuntimeError("Existing custom malaria ICT fields require manual review")
    metadata=c.execute("""SELECT source_test_id,source_format_id,options_json
        FROM royal_lab_nova_parameter_metadata WHERE nova_parameter_id=?""",
        (rows[0][0],)).fetchone()
    if not metadata or metadata[:2]!=(SOURCE_ID,SOURCE_FORMAT_ID):
        raise RuntimeError("Original malaria ICT metadata mapping absent or incorrect")
    imported=json.loads(metadata[2])
    valid=[(str(x.get("id")),str(x.get("label") or "").strip())
           for x in imported if x.get("active") not in (False,0,"False","false","0")]
    if valid!=list(zip(OPTION_IDS,OPTIONS)):
        raise RuntimeError("Original malaria ICT result options were altered")
    # Explicitly revive the original *same* parameter ID only in NOVA, without
    # claiming that the archived Royal Lab parameter was originally active.
    c.execute("UPDATE hospital_lab_parameters SET active=1 WHERE id=?",(rows[0][0],))
    c.execute("""UPDATE royal_lab_nova_parameter_metadata SET kind='select'
        WHERE nova_parameter_id=?""",(rows[0][0],))
    c.execute("""UPDATE hospital_lab_tests SET name=? WHERE id=?""",
              (DISPLAY_NAME,test_id))
    c.execute(SCHEMA)
    c.execute(MIGRATION_SCHEMA)
    c.execute("""INSERT INTO royal_lab_nova_ict_malaria_provenance(
        source_test_id,source_analyte_id,source_format_id,
        original_source_inactive,explicit_hospital_form_override,
        original_source_name,confirmed_options_json)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(source_test_id) DO UPDATE SET
        confirmed_options_json=excluded.confirmed_options_json""",
        (SOURCE_ID,SOURCE_ANALYTE_ID,SOURCE_FORMAT_ID,1,1,
         matching_name(catalog),json.dumps(OPTIONS)))
    _backfill_only_blank_fallback(c,test_id,rows[0][0])
    return 1


def matching_name(catalog):
    return next(t["name"] for t in catalog if str(t["source_test_id"])==SOURCE_ID)


def _backfill_only_blank_fallback(c,test_id,param_id):
    required={"hospital_order_items","hospital_lab_lines","hospital_lab_revisions"}
    if not required.issubset(_tables(c)):
        return 0
    if not {"id","test_id","result_status","result_version","result_text"}.issubset(
            _cols(c,"hospital_order_items")):
        return 0
    if not {"id","item_id","parameter_id","code","name","unit","reference_range","value"}.issubset(
            _cols(c,"hospital_lab_lines")):
        return 0
    field=c.execute("""SELECT code,name,unit FROM hospital_lab_parameters
        WHERE id=?""",(param_id,)).fetchone()
    touched=0
    for item_id,status,ver,note in c.execute("""SELECT id,result_status,
        result_version,result_text FROM hospital_order_items WHERE test_id=?""",
        (test_id,)).fetchall():
        if status in ("approved","published") or (ver or 0)>0 or str(note or "").strip():
            continue
        if c.execute("""SELECT 1 FROM hospital_lab_revisions WHERE item_id=?
            LIMIT 1""",(item_id,)).fetchone():
            continue
        existing=c.execute("""SELECT id,code,value FROM hospital_lab_lines
            WHERE item_id=?""",(item_id,)).fetchall()
        if len(existing)!=1 or existing[0][1]!="RESULT" or str(existing[0][2] or "").strip():
            # Only the exact empty NOVA fallback can be reconciled.
            # If no lines exist, original snapshot_item() will use the active
            # source parameter on first access without any intervention.
            continue
        c.execute("""INSERT OR IGNORE INTO hospital_lab_lines
            (item_id,parameter_id,code,name,unit,reference_range,value)
            VALUES(?,?,?,?,?,'','')""",
            (item_id,param_id,field[0],field[1],field[2]))
        c.execute("""INSERT OR IGNORE INTO royal_lab_nova_ict_malaria_migrated_items
            (item_id) VALUES(?)""",(item_id,))
        touched+=1
    return touched


def overlay_order_detail(c,detail):
    """Hide ONLY the old blank RESULT fallback for migrated malaria ICT rows."""
    if not isinstance(detail,dict) or not isinstance(detail.get("items"),list):
        return detail
    if "royal_lab_nova_ict_malaria_migrated_items" not in _tables(c):
        return detail
    ids=[item.get("id") for item in detail["items"] if isinstance(item,dict)
         and type(item.get("id")) is int]
    if not ids:
        return detail
    marks={r[0] for r in c.execute("""SELECT item_id FROM
        royal_lab_nova_ict_malaria_migrated_items
        WHERE item_id IN ("""+",".join("?" for _ in ids)+")",ids)}
    if not marks:
        return detail
    result={**detail,"items":[]}
    for item in detail["items"]:
        if item.get("id") not in marks:
            result["items"].append(item)
            continue
        clean=[]
        for line in item.get("lines",[]):
            if (line.get("code")=="RESULT" and
                    not str(line.get("value") or "").strip()):
                continue  # retained in DB; excluded from clinical results UI
            clean.append(line)
        result["items"].append({**item,"lines":clean})
    return result


def validate_save_payload(c,data):
    """Reject unsupported malware ICT values on corrected orders.

    Existing signed/nonempty legacy RESULT lines keep original NOVA revision
    permissions; they are never forcibly reinterpreted as Negative/Positive.
    """
    if not isinstance(data,dict) or type(data.get("item_id")) is not int:
        return
    if "royal_lab_nova_ict_malaria_provenance" not in _tables(c):
        return
    item_id=data["item_id"]
    own=c.execute("""SELECT t.code FROM hospital_order_items i
        JOIN hospital_lab_tests t ON t.id=i.test_id WHERE i.id=?""",
        (item_id,)).fetchone()
    if not own or own[0]!=CODE:
        return
    values=data.get("values")
    if not isinstance(values,list):
        raise ValueError("ICT malaria requires structured results")
    for entry in values:
        if not isinstance(entry,dict) or type(entry.get("line_id")) is not int:
            raise ValueError("Invalid malaria ICT result line")
        row=c.execute("""SELECT code,value FROM hospital_lab_lines
            WHERE item_id=? AND id=?""",(item_id,entry["line_id"])).fetchone()
        if not row:
            raise ValueError("Result line does not belong to this ICT malaria order")
        if row[0]!="RESULT" and row[0]!=PARAM_CODE:
            raise ValueError("Unknown malaria ICT result parameter")
        if row[0]=="RESULT":
            if str(row[1] or "").strip():
                continue  # Historic already-reported legacy text is preserved.
            raise ValueError("Obsolete blank ICT malaria text field cannot be saved")
        value=entry.get("value")
        if value is None or value=="":
            continue
        if not isinstance(value,str) or value not in OPTIONS:
            raise ValueError("Select Positive or Negative for valid malaria ICT only")
