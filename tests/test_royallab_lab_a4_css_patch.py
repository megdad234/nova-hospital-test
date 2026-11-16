"""NOVA laboratory result printing: A4 portrait, no horizontal clipping.

Controls only the printed laboratory result layout. Pharmacy receipts and
hospital invoices retain their existing print CSS and transport.
"""
import pathlib
import sys
import unittest
import zipfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/".github"/"ci"))
from royallab_lab_a4_css_patch import patch


class A4CssTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(ROOT/"NOVA_Hospital_GitHub_Ready_Source.zip") as z:
            cls.before=z.read("hospital/static/style.css").decode("utf-8-sig")
        cls.after=patch(cls.before)
        cls.delta=cls.after[len(cls.before):]

    def test_lab_only_additive_no_pharmacy_or_invoice_changes(self):
        self.assertTrue(self.after.startswith(self.before))
        self.assertIn("body.printing-lab #print-area .print-patient{break-inside:avoid-page",
                      self.delta)
        self.assertIn("thead{display:table-header-group}",self.delta)
        self.assertIn(".lab-print-group th",self.delta)
        self.assertNotIn("body.printing-receipt",self.delta)
        self.assertNotIn("body.printing-admin",self.delta)
        self.assertNotIn("body.printing-pharmacy",self.delta)
        self.assertNotIn(".bill-print",self.delta)
        self.assertNotIn("@page{size:A4 portrait",self.delta)
        with self.assertRaises(RuntimeError):
            patch(self.after)

    def test_laboratory_page_named_a4_portrait_only(self):
        self.assertEqual(self.delta.count("@page nova_lab_portrait{"),1)
        self.assertIn("size:A4 portrait;",self.delta)
        self.assertIn("page:nova_lab_portrait!important;",self.delta)
        self.assertIn("body.printing-lab #print-area",self.delta)
        self.assertNotIn("landscape",self.delta)
        # Do not override global/unnamed @page; other departments must keep
        # their own printer size/orientation policies.
        self.assertNotIn("@page { size:A4 portrait",self.delta)
        self.assertNotIn("@page{size:A4 portrait",self.delta)

    def test_four_result_columns_fit_paper_without_screen_min_width(self):
        for x in (".lab-print .lab-results{",
                  "table-layout:fixed!important;",
                  "width:100%!important;",
                  "max-width:100%!important;",
                  "min-width:0!important;",
                  "overflow-wrap:anywhere!important;"):
            self.assertIn(x,self.delta)
        for index,width in enumerate((34,16,18,32),1):
            self.assertIn(
                f".lab-print .lab-results :is(th,td):nth-child({index})"
                +"{width:"+str(width)+"%!important}",self.delta)
        self.assertEqual(sum((34,16,18,32)),100)

    def test_long_reports_repeat_headers_and_preserve_rows(self):
        self.assertIn("display:table-header-group!important;",self.delta)
        self.assertIn("break-inside:avoid-page!important;",self.delta)
        self.assertIn("page-break-inside:avoid!important;",self.delta)
        self.assertIn(".nova-lab-section,",self.delta)
        self.assertIn(".lab-print-group{",self.delta)
        self.assertIn("break-after:avoid-page!important;",self.delta)
        self.assertIn(".lab-print-test{",self.delta)
        self.assertIn(".print-head{",self.delta)
        self.assertIn(".print-patient{",self.delta)
        self.assertIn(".print-foot{",self.delta)

    def test_app_still_uses_unmodified_report_print_contract(self):
        # Source and current patch retain the existing report path and
        # window.print; this change must not touch data, approval, bills.
        js=(ROOT/".github/ci/royallab_lab_print_patch.py").read_text(encoding="utf-8")
        self.assertIn("async function printReport(id)",js)
        self.assertIn("window.print()",js)
        self.assertIn("hospital/static/app.js",js)
        source=(ROOT/".github/ci/royallab_lab_a4_css_patch.py").read_text(encoding="utf-8")
        self.assertIn('Path(root)/"hospital/static/style.css"',source)
        self.assertNotIn("pharmacy/",source)


if __name__=="__main__":
    unittest.main()
