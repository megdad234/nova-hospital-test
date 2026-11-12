"""Isolated paid-order tests; no real patient data or printing."""
import sqlite3
import unittest
from hospital.royallab_native_order_bridge import (
    attach_native_test, save_order_item_draft, load_order_item_draft)

ADMIN = {"id": 1, "role": "lab"}
class OrderBridgeTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE hospital_orders(id INTEGER PRIMARY KEY,status TEXT)")
        self.db.execute("CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,order_id INTEGER,result_status TEXT)")
        self.db.execute("INSERT INTO hospital_orders VALUES(1,'pending'),(2,'paid')")
        self.db.execute("INSERT INTO hospital_order_items VALUES(11,1,'draft'),(22,2,'draft'),(23,2,'approved')")
        self.db.execute("CREATE TABLE royal_lab_native_catalogs(id INTEGER PRIMARY KEY)")
        self.db.execute("INSERT INTO royal_lab_native_catalogs VALUES(1)")
        self.db.execute("""CREATE TABLE royal_lab_native_tests(
           catalog_id INTEGER, source_test_id TEXT, name TEXT, form_json TEXT,
           PRIMARY KEY(catalog_id,source_test_id))""")
        self.db.execute("""INSERT INTO royal_lab_native_tests VALUES
           (1,'T1','Test','{"source_test_id":"T1","fields":[{"source_format_id":"1",
           "label":"Synthetic result","kind":"select","options":[{"id":"A","label":"A","active":true}]}]}')""")
    def tearDown(self):
        self.db.close()
    def test_attach_and_save_paid_draft(self):
        attach_native_test(self.db,ADMIN,22,"T1")
        result=save_order_item_draft(self.db,ADMIN,22,{"1":"A"})
        self.assertEqual(result["nova_item_id"],22)
        self.assertEqual(load_order_item_draft(self.db,ADMIN,22)["values"],{"1":"A"})
    def test_unpaid_and_approved_are_blocked(self):
        attach_native_test(self.db,ADMIN,11,"T1")
        with self.assertRaises(PermissionError):
            attach_native_test(self.db,ADMIN,23,"T1")
        with self.assertRaises(PermissionError):
            save_order_item_draft(self.db,ADMIN,11,{"1":"A"})
        with self.assertRaises(PermissionError):
            save_order_item_draft(self.db,ADMIN,23,{"1":"A"})
    def test_unreviewed_source_cannot_be_attached_to_patient(self):
        self.db.execute("""UPDATE royal_lab_native_tests
           SET form_json=? WHERE source_test_id='T1'""",
           ('{"source_test_id":"T1","review_flags":["no_source_analytes"],'
            '"fields":[{"source_format_id":"1","label":"Synthetic result",'
            '"kind":"select","options":[{"id":"A","label":"A","active":true}]}]}',))
        with self.assertRaisesRegex(ValueError, "requires clinical review"):
            attach_native_test(self.db, ADMIN, 22, "T1")
        self.db.execute("""CREATE TABLE IF NOT EXISTS royal_lab_native_order_items
           (nova_item_id INTEGER PRIMARY KEY, source_test_id TEXT, catalog_id INTEGER)""")
        self.assertIsNone(self.db.execute(
            "SELECT source_test_id FROM royal_lab_native_order_items WHERE nova_item_id=22").fetchone())

    def test_rebinding_and_unauthorized_access_blocked(self):
        attach_native_test(self.db,ADMIN,22,"T1")
        with self.assertRaises(ValueError):
            attach_native_test(self.db,ADMIN,22,"DIFFERENT")
        with self.assertRaises(PermissionError):
            save_order_item_draft(self.db,{"id":2,"role":"reception"},22,{"1":"A"})
        with self.assertRaises(ValueError):
            attach_native_test(self.db,ADMIN,999,"T1")

if __name__=="__main__":
    unittest.main()
