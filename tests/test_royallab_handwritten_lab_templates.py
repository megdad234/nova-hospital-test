"""Handwritten lab worksheet: source-grounded readiness, method-gated templates.

Never auto-copy source sibling tests or publish kit-dependent values.
No patient data, prices, report templates or pharmacy are modified.
"""
import copy
import json
import pathlib
import sqlite3
import subprocess
import unittest
from unittest.mock import patch

from hospital.royallab_catalog_audit import SOURCE
from hospital.royallab_native_result_form import native_catalog
from hospital.royallab_nova_handwritten_lab_templates import (
    review_method_variants, review_variant_candidates, brucella_ict_local_templates)
from hospital.nova_lab_local_tests import _fields
from hospital.royallab_clinical_template_review import review_suggestion

ROOT = pathlib.Path(__file__).resolve().parents[1]


class HandwrittenSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = native_catalog(json.loads(SOURCE.read_text(encoding="utf-8-sig")))
        cls.byid = {x["source_test_id"]: x for x in cls.source["tests"]}

    def test_existing_qualitative_assays_remain_in_unchanged_original_forms(self):
        names = {
            "88":"HCG(Urine)", "314":"HCG Serum", "318":"HCG Serum",
            "59":"VDRL", "248":"ICT for HIV",
            "249":"ICT for HCV", "250":"ICT for HBsAg",
        }
        for id_, name in names.items():
            with self.subTest(id=id_):
                test=self.byid[id_]
                self.assertEqual(test["name"], name)
                self.assertEqual(len([f for f in test["fields"] if
                                      f.get("active") not in (False,0,"False")]),1)
                field=next(f for f in test["fields"] if
                           f.get("active") not in (False,0,"False"))
                self.assertGreaterEqual(len([o for o in field["options"]
                    if o.get("active") not in (False,0,"False") and o["label"].strip()]),2)
                self.assertEqual(review_method_variants(id_),[])

    def test_tft_all_five_original_numeric_fields_and_vitamin_d_separation(self):
        tft=self.byid["38"]
        active=[f for f in tft["fields"] if f.get("active") not in
                (False,0,"False","false","0")]
        self.assertEqual([f["label"] for f in active],
                         ["Serum T3","Serum T4","Serum TSH","Serum Free T3","Serum Free T4"])
        self.assertTrue(all(f["kind"]=="number" for f in active))
        vitamin_d=self.byid["316"]
        self.assertEqual(vitamin_d["name"],"Vitamin D")
        self.assertEqual(len(vitamin_d["fields"]),1)
        self.assertEqual(vitamin_d["fields"][0]["kind"],"number")
        self.assertEqual(vitamin_d["fields"][0]["unit"].lower(),"ng/ml")
        self.assertEqual(self.byid["368"]["fields"],[])
        self.assertTrue(all(not f["unit"] and not f["reference"] for v in
            review_method_variants("368") for f in v["fields"]))
        self.assertEqual(review_method_variants("316"),[])

    def test_original_widal_vs_missing_brucella_ict_and_dengue_crp_formats(self):
        widal=self.byid["58"]
        self.assertEqual(widal["name"],"Widal Test for Brucella")
        self.assertEqual(len([f for f in widal["fields"] if f.get("active")
                              not in (False,0,"False")]),3)
        self.assertFalse(any("ICT for Brucella" in t["name"] for t in self.byid.values()))
        self.assertEqual(self.byid["369"]["fields"],[])
        self.assertEqual(len(self.byid["251"]["fields"]),2)
        self.assertTrue(all(f["kind"]=="select" for f in self.byid["251"]["fields"]))
        self.assertEqual(len(self.byid["317"]["fields"]),1)
        standalone=self.byid["317"]["fields"][0]
        self.assertEqual(standalone["label"],"C.Reactive Protien")
        self.assertEqual(standalone["types"],[])
        self.assertFalse(standalone["options"])
        self.assertEqual(review_method_variants("58"),[])
        self.assertEqual(review_method_variants("251"),[])

    def test_kit_alternatives_are_independent_unapproved_and_no_ranges(self):
        expected={
            "317": [("crp-qualitative-latex",1),("crp-quantitative-mg-l",1)],
            "369": [("dengue-ns1-only",1),("dengue-igm-igg",2),
                    ("dengue-combined",3)],
            "368": [("vitamin-d-25oh",1),("vitamin-d-125oh",1)],
        }
        for tid,ids in expected.items():
            variants=review_method_variants(tid)
            self.assertEqual([(v["variant_id"],len(v["fields"])) for v in variants],ids)
            for v in variants:
                self.assertFalse(v["source_proven"])
                self.assertFalse(v["ready_for_patient_results"])
                self.assertTrue(v["requires_independent_approval"])
                self.assertTrue(v["requires_kit_and_method_verification"])
                for f in v["fields"]:
                    self.assertEqual(f["reference"],"")
                    self.assertEqual(f["reference_source"],"")
                    self.assertFalse(f["required"])
            mapped=review_variant_candidates(tid)
            self.assertTrue(all(f["source_proven"] is False for v in mapped
                                for f in v["fields"]))
            self.assertEqual([len(v["fields"]) for v in mapped],
                             [x[1] for x in ids])
        crp=review_method_variants("317")
        self.assertEqual(crp[0]["fields"][0]["options"],["Positive","Negative"])
        self.assertEqual(crp[1]["fields"][0]["kind"],"number")
        self.assertEqual(crp[1]["fields"][0]["unit"],"mg/L")
        dengue=review_method_variants("369")
        self.assertEqual([f["label"] for f in dengue[-1]["fields"]],
                         ["NS1 Ag","Dengue IgM","Dengue IgG"])
        self.assertEqual(review_method_variants("59"),[])
        self.assertEqual(review_method_variants("248"),[])

    def test_brucella_local_editor_templates_not_live_tests_or_widal_copies(self):
        original=brucella_ict_local_templates()
        self.assertEqual(original["state"],"suggestion_only")
        self.assertFalse(original["ready_for_patient_results"])
        self.assertIsNone(original["price"])
        self.assertEqual(original["must_not_replace_source_test_id"],"58")
        self.assertEqual(len(original["variants"]),2)
        self.assertEqual([len(v["fields"]) for v in original["variants"]],[1,2])
        for variant in original["variants"]:
            self.assertFalse(variant["source_proven"])
            self.assertFalse(variant["ready_for_patient_results"])
            self.assertTrue(variant["requires_independent_approval"])
            self.assertEqual(_fields(variant["fields"]),
                             [{**field,"required":False}
                              for field in _fields(variant["fields"])])
            for field in variant["fields"]:
                self.assertEqual(field["options"],["Positive","Negative"])
                self.assertEqual(field["reference"],"")
                self.assertEqual(field["unit"],"")
        original["variants"][0]["fields"][0]["options"][0]="WRONG"
        self.assertEqual(brucella_ict_local_templates()["variants"][0]
                         ["fields"][0]["options"][0],"Positive")

    def test_review_suggestion_never_prefills_undocumented_crp_or_dengue_fields(self):
        for tid in ("317","369","368"):
            original=copy.deepcopy(self.byid[tid])
            with sqlite3.connect(":memory:") as db, \
                 patch("hospital.royallab_clinical_template_review._source",
                       return_value=original), \
                 patch("hospital.royallab_native_catalog_store.effective_source_form",
                       return_value=original), \
                 patch("hospital.royallab_source_sibling_review.sibling_review_options",
                       return_value=[]):
                suggestion=review_suggestion(db,1,tid)
            self.assertEqual(suggestion["source_test_id"],tid)
            # Keep the pre-existing unapproved vitamin-D hint for reviewer
            # compatibility; method alternatives are new, not replacements.
            self.assertEqual(len(suggestion["fields"]),1 if tid=="368" else 0)
            self.assertTrue(all(f["source_proven"] is False
                                for f in suggestion["fields"]))
            self.assertFalse(suggestion["ready_for_patient_results"])
            self.assertTrue(suggestion["requires_independent_approval"])
            self.assertGreaterEqual(len(suggestion["method_variants"]),2)
            self.assertTrue(any("method" in w.lower() or "format" in w.lower()
                                for w in suggestion["warnings"]))
            self.assertTrue(all(v["source_proven"] is False for v
                                in suggestion["method_variants"]))

    def test_ui_and_gateway_expose_only_drafts_not_patient_save_endpoints(self):
        picker=(ROOT/"hospital/static/royallab-native-picker.js").read_text(
            encoding="utf-8")
        gateway=(ROOT/".github/ci/royallab_native_gateway_patch.py").read_text(
            encoding="utf-8")
        self.assertIn("/local/templates/ict-brucella",gateway)
        self.assertIn("brucella_ict_local_templates()",gateway)
        self.assertIn("core.require_role(role,'admin','lab')",gateway)
        self.assertIn("methodVariantPanel",picker)
        self.assertIn("renderMethodVariants(result,selected)",picker)
        self.assertIn("template.ready_for_patient_results !== false",picker)
        self.assertIn("variant.requires_independent_approval !== true",picker)
        self.assertIn("proposalFields.querySelector('fieldset')",picker)
        self.assertIn("localTests.some(t =>",picker)
        self.assertNotIn("api('lab/values'",gateway)
        result=subprocess.run(["node","--check",str(ROOT/
            "hospital/static/royallab-native-picker.js")],
            capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=="__main__":
    unittest.main()
