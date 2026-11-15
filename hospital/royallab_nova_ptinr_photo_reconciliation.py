"""Photo-confirmed PT/INR *result fields* for Royal Lab TestID 22 in NOVA.

The user confirmed the Alsharq Hospital reference labels: PT 10 - 15 sec,
INR Up to 1.0. This configures NEW NOVA order-entry fields and their normal
reference snapshots, NOT clinical diagnosis/warfarin therapeutic targets.

RoyalLabDB.bak identity:
  PT  = analyte 424, result format 701 (numeric), unit sec;
  INR = analyte 108, result format 288 (source open-text, local numeric form);
  PT Control = analyte 424, format 2319 (calibration, not shown in photo).
No original source rows, existing patient orders/results, pharmacy, printing,
and other assay formats are changed by this module.
"""
import json
import sqlite3
from decimal import Decimal, InvalidOperation
from hospital.royallab_nova_parameter_plan import source_code

SOURCE_ID = "22"
TEST_CODE = "ROYAL-22"
TEST_NAME = "PT/INR"
ORIGIN = "Alsharq Hospital PT/INR report, user supplied 2026-11-15"
# (source format, analyte id, label, unit, local display reference, sort)
FIELDS = (
    ("701", "424", "PT", "sec", "10 - 15", 1),
    ("288", "108", "INR", "", "Up to 1.0", 2),
)
CONTROL_FORMAT = "2319"
CONTROL_LABEL = "PT Control"
SCHEMA = """CREATE TABLE IF NOT EXISTS royal_lab_nova_ptinr_photo_provenance (
    source_test_id TEXT PRIMARY KEY,
    hospital_reference TEXT NOT NULL,
    pt_source_format_id TEXT NOT NULL,
    inr_source_format_id TEXT NOT NULL,
    pt_display_reference TEXT NOT NULL,
    inr_display_reference TEXT NOT NULL,
    inr_source_format_was_text INTEGER NOT NULL,
    original_control_format_id TEXT NOT NULL
)"""


def _original(catalog):
    matches = [t for t in catalog if str(t.get("source_test_id")) == SOURCE_ID]
    if len(matches) != 1 or str(matches[0].get("name") or "").strip() != TEST_NAME:
        raise ValueError("Original PT/INR TestID 22 changed identity; stop photo correction")
    test = matches[0]
    fields = test.get("fields")
    if not isinstance(fields, list):
        raise ValueError("Original PT/INR fields missing")
    by_format = {}
    for f in fields:
        sid = str(f.get("source_format_id"))
        if sid in by_format:
            raise ValueError("Duplicate PT/INR source format")
        by_format[sid] = f
    allowed = {spec[0] for spec in FIELDS} | {CONTROL_FORMAT}
    active = {sid for sid, f in by_format.items()
              if f.get("active") not in (False, 0, "False", "false", "0")}
    if active != allowed:
        raise ValueError("Unexpected active PT/INR formats: manual review required")
    for sid, analyte, label, unit, _ref, _order in FIELDS:
        f = by_format.get(sid)
        if (not f or str(f.get("source_analyte_id")) != analyte
                or str(f.get("label") or "").strip() != label
                or str(f.get("unit") or "").strip() != unit):
            raise ValueError("Original PT/INR analyte, format, label or unit changed")
    if by_format["701"].get("kind") != "number":
        raise ValueError("Original PT numeric format not proven")
    if by_format["288"].get("kind") not in ("text", "number"):
        raise ValueError("Original INR result is not a usable free-entry field")
    control = by_format.get(CONTROL_FORMAT)
    if (not control or str(control.get("source_analyte_id")) != "424"
            or str(control.get("label") or "").strip() != CONTROL_LABEL):
        raise ValueError("Original PT control identity changed")
    return by_format


def reconcile_in_existing_nova(conn, catalog, param_schema):
    """Apply screenshot ranges only to the exact source-verified PT/INR test.

    Called *inside* existing catalogue SAVEPOINT after source metadata import.
    Does not change order lines, patients, approved reports, reporting or prices.
    A subsequent administrator range edit is preserved on repeated startup.
    """
    source = _original(catalog)
    needed = {"reference_all", "reference_male", "reference_female", "sort_order"}
    has_references = needed.issubset(param_schema)
    # Royal Lab's disposable SOURCE-only import smoke fixture deliberately
    # uses a minimal NOVA table (id/code/name/unit/active). Do not create a
    # fake reference schema in that fixture. Real NOVA has all four columns.
    if not has_references and needed.intersection(param_schema):
        raise RuntimeError("Partially migrated NOVA PT/INR reference schema")
    test = conn.execute("SELECT id,name FROM hospital_lab_tests WHERE code=?",
                        (TEST_CODE,)).fetchone()
    if not test or str(test[1]).strip() != TEST_NAME:
        raise RuntimeError("NOVA PT/INR test identity does not match original")
    test_id = test[0]
    select_cols = ("id,code,name,unit,active,reference_all,reference_male,"
                   "reference_female,sort_order" if has_references else
                   "id,code,name,unit,active,'' AS reference_all,"
                   "'' AS reference_male,'' AS reference_female,0 AS sort_order")
    params = conn.execute("SELECT " + select_cols +
        " FROM hospital_lab_parameters WHERE test_id=?", (test_id,)).fetchall()
    by_code = {r[1]: r for r in params}
    if len(by_code) != len(params):
        raise RuntimeError("Duplicate NOVA PT/INR parameter codes")
    wanted = {source_code(x[0]) for x in FIELDS}
    control_code = source_code(CONTROL_FORMAT)
    if any(x not in by_code for x in wanted | {control_code}):
        raise RuntimeError("Expected Royal Lab PT, INR or PT Control parameter missing")

    if has_references:
        conn.execute(SCHEMA)
        prior = conn.execute("""SELECT pt_display_reference,inr_display_reference,
            pt_source_format_id,inr_source_format_id FROM
            royal_lab_nova_ptinr_photo_provenance WHERE source_test_id=?""",
            (SOURCE_ID,)).fetchone()
    else:
        prior = None
    if prior and (prior[0], prior[1], prior[2], prior[3]) != (
            FIELDS[0][4], FIELDS[1][4], FIELDS[0][0], FIELDS[1][0]):
        raise RuntimeError("PT/INR photo provenance changed; review required")

    for sid, analyte_id, label, unit, reference, order in FIELDS:
        code = source_code(sid)
        p = by_code[code]
        if (str(p[2]).strip() != label or str(p[3] or "").strip() != unit
                or p[4] != 1):
            raise RuntimeError("NOVA PT/INR current fields differ from original")
        metadata = conn.execute("""SELECT source_test_id,source_format_id,
            kind,options_json FROM royal_lab_nova_parameter_metadata
            WHERE nova_parameter_id=?""", (p[0],)).fetchone()
        if not metadata or metadata[:2] != (SOURCE_ID, sid):
            raise RuntimeError("PT/INR original format metadata missing")
        if json.loads(metadata[3]) != []:
            raise RuntimeError("Unexpected PT/INR dropdown choices; stop")
        # Local numeric-entry override: original INR format 288 is a string,
        # but the specifically requested hospital worksheet is quantitative.
        # The original RoyalLab JSON / source format ID remain unchanged.
        conn.execute("""UPDATE royal_lab_nova_parameter_metadata SET kind='number'
            WHERE nova_parameter_id=?""", (p[0],))
        # First install makes the requested photo reference effective. On
        # subsequent boots, protect any locally edited reference and sorting.
        if has_references and prior is None:
            conn.execute("""UPDATE hospital_lab_parameters
              SET reference_all=?,reference_male='',reference_female='',
                  sort_order=? WHERE id=?""", (reference, order, p[0]))
    control_param = by_code[control_code]
    if (str(control_param[2]).strip() != CONTROL_LABEL or
            str(control_param[3] or "").strip() != "sec"):
        raise RuntimeError("Expected original PT Control parameter changed")
    ctrl_meta = conn.execute("""SELECT source_test_id,source_format_id FROM
        royal_lab_nova_parameter_metadata WHERE nova_parameter_id=?""",
        (control_param[0],)).fetchone()
    if not ctrl_meta or tuple(ctrl_meta) != (SOURCE_ID, CONTROL_FORMAT):
        raise RuntimeError("Original PT Control source metadata missing")
    # Keep the historical source format/parameter row, but no extra control
    # line for NEW PT/INR orders, as requested in the pictured two-field form.
    conn.execute("UPDATE hospital_lab_parameters SET active=0 WHERE id=?",
                 (control_param[0],))
    if has_references and prior is None:
        conn.execute("""INSERT INTO royal_lab_nova_ptinr_photo_provenance
            (source_test_id,hospital_reference,pt_source_format_id,
             inr_source_format_id,pt_display_reference,inr_display_reference,
             inr_source_format_was_text,original_control_format_id)
            VALUES(?,?,?,?,?,?,?,?)""",
            (SOURCE_ID, ORIGIN, FIELDS[0][0], FIELDS[1][0],
             FIELDS[0][4], FIELDS[1][4],
             int(source["288"].get("kind") == "text"), CONTROL_FORMAT))
    live = conn.execute("""SELECT code FROM hospital_lab_parameters
        WHERE test_id=? AND active=1""" +
        (" ORDER BY sort_order,id" if has_references else " ORDER BY id"),
        (test_id,)).fetchall()
    if {r[0] for r in live} != wanted or len(live) != 2:
        raise RuntimeError("PT/INR must expose exactly two result fields")
    return len(live)


def validate_save_payload(conn, data):
    """Validate *new* corrected PT/INR numeric entries; keep legacy untouched."""
    if not isinstance(data, dict) or type(data.get("item_id")) is not int:
        return
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if "royal_lab_nova_ptinr_photo_provenance" not in tables:
        return
    if not {"hospital_order_items", "hospital_lab_tests", "hospital_lab_lines"}.issubset(tables):
        return
    row = conn.execute("""SELECT t.code,i.result_version,i.result_status
        FROM hospital_order_items i JOIN hospital_lab_tests t ON i.test_id=t.id
        WHERE i.id=?""", (data["item_id"],)).fetchone()
    if not row or row[0] != TEST_CODE:
        return
    # Existing previously saved/reviewed results retain their original
    # validation/revision and published-history behavior.
    if row[1] or row[2] in ("approved", "published"):
        return
    values = data.get("values")
    if not isinstance(values, list):
        raise ValueError("PT/INR requires structured result values")
    for entry in values:
        if not isinstance(entry, dict) or type(entry.get("line_id")) is not int:
            raise ValueError("Invalid PT/INR result line")
        line = conn.execute("""SELECT code,value FROM hospital_lab_lines
            WHERE item_id=? AND id=?""",
            (data["item_id"], entry["line_id"])).fetchone()
        if not line:
            raise ValueError("PT/INR result line does not belong to selected order")
        if line[0] not in {source_code(s[0]) for s in FIELDS}:
            # Historical PT Control lines are not valid new results.
            if not str(line[1] or "").strip():
                raise ValueError("Obsolete PT Control is not a reportable PT/INR field")
            continue
        value = entry.get("value")
        if value is None or value == "":
            continue
        if not isinstance(value, str) or len(value) > 100:
            raise ValueError("Invalid PT/INR numeric value")
        try:
            number = Decimal(value.strip())
        except (InvalidOperation, ValueError):
            raise ValueError("PT/INR result must be numeric") from None
        if not number.is_finite() or number < 0:
            raise ValueError("PT/INR result must be finite and nonnegative")
