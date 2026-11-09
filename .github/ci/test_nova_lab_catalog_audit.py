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
            self.assertEqual({x["code"] for x in result["generic_result_tests"]}, {"MALARIA", "URINE"})
            self.assertIn("GTT", result["missing_priority_codes"])
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

    def test_never_executes_catalogue_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "lab_catalog.py"
            marker = Path(tmp) / "executed.txt"
            p.write_text("from pathlib import Path\nPath("+repr(str(marker))+").write_text('bad')\nTESTS=[]\n", encoding="utf-8")
            self.assertEqual(module.audit(p)["parsed_tests"], 0)
            self.assertFalse(marker.exists())

if __name__ == "__main__":
    unittest.main()
