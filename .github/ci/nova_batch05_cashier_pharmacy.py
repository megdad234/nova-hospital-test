# -*- coding: utf-8 -*-
"""NOVA batch 05 — approved pharmacy and cashier upgrades.
Run after batches 01-04, fail closed on source drift. NO live database access.
"""
from pathlib import Path
import re
R=Path(__file__).resolve().parents[2]
changes=[]
def modify(file, old, new, count=1):
    p=R/file
    s=p.read_text(encoding='utf-8')
    seen=s.count(old)
    if seen!=count: raise RuntimeError('B05_ANCHOR: '+file+' '+repr(old[:110])+' '+str(seen)+'/'+str(count))
    p.write_text(s.replace(old,new),encoding='utf-8');changes.append(file)
def inject(file,anchor,addition):
    modify(file,anchor,addition+anchor)
def append(file,code):
    p=R/file;s=p.read_text(encoding='utf-8')
    if 'NOVA_BATCH05_EXTENSION' in s:raise RuntimeError('batch05 already applied '+file)
    if file=='pharmacy/app.py':
        anchor='class Handler(http.server.BaseHTTPRequestHandler):'
        if s.count(anchor)!=1:raise RuntimeError('Handler anchor missing')
        s=s.replace(anchor,code+'\n'+anchor)
    else:
        s=s+'\n'+code
    p.write_text(s,encoding='utf-8');changes.append(file)

# 1) Pharmacist Hold / Resume lives on central SQLite; drafts never affect sale allocations.
append('pharmacy/app.py', '''
# NOVA_BATCH05_EXTENSION — draft POS carts are NOT sales or stock reservations.
def nova_hold_schema(c):
    c.execute("""CREATE TABLE IF NOT EXISTS nova_pos_held(
       id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES users(id),
       label TEXT NOT NULL, cart_json TEXT NOT NULL, created_at TEXT NOT NULL,
       updated_at TEXT NOT NULL)""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_nova_held_owner ON nova_pos_held(owner_id,updated_at)")

def nova_hold_save(c,p,uid):
    items=p.get('items')
    if not isinstance(items,list) or not 1<=len(items)<=80:
        raise ValueError('اختر أصناف الفاتورة قبل تعليقها')
    checked=[]
    for x in items:
        pk=one(c,"""SELECT pk.id,pr.active FROM packages pk
              JOIN products pr ON pr.id=pk.product_id WHERE pk.id=?""",
              (posint(x.get('package_id'),'العبوة'),))
        if not pk or not pk['active']:raise ValueError('صنف غير متاح')
        checked.append({'package_id':pk['id'],'qty':posint(x.get('qty'),'الكمية')})
    label=textv(p,'label',100) or 'فاتورة معلقة'
    payload={'items':checked,'partner_id':p.get('partner_id') or None,
             'authority_id':p.get('authority_id') or None,
             'coverage':amt(p.get('coverage',0),'التغطية')}
    if payload['coverage']>100:raise ValueError('نسبة التغطية غير صحيحة')
    # Cart prices are deliberately excluded: prices and stock are checked on actual sale.
    begin(c)
    try:
        nova_hold_schema(c)
        hold=p.get('held_id')
        if hold:
            hid=posint(hold,'الفاتورة المعلقة')
            old=one(c,'SELECT id FROM nova_pos_held WHERE id=? AND owner_id=?',(hid,uid))
            if not old:raise ValueError('الفاتورة المعلقة غير موجودة في حسابك')
            c.execute('UPDATE nova_pos_held SET label=?,cart_json=?,updated_at=? WHERE id=?',
                      (label,json.dumps(payload,ensure_ascii=False),now(),hid))
        else:
            hid=c.execute('INSERT INTO nova_pos_held(owner_id,label,cart_json,created_at,updated_at) VALUES(?,?,?,?,?)',
                (uid,label,json.dumps(payload,ensure_ascii=False),now(),now())).lastrowid
        audit(c,uid,'pos_cart_held',{'id':hid,'items':len(checked)})
        finish(c)
    except:rollback(c);raise
    return {'held_id':hid,'stock_changed':False,'sale_created':False}

def nova_held_list(c,uid):
    nova_hold_schema(c)
    rows=query(c,'SELECT id,label,cart_json,updated_at FROM nova_pos_held WHERE owner_id=? ORDER BY updated_at DESC LIMIT 150',(uid,))
    result=[]
    for row in rows:
        data=json.loads(row['cart_json'])
        result.append({'id':row['id'],'label':row['label'],'updated_at':row['updated_at'],
                       'item_count':len(data['items']),'cart':data})
    return result

def nova_hold_delete(c,p,uid):
    hid=posint(p.get('held_id'),'الفاتورة المعلقة')
    begin(c)
    try:
        nova_hold_schema(c)
        if not c.execute('DELETE FROM nova_pos_held WHERE id=? AND owner_id=?',(hid,uid)).rowcount:
            raise ValueError('الفاتورة المعلقة غير موجودة في حسابك')
        audit(c,uid,'pos_cart_deleted',{'id':hid});finish(c)
    except:rollback(c);raise
    return {'deleted':True}

def nova_pharmacy_tasks(c,uid):
    nova_hold_schema(c)
    from datetime import timedelta
    limit_date=(date.today()+timedelta(days=90)).isoformat()
    held=one(c,'SELECT COUNT(*) n FROM nova_pos_held WHERE owner_id=?',(uid,))['n']
    outstanding=one(c,'SELECT COUNT(*) n FROM purchase_lines WHERE qty>received')['n']
    short=one(c,"""SELECT COUNT(*) n FROM products p WHERE p.active=1 AND p.reorder_point>0
          AND COALESCE((SELECT SUM(qty_base) FROM lots l WHERE l.product_id=p.id
                 AND l.status='sellable' AND (l.expiry='' OR l.expiry>=?)),0)<p.reorder_point""",(today(),))['n']
    expiry=one(c,"""SELECT COUNT(*) n FROM lots WHERE status='sellable' AND qty_base>0
          AND expiry!='' AND expiry>=? AND expiry<=?""",(today(),limit_date))['n']
    unpriced=one(c,'SELECT COUNT(*) n FROM packages pk JOIN products p ON p.id=pk.product_id WHERE p.active=1 AND pk.sale_price=0')['n']
    return {'held_carts':held,'receipts_outstanding':outstanding,'reorder_items':short,
            'expiry_90_days':expiry,'unpriced_packages':unpriced,
            'scope':'مؤشرات للعمل؛ ليست حجوزات مخزون ولا مبالغ مالية'}
''')
# APIs: existing sale and report permissions are checked by standard router.
modify('pharmacy/app.py', "'/api/v1/products':'catalog',",
       "'/api/v1/held-sales':'sale','/api/v1/pharmacy-tasks':'reports','/api/v1/products':'catalog',")
modify('pharmacy/app.py', "'/api/v1/products':lambda:catalog(c),",
       "'/api/v1/held-sales':lambda:nova_held_list(c,u['id']),'/api/v1/pharmacy-tasks':lambda:nova_pharmacy_tasks(c,u['id']),\n                     '/api/v1/products':lambda:catalog(c),")
inject('pharmacy/app.py', "                     '/api/v1/sale':('sale',lambda:sell(c,data,u['id'])),",
       """                     '/api/v1/hold-sale':('sale',lambda:nova_hold_save(c,data,u['id'])),
                     '/api/v1/held-sale-delete':('sale',lambda:nova_hold_delete(c,data,u['id'])),
""")

# 2) Fix rounding of repeated partial returns covered by insurance, without changing existing invoices.
modify('pharmacy/app.py',
       "         checked=[];value=0;covered=0;seen_lines=set()",
       """         earlier_return=one(c,'SELECT COALESCE(SUM(amount),0) a,COALESCE(SUM(covered),0) v FROM sale_returns WHERE sale_id=?',(saleid,))
         checked=[];value=0;covered=0;seen_lines=set()""")
modify('pharmacy/app.py',
       "             amount=qty*row['unit_price'];cv=(amount*s['coverage']+50)//100",
       """             amount=qty*row['unit_price']
             cv=min((amount*s['coverage']+50)//100,
                    max(0,s['covered']-earlier_return['v']-covered))""")
modify('pharmacy/app.py',
       "         rid=c.execute('INSERT INTO sale_returns",
       """         if checked and earlier_return['a']+value==s['total']:
             remainder=s['covered']-earlier_return['v']-covered
             if remainder>0:
                 row,qty,amount,cv=checked[-1]
                 if cv+remainder>amount:raise ValueError('توزيع تغطية المرتجع غير صالح')
                 checked[-1]=(row,qty,amount,cv+remainder);covered+=remainder
         rid=c.execute('INSERT INTO sale_returns""")

# 3) Cashier search: unified, paginated, legacy labs selectable but not charged twice.
append('hospital/finance.py', '''
# NOVA_BATCH05_EXTENSION — combined cashier work queue, separate billing sources.
def cashier_queue(c,params):
    page=num(params.get('page',0) or 0,'الصفحة')
    if page>100000:raise ValueError('صفحة غير صحيحة')
    size=40
    term=str(params.get('q','')).strip()[:100]
    status=str(params.get('status','pending')).strip()
    if status not in ('pending','partial','settled','all'):
        raise ValueError('حالة البحث غير صحيحة')
    # One row per financial request. A migrated lab order never appears twice.
    union="""SELECT 'invoice' kind, i.id id, i.invoice_no number,
              p.full_name patient_name,p.patient_no patient_no,
              i.total total,i.patient_due patient_due,
              COALESCE((SELECT SUM(pay.cash_amount+pay.bank_amount)
                 FROM nova_payments pay WHERE pay.invoice_id=i.id),0) paid,
              i.status status,i.created_at created_at
       FROM nova_invoices i JOIN hospital_patients p ON p.id=i.patient_id
       UNION ALL
       SELECT 'legacy_lab' kind,o.id id,o.order_no number,
              p.full_name patient_name,p.patient_no patient_no,
              o.total total,o.total patient_due,0 paid,
              'pending' status,o.created_at created_at
       FROM hospital_orders o JOIN hospital_patients p ON p.id=o.patient_id
       WHERE o.status='pending' AND NOT EXISTS
          (SELECT 1 FROM nova_invoices i WHERE i.lab_order_id=o.id)
         AND NOT EXISTS (SELECT 1 FROM hospital_receipts r WHERE r.order_id=o.id)"""
    where=["status!='void'"]
    args=[]
    if term:
        where.append("(number LIKE ? OR patient_name LIKE ? OR patient_no LIKE ?)")
        args.extend(['%'+term+'%']*3)
    if status=='pending':where.append("status='pending' AND paid=0")
    elif status=='partial':where.append("status='pending' AND paid>0")
    elif status=='settled':where.append("status='settled'")
    sql='FROM ('+union+') WHERE '+' AND '.join(where)
    count=pharmacy.one(c,'SELECT COUNT(*) n '+sql,tuple(args))['n']
    rows=pharmacy.query(c,'SELECT * '+sql+' ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?',
                        tuple(args+[size,page*size]))
    return {'rows':rows,'total':count,'page':page,'page_size':size}

''')
# Add new read-only cashier endpoint next to existing invoices endpoint.
inject('hospital/gateway.py',
       "                    if path=='/api/hospital/invoices':\n                        core.require_role(role,'admin','reception','cashier')",
       """                    if path=='/api/hospital/cashier-queue':
                        core.require_role(role,'admin','cashier','frontdesk')
                        params=parse_qs(urlparse(self.path).query)
                        return self.reply(finance.cashier_queue(c,{k:v[0] for k,v in params.items()}))
""")
# Same exact path also occurs in POST handler, insert once in GET (first occurrence).
# Frontdesk is a combined receptionist/cashier identity, not an administrator.
# Expand existing cashier functions to the explicitly combined frontdesk role.
gate=R/'hospital/gateway.py'
original=gate.read_text(encoding='utf-8')
n=original.count("core.require_role(role,'admin','cashier')")
if not 3<=n<=25:raise RuntimeError('Unexpected cashier authorization count: '+str(n))
gate.write_text(original.replace("core.require_role(role,'admin','cashier')",
                                   "core.require_role(role,'admin','cashier','frontdesk')"),encoding='utf-8')
changes.append('hospital/gateway.py')

print('NOVA_B05_PATCH_APPLIED',len(changes),sorted(set(changes)))
