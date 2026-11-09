"""Guard laboratory print isolation from pharmacy/cashier receipt styles."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "hospital/static/app.js"
CSS = ROOT / "hospital/static/style.css"

class LabPrintIsolationTests(unittest.TestCase):
    def test_lab_print_renderer_and_disclaimer(self):
        source = APP.read_text(encoding="utf-8")
        self.assertIn("async function printReport(id)", source)
        self.assertIn("nova-clinical-print", source)
        self.assertNotIn("تقرير جزئي — توجد فحوصات أخرى لم تُنشر بعد.", source)
        self.assertIn("print-patient", source)
        self.assertIn("lab-results", source)
        for token in ("section_name", "print_time", "patient_name", "patient_no", "order_no", "window.print()"):
            self.assertIn(token, source)
        self.assertIn("window.addEventListener('afterprint',cleanup", source)
        self.assertNotIn("تقرير جزئي", source)

    def test_lab_page_is_scoped(self):
        styles = [p.read_text(encoding="utf-8") for p in ROOT.glob("hospital/static/*.css")]
        joined = "\n".join(styles)
        self.assertIn("@page nova-lab-report", joined)
        self.assertIn("page:nova-lab-report", joined)
        self.assertNotIn("@page{size:A4 portrait", joined)
        for token in ("body.printing-lab .nova-clinical-print", "size:A4 portrait", "display:table-header-group", "body.printing-lab .nova-clinical-print .print-patient", "body.printing-lab .nova-clinical-print .lab-print-test", "page-break-inside:auto", "page-break-after:avoid"):
            self.assertIn(token, joined)

if __name__ == "__main__":
    unittest.main()
