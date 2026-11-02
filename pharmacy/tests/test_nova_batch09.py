# -*- coding: utf-8 -*-
"""NOVA 09: source-backed POS regressions and admin-only financial ledger."""
import base64
import io
import unittest
import zipfile
from pathlib import Path

from tests.test_hospital_gateway import HospitalServerFixture

class NovaCollectionReportAcceptance(HospitalServerFixture,unittest.TestCase):
    def test_admin_report_matches_existing_collections_when_unfiltered(self):
        current=self.admin.get('/api/hospital/admin/reports')
        detail=self.admin.get('/api/hospital/admin/collection-detail?method=all&scope=patient')
        self.assertEqual(detail['summary']['cash_gross'],current['hospital_collections']['cash_gross'])
        self.assertEqual(detail['summary']['bank_gross'],current['hospital_collections']['bank_gross'])
        self.assertEqual(detail['summary']['cash_refunds'],current['hospital_collections']['cash_refunded'])
        self.assertEqual(detail['summary']['bank_refunds'],current['hospital_collections']['bank_refunded'])
        self.assertIn('rows',detail)
        self.assertIn('banks',detail)
        self.assertIn('staff',detail)

    def test_detailed_report_filtering_and_excel_has_actual_xlsx(self):
        for suffix in ('method=bank','method=cash','scope=insurance','scope=all&bank_id=0'):
            detail=self.admin.get('/api/hospital/admin/collection-detail?'+suffix)
            self.assertIn('summary',detail)
            self.assertIn('rows',detail)
        exp=self.admin.get('/api/hospital/admin/collection-export?scope=patient')
        raw=base64.b64decode(exp['base64'],validate=True)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertIsNone(z.testzip())
            self.assertIn('xl/workbook.xml',z.namelist())
            self.assertIn('xl/worksheets/sheet1.xml',z.namelist())
            self.assertIn('autoFilter',z.read('xl/worksheets/sheet1.xml').decode('utf-8'))
        self.assertEqual(exp['row_count'],self.admin.get('/api/hospital/admin/collection-detail')['total_rows'])

    def test_ledger_rejects_invalid_filters(self):
        for suffix in ('method=wrong','scope=wrong','bank_id=-1','staff_id=xyz','from=2026-12-10&to=2026-11-01'):
            with self.assertRaises(Exception):
                self.admin.get('/api/hospital/admin/collection-detail?'+suffix)

    def test_only_admin_can_see_bank_references(self):
        cashier=self.make_user('cashier','nova09restrictedcashier')
        with self.assertRaises(Exception):
            cashier.get('/api/hospital/admin/collection-detail')
        with self.assertRaises(Exception):
            cashier.get('/api/hospital/admin/collection-export')

class NovaPosLayoutPresence(unittest.TestCase):
    def test_compact_panels_and_held_cart_are_additive(self):
        root=Path(__file__).resolve().parents[1]
        code=(root/'static'/'nova_pharmacy_batch08.js').read_text(encoding='utf-8')
        css=(root/'static'/'style.css').read_text(encoding='utf-8')
        self.assertIn("window.novaShowHeld=async function()",code)
        self.assertIn("window.novaResumeHeld=async function",code)
        self.assertIn("window.novaHoldNow=async function",code)
        self.assertIn("closeModal();nav('pos')",code)
        self.assertIn(".nova-pos-search",css)
        self.assertIn(".nova-pos-checkout",css)
        self.assertIn("max-height:clamp(",css)

if __name__=='__main__':
    unittest.main()
