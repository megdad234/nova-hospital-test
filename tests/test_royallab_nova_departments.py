"""Validate original Royal Lab department provenance against every real source test.

These tests use only a read-only original source JSON and disposable state.
No patient records, prices, pharmacy receipts or clinical result definitions.
"""
import json
import unittest

from hospital.royallab_catalog_audit import SOURCE
from hospital.royallab_native_result_form import native_catalog
from hospital.royallab_nova_departments import (
    ORIGINAL_LAB_GROUPS, DISPLAY_DEPARTMENTS, NON_LAB_LABEL,
    UNKNOWN_LABEL, for_source_test, verify_original_departments)


class OriginalRoyalLabDepartmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        library=json.loads(SOURCE.read_text(encoding="utf-8-sig"))
        cls.catalog=native_catalog(library)
        cls.by_id={str(t["source_test_id"]):t for t in cls.catalog["tests"]}

    def test_all_367_original_tests_have_audited_department_ids(self):
        r=verify_original_departments(self.catalog)
        self.assertEqual(r["test_count"],367)
        self.assertEqual(r["unknown"],0)
        self.assertGreater(r["clinical_groups"],5)
        self.assertTrue(r["non_lab_services_retained"]>0)
        self.assertTrue(all(str(t.get("source_department_id")) in ORIGINAL_LAB_GROUPS
                            for t in self.catalog["tests"]))

    def test_nova_clinical_categories_are_semantically_correct(self):
        expected={"7":"التحاليل العامة والطفيليات",
                  "8":"التحاليل العامة والطفيليات",
                  "13":"التحاليل العامة والطفيليات",
                  "21":"أمراض الدم والتخثر",
                  "101":"أمراض الدم والتخثر",
                  "36":"الهرمونات",
                  "40":"المناعة",
                  "77":"المزارع والأحياء الدقيقة",
                  "287":"الأحياء الدقيقة والسيرولوجيا",
                  "320":"التحاليل العامة والطفيليات" if
                        str(self.by_id["320"]["source_department_id"])=="2"
                        else for_source_test(self.by_id["320"])["category"],
                  "108":"بنك الدم"}
        for source_id,label in expected.items():
            with self.subTest(source_id=source_id):
                self.assertEqual(for_source_test(self.by_id[source_id])["category"],label)

    def test_known_original_group_labels_are_not_used_as_false_categories(self):
        cbc=for_source_test(self.by_id["21"])
        self.assertEqual(cbc["source_department_id"],"3")
        self.assertEqual(cbc["original_department_name"],"1 h.pp")
        self.assertEqual(cbc["category"],"أمراض الدم والتخثر")
        urine=for_source_test(self.by_id["7"])
        self.assertEqual(urine["original_department_name"],"Renal Function Test(RFT)")
        self.assertNotEqual(urine["category"],"Renal Function Test(RFT)")
        surgery=for_source_test(self.by_id["190"])
        self.assertEqual(surgery["source_department_id"],"21")
        self.assertEqual(surgery["original_department_name"],"CBC")
        self.assertEqual(surgery["category"],NON_LAB_LABEL)

    def test_not_a_single_source_test_remains_in_generic_other(self):
        labels={for_source_test(t)["category"] for t in self.catalog["tests"]}
        self.assertNotIn("Other",labels)
        self.assertNotIn("",labels)
        self.assertNotIn(UNKNOWN_LABEL,labels)
        self.assertIn("الهرمونات",labels)
        self.assertIn("المناعة",labels)
        self.assertIn("بنك الدم",labels)
        self.assertIn("الأحياء الجزيئية",labels)
        self.assertGreaterEqual(len(labels),8)

    def test_malformed_department_does_not_infer_from_name(self):
        bad={**self.by_id["21"],"source_department_id":"9999"}
        self.assertEqual(for_source_test(bad)["category"],UNKNOWN_LABEL)
        self.assertEqual(for_source_test(bad)["assignment_kind"],"unrecognized_source_group")
        with self.assertRaisesRegex(ValueError,"Unknown Royal Lab source group"):
            verify_original_departments({
                "tests":[bad]+[t for t in self.catalog["tests"] if t is not self.by_id["21"]]
            })

if __name__=="__main__":
    unittest.main()
