# -*- coding: utf-8 -*-
"""NOVA Batch08 integration acceptance on disposable pharmacy DB only."""
import tempfile
import unittest
import uuid
from datetime import date,timedelta
from pathlib import Path
import app

class NovaPurchaseWorkflowRecovery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.old_db,self.old_data=app.DB,app.DATA
        app.DATA=Path(self.temp.name)
        app.DB=app.DATA/'batch08.sqlite3'
        app.init_db()
        self.c=app.db_connect()
        app.bootstrap(self.c,{'username':'nova_owner08','full_name':'NOVA Pharmacy Test','password':'TestPassword1234567'})
        self.uid=app.one(self.c,'SELECT id FROM users')['id']
        self.product=app.create_product(self.c,{
            'sku':'NOVA08-'+uuid.uuid4().hex[:7],'name':'NOVA Synthetic Medicine',
            'base_uom':'حبة','packages':[
                {'unit_name':'علبة','factor':10,'barcode':'B08'+uuid.uuid4().hex[:12],
                 'sale_price':0,'is_default':1},
                {'unit_name':'حبة','factor':1,'barcode':'P08'+uuid.uuid4().hex[:12],
                 'sale_price':0}
            ]},self.uid)['id']
        self.box=app.one(self.c,"SELECT id FROM packages WHERE product_id=? AND unit_name='علبة'",(self.product,))['id']
        self.piece=app.one(self.c,"SELECT id FROM packages WHERE product_id=? AND unit_name='حبة'",(self.product,))['id']
        self.supplier=app.create_party(self.c,{'name':'NOVA synthetic supplier'},'supplier',self.uid)['id']
        self.expiry=(date.today()+timedelta(days=260)).isoformat()

    def tearDown(self):
        self.c.close()
        app.DB,app.DATA=self.old_db,self.old_data
        self.temp.cleanup()

    def purchase(self,ref,price=1250):
        return app.purchase(self.c,{
            'supplier_id':self.supplier,'invoice_ref':ref,
            'items':[{'package_id':self.box,'qty':2,'received':2,'unit_cost':1000,
                      'expiry':self.expiry}],
            'nova_sale_prices':[{'package_id':self.box,'price':price}]
        },self.uid)

    def test_purchase_sets_price_and_available_units_atomically(self):
        self.purchase('NOVA08-PRICE-1')
        box=app.one(self.c,'SELECT sale_price FROM packages WHERE id=?',(self.box,))
        piece=app.one(self.c,'SELECT sale_price FROM packages WHERE id=?',(self.piece,))
        self.assertEqual(box['sale_price'],1250)
        self.assertEqual(piece['sale_price'],125)
        pro=next(p for p in app.catalog(self.c) if p['id']==self.product)
        self.assertEqual(pro['available'],20)
        sale=app.sell(self.c,{'idempotency':uuid.uuid4().hex,
            'items':[{'package_id':self.box,'qty':1}],
            'payments':[{'method':'cash','amount':1250}]},self.uid)
        self.assertEqual(sale['total'],1250)
        pro=next(p for p in app.catalog(self.c) if p['id']==self.product)
        self.assertEqual(pro['available'],10)

    def test_drafts_are_server_owned_and_do_not_touch_inventory(self):
        draft=app.nova_purchase_draft_save(self.c,{'label':'Test resume',
          'draft':{'supplier_id':self.supplier,'items':[{'package_id':self.box,'qty':5,
                           'unit_cost':1000,'expiry':self.expiry}]}},self.uid)
        self.assertFalse(draft['stock_changed'])
        self.assertEqual(len(app.nova_purchase_draft_list(self.c,self.uid)),1)
        self.assertEqual(app.one(self.c,'SELECT COUNT(*) n FROM purchases')['n'],0)
        self.assertEqual(app.one(self.c,'SELECT COALESCE(SUM(qty_base),0) n FROM lots')['n'],0)
        app.nova_purchase_draft_delete(self.c,{'draft_id':draft['draft_id']},self.uid)
        self.assertEqual(len(app.nova_purchase_draft_list(self.c,self.uid)),0)

    def test_invalid_prices_roll_back_invoice_and_stock(self):
        with self.assertRaises(ValueError):
            app.purchase(self.c,{'supplier_id':self.supplier,'invoice_ref':'NOVA08-BAD',
                'items':[{'package_id':self.box,'qty':1,'unit_cost':1000,'expiry':self.expiry}],
                'nova_sale_prices':[{'package_id':99999999,'price':0}]},self.uid)
        self.assertEqual(app.one(self.c,'SELECT COUNT(*) n FROM purchases')['n'],0)
        self.assertEqual(app.one(self.c,'SELECT COUNT(*) n FROM lots')['n'],0)

    def test_business_report_costs_sold_stock_not_all_purchases(self):
        self.purchase('NOVA08-REPORT')
        app.sell(self.c,{'idempotency':uuid.uuid4().hex,
            'items':[{'package_id':self.box,'qty':1}],
            'payments':[{'method':'cash','amount':1250}]},self.uid)
        app.expense_create(self.c,{'category':'مصاريف تشغيل','description':'Synthetic Expense',
                                   'amount':20,'method':'cash'},self.uid)
        d=date.today().isoformat()
        rep=app.nova_pharmacy_business_report(self.c,d,d)
        self.assertEqual(rep['purchases_gross'],2000)
        self.assertEqual(rep['sales_gross'],1250)
        self.assertEqual(rep['sold_cost'],1000)
        self.assertEqual(rep['gross_profit'],250)
        self.assertEqual(rep['expenses'],20)
        self.assertEqual(rep['operating_result'],230)
        self.assertEqual(rep['patient_cash_collected'],1250)

if __name__=='__main__':
    unittest.main()
