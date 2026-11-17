"""Real NOVA lab-only print contract after all source patches.

The previous named @page rule was not honored by Edge print preview,
and the shared page could lose a table column. The browser must print
an independent document containing a SINGLE, GLOBAL A4 portrait @page.
"""
from pathlib import Path
import ast
import importlib.util
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'hospital/static/app.js'
SHEET=ROOT/'.github/ci/nova_lab_portrait_print.css'
PATCH=ROOT/'.github/ci/nova_lab_portrait_frame_patch.py'

class LabA4PortraitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=APP.read_text(encoding='utf-8')
        cls.css=SHEET.read_text(encoding='utf-8')
        spec=importlib.util.spec_from_file_location('nova_lab_portrait_patch',PATCH)
        cls.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_isolated_print_document_is_real_route(self):
        src=self.source
        self.assertEqual(src.count('async function printReport(id)'),1)
        self.assertEqual(src.count('/* NOVA_LAB_ISOLATED_A4_PORTRAIT_V2 */'),1)
        i=src.index('async function printReport(id)')
        # JS lab report is still the original report endpoint and clinical data.
        report=src[i:src.find('\nfunction ',i+30) if src.find('\nfunction ',i+30)>0 else i+14000]
        self.assertIn("api('lab/report/'+id)",report)
        self.assertIn('novaLabPrintA4Portrait(html)',report)
        self.assertNotIn("document.body.classList.add('printing-lab')",report)
        self.assertNotIn('window.print()',report)
        self.assertIn('reportMarkup',src)
        self.assertIn('frame.srcdoc=markup',src)
        self.assertIn('w.print()',src)
        self.assertIn('frame.contentWindow',src)

    def test_unnamed_portrait_page_is_the_only_rule_in_new_document(self):
        self.assertEqual(self.css.count('@page'),2) # comment + one CSS rule
        self.assertEqual(len(re.findall(r'(?m)^\s*@page\s*\{',self.css)),1)
        self.assertRegex(self.css,r'@page\s*\{\s*size:\s*A4\s+portrait\s*;')
        self.assertNotIn('landscape',self.css.lower())
        # The browser print document must NOT load main hospital stylesheet.
        self.assertNotIn('href="style.css"',self.source[self.source.index('function novaLabPrintA4Portrait('):self.source.index('async function printReport(id)')])
        self.assertNotIn('stylesheets',self.source[self.source.index('function novaLabPrintA4Portrait('):self.source.index('async function printReport(id)')])

    def test_no_overflow_and_four_complete_table_columns(self):
        for term in ('min-width:0!important','overflow:visible!important',
                     'table-layout:fixed!important','display:table-header-group!important',
                     'break-inside:avoid-page!important','overflow-wrap:anywhere!important'):
            self.assertIn(term,self.css)
        self.assertEqual([int(x) for x in re.findall(r'td:nth-child\(\d\)\s*\{\s*width:(\d+)%',self.css)],
                         [34,17,17,32])
        self.assertIn('.print-patient',self.css)
        self.assertIn('.lab-print-test',self.css)
        self.assertIn('.print-foot',self.css)

    def test_print_frame_kept_until_after_dialog(self):
        src=self.source
        printjs=src[src.index('function novaLabPrintA4Portrait('):src.index('async function printReport(id)')]
        self.assertIn("w.addEventListener('afterprint'",printjs)
        self.assertIn("window.setTimeout(()=>{if(frame.isConnected)frame.remove()},1200)",printjs)
        self.assertIn('frame.addEventListener',printjs)
        self.assertNotIn("frame.style.display='none'",printjs)
        self.assertIn("width:210mm;height:297mm",printjs)
        self.assertIn('if(w.document.fonts && w.document.fonts.ready)',printjs)

    def test_only_hospital_lab_printing_was_replaced(self):
        src=self.source
        # The patch leaves all other generated JS identical when reversed.
        helper=src[src.index('\n/* NOVA_LAB_ISOLATED_A4_PORTRAIT_V2 */'):
                   src.index('async function printReport(id)')]
        original=src.replace(helper,'',1).replace(
            '    novaLabPrintA4Portrait(html);',self.module.OLD_PRINT,1)
        self.assertEqual(self.module.patch(original,self.css),src)
        with self.assertRaises(RuntimeError):
            self.module.patch(src,self.css)
        # Never patch pharmacy print, receipts, or hospital invoice logic.
        self.assertNotIn('pharmacy/',PATCH.read_text(encoding='utf-8'))
        self.assertNotIn('sale_print',PATCH.read_text(encoding='utf-8'))

if __name__=='__main__':
    unittest.main()
