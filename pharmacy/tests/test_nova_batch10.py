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

    def test_thermal_receipt_uses_separate_80mm_print_document(self):
        self.assertIn("function novaPrintThermalDocument(receiptHTML)",self.finance)
        self.assertIn("frame.srcdoc=",self.finance)
        self.assertIn("'body{width:80mm!important",self.finance)
        self.assertIn("'.nova-thermal-v2{width:72mm!important",self.finance)
        self.assertIn("const heightMM=Math.max(85,Math.min(900,",self.finance)
        self.assertIn("page.textContent='@page{size:80mm '+heightMM+'mm;margin:0}'",self.finance)
        self.assertIn("win.focus();win.print()",self.finance)
        self.assertNotIn("document.body.classList.add('printing-nova-thermal')",self.finance)

    def test_hospital_a4_and_lab_printing_remain_separate(self):
        self.assertIn("function financePrintInvoice(inv)",self.finance)
        self.assertIn("document.body.classList.add('printing-lab')",self.finance)
        self.assertIn("body.printing-lab",self.css)
        self.assertIn("@page{size:A4;margin:13mm}",self.css)
        self.assertIn("class=\"lab-print nova-clinical-print\"",self.lab)

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
        self.assertIn("win.addEventListener('afterprint',cleanup,{once:true})",self.finance)
        self.assertIn("frame.remove()",self.finance)


    def test_pharmacy_thermal_ticket_prints_in_isolated_page_not_browser_layout(self):
        self.assertIn('function novaPrintPharmacyThermalDocument(receiptHTML,paperWidth)',self.pharmacy)
        self.assertIn("source.classList.contains('thermal-receipt')",self.pharmacy)
        self.assertIn("source.classList.contains('receipt-test')",self.pharmacy)
        self.assertIn("paper==='thermal58'?58:80",self.pharmacy)
        self.assertIn("frame.srcdoc=",self.pharmacy)
        self.assertIn("win.focus();win.print()",self.pharmacy)
        self.assertIn("const heightMM=Math.max(85,Math.min(2000,",self.pharmacy)
        self.assertIn("page.textContent='@page{size:'+width+'mm '+heightMM+'mm;margin:0}'",self.pharmacy)
        self.assertIn("document.body.classList.add('printing-receipt')",self.pharmacy)
        self.assertIn("if(paper==='a4'||",self.pharmacy)

    def test_pharmacy_and_lab_report_layouts_remain(self):
        self.assertIn('class="thermal-receipt"',self.pharmacy)
        self.assertIn('function printReport(id)',self.lab)
        self.assertIn('class="lab-print nova-clinical-print"',self.lab)

if __name__=='__main__':unittest.main()
