"""Install Royal Lab-native catalogue into isolated tables without old NOVA test matching.

All 367 original tests, their fields, option IDs and reference ranges are retained.
Never deletes patient data, overrides pharmacy, or silently authorizes results.
"""
import hashlib,json,pathlib,sqlite3
from hospital.royallab_native_result_form import native_catalog

# v2 restores verified Double/Integer source subtypes; prior draft values stay intact.
FORM_GENERATOR_VERSION = 2
DDL="""
CREATE TABLE IF NOT EXISTS royal_lab_native_catalogs(
 id INTEGER PRIMARY KEY, source_sha256 TEXT NOT NULL UNIQUE,
 imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, test_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS royal_lab_native_tests(
 catalog_id INTEGER NOT NULL, source_test_id TEXT NOT NULL,
 name TEXT NOT NULL, form_json TEXT NOT NULL,
 PRIMARY KEY(catalog_id,source_test_id),
 FOREIGN KEY(catalog_id) REFERENCES royal_lab_native_catalogs(id)
);
CREATE INDEX IF NOT EXISTS idx_royal_lab_native_tests_name ON royal_lab_native_tests(name);
CREATE TABLE IF NOT EXISTS royal_lab_native_catalog_generators(
 catalog_id INTEGER PRIMARY KEY, generator_version INTEGER NOT NULL,
 FOREIGN KEY(catalog_id) REFERENCES royal_lab_native_catalogs(id)
);
CREATE TABLE IF NOT EXISTS royal_lab_native_catalog_form_backups(
 catalog_id INTEGER NOT NULL, source_test_id TEXT NOT NULL,
 generator_version INTEGER NOT NULL, form_json TEXT NOT NULL,
 archived_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(catalog_id,source_test_id,generator_version)
);
"""
def install(conn,library,source_sha256):
    if not isinstance(conn,sqlite3.Connection):raise ValueError("SQLite connection required")
    if not isinstance(source_sha256,str) or len(source_sha256)!=64 or any(c not in '0123456789abcdef' for c in source_sha256):
        raise ValueError("Valid source SHA256 required")
    catalog=native_catalog(library)
    tests=catalog["tests"]
    ids=[t["source_test_id"] for t in tests]
    if len(tests)!=367 or len(set(ids))!=367:raise ValueError("Royal Lab native test IDs incomplete or duplicate")
    conn.executescript(DDL)
    with conn:
        old=conn.execute("SELECT id FROM royal_lab_native_catalogs WHERE source_sha256=?",(source_sha256,)).fetchone()
        if old:
            count=conn.execute("SELECT COUNT(*) FROM royal_lab_native_tests WHERE catalog_id=?",(old[0],)).fetchone()[0]
            if count!=367:raise ValueError("Existing Royal Lab catalog is incomplete")
            cid=old[0]
            stored_ids={str(row[0]) for row in conn.execute(
                "SELECT source_test_id FROM royal_lab_native_tests WHERE catalog_id=?",(cid,))}
            if stored_ids!=set(ids):
                raise ValueError("Existing source test IDs differ; refusing unsafe overwrite")
            version_row=conn.execute(
                "SELECT generator_version FROM royal_lab_native_catalog_generators WHERE catalog_id=?",
                (cid,)).fetchone()
            old_version=version_row[0] if version_row else 1
            if old_version>FORM_GENERATOR_VERSION:
                raise ValueError("Installed clinical form generator is newer; downgrade blocked")
            if old_version<FORM_GENERATOR_VERSION:
                # Make a recoverable, durable snapshot of EVERY prior form before
                # regenerating source metadata. Orders, results and catalog IDs
                # are not touched; source format IDs remain stable.
                conn.execute("""INSERT OR IGNORE INTO royal_lab_native_catalog_form_backups
                    (catalog_id,source_test_id,generator_version,form_json)
                    SELECT catalog_id,source_test_id,?,form_json
                    FROM royal_lab_native_tests WHERE catalog_id=?""",(old_version,cid))
                conn.executemany("""UPDATE royal_lab_native_tests SET name=?,form_json=?
                    WHERE catalog_id=? AND source_test_id=?""",
                    ((t["name"],json.dumps(t,ensure_ascii=False),cid,t["source_test_id"])
                     for t in tests))
            conn.execute("""INSERT INTO royal_lab_native_catalog_generators(catalog_id,generator_version)
                VALUES (?,?) ON CONFLICT(catalog_id) DO UPDATE SET
                generator_version=excluded.generator_version""",(cid,FORM_GENERATOR_VERSION))
            return cid
        cur=conn.execute("INSERT INTO royal_lab_native_catalogs(source_sha256,test_count) VALUES(?,?)",(source_sha256,367))
        cid=cur.lastrowid
        conn.executemany("INSERT INTO royal_lab_native_tests(catalog_id,source_test_id,name,form_json) VALUES(?,?,?,?)",
                         ((cid,t["source_test_id"],t["name"],json.dumps(t,ensure_ascii=False)) for t in tests))
        conn.execute("INSERT INTO royal_lab_native_catalog_generators VALUES(?,?)",
                     (cid,FORM_GENERATOR_VERSION))
        return cid

def install_file(conn,path):
    raw=pathlib.Path(path).read_bytes()
    return install(conn,json.loads(raw.decode('utf-8-sig')),hashlib.sha256(raw).hexdigest())

def list_tests(conn,catalog_id):
    return [{"source_test_id":r[0],"name":r[1]} for r in conn.execute(
        "SELECT source_test_id,name FROM royal_lab_native_tests WHERE catalog_id=? ORDER BY name,source_test_id",(catalog_id,))]

def test_form(conn,catalog_id,source_test_id):
    row=conn.execute("SELECT form_json FROM royal_lab_native_tests WHERE catalog_id=? AND source_test_id=?",
                     (catalog_id,str(source_test_id))).fetchone()
    if not row:raise KeyError("Unknown Royal Lab test")
    return json.loads(row[0])

def effective_source_form(raw):
    """Build the safe entry form from unchanged original source metadata.

    Source-deactivated analytes remain stored for audit and historic results,
    but cannot appear as editable values. Other source review problems remain
    blocking. Existing original catalogue and patient records are not changed.
    """
    all_fields = raw.get("fields", [])
    if not isinstance(all_fields, list):
        return raw
    inactive = (False, 0, "False", "false", "0")
    active = [f for f in all_fields if isinstance(f, dict) and f.get("active") not in inactive]
    if not active:
        return raw  # Never make an empty or fully inactive test writable.
    excluded = len(all_fields) - len(active)
    # The original database contains blank dropdown values at order 0, 1, 11
    # and 100. A choice with NO visible label cannot be safely selected or
    # interpreted as a result. Exclude these choices from entry, regardless of
    # sort order, retaining every original row in the archived source form.
    # If no labeled choice remains the field still fails validation.
    blank_placeholders = 0
    cleaned_active = []
    for field in active:
        if not str(field.get("kind") or "").startswith("select"):
            cleaned_active.append(field)
            continue
        choices = []
        for option in field.get("options", []):
            if isinstance(option, dict) and not str(option.get("label") or "").strip():
                blank_placeholders += 1
                continue
            choices.append(option)
        cleaned_active.append({**field, "options": choices})
    active = cleaned_active
    flags = list(raw.get("review_flags") or [])
    if excluded:
        flags = [f for f in flags if f != "inactive_source_field"]
    if all(f.get("kind") in ("text", "number", "select", "select_or_text", "select_or_number")
           for f in active):
        flags = [f for f in flags if f != "mixed_format_requires_combobox"]
    if all(str(f.get("label") or "").strip() for f in active):
        flags = [f for f in flags if f != "missing_source_field_label"]
    # A source analyte with no result-format row may still have a clear name.
    # Support a *manual draft-only text field* for this precise case. This is
    # not a reconstructed numeric type, a normal range or clinical approval.
    # Preserve its synthetic identity so the real analyte can be audited.
    manual_fallback_count = 0
    manual_fields = []
    for f in active:
        types = f.get("types") or []
        fallback_id = "ANALYTE-" + str(f.get("source_analyte_id") or "")
        is_manual = (not types and f.get("kind") == "text"
                     and str(f.get("source_format_id")) == fallback_id
                     and str(f.get("source_analyte_id") or "").strip()
                     and str(f.get("label") or "").strip()
                     and not f.get("options"))
        if is_manual:
            manual_fallback_count += 1
        manual_fields.append({**f, "manual_untyped_draft_only": bool(is_manual)})
    active = manual_fields
    def valid_source_format(f):
        types = f.get("types") or []
        if f.get("manual_untyped_draft_only"):
            return True
        return (bool(types) and not str(f.get("source_format_id") or "").startswith("ANALYTE-")
                and not ("ColoseEndedResultFormat" in types and not f.get("options")))
    if all(valid_source_format(f) for f in active):
        flags = [f for f in flags if f != "source_format_missing_or_incomplete_free_text_fallback"]
    # Re-evaluate dropdown metadata against active source choices only.
    def valid_choices(f):
        if not str(f.get("kind") or "").startswith("select"):
            return True
        options = [o for o in f.get("options", []) if isinstance(o, dict) and o.get("active") not in inactive]
        ids = [str(o.get("id") or "").strip() for o in options]
        return bool(ids) and all(ids) and len(ids) == len(set(ids))
    if all(valid_choices(f) for f in active):
        flags = [f for f in flags if f != "missing_or_duplicate_source_option_ids"]
    if all(not str(f.get("kind") or "").startswith("select") or
           all(str(o.get("label") or "").strip()
               for o in f.get("options", []) if isinstance(o, dict) and o.get("active") not in inactive)
           for f in active):
        flags = [f for f in flags if f != "missing_source_option_label"]
    return {**raw, "fields": active, "review_flags": flags,
            "excluded_inactive_source_fields": excluded,
            "excluded_blank_placeholder_options": blank_placeholders,
            "manual_untyped_draft_fields": manual_fallback_count}

def clinical_test_form(conn, catalog_id, source_test_id):
    """Return the safely editable subset without changing stored source data."""
    return effective_source_form(test_form(conn, catalog_id, source_test_id))

# Department IDs verified against the original dbo.Test / dbo.Laboratory tables.
# Administrative, nursing, radiology, dentistry, operations and physiotherapy
# services must not be counted as missing clinical laboratory result templates.
NON_LAB_DEPARTMENT_IDS = frozenset(("12", "13", "14", "15", "18", "19", "27"))

def is_non_lab_service(form):
    if not isinstance(form, dict):
        return False
    fields = form.get("fields")
    return (isinstance(fields, list) and not fields
            and str(form.get("source_department_id") or "") in NON_LAB_DEPARTMENT_IDS)
