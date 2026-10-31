# coding: utf-8
"""NOVA batch 02: pharmacy purchase search, barcode and guarded unit conversion.
Only changes files extracted from the reviewed source archive on CI.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
updated=[]
def dec(s):
    return s.replace("~",chr(96)).replace("@{","$"+"{")
def change(name,old,new,count=1):
    path=ROOT/name
    content=path.read_text(encoding='utf-8')
    old,new=dec(old),dec(new)
    matches=content.count(old)
    if matches!=count:raise RuntimeError("NOVA_BATCH02_ANCHOR %s %s/%s: %s"%(name,matches,count,old[:95]))
    path.write_text(content.replace(old,new),encoding='utf-8')
    updated.append(name)
def add(name,code):
    path=ROOT/name
    content=path.read_text(encoding='utf-8')
    if "NOVA_BATCH02_ADDITION" in content:raise RuntimeError("Applied twice: "+name)
    path.write_text(content+"\n"+dec(code),encoding='utf-8')
    updated.append(name)

# The native SELECT causes popups above the field; render keyboard-friendly suggestions below.
change("pharmacy/static/ux_v14.js",
 """const found = q ? allPacks().filter(({product,pk})=>searchProduct(product,q)||normalize(pk.unit_name).includes(q)).slice(0,60) : [];
    select.replaceChildren(new Option(q?'اختر من نتائج البحث':'اكتب اسم الدواء للبحث في الدليل',''));
    for(const x of found)select.add(new Option(x.label,String(x.pk.id)));
    $('buy-count') && ($('buy-count').textContent=q?(found.length?'النتائج: '+found.length+(found.length===60?' (اكتب أكثر للتحديد)':''):'الصنف غير موجود؛ تقدر تضيفه من هنا'):'اكتب جزءاً من الاسم أو التركيز أو الباركود');
    if(found.length===1)select.value=String(found[0].pk.id);""",
 """const found=q?allPacks().filter(({product,pk})=>searchProduct(product,q)||normalize(pk.unit_name).includes(q)).slice(0,40):[];
    const selected=select.value;select.replaceChildren(new Option('اختر الصنف',''));
    for(const x of found)select.add(new Option(x.label,String(x.pk.id)));
    if(found.some(x=>String(x.pk.id)===selected))select.value=selected;
    else if(found.length===1)select.value=String(found[0].pk.id);
    const suggestions=$('buy-suggestions');
    if(suggestions){
      suggestions.innerHTML=found.map(x=>'<button type="button" class="nova-buy-suggestion" data-buy-choice="'+x.pk.id+'"><strong>'+esc(x.product.name)+'</strong><small>'+esc([x.product.strength,x.product.manufacturer,x.pk.unit_name,'×'+x.pk.factor,x.pk.barcode].filter(Boolean).join(' · '))+'</small></button>').join('')||'<p class="muted-note">لا توجد نتائج. تأكد من الاسم أو أضف صنفاً جديداً.</p>';
      suggestions.querySelectorAll('[data-buy-choice]').forEach(b=>b.onclick=()=>{select.value=b.dataset.buyChoice;
        suggestions.querySelectorAll('button').forEach(x=>x.classList.toggle('selected',x===b));});
    }
    $('buy-count')&&($('buy-count').textContent=q?'نتائج البحث: '+found.length+(found.length===40?' (اكتب أكثر للتحديد)':''):'ابدأ بكتابة الاسم أو التركيز أو باركود العبوة');""")
change("pharmacy/static/ux_v14.js",
 """<div class="field"><label for="buy-pkg">نتائج البحث</label><select id="buy-pkg"><option value="">ابحث ثم اختر الصنف</option></select></div>""",
 """<select id="buy-pkg" hidden aria-label="الصنف المختار"><option value="">اختر الصنف</option></select><div id="buy-suggestions" class="nova-buy-suggestions" aria-label="اقتراحات الأدوية"></div>""")
change("pharmacy/static/ux_v14.js",
 """<button class="btn" onclick="addBuyFromDictionary()">+ أضف للفاتورة</button><button class="btn outline" onclick="newProduct()">+ صنف جديد</button>""",
 """<button class="btn" onclick="addBuyFromDictionary()">+ أضف للفاتورة</button><button class="btn outline" onclick="purchaseBarcodeModal()">ربط باركود</button><button class="btn outline" onclick="purchasePackingPreview()">التعبئة وتكلفة الوحدات</button><button class="btn outline" onclick="newProduct()">+ صنف جديد</button>""")
add("pharmacy/static/style.css", """
/* NOVA_BATCH02_ADDITION */
.nova-buy-suggestions{grid-column:1/-1;max-height:250px;overflow-y:auto;display:grid;gap:6px;overscroll-behavior:contain}
.nova-buy-suggestion{width:100%;display:flex;align-items:center;justify-content:space-between;gap:10px;background:var(--panel,#fff);border:1px solid #cbdce3;border-radius:9px;padding:11px;text-align:right;cursor:pointer}
.nova-buy-suggestion small{opacity:.72;white-space:normal}.nova-buy-suggestion:hover,.nova-buy-suggestion.selected{background:#dcedea;border-color:#117a81}
""")
add("pharmacy/static/app.js", """
// NOVA_BATCH02_ADDITION
function purchaseBarcodeModal(){
 const pkg=skuPack(Number(v('buy-pkg')));
 if(!pkg)return toast('حدد الصنف والعبوة من نتائج البحث أولاً',true);
 modal('ربط باركود — '+pkg.product.name,
   '<div class="help">التعبئة: '+esc(pkg.unit_name)+' ×'+pkg.factor+' '+esc(pkg.product.base_uom)+'. سعر البيع لن يتغير.</div>'+
   f('باركود هذه العبوة','nova-purchase-barcode','text',pkg.barcode||'')+
   '<button class="btn section" onclick="savePurchaseBarcode('+pkg.id+')">حفظ الباركود للمرات القادمة</button>');
}
async function savePurchaseBarcode(id){
 try{const pkg=skuPack(id);if(!pkg)throw Error('الصنف غير معروف');
   await api('package',{package_id:id,barcode:v('nova-purchase-barcode'),sale_price:pkg.sale_price});
   closeModal();await refresh();nav('purchase');toast('تم حفظ الباركود في نفس عبوة الصنف');
 }catch(e){toast(e.message,true)}
}
function purchasePackingPreview(){
 const pkg=skuPack(Number(v('buy-pkg')));
 if(!pkg)return toast('حدد الصنف والعبوة أولاً',true);
 modal('تعبئة الدواء وحساب سعر الشريط والحبة — '+pkg.product.name,
  '<p class="help">التعبئة المسجلة حالياً: '+esc(pkg.unit_name)+' ×'+pkg.factor+' '+esc(pkg.product.base_uom)+
  '. راجع التعبئة الفعلية على عبوة المصنع قبل التصحيح.</p>'+
  f('عدد الشرائط في العلبة','nova-strips','number',Math.max(1,Math.round(pkg.factor/10)),'min="1" oninput="calculateNovaPack()"')+
  f('عدد الحبات في الشريط','nova-pills','number',10,'min="1" oninput="calculateNovaPack()"')+
  f('سعر شراء العلبة (ج.س)','nova-box-cost','number',0,'min="0" oninput="calculateNovaPack()"')+
  '<div id="nova-pack-calculation" class="help section"></div>'+
  '<p class="warnbox">التصحيح مسموح فقط لو وحدة التعبئة ما دخلت في معاملات سابقة. أي تعبئة مستخدمة تحتاج ترحيل آمن منفصل.</p>'+
  '<button class="btn section" onclick="saveNovaPackageFactor('+pkg.id+')">حفظ عدد الحبات الصحيح لهذه العبوة</button>');
 calculateNovaPack();
}
function calculateNovaPack(){
 const strips=Math.max(1,Math.trunc(Number(v('nova-strips'))||1)),pills=Math.max(1,Math.trunc(Number(v('nova-pills'))||1));
 const cost=Math.max(0,Number(v('nova-box-cost'))||0),box=strips*pills;
 const el=$('nova-pack-calculation');
 if(el)el.textContent='العلبة: '+fmt(cost)+' ج.س | الشريط: '+(cost/strips).toFixed(2)+' ج.س | الحبة: '+(cost/box).toFixed(2)+' ج.س | إجمالي الحبات بالعلبة: '+box;
}
async function saveNovaPackageFactor(id){
 try{const pk=skuPack(id);if(!pk)throw Error('عبوة غير معروفة');
   if(!['حبة','قطعة'].includes(pk.product.base_uom))throw Error('التصحيح الآلي للشرائط متاح فقط للأدوية التي وحدتها الأساسية حبة/قطعة');
   const strips=Math.trunc(Number(v('nova-strips'))),pills=Math.trunc(Number(v('nova-pills')));
   if(!Number.isInteger(strips)||!Number.isInteger(pills)||strips<1||pills<1||strips*pills>100000)throw Error('أدخل عدد الشرائط والحبات بصورة صحيحة');
   await api('package-factor',{package_id:id,factor:strips*pills});
   closeModal();await refresh();nav('purchase');toast('تم تصحيح التعبئة دون تعديل الفواتير السابقة');
 }catch(e){toast(e.message,true)}
}
""")
# Re-fetch identity after sign in: an unauthorized request on first page load is insufficient.
change("pharmacy/static/app.js","await refresh();renderRoleMenu();nav(can('sale')",
       "await refresh();await loadNovaHospitalBrand();renderRoleMenu();nav(can('sale')")
# Backend: update factor only before ANY use, and audit; never overwrite history.
change("pharmacy/app.py",
 "\ndef edit_package(c,p,uid):",
 """
def correct_package_factor(c,p,uid):
    package_id=posint(p.get('package_id'),'العبوة')
    new_factor=posint(p.get('factor'),'عدد وحدات التعبئة')
    if new_factor>100000:raise ValueError('معامل التعبئة غير منطقي')
    begin(c)
    try:
        pk=one(c,'SELECT * FROM packages WHERE id=?',(package_id,))
        if not pk:raise ValueError('العبوة غير موجودة')
        if pk['factor']==new_factor:
            finish(c);return {'id':package_id,'factor':new_factor,'unchanged':True}
        for table in ('purchase_lines','sale_lines'):
            used=one(c,'SELECT 1 AS found FROM '+table+' WHERE package_id=? LIMIT 1',(package_id,))
            if used:raise ValueError('هذه التعبئة مستخدمة في فواتير سابقة؛ لا يمكن تغيير معاملها. يلزم تعريف عبوة جديدة ومراجعة المخزون.')
        # Opening inventory and existing product stock must never be reinterpreted silently.
        if one(c,'SELECT 1 FROM lots WHERE product_id=? AND qty_base>0 LIMIT 1',(pk['product_id'],)):
            raise ValueError('الدواء لديه مخزون سابق؛ يتطلب تصحيح التعبئة تسوية موثقة قبل التغيير.')
        c.execute('UPDATE packages SET factor=? WHERE id=?',(new_factor,package_id))
        audit(c,uid,'correct_package_factor',{'package_id':package_id,'old_factor':pk['factor'],'new_factor':new_factor})
        finish(c)
    except Exception:rollback(c);raise
    return {'id':package_id,'factor':new_factor}

def edit_package(c,p,uid):""")
change("pharmacy/app.py",
 "'/api/v1/package':('catalog',lambda:edit_package(c,data,u['id'])),",
 "'/api/v1/package':('catalog',lambda:edit_package(c,data,u['id'])),\n                     '/api/v1/package-factor':('catalog',lambda:correct_package_factor(c,data,u['id'])),")
# Make real loading errors visible, never silently proceed with empty products.
change("pharmacy/static/app.js",
 "catch(e){state[key]=key==='reports'?{}:[]}",
 "catch(e){if(key==='products')throw Error('فشل تحميل مخزون الصيدلية؛ لا يمكن متابعة البيع قبل إصلاح الاتصال');state[key]=key==='reports'?{}:[];toast('تحذير: تعذر تحميل '+key,true)}")
# Remove legacy naming from patient-facing pharmacy screen.
change("pharmacy/static/index.html","MADAR","NOVA",count=3) if False else None
print("NOVA_BATCH02_PATCH_APPLIED",len(updated),sorted(set(updated)))
