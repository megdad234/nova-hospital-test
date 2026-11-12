"""Royal Lab native replacement catalogue checks using isolated synthetic data."""
import sqlite3
import json
import unittest
from hospital.royallab_replacement_readiness import verify_replacement_catalog

class ReplacementReadinessTests(unittest.TestCase):
    def test_full_catalog_passes_and_no_legacy_matching(self):
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE royal_lab_native_catalogs (id INTEGER PRIMARY KEY)")
            db.execute("INSERT INTO royal_lab_native_catalogs VALUES (1)")
            db.execute("""CREATE TABLE royal_lab_native_tests (
              catalog_id INTEGER, source_test_id TEXT, name TEXT, form_json TEXT,
              PRIMARY KEY(catalog_id,source_test_id))""")
            fields=[{"source_format_id":str(i),"label":"Field","kind":"select",
                     "options":[{"id":"1","label":"Positive","active":True}]} for i in range(3)]
            db.executemany("INSERT INTO royal_lab_native_tests VALUES(1,?,?,?)",
                [(str(i),"Test "+str(i),json.dumps({"source_test_id":str(i),
                  "name":"Test "+str(i),"fields":fields})) for i in range(367)])
            report=verify_replacement_catalog(db)
            self.assertEqual(report["tests"],367)
            self.assertEqual(report["fields"],1101)
            self.assertFalse(report["legacy_nova_name_matching"])
            db.execute("DELETE FROM royal_lab_native_tests WHERE source_test_id='0'")
            with self.assertRaises(RuntimeError):
                verify_replacement_catalog(db)

if __name__=="__main__":
    unittest.main()
