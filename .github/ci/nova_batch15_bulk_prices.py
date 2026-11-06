"""Integrate guarded bulk price preview and approval into patched NOVA pharmacy."""
from pathlib import Path
p=Path("pharmacy/app.py")
s=p.read_text(encoding="utf-8")
anchor="def nova_bulk_unpriced(c,p,uid):"
assert s.count(anchor)==1
helpers=r'''
import secrets as _nova_secrets
import hmac as _nova_hmac
import hashlib as _nova_hashlib
_nova_price_preview_secret=_nova_secrets.token_bytes(32)

def nova_price_signature(package_id,old,new):
    message=f"{int(package_id)}:{int(old)}:{int(new)}".encode('ascii')
    return _nova_hmac.new(_nova_price_preview_secret,message,_nova_hashlib.sha256).hexdigest()

def nova_price_list_file_rows(p):
    """Parse a bounded CSV or XLSX payload on the local server."""
    import base64 as _base64
    import csv as _csv
    import io as _io
    filename=str(p.get('filename') or '').lower()
    encoded=p.get('content_base64')
    if not isinstance(encoded,str) or len(encoded)>8_000_000:
        raise ValueError('ملف الأسعار كبير أو غير صالح')
    try:
        raw=_base64.b64decode(encoded,validate=True)
    except Exception:
        raise ValueError('تعذر قراءة الملف')
    if len(raw)>6_000_000:raise ValueError('الملف يتجاوز الحد المسموح')
    if filename.endswith('.csv'):
        try:content=raw.decode('utf-8-sig')
        except UnicodeDecodeError:content=raw.decode('cp1256')
        records=_csv.reader(_io.StringIO(content))
    elif filename.endswith('.xlsx'):
        try:
            from openpyxl import load_workbook
        except ImportError:
            raise ValueError('دعم Excel غير مثبت على السيرفر')
        wb=load_workbook(_io.BytesIO(raw),read_only=True,data_only=True)
        if len(wb.sheetnames)!=1:
            wb.close()
            raise ValueError('ملف Excel يجب أن يحتوي على ورقة واحدة')
        records=wb.active.iter_rows(values_only=True)
    else:raise ValueError('الصيغ المدعومة CSV و XLSX')
    try:
        header=next(iter(records))
        aliases={'name':('name','trade name','product','اسم الصنف','الاسم التجاري','الصنف'),
                 'purchase_price':('purchase_price','purchase price','price','السعر','سعر الشراء'),
                 'strength':('strength','التركيز'),'pack':('pack','العبوة'),
                 'barcode':('barcode','باركود')}
        normalized=[str(h or '').strip().casefold() for h in header]
        cols={key:next((i for i,h in enumerate(normalized) if h in names),None)
              for key,names in aliases.items()}
        if cols['name'] is None or cols['purchase_price'] is None:
            raise ValueError('يجب وجود عمود الاسم التجاري والسعر')
        rows=[]
        for i,values in enumerate(records,2):
            if i>20001:raise ValueError('الملف يتجاوز 20 ألف صنف')
            row={key:str(values[idx] if idx is not None and idx<len(values) and values[idx] is not None else '').strip()
                 for key,idx in cols.items()}
            if row['name']:
                row['line']=i
                rows.append(row)
        return {'rows':rows,'count':len(rows)}
    finally:
        if filename.endswith('.xlsx'):wb.close()

def nova_price_list_preview(c,p):
    """Read-only, exact-match preview. Never creates purchases or stock movements."""
    from decimal import Decimal, ROUND_HALF_UP
    rows=p.get('rows')
    if not isinstance(rows,list) or not 0<len(rows)<=20000:
        raise ValueError('قائمة الأسعار فارغة أو كبيرة')
    pct=p.get('markup_percent')
    if pct is not None:
        pct=Decimal(str(pct))
        if not pct.is_finite() or pct<0 or pct>1000:raise ValueError('نسبة الربح غير صحيحة')
    def norm(x):
        return ''.join(str(x or '').casefold().split())
    catalog_rows=c.execute("""SELECT pk.id,pk.factor,pk.sale_price,pk.barcode,
        pr.name,pr.strength,pr.form,pr.manufacturer,pk.unit_name
        FROM packages pk JOIN products pr ON pr.id=pk.product_id
        WHERE pr.active=1""").fetchall()
    result=[]
    for i,row in enumerate(rows):
        if not isinstance(row,dict):raise ValueError('صف غير صالح')
        name=str(row.get('name') or '').strip()
        price=Decimal(str(row.get('purchase_price') or 0))
        if not price.is_finite() or price<=0 or price>1000000000000:raise ValueError('سعر شراء غير صالح')
        strength=norm(row.get('strength'));pack=norm(row.get('pack'))
        barcode=str(row.get('barcode') or '').strip()
        hits=[]
        for pk in catalog_rows:
            if barcode and pk['barcode'] and barcode==str(pk['barcode']):
                if strength and norm(pk['strength'])!=strength:continue
                if pack and norm(pk['unit_name'])!=pack:continue
                hits.append(pk);continue
            if norm(pk['name'])!=norm(name):continue
            if strength and norm(pk['strength'])!=strength:continue
            if pack and norm(pk['unit_name'])!=pack:continue
            hits.append(pk)
        record={'line':row.get('line',i+1),'name':name,'purchase_price':str(price),
                'status':'review','selected':False,'candidates':[int(x['id']) for x in hits[:10]]}
        if len(hits)==1 and (barcode or (strength and pack)):
            pk=hits[0]
            # Actual purchase history, never previously imported price lists.
            last=c.execute("""SELECT pl.id,pl.amount,pl.qty,pl.bonus,pl.received,src.factor
                FROM purchase_lines pl JOIN packages src ON src.id=pl.package_id
                WHERE src.product_id=(SELECT product_id FROM packages WHERE id=?)
                AND (pl.received+pl.bonus)>0 ORDER BY pl.id DESC LIMIT 1""",(pk['id'],)).fetchone()
            if last and (last['qty']+last['bonus'])>0:
                old_cost=Decimal(last['amount'])*Decimal(pk['factor'])/(Decimal(last['qty']+last['bonus'])*Decimal(last['factor']))
                # Uploaded price is explicitly per matched target package.
                if pct is None:
                    if old_cost<=0:
                        record['status']='missing_cost'
                        result.append(record);continue
                    multiplier=Decimal(pk['sale_price'])/old_cost
                else:multiplier=1+pct/100
                proposed=int((price*multiplier).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
                if 0<proposed<=1000000000000:
                    record.update({'status':'matched','package_id':int(pk['id']),
                        'old_sale_price':int(pk['sale_price']),'old_purchase_cost':str(old_cost),
                        'last_purchase_line_id':int(last['id']),
                        'proposed_sale_price':proposed,
                        'approval_token':nova_price_signature(pk['id'],pk['sale_price'],proposed),
                        'selected':proposed!=int(pk['sale_price'])})
        result.append(record)
    counts={x:sum(r['status']==x for r in result) for x in ('matched','review','missing_cost')}
    return {'rows':result,'counts':counts,'saved':False}

def nova_price_list_history(c):
    records=c.execute("""SELECT id,created_at,user_id,action,details FROM audit
        WHERE action IN ('bulk_supplier_price_list_approved','bulk_supplier_price_list_rollback')
        ORDER BY id DESC LIMIT 100""").fetchall()
    import json as _json
    return [{'id':r['id'],'created_at':r['created_at'],'user_id':r['user_id'],
             'action':r['action'],'details':_json.loads(r['details'])} for r in records]

def nova_price_list_rollback(c,p,uid):
    import json as _json
    source_id=int(p.get('audit_id',0))
    if source_id<=0:raise ValueError('عملية الاعتماد غير صحيحة')
    begin(c)
    try:
        row=c.execute("""SELECT details FROM audit WHERE id=?
            AND action='bulk_supplier_price_list_approved'""",(source_id,)).fetchone()
        if not row:raise ValueError('عملية الاعتماد غير موجودة')
        already=c.execute("""SELECT 1 FROM audit
            WHERE action='bulk_supplier_price_list_rollback'
            AND json_extract(details,'$.source_audit_id')=? LIMIT 1""",(source_id,)).fetchone()
        if already:raise ValueError('تم التراجع عن العملية مسبقاً')
        updates=_json.loads(row['details'])['updates']
        for x in updates:
            pid=int(x['package_id']);old=int(x['old']);new=int(x['new'])
            if c.execute('UPDATE packages SET sale_price=? WHERE id=? AND sale_price=?',
                (old,pid,new)).rowcount!=1:
                raise ValueError('بعض الأسعار تغيرت لاحقاً؛ لا يمكن التراجع تلقائياً')
        audit(c,uid,'bulk_supplier_price_list_rollback',
              {'source_audit_id':source_id,'updates':updates})
        finish(c)
        return {'restored':len(updates),'source_audit_id':source_id}
    except Exception:
        rollback(c)
        raise

def nova_manual_sale_price(c,p,uid):
    """Update a package selling price only, with an atomic audit record."""
    from decimal import Decimal, InvalidOperation
    try:
        pid=int(p.get('package_id',0))
        old=Decimal(str(p.get('old_sale_price')))
        new=Decimal(str(p.get('new_sale_price')))
    except (TypeError,ValueError,InvalidOperation):
        raise ValueError('بيانات السعر غير صحيحة')
    if pid<=0 or not old.is_finite() or not new.is_finite():
        raise ValueError('بيانات السعر غير صحيحة')
    if old!=old.to_integral_value() or new!=new.to_integral_value():
        raise ValueError('السعر يجب أن يكون عدداً صحيحاً')
    if old<0 or new<=0 or new>1000000000000 or old==new:
        raise ValueError('السعر الجديد غير صالح')
    begin(c)
    try:
        row=c.execute('SELECT id FROM packages WHERE id=?',(pid,)).fetchone()
        if not row:raise ValueError('العبوة غير موجودة')
        n=c.execute('UPDATE packages SET sale_price=? WHERE id=? AND sale_price=?',
                    (int(new),pid,int(old))).rowcount
        if n!=1:raise ValueError('السعر تغير؛ أعد تحميل الصنف')
        audit(c,uid,'manual_sale_price_update',
              {'package_id':pid,'old':int(old),'new':int(new)})
        finish(c)
        return {'updated':True,'package_id':pid,'new_sale_price':int(new)}
    except Exception:
        rollback(c)
        raise

def nova_price_list_approve(c,p,uid):
    """Optimistic conditional update; entire approval is one transaction."""
    items=p.get('items')
    if not isinstance(items,list) or not items or len(items)>20000:
        raise ValueError('لا توجد أسعار للاعتماد')
    if len({str(x.get('package_id')) for x in items if isinstance(x,dict)})!=len(items):
        raise ValueError('عبوة مكررة في الاعتماد')
    begin(c)
    try:
        updates=[]
        for item in items:
            if not isinstance(item,dict):raise ValueError('صف غير صالح')
            pid=int(item['package_id']);old=int(item['old_sale_price'])
            new=int(item['proposed_sale_price'])
            signature=str(item.get('approval_token',''))
            expected=nova_price_signature(pid,old,new)
            if not _nova_hmac.compare_digest(signature,expected):
                raise ValueError('يجب معاينة الأسعار أولاً قبل اعتمادها')
            if new<=0 or new>1000000000000:raise ValueError('سعر بيع غير صالح')
            changed=c.execute('UPDATE packages SET sale_price=? WHERE id=? AND sale_price=?',
                (new,pid,old)).rowcount
            if changed!=1:raise ValueError('السعر تغير بعد المراجعة؛ أعد المعاينة')
            updates.append({'package_id':pid,'old':old,'new':new})
        audit(c,uid,'bulk_supplier_price_list_approved',{'updates':updates})
        finish(c)
        return {'updated':len(updates),'saved':True}
    except Exception:
        rollback(c)
        raise

'''
s=s.replace(anchor,helpers+anchor)
anchor2="'/api/v1/nova-reprice-unpriced':('prices',lambda:nova_bulk_unpriced(c,data,u['id'])),"
assert s.count(anchor2)==1
s=s.replace(anchor2,"'/api/v1/nova-price-list-parse':('prices',lambda:nova_price_list_file_rows(data)),\n                     '/api/v1/nova-price-list-preview':('prices',lambda:nova_price_list_preview(c,data)),\n                     '/api/v1/nova-price-list-approve':('prices',lambda:nova_price_list_approve(c,data,u['id'])),
                     '/api/v1/nova-manual-sale-price':('prices',lambda:nova_manual_sale_price(c,data,u['id'])),\n                     "+anchor2)
get_anchor="'/api/v1/products':lambda:catalog(c),"
assert s.count(get_anchor)==1
s=s.replace(get_anchor,"'/api/v1/nova-price-list-history':lambda:nova_price_list_history(c),\n                     "+get_anchor)
permission_anchor="'/api/v1/products':'catalog'"
assert s.count(permission_anchor)>=1
s=s.replace(permission_anchor,"'/api/v1/nova-price-list-history':'prices',"+permission_anchor,1)
rollback_anchor="'/api/v1/nova-price-list-approve':('prices',lambda:nova_price_list_approve(c,data,u['id'])),"
assert s.count(rollback_anchor)==1
s=s.replace(rollback_anchor,rollback_anchor+"\n                     '/api/v1/nova-price-list-rollback':('prices',lambda:nova_price_list_rollback(c,data,u['id'])),")
# Ship the price-list screen with the installed offline pharmacy client.
ui=Path(".github/ci/nova_bulk_prices_ui.js").read_text(encoding="utf-8")
Path("pharmacy/static/nova_bulk_prices_ui.js").write_text(ui,encoding="utf-8")
static_anchor="'/static/nova_pharmacy_batch08.js','/static/logo.png'"
assert s.count(static_anchor)==1
s=s.replace(static_anchor,"'/static/nova_pharmacy_batch08.js','/static/nova_bulk_prices_ui.js','/static/logo.png'")
index=Path("pharmacy/static/index.html")
html=index.read_text(encoding="utf-8")
script_anchor='<script src="/static/nova_pharmacy_batch08.js"></script>'
assert html.count(script_anchor)==1
html=html.replace(script_anchor,script_anchor+'<script src="/static/nova_bulk_prices_ui.js"></script>')
index.write_text(html,encoding="utf-8")
p.write_text(s,encoding="utf-8")
print("NOVA_PRICE_LIST_BACKEND_INTEGRATED")
