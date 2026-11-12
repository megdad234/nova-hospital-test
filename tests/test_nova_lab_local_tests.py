"""Regression coverage for local NOVA tests; all records synthetic and in-memory."""
import json
import sqlite3
import unittest

from hospital import nova_lab_local_tests as local

LAB={"id":101,"role":"lab"}
ADMIN={"id":202,"role":"admin"}
OTHER_ADMIN={"id":303,"role":"admin"}
FIELDS=[
    {"key":"value","label":"Value result","kind":"number","unit":"mg/L",
     "reference":"","reference_source":""},
    {"key":"answer","label":"Screening result","kind":"select",
     "options":["Nonreactive","Reactive"],"unit":"","reference":"",
     "reference_source":""},
    {"key":"note","label":"Observation","kind":"text","unit":""},
]
NOTES={"method":"Documented local assay manufacturer method",
       "evidence":"Laboratory approved kit IFU revision 2026",
       "rationale":"Add an independently verified local test form"}


class NOVALocalTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.executescript("""
        CREATE TABLE hospital_lab_tests(
          id INTEGER PRIMARY KEY,code TEXT UNIQUE,name TEXT,category TEXT NOT NULL DEFAULT 'Other',price REAL,active INTEGER DEFAULT 1);
        CREATE TABLE hospital_lab_parameters(
          id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,name TEXT,unit TEXT,active INTEGER DEFAULT 1);
        CREATE TABLE hospital_orders(id INTEGER PRIMARY KEY,status TEXT);
        CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,test_id INTEGER,order_id INTEGER);
        CREATE TABLE hospital_lab_lines(
          id INTEGER PRIMARY KEY,item_id INTEGER,code TEXT,name TEXT,unit TEXT,value TEXT);
        INSERT INTO hospital_lab_tests(code,name,price) VALUES('OLD-NOVA','Old',100);
        """)
    def tearDown(self):
        self.db.close()
    def propose(self, actor=LAB, fields=None, local_id=None):
        return local.propose(self.db,actor,local_id=local_id,
          name="Test for NOVA",section="Biochemistry",price=1500,
          fields=FIELDS if fields is None else fields,**NOTES)
    def approve(self, proposal,actor=ADMIN):
        return local.approve(self.db,actor,proposal["proposal_id"],proposal["form_hash"],
                             attestation="I independently checked the laboratory kit method")
    def create(self):
        p=self.propose()
        return self.approve(p)

    def test_full_new_test_lifecycle_in_actual_nova_tables(self):
        p=self.propose()
        self.assertEqual(p["state"],"pending")
        self.assertEqual(local.list_local(self.db),[])
        data=self.approve(p)
        self.assertEqual(data["revision"],1)
        self.assertTrue(data["code"].startswith("NOVA-LOCAL-"))
        one=local.local_form(self.db,data["local_id"])
        self.assertEqual(len(one["fields"]),3)
        self.assertEqual(one["fields"][1]["options"],["Nonreactive","Reactive"])
        self.assertEqual(one["section"],"Biochemistry")
        rows=self.db.execute("""SELECT code,name,price,active,category FROM hospital_lab_tests
                    WHERE id=?""",(data["nova_test_id"],)).fetchone()
        self.assertEqual(rows,(data["code"],"Test for NOVA",1500,1,"Biochemistry"))
        self.assertEqual(self.db.execute("""SELECT COUNT(*) FROM hospital_lab_parameters
                       WHERE test_id=? AND active=1""",(data["nova_test_id"],)).fetchone()[0],3)
        self.assertEqual(len(local.list_local(self.db)),1)
        self.assertEqual(local.proposals(self.db)[0]["state"],"approved")

    def test_approver_must_be_another_user_and_admin(self):
        p=self.propose(actor=ADMIN)
        with self.assertRaises(PermissionError):self.approve(p,ADMIN)
        with self.assertRaises(PermissionError):self.approve(p,LAB)
        self.assertEqual(self.approve(p,OTHER_ADMIN)["revision"],1)
        with self.assertRaises(ValueError):self.approve(p,OTHER_ADMIN)

    def test_unsafe_choice_ranges_and_price_are_rejected(self):
        for fields in [
          [{**FIELDS[1],"options":[]}],
          [{**FIELDS[1],"options":["Positive","positive"]}],
          [{**FIELDS[0],"reference":"0 to 99"}],
          [{**FIELDS[0],"key":"test!bad"}],
        ]:
            with self.subTest(fields=fields),self.assertRaises(ValueError):
                self.propose(fields=fields)
        with self.assertRaises(ValueError):
            local.propose(self.db,LAB,name="X",section="Biochemistry",price=0,
                          fields=FIELDS,**NOTES)
        with self.assertRaises(ValueError):
            local.propose(self.db,LAB,name="Test",section="Biochemistry",price="12.5",
                          fields=FIELDS,**NOTES)
        with self.assertRaises(PermissionError):
            self.propose(actor={"id":77,"role":"pharmacy"})

    def test_edit_before_first_order_preserves_identity(self):
        item=self.create()
        p=self.propose(local_id=item["local_id"],fields=[
           {**FIELDS[0],"unit":"mmol/L"},
           FIELDS[1]
        ])
        updated=self.approve(p)
        self.assertEqual(updated["nova_test_id"],item["nova_test_id"])
        self.assertEqual(updated["revision"],2)
        self.assertEqual(self.db.execute("SELECT category FROM hospital_lab_tests WHERE id=?",
                          (item["nova_test_id"],)).fetchone()[0],"Biochemistry")
        self.assertEqual(self.db.execute("""SELECT COUNT(*) FROM hospital_lab_parameters
                     WHERE test_id=? AND active=1""",(item["nova_test_id"],)).fetchone()[0],2)
        self.assertEqual(local.local_form(self.db,item["local_id"])["fields"][0]["unit"],"mmol/L")

    def test_historical_orders_freeze_template_and_price_changes(self):
        item=self.create()
        self.db.execute("INSERT INTO hospital_orders VALUES(1,'paid')")
        self.db.execute("INSERT INTO hospital_order_items VALUES(22,?,1)",
                        (item["nova_test_id"],))
        with self.assertRaisesRegex(ValueError,"historical orders"):
            self.propose(local_id=item["local_id"])
        self.assertTrue(local.local_form(self.db,item["local_id"])["has_orders"])

    def test_second_review_rechecks_no_order_race(self):
        item=self.create()
        p=self.propose(local_id=item["local_id"])
        self.db.execute("INSERT INTO hospital_orders VALUES(1,'paid')")
        self.db.execute("INSERT INTO hospital_order_items VALUES(22,?,1)",
                        (item["nova_test_id"],))
        with self.assertRaisesRegex(ValueError,"orders"):
            self.approve(p)
        self.assertEqual(local.proposals(self.db)[0]["state"],"pending")

    def test_only_local_approved_tests_reenabled_after_original_catalog_refresh(self):
        item=self.create()
        self.db.execute("UPDATE hospital_lab_tests SET active=0")
        self.assertEqual(local.restore_active(self.db),1)
        self.assertEqual(self.db.execute("""SELECT active FROM hospital_lab_tests
                     WHERE code='OLD-NOVA'""").fetchone()[0],0)
        self.assertEqual(self.db.execute("""SELECT active FROM hospital_lab_tests
                     WHERE id=?""",(item["nova_test_id"],)).fetchone()[0],1)

    def test_existing_nova_order_result_types_enriched_without_altering_other_tests(self):
        item=self.create()
        tid=item["nova_test_id"]
        self.db.execute("INSERT INTO hospital_orders VALUES(1,'paid')")
        self.db.execute("INSERT INTO hospital_order_items VALUES(22,?,1)",(tid,))
        self.db.execute("INSERT INTO hospital_order_items VALUES(23,1,1)")
        codes=list(self.db.execute("""SELECT code FROM hospital_lab_parameters
                                          WHERE test_id=? ORDER BY id""",(tid,)))
        detail={"items":[{"id":22,"lines":[{"id":101,"code":x[0],"value":""}
                  for x in codes]},{"id":23,"lines":[{"id":201,"code":"OLD","value":""}]}]}
        out=local.overlay_order_detail(self.db,detail)
        kinds=[x["royal_lab_field"]["kind"] for x in out["items"][0]["lines"]]
        self.assertEqual(kinds,["number","select","text"])
        self.assertEqual(out["items"][0]["lines"][1]["royal_lab_field"]["options"],
                         ["Nonreactive","Reactive"])
        self.assertNotIn("royal_lab_field",out["items"][1]["lines"][0])
        self.assertNotIn("royal_lab_field",detail["items"][0]["lines"][0])

    def test_original_nova_save_rejects_invalid_dropdown_and_numeric(self):
        item=self.create()
        tid=item["nova_test_id"]
        self.db.execute("INSERT INTO hospital_orders VALUES(1,'paid')")
        self.db.execute("INSERT INTO hospital_order_items VALUES(22,?,1)",(tid,))
        codes=list(self.db.execute("""SELECT code FROM hospital_lab_parameters
                                  WHERE test_id=? ORDER BY id""",(tid,)))
        for index,(code,) in enumerate(codes,101):
            self.db.execute("""INSERT INTO hospital_lab_lines(id,item_id,code,name,unit,value)
                               VALUES(?,22,?,'Result','','')""",(index,code))
        base={"item_id":22,"values":[{"line_id":102,"value":"No"}]}
        with self.assertRaisesRegex(ValueError,"dropdown"):
            local.validate_save_payload(self.db,base)
        with self.assertRaisesRegex(ValueError,"Numeric"):
            local.validate_save_payload(self.db,{"item_id":22,
                    "values":[{"line_id":101,"value":"oops"}]})
        local.validate_save_payload(self.db,{"item_id":22,
                "values":[{"line_id":101,"value":"12.5"},
                          {"line_id":102,"value":"Reactive"}]})
        with self.assertRaisesRegex(ValueError,"does not belong"):
            local.validate_save_payload(self.db,{"item_id":22,
                "values":[{"line_id":987654,"value":"Reactive"}]})

    def test_tampering_and_nonexistent_id_are_rejected(self):
        item=self.create()
        self.db.execute("""UPDATE nova_lab_local_tests SET approved_form_json='{}'
                    WHERE id=?""",(item["local_id"],))
        with self.assertRaisesRegex(ValueError,"modified"):
            local.local_form(self.db,item["local_id"])
        with self.assertRaises(KeyError):
            local.local_form(self.db,55555)

if __name__=="__main__":
    unittest.main()
