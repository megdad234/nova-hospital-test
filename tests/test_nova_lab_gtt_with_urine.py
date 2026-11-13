"""Photographed Al Sharq GTT/urine glucose form: no guessed clinical values.

Covers the real NOVA local authoring path using an isolated synthetic database.
Never reads patient records or changes the original Royal Lab catalogue.
"""
import importlib.util
import pathlib
import sqlite3
import unittest

from hospital import nova_lab_local_tests as local

HERE = pathlib.Path(__file__).resolve().parents[1]
LAB = {"id": 11, "role": "lab"}
ADMIN = {"id": 22, "role": "admin"}
OTHER_ADMIN = {"id": 33, "role": "admin"}


class GTTTemplateTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("""
        CREATE TABLE hospital_lab_tests (
          id INTEGER PRIMARY KEY,code TEXT UNIQUE,name TEXT,
          category TEXT DEFAULT 'Other',price INTEGER,active INTEGER DEFAULT 1);
        CREATE TABLE hospital_lab_parameters (
          id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,name TEXT,unit TEXT,
          reference_all TEXT,sort_order INTEGER,active INTEGER DEFAULT 1);
        CREATE TABLE hospital_orders(id INTEGER PRIMARY KEY,status TEXT);
        CREATE TABLE hospital_order_items(
          id INTEGER PRIMARY KEY,test_id INTEGER,order_id INTEGER);
        CREATE TABLE hospital_lab_lines(
          id INTEGER PRIMARY KEY,item_id INTEGER,code TEXT,name TEXT,unit TEXT,value TEXT);
        INSERT INTO hospital_lab_tests(code,name,category,price)
          VALUES('ROYAL-352','Blood Sugar Curve','Chemistry',1);
        """)
        self.template = local.gtt_urine_template()

    def tearDown(self):
        self.db.close()

    def propose(self, actor=LAB):
        return local.propose(
            self.db, actor, name=self.template["name"],
            section=self.template["section"],
            price=12000, fields=self.template["fields"],
            method="Lab-confirmed protocol with fasting, one-hour, two-hour samples",
            evidence="Synthetic manufacturer IFU for CI test only; replace with actual local kit reference",
            rationale="Distinct GTT with concurrent urine glucose documented in user's local laboratory form",
        )

    def test_exact_three_time_points_and_both_specimen_types(self):
        t = self.template
        self.assertEqual(t["template_id"], "gtt-urine-0-1-2h")
        self.assertEqual(t["section"], "Chemistry")
        self.assertIn("GTT", t["name"])
        self.assertEqual(len(t["fields"]), 11)
        self.assertEqual([f["key"] for f in t["fields"]], [
            "glucose_load", "specimen", "method_recorded",
            "blood_fasting", "urine_fasting",
            "blood_one_hour", "urine_one_hour",
            "blood_two_hours", "urine_two_hours",
            "interpretation", "comments",
        ])
        for idx in (3, 5, 7):
            f = t["fields"][idx]
            self.assertEqual(f["kind"], "number")
            self.assertEqual(f["unit"], "mg/dL")
            self.assertEqual(f["options"], [])
        for idx in (4, 6, 8):
            f = t["fields"][idx]
            self.assertEqual(f["kind"], "select")
            self.assertEqual(f["options"],
                             ["Negative", "Trace", "+1", "+2", "+3", "+4"])
        self.assertEqual(t["fields"][1]["options"], ["Plasma", "Serum"])
        self.assertTrue(all(f["key"] != "patient_name" for f in t["fields"]))

    def test_no_guessed_price_load_reference_threshold_or_assay(self):
        self.assertIsNone(self.template["price"])
        self.assertEqual(self.template["method"], "")
        self.assertEqual(self.template["evidence"], "")
        self.assertFalse(self.template["ready_for_patient_results"])
        self.assertFalse(self.template["reference_ranges_verified"])
        self.assertEqual(self.template["state"], "suggestion_only")
        self.assertTrue(all(f["reference"] == "" and f["reference_source"] == ""
                            for f in self.template["fields"]))
        self.assertTrue(all(f["required"] is False for f in self.template["fields"]))
        with self.assertRaises(ValueError):
            local.propose(self.db, LAB, name=self.template["name"], section="Chemistry",
                          price=self.template["price"], fields=self.template["fields"],
                          method="method", evidence="real kit verification required",
                          rationale="Separate clinical review needed")

    def test_approval_creates_one_separate_local_test_not_royal_sugar_curve(self):
        p = self.propose()
        self.assertEqual(p["state"], "pending")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM hospital_lab_tests").fetchone()[0], 1)
        with self.assertRaises(PermissionError):
            local.approve(self.db, LAB, p["proposal_id"], p["form_hash"],
                          attestation="I reviewed the actual local method")
        approved = local.approve(
            self.db, ADMIN, p["proposal_id"], p["form_hash"],
            attestation="Independent local-method verification completed by approver")
        self.assertEqual(approved["state"], "approved")
        self.assertTrue(approved["code"].startswith("NOVA-LOCAL-"))
        self.assertEqual(self.db.execute("SELECT name,category,price FROM hospital_lab_tests WHERE id=?",
                                         (approved["nova_test_id"],)).fetchone(),
                         (self.template["name"], "Chemistry", 12000))
        self.assertEqual(self.db.execute("SELECT name,category,price FROM hospital_lab_tests WHERE code='ROYAL-352'"
                                         ).fetchone(), ("Blood Sugar Curve", "Chemistry", 1))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM hospital_lab_parameters WHERE test_id=?",
                                         (approved["nova_test_id"],)).fetchone()[0], 11)
        options = self.db.execute(
            "SELECT kind,options_json FROM nova_lab_local_fields WHERE key='urine_two_hours'"
        ).fetchone()
        self.assertEqual(options[0], "select")
        self.assertIn('"Trace"', options[1])

    def test_cannot_create_duplicate_while_pending_or_after_approval(self):
        pending = self.propose()
        with self.assertRaisesRegex(ValueError, "already exists or awaits"):
            self.propose()
        local.approve(self.db, ADMIN, pending["proposal_id"], pending["form_hash"],
                      attestation="Independent local-method verification completed by approver")
        with self.assertRaisesRegex(ValueError, "already exists or awaits"):
            self.propose()

    def test_existing_clinical_result_validation_is_reused(self):
        p = self.propose()
        approved = local.approve(self.db, ADMIN, p["proposal_id"], p["form_hash"],
                     attestation="Independent local-method verification completed by approver")
        test_id = approved["nova_test_id"]
        self.db.execute("INSERT INTO hospital_orders(id,status) VALUES(500,'paid')")
        self.db.execute("INSERT INTO hospital_order_items(id,test_id,order_id) VALUES(501,?,500)",
                        (test_id,))
        params = self.db.execute(
            "SELECT code,name FROM hospital_lab_parameters WHERE test_id=? ORDER BY sort_order",
            (test_id,)).fetchall()
        for line_id,(code,name) in enumerate(params,1):
            self.db.execute("INSERT INTO hospital_lab_lines(id,item_id,code,name,unit,value)"
                            " VALUES(?,501,?,?,'','')", (line_id, code, name))
        with self.assertRaisesRegex(ValueError, "Numeric"):
            local.validate_save_payload(self.db, {"item_id":501,
                "values":[{"line_id":4, "value":"high"}]})
        with self.assertRaisesRegex(ValueError, "dropdown"):
            local.validate_save_payload(self.db, {"item_id":501,
                "values":[{"line_id":5, "value":"Not a documented result"}]})
        local.validate_save_payload(self.db, {"item_id":501,
            "values":[{"line_id":4, "value":"91"},
                      {"line_id":5, "value":"Trace"},
                      {"line_id":6, "value":"130"},
                      {"line_id":7, "value":"+1"}]})
        with self.assertRaises(ValueError):
            self.propose()

    def test_existing_nova_gateway_get_and_post_are_not_interchanged(self):
        path=HERE/".github/ci/royallab_native_gateway_patch.py"
        spec=importlib.util.spec_from_file_location("royallab_native_gateway_patch_gtt",path)
        m=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        self.assertIn("/local/templates/gtt-urine",m.ROUTES)
        self.assertIn("nova_lab_local_tests.gtt_urine_template()",m.ROUTES)
        self.assertIn("/local/tests",m.ROUTES)
        self.assertIn("/local/proposals",m.ROUTES)
        self.assertIn("/local/form/",m.ROUTES)
        self.assertNotIn("/local/templates/gtt-urine",m.POST_ROUTES)
        self.assertNotIn("/local/tests",m.POST_ROUTES)
        self.assertIn("/local/propose",m.POST_ROUTES)
        self.assertIn("/local/approve",m.POST_ROUTES)
        self.assertIn("core.require_role(role,'admin','lab')",m.ROUTES)

    def test_real_frontend_button_only_prefills_existing_local_editor(self):
        js=(HERE/"hospital/static/royallab-native-picker.js").read_text(encoding="utf-8")
        self.assertIn("تهيئة فحص GTT مع سكر البول",js)
        self.assertIn("fetchJson('/local/templates/gtt-urine')",js)
        self.assertIn("suggestion.ready_for_patient_results !== false",js)
        self.assertIn("for (const field of suggestion.fields) makeField(field)",js)
        self.assertIn("price.value = '';",js)
        self.assertIn("method.value = '';",js)
        self.assertIn("evidence.value = '';",js)
        self.assertIn("المقترح لاعتماد مراجع مستقل",js)
        self.assertNotIn("GTT_URINE_RESULT_DEFAULT",js)

if __name__=="__main__":
    unittest.main()
