#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NOVA unified selling prices. Apply only to extracted build source after Batch15.
The rollback branch is untouched. Does not operate on any patient/pharmacy DB.
"""
from pathlib import Path
import ast
APP=Path('pharmacy/app.py')
UI=Path('pharmacy/static/app.js')
source=APP.read_text(encoding='utf-8')
if 'NOVA_UNIFIED_PRICE_ENGINE_V1' in source:
    raise RuntimeError('Pricing engine already applied')

def one(s,old,new,tag):
    if s.count(old)!=1:
        raise RuntimeError('NOVA_PRICE_ANCHOR '+tag+' '+str(s.count(old)))
    return s.replace(old,new,1)

def function(s,name,definition):
    nodes=[n for n in ast.parse(s).body
           if isinstance(n,ast.FunctionDef) and n.name==name]
    if len(nodes)!=1:raise RuntimeError('NOVA_PRICE_FUNCTION '+name)
    lines=s.splitlines(keepends=True)
    return ''.join(lines[:nodes[0].lineno-1])+definition.strip()+'\n\n'+''.join(lines[nodes[0].end_lineno:])

engine=r'''
# NOVA_UNIFIED_PRICE_ENGINE_V1
# Price is per package in integer SDG. Linked pricing uses factor ratios.
def nova_pricing_apply(c,entries):
    if not isinstance(entries,list) or not entries or len(entries)>10000:
        raise ValueError('اختر أسعار بيع صحيحة لاعتمادها')
    targets={}
    checked=set()
    for entry in entries:
        if not isinstance(entry,dict):
            raise ValueError('بيانات التسعير غير صحيحة')
        pid=posint(entry.get('package_id'),'العبوة')
        if pid in checked:raise ValueError('تكرار عبوة في عملية التسعير')
        checked.add(pid)
        price=amt(entry.get('price'),'سعر البيع')
        if price<=0 or price>1000000000000:
            raise ValueError('سعر البيع يجب أن يكون موجباً وصحيحاً')
        row=one(c,'SELECT * FROM packages WHERE id=?',(pid,))
        if not row:raise ValueError('العبوة غير موجودة')
        expected=entry.get('old_sale_price')
        if expected is not None and row['sale_price']!=amt(expected,'السعر السابق'):
            raise ValueError('سعر الصنف تغير في جهاز آخر؛ أعد تحميل الأسعار')
        mode=entry.get('mode','linked')
        if mode not in ('linked','independent'):
            raise ValueError('طريقة ربط الأسعار غير صحيحة')
        related=query(c,'SELECT * FROM packages WHERE product_id=? ORDER BY id',(row['product_id'],))
        snapshot=entry.get('expected_related')
        if snapshot is not None:
            if not isinstance(snapshot,dict) or set(str(p['id']) for p in related)!=set(str(k) for k in snapshot):
                raise ValueError('تعبئات الصنف تغيرت؛ أعد فتح شاشة التسعير')
            for pack in related:
                if pack['sale_price']!=amt(snapshot[str(pack['id'])],'سعر التعبئة السابق'):
                    raise ValueError('تم تغيير سعر تعبئة مرتبطة في جهاز آخر؛ أعد المعاينة')
        origin=int(row['factor'])
        if origin<=0:raise ValueError('معامل تحويل العبوة غير صالح')
        if mode=='linked':
            proposed=[]
            for pack in related:
                factor=int(pack['factor'])
                if factor<=0:raise ValueError('معامل تحويل التعبئة غير صالح')
                # Exact nearest SDG; half-up, without floating-point money.
                new=max(1,(2*price*factor+origin)//(2*origin))
                if new>1000000000000:raise ValueError('السعر المقترح خارج الحد المسموح')
                proposed.append((pack,new))
        else:proposed=[(row,price)]
        for pack,value in proposed:
            key=int(pack['id'])
            if key in targets and targets[key][1]!=value:
                raise ValueError('سعران متعارضان لتعبئات الصنف نفسه؛ راجع العلبة والشريط')
            targets[key]=(pack,value)
    updates=[]
    for key,(pack,value) in sorted(targets.items()):
        old=int(pack['sale_price'])
        if old==value:continue
        if c.execute('UPDATE packages SET sale_price=? WHERE id=? AND sale_price=?',
                     (value,key,old)).rowcount!=1:
            raise ValueError('تغير السعر أثناء الحفظ؛ أعد المحاولة')
        updates.append({'package_id':key,'product_id':int(pack['product_id']),
                        'unit_name':str(pack['unit_name']),'old':old,'new':value})
    return updates

def nova_unified_prices(c,p,uid):
    begin(c)
    try:
        updated=nova_pricing_apply(c,p.get('items'))
        if not updated:raise ValueError('لا توجد أسعار متغيرة')
        audit(c,uid,'unified_sale_prices',{'source':'unified_editor','updates':updated})
        finish(c)
        return {'updated':len(updated),'items':updated}
    except:
        rollback(c)
        raise

def nova_price_revision(c):
    r=c.execute("""SELECT COALESCE(MAX(id),0) FROM audit WHERE action IN
      ('unified_sale_prices','manual_sale_price_update','price_update',
       'bulk_supplier_price_list_approved','bulk_supplier_price_list_rollback',
       'purchase_unified_prices','purchase_sale_price','purchase_auto_price_unit',
       'nova_purchase_reprice_strip','update_package')""").fetchone()
    return {'revision':int(r[0]) if r else 0}
'''
source=one(source,'def nova_bulk_unpriced(c,p,uid):',
           engine+'\ndef nova_bulk_unpriced(c,p,uid):','engine')

source=function(source,'nova_manual_sale_price',r'''
def nova_manual_sale_price(c,p,uid):
    pid=posint(p.get('package_id'),'العبوة')
    new=amt(p.get('new_sale_price'),'سعر البيع')
    old=amt(p.get('old_sale_price'),'السعر السابق')
    if new==old:raise ValueError('السعر الجديد مطابق للقديم')
    begin(c)
    try:
        updates=nova_pricing_apply(c,[{'package_id':pid,'price':new,
             'old_sale_price':old,'mode':p.get('mode','linked'),
             'expected_related':p.get('expected_related')}])
        if not updates:raise ValueError('لا توجد أسعار متغيرة')
        audit(c,uid,'manual_sale_price_update',
              {'package_id':pid,'old':old,'new':new,'updates':updates})
        finish(c)
        return {'updated':True,'package_id':pid,'new_sale_price':new,'affected':updates}
    except:
        rollback(c)
        raise
''')

source=function(source,'nova_price_list_approve',r'''
def nova_price_list_approve(c,p,uid):
    import hmac as _hmac
    items=p.get('items')
    if not isinstance(items,list) or not items or len(items)>20000:
        raise ValueError('لا توجد أسعار للاعتماد')
    if len({str(x.get('package_id')) for x in items if isinstance(x,dict)})!=len(items):
        raise ValueError('عبوة مكررة في الاعتماد')
    begin(c)
    try:
        proposed=[]
        for item in items:
            if not isinstance(item,dict):raise ValueError('صف غير صالح')
            pid=posint(item.get('package_id'),'العبوة')
            old=amt(item.get('old_sale_price'),'السعر القديم')
            new=amt(item.get('proposed_sale_price'),'السعر المقترح')
            if not _hmac.compare_digest(str(item.get('approval_token','')),
                                        nova_price_signature(pid,old,new)):
                raise ValueError('يجب معاينة الأسعار أولاً قبل اعتمادها')
            if not 0<new<=1000000000000:raise ValueError('سعر بيع غير صالح')
            stocked=one(c,"""SELECT pk.id FROM packages pk
                 JOIN products pr ON pr.id=pk.product_id
                 WHERE pk.id=? AND pr.active=1
                 AND EXISTS (SELECT 1 FROM lots l WHERE l.product_id=pr.id
                 AND l.status='sellable' AND l.qty_base>0
                 AND (l.expiry='' OR l.expiry>=date('now')))""",(pid,))
            if not stocked:raise ValueError('الصنف لم يعد متاحاً؛ أعد المعاينة')
            proposed.append({'package_id':pid,'old_sale_price':old,
                             'price':new,'mode':'linked'})
        updates=nova_pricing_apply(c,proposed)
        if not updates:raise ValueError('لا توجد أسعار متغيرة')
        audit(c,uid,'bulk_supplier_price_list_approved',
              {'updates':[{'package_id':x['package_id'],'old':x['old'],
                           'new':x['new']} for x in updates],
               'source_items':len(items),'linked':True})
        finish(c)
        return {'updated':len(updates),'saved':True}
    except:
        rollback(c)
        raise
''')

source=function(source,'nova_sale_price_catalog',r'''
def nova_sale_price_catalog(c,p):
    q=str(p.get('q') or '').strip()[:100]
    if not q:return {'rows':[],'count':0}
    pattern='%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
    hits=c.execute("""SELECT DISTINCT pr.id FROM products pr
        WHERE pr.active=1 AND (pr.name LIKE ? ESCAPE '\\'
        OR pr.strength LIKE ? ESCAPE '\\'
        OR EXISTS(SELECT 1 FROM packages pk WHERE pk.product_id=pr.id
                  AND pk.barcode LIKE ? ESCAPE '\\'))
        ORDER BY pr.name LIMIT 60""",(pattern,pattern,pattern)).fetchall()
    if not hits:return {'rows':[],'count':0}
    ids=[int(x[0]) for x in hits]
    placeholders=','.join('?' for _ in ids)
    rows=c.execute("""SELECT pk.id AS package_id,pk.product_id,pr.name,
        pr.strength,pk.unit_name,pk.factor,pk.is_default,pk.barcode,pk.sale_price
        FROM packages pk JOIN products pr ON pr.id=pk.product_id
        WHERE pk.product_id IN ("""+placeholders+""")
        ORDER BY pr.name,pk.factor DESC,pk.id""",ids).fetchall()
    return {'rows':[dict(r) for r in rows],'count':len(ids)}
''')

source=function(source,'nova_manual_price_history',r'''
def nova_manual_price_history(c):
    import json as _json
    rows=c.execute("""SELECT id,created_at,user_id,action,details FROM audit
        WHERE action IN ('unified_sale_prices','manual_sale_price_update',
        'price_update','purchase_unified_prices','bulk_supplier_price_list_approved',
        'bulk_supplier_price_list_rollback') ORDER BY id DESC LIMIT 100""").fetchall()
    out=[]
    for r in rows:
        d=_json.loads(r['details'])
        affected=d.get('updates') or d.get('changed') or []
        if affected:
            for line in affected:
                out.append({'id':r['id'],'created_at':r['created_at'],
                     'user_id':r['user_id'],'action':r['action'],
                     'package_id':line.get('package_id'),
                     'old':line.get('old',line.get('before')),
                     'new':line.get('new',line.get('after'))})
        else:
            out.append({'id':r['id'],'created_at':r['created_at'],
                     'user_id':r['user_id'],'action':r['action'],
                     'package_id':d.get('package_id'),'old':d.get('old'),
                     'new':d.get('new')})
    return {'rows':out[:100]}
''')

source=function(source,'edit_package',r'''
def edit_package(c,p,uid):
    pid=posint(p.get('package_id'),'معرف العبوة')
    begin(c)
    try:
        row=one(c,'SELECT * FROM packages WHERE id=?',(pid,))
        if not row:raise ValueError('العبوة غير موجودة')
        barcode=textv(p,'barcode',80) if 'barcode' in p else (row['barcode'] or '')
        updates=[]
        desired=row['sale_price']
        if 'sale_price' in p:
            desired=amt(p['sale_price'],'سعر البيع')
            if desired!=row['sale_price']:
                if 'old_sale_price' not in p:
                    raise ValueError('افتح شاشة تعديل الأسعار الجديدة لتجنب إعادة سعر قديم')
                updates=nova_pricing_apply(c,[{'package_id':pid,'price':desired,
                    'old_sale_price':p['old_sale_price'],
                    'mode':p.get('mode','linked')}])
        if barcode!=(row['barcode'] or ''):
            c.execute('UPDATE packages SET barcode=? WHERE id=?',(barcode or None,pid))
        audit(c,uid,'update_package',{'id':pid,'barcode_before':row['barcode'],
              'barcode_after':barcode,'old_price':row['sale_price'],
              'new_price':desired,'updates':updates})
        finish(c)
        return {'id':pid,'updated_prices':updates}
    except:
        rollback(c)
        raise
''')

source=function(source,'price_update',r'''
def price_update(c,p,uid):
    items=p.get('items',[])
    if not isinstance(items,list) or not items:raise ValueError('لا توجد أسعار لاعتمادها')
    entries=[{'package_id':x.get('package_id'),'price':x.get('price'),
              'old_sale_price':x.get('old_sale_price'),
              'mode':x.get('mode','linked')} for x in items]
    begin(c)
    try:
        changes=nova_pricing_apply(c,entries)
        audit(c,uid,'price_update',{'changed':[{'package_id':r['package_id'],
            'before':r['old'],'after':r['new']} for r in changes]})
        finish(c)
        return {'updated':len(changes),'items':changes}
    except:
        rollback(c)
        raise
''')

# Purchase writers from Batch08/13 already ran within the purchase transaction.
# The NEW purchase sale price is authoritative for every linked pack and strip.
marker="        audit(c,uid,'purchase',{'id':new,'supplier':supplier,'invoice':ref,'total':total})"
source=one(source,marker,r'''
        if price_updates:
            chosen=[{'package_id':pack_id,'price':price,'mode':'linked'}
                    for pack_id,price in price_updates.items()]
            changed=nova_pricing_apply(c,chosen)
            if changed:
                audit(c,uid,'purchase_unified_prices',
                      {'purchase_id':new,'updates':changed,
                       'rule':'latest_purchase_price_is_authoritative'})
'''+marker,'purchase linked prices')

source=one(source,'    checked=[]\n    rx_needed=False',
    """    quotes=p.get('nova_price_quotes')
    if quotes is not None and not isinstance(quotes,dict):
        raise ValueError('أسعار سلة البيع غير صحيحة؛ أعد تحميل نقطة البيع')
    checked=[]
    rx_needed=False""",'sale quote input')
source=one(source,
    "        checked.append((pkg,qty,qty*pkg['sale_price']))",
    """        if quotes is not None:
            expected=quotes.get(str(pkg['id']))
            if expected is None or amt(expected,'السعر المعروض')!=pkg['sale_price']:
                raise ValueError('تغير سعر بيع دواء بالسلة؛ راجع السعر الجديد قبل اعتماد الفاتورة')
        checked.append((pkg,qty,qty*pkg['sale_price']))""",'sale quote check')
source=one(source,
    "        existed=one(c,'SELECT id,ref,total FROM sales WHERE idempotency=?',(idemp,))",
    """        if quotes is not None:
            for pkg,qty,amount in checked:
                latest=one(c,'SELECT sale_price FROM packages WHERE id=?',(pkg['id'],))
                if not latest or latest['sale_price']!=pkg['sale_price']:
                    raise ValueError('تغير السعر أثناء الحفظ؛ حدّث شاشة البيع قبل الاعتماد')
        existed=one(c,'SELECT id,ref,total FROM sales WHERE idempotency=?',(idemp,))""",'sale quote locked')

source=one(source,
    "'/api/v1/nova-sale-price-catalog':'prices','/api/v1/nova-manual-price-history':'prices',",
    "'/api/v1/nova-price-revision':'prices','/api/v1/nova-sale-price-catalog':'prices','/api/v1/nova-manual-price-history':'prices',",
    'read permission')
source=one(source,
    "'/api/v1/nova-sale-price-catalog':lambda:nova_sale_price_catalog(c,{'q':parse_qs(urlparse(self.path).query).get('q',[''])[0]}),",
    "'/api/v1/nova-price-revision':lambda:nova_price_revision(c),\n                     '/api/v1/nova-sale-price-catalog':lambda:nova_sale_price_catalog(c,{'q':parse_qs(urlparse(self.path).query).get('q',[''])[0]}),",
    'revision GET')
source=one(source,
    "'/api/v1/nova-manual-sale-price':('prices',lambda:nova_manual_sale_price(c,data,u['id'])),",
    "'/api/v1/nova-unified-prices':('prices',lambda:nova_unified_prices(c,data,u['id'])),\n                     '/api/v1/nova-manual-sale-price':('prices',lambda:nova_manual_sale_price(c,data,u['id'])),",
    'unified POST')

ast.parse(source)
APP.write_text(source,encoding='utf-8')

js=UI.read_text(encoding='utf-8')
js=one(js,
    "async function confirmSale(){try{if(!state.saleRows.length)throw Error('السلة فارغة');",
    """async function confirmSale(){try{if(!state.saleRows.length)throw Error('السلة فارغة');
 const original=state.saleRows.map(r=>({id:r.package_id,price:skuPack(r.package_id)?.sale_price}));
 state.products=await api('products');
 if(original.some(x=>skuPack(x.id)?.sale_price!==x.price)){
     redraw();throw Error('تغير سعر بيع دواء بالسلة؛ راجع الإجمالي الجديد قبل تأكيد الفاتورة مجدداً');
 }""",'POS refresh before checkout')
js=one(js,'prescription,items:state.saleRows,discount:saleDiscount(),partner_id:',
     'prescription,items:state.saleRows,nova_price_quotes:Object.fromEntries(state.saleRows.map(r=>[String(r.package_id),skuPack(r.package_id)?.sale_price])),discount:saleDiscount(),partner_id:',
     'POS quote to backend')
js=one(js,"barcode:v('edit-pk-barcode'),sale_price:n('edit-pk-price')",
    "barcode:v('edit-pk-barcode'),sale_price:n('edit-pk-price'),old_sale_price:skuPack(id)?.sale_price,mode:'linked'",
    'package compare-and-swap')
js=one(js,
    "async function approvePrices(){try{let items=[...document.querySelectorAll('[data-price]')].map(el=>({package_id:Number(el.dataset.price),price:Number(el.value)})).filter(x=>x.price!==skuPack(x.package_id).sale_price);",
    """async function approvePrices(){try{let items=[...document.querySelectorAll('[data-price]')].map(el=>({package_id:Number(el.dataset.price),price:Number(el.value),old_sale_price:skuPack(Number(el.dataset.price)).sale_price})).filter(x=>x.price!==x.old_sale_price);
 const groups={};for(const x of items){const product=skuPack(x.package_id).product.id;groups[product]=(groups[product]||0)+1}
 items=items.map(x=>({...x,mode:groups[skuPack(x.package_id).product.id]>1?'independent':'linked'}));""",
    'legacy price grid')
UI.write_text(js,encoding='utf-8')

client=Path('.github/ci/nova_unified_pricing_ui.js').read_text(encoding='utf-8')
Path('pharmacy/static/nova_manual_price_editor.js').write_text(client,encoding='utf-8')
print('NOVA_UNIFIED_PRICING_APPLIED')
