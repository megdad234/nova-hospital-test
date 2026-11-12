"""Real Royal Lab Seminal Culture (source TestID 284) separator evidence.

Only drop source-proven nameless, choice-less placeholder columns. The original
source and all named microbiology result fields remain unchanged for audit.
"""
import sqlite3
import unittest
from hospital.royallab_catalog_audit import SOURCE
from hospital.royallab_native_catalog_store import install_file,test_form,clinical_test_form
from hospital.royallab_native_result_drafts import validate_source_form


class SeminalCultureOriginalSourceTests(unittest.TestCase):
    def test_original_dash_only_separators_are_not_editable_clinical_fields(self):
        with sqlite3.connect(":memory:") as db:
            cid=install_file(db,SOURCE)
            original=test_form(db,cid,"284")
            form=clinical_test_form(db,cid,"284")
            original_ids={str(f["source_analyte_id"]) for f in original["fields"]}
            self.assertTrue({str(x) for x in range(1185,1195)}.issubset(original_ids))
            self.assertEqual(form["excluded_empty_source_separators"],10)
            for field in form["fields"]:
                self.assertFalse(
                    str(field.get("source_analyte_id")) in
                    {str(x) for x in range(1185,1195)})
            self.assertEqual(len(original["fields"])-len(form["fields"]),
                             10+form["excluded_inactive_source_fields"]+
                             form["excluded_redundant_empty_closed_formats"])
            self.assertTrue(len(form["fields"])>0)
            self.assertFalse(form.get("review_flags"))
            validate_source_form(form)
            self.assertEqual(len(test_form(db,cid,"284")["fields"]),len(original["fields"]))


if __name__=="__main__":
    unittest.main()
