from pathlib import Path
p=Path('pharmacy/static/app.js')
s=p.read_text(encoding='utf-8')
a=s.index('function sales(){return ')
# The approved POS is immutable during return-status changes.
pos_before=s[s.index('function pos()'):s.index('function sales(){return ')] if 'function pos()' in s else None
b=s.index('\nfunction showReceipt(',a)
replacement="""function novaReturnStatus(s){
 const lines=Array.isArray(s.lines)?s.lines:[];
 const original=lines.reduce((n,l)=>n+Number(l.qty||0),0);
 const returned=lines.reduce((n,l)=>n+Math.min(Number(l.qty||0),Math.max(0,Number(l.returned||0))),0);
 return original>0&&returned>=original?'full':returned>0?'partial':'none';
}
function sales(){return `<div class="panel"><div class="panel-head"><h2>سجل الفواتير والمرتجعات</h2><button class="btn" onclick="nav('pos')">＋ فاتورة جديدة</button></div>${table(['الرقم','التاريخ','العميل/الجهة','القيمة','كاش / تحويل','الحالة','الإجراءات'],state.sales.map(s=>{const status=novaReturnStatus(s);const color=status==='full'?'#b91c1c':status==='partial'?'#b45309':'#15803d';const label=status==='full'?'مرتجع بالكامل':status==='partial'?'مرتجع جزئي':'بيع عادي';return `<tr style="border-inline-start:4px solid ${color}"><td><b>${esc(s.ref)}</b></td><td>${esc(s.created_at)}</td><td>${esc(s.customer||s.authority||'زبون عادي')}</td><td>${fmt(s.total)}</td><td>${fmt(s.cash_paid)} / ${fmt(s.bank_paid)}</td><td><strong style="color:${color}">${label}</strong></td><td><div class="actions"><button class="btn outline small" onclick="showReceipt(${s.id})">فاتورة / طباعة</button>${can('refund')?(status==='full'?'<span style="color:#b91c1c">تم الإرجاع</span>':`<button class="btn danger small" onclick="returnModal(${s.id})">${status==='partial'?'استكمال المرتجع':'مرتجع'}</button>`):''}</div></td></tr>`;}))}</div>`}
"""
s=s[:a]+replacement+s[b:]
old="let lines=s.lines.filter(x=>x.qty>x.returned);modal("
new="let lines=s.lines.filter(x=>x.qty>x.returned);if(!lines.length){toast('هذه الفاتورة مرتجعة بالكامل ولا توجد كمية متاحة للإرجاع',true);return;}modal("
assert s.count(old)==1
s=s.replace(old,new)
if pos_before is not None:
    assert s[s.index('function pos()'):s.index('function novaReturnStatus(')] == pos_before, 'POS changed during returns patch'
p.write_text(s,encoding='utf-8')
print('NOVA16_RETURN_STATUS_UI_APPLIED')
