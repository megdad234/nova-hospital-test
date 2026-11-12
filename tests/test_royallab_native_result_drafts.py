"""Synthetic regression for native Royal Lab result drafts."""
import sqlite3
import unittest
from hospital.royallab_native_result_drafts import save_draft, load_draft

class DraftTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE royal_lab_native_catalogs (id INTEGER PRIMARY KEY)")
        self.db.execute("INSERT INTO royal_lab_native_catalogs(id) VALUES (1)")
        self.db.execute("""CREATE TABLE royal_lab_native_tests (
            catalog_id INTEGER, source_test_id TEXT, name TEXT, form_json TEXT,
            PRIMARY KEY(catalog_id, source_test_id))""")
        self.db.execute("""INSERT INTO royal_lab_native_tests VALUES
          (1, 'TEST-1', 'Synthetic Test', '{"source_test_id":"TEST-1","fields":[{"source_format_id":"F1","kind":"select","options":[{"id":"A","active":true},{"id":"B","active":true}]}]}')""")

    def tearDown(self):
        self.db.close()

    def test_save_reopen_update(self):
        first = save_draft(self.db, "ORDER-1", "TEST-1", {"F1": "A"})
        self.assertEqual(first["status"], "draft")
        self.assertEqual(load_draft(self.db, "ORDER-1", "TEST-1")["values"], {"F1": "A"})
        save_draft(self.db, "ORDER-1", "TEST-1", {"F1": "B"})
        self.assertEqual(load_draft(self.db, "ORDER-1", "TEST-1")["values"], {"F1": "B"})
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM royal_lab_native_result_drafts").fetchone()[0], 1)

    def test_reject_invalid_dropdown_without_overwrite(self):
        save_draft(self.db, "ORDER-1", "TEST-1", {"F1": "A"})
        with self.assertRaises(ValueError):
            save_draft(self.db, "ORDER-1", "TEST-1", {"F1": "INVALID"})
        self.assertEqual(load_draft(self.db, "ORDER-1", "TEST-1")["values"], {"F1": "A"})

    def test_numeric_source_format_id_is_accepted(self):
        self.db.execute("""INSERT INTO royal_lab_native_tests VALUES
          (1, 'TEST-2', 'Numeric ID', '{"source_test_id":"TEST-2","fields":[{"source_format_id":12,"kind":"select","options":[{"id":9,"active":true}]}]}')""")
        result=save_draft(self.db,"ORDER-1","TEST-2",{"12":"9"})
        self.assertEqual(result["values"],{"12":"9"})
        self.assertEqual(load_draft(self.db,"ORDER-1","TEST-2")["values"],{"12":"9"})

    def test_separate_orders_and_missing_draft(self):
        self.assertIsNone(load_draft(self.db, "ORDER-2", "TEST-1"))
        save_draft(self.db, "ORDER-1", "TEST-1", {"F1": "A"})
        self.assertIsNone(load_draft(self.db, "ORDER-2", "TEST-1"))

if __name__ == "__main__":
    unittest.main()
