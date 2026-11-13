"""Regression: real existing ROYAL-240 G.T.T must NOT render Royal source ALP.

Synthetic NOVA schema/order fixtures only. No patient data or pharmacy changes.
"""
import sqlite3
import unittest
from unittest.mock import patch

from hospital.nova_gtt_royal240_fix import (
    TARGET_CODE, PREFIX, FIELDS, install, overlay_order_detail,
    validate_save_payload)
from hospital.royallab_existing_catalog_replacement import replace_catalog
def synthetic_catalog():
    return {"tests":[{
        "source_test_id":str(i), "name":"Royal Test "+str(i),
        "source_department_id":"1", "review_flags":[],
        "fields":[{
            "source_format_id":str(i+1),
            "label":"ALP" if i==240 else "Result",
            "kind":"select", "unit":"",
            "options":[{"id":"P","label":"Positive","active":True}],
            "numeric_ranges":[], "text_ranges":[]
        }]} for i in range(367)]}



def db_fixture():
    db=sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE hospital_lab_tests(
            id INTEGER PRIMARY KEY,code TEXT UNIQUE,name TEXT,price INTEGER DEFAULT 0,
            category TEXT DEFAULT 'Other',active INTEGER DEFAULT 1);
        CREATE TABLE hospital_lab_parameters(
            id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,name TEXT,unit TEXT DEFAULT '',
            reference_all TEXT DEFAULT '',sort_order INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,UNIQUE(test_id,code));
        CREATE TABLE hospital_order_items(
            id INTEGER PRIMARY KEY,order_id INTEGER,test_id INTEGER,
            result_status TEXT DEFAULT 'pending',result_version INTEGER DEFAULT 0,
            result_text TEXT DEFAULT '');
        CREATE TABLE hospital_lab_lines(
            id INTEGER PRIMARY KEY,item_id INTEGER,parameter_id INTEGER,
            code TEXT,name TEXT,unit TEXT DEFAULT '',reference_range TEXT DEFAULT '',
            value TEXT DEFAULT '',source TEXT DEFAULT 'manual',UNIQUE(item_id,code));
        CREATE TABLE hospital_lab_revisions(id INTEGER PRIMARY KEY,item_id INTEGER);
        INSERT INTO hospital_lab_tests(id,code,name,price,category)
          VALUES(240,'ROYAL-240','G.T.T',12500,'Chemistry');
        INSERT INTO hospital_lab_parameters(id,test_id,code,name,unit,sort_order)
          VALUES(973,240,'ROYAL_FMT_2400','ALP','mg/dl',0);
        INSERT INTO hospital_lab_tests(id,code,name,price,category)
          VALUES(237,'ROYAL-237','ALT',5000,'Chemistry');
        INSERT INTO hospital_lab_parameters(id,test_id,code,name,unit)
          VALUES(970,237,'ROYAL_FMT_2370','ALT','U/L');
        INSERT INTO hospital_order_items(id,order_id,test_id) VALUES (1,100,240);
        INSERT INTO hospital_order_items(id,order_id,test_id,result_status,result_version)
          VALUES(2,101,240,'approved',2);
        INSERT INTO hospital_order_items(id,order_id,test_id) VALUES (3,102,237);
        INSERT INTO hospital_lab_lines(item_id,parameter_id,code,name,unit,value)
          VALUES(1,973,'ROYAL_FMT_2400','ALP','mg/dl','');
        INSERT INTO hospital_lab_lines(item_id,parameter_id,code,name,unit,value)
          VALUES(2,973,'ROYAL_FMT_2400','ALP','mg/dl','55');
        INSERT INTO hospital_lab_lines(item_id,parameter_id,code,name,unit,value)
          VALUES(3,970,'ROYAL_FMT_2370','ALT','U/L','14');
    """)
    return db


class GTTExistingRoyalTestFix(unittest.TestCase):
    def setUp(self):
        self.db=db_fixture()

    def tearDown(self):
        self.db.close()

    def _detail(self,item_id):
        rows=self.db.execute("""SELECT id,parameter_id,code,name,unit,value
            FROM hospital_lab_lines WHERE item_id=? ORDER BY id""",
            (item_id,)).fetchall()
        return {"items":[{"id":item_id,"lines":[
            dict(zip(("id","parameter_id","code","name","unit","value"),r))
            for r in rows]}]}

    def test_existing_royal_240_is_corrected_without_new_test_or_price_change(self):
        before=self.db.execute("SELECT count(*),sum(price) FROM hospital_lab_tests").fetchone()
        result=install(self.db)
        self.assertEqual(result["test_code"],TARGET_CODE)
        self.assertEqual(result["corrected_fields"],11)
        self.assertEqual(self.db.execute("SELECT count(*),sum(price) FROM hospital_lab_tests").fetchone(),before)
        rows=self.db.execute("""SELECT code,name,unit,active FROM hospital_lab_parameters
            WHERE test_id=240 ORDER BY sort_order,id""").fetchall()
        self.assertEqual(len(rows),12)
        self.assertEqual(rows[0],("ROYAL_FMT_2400","ALP","mg/dl",0))
        self.assertEqual(sum(x[3]==1 for x in rows),11)
        self.assertEqual([r[0] for r in rows[1:]], [PREFIX+f["key"] for f in FIELDS])
        self.assertEqual(self.db.execute(
            "SELECT active FROM hospital_lab_parameters WHERE id=970").fetchone()[0],1)

    def test_unreported_existing_order_is_backfilled_but_alp_kept_in_archive(self):
        install(self.db)
        raw=self._detail(1)
        self.assertEqual(len(raw["items"][0]["lines"]),12)
        self.assertEqual(raw["items"][0]["lines"][0]["name"],"ALP")
        shown=overlay_order_detail(self.db,raw)["items"][0]["lines"]
        self.assertEqual(len(shown),11)
        self.assertNotIn("ALP",[f["name"] for f in shown])
        self.assertEqual([f["name"] for f in shown],[f["label"] for f in FIELDS])
        for f in shown:
            self.assertIn(f["royal_lab_field"]["kind"],("number","text","select"))
        selections=[f for f in shown if f["royal_lab_field"]["kind"]=="select"]
        self.assertEqual(len(selections),4)
        self.assertEqual(selections[1]["royal_lab_field"]["options"],
                         ["Negative","Trace","+1","+2","+3","+4"])
        self.assertEqual(self.db.execute(
            "SELECT value FROM hospital_lab_lines WHERE item_id=1 AND code='ROYAL_FMT_2400'"
        ).fetchone(),("",))
        self.assertEqual(self.db.execute(
            "SELECT result_version,result_status FROM hospital_order_items WHERE id=1"
        ).fetchone(),(0,"pending"))

    def test_historical_approved_alp_is_unchanged_and_not_backfilled(self):
        install(self.db)
        rows=self.db.execute("SELECT code,value FROM hospital_lab_lines WHERE item_id=2").fetchall()
        self.assertEqual(rows,[("ROYAL_FMT_2400","55")])
        shown=overlay_order_detail(self.db,self._detail(2))["items"][0]["lines"]
        self.assertEqual([(f["code"],f["value"]) for f in shown],rows)
        self.assertEqual(self.db.execute(
            "SELECT result_status,result_version FROM hospital_order_items WHERE id=2"
        ).fetchone(),("approved",2))

    def test_safe_idempotence_across_restart_and_original_other_test_preserved(self):
        install(self.db)
        ids=self.db.execute("""SELECT id FROM hospital_lab_parameters
            WHERE test_id=240 AND code LIKE 'NOVA_GTT_%' ORDER BY id""").fetchall()
        total=self.db.execute("SELECT count(*) FROM hospital_lab_lines").fetchone()[0]
        install(self.db)
        self.assertEqual(ids,self.db.execute("""SELECT id FROM hospital_lab_parameters
            WHERE test_id=240 AND code LIKE 'NOVA_GTT_%' ORDER BY id""").fetchall())
        self.assertEqual(self.db.execute("SELECT count(*) FROM hospital_lab_lines").fetchone()[0],total)
        self.assertEqual(self.db.execute(
            "SELECT name,value FROM hospital_lab_lines WHERE item_id=3").fetchone(),
            ("ALT","14"))
        self.assertEqual(overlay_order_detail(self.db,self._detail(3)),self._detail(3))

    def test_original_mislinked_alp_cannot_be_saved_as_gtt_result(self):
        install(self.db)
        with self.assertRaisesRegex(ValueError,"ALP"):
            validate_save_payload(self.db,{"item_id":1,"values":[{"line_id":1,"value":"52"}]})

    def test_correct_form_numeric_dropdown_and_nonfinite_validation(self):
        install(self.db)
        rows=self.db.execute("""SELECT l.id,m.field_key
            FROM hospital_lab_lines l
            JOIN hospital_lab_parameters p ON p.id=l.parameter_id
            JOIN nova_gtt_royal240_field_metadata m ON m.nova_parameter_id=p.id
            WHERE l.item_id=1""").fetchall()
        fields={k:i for i,k in rows}
        self.assertEqual(len(fields),11)
        validate_save_payload(self.db,{"item_id":1,"values":[
            {"line_id":fields["blood_fasting"],"value":"95"},
            {"line_id":fields["urine_fasting"],"value":"Negative"},
            {"line_id":fields["blood_one_hour"],"value":"160"},
            {"line_id":fields["urine_two_hours"],"value":"+2"}]})
        for invalid in ("ALP","NaN","Infinity","-1"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_save_payload(self.db,{"item_id":1,"values":[
                    {"line_id":fields["blood_fasting"],"value":invalid}]})
        with self.assertRaisesRegex(ValueError,"dropdown"):
            validate_save_payload(self.db,{"item_id":1,"values":[
                {"line_id":fields["urine_fasting"],"value":"not in the original paper"}]})
        with self.assertRaisesRegex(ValueError,"does not belong"):
            validate_save_payload(self.db,{"item_id":1,"values":[
                {"line_id":900000,"value":"3"}]})

    def test_migration_fails_closed_if_source_definition_no_longer_alp(self):
        self.db.execute("UPDATE hospital_lab_parameters SET name='CRP' WHERE id=973")
        with self.assertRaisesRegex(RuntimeError,"ALP source"):
            install(self.db)
        self.assertEqual(self.db.execute("SELECT count(*) FROM hospital_lab_parameters").fetchone()[0],2)

    def test_preserve_preexisting_drafts_or_nonempty_unapproved_result(self):
        self.db.execute("UPDATE hospital_lab_lines SET value='48' WHERE item_id=1")
        install(self.db)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM hospital_lab_lines WHERE item_id=1").fetchone()[0],1)
        shown=overlay_order_detail(self.db,self._detail(1))["items"][0]["lines"]
        self.assertEqual(shown[0]["value"],"48")

    def test_source_catalog_reimport_does_not_reject_hospital_documented_gtt_fields(self):
        # Existing source import must keep its *real* metadata, and not confuse
        # the 11 photographed hospital fields with original Royal ResultFormats.
        cat=synthetic_catalog()
        orig=cat["tests"][240]
        orig["fields"][0]["label"]="ALP"
        with patch("hospital.royallab_existing_catalog_replacement.native_catalog",return_value=cat):
            c=sqlite3.connect(":memory:")
            try:
                c.executescript("""
                    CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,code TEXT UNIQUE,
                        name TEXT,price INTEGER DEFAULT 0,category TEXT DEFAULT 'Other',
                        active INTEGER DEFAULT 1);
                    CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,
                        test_id INTEGER,code TEXT,name TEXT,unit TEXT,sort_order INTEGER DEFAULT 0,
                        active INTEGER DEFAULT 1);
                    CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,test_id INTEGER,
                        result_version INTEGER DEFAULT 0,result_status TEXT DEFAULT 'pending',
                        result_text TEXT DEFAULT '');
                    CREATE TABLE hospital_lab_lines(id INTEGER PRIMARY KEY,item_id INTEGER,
                        parameter_id INTEGER,code TEXT,name TEXT,unit TEXT,value TEXT DEFAULT '');
                    CREATE TABLE hospital_lab_revisions(id INTEGER PRIMARY KEY,item_id INTEGER);
                """)
                replace_catalog(c,{},approved=True)
                install(c)
                replace_catalog(c,{},approved=True)
                install(c)
                gtt=c.execute("""SELECT active FROM hospital_lab_parameters p
                    JOIN hospital_lab_tests t ON t.id=p.test_id
                    WHERE t.code='ROYAL-240' AND p.name='ALP'""").fetchone()[0]
                self.assertEqual(gtt,0)
                self.assertEqual(c.execute("SELECT COUNT(*) FROM nova_gtt_royal240_field_metadata").fetchone()[0],11)
            finally:
                c.close()


if __name__=="__main__":
    unittest.main()
