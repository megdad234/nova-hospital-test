"""NOVA safe repeated patient refunds, applied after earlier patches, never touches pharmacy."""
from pathlib import Path
p=Path('hospital/finance.py')
s=p.read_text(encoding='utf-8')
assert 'invoice_id INTEGER NOT NULL UNIQUE REFERENCES nova_invoices(id)' in s
assert 'def init(c):\n    c.executescript(SCHEMA)' in s
assert 'def refund_invoice(c,actor,data):' in s
s=s.replace('invoice_id INTEGER NOT NULL UNIQUE REFERENCES nova_invoices(id),','invoice_id INTEGER NOT NULL REFERENCES nova_invoices(id),',1)
anchor='def init(c):\n    c.executescript(SCHEMA)'
migration='''def _nova_migrate_refund_ledger(c):
    """Preserve old refunds, constraints and IDs; rebuild only on legacy UNIQUE(invoice_id)."""
    indexes=c.execute("PRAGMA index_list(nova_refunds)").fetchall()
    legacy=False
    for index in indexes:
        if not index[2]:continue
        cols=[r[2] for r in c.execute('PRAGMA index_info("'+index[1]+'")')]
        if cols==['invoice_id']:legacy=True
    if not legacy:return
    required={'id','refund_no','invoice_id','idempotency_key','cash_amount','bank_amount',
              'bank_id','bank_name','bank_reference','note','created_by','created_at','shift_id'}
    existing={r[1] for r in c.execute('PRAGMA table_info(nova_refunds)')}
    if existing!=required:raise RuntimeError('Refund schema mismatch; migration stopped')
    if c.execute('PRAGMA foreign_key_check').fetchall():
        raise RuntimeError('Database foreign key errors; migration stopped')
    # Stop rather than modifying a table referenced by another table.
    for (name,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        if name=='nova_refunds':continue
        if any(row[2]=='nova_refunds' for row in c.execute('PRAGMA foreign_key_list("'+name+'")')):
            raise RuntimeError('Unexpected refund dependencies; migration stopped')
    c.execute('SAVEPOINT nova_refund_schema_upgrade')
    try:
        before=c.execute('SELECT COUNT(*),COALESCE(SUM(cash_amount+bank_amount),0) FROM nova_refunds').fetchone()
        c.execute("""CREATE TABLE nova_refunds_new(
          id INTEGER PRIMARY KEY,refund_no TEXT NOT NULL UNIQUE,
          invoice_id INTEGER NOT NULL REFERENCES nova_invoices(id),
          idempotency_key TEXT NOT NULL UNIQUE,
          cash_amount INTEGER NOT NULL DEFAULT 0 CHECK(cash_amount>=0),
          bank_amount INTEGER NOT NULL DEFAULT 0 CHECK(bank_amount>=0),
          bank_id INTEGER REFERENCES nova_banks(id),bank_name TEXT NOT NULL DEFAULT '',
          bank_reference TEXT NOT NULL DEFAULT '',note TEXT NOT NULL DEFAULT '',
          created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,
          shift_id INTEGER REFERENCES nova_cashier_shifts(id),
          CHECK(cash_amount+bank_amount>0),CHECK(bank_amount>0 OR bank_id IS NULL))""")
        cols=','.join(sorted(required))
        c.execute('INSERT INTO nova_refunds_new('+cols+') SELECT '+cols+' FROM nova_refunds')
        after=c.execute('SELECT COUNT(*),COALESCE(SUM(cash_amount+bank_amount),0) FROM nova_refunds_new').fetchone()
        if tuple(before)!=tuple(after):raise RuntimeError('Refund ledger verification failed')
        c.execute('DROP TABLE nova_refunds')
        c.execute('ALTER TABLE nova_refunds_new RENAME TO nova_refunds')
        c.execute("""CREATE UNIQUE INDEX nova_unique_refund_bank_ref
          ON nova_refunds(bank_id,bank_reference)
          WHERE bank_id IS NOT NULL AND bank_reference!=''""")
        c.execute('CREATE INDEX nova_refunds_invoice_lookup ON nova_refunds(invoice_id,id)')
        if c.execute('PRAGMA foreign_key_check').fetchall():
            raise RuntimeError('Refund ledger migration violates foreign keys')
        c.execute('RELEASE SAVEPOINT nova_refund_schema_upgrade')
    except:
        c.execute('ROLLBACK TO SAVEPOINT nova_refund_schema_upgrade')
        c.execute('RELEASE SAVEPOINT nova_refund_schema_upgrade')
        raise

'''
s=s.replace(anchor,migration+anchor+'\n    _nova_migrate_refund_ledger(c)',1)
start=s.index('def refund_invoice(c,actor,data):')
end=s.index('\ndef void_invoice(',start)
new="""def refund_invoice(c,actor,data):
    # Admin-only ledger refund: partial preserves service; full cancels unstarted service.
    iid=num(data.get('invoice_id'),'الفاتورة',1)
    key=text(data,'idempotency_key',128,True)
    if len(key)<12:raise ValueError('مفتاح العملية غير صالح')
    cash=num(data.get('cash_amount',0),'النقدي المسترجع')
    bank=num(data.get('bank_amount',0),'البنكي المسترجع')
    bank_id=num(data.get('bank_id',0) or 0,'البنك',0)
    ref=text(data,'bank_reference',120)
    note=text(data,'note',500,True)
    if len(note)<5:raise ValueError('سبب الاسترداد مطلوب')
    if cash+bank<=0:raise ValueError('لا يوجد مبلغ للاسترجاع')
    start(c)
    try:
        old=pharmacy.one(c,'SELECT * FROM nova_refunds WHERE idempotency_key=?',(key,))
        if old:
            if (old['invoice_id']!=iid or old['cash_amount']!=cash or old['bank_amount']!=bank
                or (old['bank_id'] or 0)!=bank_id or old['bank_reference']!=ref or old['note']!=note):
                raise ValueError('مفتاح الاسترجاع مستخدم ببيانات مختلفة')
            inv=pharmacy.one(c,'SELECT status FROM nova_invoices WHERE id=?',(iid,))
            done(c)
            return {'refund_no':old['refund_no'],'invoice_id':iid,'already_recorded':True,
                    'cash_amount':cash,'bank_amount':bank,'status':inv['status']}
        inv=pharmacy.one(c,'SELECT * FROM nova_invoices WHERE id=?',(iid,))
        if not inv or inv['status'] not in ('pending','settled'):
            raise ValueError('الفاتورة غير متاحة للاسترجاع')
        paid=pharmacy.one(c,'''SELECT COALESCE(SUM(cash_amount+bank_amount),0) AS amount
                       FROM nova_payments WHERE invoice_id=?''',(iid,))['amount']
        refunded=pharmacy.one(c,'''SELECT COALESCE(SUM(cash_amount+bank_amount),0) AS amount
                       FROM nova_refunds WHERE invoice_id=?''',(iid,))['amount']
        available=paid-refunded
        if available<=0 or cash+bank>available:
            raise ValueError('المبلغ المسترجع أكبر من الرصيد المتاح')
        full=(cash+bank==available)
        if bank:
            if not bank_id:raise ValueError('اختر بنك إرجاع التحويل')
            b=pharmacy.one(c,'SELECT * FROM nova_banks WHERE id=? AND active=1',(bank_id,))
            if not b:raise ValueError('البنك غير متاح')
            if b['require_reference'] and not ref:raise ValueError('رقم العملية مطلوب لهذا البنك')
        else:
            if bank_id or ref:raise ValueError('بيانات البنك لا تستخدم مع الاسترجاع النقدي')
            b=None
        claim=pharmacy.one(c,'SELECT * FROM nova_claims WHERE invoice_id=?',(iid,))
        if claim and (claim['received']>0 or claim['status']!='unverified'):
            raise ValueError('مطالبة التأمين بدأت إجراءاتها؛ راجع الإدارة المالية أولاً')
        if full:_assert_lab_not_started(c,inv['lab_order_id'])
        refund_no='RF-'+uid()
        shift=pharmacy.one(c,'SELECT id FROM nova_cashier_shifts WHERE cashier_id=? AND closed_at IS NULL',(actor['id'],))
        c.execute('''INSERT INTO nova_refunds(refund_no,invoice_id,idempotency_key,cash_amount,bank_amount,
           bank_id,bank_name,bank_reference,note,created_by,created_at,shift_id)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
           (refund_no,iid,key,cash,bank,bank_id or None,b['name'] if b else '',ref,note,
            actor['id'],now(),shift['id'] if shift else None))
        if full:
            c.execute("UPDATE nova_invoices SET status='void' WHERE id=?",(iid,))
            if inv['lab_order_id']:
                c.execute("UPDATE hospital_orders SET status='cancelled' WHERE id=? AND status IN ('pending','paid')",(inv['lab_order_id'],))
            if claim:c.execute('DELETE FROM nova_claims WHERE invoice_id=?',(iid,))
        audit(c,actor,'invoice_refund' if full else 'invoice_partial_refund',iid,
              {'refund_no':refund_no,'cash':cash,'bank':bank,'bank_id':bank_id,
               'reference':ref,'note':note,'original_paid':paid,'previous_refunds':refunded,
               'full':full})
        done(c)
    except Exception:rollback(c);raise
    return {'refund_no':refund_no,'invoice_id':iid,'already_recorded':False,
            'cash_amount':cash,'bank_amount':bank,'status':'void' if full else inv['status'],
            'remaining_refundable':available-cash-bank}

"""
s=s[:start]+new+s[end:]
p.write_text(s,encoding='utf-8')
print('NOVA_REPEATED_REFUNDS_BACKEND_APPLIED')
