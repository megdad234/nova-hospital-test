"""Photo-approved PT/INR result-entry fields, strictly excluding report printing."""
import json
import sqlite3
import unittest

from hospital.royallab_catalog_audit import SOURCE
from hospital.royallab_native_result_form import native_catalog
from hospital.royallab_nova_ptinr_photo_reconciliation import (
    SOURCE_ID, TEST_CODE, FIELDS, _original, reconcile_in_existing_nova,
    validate_save_payload,
)


def fixture():
    return [{"source_test_id": "22", "name": "PT/INR", "fields": [
        {"source_format_id":"701","source_analyte_id":"424","label":"PT",
         "unit":"sec","kind":"number","active":True},
        {"source_format_id":"288","source_analyte_id":"108","label":"INR",
         "unit":"","kind":"text","active":True},
        {"source_format_id":"2319","source_analyte_id":"424","label":"PT Control",
         "unit":"sec","kind":"number","active":True},
        {"source_format_id":"286","source_analyte_id":"106","label":"PT",
         "unit":"sec","kind":"number","active":False},
    ]}]


class PhotoPTINRTests(unittest.TestCase):
    def setUp(self):
        self.c=sqlite3.connect(":memory:")
        self.c.row_factory=sqlite3.Row
        self.c.executescript("""
          CREATE TABLE hospital_lab_tests(
            id INTEGER PRIMARY KEY,code TEXT UNIQUE,name TEXT,price INTEGER);
          CREATE TABLE hospital_lab_parameters(
            id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,name TEXT,unit TEXT,
            active INTEGER,reference_all TEXT DEFAULT '',
            reference_male TEXT DEFAULT '',reference_female TEXT DEFAULT '',
            sort_order INTEGER DEFAULT 0);
          CREATE TABLE royal_lab_nova_parameter_metadata(
            nova_parameter_id INTEGER PRIMARY KEY,source_test_id TEXT,
            source_format_id TEXT,kind TEXT,options_json TEXT);
          CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,
            test_id INTEGER,result_status TEXT DEFAULT 'pending',
            result_version INTEGER DEFAULT 0);
          CREATE TABLE hospital_lab_lines(id INTEGER PRIMARY KEY,
            item_id INTEGER,code TEXT,value TEXT,reference_range TEXT);
          INSERT INTO hospital_lab_tests VALUES (22,'ROYAL-22','PT/INR',4321);
          INSERT INTO hospital_lab_tests VALUES (23,'ROYAL-23','Another assay',100);
          INSERT INTO hospital_lab_parameters VALUES
            (11,22,'ROYAL_FMT_288','INR','',1,'','','',0),
            (12,22,'ROYAL_FMT_701','PT','sec',1,'','','',0),
            (13,22,'ROYAL_FMT_2319','PT Control','sec',1,'','','',0),
            (14,22,'ROYAL_FMT_286','PT','sec',0,'','','',0),
            (15,23,'OTHER','other','',1,'99','','',0);
          INSERT INTO royal_lab_nova_parameter_metadata VALUES
            (11,'22','288','text','[]'),
            (12,'22','701','number','[]'),
            (13,'22','2319','number','[]');
          INSERT INTO hospital_order_items VALUES(100,22,'approved',5);
          INSERT INTO hospital_order_items VALUES(101,22,'pending',0);
          INSERT INTO hospital_order_items VALUES(102,23,'pending',0);
          INSERT INTO hospital_lab_lines VALUES(1,100,'ROYAL_FMT_701','17.2','Old reference');
          INSERT INTO hospital_lab_lines VALUES(2,100,'ROYAL_FMT_288','1.34','Old reference');
          INSERT INTO hospital_lab_lines VALUES(3,101,'ROYAL_FMT_701','','');
          INSERT INTO hospital_lab_lines VALUES(4,101,'ROYAL_FMT_288','','');
          INSERT INTO hospital_lab_lines VALUES(5,101,'ROYAL_FMT_2319','','');
          INSERT INTO hospital_lab_lines VALUES(6,102,'OTHER','free text','99');
        """)
        self.schema = {r[1] for r in self.c.execute(
            "PRAGMA table_info(hospital_lab_parameters)")}

    def tearDown(self):
        self.c.close()

    def test_recovered_source_proves_exact_two_fields_and_control(self):
        source=native_catalog(json.loads(SOURCE.read_text(encoding="utf-8-sig")))
        original=_original(source["tests"])
        self.assertEqual(original["701"]["source_analyte_id"],"424")
        self.assertEqual(original["288"]["source_analyte_id"],"108")
        self.assertEqual(original["701"]["kind"],"number")
        self.assertEqual(original["288"]["kind"],"text")
        self.assertEqual(original["2319"]["label"],"PT Control")
        self.assertEqual((FIELDS[0][4],FIELDS[1][4]),("10 - 15","Up to 1.0"))

    def test_exactly_two_reportable_parameters_with_user_photo_references(self):
        before=[tuple(r) for r in self.c.execute(
            "SELECT * FROM hospital_lab_lines ORDER BY id")]
        n=reconcile_in_existing_nova(self.c,fixture(),self.schema)
        self.assertEqual(n,2)
        self.assertEqual([tuple(r) for r in self.c.execute(
            """SELECT code,name,unit,reference_all,sort_order
               FROM hospital_lab_parameters WHERE test_id=22 AND active=1
               ORDER BY sort_order,id""")],[
                ("ROYAL_FMT_701","PT","sec","10 - 15",1),
                ("ROYAL_FMT_288","INR","","Up to 1.0",2),
               ])
        self.assertEqual(self.c.execute("""SELECT active FROM hospital_lab_parameters
            WHERE code='ROYAL_FMT_2319'""").fetchone()[0],0)
        self.assertEqual(self.c.execute("""SELECT kind FROM
            royal_lab_nova_parameter_metadata WHERE nova_parameter_id=11"""
            ).fetchone()[0],"number")
        self.assertEqual(self.c.execute("""SELECT price FROM hospital_lab_tests
            WHERE code='ROYAL-22'""").fetchone()[0],4321)
        self.assertEqual([tuple(r) for r in self.c.execute(
            "SELECT * FROM hospital_lab_lines ORDER BY id")],before)
        self.assertEqual(self.c.execute(
            "SELECT reference_all FROM hospital_lab_parameters WHERE id=15"
            ).fetchone()[0],"99")

    def test_repeat_startup_preserves_manual_reference_edits_and_original_lines(self):
        reconcile_in_existing_nova(self.c,fixture(),self.schema)
        self.c.execute("UPDATE hospital_lab_parameters SET reference_all='9 - 14' WHERE id=12")
        self.c.execute("UPDATE royal_lab_nova_parameter_metadata SET kind='text' WHERE nova_parameter_id=11")
        self.c.execute("UPDATE hospital_lab_parameters SET active=1 WHERE id=13")
        reconcile_in_existing_nova(self.c,fixture(),self.schema)
        self.assertEqual(self.c.execute(
            "SELECT reference_all FROM hospital_lab_parameters WHERE id=12"
            ).fetchone()[0],"9 - 14")
        self.assertEqual(self.c.execute(
            "SELECT active FROM hospital_lab_parameters WHERE id=13"
            ).fetchone()[0],0)
        self.assertEqual(self.c.execute(
            "SELECT kind FROM royal_lab_nova_parameter_metadata WHERE nova_parameter_id=11"
            ).fetchone()[0],"number")
        self.assertEqual(self.c.execute(
            "SELECT COUNT(*) FROM royal_lab_nova_ptinr_photo_provenance"
            ).fetchone()[0],1)

    def test_invalid_source_does_not_modify_pt_inr_fields(self):
        source=fixture()
        source[0]["fields"][0]["source_analyte_id"]="wrong"
        before=[tuple(r) for r in self.c.execute("SELECT * FROM hospital_lab_parameters")]
        with self.assertRaises(ValueError):
            reconcile_in_existing_nova(self.c,source,self.schema)
        self.assertEqual([tuple(r) for r in self.c.execute(
            "SELECT * FROM hospital_lab_parameters")],before)

    def test_new_numeric_results_validation_without_approved_report_changes(self):
        reconcile_in_existing_nova(self.c,fixture(),self.schema)
        valid={"item_id":101,"values":[{"line_id":3,"value":"17.2"},
              {"line_id":4,"value":"1.34"}]}
        validate_save_payload(self.c,valid)
        for bad in ("abc","Infinity","-2","NaN"):
            invalid={"item_id":101,"values":[{"line_id":4,"value":bad}]}
            with self.subTest(value=bad),self.assertRaises(ValueError):
                validate_save_payload(self.c,invalid)
        with self.assertRaises(ValueError):
            validate_save_payload(self.c,{"item_id":101,"values":[
                {"line_id":5,"value":"5"}]})
        # Existing approved/historical result stays in original save workflow.
        validate_save_payload(self.c,{"item_id":100,"values":[
            {"line_id":1,"value":"old historical text"}]})
        # Unrelated assay remains unaffected.
        validate_save_payload(self.c,{"item_id":102,"values":[
            {"line_id":6,"value":"anything"}]})


if __name__=="__main__":
    unittest.main()
