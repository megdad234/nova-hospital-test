"""Direct NOVA table replacement tests, using synthetic Royal Lab forms."""
import sqlite3
import unittest
from unittest.mock import patch
from hospital.royallab_existing_catalog_replacement import replacement_plan,replace_catalog

def synthetic_catalog():
    return {"tests":[{"source_test_id":str(i),"name":"Royal Test "+str(i),
             "review_flags":[],"fields":[{"source_format_id":str(i+1),
             "label":"Result","kind":"select","unit":"",
             "options":[{"id":"P","label":"Positive","active":True}],
             "numeric_ranges":[],"text_ranges":[]}]} for i in range(367)]}

class ReplacementTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,code TEXT UNIQUE,name TEXT,active INTEGER DEFAULT 1)")
        self.db.execute("CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,name TEXT,unit TEXT)")
        self.db.execute("INSERT INTO hospital_lab_tests(code,name) VALUES('OLD','Old test')")
        self.db.execute("INSERT INTO hospital_lab_parameters(test_id,code,name,unit) VALUES(1,'OLD-P','Old parameter','')")
        self.patcher=patch("hospital.royallab_existing_catalog_replacement.native_catalog",
                           return_value=synthetic_catalog())
        self.patcher.start()
    def tearDown(self):
        self.patcher.stop()
        self.db.close()
    def test_explicit_approval_and_idempotent_replacement(self):
        with self.assertRaises(PermissionError):
            replace_catalog(self.db,{},approved=False)
        result=replace_catalog(self.db,{},approved=True)
        self.assertEqual(result["active_royal_lab_tests"],367)
        self.assertEqual(self.db.execute("SELECT active FROM hospital_lab_tests WHERE code='OLD'").fetchone()[0],0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM royal_lab_nova_parameter_metadata").fetchone()[0],367)
        self.assertEqual(self.db.execute("SELECT options_json FROM royal_lab_nova_parameter_metadata LIMIT 1").fetchone()[0].count("Positive"),1)
        replace_catalog(self.db,{},approved=True)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM hospital_lab_tests").fetchone()[0],368)
    def test_unresolved_format_never_hides_existing_catalogue(self):
        catalog=synthetic_catalog()
        catalog["tests"][0]["fields"][0]["source_format_id"]=None
        with patch("hospital.royallab_existing_catalog_replacement.native_catalog",
                   return_value=catalog):
            with self.assertRaises(RuntimeError):
                replace_catalog(self.db,{},approved=True)
        self.assertEqual(self.db.execute("SELECT active FROM hospital_lab_tests WHERE code='OLD'").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM hospital_lab_tests").fetchone()[0],1)
    def test_unexpected_royal_prefix_is_not_modified(self):
        self.db.execute("INSERT INTO hospital_lab_tests(code,name) VALUES('ROYAL-UNKNOWN','Other')")
        with self.assertRaises(RuntimeError):
            replace_catalog(self.db,{},approved=True)
        self.assertEqual(self.db.execute("SELECT active FROM hospital_lab_tests WHERE code='OLD'").fetchone()[0],1)
    def test_imported_format_codes_match_nova_line_resolver(self):
        replace_catalog(self.db,{},approved=True)
        self.assertEqual(self.db.execute("SELECT code FROM hospital_lab_parameters WHERE test_id=(SELECT id FROM hospital_lab_tests WHERE code='ROYAL-0')").fetchone()[0],"ROYAL_FMT_1")
    def test_atomic_rollback_on_parameter_insert_failure(self):
        self.db.execute("""CREATE TRIGGER reject_royal_parameter BEFORE INSERT ON hospital_lab_parameters
            WHEN NEW.code LIKE 'ROYAL_FMT_%'
            BEGIN SELECT RAISE(ABORT,'synthetic insert failure'); END""")
        with self.assertRaises(sqlite3.DatabaseError):
            replace_catalog(self.db,{},approved=True)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM hospital_lab_tests").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT active FROM hospital_lab_tests WHERE code='OLD'").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='royal_lab_nova_parameter_metadata'").fetchone()[0],0)
    def test_import_preserves_existing_parameter_identity(self):
        replace_catalog(self.db,{},approved=True)
        first=self.db.execute("SELECT id FROM hospital_lab_parameters WHERE code='ROYAL_FMT_1'").fetchone()[0]
        replace_catalog(self.db,{},approved=True)
        second=self.db.execute("SELECT id FROM hospital_lab_parameters WHERE code='ROYAL_FMT_1'").fetchone()[0]
        self.assertEqual(first,second)
    def test_missing_active_column_blocks_without_writes(self):
        self.db.execute("ALTER TABLE hospital_lab_tests RENAME TO old_tests")
        self.db.execute("CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,code TEXT,name TEXT)")
        before=self.db.total_changes
        with self.assertRaises(RuntimeError):
            replacement_plan(self.db,{})
        self.assertEqual(self.db.total_changes,before)

if __name__=="__main__":
    unittest.main()
