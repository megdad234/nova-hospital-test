#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NOVA Batch13 — approved purchasing UX and safe unit/barcode transactions.
Runs after Batch12 against the extracted build, never the live patient database.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def put(name, transform):
    path = ROOT / name
    before = path.read_text(encoding="utf-8")
    after = transform(before)
    if before == after:
        raise RuntimeError("NOVA13_NO_CHANGE " + name)
    path.write_text(after, encoding="utf-8")

def one(src, needle, replacement, label):
    hits = src.count(needle)
    if hits != 1:
        raise RuntimeError("NOVA13_ANCHOR " + label + " " + str(hits))
    return src.replace(needle, replacement, 1)

def backend(s):
    validation = '''
    # NOVA13: strip price and barcode are explicit purchase-line actions.
    # Checked BEFORE beginning a write transaction; all changes commit with the invoice.
    purchased_ids={int(t[0]['id']) for t in checked}
    nova_unit_changes=[]
    nova_unit_promotions=[]
    seen_unit=set()
    unit_rules=p.get('nova_unit_rules') or []
    if not isinstance(unit_rules,list):raise ValueError('بيانات بيع الشرائط غير صحيحة')
    for rec in unit_rules:
        if not isinstance(rec,dict):raise ValueError('بيانات الشريط غير صحيحة')
        main_id=posint(rec.get('package_id'),'عبوة الشراء')
        count=posint(rec.get('strips'),'عدد الشرائط')
        unit_price=posint(rec.get('unit_price'),'سعر بيع الشريط')
        if main_id not in purchased_ids or main_id in seen_unit:
            raise ValueError('تعبئة الشرائط يجب أن تطابق صنفاً واحداً في الفاتورة')
        if count<2 or count>100:raise ValueError('عدد الشرائط خارج النطاق')
        main=one(c,'SELECT id,product_id,factor FROM packages WHERE id=?',(main_id,))
        # NOVA13_SAFE_CATALOG_PROMOTION: catalogue-only boxes may be defined as
        # factor=1/base_uom=علبة. Convert BEFORE receiving, within this invoice.
        # Historical products must never have their stock base unit reinterpreted.
        if main['factor']==1 and count>1:
            product=one(c,'SELECT base_uom FROM products WHERE id=?',(main['product_id'],))
            packs=query(c,'SELECT id,unit_name,factor FROM packages WHERE product_id=?',(main['product_id'],))
            history=any((
                one(c,'SELECT id FROM '+table+' WHERE '+column+'=? LIMIT 1',(main['product_id'] if column=='product_id' else main_id,))
                for table,column in [('lots','product_id'),('stock_moves','product_id'),
                                     ('purchase_lines','package_id'),('sale_lines','package_id')]
            ))
            if (not product or product['base_uom'] not in ('علبة','حبة') or
                len(packs)!=1 or packs[0]['id']!=main_id or packs[0]['unit_name']!='علبة' or history):
                raise ValueError('للصنف حركات أو تعريف عبوات سابق؛ لا يمكن تحويل وحدته تلقائياً. استخدم إجراء تحويل مخزون معتمد')
            nova_unit_promotions.append((main_id,main['product_id'],count))
            for idx,entry in enumerate(checked):
                if entry[0]['id']==main_id:
                    changed=dict(entry[0]);changed['factor']=count
                    checked[idx]=(changed,)+entry[1:]
            new_factor=1
        else:
            if main['factor']<count or main['factor']%count:
                raise ValueError('معامل تعبئة العلبة لا يقبل عدد الشرائط؛ صحح التعبئة قبل الاستلام')
            new_factor=main['factor']//count
        strip=one(c,"SELECT * FROM packages WHERE product_id=? AND unit_name='شريط'",
                  (main['product_id'],))
        if strip and (strip['factor']!=new_factor or strip['id']==main_id):
            raise ValueError('تعريف الشريط الموجود لا يطابق عدد الشرائط المدخل؛ راجع التعبئة ولا تغيّر التاريخ')
        nova_unit_changes.append((main_id,main['product_id'],new_factor,unit_price,
                                 strip['id'] if strip else None))
        seen_unit.add(main_id)
    barcode_changes=[]
    seen_barcodes=set()
    seen_packs=set()
    barcode_rows=p.get('nova_purchase_barcodes') or []
    if not isinstance(barcode_rows,list):raise ValueError('بيانات الباركود غير صحيحة')
    for rec in barcode_rows:
        if not isinstance(rec,dict):raise ValueError('تعديل باركود غير صحيح')
        pack_id=posint(rec.get('package_id'),'عبوة الباركود')
        bc=textv(rec,'barcode',80)
        if pack_id not in purchased_ids or pack_id in seen_packs:
            raise ValueError('ربط الباركود مسموح للعبوة الموجودة بالفاتورة مرة واحدة فقط')
        if bc and bc in seen_barcodes:raise ValueError('الباركود مكرر في نفس الفاتورة')
        if bc:
            other=one(c,'SELECT id FROM packages WHERE barcode=? AND id<>?',(bc,pack_id))
            if other:raise ValueError('الباركود مرتبط بعبوة أخرى؛ لا يمكن تكراره')
            seen_barcodes.add(bc)
        barcode_changes.append((pack_id,bc))
        seen_packs.add(pack_id)
'''
    s=one(s,
      "    total=sum(x[-1] for x in checked);paid=amt(p.get('paid',0),'المدفوع');method=textv(p,'payment_method',24) or 'credit'",
      validation+"    total=sum(x[-1] for x in checked);paid=amt(p.get('paid',0),'المدفوع');method=textv(p,'payment_method',24) or 'credit'",
      "validate units and barcodes before invoice")

    updates = '''
        # NOVA13: explicit strip pricing after the original Batch08 pack pricing.
        # Never change historical line prices or stock quantities; only package catalog prices.
        for main_id,pid,factor,sale_price,strip_id in nova_unit_changes:
            if strip_id is None:
                strip_id=c.execute(
                   "INSERT INTO packages(product_id,unit_name,factor,barcode,sale_price,is_default) VALUES(?,?,?,?,?,0)",
                   (pid,'شريط',factor,None,sale_price)).lastrowid
                audit(c,uid,'nova_purchase_create_strip',
                     {'purchase_id':new,'main_package_id':main_id,'strip_id':strip_id,
                      'factor':factor,'sale_price':sale_price})
            else:
                row=one(c,'SELECT sale_price FROM packages WHERE id=?',(strip_id,))
                if row['sale_price']!=sale_price:
                    c.execute('UPDATE packages SET sale_price=? WHERE id=?',(sale_price,strip_id))
                    audit(c,uid,'nova_purchase_reprice_strip',
                          {'purchase_id':new,'strip_id':strip_id,
                           'old_price':row['sale_price'],'new_price':sale_price})
        for pack_id,barcode in barcode_changes:
            before=one(c,'SELECT barcode FROM packages WHERE id=?',(pack_id,))
            if (before['barcode'] or '')!=barcode:
                c.execute('UPDATE packages SET barcode=? WHERE id=?',(barcode or None,pack_id))
                audit(c,uid,'nova_purchase_scan_barcode',
                      {'purchase_id':new,'package_id':pack_id,
                       'barcode_before':before['barcode'],'barcode_after':barcode})
'''
    # Promotions are applied atomically with purchase receipt, before stock lots.
    s=one(s,
      "        new=c.execute('INSERT INTO purchases(",
      """        # NOVA13_SAFE_CATALOG_PROMOTION — no historical quantity reinterpretation.
        for package_id,product_id,strip_count in nova_unit_promotions:
            c.execute("UPDATE products SET base_uom='شريط' WHERE id=?",(product_id,))
            c.execute("UPDATE packages SET factor=? WHERE id=?",(strip_count,package_id))
            audit(c,uid,'nova_purchase_activate_strips',
                  {'product_id':product_id,'package_id':package_id,'strips_per_box':strip_count})
        new=c.execute('INSERT INTO purchases(""",
      "promote untouched catalogue boxes inside purchase transaction")

    s=one(s,
      "        audit(c,uid,'purchase',{'id':new,'supplier':supplier,'invoice':ref,'total':total})",
      updates+"        audit(c,uid,'purchase',{'id':new,'supplier':supplier,'invoice':ref,'total':total})",
      "atomic package and barcode operations")

    quick = '''
def nova_purchase_quick_product(c,p,uid):
    """Create only a basic catalog item from purchases, without leaving an invoice."""
    name=textv(p,'name',140,True)
    if len(name)<2:raise ValueError('أدخل اسماً تجارياً واضحاً')
    if one(c,'SELECT id FROM products WHERE lower(trim(name))=lower(?)',(name,)):
        raise ValueError('هذا الاسم التجاري موجود بالفعل؛ اختر الصنف من البحث')
    barcode=textv(p,'barcode',80)
    if barcode and one(c,'SELECT id FROM packages WHERE barcode=?',(barcode,)):
        raise ValueError('الباركود مربوط بعبوة أخرى')
    strips=p.get('strips')
    factor=1
    if strips not in (None,''):
        factor=posint(strips,'عدد الشرائط في العلبة')
        if factor<2 or factor>100:raise ValueError('عدد الشرائط يجب أن يكون من 2 إلى 100')
    sku='NOVA-Q-'+uuid.uuid4().hex[:20].upper()
    prod={'sku':sku,'name':name,'generic_name':textv(p,'generic_name',160),
          'strength':textv(p,'strength',80),'manufacturer':textv(p,'manufacturer',160),
          'base_uom':'شريط' if factor>1 else 'علبة',
          'packages':[{'unit_name':'علبة','factor':factor,'barcode':barcode,
                       'sale_price':0,'is_default':1}]}
    response=create_product(c,prod,uid)
    pk=one(c,'SELECT id FROM packages WHERE product_id=?',(response['id'],))
    return {'product_id':response['id'],'package_id':pk['id']}
'''
    s=one(s, "def nova_purchase_draft_schema(c):",
          quick+"\ndef nova_purchase_draft_schema(c):", "quick add before purchase drafts")

    s=one(s,
      "'/api/v1/nova-purchase-draft-save':('purchase',lambda:nova_purchase_draft_save(c,data,u['id'])),",
      "'/api/v1/nova-purchase-quick-product':('purchase',lambda:nova_purchase_quick_product(c,data,u['id'])),\n                     '/api/v1/nova-purchase-draft-save':('purchase',lambda:nova_purchase_draft_save(c,data,u['id'])),",
      "quick add permission-gated route")
    return s

put("pharmacy/app.py",backend)

def request(s):
    return one(s,
      "items:rows,nova_sale_prices:novaPurchasePricePayload(rows),payment_method:method",
      "items:rows,nova_sale_prices:novaPurchasePricePayload(rows),nova_unit_rules:nova13UnitRules(rows),nova_purchase_barcodes:nova13Barcodes(rows),payment_method:method",
      "approved purchasing payload")
put("pharmacy/static/ux_v14.js",request)

put("pharmacy/static/nova_pharmacy_batch08.js",
    lambda s:s+"\n/* NOVA_BATCH13_APPROVED_PURCHASES */\n"+
       (ROOT/"pharmacy/static/nova_batch13_purchase.js").read_text(encoding="utf-8")+"\n")
put("pharmacy/static/style.css",
    lambda s:s+"\n"+(ROOT/"pharmacy/static/nova_batch13_purchase.css").read_text(encoding="utf-8")+"\n")

print("NOVA13_APPLIED: approved split UI, stock-first search, quick add, barcodes, strip sale price, existing invoices preserved")
