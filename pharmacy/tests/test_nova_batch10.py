# -*- coding: utf-8 -*-
"""Receipt print acceptance: never regress the already-good pharmacy printer."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
class ThermalPrintAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.finance=(ROOT/'hospital/static/finance-ui.js').read_text(encoding='utf-8')
        cls.css=(ROOT/'hospital/static/style.css').read_text(encoding='utf-8')
        cls.lab=(ROOT/'hospital/static/app.js').read_text(encoding='utf-8')
        cls.pharmacy=(ROOT/'pharmacy/static/app.js').read_text(encoding='utf-8')

    def test_receipt_paper_width_matches_proven_pharmacy(self):
        self.assertIn('width:72mm!important',self.css)
        self.assertIn('max-width:72mm!important',self.css)
        self.assertIn('font-family:Tahoma,Arial,sans-serif!important',self.css)
        self.assertIn('@page novaReceiptPaper{size:auto;margin:3mm}',self.css)

    def test_named_thermal_page_is_isolated_from_a4(self):
        self.assertIn('page:novaReceiptPaper;',self.css)
        self.assertIn('body.printing-nova-thermal > *:not(#print-area)',self.css)
        self.assertIn('body.printing-nova-thermal #print-area{display:block!important',self.css)
        self.assertIn('body.printing-lab',self.css)
        self.assertIn('@page{size:A4;margin:13mm}',self.css)
        self.assertIn('function financePrintInvoice(inv)',self.finance)
        self.assertIn("document.body.classList.add('printing-lab')",self.finance)

    def test_payment_receipt_contains_exact_installment_and_all_methods(self):
        self.assertIn('function novaPrintReceipt(inv,index)',self.finance)
        self.assertIn('selected=index??(last.length-1)',self.finance)
        self.assertIn('novaPrintReceipt(financeState.invoice);',self.finance)
        self.assertIn('remainAtReceipt',self.finance)
        self.assertIn('row(\'الكاشير\',p.cashier_name)',self.finance)
        self.assertNotIn("if(receipt.status==='settled')financePrintInvoice(financeState.invoice)",self.finance)
        for fragment in ('p.cash_amount','p.bank_amount','p.bank_reference','p.bank_name',
                         'p.payment_no','inv.invoice_no','inv.patient_name'):
            self.assertIn(fragment,self.finance)

    def test_iso_dates_are_not_reordered_by_rtl(self):
        self.assertIn("replace('T',' ').slice(0,16)",self.finance)
        self.assertIn('class="nova-receipt-ltr" dir="ltr"',self.finance)
        self.assertIn('dir="ltr"',self.finance)

    def test_receipt_content_is_safely_escaped_and_cleanup_restored(self):
        self.assertIn("const text=x=>esc(String(x??'—'))",self.finance)
        self.assertIn("window.addEventListener('afterprint',clear,{once:true})",self.finance)
        self.assertIn("document.body.classList.add('printing-nova-thermal')",self.finance)

    def test_pharmacy_and_lab_report_layouts_remain(self):
        self.assertIn('class="thermal-receipt"',self.pharmacy)
        self.assertIn('function printReport(id)',self.lab)
        self.assertIn('class="lab-print nova-clinical-print"',self.lab)

if __name__=='__main__':unittest.main()
