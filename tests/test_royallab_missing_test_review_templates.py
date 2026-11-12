"""Missing clinical template proposals must remain review-only."""
import json
import unittest
from hospital.royallab_catalog_audit import SOURCE
from hospital.royallab_missing_test_review_templates import build_review_proposals, CANDIDATE_FIELDS


class MissingClinicalTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = json.loads(SOURCE.read_text(encoding="utf-8-sig"))

    def test_all_missing_clinical_tests_have_nonoperative_proposal(self):
        proposals = build_review_proposals(self.library)
        self.assertEqual(len(proposals), 20)
        self.assertEqual(len({x["source_test_id"] for x in proposals}), 20)
        self.assertEqual({x["source_test_id"] for x in proposals}, set(CANDIDATE_FIELDS))
        self.assertTrue(all(not x["can_save_patient_results"] and not x["can_publish"]
                            and x["requires_laboratory_director_approval"]
                            for x in proposals))

    def test_unknown_assay_never_gets_assumed_dropdown_or_unit(self):
        proposals = {x["source_test_id"]: x for x in build_review_proposals(self.library)}
        for sid in ("336", "369", "347", "343", "344", "340"):
            self.assertEqual(proposals[sid]["suggested_fields"], [])
            self.assertTrue(proposals[sid]["requires_assay_specification"])
        for x in proposals.values():
            for f in x["suggested_fields"]:
                self.assertIsNone(f["unit"])
                self.assertIsNone(f["options"])
                self.assertIsNone(f["reference_ranges"])


if __name__ == "__main__":
    unittest.main()
