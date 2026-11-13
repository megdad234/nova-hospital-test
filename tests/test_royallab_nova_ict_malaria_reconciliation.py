"""Screenshot-driven regression: inactive Royal Lab malaria ICT must be a dropdown.

No patient names, no production DB, no fabricated values or inferred kit species.
"""
import json
import sqlite3
import unittest
from hospital.royallab_catalog_audit import SOURCE
from hospital.royallab_native_result_form import native_catalog
from unittest.mock import patch
from hospital.royallab_existing_catalog_replacement import replace_catalog
from hospital.royallab_existing_line_overlay import overlay_existing_order_lines
from hospital.royallab_nova_ict_malaria_reconciliation import (
    _proven_source,reconcile_in_existing_nova,overlay_order_detail,
    validate_save_payload,CODE,PARAM_CODE,OPTIONS,OPTION_IDS)


def catalog():
    tests=[]
    for n in range(367):
        field={"source_analyte_id":str(n+1000),
            "source_format_id":str(n+400),
            "label":"Result","kind":"text","unit":"",
            "active":True,"options":[],"numeric_ranges":[],"text_ranges":[]}
        name="Royal Test "+str(n)
        if n==14:
            name="  Ict fof malaria"
            field.update(source_analyte_id="165",source_format_id="30",
                label="I.C.T for Malaria  ",active=False,
                kind="select_or_text",options=[
                {"id":"131","label":"Positive","active":True},
                {"id":"132","label":"Negative","active":True}])
        tests.append({"source_test_id":str(n),"name":name,
             "source_department_id":"1","review_flags":[],
             "fields":[field]})
    return {"tests":tests}


class MalariaICTPhotoTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.executescript("""
            CREATE TABLE hospital_lab_tests(
                id INTEGER PRIMARY KEY,code TEXT UNIQUE,name TEXT,
                category TEXT DEFAULT 'Other',price INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1);
            CREATE TABLE hospital_lab_parameters(
                id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,name TEXT,
                unit TEXT DEFAULT '',sort_order INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1);
            CREATE TABLE hospital_order_items(
                id INTEGER PRIMARY KEY,test_id INTEGER,order_id INTEGER,
                result_status TEXT DEFAULT 'pending',
                result_version INTEGER DEFAULT 0,result_text TEXT DEFAULT '');
            CREATE TABLE hospital_lab_lines(
                id INTEGER PRIMARY KEY,item_id INTEGER,parameter_id INTEGER,
                code TEXT NOT NULL,name TEXT NOT NULL,unit TEXT DEFAULT '',
                reference_range TEXT DEFAULT '',value TEXT DEFAULT '',
                UNIQUE(item_id,code));
            CREATE TABLE hospital_lab_revisions(id INTEGER PRIMARY KEY,item_id INTEGER);
            INSERT INTO hospital_lab_tests(id,code,name,price)
                VALUES(14,'ROYAL-14','  Ict fof malaria',8100);
            INSERT INTO hospital_lab_parameters(id,test_id,code,name,unit,active)
                VALUES(165,14,'ROYAL_FMT_30','I.C.T for Malaria','',0);
            INSERT INTO hospital_order_items(id,test_id,order_id)
                VALUES(1001,14,5001);
            INSERT INTO hospital_order_items(id,test_id,order_id,result_status,result_version)
                VALUES(1002,14,5002,'approved',1);
            INSERT INTO hospital_lab_lines(id,item_id,code,name,value)
                VALUES(301,1001,'RESULT','  Ict fof malaria','');
            INSERT INTO hospital_lab_lines(id,item_id,code,name,value)
                VALUES(302,1002,'RESULT','  Ict fof malaria','Negative');
        """)
        self.patcher=patch("hospital.royallab_existing_catalog_replacement.native_catalog",
                            return_value=catalog())
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.db.close()

    def details(self,item_id):
        lines=self.db.execute("""SELECT id,parameter_id,code,name,value FROM
            hospital_lab_lines WHERE item_id=? ORDER BY id""",(item_id,)).fetchall()
        return {"items":[{"id":item_id,
            "lines":[dict(zip(("id","parameter_id","code","name","value"),row)) for row in lines]}]}

    def test_actual_royal_source_ict_options_from_archive_are_preserved(self):
        library=json.loads(SOURCE.read_text(encoding="utf-8-sig"))
        native=native_catalog(library)
        field=_proven_source(native["tests"])
        self.assertEqual(field["source_analyte_id"],"165")
        self.assertEqual(field["source_format_id"],"30")
        self.assertIn(field["kind"],("select","select_or_text","select_or_number"))
        self.assertIn(field["active"],(False,0,"False","false","0"))

    def test_recovered_source_exact_identity_and_options(self):
        field=_proven_source(catalog()["tests"])
        self.assertEqual(field["source_format_id"],"30")
        self.assertIn(field["active"],(False,0,"False","false","0"))
        self.assertEqual(OPTIONS,("Positive","Negative"))
        self.assertEqual(OPTION_IDS,("131","132"))
        with self.assertRaisesRegex(ValueError,"documented options"):
            wrong=catalog()
            wrong["tests"][14]["fields"][0]["options"][0]["label"]="P. falciparum"
            _proven_source(wrong["tests"])
        with self.assertRaisesRegex(ValueError,"active state"):
            wrong=catalog()
            wrong["tests"][14]["fields"][0]["active"]=True
            _proven_source(wrong["tests"])

    def test_repair_existing_ict_in_place_without_price_or_new_test(self):
        result=replace_catalog(self.db,{},approved=True)
        self.assertEqual(result["ict_malaria_original_dropdown_fields"],1)
        self.assertEqual(self.db.execute("SELECT id,name,price FROM hospital_lab_tests WHERE code=?",(CODE,)).fetchone(),
                         (14,"ICT for Malaria",8100))
        self.assertEqual(self.db.execute("SELECT active FROM hospital_lab_parameters WHERE id=165").fetchone(),(1,))
        self.assertEqual(self.db.execute("""SELECT source_format_id,kind,options_json
            FROM royal_lab_nova_parameter_metadata WHERE nova_parameter_id=165""").fetchone()[:2],
            ("30","select"))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM hospital_lab_tests").fetchone()[0],367)
        row=self.db.execute("""SELECT original_source_inactive,explicit_hospital_form_override
            FROM royal_lab_nova_ict_malaria_provenance WHERE source_test_id='14'""").fetchone()
        self.assertEqual(row,(1,1))
        self.assertEqual(self.db.execute("""SELECT name FROM hospital_lab_tests
            WHERE code='ROYAL-13'""").fetchone(),("Royal Test 13",))

    def test_fallback_blank_in_existing_paid_order_becomes_original_dropdown(self):
        replace_catalog(self.db,{},approved=True)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM hospital_lab_lines WHERE item_id=1001").fetchone()[0],2)
        shown=overlay_order_detail(self.db,overlay_existing_order_lines(
            self.db,self.details(1001)))["items"][0]["lines"]
        self.assertEqual(len(shown),1)
        self.assertEqual(shown[0]["code"],PARAM_CODE)
        self.assertEqual(shown[0]["name"],"I.C.T for Malaria")
        self.assertEqual(shown[0]["royal_lab_field"]["kind"],"select")
        self.assertEqual(shown[0]["royal_lab_field"]["options"],["Positive","Negative"])
        self.assertEqual(self.db.execute("""SELECT code,value FROM hospital_lab_lines
            WHERE id=301""").fetchone(),("RESULT",""))
        self.assertEqual(self.db.execute(
            "SELECT result_version,result_status FROM hospital_order_items WHERE id=1001"
        ).fetchone(),(0,"pending"))
        # The old RESULT row stays hidden even after a new valid result is saved.
        self.db.execute("UPDATE hospital_lab_lines SET value='Positive' WHERE code='ROYAL_FMT_30' AND item_id=1001")
        self.db.execute("UPDATE hospital_order_items SET result_version=1,result_status='draft' WHERE id=1001")
        after=overlay_order_detail(self.db,self.details(1001))["items"][0]["lines"]
        self.assertEqual(len(after),1)
        self.assertEqual(after[0]["value"],"Positive")

    def test_historical_approved_negative_and_previous_text_are_unmodified(self):
        replace_catalog(self.db,{},approved=True)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM hospital_lab_lines WHERE item_id=1002").fetchone()[0],1)
        self.assertEqual(self.db.execute(
            "SELECT code,name,value FROM hospital_lab_lines WHERE id=302").fetchone(),
            ("RESULT","  Ict fof malaria","Negative"))
        self.assertEqual(overlay_order_detail(self.db,self.details(1002)),
                         self.details(1002))
        self.assertFalse(self.db.execute("""SELECT 1 FROM
            royal_lab_nova_ict_malaria_migrated_items WHERE item_id=1002""").fetchone())

    def test_idempotent_import_and_old_result_line_id(self):
        replace_catalog(self.db,{},approved=True)
        first=self.db.execute("SELECT id FROM hospital_lab_lines WHERE item_id=1001 AND code=?",
                              (PARAM_CODE,)).fetchone()[0]
        replace_catalog(self.db,{},approved=True)
        self.assertEqual(first,self.db.execute(
            "SELECT id FROM hospital_lab_lines WHERE item_id=1001 AND code=?",
            (PARAM_CODE,)).fetchone()[0])
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM hospital_lab_lines WHERE item_id=1001").fetchone()[0],2)
        self.assertEqual(self.db.execute(
            "SELECT active FROM hospital_lab_parameters WHERE id=165").fetchone()[0],1)
        self.assertEqual(self.db.execute(
            "SELECT price FROM hospital_lab_tests WHERE code='ROYAL-14'").fetchone()[0],8100)

    def test_save_validation_rejects_fake_results_invalid_and_legacy_blank(self):
        replace_catalog(self.db,{},approved=True)
        new_line=self.db.execute("SELECT id FROM hospital_lab_lines WHERE item_id=1001 AND code=?",
                                 (PARAM_CODE,)).fetchone()[0]
        for ok in OPTIONS:
            validate_save_payload(self.db,{"item_id":1001,"values":[
                {"line_id":new_line,"value":ok}]})
        for bad in ("P.falciparum","Invalid","POSITIVE","1",""):
            if bad=="":
                continue # An empty draft is allowed, never auto Negative.
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,"Positive or Negative"):
                validate_save_payload(self.db,{"item_id":1001,"values":[
                    {"line_id":new_line,"value":bad}]})
        with self.assertRaisesRegex(ValueError,"Obsolete"):
            validate_save_payload(self.db,{"item_id":1001,"values":[
                {"line_id":301,"value":"Positive"}]})
        with self.assertRaisesRegex(ValueError,"does not belong"):
            validate_save_payload(self.db,{"item_id":1001,"values":[
                {"line_id":302,"value":"Positive"}]})
        # A historically signed result can still be revised by NOVA's
        # existing permissions, independent of this new metadata.
        validate_save_payload(self.db,{"item_id":1002,"values":[
            {"line_id":302,"value":"Negative"}]})

    def test_nonempty_existing_free_text_does_not_rewrite_or_create_dropdown_line(self):
        self.db.execute("UPDATE hospital_lab_lines SET value='P. vivax?' WHERE id=301")
        replace_catalog(self.db,{},approved=True)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM hospital_lab_lines WHERE item_id=1001").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT value FROM hospital_lab_lines WHERE id=301").fetchone(),
                         ("P. vivax?",))
        self.assertFalse(self.db.execute("""SELECT 1 FROM
            royal_lab_nova_ict_malaria_migrated_items WHERE item_id=1001""").fetchone())

    def test_unrelated_test_source_mismatch_does_not_change_catalogue(self):
        bad=catalog()
        bad["tests"][14]["name"]="Different Malaria Assay"
        with patch("hospital.royallab_existing_catalog_replacement.native_catalog",
                   return_value=bad):
            res=replace_catalog(self.db,{},approved=True)
        self.assertEqual(res["ict_malaria_original_dropdown_fields"],0)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM royal_lab_nova_ict_malaria_provenance"
        ).fetchone()[0] if "royal_lab_nova_ict_malaria_provenance" in
            {r[0] for r in self.db.execute("SELECT name FROM sqlite_master")} else 0,0)


if __name__=="__main__":
    unittest.main()
