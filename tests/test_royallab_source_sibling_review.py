"""Pinned Royal Lab real-source checks: sibling evidence never merges tests.

All SQLite databases are disposable, no patient/order databases or prices read.
"""
import collections
import sqlite3
import unittest

from hospital.royallab_catalog_audit import SOURCE
from hospital.royallab_native_catalog_store import install_file, test_form
from hospital.royallab_clinical_template_review import review_suggestion
from hospital.royallab_source_sibling_review import (
    sibling_review_options, SIBLING_REFERENCES)
from hospital.royallab_native_form_html import render_form


class SourceSiblingEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db=sqlite3.connect(":memory:")
        cls.cid=install_file(cls.db,SOURCE)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_vitamin_d_source_sibling_is_visible_but_not_auto_adopted(self):
        target=test_form(self.db,self.cid,"368")
        self.assertEqual(target["fields"],[])
        refs=sibling_review_options(self.db,self.cid,"368")
        self.assertEqual(len(refs),1)
        self.assertEqual(refs[0]["related_source_test_id"],"316")
        self.assertGreater(refs[0]["source_field_count"],0)
        self.assertFalse(refs[0]["ready_for_patient_results"])
        self.assertFalse(refs[0]["can_auto_import_to_target"])
        self.assertFalse(refs[0]["same_test_identity"])
        self.assertEqual(test_form(self.db,self.cid,"368")["fields"],[])
        reviewed=review_suggestion(self.db,self.cid,"368")
        self.assertEqual(reviewed["related_source_forms"][0]["related_source_test_id"],"316")
        self.assertTrue(reviewed["requires_independent_approval"])
        self.assertFalse(reviewed["ready_for_patient_results"])

    def test_five_part_cbc_uses_five_diff_not_legacy_three_diff(self):
        refs=sibling_review_options(self.db,self.cid,"320")
        self.assertEqual([x["related_source_test_id"] for x in refs],["101"])
        self.assertGreaterEqual(refs[0]["source_field_count"],20)
        self.assertNotEqual(refs[0]["related_source_test_id"],"21")
        self.assertTrue(all(not f["source_proven_for_target"] for f in refs[0]["fields"]))

    def test_typhoid_ict_is_not_widal_test(self):
        refs=sibling_review_options(self.db,self.cid,"347")
        self.assertEqual([x["related_source_test_id"] for x in refs],["309"])
        self.assertNotIn("115",[x["related_source_test_id"] for x in refs])
        self.assertTrue(all(not x["can_auto_import_to_target"] for x in refs))

    def test_cholera_subcomponents_never_merge_parent_identity(self):
        for test_id in ("288","289","291"):
            with self.subTest(test_id=test_id):
                refs=sibling_review_options(self.db,self.cid,test_id)
                self.assertEqual(refs[0]["related_source_test_id"],"292")
                self.assertEqual(refs[0]["relation"],"possible_parent_components")
                self.assertFalse(refs[0]["same_test_identity"])

    def test_hcv_sources_are_disclosed_as_method_dependent(self):
        refs=sibling_review_options(self.db,self.cid,"336")
        self.assertEqual(refs[0]["related_source_test_id"],"337")
        self.assertIn("genotyping",refs[0]["method_warning"])
        self.assertFalse(refs[0]["ready_for_patient_results"])

    def test_unmapped_unknown_and_unproven_fields_do_not_infer(self):
        self.assertEqual(sibling_review_options(self.db,self.cid,"339"),[])
        self.assertEqual(sibling_review_options(self.db,self.cid,"0"),[])
        self.assertEqual(test_form(self.db,self.cid,"391")["fields"],[])
        for key in SIBLING_REFERENCES:
            for related in sibling_review_options(self.db,self.cid,key):
                self.assertFalse(related["can_auto_import_to_target"])
                for field in related["fields"]:
                    self.assertFalse(field["target_can_save_results"])
                    self.assertFalse(field["source_proven_for_target"])

    def test_original_multi_format_fields_remain_individually_addressed(self):
        # Urine microscopy contains original analytes with multiple formats.
        # Never flatten its controls into one arbitrary dropdown.
        form=test_form(self.db,self.cid,"7")
        groups=collections.defaultdict(list)
        for field in form["fields"]:
            groups[field["source_analyte_id"]].append(field["source_format_id"])
        multiple=[ids for ids in groups.values() if len(ids)>1]
        self.assertGreater(len(multiple),0)
        for ids in multiple:
            self.assertEqual(len(ids),len(set(ids)))
        html=render_form(form)
        for identity in multiple[0]:
            self.assertIn('data-source-format-id="'+identity+'"',html)


if __name__=="__main__":
    unittest.main()
