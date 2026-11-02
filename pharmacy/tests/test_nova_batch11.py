# -*- coding: utf-8 -*-
"""NOVA Batch11: source and packaging checks, database remains untouched."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

class UnifiedReceiptAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine=(ROOT/'.github/ci/nova_unified_thermal_engine.js').read_text(encoding='utf-8')
        cls.pharmacy=(ROOT/'pharmacy/static/nova_pharmacy_batch08.js').read_text(encoding='utf-8')
        cls.pharmacy_main=(ROOT/'pharmacy/static/app.js').read_text(encoding='utf-8')
        cls.hospital=(ROOT/'hospital/static/finance-ui.js').read_text(encoding='utf-8')
        cls.legacy_pharmacy_style=(ROOT/'pharmacy/static/style.css').read_text(encoding='utf-8')

    def test_identical_engine_for_both_modules(self):
        self.assertIn(self.engine.strip(),self.pharmacy)
        self.assertIn(self.engine.strip(),self.hospital)
        self.assertIn('printReceipt=async function()',self.pharmacy)
        self.assertIn('novaPrintThermalDocument=function(markup)',self.hospital)

    def test_pharmacy_receipt_appearance_preserved(self):
        self.assertIn('function receipt(s)',self.pharmacy_main)
        self.assertIn('class="thermal-receipt"',self.pharmacy_main)
        self.assertIn("printable.outerHTML",self.pharmacy)
        self.assertIn("if(printable.classList.contains('thermal-receipt')&&paper!=='a4')",self.pharmacy)
        self.assertIn("function printPurchase(id)",self.pharmacy_main)

    def test_browser_print_isolated_from_a4_and_regular_reports(self):
        self.assertIn("frame.srcdoc=source",self.engine)
        self.assertIn("'@page{size:'+mm+'mm '+length+'mm;margin:0}'",self.engine)
        self.assertIn("body.scrollHeight includes iframe viewport height",self.engine)
        self.assertIn("Math.max(ticket.getBoundingClientRect().height,ticket.scrollHeight)",self.engine)
        self.assertNotIn('size:A4',self.engine)
        self.assertIn('window.print();setTimeout(clean,120000)',self.pharmacy)
        self.assertIn('function financePrintInvoice(inv)',self.hospital)
        self.assertIn('@page{margin:3mm}',self.legacy_pharmacy_style)

    def test_58_80_and_rtl(self):
        for marker in ('thermal58', 'thermal80',"dir=\\"rtl\\"",
                       'Tahoma,Arial','unicode-bidi:isolate','overflow-wrap:anywhere'):
            self.assertIn(marker,self.engine)
        self.assertIn('25.4/96',self.engine)

if __name__=='__main__':unittest.main()
