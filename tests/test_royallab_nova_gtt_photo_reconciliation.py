"""Protect G.T.T TestID 240 against its wrong original Royal Lab ALP field.

The original source is preserved; only future NOVA order parameter rows use
the photographed Al Sharq Hospital GTT with urine glucose result chart.
"""
import json
import sqlite3
import unittest
from unittest.mock import patch

from hospital.royallab_existing_catalog_replacement import replace_catalog
from hospital.royallab_existing_line_overlay import overlay_existing_order_lines
from hospital.royallab_nova_gtt_photo_reconciliation import (
    FIELDS, URINE_CHOICES, SOURCE_CODE, PARAM_PREFIX, _source_confirmed,
    overlay_order_detail as photo_overlay,validate_save_payload as gtt_validate,
)
from hospital.royallab_native_result_form import native_catalog
from hospital.royallab_catalog_audit import SOURCE


def source_like_fixture():
    tests=[]
    for n in range(367):
        f={"source_format_id":str(n+1), "label":"Result", "kind":"text",
           "unit":"","options":[],"numeric_ranges":[],"text_ranges":[]}
        name="Source Test "+str(n)
        if n == 240:
            name="G.T.T"
            f.update(label="ALP", kind="number", unit="mg/dl")
        tests.append({"source_test_id":str(n),"name":name,
                      "source_department_id":"1","review_flags":[],
                      "fields":[f]})
    return {"tests":tests}


class GTTWorksheetRepairTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.executescript("""
        CREATE TABLE hospital_lab_tests(
          id INTEGER PRIMARY KEY, code TEXT UNIQUE,name TEXT,
          category TEXT NOT NULL DEFAULT 'Other',price INTEGER DEFAULT 555,
          active INTEGER DEFAULT 1);
        CREATE TABLE hospital_lab_parameters(
          id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,name TEXT,
          unit TEXT,active INTEGER DEFAULT 1,sort_order INTEGER DEFAULT 0);
        CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,test_id INTEGER);
        CREATE TABLE hospital_lab_lines(
          id INTEGER PRIMARY KEY,item_id INTEGER,parameter_id INTEGER,
          code TEXT,name TEXT,value TEXT);
        INSERT INTO hospital_lab_tests(code,name,active)
           VALUES('OLD','Old clinic test',1);
        """)
        self.fixture=source_like_fixture()
        self.patcher=patch("hospital.royallab_existing_catalog_replacement.native_catalog",
                           return_value=self.fixture)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.db.close()

    def test_actual_recovered_source_gtt_is_alp_not_real_gtt(self):
        original=native_catalog(json.loads(SOURCE.read_text(encoding="utf-8-sig")))
        source=_source_confirmed(original["tests"])
        self.assertEqual(source["label"],"ALP")
        self.assertEqual(next(t for t in original["tests"]
                             if t["source_test_id"]=="240")["name"],"G.T.T")

    def test_repair_exactly_eleven_fields_with_no_fake_normal_range(self):
        res=replace_catalog(self.db,{},approved=True)
        self.assertEqual(res["gtt_photo_reconciled_fields"],11)
        test=self.db.execute("SELECT id,name,price,category FROM hospital_lab_tests WHERE code=?",
                             (SOURCE_CODE,)).fetchone()
        self.assertEqual(test[1:],("G.T.T",0,"Chemistry"))
        params=self.db.execute(
           "SELECT code,name,unit,active,sort_order,id FROM hospital_lab_parameters "
           "WHERE test_id=? ORDER BY id",(test[0],)).fetchall()
        self.assertEqual(len(params),12)
        original=[x for x in params if x[0]=="ROYAL_FMT_241"]
        self.assertEqual(len(original),1)
        self.assertEqual(original[0][1],"ALP")
        self.assertEqual(original[0][3],0)
        live=[p for p in params if p[3]==1]
        self.assertEqual([p[0] for p in live],[PARAM_PREFIX+f[0] for f in FIELDS])
        self.assertEqual([p[1] for p in live],[f[1] for f in FIELDS])
        self.assertEqual([p[2] for p in live],[f[3] for f in FIELDS])
        for p,field in zip(live,FIELDS):
            meta=self.db.execute(
              "SELECT kind,options_json,numeric_ranges_json,text_ranges_json,source_format_id "
              "FROM royal_lab_nova_parameter_metadata WHERE nova_parameter_id=?", (p[5],)
            ).fetchone()
            self.assertEqual(meta[0],field[2])
            self.assertEqual([x["label"] for x in json.loads(meta[1])],list(field[4]))
            self.assertEqual(json.loads(meta[2]),[])
            self.assertEqual(json.loads(meta[3]),[])
            self.assertEqual(meta[4],"PHOTO_GTT_240_"+field[0])
        self.assertEqual(self.db.execute(
          "SELECT original_analyte_name FROM royal_lab_nova_gtt_photo_provenance"
        ).fetchone()[0],"ALP")

    def test_existing_gtt_price_is_not_changed_by_worksheet_repair(self):
        self.db.execute("""INSERT INTO hospital_lab_tests(code,name,category,price,active)
             VALUES('ROYAL-240','G.T.T','Chemistry',555,1)""")
        replace_catalog(self.db,{},approved=True)
        self.assertEqual(self.db.execute(
            "SELECT price FROM hospital_lab_tests WHERE code='ROYAL-240'"
        ).fetchone()[0],555)
        replace_catalog(self.db,{},approved=True)
        self.assertEqual(self.db.execute(
            "SELECT price FROM hospital_lab_tests WHERE code='ROYAL-240'"
        ).fetchone()[0],555)

    def test_repeated_boot_preserves_parameter_ids_and_historical_result(self):
        replace_catalog(self.db,{},approved=True)
        id_test=self.db.execute("SELECT id FROM hospital_lab_tests WHERE code='ROYAL-240'").fetchone()[0]
        originals=self.db.execute(
           "SELECT id,code FROM hospital_lab_parameters WHERE test_id=? ORDER BY id",
           (id_test,)).fetchall()
        bad_id=next(p[0] for p in originals if p[1]=="ROYAL_FMT_241")
        self.db.execute("INSERT INTO hospital_order_items VALUES(101,?)",(id_test,))
        self.db.execute("""INSERT INTO hospital_lab_lines
            (id,item_id,parameter_id,code,name,value) VALUES(501,101,?,'ROYAL_FMT_241','ALP','12.3')""",
                        (bad_id,))
        replace_catalog(self.db,{},approved=True)
        after=self.db.execute(
           "SELECT id,code FROM hospital_lab_parameters WHERE test_id=? ORDER BY id",
           (id_test,)).fetchall()
        self.assertEqual(originals,after)
        self.assertEqual(self.db.execute(
          "SELECT code,name,value FROM hospital_lab_lines WHERE id=501").fetchone(),
          ("ROYAL_FMT_241","ALP","12.3"))
        self.assertEqual(self.db.execute(
          "SELECT active FROM hospital_lab_parameters WHERE id=?",(bad_id,)).fetchone()[0],0)

    def test_new_order_line_dropdown_metadata_is_usable(self):
        replace_catalog(self.db,{},approved=True)
        test=self.db.execute("SELECT id FROM hospital_lab_tests WHERE code='ROYAL-240'").fetchone()[0]
        self.db.execute("INSERT INTO hospital_order_items VALUES(110,?)",(test,))
        lines=[]
        for i,(code,label) in enumerate(self.db.execute(
          "SELECT code,name FROM hospital_lab_parameters WHERE test_id=? AND active=1 ORDER BY id",
          (test,)).fetchall(),1):
            line={"id":i,"code":code,"name":label}
            lines.append(line)
            self.db.execute(
                "INSERT INTO hospital_lab_lines(id,item_id,code,name,value) VALUES(?,?,?,?,'')",
                (i,110,code,label),
            )
        view=overlay_existing_order_lines(self.db,{"items":[{"id":110,"lines":lines}]})
        loaded=view["items"][0]["lines"]
        self.assertEqual(len(loaded),11)
        self.assertEqual(loaded[3]["royal_lab_field"]["kind"],"number")
        self.assertEqual(loaded[4]["royal_lab_field"]["kind"],"select")
        self.assertEqual(loaded[4]["royal_lab_field"]["options"],list(URINE_CHOICES))
        self.assertTrue(all(l.get("royal_lab_field") for l in loaded))

    def _make_legacy_order_schema(self):
        self.db.execute("ALTER TABLE hospital_order_items ADD COLUMN result_status TEXT DEFAULT 'pending'")
        self.db.execute("ALTER TABLE hospital_order_items ADD COLUMN result_version INTEGER DEFAULT 0")
        self.db.execute("ALTER TABLE hospital_order_items ADD COLUMN result_text TEXT DEFAULT ''")
        self.db.execute("ALTER TABLE hospital_lab_lines ADD COLUMN unit TEXT DEFAULT ''")
        self.db.execute("ALTER TABLE hospital_lab_lines ADD COLUMN reference_range TEXT DEFAULT ''")
        self.db.execute("CREATE TABLE hospital_lab_revisions(id INTEGER PRIMARY KEY,item_id INTEGER)")

    def _detail(self,item_id):
        result=self.db.execute("""SELECT id,parameter_id,code,name,value FROM
            hospital_lab_lines WHERE item_id=? ORDER BY id""",(item_id,)).fetchall()
        return {"items":[{"id":item_id,"lines":[
            dict(zip(("id","parameter_id","code","name","value"),row))
            for row in result]}]}

    def test_existing_paid_blank_alp_order_migrates_into_correct_gtt_form(self):
        self._make_legacy_order_schema()
        replace_catalog(self.db,{},approved=True)
        tid=self.db.execute("SELECT id FROM hospital_lab_tests WHERE code='ROYAL-240'").fetchone()[0]
        bad=self.db.execute("""SELECT id,code FROM hospital_lab_parameters
            WHERE test_id=? AND name='ALP'""",(tid,)).fetchone()
        self.db.execute("INSERT INTO hospital_order_items(id,test_id) VALUES(2001,?)",(tid,))
        self.db.execute("""INSERT INTO hospital_lab_lines
            (id,item_id,parameter_id,code,name,value) VALUES(9001,2001,?,?,'ALP','')""",
            bad)
        replace_catalog(self.db,{},approved=True)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM hospital_lab_lines WHERE item_id=2001").fetchone()[0],12)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM royal_lab_nova_gtt_migrated_items WHERE item_id=2001").fetchone()[0],1)
        details=overlay_existing_order_lines(self.db,self._detail(2001))
        shown=photo_overlay(self.db,details)["items"][0]["lines"]
        self.assertEqual(len(shown),11)
        self.assertEqual([line["name"] for line in shown],[f[1] for f in FIELDS])
        self.assertTrue(all(line["royal_lab_field"]["kind"] in ("number","select","text")
                            for line in shown))
        self.assertEqual(self.db.execute("SELECT value FROM hospital_lab_lines WHERE id=9001").fetchone(),("",))
        self.assertEqual(self.db.execute(
            "SELECT result_status,result_version FROM hospital_order_items WHERE id=2001").fetchone(),
            ("pending",0))
        # The wrong ALP does NOT reappear after this item has been saved.
        fasting=next(line for line in shown if line["code"]==PARAM_PREFIX+"blood_fasting")
        self.db.execute("UPDATE hospital_lab_lines SET value='92' WHERE id=?",(fasting["id"],))
        self.db.execute("UPDATE hospital_order_items SET result_version=1,result_status='draft' WHERE id=2001")
        shown_again=photo_overlay(self.db,self._detail(2001))["items"][0]["lines"]
        self.assertEqual(len(shown_again),11)
        self.assertNotIn("ALP",[x["name"] for x in shown_again])

    def test_old_approved_result_never_migrates_or_loses_original_alp(self):
        self._make_legacy_order_schema()
        replace_catalog(self.db,{},approved=True)
        tid=self.db.execute("SELECT id FROM hospital_lab_tests WHERE code='ROYAL-240'").fetchone()[0]
        bad=self.db.execute("""SELECT id,code FROM hospital_lab_parameters
            WHERE test_id=? AND name='ALP'""",(tid,)).fetchone()
        self.db.execute("""INSERT INTO hospital_order_items
            (id,test_id,result_status,result_version) VALUES(2002,?,'approved',1)""",(tid,))
        self.db.execute("""INSERT INTO hospital_lab_lines
            (id,item_id,parameter_id,code,name,value) VALUES(9002,2002,?,?,'ALP','55')""",bad)
        replace_catalog(self.db,{},approved=True)
        self.assertFalse(self.db.execute(
            "SELECT 1 FROM royal_lab_nova_gtt_migrated_items WHERE item_id=2002").fetchone())
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM hospital_lab_lines WHERE item_id=2002").fetchone()[0],1)
        record=photo_overlay(self.db,self._detail(2002))["items"][0]["lines"]
        self.assertEqual([(x["name"],x["value"]) for x in record],[("ALP","55")])

    def test_corrected_gtt_numeric_and_urine_inputs_are_validated(self):
        self._make_legacy_order_schema()
        replace_catalog(self.db,{},approved=True)
        tid=self.db.execute("SELECT id FROM hospital_lab_tests WHERE code='ROYAL-240'").fetchone()[0]
        bad=self.db.execute("SELECT id,code FROM hospital_lab_parameters WHERE test_id=? AND name='ALP'",
                            (tid,)).fetchone()
        self.db.execute("INSERT INTO hospital_order_items(id,test_id) VALUES(2003,?)",(tid,))
        self.db.execute("""INSERT INTO hospital_lab_lines
            (id,item_id,parameter_id,code,name,value) VALUES(9003,2003,?,?,'ALP','')""",bad)
        replace_catalog(self.db,{},approved=True)
        codes=dict(self.db.execute("SELECT code,id FROM hospital_lab_lines WHERE item_id=2003"))
        gtt_validate(self.db,{"item_id":2003,"values":[
            {"line_id":codes[PARAM_PREFIX+"blood_fasting"],"value":"97"},
            {"line_id":codes[PARAM_PREFIX+"urine_fasting"],"value":"Trace"}]})
        for invalid in ("ALP","NaN","Infinity","-2"):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                gtt_validate(self.db,{"item_id":2003,"values":[
                    {"line_id":codes[PARAM_PREFIX+"blood_fasting"],"value":invalid}]})
        with self.assertRaisesRegex(ValueError,"dropdown"):
            gtt_validate(self.db,{"item_id":2003,"values":[
                {"line_id":codes[PARAM_PREFIX+"urine_fasting"],"value":"Other"}]})
        with self.assertRaisesRegex(ValueError,"ALP"):
            gtt_validate(self.db,{"item_id":2003,"values":[{"line_id":9003,"value":"53"}]})

    def test_unrelated_source_does_not_trigger_photo_override(self):
        fake=source_like_fixture()
        fake["tests"][240]["fields"][0]["label"]="Glucose"
        with patch("hospital.royallab_existing_catalog_replacement.native_catalog",
                   return_value=fake):
            res=replace_catalog(self.db,{},approved=True)
        self.assertEqual(res["gtt_photo_reconciled_fields"],0)
        self.assertFalse(self.db.execute(
            "SELECT 1 FROM sqlite_master WHERE name='royal_lab_nova_gtt_photo_provenance'"
        ).fetchone())
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM hospital_lab_parameters WHERE code LIKE 'ROYAL_GTT_240_%'"
        ).fetchone()[0],0)

if __name__=="__main__":
    unittest.main()
