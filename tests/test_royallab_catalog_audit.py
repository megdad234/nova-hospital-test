import unittest
from hospital.royallab_catalog_audit import audit, SOURCE

class CatalogAuditTests(unittest.TestCase):
    def test_bundled_catalog_is_readable_and_audited_without_writes(self):
        self.assertTrue(SOURCE.is_file())
        report = audit()
        self.assertEqual(report["test_count"], 367)
        self.assertEqual(report["source_analyte_count"], 1245)
        self.assertFalse(report["clinical_approval"])
        self.assertEqual(report["detached_analyte_count"], sum(x["analyte_count"] for x in report["detached_source_test_groups"]))
        self.assertEqual(len(report["tests_without_analytes"]), report["review_flags"].get("no_source_analytes", 0))
        self.assertEqual(report["orphan_groups_missing_source_test"], sum(not x["source_test_exists"] for x in report["detached_source_test_groups"]))
        self.assertEqual(
            report["tests_requiring_review"],
            len(report["flagged_tests"])
        )
        self.assertEqual(
            report["source_result_field_count"],
            sum(report["field_kinds"].values())
        )
        self.assertTrue(all("source_test_id" in item for item in report["flagged_tests"]))

if __name__ == "__main__":
    unittest.main()
