import unittest
from hospital.royallab_catalog_audit import audit, SOURCE

class CatalogAuditTests(unittest.TestCase):
    def test_bundled_catalog_is_readable_and_audited_without_writes(self):
        self.assertTrue(SOURCE.is_file())
        report = audit()
        self.assertEqual(report["test_count"], 367)
        self.assertEqual(report["source_analyte_count"], 1245)
        self.assertFalse(report["clinical_approval"])
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
