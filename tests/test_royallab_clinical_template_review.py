"""End-to-end proof: original missing test stays blocked until a second reviewer.

Uses only the ORIGINAL source catalog and disposable in-memory SQLite tables.
No real patient, no clinical diagnosis or invented reference normal ranges.
"""
import sqlite3
import unittest

from hospital.royallab_catalog_audit import SOURCE, audit
from hospital.royallab_native_catalog_store import install_file,clinical_test_form,test_form
from hospital.royallab_clinical_template_review import (
    propose,approve,review_history,review_details,review_suggestion)
from hospital.royallab_native_result_drafts import save_draft,validate_source_form
from hospital.royallab_native_catalog_api import catalog_response,form_response

LAB={"id":101,"role":"lab"}
REVIEWER={"id":202,"role":"admin"}
NUMBER=[{"key":"vitd","label":"25-OH Vitamin D","kind":"number","unit":"ng/mL"}]
CHOICES=[{"key":"answer","label":"Method-specific result","kind":"select",
          "options":[{"key":"N","label":"Non-reactive"},{"key":"P","label":"Reactive"}]}]
DETAILS={"method":"Local identified assay 25-hydroxyvitamin D",
         "evidence":"Local laboratory kit IFU revision and validation protocol",
         "rationale":"Local director review of missing legacy result schema"}
ATTEST="Reviewed local assay, control method and documented permitted result definitions"


class TwoPersonClinicalReviewTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.cid=install_file(self.db,SOURCE)

    def tearDown(self):
        self.db.close()

    def test_approval_unlocks_exact_missing_source_id_and_draft_save(self):
        source_id="368"
        self.assertEqual(clinical_test_form(self.db,self.cid,source_id)["fields"],[])
        self.assertFalse(next(t for t in catalog_response(self.db)["tests"]
                              if t["source_test_id"]==source_id)["result_entry_ready"])
        pending=propose(self.db,LAB,self.cid,source_id,NUMBER,**DETAILS)
        self.assertEqual(pending["state"],"pending")
        detail=review_details(self.db,self.cid,source_id,pending["revision"])
        self.assertEqual(detail["form"]["fields"][0]["label"],"25-OH Vitamin D")
        self.assertEqual(detail["form_hash"],pending["form_hash"])
        self.assertFalse(detail["can_publish_patient_results"])
        with self.assertRaises(ValueError):
            validate_source_form(clinical_test_form(self.db,self.cid,source_id))
        with self.assertRaises(PermissionError):
            approve(self.db,LAB,self.cid,source_id,pending["revision"],
                    pending["form_hash"],attestation=ATTEST)
        with self.assertRaises(PermissionError):
            approve(self.db,{"id":101,"role":"admin"},self.cid,source_id,
                    pending["revision"],pending["form_hash"],attestation=ATTEST)
        accepted=approve(self.db,REVIEWER,self.cid,source_id,pending["revision"],
                         pending["form_hash"],attestation=ATTEST)
        self.assertEqual(accepted["state"],"approved")
        form=clinical_test_form(self.db,self.cid,source_id)
        validate_source_form(form)
        self.assertEqual(form["clinical_template_revision"],1)
        self.assertEqual(form["fields"][0]["source_format_id"],"REVIEW-368-vitd")
        self.assertEqual(test_form(self.db,self.cid,source_id)["fields"],[])
        self.assertTrue(next(t for t in catalog_response(self.db)["tests"]
                             if t["source_test_id"]==source_id)["result_entry_ready"])
        self.assertEqual(form_response(self.db,source_id)["test"]["fields"][0]["kind"],"number")
        saved=save_draft(self.db,"NOVA-ITEM-22",source_id,{"REVIEW-368-vitd":"26.5"})
        self.assertEqual(saved["values"],{"REVIEW-368-vitd":"26.5"})
        self.assertEqual(review_history(self.db,self.cid,source_id)[0]["approved_by"],202)
        with self.assertRaisesRegex(ValueError,"Historical result drafts"):
            propose(self.db,LAB,self.cid,source_id,NUMBER,**DETAILS)

    def test_option_ids_are_immutable_and_unlisted_values_blocked(self):
        # This test uses synthetic, local documentation, NOT a claimed HCV kit.
        p=propose(self.db,LAB,self.cid,"336",CHOICES,
                  method="Lab validated rapid screening kit method",
                  evidence="Local signed manufacturer instructions for test kit",
                  rationale="Explicitly documented locally selected assay")
        approve(self.db,REVIEWER,self.cid,"336",p["revision"],p["form_hash"],
                attestation=ATTEST)
        form=clinical_test_form(self.db,self.cid,"336")
        self.assertEqual([x["label"] for x in form["fields"][0]["options"]],
                         ["Non-reactive","Reactive"])
        save_draft(self.db,"NOVA-ITEM-23","336",
                   {"REVIEW-336-answer":"REVIEW-336-answer-N"})
        with self.assertRaises(ValueError):
            save_draft(self.db,"NOVA-ITEM-24","336",{"REVIEW-336-answer":"Positive"})
        with self.assertRaises(ValueError):
            save_draft(self.db,"NOVA-ITEM-24","336",
                       {"REVIEW-336-answer":"REVIEW-368-vitd"})

    def test_rejects_nonlab_or_already_complete_source(self):
        with self.assertRaisesRegex(ValueError,"already has"):
            propose(self.db,LAB,self.cid,"21",NUMBER,**DETAILS)
        nonlab=audit()["non_lab_services"][0]["source_test_id"]
        with self.assertRaisesRegex(ValueError,"Non-laboratory"):
            propose(self.db,LAB,self.cid,nonlab,NUMBER,**DETAILS)

    def test_rejects_missing_or_duplicated_dropdown_and_fake_signoff(self):
        bad=[{"key":"x","label":"Result","kind":"select","options":[]}]
        with self.assertRaisesRegex(ValueError,"Dropdown"):
            propose(self.db,LAB,self.cid,"368",bad,**DETAILS)
        bad=[{"key":"x","label":"Result","kind":"select",
              "options":[{"key":"x","label":"X"},{"key":"x","label":"Duplicate"}]}]
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            propose(self.db,LAB,self.cid,"368",bad,**DETAILS)
        p=propose(self.db,LAB,self.cid,"368",NUMBER,**DETAILS)
        with self.assertRaises(ValueError):
            approve(self.db,REVIEWER,self.cid,"368",1,"0"*64,attestation=ATTEST)
        with self.assertRaises(ValueError):
            approve(self.db,REVIEWER,self.cid,"368",1,p["form_hash"],attestation="")
        self.assertEqual(review_history(self.db,self.cid,"368")[0]["state"],"pending")

    def test_suggestions_are_nonoperative_and_preserve_missing_source_evidence(self):
        vitamin=review_suggestion(self.db,self.cid,"368")
        self.assertEqual(vitamin["source_test_id"],"368")
        self.assertFalse(vitamin["ready_for_patient_results"])
        self.assertTrue(vitamin["requires_independent_approval"])
        self.assertTrue(vitamin["source_archive_unchanged"])
        self.assertEqual(len(vitamin["fields"]),1)
        self.assertFalse(vitamin["fields"][0]["source_proven"])
        self.assertEqual(vitamin["fields"][0]["option_labels"],[])
        original=review_suggestion(self.db,self.cid,"60")
        self.assertGreater(len(original["fields"]),0)
        self.assertTrue(any(x["source_was_inactive"] for x in original["fields"]))
        self.assertTrue(any("inactive" in w for w in original["warnings"]))
        self.assertFalse(any(x["unit"] is None for x in original["fields"]))
        with self.assertRaisesRegex(ValueError,"already has"):
            review_suggestion(self.db,self.cid,"21")

    def test_source_preserved_and_approved_form_tampering_detected(self):
        p=propose(self.db,LAB,self.cid,"368",NUMBER,**DETAILS)
        approve(self.db,REVIEWER,self.cid,"368",p["revision"],p["form_hash"],
                attestation=ATTEST)
        self.db.execute("""UPDATE royal_lab_template_reviews SET form_json=?
           WHERE catalog_id=? AND source_test_id='368'""",
           ('{"fields":[],"review_flags":[]}',self.cid))
        with self.assertRaisesRegex(ValueError,"modified"):
            clinical_test_form(self.db,self.cid,"368")
        self.assertEqual(test_form(self.db,self.cid,"368")["fields"],[])


if __name__=="__main__":
    unittest.main()
