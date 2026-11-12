"""Bind Royal Lab original test IDs to actual NOVA lab order items.

Uses NOVA's existing paid-order gate and original item identifiers. Never
replaces print logic, creates clinical approval, or touches pharmacy records.
"""
import sqlite3
from hospital.royallab_native_catalog_api import current_catalog_id
from hospital.royallab_native_catalog_store import test_form
from hospital.royallab_native_result_drafts import save_draft, load_draft

SCHEMA = """
CREATE TABLE IF NOT EXISTS royal_lab_native_order_items (
  nova_item_id INTEGER PRIMARY KEY,
  source_test_id TEXT NOT NULL,
  catalog_id INTEGER NOT NULL,
  linked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(catalog_id) REFERENCES royal_lab_native_catalogs(id)
);
"""

def _existing_order(conn, item_id):
    if type(item_id) is not int or item_id <= 0:
        raise ValueError("NOVA order item ID required")
    row = conn.execute(
        """SELECT i.id, i.result_status, o.status
           FROM hospital_order_items i
           JOIN hospital_orders o ON o.id=i.order_id
           WHERE i.id=?""", (item_id,)).fetchone()
    if row is None:
        raise ValueError("NOVA lab order item not found")
    return row

def _actor(actor):
    if not isinstance(actor, dict) or type(actor.get("id")) is not int or actor["id"] <= 0:
        raise PermissionError("Authenticated NOVA lab user required")
    if actor.get("role") not in ("admin", "lab"):
        raise PermissionError("Only lab staff or administrators may enter results")

def attach_native_test(conn, actor, nova_item_id, source_test_id):
    """Attach the original test to a real NOVA item, never a name-based guess."""
    _actor(actor)
    if not isinstance(conn, sqlite3.Connection):
        raise TypeError("SQLite connection required")
    item = _existing_order(conn, nova_item_id)
    if item[1] == "approved":
        raise PermissionError("Approved NOVA item cannot be rebound")
    catalog_id = current_catalog_id(conn)
    source_test_id = str(source_test_id)
    conn.execute(SCHEMA)
    row = conn.execute("SELECT source_test_id FROM royal_lab_native_order_items WHERE nova_item_id=?",
                       (nova_item_id,)).fetchone()
    if row and row[0] != source_test_id:
        raise ValueError("NOVA order item already linked to another Royal Lab test")
    form = test_form(conn, catalog_id, source_test_id)
    # Do not attach a clinically blocked source test to a real patient order.
    if form.get("review_flags"):
        raise ValueError("Source test requires review before attaching to NOVA order")
    fields = form.get("fields")
    if not isinstance(fields, list) or not fields:
        raise ValueError("Source test has no usable result fields")
    if any(not isinstance(field, dict)
           or not str(field.get("label") or "").strip()
           or field.get("active") in (False, 0, "False", "false", "0")
           or field.get("kind") not in ("text", "number", "select", "select_or_text", "select_or_number")
           for field in fields):
        raise ValueError("Source test has invalid or inactive result fields")
    with conn:
        conn.execute("""INSERT OR IGNORE INTO royal_lab_native_order_items
                        (nova_item_id, source_test_id, catalog_id) VALUES (?,?,?)""",
                     (nova_item_id, source_test_id, catalog_id))
    return {"nova_item_id": nova_item_id, "source_test_id": source_test_id,
            "catalog_id": catalog_id, "linked": True}

def save_order_item_draft(conn, actor, nova_item_id, values):
    """Save values for a paid existing NOVA item; does not publish or print."""
    _actor(actor)
    item = _existing_order(conn, nova_item_id)
    if item[2] not in ("paid", "completed"):
        raise PermissionError("Order must be paid before result entry")
    if item[1] == "approved":
        raise PermissionError("Approved result is immutable")
    conn.execute(SCHEMA)
    link = conn.execute("SELECT source_test_id FROM royal_lab_native_order_items WHERE nova_item_id=?",
                        (nova_item_id,)).fetchone()
    if not link:
        raise ValueError("NOVA order item has no Royal Lab test binding")
    result = save_draft(conn, "NOVA-ITEM-" + str(nova_item_id), link[0], values)
    result["nova_item_id"] = nova_item_id
    return result

def load_order_item_draft(conn, actor, nova_item_id):
    _actor(actor)
    _existing_order(conn, nova_item_id)
    conn.execute(SCHEMA)
    link = conn.execute("SELECT source_test_id FROM royal_lab_native_order_items WHERE nova_item_id=?",
                        (nova_item_id,)).fetchone()
    if not link:
        return None
    return load_draft(conn, "NOVA-ITEM-" + str(nova_item_id), link[0])
