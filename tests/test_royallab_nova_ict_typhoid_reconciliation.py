"""Original Typhoid ICT TestID 309: photo-confirmed dropdown, no print changes."""
import json
import sqlite3
import unittest

from hospital.royallab_catalog_audit import SOURCE
from hospital.royallab_native_result_form import native_catalog
from hospital.royallab_existing_line_overlay import overlay_existing_order_lines
from hospital.royallab_nova_ict_typhoid_reconciliation import (
    _source, reconcile_in_existing_nova, validate_save_payload,
    FIELD_SPECS, PARAM_CODES, OPTIONS, TEST_CODE,
)


def original_like_catalog():
    return [{"source_test_id":"309","name":"ICT for Typhoid","fields":[
        {"source_format_id":sid,"source_analyte_id":analyte,"label":name,
         "unit":"","kind":"text","types":[],"options":[],"active":True}
        for analyte,name,sid in FIELD_SPECS]}]


class TyphoidICThreeDropdownTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.executescript("""
        CREATE TABLE hospital_lab_tests(
          id INTEGER PRIMARY KEY,code TEXT UNIQUE,name TEXT,price INTEGER DEFAULT 0);
        CREATE TABLE hospital_lab_parameters(
          id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,name TEXT,
          unit TEXT,active INTEGER,sort_order INTEGER DEFAULT 0);
        CREATE TABLE royal_lab_nova_parameter_metadata(
          nova_parameter_id INTEGER PRIMARY KEY,
          source_test_id TEXT NOT NULL,source_format_id TEXT NOT NULL,
          kind TEXT NOT NULL,options_json TEXT NOT NULL,
          numeric_ranges_json TEXT NOT NULL,text_ranges_json TEXT NOT NULL);
        CREATE TABLE hospital_order_items(
          id INTEGER PRIMARY KEY,test_id INTEGER,
          result_status TEXT DEFAULT 'pending',result_version INTEGER DEFAULT 0);
        CREATE TABLE hospital_lab_lines(
          id INTEGER PRIMARY KEY,item_id INTEGER,parameter_id INTEGER,
          code TEXT,name TEXT,value TEXT,unit TEXT DEFAULT '',
          reference_range TEXT DEFAULT '');
        INSERT INTO hospital_lab_tests VALUES(309,'ROYAL-309','ICT for Typhoid',8000);
        INSERT INTO hospital_lab_tests VALUES(347,'ROYAL-347','ICT for typhoid',100);
        INSERT INTO hospital_lab_tests VALUES(115,'ROYAL-115','Widal Test for Typhoid',200);
        INSERT INTO hospital_lab_tests VALUES(14,'ROYAL-14','ICT for Malaria',300);
        INSERT INTO hospital_lab_tests VALUES(1000,'OLD-MALARIA','Malaria test',400);
        INSERT INTO hospital_order_items VALUES(1,309,'pending',0);
        INSERT INTO hospital_order_items VALUES(2,309,'approved',3);
        INSERT INTO hospital_order_items VALUES(3,309,'pending',0);
        INSERT INTO hospital_order_items VALUES(4,347,'pending',0);
        INSERT INTO hospital_order_items VALUES(5,115,'pending',0);
        INSERT INTO hospital_order_items VALUES(6,14,'pending',0);
        INSERT INTO hospital_order_items VALUES(7,1000,'pending',0);
        INSERT INTO hospital_lab_lines(id,item_id,parameter_id,code,name,value)
          VALUES(21,2,1,'ROYAL_ANALYTE_1291','ICT for Typhoid','Historical');
        INSERT INTO hospital_lab_lines(id,item_id,code,name,value)
          VALUES(41,4,'RESULT','ICT for typhoid','old');
        INSERT INTO hospital_lab_lines(id,item_id,code,name,value)
          VALUES(51,5,'WIDAL','Titre','1/160');
        INSERT INTO hospital_lab_lines(id,item_id,code,name,value)
          VALUES(61,6,'ROYAL_FMT_30','I.C.T for Malaria','Positive');
        INSERT INTO hospital_lab_lines(id,item_id,code,name,value)
          VALUES(71,7,'RESULT','Malaria parasite','old free text');
        """)
        for i,(analyte,name,sid) in enumerate(FIELD_SPECS,1):
            code=PARAM_CODES[i-1]
            self.db.execute("""INSERT INTO hospital_lab_parameters
              (id,test_id,code,name,unit,active,sort_order)
              VALUES(?,?,?,?,?,1,0)""",(i,309,code,name,""))
            self.db.execute("""INSERT INTO royal_lab_nova_parameter_metadata
              (nova_parameter_id,source_test_id,source_format_id,kind,
               options_json,numeric_ranges_json,text_ranges_json)
              VALUES(?,'309',?,'text','[]','[]','[]')""",(i,sid))
            self.db.execute("""INSERT INTO hospital_lab_lines
              (id,item_id,parameter_id,code,name,value)
              VALUES(?,?,?,?,?,'')""",(10+i,1,i,code,name))
            self.db.execute("""INSERT INTO hospital_lab_lines
              (id,item_id,parameter_id,code,name,value)
              VALUES(?,?,?,?,?,?)""",(30+i,3,i,code,name,"Previously written" if i==1 else ""))
        self.schema={r[1] for r in self.db.execute(
            "PRAGMA table_info(hospital_lab_parameters)")}

    def tearDown(self):
        self.db.close()

    def test_original_archive_has_exact_three_active_untyped_fields(self):
        catalog=native_catalog(json.loads(SOURCE.read_text(encoding="utf-8-sig")))
        src=_source(catalog["tests"])
        self.assertEqual(src["source_test_id"],"309")
        self.assertEqual([(f["source_analyte_id"],f["label"],f["source_format_id"])
                          for f in src["fields"]],list(FIELD_SPECS))
        self.assertTrue(all(f["kind"]=="text" and not f["types"] and
                            not f["options"] for f in src["fields"]))
        other=next(t for t in catalog["tests"] if t["source_test_id"]=="347")
        self.assertEqual(other["fields"],[], "Do not treat untyped 347 as screenshot 309")
        widal=next(t for t in catalog["tests"] if t["source_test_id"]=="115")
        self.assertTrue(any("Titre" in f["label"] for f in widal["fields"]))
        self.assertEqual(OPTIONS,("Positive","Negative"))

    def test_upgrades_only_three_existing_source_parameter_ids_to_dropdown(self):
        before=[tuple(r) for r in self.db.execute(
            "SELECT * FROM hospital_lab_lines ORDER BY id")]
        self.assertEqual(reconcile_in_existing_nova(
            self.db,original_like_catalog(),self.schema),3)
        params=self.db.execute("""SELECT id,code,name,sort_order FROM
             hospital_lab_parameters WHERE test_id=309 ORDER BY sort_order,id""").fetchall()
        self.assertEqual(params,[(1,PARAM_CODES[0],"ICT for Typhoid",1),
                                 (2,PARAM_CODES[1],"IgG",2),
                                 (3,PARAM_CODES[2],"IgM",3)])
        for i,(_a,_n,sid) in enumerate(FIELD_SPECS,1):
            m=self.db.execute("""SELECT source_format_id,kind,options_json
                FROM royal_lab_nova_parameter_metadata
                WHERE nova_parameter_id=?""",(i,)).fetchone()
            self.assertEqual((m[0],m[1]),(sid,"select"))
            self.assertEqual([o["label"] for o in json.loads(m[2])],
                             ["Positive","Negative"])
        self.assertEqual([tuple(r) for r in self.db.execute(
            "SELECT * FROM hospital_lab_lines ORDER BY id")],before)
        self.assertEqual(self.db.execute(
            "SELECT price FROM hospital_lab_tests WHERE code='ROYAL-309'"
            ).fetchone()[0],8000)
        for code in ("ROYAL-347","ROYAL-115","ROYAL-14","OLD-MALARIA"):
            self.assertEqual(self.db.execute(
                "SELECT COUNT(*) FROM hospital_lab_tests WHERE code=?",
                (code,)).fetchone()[0],1)

    def test_existing_result_screen_receives_three_real_selects(self):
        reconcile_in_existing_nova(self.db,original_like_catalog(),self.schema)
        lines=[{"id":10+i,"parameter_id":i,"code":code,"name":name,"value":""}
                for i,(code,(_a,name,_sid)) in
                enumerate(zip(PARAM_CODES,FIELD_SPECS),1)]
        detail={"items":[{"id":1,"lines":lines}]}
        rendered=overlay_existing_order_lines(self.db,detail)
        self.assertEqual([line["royal_lab_field"]["kind"]
                          for line in rendered["items"][0]["lines"]],
                         ["select","select","select"])
        self.assertEqual([line["royal_lab_field"]["options"]
                          for line in rendered["items"][0]["lines"]],
                         [["Positive","Negative"]]*3)
        self.assertNotIn("royal_lab_field",detail["items"][0]["lines"][0])

    def test_validate_new_choices_and_preserve_legacy_free_text(self):
        reconcile_in_existing_nova(self.db,original_like_catalog(),self.schema)
        validate_save_payload(self.db,{"item_id":1,"values":[
            {"line_id":11,"value":"Positive"},
            {"line_id":12,"value":"Negative"},
            {"line_id":13,"value":"Positive"}]})
        for bad in ("positive","Negative ", "pending", "Reactive", "No malaria parasite seen"):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                validate_save_payload(self.db,{"item_id":1,"values":[
                    {"line_id":12,"value":bad}]})
        with self.assertRaises(ValueError):
            validate_save_payload(self.db,{"item_id":1,"values":[
                {"line_id":71,"value":"Positive"}]})
        # Previously saved historical text, including unapproved text orders,
        # is not silently reinterpreted.
        validate_save_payload(self.db,{"item_id":2,"values":[
            {"line_id":21,"value":"History is preserved"}]})
        validate_save_payload(self.db,{"item_id":3,"values":[
            {"line_id":31,"value":"Previously written"}]})
        for iid,lid in ((4,41),(5,51),(6,61),(7,71)):
            validate_save_payload(self.db,{"item_id":iid,"values":[
                {"line_id":lid,"value":"Unchanged unrelated result"}]})

    def test_repeat_import_preserves_ids_and_administrator_sorting(self):
        reconcile_in_existing_nova(self.db,original_like_catalog(),self.schema)
        self.db.execute("UPDATE hospital_lab_parameters SET sort_order=77 WHERE id=2")
        reconcile_in_existing_nova(self.db,original_like_catalog(),self.schema)
        self.assertEqual(self.db.execute(
            "SELECT sort_order FROM hospital_lab_parameters WHERE id=2"
            ).fetchone()[0],77)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM royal_lab_nova_ict_typhoid_photo_provenance"
            ).fetchone()[0],1)
        # Catalogue import refreshes native metadata on every startup.
        for i,(_a,_n,sid) in enumerate(FIELD_SPECS,1):
            self.db.execute("""UPDATE royal_lab_nova_parameter_metadata
                SET kind='text',options_json='[]' WHERE nova_parameter_id=?""",(i,))
        reconcile_in_existing_nova(self.db,original_like_catalog(),self.schema)
        self.assertEqual(self.db.execute(
            "SELECT sort_order FROM hospital_lab_parameters WHERE id=2"
            ).fetchone()[0],77)

    def test_changed_source_fails_before_any_catalogue_or_patient_mutation(self):
        src=original_like_catalog()
        src[0]["fields"][0]["source_analyte_id"]="not-original"
        prior=[tuple(r) for r in self.db.execute(
            "SELECT * FROM hospital_lab_parameters ORDER BY id")]
        with self.assertRaises(ValueError):
            reconcile_in_existing_nova(self.db,src,self.schema)
        self.assertEqual([tuple(r) for r in self.db.execute(
            "SELECT * FROM hospital_lab_parameters ORDER BY id")],prior)


if __name__ == "__main__":
    unittest.main()
