# -*- coding: utf-8 -*-
"""NOVA Batch08 — preserve pharmacy purchase UI; atomic pricing, drafts, reports.

This patch runs AFTER the existing reviewed NOVA patches. It never edits a
real DB, does not alter prior invoices, and fails closed on unexpected anchors.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def replace_one(text,old,new,label):
    count=text.count(old)
    if count!=1:
        raise RuntimeError('NOVA08_ANCHOR '+label+' '+str(count))
    return text.replace(old,new,1)

app_path=ROOT/'pharmacy/app.py'
s=app_path.read_text(encoding='utf-8')

# Prices are submitted by the existing purchase form with an explicit preview,
# and committed in the SAME transaction as the original purchase/stock entries.
anchor="    total=sum(x[-1] for x in checked);paid=amt(p.get('paid',0),'المدفوع');method=textv(p,'payment_method',24) or 'credit'"
validation="""    # Backwards compatible: old clients without nova_sale_prices retain old behavior.
    price_data=p.get('nova_sale_prices')
    price_updates={}
    if price_data is not None:
        if not isinstance(price_data,list):raise ValueError('بيانات أسعار البيع غير صحيحة')
        purchased_ids={int(row[0]['id']) for row in checked}
        for price_row in price_data:
            if not isinstance(price_row,dict):raise ValueError('سطر التسعير غير صحيح')
            pack_id=posint(price_row.get('package_id'),'عبوة التسعير')
            sale_price=posint(price_row.get('price'),'سعر البيع')
            if sale_price>1_000_000_000_000:raise ValueError('سعر البيع غير منطقي')
            if pack_id not in purchased_ids:
                raise ValueError('أسعار البيع يجب أن تطابق عبوات فاتورة الشراء')
            price_updates[pack_id]=sale_price
        if set(price_updates)!=purchased_ids:
            raise ValueError('حدد سعر بيع موجب لكل عبوة مشتراة قبل الحفظ')
"""
s=replace_one(s,anchor,validation+anchor,'purchase pricing validate')
anchor="        audit(c,uid,'purchase',{'id':new,'supplier':supplier,'invoice':ref,'total':total})"
update="""        # No partial invoices or stock writes survive a pricing failure.
        for pack_id,price in price_updates.items():
            main_pack=one(c,'SELECT product_id,factor,sale_price FROM packages WHERE id=?',(pack_id,))
            old_price=main_pack['sale_price']
            if old_price!=price:
                c.execute('UPDATE packages SET sale_price=? WHERE id=?',(price,pack_id))
                audit(c,uid,'purchase_sale_price',{'purchase_id':new,'package_id':pack_id,
                                                  'old_price':old_price,'new_price':price})
            # Enable sale by existing strip/piece packs too, but preserve all manual nonzero prices.
            for other in query(c,'SELECT id,factor,sale_price FROM packages WHERE product_id=? AND id<>?',
                               (main_pack['product_id'],pack_id)):
                if other['sale_price']>0 or other['id'] in price_updates:continue
                derived=max(1,(price*other['factor']+main_pack['factor']-1)//main_pack['factor'])
                c.execute('UPDATE packages SET sale_price=? WHERE id=?',(derived,other['id']))
                audit(c,uid,'purchase_auto_price_unit',{'purchase_id':new,'package_id':other['id'],
                                                        'old_price':0,'new_price':derived})
"""
s=replace_one(s,anchor,update+anchor,'purchase pricing transaction')
helpers=String='''
def nova_purchase_draft_schema(c):
    c.execute("""CREATE TABLE IF NOT EXISTS nova_purchase_drafts(
       id INTEGER PRIMARY KEY,owner_id INTEGER NOT NULL REFERENCES users(id),
       label TEXT NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_nova_purchase_draft_owner ON nova_purchase_drafts(owner_id,updated_at)")

def nova_purchase_draft_save(c,p,uid):
    label=textv(p,'label',100) or 'فاتورة مشتريات معلقة'
    data=p.get('draft')
    if not isinstance(data,dict) or not isinstance(data.get('items'),list):
        raise ValueError('بيانات مسودة المشتريات غير صحيحة')
    if len(data['items'])>500:raise ValueError('المسودة كبيرة جداً')
    for item in data['items']:
        if not isinstance(item,dict):raise ValueError('صنف غير صحيح في المسودة')
        pid=posint(item.get('package_id'),'العبوة')
        if not one(c,'SELECT id FROM packages WHERE id=?',(pid,)):
            raise ValueError('عبوة غير موجودة في المسودة')
        posint(item.get('qty'),'كمية المسودة')
    body=json.dumps(data,ensure_ascii=False,separators=(',',':'))
    if len(body)>500_000:raise ValueError('حجم المسودة كبير جداً')
    begin(c)
    try:
        nova_purchase_draft_schema(c)
        owner_count=one(c,'SELECT COUNT(*) n FROM nova_purchase_drafts WHERE owner_id=?',(uid,))['n']
        if owner_count>=80:raise ValueError('لديك عدد كبير من المسودات؛ احذف غير الضروري أولاً')
        draft_id=c.execute('INSERT INTO nova_purchase_drafts(owner_id,label,body,created_at,updated_at) VALUES(?,?,?,?,?)',
                           (uid,label,body,now(),now())).lastrowid
        audit(c,uid,'purchase_draft_saved',{'draft_id':draft_id,'items':len(data['items'])})
        finish(c)
    except Exception:rollback(c);raise
    return {'draft_id':draft_id,'stock_changed':False,'invoice_created':False}

def nova_purchase_draft_list(c,uid):
    nova_purchase_draft_schema(c)
    records=query(c,'SELECT id,label,body,updated_at FROM nova_purchase_drafts WHERE owner_id=? ORDER BY updated_at DESC',(uid,))
    return [{'id':r['id'],'label':r['label'],'draft':json.loads(r['body']),'updated_at':r['updated_at']} for r in records]

def nova_purchase_draft_delete(c,p,uid):
    draft_id=posint(p.get('draft_id'),'مسودة المشتريات')
    begin(c)
    try:
        nova_purchase_draft_schema(c)
        row=c.execute('DELETE FROM nova_purchase_drafts WHERE id=? AND owner_id=?',(draft_id,uid))
        if row.rowcount!=1:raise ValueError('المسودة غير موجودة أو لا تخص المستخدم')
        audit(c,uid,'purchase_draft_deleted',{'draft_id':draft_id})
        finish(c)
    except Exception:rollback(c);raise
    return {'deleted':True,'stock_changed':False}

def nova_bulk_unpriced(c,p,uid):
    """Preview or approve prices ONLY for stocked, previously unpriced pharmacy packages."""
    try:
        pct=Decimal(str(p.get('markup_percent',0)))
    except (InvalidOperation,ValueError,TypeError):
        raise ValueError('نسبة زيادة البيع غير صحيحة')
    if not pct.is_finite() or pct<0 or pct>1000:raise ValueError('النسبة من 0 إلى 1000 فقط')
    preview=p.get('preview',True) is not False
    candidates=query(c,"""SELECT pk.id,pk.product_id,pk.factor,pr.name
        FROM packages pk JOIN products pr ON pr.id=pk.product_id
        WHERE pk.sale_price=0 AND pr.active=1 AND EXISTS(
          SELECT 1 FROM lots l WHERE l.product_id=pr.id AND l.status='sellable'
          AND l.qty_base>0 AND (l.expiry='' OR l.expiry>=date('now')))
        ORDER BY pr.name,pk.id""")
    changes=[]
    for pk in candidates:
        last=one(c,"""SELECT pl.amount,pl.qty,pl.bonus,src.factor FROM purchase_lines pl
              JOIN packages src ON src.id=pl.package_id
              WHERE src.product_id=? AND (pl.received+pl.bonus)>0
              ORDER BY pl.id DESC LIMIT 1""",(pk['product_id'],))
        if not last:continue
        denom=Decimal(last['qty']+last['bonus'])
        if not denom:continue
        unit=Decimal(last['amount'])/denom
        proposed=int((max(Decimal(0),unit)*Decimal(pk['factor'])/
                      Decimal(last['factor'])*(Decimal(1)+pct/Decimal(100))+
                      Decimal('0.5')).to_integral_value(rounding='ROUND_DOWN'))
        if proposed<1 or proposed>1_000_000_000_000:continue
        changes.append({'package_id':pk['id'],'name':pk['name'],'price':proposed})
    if preview:
        return {'count':len(changes),'sample':changes[:20],'markup_percent':str(pct),
                'saved':False}
    begin(c)
    try:
        updated=0
        for rec in changes:
            res=c.execute('UPDATE packages SET sale_price=? WHERE id=? AND sale_price=0',
                          (rec['price'],rec['package_id']))
            if res.rowcount:
                updated+=1
                audit(c,uid,'legacy_purchase_price_approved',
                      {'package_id':rec['package_id'],'new_price':rec['price'],'markup_percent':str(pct)})
        finish(c)
    except Exception:rollback(c);raise
    return {'updated':updated,'saved':True,'markup_percent':str(pct)}

def nova_pharmacy_business_report(c,day_from,day_to):
    """Accounting: revenue minus sold-stock COGS; purchases remain inventory, not expenses.
    Operational reporting, not an independently audited financial statement.
    """
    try:
        a=date.fromisoformat(day_from);b=date.fromisoformat(day_to)
        if a.isoformat()!=day_from or b.isoformat()!=day_to or a>b:
            raise ValueError('نطاق التاريخ غير صحيح')
    except (ValueError,TypeError):
        raise ValueError('التاريخ يجب أن يكون صحيحاً ومن تاريخ إلى تاريخ')
    def amount(sql,params=( )):
        return int(c.execute(sql,params).fetchone()[0] or 0)
    period=(day_from,day_to)
    purchase_gross=amount('SELECT SUM(total) FROM purchases WHERE invoice_date BETWEEN ? AND ?',period)
    purchase_returns=amount("""SELECT SUM(pr.amount) FROM purchase_returns pr
        JOIN purchase_lines pl ON pl.id=pr.purchase_line_id
        JOIN purchases pu ON pu.id=pl.purchase_id
        WHERE substr(pr.created_at,1,10) BETWEEN ? AND ?""",period)
    sales_gross=amount("SELECT SUM(total) FROM sales WHERE substr(created_at,1,10) BETWEEN ? AND ?",period)
    sales_returns=amount("SELECT SUM(amount) FROM sale_returns WHERE substr(created_at,1,10) BETWEEN ? AND ?",period)
    sold_cost=amount("""SELECT SUM(sl.cost) FROM sale_lines sl
        JOIN sales s ON s.id=sl.sale_id WHERE substr(s.created_at,1,10) BETWEEN ? AND ?""",period)
    returned_cost=amount("""SELECT SUM(ra.cost) FROM return_allocations ra
        JOIN sale_returns sr ON sr.id=ra.return_id
        WHERE substr(sr.created_at,1,10) BETWEEN ? AND ?""",period)
    operating_expenses=amount("SELECT SUM(amount) FROM expenses WHERE substr(created_at,1,10) BETWEEN ? AND ?",period)
    purchase_paid=amount("""SELECT SUM(pm.amount) FROM payments pm WHERE pm.party_kind='supplier'
        AND substr(pm.created_at,1,10) BETWEEN ? AND ?""",period)
    patient_cash=amount("""SELECT SUM(amount) FROM payments WHERE party_kind='customer'
        AND method='cash' AND substr(created_at,1,10) BETWEEN ? AND ?""",period)
    patient_bank=amount("""SELECT SUM(amount) FROM payments WHERE party_kind='customer'
        AND method='bank' AND substr(created_at,1,10) BETWEEN ? AND ?""",period)
    refund_cash=amount("""SELECT SUM(amount-covered) FROM sale_returns
        WHERE refund_method='cash' AND substr(created_at,1,10) BETWEEN ? AND ?""",period)
    refund_bank=amount("""SELECT SUM(amount-covered) FROM sale_returns
        WHERE refund_method='bank' AND substr(created_at,1,10) BETWEEN ? AND ?""",period)
    sales_net=sales_gross-sales_returns
    net_cogs=sold_cost-returned_cost
    gross_profit=sales_net-net_cogs
    expenses=query(c,"""SELECT category,COUNT(*) count,SUM(amount) amount
        FROM expenses WHERE substr(created_at,1,10) BETWEEN ? AND ?
        GROUP BY category ORDER BY amount DESC""",period)
    # Snapshot is current inventory valuation, NOT historical closing stock.
    inventory_sellable=amount("""SELECT SUM(qty_base*unit_cost_milli/1000) FROM lots
        WHERE status='sellable' AND (expiry='' OR expiry>=date('now'))""")
    inventory_expired=amount("""SELECT SUM(qty_base*unit_cost_milli/1000) FROM lots
        WHERE status='sellable' AND expiry<>'' AND expiry<date('now')""")
    return {
      'from':day_from,'to':day_to,
      'purchases_gross':purchase_gross,'purchase_returns':purchase_returns,
      'purchases_net':purchase_gross-purchase_returns,'supplier_payments':purchase_paid,
      'sales_gross':sales_gross,'sales_returns':sales_returns,'sales_net':sales_net,
      'sold_cost':sold_cost,'returned_cost':returned_cost,'net_cogs':net_cogs,
      'gross_profit':gross_profit,'expenses':operating_expenses,
      'operating_result':gross_profit-operating_expenses,
      'gross_margin_pct':round(100*gross_profit/sales_net,2) if sales_net else None,
      'net_margin_pct':round(100*(gross_profit-operating_expenses)/sales_net,2) if sales_net else None,
      'patient_cash_collected':patient_cash,'patient_bank_collected':patient_bank,
      'cash_refunds':refund_cash,'bank_refunds':refund_bank,
      'patient_cash_net':patient_cash-refund_cash,'patient_bank_net':patient_bank-refund_bank,
      'expenses_by_category':expenses,
      'stock_current_sellable_value':inventory_sellable,
      'stock_current_expired_value':inventory_expired,
      'notes':['مشتريات الفترة منفصلة عن تكلفة الأصناف المباعة، ولا تُخصم كاملة من الربح.',
               'صافي الربح التشغيلي يعكس المصروفات المسجلة فقط؛ لا يشمل المصروفات غير المدخلة أو الاستحقاقات غير المقيدة.',
               'قيمة المخزون المعروضة حالية وليست رصيد نهاية الفترة التاريخي.',
               'حركة التحصيلات هنا لمبيعات الصيدلية؛ لا تمثل رصيد بنكك الحقيقي ولا تشمل تحصيلات المستشفى الأخرى.']
    }

'''
s=replace_one(s,'def report(c):\n',helpers+'def report(c):\n','helpers before reports')
s=replace_one(s,"'/api/v1/held-sales':'sale','/api/v1/pharmacy-tasks':'reports',",
    "'/api/v1/nova-purchase-drafts':'purchase','/api/v1/nova-pharmacy-finance':'reports','/api/v1/held-sales':'sale','/api/v1/pharmacy-tasks':'reports',",
    'GET permissions')
s=replace_one(s,"'/api/v1/held-sales':lambda:nova_held_list(c,u['id']),",
    "'/api/v1/nova-purchase-drafts':lambda:nova_purchase_draft_list(c,u['id']),\n                     '/api/v1/nova-pharmacy-finance':lambda:nova_pharmacy_business_report(c,(parse_qs(urlparse(self.path).query).get('from') or [today()[:7]+'-01'])[0],(parse_qs(urlparse(self.path).query).get('to') or [today()])[0]),\n                     '/api/v1/held-sales':lambda:nova_held_list(c,u['id']),",
    'GET result routes')
s=replace_one(s,"'/api/v1/hold-sale':('sale',lambda:nova_hold_save(c,data,u['id'])),",
    "'/api/v1/nova-reprice-unpriced':('prices',lambda:nova_bulk_unpriced(c,data,u['id'])),\n                     '/api/v1/nova-purchase-draft-save':('purchase',lambda:nova_purchase_draft_save(c,data,u['id'])),\n                     '/api/v1/nova-purchase-draft-delete':('purchase',lambda:nova_purchase_draft_delete(c,data,u['id'])),\n                     '/api/v1/hold-sale':('sale',lambda:nova_hold_save(c,data,u['id'])),",
    'POST purchase draft routes')
# Existing static whitelist is explicit: keep installed script served locally over LAN.
s=replace_one(s,"'/static/ux_v14.js','/static/logo.png'",
    "'/static/ux_v14.js','/static/nova_pharmacy_batch08.js','/static/logo.png'",
    'serve new UI module')
app_path.write_text(s,encoding='utf-8')

index=ROOT/'pharmacy/static/index.html'
s=index.read_text(encoding='utf-8')
s=replace_one(s,'<script src="/static/ux_v14.js"></script>',
              '<script src="/static/ux_v14.js"></script><script src="/static/nova_pharmacy_batch08.js"></script>',
              'load UI after existing scripts')
index.write_text(s,encoding='utf-8')

ux=ROOT/'pharmacy/static/ux_v14.js'
s=ux.read_text(encoding='utf-8')
s=replace_one(s,"items:rows,payment_method:method,paid,bank_ref:v('buy-bankref')||state.purchaseBankRef};",
    "items:rows,nova_sale_prices:novaPurchasePricePayload(rows),payment_method:method,paid,bank_ref:v('buy-bankref')||state.purchaseBankRef};",
    'send prices atomically on purchase')
ux.write_text(s,encoding='utf-8')
style=ROOT/'pharmacy/static/style.css'
extra=ROOT/'pharmacy/static/nova_pharmacy_batch08.css'
style.write_text(style.read_text(encoding='utf-8')+'\n'+extra.read_text(encoding='utf-8'),encoding='utf-8')
print('NOVA08_BACKEND_APPLIED: atomic invoice prices, persistent drafts, period financial report, original UI preserved')
