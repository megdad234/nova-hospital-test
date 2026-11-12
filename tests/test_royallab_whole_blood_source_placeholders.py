"""Real RoyalLab source test 108 has empty analytes without any result format.

Do not fabricate blood-bank results. Exclude only literal empty/no-format
placeholder rows; retain all original records and meaningful fields.
"""
import sqlite3
import unittest
from hospital.royallab_catalog_audit import SOURCE
from hospital.royallab_native_catalog_store import install_file,test_form,clinical_test_form
from hospital.royallab_native_result_drafts import validate_source_form


class WholeBloodSourcePlaceholderTests(unittest.TestCase):
    def test_whole_blood_unnamed_without_format_is_not_a_result_field(self):
        with sqlite3.connect(":memory:") as db:
            cid=install_file(db,SOURCE)
            original=test_form(db,cid,"108")
            form=clinical_test_form(db,cid,"108")
            excluded_ids={"657","659","662","664"}
            original_ids={str(f.get("source_analyte_id")) for f in original["fields"]}
            self.assertTrue(excluded_ids.issubset(original_ids))
            self.assertGreaterEqual(form["excluded_unnamed_untyped_placeholders"],4)
            self.assertTrue(all(str(f.get("source_analyte_id")) not in excluded_ids
                                for f in form["fields"]))
            self.assertEqual(form["review_flags"],[])
            validate_source_form(form)
            self.assertEqual(len(test_form(db,cid,"108")["fields"]),len(original["fields"]))

    def test_named_untyped_source_field_is_never_dropped_as_empty(self):
        with sqlite3.connect(":memory:") as db:
            cid=install_file(db,SOURCE)
            original=test_form(db,cid,"108")
            meaningful=[f for f in original["fields"] if str(f.get("label") or "").strip()]
            edited=clinical_test_form(db,cid,"108")
            active_ids={str(f.get("source_format_id")) for f in edited["fields"]}
            self.assertTrue(all(f["source_format_id"] in active_ids
                                for f in meaningful if f.get("active") not in
                                (False,0,"False","false","0")))


if __name__=="__main__":
    unittest.main()
