# -*- coding: utf-8 -*-
"""NOVA Batch12 insurance: synthetic central DB, no real patient information."""
import tempfile
import unittest
import uuid
from datetime import date,timedelta
from pathlib import Path
import app
from hospital import core

class NovaPharmacyInsuranceAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.original=(app.DB,app.DATA)
        app.DATA=Path(self.temp.name);app.DB=app.DATA/'nova12.sqlite'
        app.init_db()
        core.init_schema()
        self.c=app.db_connect()
        app.bootstrap(self.c,{'username':'nova12owner','full_name':'Synthetic Owner',
            'password':'SyntheticPassword98765'})
        self.uid=app.one(self.c,'SELECT id FROM users LIMIT 1')['id']
        self.insurer=app.create_party(self.c,{'name':'NOVA12 Synthetic Insurance',
            'kind':'authority','phone':'000000'},'authority',self.uid)['id']
        self.contract=self.c.execute("""INSERT INTO insurance_contracts(
            authority_id,code,coverage_default,starts,ends,created_at)
            VALUES(?,?,?,?,?,?)""",
            (self.insurer,'N12-INSURER',80,(date.today()-timedelta(days=4)).isoformat(),
             (date.today()+timedelta(days=365)).isoformat(),app.now())).lastrowid
        self.product=app.create_product(self.c,{
            'sku':'NOVA12-'+uuid.uuid4().hex[:6],'name':'Synthetic Treatment',
            'base_uom':'حبة',
            'packages':[{'unit_name':'علبة','factor':10,'sale_price':1000,
             'barcode':'N12'+uuid.uuid4().hex[:10],'is_default':1}]},self.uid)['id']
        self.pack=app.one(self.c,'SELECT id FROM packages WHERE product_id=?',(self.product,))['id']
        supplier=app.create_party(self.c,{'name':'NOVA12 Supplier'},'supplier',self.uid)['id']
        app.purchase(self.c,{'supplier_id':supplier,'invoice_ref':'NOVA12-INPUT',
           'items':[{'package_id':self.pack,'qty':20,'received':20,
                     'unit_cost':500,'expiry':(date.today()+timedelta(days=365)).isoformat()}]},self.uid)
        self.person=core.create_patient(self.c,{'id':self.uid},
           {'full_name':'NOVA Synthetic Patient','phone':'0012345678'})

    def tearDown(self):
        self.c.close()
        app.DB,app.DATA=self.original
        self.temp.cleanup()

    def enroll(self,card='0000123'):
        return app.nova_insured_enroll(self.c,{
            'contract_id':self.contract,'patient_id':self.person['id'],
            'card_no':card,'relation':'primary','eligibility_confirmed':True},self.uid)

    def sale(self,member,coverage=80,verified=True,extra=None):
        payload={'idempotency':uuid.uuid4().hex,
                 'items':[{'package_id':self.pack,'qty':1}],
                 'partner_id':member['partner_id'],'authority_id':self.insurer,
                 'insurance_contract_id':self.contract,
                 'insurance_member_id':member['member_id'],
                 'coverage':coverage,'insurance_verified':verified,
                 'payments':[{'method':'cash','amount':1000-round(1000*coverage/100)}]}
        if extra:payload.update(extra)
        return app.sell(self.c,payload,self.uid)

    def test_existing_patient_card_sale_and_immutable_history(self):
        card=self.enroll()
        self.assertEqual(card['card_no'],'0000123')
        self.assertEqual(card['patient_id'],self.person['id'])
        self.assertEqual(card['coverage'],80)
        found=app.nova_insured_search(self.c,self.contract,'0000123')
        self.assertEqual(len(found),1)
        sale=self.sale(card)
        self.assertEqual(sale['covered'],800)
        history=next(x for x in app.sales(self.c) if x['id']==sale['id'])
        self.assertEqual(history['insurance_details']['patient_no'],self.person['patient_no'])
        self.assertEqual(history['insurance_details']['card_no'],'0000123')
        app.nova_insured_enroll(self.c,{'contract_id':self.contract,
            'patient_id':self.person['id'],'card_no':'00009999',
            'eligibility_confirmed':True},self.uid)
        history=next(x for x in app.sales(self.c) if x['id']==sale['id'])
        self.assertEqual(history['insurance_details']['card_no'],'0000123')
        self.assertEqual(app.one(self.c,'SELECT COUNT(*) n FROM hospital_patients')['n'],1)

    def test_bad_member_or_unchecked_eligibility_never_decrements_stock(self):
        card=self.enroll()
        before=app.one(self.c,'SELECT COALESCE(SUM(qty_base),0) total FROM lots')['total']
        for case in [
          {'insurance_verified':False},
          {'insurance_member_id':999999},
          {'coverage':70,'payments':[{'method':'cash','amount':300}]},
          {'insurance_contract_id':None}
        ]:
            with self.assertRaises((ValueError,PermissionError)):
                self.sale(card,extra=case)
        after=app.one(self.c,'SELECT COALESCE(SUM(qty_base),0) total FROM lots')['total']
        self.assertEqual(before,after)
        self.assertEqual(app.one(self.c,'SELECT COUNT(*) n FROM sales')['n'],0)

    def test_duplicate_card_rejected_for_other_patient(self):
        self.enroll('ABC0001')
        other=core.create_patient(self.c,{'id':self.uid},
            {'full_name':'Second Synthetic Patient'})
        with self.assertRaises(ValueError):
            app.nova_insured_enroll(self.c,{'contract_id':self.contract,
               'patient_id':other['id'],'card_no':'abc0001','eligibility_confirmed':True},self.uid)
        self.assertEqual(app.one(self.c,'SELECT COUNT(*) n FROM nova_pharmacy_insured_cards')['n'],1)

    def test_new_patient_created_in_same_hospital_database(self):
        row=app.nova_insured_enroll(self.c,{
             'contract_id':self.contract,'full_name':'New Synthetic Insured Person',
             'phone':'0123000','card_no':'P-5000','eligibility_confirmed':True},self.uid)
        self.assertTrue(row['patient_no'].startswith('P-'))
        self.assertEqual(app.one(self.c,'SELECT COUNT(*) n FROM hospital_patients')['n'],2)
        with self.assertRaises(ValueError):
            app.nova_insured_enroll(self.c,{
                'contract_id':self.contract,'full_name':'New Synthetic Insured Person',
                'phone':'0123000','card_no':'P-5001','eligibility_confirmed':True},self.uid)
        self.assertEqual(app.one(self.c,'SELECT COUNT(*) n FROM hospital_patients')['n'],2)

    def test_monthly_detail_claim_and_regular_cash_sale_unchanged(self):
        card=self.enroll()
        self.sale(card)
        app.sell(self.c,{'idempotency':uuid.uuid4().hex,
           'items':[{'package_id':self.pack,'qty':1}],
           'payments':[{'method':'cash','amount':1000}]},self.uid)
        period=date.today().strftime('%Y-%m')
        report=app.nova_insurance_monthly_detail(self.c,self.insurer,period)
        self.assertEqual(report['invoice_count'],1)
        self.assertEqual(report['covered_invoices_total'],800)
        self.assertEqual(report['rows'][0]['card_no'],'0000123')
        claim=app.claim_create(self.c,{'authority_id':self.insurer,'period':period},self.uid)
        self.assertEqual(claim['total'],800)
        report=app.nova_insurance_monthly_detail(self.c,self.insurer,period)
        self.assertEqual(report['invoice_count'],1)
        self.assertEqual(report['covered_invoices_total'],800)
        self.assertEqual(report['rows'][0]['claim_id'],claim['id'])

if __name__=='__main__':
    unittest.main()
