# coding: utf-8
"""NOVA batch 01: repeatable, fail-closed patches to CI-extracted source only.
Does not access the customer's running server or database.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
changes=[]
def decoded(s):
    return s.replace("~",chr(96)).replace("@{","$"+"{")
def patch(file,old,new,expected=1):
    path=ROOT/file; content=path.read_text(encoding="utf-8")
    old,new=decoded(old),decoded(new)
    count=content.count(old)
    if count!=expected:raise RuntimeError("BATCH01_ANCHOR_MISMATCH %s (%s, expected %s): %s"%(file,count,expected,old[:90]))
    path.write_text(content.replace(old,new),encoding="utf-8")
    changes.append(file)
def append(file,extra):
    path=ROOT/file; content=path.read_text(encoding="utf-8")
    if "NOVA_BATCH01_ADDITION" in content:raise RuntimeError("Batch applied twice")
    path.write_text(content+"\n"+decoded(extra)+"\n",encoding="utf-8")
    changes.append(file)

# Server validates sellability, independently of the client and its barcode route.
patch("pharmacy/app.py",
 "if not pkg or not pkg['active']:raise ValueError('الصنف غير موجود أو موقوف')",
 "if not pkg or not pkg['active']:raise ValueError('الصنف غير موجود أو موقوف')\n        if pkg['sale_price']<=0:raise ValueError('سعر بيع العبوة غير محدد؛ لا يجوز بيعها قبل التسعير')")
patch("pharmacy/static/ux_v14.js",
 "const found=state.products.filter(p=>p.active&&(!term?(p.available>0):searchProduct(p,term))).slice(0,45);",
 "const found=state.products.filter(p=>p.active&&p.available>0&&(!term||searchProduct(p,term))).slice(0,45);")
patch("pharmacy/static/ux_v14.js",
 "const list=found.flatMap(p=>p.packages.map(pk=>pkgTile(p,pk))).slice(0,65);",
 "const list=found.flatMap(p=>p.packages.filter(pk=>pk.sale_price>0&&pk.factor<=p.available).map(pk=>pkgTile(p,pk))).slice(0,65);")
patch("pharmacy/static/ux_v14.js",
 "if(term&&found.length&&found.every(p=>p.available<=0))el.insertAdjacentHTML('beforeend','<div class=\"madar-unavailable-tip\">الأصناف دي مسجلة في الدليل، لكن ما عندها رصيد متاح للبيع.</div>');",
 "if(term&&!list.length)el.insertAdjacentHTML('beforeend','<div class=\"madar-unavailable-tip\">لا توجد عبوة متاحة للبيع. راجع دليل الأدوية والمخزون.</div>');")
patch("pharmacy/static/app.js",
 "p.packages.filter(pk=>pk.sale_price>0).map(pk=>pkgTile(p,pk))",
 "p.packages.filter(pk=>pk.sale_price>0&&pk.factor<=p.available).map(pk=>pkgTile(p,pk))")
patch("pharmacy/static/app.js",
 "function addSale(id){let pk=skuPack(id);if(!pk)return;let r=state.saleRows.find(x=>x.package_id===Number(id));if(r)r.qty++;else state.saleRows.push({package_id:Number(id),qty:1});redraw()}",
 """function addSale(id){const pk=skuPack(id);if(!pk||!pk.product.active)return toast('الصنف غير متاح',true);
  if(pk.sale_price<=0)return toast('سعر بيع العبوة غير محدد',true);
  const r=state.saleRows.find(x=>x.package_id===Number(id));
  const other=state.saleRows.filter(x=>x.package_id!==Number(id)&&skuPack(x.package_id)?.product.id===pk.product.id).reduce((s,x)=>s+x.qty*skuPack(x.package_id).factor,0);
  if(((r?r.qty:0)+1)*pk.factor+other>pk.product.available)return toast('الرصيد لا يكفي',true);
  if(r)r.qty++;else state.saleRows.push({package_id:Number(id),qty:1});redraw()}""")
patch("pharmacy/static/app.js",
 "function qtySale(i,delta){state.saleRows[i].qty+=delta;if(state.saleRows[i].qty<=0)state.saleRows.splice(i,1);redraw()}",
 """function qtySale(i,delta){const r=state.saleRows[i];if(!r)return;const pk=skuPack(r.package_id);if(!pk)return;
  const other=state.saleRows.filter((_,j)=>j!==i).filter(x=>skuPack(x.package_id)?.product.id===pk.product.id).reduce((s,x)=>s+x.qty*skuPack(x.package_id).factor,0);
  if(delta>0&&(r.qty+delta)*pk.factor+other>pk.product.available)return toast('الرصيد لا يكفي',true);
  r.qty+=delta;if(r.qty<=0)state.saleRows.splice(i,1);redraw()}""")

# Prevent the duplicate catalog search from searching only the displayed DOM page.
# Remove the extra search field that filters only rendered DOM rows.
import re
_source=ROOT/"pharmacy/static/workstation_upgrade.js"
_text=_source.read_text(encoding="utf-8")
_new,count=re.subn(r"catalog=function\(\)\{\s*return [\s\S]*?\+madarMasterCatalogView\(\);\s*\};",
                   "catalog=function(){return madarMasterCatalogView();};",_text,count=1)
if count!=1:raise RuntimeError("BATCH01_ANCHOR_MISMATCH pharmacy duplicate search")
_source.write_text(_new,encoding="utf-8")
changes.append("pharmacy/static/workstation_upgrade.js")
# Hospital-scoped identity in pharmacy receipts and purchasing prints.
patch("pharmacy/static/app.js","<h2>مدار | MADAR</h2><b>وحدة الصيدلية</b>",
 "<h2>@{esc(window.NOVA_HOSPITAL_BRAND?.hospital_name||'اسم المستشفى')}</h2><b>وحدة الصيدلية</b><p>@{esc(window.NOVA_HOSPITAL_BRAND?.hospital_phone||'')}</p>")
patch("pharmacy/static/app.js","<h2>مدار | MADAR — الصيدلية — فاتورة مشتريات</h2>",
 "<h2>@{esc(window.NOVA_HOSPITAL_BRAND?.hospital_name||'اسم المستشفى')} — الصيدلية — فاتورة مشتريات</h2>")
patch("pharmacy/static/index.html","<title>مدار | MADAR — وحدة الصيدلية</title>","<title>NOVA — صيدلية المستشفى</title>")
patch("pharmacy/static/index.html","<h1>مدار <small>MADAR</small></h1>","<h1>NOVA <small>Hospital Pharmacy</small></h1>")
patch("pharmacy/static/index.html","منظومة مدار — إدارة الصيدلية والمخزون والمبيعات والحسابات","وحدة الصيدلية — نظام المستشفى الموحد")
append("pharmacy/static/app.js", """
// NOVA_BATCH01_ADDITION
async function loadNovaHospitalBrand(){
 try{const r=await fetch('/api/hospital/lab/brand',{credentials:'same-origin',cache:'no-store'});
 if(r.ok)window.NOVA_HOSPITAL_BRAND=await r.json();}catch(e){}
}
loadNovaHospitalBrand();
""")

# Per-employee lab pricing authority (admins always have it).
patch("hospital/core.py","\ndef create_patient(c, actor, data):",
 """
def lab_pricing_allowed(c, user_id, role):
    return role=='admin' or bool(pharmacy.one(c,
        "SELECT 1 FROM hospital_staff_extra WHERE user_id=? AND permission='lab_pricing'",(user_id,)))

def set_lab_pricing(c, actor, data):
    uid=integer(data.get('user_id'),'الموظف',1)
    enabled=data.get('enabled')
    if type(enabled) is not bool:raise ValueError('صلاحية التسعير غير صحيحة')
    member=pharmacy.one(c,'SELECT role FROM hospital_staff WHERE user_id=?',(uid,))
    if not member or member['role']!='lab':raise ValueError('صلاحية تسعير المعمل لموظف المعمل فقط')
    c.execute('BEGIN IMMEDIATE')
    try:
        if enabled:c.execute("INSERT OR IGNORE INTO hospital_staff_extra(user_id,permission) VALUES(?,'lab_pricing')",(uid,))
        else:c.execute("DELETE FROM hospital_staff_extra WHERE user_id=? AND permission='lab_pricing'",(uid,))
        track(c,actor['id'],'lab_pricing_permission_changed',uid,{'enabled':enabled})
        c.execute('COMMIT')
    except Exception:c.execute('ROLLBACK');raise
    return {'user_id':uid,'enabled':enabled}

def create_patient(c, actor, data):""")
patch("hospital/gateway.py",
 "core.require_role(role,'admin','lab');return self.reply(lab.update_test(c,user,data))",
 """core.require_role(role,'admin','lab')
                       if role=='lab' and not core.lab_pricing_allowed(c,user['id'],role) and data.get('price') is not None:
                          previous=pharmacy.one(c,'SELECT price FROM hospital_lab_tests WHERE id=?',(data.get('test_id'),))
                          if not previous or int(data['price'])!=previous['price']:raise PermissionError('لا تملك صلاحية تعديل أسعار المعمل')
                       return self.reply(lab.update_test(c,user,data))""")
patch("hospital/gateway.py",
 "core.require_role(role,'admin','lab');return self.reply(core.create_test(c,user,data),201)",
 """core.require_role(role,'admin','lab')
                       if role=='lab' and not core.lab_pricing_allowed(c,user['id'],role) and int(data.get('price') or 0)!=0:
                          raise PermissionError('لا تملك صلاحية تسعير الفحص الجديد')
                       return self.reply(core.create_test(c,user,data),201)""")
patch("hospital/gateway.py",
 "core.require_role(role,'admin');return self.reply(core.staff_list(c))",
 """core.require_role(role,'admin')
                       members=core.staff_list(c)
                       for member in members:member['lab_pricing']=core.lab_pricing_allowed(c,member['id'],member['role'])
                       return self.reply(members)""")
patch("hospital/gateway.py",
 "if path=='/api/hospital/staff-role':",
 """if path=='/api/hospital/staff-lab-pricing':
                       core.require_role(role,'admin');return self.reply(core.set_lab_pricing(c,user,data))
                    if path=='/api/hospital/staff-role':""")
patch("hospital/gateway.py",
 "if path=='/api/hospital/lab/stats':",
 """if path=='/api/hospital/lab/pricing-permission':
                       return self.reply({'allowed':core.lab_pricing_allowed(c,user['id'],role)})
                    if path=='/api/hospital/lab/stats':""")
patch("hospital/static/app.js",
 "['services-admin','الخدمات والأسعار'],['brand','هوية المستشفى']",
 "['services-admin','الخدمات والأسعار'],['catalog','أسعار وفحوصات المعمل'],['brand','هوية المستشفى']")
patch("hospital/static/app.js",
 "const jobs=[api('tests').then(r=>state.tests=r),api('orders').then(r=>state.orders=r),api('lab/brand').then(r=>state.brand=r)];",
 "const jobs=[api('tests').then(r=>state.tests=r),api('orders').then(r=>state.orders=r),api('lab/brand').then(r=>state.brand=r),api('lab/pricing-permission').then(r=>state.canLabPrice=r.allowed)];")
patch("hospital/static/app.js",
 """name="price" type="number" min="0" step="1" value="@{t.price}" required""",
 """name="price" type="number" min="0" step="1" value="@{t.price}" @{state.canLabPrice?'':'readonly title="المدير لم يمنحك صلاحية التسعير"'} required""")
patch("hospital/static/app.js",
 "['الاسم','الدخول','القسم','الحالة'],state.staff.map",
 "['الاسم','الدخول','القسم','الحالة','تسعير المعمل'],state.staff.map")
patch("hospital/static/app.js",
 """@{x.active?'نشط':'متوقف'}</td></tr>~)))""",
 """@{x.active?'نشط':'متوقف'}</td><td><input type="checkbox" data-lab-pricing="@{x.id}" @{x.lab_pricing?'checked':''} @{x.role==='lab'?'':'disabled'}></td></tr>~)))""")
patch("hospital/static/app.js",
 "if(section==='catalog'){form('test-form'",
 """if(section==='staff'){document.querySelectorAll('[data-lab-pricing]').forEach(cb=>cb.addEventListener('change',async()=>{try{await api('staff-lab-pricing',{user_id:Number(cb.dataset.labPricing),enabled:cb.checked});notice('تم تحديث صلاحية التسعير')}catch(e){notice(e.message,true);await navigate('staff')}}))}
 if(section==='catalog'){form('test-form'""")
# Hospital identity: saved logo preview and reliable decode before calling browser print.
patch("hospital/static/app.js",
 """<p class="muted small">تُحفظ الإعدادات على السيرفر. عند الطباعة تظهر الهوية المحفوظة تلقائياً.</p>""",
 """@{b.hospital_logo?'<div class="section"><b>الشعار المحفوظ:</b><img style="display:block;max-width:180px;max-height:110px;object-fit:contain" src="'+esc(b.hospital_logo)+'" alt="الشعار المحفوظ"></div>':'<p class="muted small">لم يُحفظ شعار بعد</p>'}<p class="muted small">بعد الحفظ تأكد من ظهور الشعار أعلاه.</p>""")
patch("hospital/static/app.js",
 "window.addEventListener('afterprint',cleanup,{once:true});window.print()}catch(e){notice(e.message,true)}}",
 """window.addEventListener('afterprint',cleanup,{once:true});
 await Promise.all([...area.querySelectorAll('img')].map(x=>x.decode?.().catch(()=>{})||Promise.resolve()));
 window.print()}catch(e){notice(e.message,true)}}""")
patch("hospital/static/app.js",
 "<span>نتائج الفحوصات المعملية</span></footer>",
 "<span>@{esc(contact)} · Powered by NOVA Hospital System</span></footer>")
patch("hospital/static/finance-ui.js","function financePrintInvoice(inv){if(!inv)return;",
 "async function financePrintInvoice(inv){if(!inv)return;")
patch("hospital/static/finance-ui.js",
 "<header><h1>@{esc(brand.hospital_name||'NOVA Hospital')}</h1>",
 "<header>@{brand.hospital_logo?'<img class=\"print-logo\" src=\"'+esc(brand.hospital_logo)+'\" alt=\"شعار المستشفى\">':''}<h1>@{esc(brand.hospital_name||'اسم المستشفى')}</h1>")
patch("hospital/static/finance-ui.js",
 "window.addEventListener('afterprint',cleanup,{once:true});window.print();setTimeout(cleanup,20000)",
 """window.addEventListener('afterprint',cleanup,{once:true});
 await Promise.all([...area.querySelectorAll('img')].map(x=>x.decode?.().catch(()=>{})||Promise.resolve()));
 window.print();setTimeout(cleanup,20000)""")
patch("hospital/static/finance-ui.js",
 "طلبات المعمل القديمة","طلبات المعمل الواردة — فتح الطلب للتحصيل")
patch("hospital/static/finance-ui.js",
 "كل الأسعار مبدئياً صفر حتى تحددها الإدارة؛ لا يوجد سعر افتراضي مفترض.",
 "لتسعير التحاليل من مكتبة المعمل اضغط <button type=\"button\" onclick=\"navigate('catalog')\">أسعار تحاليل المعمل</button>. بقية الأسعار مبدئياً صفر حتى تحددها الإدارة.")
dental=[
 ('DENT-FOLLOW','مراجعة أسنان','followup'),('DENT-EXT-TOOTH','خلع سن عادي','extraction'),
 ('DENT-EXT-MOLAR','خلع ضرس عادي','molar extraction'),('DENT-SURG-EXT','خلع جراحي','surgical extraction'),
 ('DENT-ROOT-REST','خلع بقايا جذور','roots'),('DENT-FILL','حشو دائم','filling'),
 ('DENT-TEMP-FILL','حشو مؤقت','temporary filling'),('DENT-ENDO','علاج عصب','root canal'),
 ('DENT-SCALE','تنظيف الجير','scaling'),('DENT-POLISH','تلميع أسنان','polishing'),
 ('DENT-PERIO','علاج لثة','periodontal'),('DENT-WHITEN','تبييض أسنان','whitening'),
 ('DENT-CROWN','تركيب طربوش','crown'),('DENT-TEMP-CROWN','طربوش مؤقت','temporary crown'),
 ('DENT-BRIDGE','جسر أسنان','bridge'),('DENT-DENTURE','طقم أسنان','denture'),
 ('DENT-REPAIR','إصلاح تركيبة','repair'),('DENT-XRAY','أشعة أسنان','dental xray'),
 ('DENT-POST','مراجعة بعد الخلع','post extraction'),('DENT-DRESS','غيار أسنان','dressing')
]
_target=ROOT/"hospital/finance.py"
_text=_target.read_text(encoding="utf-8")
_line="('dental','DENT-CONS','كشف أسنان','dental',0),"
if _text.count(_line)!=1:raise RuntimeError("Dental seed anchor missing or duplicated")
_newline="".join("  ('dental',%r,%r,%r,0),\n"%x for x in dental)
_target.write_text(_text.replace(_line,_line+"\n"+_newline),encoding="utf-8")
changes.append("hospital/finance.py")
# Update only the obsolete brand assertion in the legacy pharmacy regression suite.
_brand_test=ROOT/"pharmacy/tests/test_madar_daily_finance.py"
_t=_brand_test.read_text(encoding="utf-8")
if "مدار | MADAR" in _t:
    _brand_test.write_text(_t.replace("مدار | MADAR","NOVA_HOSPITAL_BRAND"),encoding="utf-8")
    changes.append("pharmacy/tests/test_madar_daily_finance.py")
else:raise RuntimeError("Expected legacy pharmacy branding test not found")
print("NOVA_BATCH01_PATCH_APPLIED",len(changes),len(set(changes)),sorted(set(changes)))
