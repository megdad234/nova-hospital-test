"""Install Royal Lab-native catalogue into isolated tables without old NOVA test matching.

All 367 original tests, their fields, option IDs and reference ranges are retained.
Never deletes patient data, overrides pharmacy, or silently authorizes results.
"""
import hashlib,json,pathlib,sqlite3
from hospital.royallab_native_result_form import native_catalog
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
            return old[0]
        cur=conn.execute("INSERT INTO royal_lab_native_catalogs(source_sha256,test_count) VALUES(?,?)",(source_sha256,367))
        cid=cur.lastrowid
        conn.executemany("INSERT INTO royal_lab_native_tests(catalog_id,source_test_id,name,form_json) VALUES(?,?,?,?)",
                         ((cid,t["source_test_id"],t["name"],json.dumps(t,ensure_ascii=False)) for t in tests))
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
    flags = list(raw.get("review_flags") or [])
    if excluded:
        flags = [f for f in flags if f != "inactive_source_field"]
    if all(f.get("kind") in ("text", "number", "select", "select_or_text", "select_or_number")
           for f in active):
        flags = [f for f in flags if f != "mixed_format_requires_combobox"]
    if all(str(f.get("label") or "").strip() for f in active):
        flags = [f for f in flags if f != "missing_source_field_label"]
    def valid_source_format(f):
        types = f.get("types") or []
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
            "excluded_inactive_source_fields": excluded}

def clinical_test_form(conn, catalog_id, source_test_id):
    """Return the safely editable subset without changing stored source data."""
    return effective_source_form(test_form(conn, catalog_id, source_test_id))
