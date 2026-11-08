"""NOVA guarded partial-refund backend extension. Applied after existing patches."""
from pathlib import Path
p=Path('hospital/finance.py')
s=p.read_text(encoding='utf-8')
anchor='def refund_invoice(c,actor,data):'
assert s.count(anchor)==1
assert 'invoice_id INTEGER NOT NULL UNIQUE REFERENCES nova_invoices(id)' in s
# A separate partial-refund ledger avoids rebuilding or altering the legacy refund table.
# Existing full refunds and original payment records remain untouched.
addon='''
def partial_refund_invoice(c,actor,data):
    """Admin-only partial patient refund; never voids an invoice or cancels clinical work."""
    iid=num(data.get('invoice_id'),'الفاتورة',1)
    key=text(data,'idempotency_key',128,True)
    if len(key)<12:raise ValueError('مفتاح العملية غير صالح')
    cash=num(data.get('cash_amount',0),'النقدي المسترجع')
    bank=num(data.get('bank_amount',0),'البنكي المسترجع')
    bank_id=num(data.get('bank_id',0) or 0,'البنك',0)
    ref=text(data,'bank_reference',120)
    note=text(data,'note',500,True)
    if len(note.strip())<5:raise ValueError('سبب الاسترداد مطلوب')
    if cash+bank<=0:raise ValueError('لا يوجد مبلغ للاسترجاع')
    start(c)
    try:
        c.execute("""CREATE TABLE IF NOT EXISTS nova_partial_refunds(
          id INTEGER PRIMARY KEY, refund_no TEXT NOT NULL UNIQUE,
          invoice_id INTEGER NOT NULL REFERENCES nova_invoices(id),
          idempotency_key TEXT NOT NULL UNIQUE,
          cash_amount INTEGER NOT NULL CHECK(cash_amount>=0),
          bank_amount INTEGER NOT NULL CHECK(bank_amount>=0),
          bank_id INTEGER REFERENCES nova_banks(id),
          bank_name TEXT NOT NULL DEFAULT '',
          bank_reference TEXT NOT NULL DEFAULT '',
          note TEXT NOT NULL,
          created_by INTEGER NOT NULL REFERENCES users(id),
          created_at TEXT NOT NULL,
          CHECK(cash_amount+bank_amount>0),
          CHECK(bank_amount>0 OR bank_id IS NULL))""")
        old=pharmacy.one(c,'SELECT * FROM nova_partial_refunds WHERE idempotency_key=?',(key,))
        if old:
            if (old['invoice_id']!=iid or old['cash_amount']!=cash or old['bank_amount']!=bank or
                (old['bank_id'] or 0)!=bank_id or old['bank_reference']!=ref or old['note']!=note):
                raise ValueError('مفتاح الاسترجاع مستخدم ببيانات مختلفة')
            done(c)
            return {'refund_no':old['refund_no'],'invoice_id':iid,'already_recorded':True,
                    'cash_amount':cash,'bank_amount':bank,'status':'partial'}
        if pharmacy.one(c,'SELECT id FROM nova_refunds WHERE idempotency_key=?',(key,)):
            raise ValueError('مفتاح الاسترجاع مستخدم مسبقاً')
        inv=pharmacy.one(c,'SELECT * FROM nova_invoices WHERE id=?',(iid,))
        if not inv or inv['status'] not in ('pending','settled'):
            raise ValueError('الفاتورة غير متاحة للاسترجاع')
        if pharmacy.one(c,'SELECT id FROM nova_refunds WHERE invoice_id=?',(iid,)):
            raise ValueError('الفاتورة مستردة بالكامل سابقاً')
        paid=pharmacy.one(c,'SELECT COALESCE(SUM(cash_amount+bank_amount),0) amount FROM nova_payments WHERE invoice_id=?',(iid,))['amount']
        partial=pharmacy.one(c,'SELECT COALESCE(SUM(cash_amount+bank_amount),0) amount FROM nova_partial_refunds WHERE invoice_id=?',(iid,))['amount']
        available=paid-partial
        if cash+bank>=available:
            raise ValueError('الاسترداد الجزئي يجب أن يكون أقل من المبلغ المتاح؛ استخدم الاسترداد الكامل للباقي')
        if bank:
            if not bank_id:raise ValueError('اختر بنك إرجاع التحويل')
            b=pharmacy.one(c,'SELECT * FROM nova_banks WHERE id=? AND active=1',(bank_id,))
            if not b:raise ValueError('البنك غير متاح')
            if b['require_reference'] and not ref:raise ValueError('رقم العملية مطلوب لهذا البنك')
            if ref and (pharmacy.one(c,'SELECT id FROM nova_partial_refunds WHERE bank_id=? AND bank_reference=?',(bank_id,ref)) or
                        pharmacy.one(c,'SELECT id FROM nova_refunds WHERE bank_id=? AND bank_reference=?',(bank_id,ref))):
                raise ValueError('مرجع الاسترداد البنكي مستخدم مسبقاً')
        else:
            if bank_id or ref:raise ValueError('بيانات البنك لا تستخدم مع الاسترجاع النقدي')
            b=None
        refund_no='PRF-'+uid()
        c.execute("""INSERT INTO nova_partial_refunds(refund_no,invoice_id,idempotency_key,cash_amount,bank_amount,
          bank_id,bank_name,bank_reference,note,created_by,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
          (refund_no,iid,key,cash,bank,bank_id or None,b['name'] if b else '',ref,note,actor['id'],now()))
        audit(c,actor,'invoice_partial_refund',iid,{'refund_no':refund_no,'cash':cash,'bank':bank,'note':note})
        done(c)
    except Exception:rollback(c);raise
    return {'refund_no':refund_no,'invoice_id':iid,'already_recorded':False,
            'cash_amount':cash,'bank_amount':bank,'status':'partial'}

'''
if 'def partial_refund_invoice(' not in s:
 s=s.replace(anchor,addon+anchor,1)
p.write_text(s,encoding='utf-8')
print('NOVA_PARTIAL_REFUND_BACKEND_ADDED')
