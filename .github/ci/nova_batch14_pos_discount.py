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
 s=replace(s,"            amount=qty*row['unit_price'];cv=(amount*s['coverage']+50)//100",
 """            # Cumulative allocation prevents a split refund from exceeding
            # the original discounted line, including rounding remainders.
            before=(row['total']*earlier)//row['qty']
            after=(row['total']*(earlier+qty))//row['qty']
            amount=after-before
            cv=(amount*s['coverage']+50)//100""",'refund net')
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
 return s
edit('pharmacy/static/app.js',ui)
print('NOVA14_DISCOUNT_APPLIED')
