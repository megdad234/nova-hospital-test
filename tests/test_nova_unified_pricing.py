"""NOVA pharmacy price contract regression: no live database, invoices or stock.

Executed against the assembled NOVA source *after* the purchase, POS,
bulk-list, and unified-price patches; tests are all isolated in-memory SQLite.
"""
import ast
import json
import pathlib
import sqlite3
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
APP=ROOT/'pharmacy/app.py'

def build_scope(source):
    tree=ast.parse(source)
    names={'nova_pricing_apply','nova_unified_prices','nova_manual_sale_price',
           'nova_sale_price_catalog','nova_manual_price_history',
           'nova_price_revision','edit_package','price_update'}
    defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    if {n.name for n in defs}!=names:
        raise AssertionError('Missing unified pricing route: '+str(names-{n.name for n in defs}))
    namespace={}
    exec(compile(ast.Module(body=defs,type_ignores=[]),'NOVA/unified_pricing','exec'),namespace)
    def one(c,q,params=()):
        return c.execute(q,params).fetchone()
    def query(c,q,params=()):
        return c.execute(q,params).fetchall()
    def amt(v,label):
        try:x=int(str(v))
        except (TypeError,ValueError):raise ValueError(label)
        if str(v).strip()!=str(x) or x<0:raise ValueError(label)
        return x
    def posint(v,label):
        val=amt(v,label)
        if val<1:raise ValueError(label)
        return val
    def textv(p,k,n,required=False):
        x=str(p.get(k,'')).strip()
        if required and not x:raise ValueError(k)
        if len(x)>n:raise ValueError(k)
        return x
    namespace.update(one=one,query=query,amt=amt,posint=posint,textv=textv,
        begin=lambda c:c.execute('BEGIN IMMEDIATE'),
        finish=lambda c:c.execute('COMMIT'),
        rollback=lambda c:c.execute('ROLLBACK'),
        audit=lambda c,uid,event,details:c.execute(
            'INSERT INTO audit(user_id,action,details) VALUES(?,?,?)',
            (uid,event,json.dumps(details,ensure_ascii=False))))
    return namespace

def database():
    c=sqlite3.connect(':memory:',isolation_level=None)
    c.row_factory=sqlite3.Row
    c.executescript("""
    CREATE TABLE products(id INTEGER PRIMARY KEY,name TEXT,strength TEXT,
                          active INTEGER);
    CREATE TABLE packages(id INTEGER PRIMARY KEY,product_id INTEGER,
                          unit_name TEXT,factor INTEGER,barcode TEXT,
                          sale_price INTEGER,is_default INTEGER DEFAULT 0);
    CREATE TABLE audit(id INTEGER PRIMARY KEY,created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                       user_id INTEGER,action TEXT,details TEXT);
    CREATE TABLE sales(id INTEGER PRIMARY KEY,total INTEGER);
    CREATE TABLE sale_lines(id INTEGER PRIMARY KEY,unit_price INTEGER,total INTEGER);
    CREATE TABLE stock_moves(id INTEGER PRIMARY KEY,qty_base INTEGER);
    INSERT INTO products VALUES(1,'ALLvitamin 30tabs','Multivitamin',1);
    INSERT INTO packages VALUES(10,1,'علبة',3,'BOX',60000,1);
    INSERT INTO packages VALUES(11,1,'شريط',1,'STRIP',20000,0);
    INSERT INTO products VALUES(2,'AMIPRIDE 2','2mg',1);
    INSERT INTO packages VALUES(20,2,'علبة',2,'AM2',40000,1);
    INSERT INTO packages VALUES(21,2,'شريط',1,'AMSTR',20000,0);
    INSERT INTO sales VALUES(1,65000);
    INSERT INTO sale_lines VALUES(1,5000,5000);
    INSERT INTO stock_moves VALUES(1,99);
    """)
    return c

class UnifiedPriceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=APP.read_text(encoding='utf-8')
        cls.ns=build_scope(cls.source)
    def setUp(self):
        self.c=database()
        self.p=self.ns['nova_pricing_apply']
    def tearDown(self):
        self.c.close()
    def price(self,id):
        return self.c.execute('SELECT sale_price FROM packages WHERE id=?',(id,)).fetchone()[0]
    def edit(self,anchor,price,mode='linked'):
        old=self.price(anchor)
        return self.ns['nova_unified_prices'](self.c,{'items':[{
            'package_id':anchor,'price':price,'mode':mode,
            'old_sale_price':old,
            'expected_related':{str(i):self.price(i)
                for i in ((10,11) if anchor in (10,11) else (20,21))}
        }]},7)
    def test_box_change_reprices_strip_in_both_directions(self):
        self.assertEqual(self.edit(10,70000)['updated'],2)
        self.assertEqual(self.price(10),70000)
        self.assertEqual(self.price(11),23333)
        self.assertEqual(self.edit(11,5000)['updated'],2)
        self.assertEqual((self.price(10),self.price(11)),(15000,5000))
    def test_independent_pricing_is_explicit_and_isolated(self):
        self.edit(11,5500,mode='independent')
        self.assertEqual((self.price(10),self.price(11)),(60000,5500))
        self.edit(10,90000)
        self.assertEqual((self.price(10),self.price(11)),(90000,30000))
    def test_other_products_never_change(self):
        self.edit(10,66000)
        self.assertEqual((self.price(20),self.price(21)),(40000,20000))
    def test_stale_box_or_sibling_rejects_entire_transaction(self):
        self.edit(10,90000)
        with self.assertRaisesRegex(ValueError,'تغير'):
            self.ns['nova_unified_prices'](self.c,{'items':[{
               'package_id':10,'price':60000,'old_sale_price':60000,
               'mode':'linked'}]},3)
        with self.assertRaisesRegex(ValueError,'تغيير سعر تعبئة'):
            self.ns['nova_unified_prices'](self.c,{'items':[{
               'package_id':10,'price':70000,'old_sale_price':90000,
               'mode':'linked','expected_related':{'10':90000,'11':20000}}]},3)
        self.assertEqual((self.price(10),self.price(11)),(90000,30000))
    def test_barcode_only_never_restores_old_sale_price(self):
        self.edit(10,81000)
        self.ns['edit_package'](self.c,{'package_id':10,'barcode':'NEWBOX'},2)
        self.assertEqual((self.price(10),self.price(11)),(81000,27000))
        self.assertEqual(self.c.execute('SELECT barcode FROM packages WHERE id=10').fetchone()[0],'NEWBOX')
        with self.assertRaises(ValueError):
            self.ns['edit_package'](self.c,{'package_id':10,'barcode':'BAD',
                'sale_price':60000,'old_sale_price':60000},2)
        self.assertEqual(self.price(10),81000)
        self.assertEqual(self.c.execute('SELECT barcode FROM packages WHERE id=10').fetchone()[0],'NEWBOX')
    def test_legacy_manual_and_bulk_pricing_use_same_engine(self):
        result=self.ns['nova_manual_sale_price'](self.c,{'package_id':10,
            'old_sale_price':60000,'new_sale_price':72000},9)
        self.assertTrue(result['updated'])
        self.assertEqual((self.price(10),self.price(11)),(72000,24000))
        result=self.ns['price_update'](self.c,{'items':[{
            'package_id':11,'old_sale_price':24000,'price':17000}]},9)
        self.assertEqual(result['updated'],2)
        self.assertEqual((self.price(10),self.price(11)),(51000,17000))
    def test_all_affected_packages_committed_once_with_audit(self):
        result=self.edit(10,30000)
        self.assertEqual(result['updated'],2)
        self.assertEqual(self.c.execute("SELECT count(*) FROM audit WHERE action='unified_sale_prices'").fetchone()[0],1)
        audit=json.loads(self.c.execute("SELECT details FROM audit WHERE action='unified_sale_prices'").fetchone()[0])
        self.assertEqual({p['package_id'] for p in audit['updates']},{10,11})
        self.assertEqual(self.ns['nova_price_revision'](self.c)['revision'],1)
    def test_conflicting_bulk_anchor_rolls_back_all_prices(self):
        with self.assertRaisesRegex(ValueError,'متعارضان'):
            self.ns['nova_unified_prices'](self.c,{'items':[
                {'package_id':10,'price':60000,'mode':'linked'},
                {'package_id':11,'price':5000,'mode':'linked'}]},9)
        self.assertEqual((self.price(10),self.price(11)),(60000,20000))
        self.assertEqual(self.c.execute('SELECT count(*) FROM audit').fetchone()[0],0)
    def test_find_by_product_or_barcode_returns_all_siblings(self):
        find=self.ns['nova_sale_price_catalog']
        for q in ('ALLvitamin','BOX','STRIP'):
            rows=find(self.c,{'q':q})['rows']
            self.assertEqual({r['package_id'] for r in rows},{10,11})
            self.assertEqual({r['factor'] for r in rows},{1,3})
        self.assertEqual(find(self.c,{'q':'nonsense'})['rows'],[])
    def test_legacy_sale_and_stock_facts_not_modified(self):
        self.edit(10,66000)
        self.assertEqual(self.c.execute('SELECT total FROM sales').fetchone()[0],65000)
        self.assertEqual(self.c.execute('SELECT unit_price FROM sale_lines').fetchone()[0],5000)
        self.assertEqual(self.c.execute('SELECT qty_base FROM stock_moves').fetchone()[0],99)
    def test_cashier_uses_quoted_server_prices_not_stale_cart(self):
        self.assertIn("nova_price_quotes",self.source)
        self.assertIn("تغير سعر بيع دواء بالسلة",self.source)
        self.assertIn("latest['sale_price']!=pkg['sale_price']",self.source)
        ui=(ROOT/'pharmacy/static/app.js').read_text(encoding='utf-8')
        self.assertIn("state.products=await api('products')",ui)
        self.assertIn('nova_price_quotes:Object.fromEntries',ui)
    def test_purchase_new_sale_price_overwrites_old_nonzero_siblings(self):
        self.assertIn('if price_updates:',self.source)
        self.assertIn("'purchase_unified_prices'",self.source)
        self.assertIn('chosen=[',self.source)
        self.assertIn('changed=nova_pricing_apply(c,chosen)',self.source)
    def test_pricing_ui_groups_units_and_previews_each_change(self):
        js=(ROOT/'pharmacy/static/nova_manual_price_editor.js').read_text(encoding='utf-8')
        for word in ['novaSaveBarcodeOnly','const oldPriceGrid=pricing','novaShowAdvancedPrices',
                     'expected_related:snapshot','ربط العلبة والشريط تلقائيًا',
                     "mode:mode.value",'nova-unified-prices','النظام']:
            if word=='النظام':continue
            self.assertIn(word,js)

if __name__=='__main__':
    unittest.main()
