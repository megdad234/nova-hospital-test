# -*- coding: utf-8 -*-
"""NOVA14: atomic invoice discount; net line revenue, refunds and ledger remain aligned."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
def edit(path,fn):
 p=root/path;s=p.read_text(encoding='utf-8');n=fn(s)
 if s==n:raise RuntimeError('NOVA14_NO_CHANGE '+path)
 p.write_text(n,encoding='utf-8')
def replace(s,a,b,tag):
 if s.count(a)!=1:raise RuntimeError('NOVA14_ANCHOR '+tag+' '+str(s.count(a)))
 return s.replace(a,b,1)
def backend(s):
 s=replace(s,"    total=sum(x[2] for x in checked)\n    covered=(total*coverage+50)//100",
 """    gross=sum(x[2] for x in checked)
    discount=amt(p.get('discount',0),'خصم فاتورة البيع')
    if discount>gross:raise ValueError('الخصم يتجاوز قيمة الفاتورة')
    total=gross-discount
    # Allocate discount by original line value, last line absorbs rounding.
    net_lines=[];allocated=0
    for idx,(_,_,line_amount) in enumerate(checked):
        net=(line_amount*total)//gross if gross and idx<len(checked)-1 else total-allocated
        net_lines.append(net);allocated+=net
    covered=(total*coverage+50)//100""",'discount')
 s=replace(s,"        for pkg,qty,line_amount in checked:\n            sl=c.execute('INSERT INTO sale_lines", "        for (pkg,qty,line_amount),net_line in zip(checked,net_lines):\n            sl=c.execute('INSERT INTO sale_lines",'line loop')
 s=replace(s,"(saleid,pkg['id'],qty,pkg['sale_price'],line_amount,0)","(saleid,pkg['id'],qty,pkg['sale_price'],net_line,0)",'net line')
 s=replace(s,"        audit(c,uid,'sale',{'ref':ref,'total':total,'covered':covered,'cost':cost_total})",
 """        audit(c,uid,'sale',{'ref':ref,'gross':gross,'discount':discount,'total':total,'covered':covered,'cost':cost_total})""",'audit')
 s=replace(s,"    return {'id':saleid,'ref':ref,'total':total,'covered':covered,", "    return {'id':saleid,'ref':ref,'total':total,'discount':discount,'covered':covered,",'response')
 # The preceding insurance patches may alter the return expression.
 # Anchor on the return block rather than the exact original expression.
 start=s.index('def sale_return(c,p,uid):')
 end=s.find('\\ndef ',start+1)
 if end<0:end=len(s)
 block=s[start:end]
 candidates=[line for line in block.splitlines() if "amount=qty*row['unit_price']" in line]
 if len(candidates)!=1:
     print('NOVA14_REFUND_CONTEXT',[(i+1,line[:500]) for i,line in enumerate(block.splitlines()) if 'amount=' in line or 'coverage' in line])
     raise RuntimeError('NOVA14_REFUND_CANDIDATES '+str(len(candidates)))
 original=candidates[0]
 indentation=original[:len(original)-len(original.lstrip())]
 replacement=indentation+"before=(row['total']*earlier)//row['qty']\n"+indentation+"after=(row['total']*(earlier+qty))//row['qty']\n"+indentation+"amount=after-before;cv=(amount*s['coverage']+50)//100"
 s=s[:start]+block.replace(original,replacement,1)+s[end:]
 s=replace(s,"    return {'id':saleid,'ref':ref,'total':total,'discount':discount,'covered':covered,",
 """    actor=one(c,'SELECT permissions FROM users WHERE id=? AND active=1',(uid,))
    permissions=set(json.loads(actor['permissions'])) if actor else set()
    can_profit=bool(permissions.intersection({'reports','reports_view','view_reports','admin','manage_users','profit_view'}))
    return {'net_profit':total-cost_total if can_profit else None,'id':saleid,'ref':ref,'total':total,'discount':discount,'covered':covered,""",'profit access')
 return s
edit('pharmacy/app.py',backend)
def ui(s):
 s=replace(s,"function saleTotal(){return state.saleRows.reduce((sum,r)=>sum+(skuPack(r.package_id)?.sale_price||0)*r.qty,0)}",
 """function saleGross(){return state.saleRows.reduce((sum,r)=>sum+(skuPack(r.package_id)?.sale_price||0)*r.qty,0)}
function saleDiscount(){return Math.max(0,Number(state.novaSaleDiscount||0))}
function saleTotal(){return Math.max(0,saleGross()-saleDiscount())}
function novaSetSaleDiscount(value){state.novaSaleDiscount=value;redraw()}""",'total')
 s=replace(s,"function payFields(due){switch(state.payMode){case'cash':return", "function payFields(due){switch(state.payMode){case'cash':return",'pay guard') if False else s
 s=replace(s,"if(state.payMode==='cash'&&v('cash-tender')!==''&&Number(v('cash-tender'))<due)throw Error('المبلغ المستلم أقل من قيمة الفاتورة');",
 """if(!Number.isSafeInteger(Number(state.novaSaleDiscount||0))||saleDiscount()>saleGross())throw Error('الخصم غير صحيح أو أكبر من الفاتورة');""",'tender validation')
 s=replace(s,"prescription,items:state.saleRows,partner_id:", "prescription,items:state.saleRows,discount:saleDiscount(),partner_id:",'request')
 s=replace(s,"state.saleRows=[];state.idempotency=token();await refresh();", "state.saleRows=[];state.novaSaleDiscount=0;state.idempotency=token();await refresh();",'reset')
 s=replace(s,'</div><div class="sale-cart-list" aria-label="أصناف الفاتورة">',"""</div><div class="field"><label for="nova-sale-discount">خصم الفاتورة (جنيه سوداني)</label><input id="nova-sale-discount" type="number" min="0" step="1" value="${saleDiscount()}" onchange="novaSetSaleDiscount(this.value)"><small>الإجمالي بعد الخصم: ${fmt(saleTotal())} ج.س</small></div><div class="sale-cart-list" aria-label="أصناف الفاتورة">""",'discount input')
 # Cash sale is settled automatically; keep tender field out of the daily workflow.
 s=replace(s,"function payFields(due){switch(state.payMode){case'cash':return", "function payFields(due){switch(state.payMode){case'cash':return",'noop') if False else s
 s=replace(s,"function payFields(due){switch(state.payMode){case'cash':return", "function payFields(due){switch(state.payMode){case'cash':return",'noop') if False else s
 # Remove optional cash tender from cash mode; paid amount is always due.
 start=s.index("function payFields(due)")
 end=s.index("function mixedBalance()",start)
 block=s[start:end]
 first=block.index("case'cash':return")
 next_case=block.index("case'bank':return",first)
 block=block[:first]+"""case'cash':return \`<div class="help">المطلوب كاش: <strong>\\${fmt(due)}</strong>. السداد كامل تلقائياً.</div>\`;"""+block[next_case:]
 s=s[:start]+block+s[end:]
 s=replace(s,"modal('تم إصدار فاتورة '+data.ref,receipt(actual)+", "modal('تم إصدار فاتورة '+data.ref,(data.net_profit===null||data.net_profit===undefined?'':'<div class=\\\"help\\\">صافي ربح الفاتورة: '+fmt(data.net_profit)+' ج.س</div>')+receipt(actual)+",'profit display')
 return s
edit('pharmacy/static/app.js',ui)
print('NOVA14_DISCOUNT_APPLIED')
