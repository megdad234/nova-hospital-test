"""Royal Lab native result drafts; source IDs only, no old NOVA catalogue matching.

Isolated persistence for the replacement catalogue. Does not approve or publish
clinical results, and does not modify patient, pharmacy or finance tables.
"""
import json
import sqlite3
from hospital.royallab_native_catalog_api import current_catalog_id
from hospital.royallab_native_catalog_store import test_form
from hospital.royallab_native_result_form import validate_result_values

SCHEMA = """
CREATE TABLE IF NOT EXISTS royal_lab_native_result_drafts (
 order_key TEXT NOT NULL,
 source_test_id TEXT NOT NULL,
 catalog_id INTEGER NOT NULL,
 values_json TEXT NOT NULL,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY (order_key, source_test_id),
 FOREIGN KEY (catalog_id) REFERENCES royal_lab_native_catalogs(id)
);
"""

def _key(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError("A nonempty order key up to 128 characters is required")
    return value.strip()

def save_draft(conn, order_key, source_test_id, values):
    """Save validated values atomically; caller must authorize the order first."""
    if not isinstance(conn, sqlite3.Connection):
        raise TypeError("SQLite connection required")
    order_key = _key(order_key)
    source_test_id = str(source_test_id)
    catalog_id = current_catalog_id(conn)
    form = test_form(conn, catalog_id, source_test_id)
    validated = validate_result_values(form, values)
    conn.execute(SCHEMA)
    with conn:
        conn.execute(
            """INSERT INTO royal_lab_native_result_drafts
               (order_key, source_test_id, catalog_id, values_json)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(order_key, source_test_id) DO UPDATE SET
                 catalog_id=excluded.catalog_id,
                 values_json=excluded.values_json,
                 updated_at=CURRENT_TIMESTAMP""",
            (order_key, source_test_id, catalog_id,
             json.dumps(validated, ensure_ascii=False, sort_keys=True)),
        )
    return {"order_key": order_key, "source_test_id": source_test_id,
            "catalog_id": catalog_id, "values": validated, "status": "draft"}

def load_draft(conn, order_key, source_test_id):
    """Read only a saved draft; caller must authorize access to the order."""
    order_key = _key(order_key)
    source_test_id = str(source_test_id)
    conn.execute(SCHEMA)
    row = conn.execute(
        """SELECT catalog_id, values_json, updated_at
           FROM royal_lab_native_result_drafts
           WHERE order_key=? AND source_test_id=?""",
        (order_key, source_test_id),
    ).fetchone()
    if row is None:
        return None
    return {"order_key": order_key, "source_test_id": source_test_id,
            "catalog_id": row[0], "values": json.loads(row[1]),
            "updated_at": row[2], "status": "draft"}
