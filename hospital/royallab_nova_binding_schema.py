"""Explicit Royal Lab review bindings: schema only, never automatic approval.

The migration deliberately creates no reviewed rows. Approval must come from a
separate authorized clinical workflow after checking each source form.
"""
DDL="""
CREATE TABLE IF NOT EXISTS royal_lab_approved_item_bindings(
 item_id INTEGER NOT NULL,
 batch_id INTEGER NOT NULL,
 nova_test_id INTEGER NOT NULL,
 source_test_id TEXT NOT NULL,
 reviewed INTEGER NOT NULL DEFAULT 0 CHECK(reviewed IN (0,1)),
 clinical_approved INTEGER NOT NULL DEFAULT 0 CHECK(clinical_approved IN (0,1)),
 reviewed_by INTEGER,
 reviewed_at TEXT,
 PRIMARY KEY(item_id,batch_id),
 FOREIGN KEY(item_id) REFERENCES hospital_order_items(id),
 FOREIGN KEY(batch_id) REFERENCES royal_lab_import_batches(id),
 FOREIGN KEY(nova_test_id) REFERENCES hospital_lab_tests(id),
 CHECK(reviewed=0 OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)),
 CHECK(clinical_approved=0 OR (reviewed=1 AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_royal_lab_bindings_batch
 ON royal_lab_approved_item_bindings(batch_id,reviewed);
"""
def create_schema(conn):
    required={'hospital_order_items','hospital_lab_tests','royal_lab_import_batches'}
    tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not required.issubset(tables):raise ValueError("NOVA lab and Royal Lab staging tables required")
    conn.executescript(DDL)
