"""Direct NOVA table replacement tests, using synthetic Royal Lab forms."""
import sqlite3
import unittest
from unittest.mock import patch
from hospital.royallab_existing_catalog_replacement import replacement_plan,replace_catalog

def synthetic_catalog():
    return {"tests":[{"source_test_id":str(i),"name":"Royal Test "+str(i),
             "source_department_id":{7:"2",21:"3",36:"8",40:"10",77:"54",120:"12",287:"35"}.get(i,"1"),
             "review_flags":[],"fields":[{"source_format_id":str(i+1),
             "label":"Result","kind":"select","unit":"",
             "options":[{"id":"P","label":"Positive","active":True}],
             "numeric_ranges":[],"text_ranges":[]}]} for i in range(367)]}

class ReplacementTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,code TEXT UNIQUE,name TEXT,category TEXT NOT NULL DEFAULT 'Other',active INTEGER DEFAULT 1)")
        self.db.execute("CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,name TEXT,unit TEXT,active INTEGER DEFAULT 1)")
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
    def test_source_department_populates_nova_picker_and_preserves_manual_override(self):
        replace_catalog(self.db,{},approved=True)
        expected = {"ROYAL-7":"التحاليل العامة والطفيليات",
                    "ROYAL-21":"أمراض الدم والتخثر",
                    "ROYAL-36":"الهرمونات",
                    "ROYAL-40":"المناعة",
                    "ROYAL-77":"المزارع والأحياء الدقيقة",
                    "ROYAL-120":"خدمات غير معملية",
                    "ROYAL-287":"الأحياء الدقيقة والسيرولوجيا"}
        for code,category in expected.items():
            self.assertEqual(self.db.execute(
                "SELECT category FROM hospital_lab_tests WHERE code=?",(code,)).fetchone()[0], category)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM hospital_lab_tests WHERE code LIKE 'ROYAL-%' AND category='Other'"
        ).fetchone()[0],0)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM royal_lab_nova_department_metadata").fetchone()[0],367)
        evidence=self.db.execute("""SELECT source_department_id,original_department_name
                   FROM royal_lab_nova_department_metadata
                   WHERE source_test_id='21'""").fetchone()
        self.assertEqual(evidence,("3","1 h.pp"))
        self.db.execute("UPDATE hospital_lab_tests SET category='تصنيف محلي مراجع' WHERE code='ROYAL-21'")
        replace_catalog(self.db,{},approved=True)
        self.assertEqual(self.db.execute(
            "SELECT category FROM hospital_lab_tests WHERE code='ROYAL-21'").fetchone()[0],
            "تصنيف محلي مراجع")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM royal_lab_nova_department_metadata").fetchone()[0],367)

    def test_missing_original_department_in_mixed_real_source_is_rejected_safely(self):
        catalog=synthetic_catalog()
        catalog["tests"][42].pop("source_department_id")
        with patch("hospital.royallab_existing_catalog_replacement.native_catalog",
                   return_value=catalog):
            with self.assertRaisesRegex(ValueError,"Unknown Royal Lab source group"):
                replace_catalog(self.db,{},approved=True)
        self.assertEqual(self.db.execute(
            "SELECT active FROM hospital_lab_tests WHERE code='OLD'").fetchone()[0],1)

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
    def test_imported_parameters_are_active_for_existing_nova_resolver(self):
        replace_catalog(self.db,{},approved=True)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM hospital_lab_parameters WHERE code LIKE 'ROYAL_FMT_%' AND active=1").fetchone()[0],367)
        self.db.execute("UPDATE hospital_lab_parameters SET active=0 WHERE code='ROYAL_FMT_1'")
        replace_catalog(self.db,{},approved=True)
        self.assertEqual(self.db.execute("SELECT active FROM hospital_lab_parameters WHERE code='ROYAL_FMT_1'").fetchone()[0],1)
    def test_explicitly_inactive_source_field_stays_inactive_with_metadata(self):
        catalog=synthetic_catalog()
        catalog["tests"][0]["fields"][0]["active"]=False
        with patch("hospital.royallab_existing_catalog_replacement.native_catalog",
                   return_value=catalog):
            replace_catalog(self.db,{},approved=True)
            replace_catalog(self.db,{},approved=True)
        row=self.db.execute("""SELECT p.active,m.source_format_id
          FROM hospital_lab_parameters p
          JOIN royal_lab_nova_parameter_metadata m ON m.nova_parameter_id=p.id
          WHERE p.code='ROYAL_FMT_1'""").fetchone()
        self.assertEqual(row,(0,"1"))
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM hospital_lab_parameters WHERE code LIKE 'ROYAL_FMT_%' AND active=1"
        ).fetchone()[0],366)

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
