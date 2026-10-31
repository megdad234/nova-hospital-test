# coding: utf-8
"""NOVA batch 03: audited identity cleanup and end-to-end regression checks."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
files=[]
def replace(file,old,new):
    p=ROOT/file;data=p.read_text(encoding='utf-8')
    if data.count(old)!=1:raise RuntimeError("NOVA_BATCH03 missing anchor "+file+": "+old[:70])
    p.write_text(data.replace(old,new),encoding='utf-8');files.append(file)

# Remove MADAR name from remaining visible pharmacy page labels; keep code internals intact.
page=ROOT/"pharmacy/static/index.html"
html=page.read_text(encoding="utf-8")
html=html.replace("مدار","NOVA").replace("MADAR","NOVA")
page.write_text(html,encoding="utf-8");files.append("pharmacy/static/index.html")

# Existing pharmacy logo asset may be from upstream; use hospital logo after authenticated brand read.
replace("pharmacy/static/app.js",
 "if(r.ok)window.NOVA_HOSPITAL_BRAND=await r.json();",
 """if(r.ok){window.NOVA_HOSPITAL_BRAND=await r.json();
   const brand=window.NOVA_HOSPITAL_BRAND;
   if(brand.hospital_logo)document.querySelectorAll('img.brand-logo').forEach(img=>{img.src=brand.hospital_logo;img.alt=brand.hospital_name||'شعار المستشفى'});
   if(brand.hospital_name){const title=document.querySelector('.sidebar .brand h1');if(title)title.textContent=brand.hospital_name;}
 }""")
# Input and document display from hospital owner must not inherit unrelated upstream iconography.
style=ROOT/"pharmacy/static/style.css"
style.write_text(style.read_text(encoding="utf-8")+
 "\n/* NOVA batch03: do not show historical upstream logo until hospital branding is loaded */\n"
 ".login-card .brand-logo:not([src^='data:']),.sidebar .brand-logo:not([src^='data:']){display:none}\n",encoding="utf-8")
files.append("pharmacy/static/style.css")

# Reject impossible expiry dates on positive inventory corrections; negative writeoffs still possible.
replace("pharmacy/app.py",
 "if diff==0 or abs(diff)>10_000_000:raise ValueError('أدخل فرق جرد صالح')",
 """if diff==0 or abs(diff)>10_000_000:raise ValueError('أدخل فرق جرد صالح')
    try:
        expiry_date=date.fromisoformat(expiry)
    except ValueError:
        raise ValueError('تاريخ الصلاحية غير صحيح')
    if diff>0 and expiry_date<=date.today():
        raise ValueError('لا يمكن إضافة كمية متاحة للبيع بصلاحية منتهية أو بتاريخ اليوم')""")

pharmacy_test='''import tempfile
import unittest
import uuid
from pathlib import Path
from datetime import date,timedelta
import app

class NovaPurchaseAndSellSafety(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db,self.data=app.DB,app.DATA
        app.DATA=Path(self.tmp.name);app.DB=app.DATA/'test.sqlite3';app.init_db()
        self.c=app.db_connect()
        app.bootstrap(self.c,{'username':'novaowner','full_name':'NOVA Tester','password':'TestPassword12345'})
        self.uid=app.one(self.c,'SELECT id FROM users LIMIT 1')['id']
        self.pid=app.create_product(self.c,{'sku':'NOVA-TEST-01','name':'NOVA synthetic medicine',
           'base_uom':'حبة','packages':[{'unit_name':'علبة','factor':20,'barcode':'PKTEST100','sale_price':0,'is_default':1}]},self.uid)['id']
        self.pack=app.one(self.c,'SELECT id FROM packages WHERE product_id=?',(self.pid,))['id']
        self.supplier=app.create_party(self.c,{'name':'NOVA test supplier'},'supplier',self.uid)['id']
        self.expiry=(date.today()+timedelta(days=360)).isoformat()
    def tearDown(self):
        self.c.close();app.DB,self.data_old= self.db,self.data
        app.DATA=self.data;self.tmp.cleanup()
    def test_correct_unused_pack_and_preserve_used_pack(self):
        app.correct_package_factor(self.c,{'package_id':self.pack,'factor':30},self.uid)
        self.assertEqual(app.one(self.c,'SELECT factor FROM packages WHERE id=?',(self.pack,))['factor'],30)
        app.purchase(self.c,{'supplier_id':self.supplier,'invoice_ref':'NOVA-PUR-1',
           'items':[{'package_id':self.pack,'qty':1,'unit_cost':5000,'expiry':self.expiry}]},self.uid)
        with self.assertRaises(ValueError):
            app.correct_package_factor(self.c,{'package_id':self.pack,'factor':40},self.uid)
        self.assertEqual(app.one(self.c,'SELECT factor FROM packages WHERE id=?',(self.pack,))['factor'],30)
        self.assertEqual(app.one(self.c,'SELECT SUM(qty_base) n FROM lots WHERE product_id=?',(self.pid,))['n'],30)
    def test_zero_sale_price_rejected_on_server(self):
        app.purchase(self.c,{'supplier_id':self.supplier,'invoice_ref':'NOVA-PUR-2',
           'items':[{'package_id':self.pack,'qty':1,'unit_cost':5000,'expiry':self.expiry}]},self.uid)
        with self.assertRaisesRegex(ValueError,'سعر بيع'):
            app.sell(self.c,{'idempotency':uuid.uuid4().hex,
                'items':[{'package_id':self.pack,'qty':1}],'payments':[]},self.uid)
        self.assertEqual(app.one(self.c,'SELECT COUNT(*) n FROM sales')['n'],0)

if __name__=='__main__':unittest.main()
'''
# The created tests run in the same original suite as the existing Windows tests.
test=ROOT/"pharmacy/tests/test_nova_batch03.py"
if test.exists():raise RuntimeError("Unexpected existing test")
test.write_text(pharmacy_test,encoding="utf-8")
files.append("pharmacy/tests/test_nova_batch03.py")

hospital_test='''import unittest
import urllib.error
from tests.test_hospital_gateway import HospitalServerFixture

class NovaLabPriceRightsAndDentistry(HospitalServerFixture,unittest.TestCase):
    def test_admin_controls_lab_price_privilege(self):
        labtech=self.make_user('lab','novaLabPrice')
        staff=self.admin.get('/api/hospital/staff')
        uid=next(s['id'] for s in staff if s['username']=='novaLabPrice')
        cbc=next(x for x in self.admin.get('/api/hospital/tests') if x['code']=='CBC')
        with self.assertRaises(urllib.error.HTTPError) as err:
            labtech.post('/api/hospital/lab/test',{'test_id':cbc['id'],'price':3211})
        self.assertEqual(err.exception.code,403)
        self.admin.post('/api/hospital/staff-lab-pricing',{'user_id':uid,'enabled':True})
        result=labtech.post('/api/hospital/lab/test',{'test_id':cbc['id'],'price':3211})
        self.assertEqual(self.admin.get('/api/hospital/lab/profile/'+str(cbc['id']))['price'],3211)
        self.admin.post('/api/hospital/staff-lab-pricing',{'user_id':uid,'enabled':False})
        with self.assertRaises(urllib.error.HTTPError) as err:
            labtech.post('/api/hospital/lab/test',{'test_id':cbc['id'],'price':3222})
        self.assertEqual(err.exception.code,403)
    def test_dental_services_seeded_and_idempotent(self):
        services=self.admin.get('/api/hospital/services')
        codes={x['code'] for x in services}
        self.assertTrue({'DENT-CONS','DENT-ENDO','DENT-SCALE','DENT-EXT-MOLAR'}.issubset(codes))
        self.assertGreaterEqual(len([x for x in services if x.get('category_code')=='dental']),20)

if __name__=='__main__':unittest.main()
'''
test=ROOT/"tests/test_nova_batch03.py"
if test.exists():raise RuntimeError("Unexpected existing test")
test.write_text(hospital_test,encoding="utf-8")
files.append("tests/test_nova_batch03.py")
# Update the obsolete upstream-brand check to the newly required hospital identity.
legacy=ROOT/"pharmacy/tests/test_hospital_brand.py"
source=legacy.read_text(encoding="utf-8")
if "مدار | MADAR" not in source:raise RuntimeError("Expected obsolete upstream brand assertion missing")
legacy.write_text(source.replace("مدار | MADAR","NOVA — صيدلية المستشفى"),encoding="utf-8")
files.append("pharmacy/tests/test_hospital_brand.py")
print("NOVA_BATCH03_PATCH_APPLIED",files)
