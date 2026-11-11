"""Isolated Royal Lab catalog staging schema; never alters NOVA's live tables.
Imported only by explicit migration runner after preflight and database backup.
"""
import sqlite3, json, pathlib

DDL="""
CREATE TABLE IF NOT EXISTS royal_lab_import_batches(
 id INTEGER PRIMARY KEY, source_sha256 TEXT NOT NULL UNIQUE,
 imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 source_test_count INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'staged'
);
CREATE TABLE IF NOT EXISTS royal_lab_source_tests(
 batch_id INTEGER NOT NULL REFERENCES royal_lab_import_batches(id),
 source_test_id TEXT NOT NULL, payload_json TEXT NOT NULL,
 PRIMARY KEY(batch_id,source_test_id)
);
CREATE TABLE IF NOT EXISTS royal_lab_source_analytes(
 batch_id INTEGER NOT NULL REFERENCES royal_lab_import_batches(id),
 source_analyte_id TEXT NOT NULL, source_test_id TEXT,
 payload_json TEXT NOT NULL,
 PRIMARY KEY(batch_id,source_analyte_id)
);
CREATE TABLE IF NOT EXISTS royal_lab_unresolved_options(
 batch_id INTEGER NOT NULL REFERENCES royal_lab_import_batches(id),
 source_option_id TEXT NOT NULL, reason TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 PRIMARY KEY(batch_id,source_option_id)
);
"""
def stage(conn, library, unlinked, sha256):
    """Atomic and idempotent staging; no modifications to existing NOVA tables."""
    if not isinstance(library,dict) or not isinstance(library.get("tests"),list) or not isinstance(library.get("analytes"),list):
        raise ValueError("Invalid Royal Lab library")
    tests=library["tests"];analytes=library["analytes"]
    if len(tests)!=367 or len(analytes)!=1245:
        raise ValueError("Unexpected Royal Lab catalog cardinality")
    if len(unlinked)!=2551:raise ValueError("Unexpected unresolved option count")
    test_ids=[str(t["TestID"]) for t in tests]
    analyte_ids=[str(a["analyte_id"]) for a in analytes]
    option_ids=[str(o["ColoseEndedResultOptionID"]) for o in unlinked]
    if len(set(test_ids))!=len(test_ids) or len(set(analyte_ids))!=len(analyte_ids) or len(set(option_ids))!=len(option_ids):
        raise ValueError("Duplicate source identifiers")
    with conn:
        conn.executescript(DDL)
        old=conn.execute("SELECT id FROM royal_lab_import_batches WHERE source_sha256=?",(sha256,)).fetchone()
        if old:return old[0]
        cur=conn.execute("INSERT INTO royal_lab_import_batches(source_sha256,source_test_count) VALUES(?,?)",(sha256,len(tests)))
        batch=cur.lastrowid
        conn.executemany("INSERT INTO royal_lab_source_tests VALUES(?,?,?)",((batch,str(t["TestID"]),json.dumps(t,ensure_ascii=False)) for t in tests))
        conn.executemany("INSERT INTO royal_lab_source_analytes VALUES(?,?,?,?)",((batch,str(a["analyte_id"]),str(a.get("test_id","")),json.dumps(a,ensure_ascii=False)) for a in analytes))
        conn.executemany("INSERT INTO royal_lab_unresolved_options VALUES(?,?,?,?)",((batch,str(o["ColoseEndedResultOptionID"]),o["reason"],json.dumps(o,ensure_ascii=False)) for o in unlinked))
        return batch

def verify(conn,batch):
    return {table:conn.execute("SELECT count(*) FROM "+table+" WHERE batch_id=?",(batch,)).fetchone()[0] for table in ("royal_lab_source_tests","royal_lab_source_analytes","royal_lab_unresolved_options")}
