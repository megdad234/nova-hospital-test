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
        self.assertIn("لا توجد نتائج مدخلة قابلة للطباعة", source)
        self.assertIn("منطقة الطباعة غير متاحة", source)
        self.assertIn("window.removeEventListener('afterprint',cleanup)", source)
        self.assertIn("catch(printError){cleanup();throw printError}", source)
        self.assertIn(".filter(item=>(item.lines||[]).some(", source)

    def test_lab_print_function_boundary_and_receipt_preservation(self):
        source = APP.read_text(encoding="utf-8")
        self.assertEqual(source.count("async function printReport(id){"), 1)
        start = source.index("async function printReport(id){")
        end = source.find("\\nfunction ", start)
        async_end = source.find("\\nasync function ", start + 1)
        candidates = [x for x in (end, async_end) if x >= 0]
        self.assertTrue(candidates, "Lab print must end before the next top-level function")
        lab = source[start:min(candidates)]
        self.assertIn("await Promise.all(", lab)
        self.assertIn("window.print();", lab)
        self.assertIn("catch(printError){cleanup();throw printError}", lab)
        self.assertNotIn("window.print()}catch(e){notice(e.message,true)}}", source)
        # This laboratory-only test must never replace or normalize the receipt engines.
        self.assertIn("printing-lab", lab)

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
