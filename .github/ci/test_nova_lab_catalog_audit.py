"""Synthetic regression tests for NOVA's read-only laboratory catalogue audit."""
import ast
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().with_name("nova_lab_catalog_audit.py")
spec = importlib.util.spec_from_file_location("nova_lab_catalog_audit", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class LabCatalogueAuditTests(unittest.TestCase):
    def test_detects_generic_missing_and_duplicate_without_running_catalogue(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "lab_catalog.py"
            p.write_text(
                "TESTS=[('CBC','CBC','Hematology',(),[('WBC','WBC','','','','')]),"
                "('MALARIA','Malaria','Parasitology',(),[('RESULT','Result','','','','')]),"
                "('CBC','Duplicate','Hematology',(),[])]\n"
                "TESTS.extend([('URINE','Urine','Urinalysis',(),[('RESULT','Result','','','','')])])\n",
                encoding="utf-8"
            )
            before = p.read_bytes()
            result = module.audit(p)
            self.assertEqual(result["parsed_tests"], 4)
            self.assertEqual(result["duplicate_codes"], ["CBC"])
            self.assertEqual(result["empty_parameter_tests"], ["CBC"])
            self.assertTrue(result["review_required"])
            self.assertEqual({x["code"] for x in result["generic_result_tests"]}, {"MALARIA", "URINE"})
            self.assertIn("GTT", result["missing_priority_codes"])
            self.assertEqual(result["priority_generic_only"], ["MALARIA", "URINE"])
            self.assertEqual(before, p.read_bytes())

    def test_malformed_parameters_are_reported_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "lab_catalog.py"
            p.write_text("TESTS=[('BAD','Bad','Lab',(),[()]),('OK','OK','Lab',(),[('RESULT','Result')])]\n", encoding="utf-8")
            before = p.read_bytes()
            report = module.audit(p)
            self.assertEqual(report["malformed_parameter_codes"], ["BAD"])
            self.assertEqual([x["code"] for x in report["generic_result_tests"]], ["OK"])
            self.assertEqual(before, p.read_bytes())

    def test_repeated_parameter_codes_and_invalid_test_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "lab_catalog.py"
            p.write_text(
                "TESTS=[('GTT','GTT','Chemistry',(),[('FAST','Fasting'),('FAST','Repeated')]),('BROKEN',)]\n",
                encoding="utf-8"
            )
            report = module.audit(p)
            self.assertEqual(report["duplicate_parameter_codes"], {"GTT": ["FAST"]})
            self.assertEqual(len(report["malformed_tests"]), 1)
            self.assertEqual(report["all_tests"][0]["parameter_codes"], ["FAST", "FAST"])
            self.assertTrue(report["review_required"])

    def test_unparseable_literal_extension_is_visible_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "lab_catalog.py"
            p.write_text("TESTS=[]\nTESTS.extend(make_tests())\n", encoding="utf-8")
            report = module.audit(p)
            self.assertEqual(report["parsed_tests"], 0)
            self.assertEqual(report["parse_warnings"], ["TESTS.extend: ValueError"])
            self.assertTrue(report["review_required"])

    def test_priority_details_preserve_exact_parameter_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "lab_catalog.py"
            p.write_text("TESTS=[('MALARIA','Malaria','Parasitology',(),[('PARASITE','Parasites','','','','')])]\n", encoding="utf-8")
            report = module.audit(p)
            self.assertEqual(report["priority_template_details"]["MALARIA"][0]["parameter_definitions"][0][0], "PARASITE")
            self.assertNotIn("MALARIA", report["priority_generic_only"])

    def test_invalid_parameter_containers_are_not_treated_as_valid_panels(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "lab_catalog.py"
            p.write_text(
                "TESTS=[('A','A','Lab',(),None),('B','B','Lab',(),[('CODE',)])]\n",
                encoding="utf-8"
            )
            report = module.audit(p)
            self.assertEqual(report["malformed_parameter_codes"], ["A", "B"])
            self.assertIn("A", report["empty_parameter_tests"])
            self.assertTrue(report["review_required"])

    def test_blank_field_labels_and_codes_are_flagged_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "lab_catalog.py"
            p.write_text(
                "TESTS=[('URINE','Urine','Urinalysis',(),[('COLOR','','','','',''),('', 'Appearance','','','','')])]\n",
                encoding="utf-8",
            )
            original = p.read_bytes()
            report = module.audit(p)
            self.assertEqual(report["blank_parameter_labels"], {"URINE": ["COLOR"]})
            self.assertEqual(report["blank_parameter_codes"], {"URINE": ["Appearance"]})
            self.assertTrue(report["review_required"])
            self.assertEqual(p.read_bytes(), original)

    def test_resolves_named_static_panels_without_executing_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "lab_catalog.py"
            p.write_text(
                "CBC_FIELDS=[('WBC','White cells','10^9/L','','','')]\\n"
                "URINE_FIELDS=[('COLOR','Colour','','','','')]\\n"
                "BASE=[('CBC','CBC','Hematology',(),CBC_FIELDS)]\\n"
                "TESTS=BASE+[('URINE','Urine','Urinalysis',(),URINE_FIELDS)]\\n",
                encoding="utf-8"
            )
            original = p.read_bytes()
            report = module.audit(p)
            self.assertEqual(report["parse_warnings"], [])
            self.assertEqual(report["parsed_tests"], 2)
            self.assertEqual(report["missing_priority_codes"], ["GTT", "MALARIA", "STOOL"])
            self.assertEqual(p.read_bytes(), original)

    def test_never_executes_catalogue_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "lab_catalog.py"
            marker = Path(tmp) / "executed.txt"
            p.write_text("from pathlib import Path\nPath("+repr(str(marker))+").write_text('bad')\nTESTS=[]\n", encoding="utf-8")
            self.assertEqual(module.audit(p)["parsed_tests"], 0)
            self.assertFalse(marker.exists())

if __name__ == "__main__":
    unittest.main()
