# -*- coding: utf-8 -*-
"""NOVA Batch05 pricing safety: distinguish explicitly free services from missing prices.
Does not rewrite historical invoices or installed customer data.
"""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def replace(path,a,b):
 p=R/path;s=p.read_text(encoding='utf-8')
 if s.count(a)!=1:raise RuntimeError('NOVA05_FREE_ANCHOR '+path+' '+repr(a[:80])+' count '+str(s.count(a)))
 p.write_text(s.replace(a,b),encoding='utf-8')
def add(path,code):
 p=R/path;s=p.read_text(encoding='utf-8')
 if 'NOVA05_FREE_EXTENSION' in s:raise RuntimeError('already patched')
 p.write_text(s+'\n'+code,encoding='utf-8')
add('hospital/finance.py',"""
# NOVA05_FREE_EXTENSION — explicit zero-price approval only by hospital administrator.
def _free_schema(c):
    c.execute('CREATE TABLE IF NOT EXISTS nova_free_approved (kind TEXT NOT NULL,source_id INTEGER NOT NULL,approved_by INTEGER NOT NULL,approved_at TEXT NOT NULL,PRIMARY KEY(kind,source_id))')
def _free_approved(c,kind,source_id):
    if kind in ('svc','service'):kind='service'
    _free_schema(c)
    return bool(pharmacy.one(c,'SELECT 1 AS approved FROM nova_free_approved WHERE kind=? AND source_id=?',(kind,source_id)))
def free_list(c):
    _free_schema(c)
    return pharmacy.query(c,'SELECT kind,source_id,approved_at FROM nova_free_approved ORDER BY approved_at DESC')
def free_approve(c,actor,data):
    key=str(data.get('service_key','')).strip()
    if key.count(':')!=1:raise ValueError('رمز الخدمة غير صالح')
    prefix,number=key.split(':')
    if prefix not in ('svc','lab') or not number.isdigit():raise ValueError('رمز الخدمة غير صالح')
    sid=int(number)
    if sid<=0:raise ValueError('الخدمة غير صالحة')
    kind='lab' if prefix=='lab' else 'service'
    approved=data.get('approved') is True
    start(c)
    try:
        _free_schema(c)
        table='hospital_lab_tests' if kind=='lab' else 'nova_services'
        row=pharmacy.one(c,'SELECT id,price FROM '+table+' WHERE id=?',(sid,))
        if not row:raise ValueError('الخدمة غير موجودة')
        if approved and row['price']!=0:raise ValueError('الموافقة المجانية فقط للخدمات بسعر صفر')
        if approved:
            c.execute('INSERT INTO nova_free_approved(kind,source_id,approved_by,approved_at) VALUES(?,?,?,?) ON CONFLICT(kind,source_id) DO UPDATE SET approved_by=excluded.approved_by,approved_at=excluded.approved_at',(kind,sid,actor['id'],now()))
        else:c.execute('DELETE FROM nova_free_approved WHERE kind=? AND source_id=?',(kind,sid))
        audit(c,actor,'free_price_approval_changed',sid,{'kind':kind,'approved':approved})
        done(c)
    except Exception:rollback(c);raise
    return {'service_key':key,'approved':approved}
""")
replace('hospital/finance.py',
"def _settle(c,invoice):\n",
"""def _settle(c,invoice):
    # A zero amount can be either a valid free service or an unpriced draft.
    # Do not release clinical orders when administrator did not explicitly approve free.
    for line in pharmacy.query(c,'SELECT source_kind,source_id,name FROM nova_invoice_lines WHERE invoice_id=? AND price=0',(invoice['id'],)):
        if not _free_approved(c,line['source_kind'],line['source_id']):
            raise ValueError('الخدمة بلا سعر معتمد: '+line['name']+' — اطلب تسعيرها أو اعتمادها مجانية')
""")
replace('hospital/gateway.py',
"                    if path=='/api/hospital/cashier-queue':",
"""                    if path=='/api/hospital/nova-free-list':
                        core.require_role(role,'admin')
                        return self.reply(finance.free_list(c))
                    if path=='/api/hospital/cashier-queue':""")
replace('hospital/gateway.py',
"                    if path=='/api/hospital/nova-cashier-quick-invoice':",
"""                    if path=='/api/hospital/nova-free-approval':
                         core.require_role(role,'admin')
                         return self.reply(finance.free_approve(c,user,data))
                    if path=='/api/hospital/nova-cashier-quick-invoice':""")
replace('hospital/static/finance-ui.js',
"function wireFinanceSettings(){",
"function wireFinanceSettings(){novaFreeApprovalPanel();")
add('hospital/static/finance-ui.js',"""
// NOVA05_FREE_EXTENSION — administrative approval, separate from setting price to zero.
async function novaFreeApprovalPanel(){
 const root=$('content');if(!root||state.role!=='admin')return;
 const unpriced=financeState.services.filter(x=>x.price===0&&x.active);
 const options=unpriced.map(x=>'<option value="'+esc(x.key)+'">'+esc(x.name)+' ('+esc(x.category_name||x.category_code)+')</option>').join('');
 root.insertAdjacentHTML('beforeend',panel('الخدمات المجانية المعتمدة',
 '<p class="help">السعر صفر يعني غير مسعّر، ولا يسمح بتنفيذ الخدمة قبل تسعيرها أو موافقة الإدارة أنها مجانية.</p>'+
 '<label>الخدمة بسعر صفر<select id="nova-free-item">'+options+'</select></label>'+
 '<label class="checklabel"><input id="nova-free-check" type="checkbox"> اعتمد هذه الخدمة مجانية</label>'+
 '<div class="actions"><button type="button" class="outline" id="nova-free-save">حفظ قرار الاعتماد / الإلغاء</button></div>'+
 '<div id="nova-free-status"></div>'));
 const approved=await api('nova-free-list');
 const saved=new Set(approved.map(x=>(x.kind==='lab'?'lab:':'svc:')+x.source_id));
 const selected=$('nova-free-item'),checkbox=$('nova-free-check');
 const update=()=>{checkbox.checked=saved.has(selected.value)};
 selected.onchange=update;update();
 $('nova-free-save').onclick=async()=>{
    if(!selected.value)return notice('اختر خدمة',true);
    if(!confirm(checkbox.checked?'اعتماد الخدمة مجانية؟':'إلغاء اعتماد الخدمة مجانية؟'))return;
    try{await api('nova-free-approval',{service_key:selected.value,approved:checkbox.checked});
      notice('تم تسجيل قرار الإدارة');await navigate('services-admin')}
    catch(e){notice(e.message,true)}
 };
}
""")
# Only one open shift per individual cashier; transfers between employees remain auditable.
replace('hospital/finance.py',
"        s=c.execute('INSERT INTO nova_cashier_shifts(cashier_id,opened_at,opening_cash) VALUES(?,?,?)',",
"""        if pharmacy.one(c,'SELECT id FROM nova_cashier_shifts WHERE cashier_id=? AND closed_at IS NULL',(actor['id'],)):
            raise ValueError('لديك وردية مفتوحة بالفعل؛ أقفلها قبل بدء وردية جديدة')
        s=c.execute('INSERT INTO nova_cashier_shifts(cashier_id,opened_at,opening_cash) VALUES(?,?,?)',""")
# Shared print surface already hides app on the printing-lab selector: reuse it for 80mm.
replace('hospital/static/finance-ui.js',
"document.body.classList.add('printing-nova-thermal');",
"document.body.classList.add('printing-nova-thermal','printing-lab');")
replace('hospital/static/finance-ui.js',
"document.body.classList.remove('printing-nova-thermal');area.innerHTML=''",
"document.body.classList.remove('printing-nova-thermal','printing-lab');area.innerHTML=''")

print('NOVA_BATCH05_PRICING_POLICY_READY')
