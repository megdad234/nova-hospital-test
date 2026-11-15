"""Photo-confirmed qualitative ICT for Typhoid form, TestID 309 ONLY.

RoyalLabDB original TestID 309 has three active analytes 1291/1292/1293
(ICT for Typhoid, IgG, IgM) but NO attached ResultFormat or options.
An unrelated empty source test, TestID 347, shares a similar name; do not
combine or rename it. Widal TestID 115 is entirely unrelated.

User's 2026-11-15 NOVA screenshot confirms exactly these three input rows,
and user requested Positive / Negative dropdowns. The two options below
are therefore an EXPLICIT HOSPITAL WORKSHEET OVERRIDE, not claimed to be
present in RoyalLabDB. Original source/catalog remains immutable.

No changes to historical orders/results, prices, print templates, pharmacy,
other tests, or approval/payment/version logic.
"""
import json
from hospital.royallab_nova_parameter_plan import source_code

SOURCE_TEST_ID = "309"
SOURCE_TEST_NAME = "ICT for Typhoid"
TEST_CODE = "ROYAL-309"
PHOTO_ORIGIN = "NOVA screenshot 2026-11-15, user-approved Positive/Negative"
# Source analyte ID, exact name, original synthetic format ID (NO ResultFormat).
FIELD_SPECS = (
    ("1291", "ICT for Typhoid", "ANALYTE-1291"),
    ("1292", "IgG", "ANALYTE-1292"),
    ("1293", "IgM", "ANALYTE-1293"),
)
OPTIONS = ("Positive", "Negative")
PARAM_CODES = tuple(source_code(sid) for _a, _n, sid in FIELD_SPECS)
PROVENANCE_SQL = """CREATE TABLE IF NOT EXISTS royal_lab_nova_ict_typhoid_photo_provenance (
    source_test_id TEXT PRIMARY KEY,
    photo_origin TEXT NOT NULL,
    original_source_has_no_result_formats INTEGER NOT NULL,
    source_analytes_json TEXT NOT NULL,
    confirmed_options_json TEXT NOT NULL
)"""


def _tables(conn):
    return {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}


def _columns(conn, name):
    return {row[1] for row in conn.execute("PRAGMA table_info(" + name + ")")}


def _source(catalog):
    if not isinstance(catalog, list):
        raise ValueError("Royal Lab source catalogue required")
    matches = [t for t in catalog if str(t.get("source_test_id")) == SOURCE_TEST_ID]
    if len(matches) != 1 or str(matches[0].get("name") or "").strip() != SOURCE_TEST_NAME:
        raise ValueError("ICT Typhoid TestID 309 identity changed; stop")
    fs = matches[0].get("fields")
    if not isinstance(fs, list) or len(fs) != len(FIELD_SPECS):
        raise ValueError("Original ICT Typhoid three-field source changed")
    expected = {sid: (aid, name) for aid, name, sid in FIELD_SPECS}
    for field in fs:
        sid = str(field.get("source_format_id") or "")
        identity = expected.pop(sid, None)
        if identity is None:
            raise ValueError("Typhoid source format identity unexpected")
        if (str(field.get("source_analyte_id")) != identity[0] or
                str(field.get("label") or "").strip() != identity[1] or
                str(field.get("unit") or "").strip() or field.get("types") or
                field.get("kind") != "text" or field.get("options")):
            raise ValueError("Typhoid no-format source is no longer as documented")
        if field.get("active") in (False, 0, "False", "false", "0"):
            raise ValueError("Original Typhoid analyte unexpectedly inactive")
    if expected:
        raise ValueError("Original Typhoid analytes missing")
    return matches[0]


def reconcile_in_existing_nova(conn, catalog, param_schema):
    """Update only existing NOVA TestID 309 parameter dropdown presentation.

    Called from catalog replace SAVEPOINT after imported original metadata.
    It reuses three original parameter IDs and does not touch result snapshots.
    """
    _source(catalog)
    row = conn.execute(
        "SELECT id,name FROM hospital_lab_tests WHERE code=?",
        (TEST_CODE,)).fetchone()
    if not row or str(row[1]).strip() != SOURCE_TEST_NAME:
        raise RuntimeError("NOVA source TestID 309 mapping changed")
    test_id = row[0]
    all_params = conn.execute("""SELECT id,code,name,unit,active
        FROM hospital_lab_parameters WHERE test_id=?""", (test_id,)).fetchall()
    by_code = {r[1]: r for r in all_params}
    if len(all_params) != len(FIELD_SPECS) or set(by_code) != set(PARAM_CODES):
        raise RuntimeError("Typhoid fields differ from exact photo/source identities")
    if "royal_lab_nova_parameter_metadata" not in _tables(conn):
        raise RuntimeError("Royal Lab original parameter metadata missing")

    for analyte, label, sid in FIELD_SPECS:
        code = source_code(sid)
        param = by_code[code]
        if (str(param[2]).strip() != label or str(param[3] or "").strip() or param[4] != 1):
            raise RuntimeError("Typhoid original NOVA field is not active or differs")
        metadata = conn.execute("""SELECT source_test_id,source_format_id,kind,
            options_json FROM royal_lab_nova_parameter_metadata
            WHERE nova_parameter_id=?""", (param[0],)).fetchone()
        if (not metadata or tuple(metadata[:3]) != (SOURCE_TEST_ID, sid, "text")
                or json.loads(metadata[3]) != []):
            raise RuntimeError("Typhoid original no-format metadata differs")
    conn.execute(PROVENANCE_SQL)
    prior = conn.execute("""SELECT source_analytes_json, confirmed_options_json
        FROM royal_lab_nova_ict_typhoid_photo_provenance WHERE source_test_id=?""",
        (SOURCE_TEST_ID,)).fetchone()
    expected_source = json.dumps(FIELD_SPECS, ensure_ascii=False)
    expected_options = json.dumps(OPTIONS, ensure_ascii=False)
    if prior and (prior[0], prior[1]) != (expected_source, expected_options):
        raise RuntimeError("Existing hospital Typhoid form override differs")
    for position, (_analyte, label, sid) in enumerate(FIELD_SPECS, 1):
        code = source_code(sid)
        param_id = by_code[code][0]
        # Stored in NOVA metadata, never in original RoyalLabDB JSON.
        opts = [{"id":str(i + 1), "label":value, "active":True}
                for i, value in enumerate(OPTIONS)]
        conn.execute("""UPDATE royal_lab_nova_parameter_metadata SET
            kind='select',options_json=? WHERE nova_parameter_id=?""",
            (json.dumps(opts, ensure_ascii=False), param_id))
        # The existing source fields have no original sorting metadata.
        # Set photo order on the first installation only, never overwrite
        # administrator ordering when the local override is already present.
        if prior is None and "sort_order" in param_schema:
            conn.execute("UPDATE hospital_lab_parameters SET sort_order=? WHERE id=?",
                         (position, param_id))
    if prior is None:
        conn.execute("""INSERT INTO royal_lab_nova_ict_typhoid_photo_provenance
            (source_test_id,photo_origin,original_source_has_no_result_formats,
             source_analytes_json,confirmed_options_json)
            VALUES(?,?,?,?,?)""",
            (SOURCE_TEST_ID,PHOTO_ORIGIN,1,expected_source,expected_options))
    live = conn.execute("""SELECT code FROM hospital_lab_parameters
        WHERE test_id=? AND active=1""", (test_id,)).fetchall()
    if len(live) != 3 or {r[0] for r in live} != set(PARAM_CODES):
        raise RuntimeError("ICT Typhoid must keep three independent active result inputs")
    return len(live)


def validate_save_payload(conn, data):
    """Allow only photo-approved choices on new TestID 309 findings.

    Leave historical nonempty/signed results and unrelated tests untouched.
    Original NOVA payment, revision, version, and publish checks still run.
    """
    if not isinstance(data, dict) or type(data.get("item_id")) is not int:
        return
    tables = _tables(conn)
    if not {"royal_lab_nova_ict_typhoid_photo_provenance",
            "hospital_lab_tests", "hospital_order_items",
            "hospital_lab_lines"}.issubset(tables):
        return
    row = conn.execute("""SELECT t.code,i.result_status,i.result_version
        FROM hospital_order_items i JOIN hospital_lab_tests t
        ON t.id=i.test_id WHERE i.id=?""", (data["item_id"],)).fetchone()
    if not row or row[0] != TEST_CODE:
        return
    if row[1] in ("approved", "published") or (row[2] or 0) > 0:
        return
    values = data.get("values")
    if not isinstance(values, list):
        raise ValueError("Typhoid ICT needs structured result values")
    for entry in values:
        if not isinstance(entry, dict) or type(entry.get("line_id")) is not int:
            raise ValueError("Invalid Typhoid result line")
        line = conn.execute("""SELECT code,value FROM hospital_lab_lines
            WHERE item_id=? AND id=?""", (data["item_id"],entry["line_id"])).fetchone()
        if not line:
            raise ValueError("Result line not in selected Typhoid ICT order")
        if line[0] not in PARAM_CODES:
            if str(line[1] or "").strip():
                continue  # Legacy historical findings are not reclassified.
            raise ValueError("Unknown blank Typhoid ICT result line")
        if str(line[1] or "").strip():
            continue  # Preserve previously entered free text and revisions.
        value = entry.get("value")
        if value is None or value == "":
            continue
        if not isinstance(value, str) or value not in OPTIONS:
            raise ValueError("Select Positive or Negative for ICT Typhoid")
