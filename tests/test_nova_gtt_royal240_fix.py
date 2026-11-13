"""Existing Royal Lab G.T.T TestID 240: no more ALP on active result entry."""
import sqlite3
import unittest
from hospital.nova_gtt_royal240_fix import (
    install,overlay_order_detail,validate_save_payload,FORM,PREFIX)


def db_fixture():
    c=sqlite3.connect(":memory:")
    c.executescript("""
      CREATE TABLE hospital_lab_tests (
        id INTEGER PRIMARY KEY, code TEXT UNIQUE,name TEXT,
        category TEXT DEFAULT 'Other',price INTEGER DEFAULT 0,active INTEGER DEFAULT 1);
      CREATE TABLE hospital_lab_parameters (
        id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,name TEXT,unit TEXT DEFAULT '',
        reference_all TEXT DEFAULT '',sort_order INTEGER DEFAULT 0,active INTEGER DEFAULT 1,
        UNIQUE(test_id,code));
      CREATE TABLE hospital_order_items(
        id INTEGER PRIMARY KEY,test_id INTEGER,order_id INTEGER,
        result_status TEXT DEFAULT 'pending', result_version INTEGER DEFAULT 0,
        result_text TEXT DEFAULT '');
      CREATE TABLE hospital_lab_lines(
        id INTEGER PRIMARY KEY,item_id INTEGER,parameter_id INTEGER,
        code TEXT,name TEXT,unit TEXT DEFAULT '',reference_range TEXT DEFAULT '',
        value TEXT DEFAULT '', UNIQUE(item_id,code));
      CREATE TABLE hospital_lab_revisions(id INTEGER PRIMARY KEY,item_id INTEGER);
      INSERT INTO hospital_lab_tests(id,code,name,category,price)
        VALUES(240,'ROYAL-240','G.T.T','Chemistry',12000);
      INSERT INTO hospital_lab_parameters(id,test_id,code,name,unit,sort_order)
        VALUES(973,240,'ROYAL_FMT_7777','ALP','mg/dl',0);
      INSERT INTO hospital_lab_tests(id,code,name,price)
        VALUES(237,'ROYAL-237','ALT',4000);
      INSERT INTO hospital_lab_parameters(id,test_id,code,name,unit)
        VALUES(970,237,'ROYAL_FMT_2370','ALT','U/L');
      INSERT INTO hospital_order_items(id,test_id,order_id) VALUES(1001,240,500);
      INSERT INTO hospital_order_items(id,test_id,order_id,result_status,result_version)
        VALUES(1002,240,501,'approved',1);
      INSERT INTO hospital_order_items(id,test_id,order_id) VALUES(1003,237,502);
      INSERT INTO hospital_lab_lines(id,item_id,parameter_id,code,name,unit,value)
        VALUES(3001,1001,973,'ROYAL_FMT_7777','ALP','mg/dl','');
      INSERT INTO hospital_lab_lines(id,item_id,parameter_id,code,name,unit,value)
        VALUES(3002,1002,973,'ROYAL_FMT_7777','ALP','mg/dl','55');
      INSERT INTO hospital_lab_lines(id,item_id,parameter_id,code,name,unit,value)
        VALUES(3003,1003,970,'ROYAL_FMT_2370','ALT','U/L','14');
    """)
    return c


class RealExistingGTTFormTests(unittest.TestCase):
    def setUp(self):
        self.db=db_fixture()

    def tearDown(self):
        self.db.close()

    def detail(self,item_id):
        rows=self.db.execute("""SELECT id,parameter_id,code,name,unit,value
          FROM hospital_lab_lines WHERE item_id=? ORDER BY id""",(item_id,)).fetchall()
        keys=("id","parameter_id","code","name","unit","value")
        return {"items":[{"id":item_id,"lines":[dict(zip(keys,row)) for row in rows]}]}

    def test_correct_original_gtt_without_new_billing_or_alp_active(self):
        snapshot=self.db.execute("SELECT COUNT(*),SUM(price) FROM hospital_lab_tests").fetchone()
        report=install(self.db)
        self.assertEqual(report["original_test"],"ROYAL-240")
        self.assertEqual(report["new_result_fields"],11)
        self.assertEqual(self.db.execute(
          "SELECT COUNT(*),SUM(price) FROM hospital_lab_tests").fetchone(),snapshot)
        self.assertEqual(self.db.execute(
          "SELECT active FROM hospital_lab_parameters WHERE id=973").fetchone()[0],0)
        fields=self.db.execute("""SELECT code,name,unit FROM hospital_lab_parameters
          WHERE test_id=240 AND active=1 ORDER BY sort_order,id""").fetchall()
        self.assertEqual([row[0] for row in fields],[PREFIX+f["key"] for f in FORM])
        self.assertEqual([row[1] for row in fields],[f["label"] for f in FORM])
        self.assertEqual(fields[3][2],"mg/dL")
        self.assertEqual(self.db.execute(
          "SELECT name,value FROM hospital_lab_lines WHERE item_id=1003").fetchone(),
          ("ALT","14"))

    def test_old_paid_blank_alp_transforms_into_right_input_screen(self):
        install(self.db)
        self.assertEqual(self.db.execute(
          "SELECT COUNT(*) FROM hospital_lab_lines WHERE item_id=1001").fetchone()[0],12)
        shown=overlay_order_detail(self.db,self.detail(1001))["items"][0]["lines"]
        self.assertEqual(len(shown),11)
        self.assertNotIn("ALP",[row["name"] for row in shown])
        self.assertEqual([row["name"] for row in shown],[f["label"] for f in FORM])
        self.assertEqual(len([x for x in shown
                              if x["royal_lab_field"]["kind"]=="select"]),4)
        urine=next(x for x in shown if x["code"]==PREFIX+"urine_one_hour")
        self.assertEqual(urine["royal_lab_field"]["options"],
                         ["Negative","Trace","+1","+2","+3","+4"])
        self.assertEqual(self.db.execute(
          "SELECT value FROM hospital_lab_lines WHERE id=3001").fetchone(),("",))
        self.assertEqual(self.db.execute(
          "SELECT result_status,result_version FROM hospital_order_items WHERE id=1001"
        ).fetchone(),("pending",0))
        # After valid lab result is entered, old ALP must NOT resurface.
        glucose=next(x for x in shown if x["code"]==PREFIX+"blood_fasting")
        self.db.execute("UPDATE hospital_lab_lines SET value='92' WHERE id=?",(glucose["id"],))
        self.db.execute("""UPDATE hospital_order_items SET result_version=1,
            result_status='draft' WHERE id=1001""")
        after=overlay_order_detail(self.db,self.detail(1001))["items"][0]["lines"]
        self.assertEqual(len(after),11)
        self.assertNotIn("ALP",[x["name"] for x in after])
        self.assertEqual(next(x for x in after if x["id"]==glucose["id"])["value"],"92")

    def test_existing_approved_alp_value_preserved_exactly(self):
        install(self.db)
        self.assertEqual(self.db.execute(
          "SELECT code,name,value FROM hospital_lab_lines WHERE id=3002").fetchone(),
          ("ROYAL_FMT_7777","ALP","55"))
        self.assertEqual(self.db.execute(
          "SELECT COUNT(*) FROM hospital_lab_lines WHERE item_id=1002").fetchone()[0],1)
        shown=overlay_order_detail(self.db,self.detail(1002))["items"][0]["lines"]
        self.assertEqual([(x["name"],x["value"]) for x in shown],[("ALP","55")])

    def test_restart_idempotent_no_duplicate_parameters_or_result_lines(self):
        install(self.db)
        ids=self.db.execute("""SELECT id FROM hospital_lab_parameters WHERE test_id=240
          AND code LIKE 'NOVA_GTT_%' ORDER BY id""").fetchall()
        line_count=self.db.execute(
          "SELECT COUNT(*) FROM hospital_lab_lines WHERE item_id=1001").fetchone()[0]
        install(self.db)
        self.assertEqual(ids,self.db.execute("""SELECT id FROM hospital_lab_parameters
          WHERE test_id=240 AND code LIKE 'NOVA_GTT_%' ORDER BY id""").fetchall())
        self.assertEqual(line_count,self.db.execute(
          "SELECT COUNT(*) FROM hospital_lab_lines WHERE item_id=1001").fetchone()[0])

    def test_result_validation_uses_existing_item_and_parameter_ids(self):
        install(self.db)
        fields=dict(self.db.execute("""SELECT code,id FROM hospital_lab_lines
          WHERE item_id=1001 AND code LIKE 'NOVA_GTT_%'""").fetchall())
        validate_save_payload(self.db,{"item_id":1001,"values":[
          {"line_id":fields[PREFIX+"blood_fasting"],"value":"99"},
          {"line_id":fields[PREFIX+"urine_fasting"],"value":"Trace"}]})
        for invalid in ("foo","NaN","Infinity","-2"):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                validate_save_payload(self.db,{"item_id":1001,"values":[
                  {"line_id":fields[PREFIX+"blood_fasting"],"value":invalid}]})
        with self.assertRaisesRegex(ValueError,"dropdown"):
            validate_save_payload(self.db,{"item_id":1001,"values":[
              {"line_id":fields[PREFIX+"urine_fasting"],"value":"Wrong"}]})
        with self.assertRaisesRegex(ValueError,"ALP"):
            validate_save_payload(self.db,{"item_id":1001,"values":[
              {"line_id":3001,"value":"1"}]})
        with self.assertRaisesRegex(ValueError,"does not belong"):
            validate_save_payload(self.db,{"item_id":1001,"values":[
              {"line_id":999999,"value":"5"}]})

    def test_unexpected_source_field_blocks_without_writing(self):
        self.db.execute("UPDATE hospital_lab_parameters SET name='CRP' WHERE id=973")
        with self.assertRaisesRegex(RuntimeError,"ALP source"):
            install(self.db)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM hospital_lab_parameters").fetchone()[0],2)

    def test_real_historical_nonblank_unapproved_is_not_migrated(self):
        self.db.execute("UPDATE hospital_lab_lines SET value='30' WHERE id=3001")
        install(self.db)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM hospital_lab_lines WHERE item_id=1001").fetchone()[0],1)
        shown=overlay_order_detail(self.db,self.detail(1001))["items"][0]["lines"]
        self.assertEqual([(x["name"],x["value"]) for x in shown],[("ALP","30")])


if __name__=="__main__":
    unittest.main()
