"""Only historical result headers may inform NOVA schema recovery; no PHI."""
import json
import pathlib
import tempfile
import unittest
from hospital.royallab_historical_schema_audit import historical_headers, recovery_for_blocked
from hospital.royallab_catalog_audit import SOURCE


class HistoricalSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = json.loads(SOURCE.read_text(encoding="utf-8-sig"))

    def test_source_ids_are_recovered_from_real_original_column_names(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            (root / "dbo__Test_273.csv").write_bytes(
                b"TestOrderID,AnalyteResult_1078_1757,AnalyteResult_1079_1758\r\n"
                b"1,SEALED_PRIVATE_RECORD,OTHER_PRIVATE_VALUE\r\n")
            report = historical_headers(root, self.library)
            self.assertEqual(report["patient_rows_read"], 0)
            self.assertEqual(report["matched_column_count"], 2)
            self.assertEqual(report["unmatched_historical_columns"], [])
            self.assertTrue(report["historical_test_schemas"]["273"]["source_test_exists"])
            self.assertTrue(all(c["test_id_consistent"] for c in
                                report["historical_test_schemas"]["273"]["historical_format_columns"]))
            self.assertNotIn("SEALED_PRIVATE_RECORD", json.dumps(report))

    def test_never_buffer_or_decode_historical_patient_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            # Invalid UTF-8 after newline would raise if the file were read,
            # even if the returned report intentionally omitted its values.
            (root / "dbo__Test_274.csv").write_bytes(
                b"TestOrderID,AnalyteResult_1081_1768\n" + b"SECRET:\xff\xfe\0\0")
            report = recovery_for_blocked(root, self.library)
            self.assertEqual(report["patient_rows_read"], 0)
            self.assertFalse(report["patient_values_exported"])
            self.assertEqual(report["blocked_count"] +
                             sum(1 for x in self.library["tests"] if str(x["TestID"]) == "__no_match__"),
                             report["blocked_count"])
            self.assertFalse(report["clinical_approval"])

    def test_detects_wrong_analyte_parent_without_guessing_relationship(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            (root / "dbo__Test_274.csv").write_bytes(
                b"TestOrderID,AnalyteResult_1078_1757\nDO_NOT_READ\n")
            report = historical_headers(root, self.library)
            self.assertEqual(report["matched_column_count"], 0)
            self.assertEqual(report["unmatched_historical_columns"][0]["analyte_id"], "1078")
            self.assertFalse(report["unmatched_historical_columns"][0]["test_id_consistent"])

    def test_rejects_incomplete_and_duplicate_result_headers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            path = root / "dbo__Test_273.csv"
            path.write_bytes(b"TestOrderID,AnalyteResult_1078_1757")
            with self.assertRaisesRegex(ValueError, "Missing or oversized"):
                historical_headers(root, self.library)
            path.write_bytes(b"TestOrderID,AnalyteResult_1078_1757,AnalyteResult_1078_1757\n")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                historical_headers(root, self.library)


if __name__ == "__main__":
    unittest.main()
