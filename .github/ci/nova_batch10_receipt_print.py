#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NOVA Batch10 — Match successful pharmacy receipt for hospital collections.

Applied after Batch09 to extracted Windows source. The pharmacy receipt is
intentionally not modified. No changes to finance/stock/database backend.
"""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]

def replace_exact(path,old,new,label):
    p=ROOT/path
    s=p.read_text(encoding="utf-8")
    if s.count(old)!=1:
        raise RuntimeError(f"NOVA10 print source drift: {label}, hits={s.count(old)}")
    p.write_text(s.replace(old,new,1),encoding="utf-8")

receipt_fn=r"""function novaPrintReceipt(inv){
  const last=inv?.payments||[];
  const p=last[last.length-1];
  if(!p)return notice('لا توجد دفعة مسجلة لإصدار الإيصال',true);
  const brand=state.brand||{},area=$('print-area');
  if(!area)return notice('تعذر العثور على مساحة الطباعة',true);
  const text=x=>esc(String(x??'—'));
  // Keep the stored local date/time exactly as written, without browser
  // timezone conversion; enforce one LTR element to avoid Arabic reordering.
  const clock=String(p.created_at||'').replace('T',' ').slice(0,16);
  const ltr=x=>'<b class="nova-receipt-ltr" dir="ltr">'+text(x)+'</b>';
  const row=(label,value,kind='')=>
    '<div class="nova-receipt-row"><span>'+text(label)+'</span><strong class="'+
    (kind==='ltr'?'nova-receipt-ltr':'')+'"'+(kind==='ltr'?' dir="ltr"':'')+'>'+
    text(value)+'</strong></div>';
  const cash=Number(p.cash_amount||0),bank=Number(p.bank_amount||0);
  const items=(inv.lines||[]).map(x=>
    '<div class="nova-receipt-service"><span>'+text(x.name)+'</span>'+
    '<span>'+money(Number(x.patient_part??x.price??0))+'</span></div>').join('');
  const receiptTotal=cash+bank;
  area.innerHTML='<article class="nova-thermal nova-thermal-v2" dir="rtl">'+
    '<div class="nova-receipt-head"><h2>'+text(brand.hospital_name||'NOVA Hospital')+'</h2>'+
    (brand.hospital_name_en?'<p lang="en" dir="ltr">'+text(brand.hospital_name_en)+'</p>':'')+
    '<strong>إيصال تحصيل — مستشفى</strong></div>'+
    '<div class="nova-receipt-divider"></div>'+
    row('رقم الإيصال',p.payment_no,'ltr')+
    row('رقم الفاتورة',inv.invoice_no,'ltr')+
    row('التاريخ والوقت',clock,'ltr')+
    row('المريض',inv.patient_name)+
    '<div class="nova-receipt-divider"></div>'+
    (items?'<div class="nova-receipt-service-title">الخدمات</div>'+items+
      '<div class="nova-receipt-divider"></div>':'')+
    (cash>0?row('نقدي',money(cash)):'')+
    (bank>0?row('تحويل بنكي',money(bank))+
      (p.bank_name?row('البنك',p.bank_name):'')+
      (p.bank_reference?row('رقم العملية',p.bank_reference,'ltr'):''):'')+
    '<div class="nova-receipt-divider"></div>'+
    '<div class="nova-receipt-total">'+row('قيمة هذه الدفعة',money(receiptTotal))+'</div>'+
    row('المتبقي على المريض',money(Number(inv.remaining||0)))+
    '<div class="nova-receipt-divider"></div>'+
    '<div class="nova-receipt-foot">'+(brand.hospital_phone?
       '<span dir="ltr">'+text(brand.hospital_phone)+'</span>':'')+
    '<strong>شكراً لزيارتكم</strong></div></article>';
  document.body.classList.add('printing-nova-thermal');
  let cleaned=false;
  const clear=()=>{
    if(cleaned)return;
    cleaned=true;document.body.classList.remove('printing-nova-thermal');area.innerHTML='';
  };
  window.addEventListener('afterprint',clear,{once:true});
  window.print();
  setTimeout(clear,30000);
}"""

finance=ROOT/'hospital/static/finance-ui.js'
s=finance.read_text(encoding='utf-8')
anchor='function novaPrintReceipt(inv){'
start=s.find(anchor)
if start<0 or s.count(anchor)!=1:
    at=s.find('novaPrintReceipt')
    raise RuntimeError('NOVA10 receipt anchor missing '+repr(s[max(0,at-45):at+105]))
end_token="window.addEventListener('afterprint',clear,{once:true});window.print();"
end=s.find(end_token,start)
if end<0:raise RuntimeError('NOVA10 old receipt cleanup anchor missing')
close=s.find('}',end+len(end_token))
if close<0:raise RuntimeError('NOVA10 receipt closing brace missing')
s=s[:start]+receipt_fn+s[close+1:]
old="if(receipt.status==='settled')financePrintInvoice(financeState.invoice);"
if s.count(old)!=1:
    raise RuntimeError('NOVA10 cashier automatic print anchor missing')
s=s.replace(old,"if(financeState.invoice?.payments?.length)novaPrintReceipt(financeState.invoice);",1)
finance.write_text(s,encoding='utf-8')

# CSS isolation matters: previous global A4 @page is applied to thermal tickets
# on some browser/printer combinations. Named ticket page uses the paper
# selected for the Xprinter in Chromium/Edge. A4 invoice & lab use default A4.
css=ROOT/'hospital/static/style.css'
style=css.read_text(encoding='utf-8')
extension=r"""
/* NOVA_BATCH10_THERMAL: same proven printable width and font as pharmacy. */
.nova-thermal-v2{direction:rtl;font-family:Tahoma,Arial,sans-serif;
  font-size:10pt;line-height:1.55;color:#101010;background:#fff;
  box-sizing:border-box;overflow-wrap:anywhere}
.nova-thermal-v2 .nova-receipt-head{text-align:center;padding:0 0 3mm}
.nova-thermal-v2 .nova-receipt-head h2{font-size:17pt;line-height:1.3;
  font-weight:800;margin:0 0 2mm}
.nova-thermal-v2 .nova-receipt-head p{font-size:10pt;margin:1mm 0}
.nova-thermal-v2 .nova-receipt-head strong{display:block;font-size:11pt}
.nova-thermal-v2 .nova-receipt-divider{border-top:1px dashed #333;
  margin:3mm 0}
.nova-thermal-v2 .nova-receipt-row{display:flex;align-items:baseline;
  justify-content:space-between;gap:2mm;padding:1mm 0}
.nova-thermal-v2 .nova-receipt-row span{flex:0 1 auto}
.nova-thermal-v2 .nova-receipt-row strong{flex:0 1 auto;
  text-align:start;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.nova-thermal-v2 .nova-receipt-ltr{direction:ltr!important;
  unicode-bidi:isolate;white-space:normal;text-align:left!important}
.nova-thermal-v2 .nova-receipt-service-title{font-weight:700;
  margin-bottom:1mm}
.nova-thermal-v2 .nova-receipt-service{display:flex;align-items:start;
  justify-content:space-between;gap:3mm;padding:1mm 0;
  border-bottom:1px dotted #ddd}
.nova-thermal-v2 .nova-receipt-service span:first-child{flex:1;min-width:0}
.nova-thermal-v2 .nova-receipt-service span:last-child{
  white-space:nowrap;font-weight:700}
.nova-thermal-v2 .nova-receipt-total{font-size:12pt;font-weight:800;
  border-top:1px solid #888;border-bottom:1px solid #888;
  padding:1mm 0;margin:1mm 0}
.nova-thermal-v2 .nova-receipt-foot{text-align:center;
  display:flex;flex-direction:column;gap:1mm;font-size:9pt}
@page novaReceiptPaper{size:auto;margin:3mm}
@media print{
  body.printing-nova-thermal{background:white!important;margin:0!important;
    padding:0!important}
  body.printing-nova-thermal > *:not(#print-area){display:none!important}
  body.printing-nova-thermal #print-area{display:block!important;
    position:static!important;inset:auto!important;padding:0!important;
    margin:0!important;width:100%!important;max-width:none!important}
  body.printing-nova-thermal #print-area .nova-thermal-v2{
    page:novaReceiptPaper;display:block!important;
    width:72mm!important;max-width:72mm!important;
    padding:0!important;margin:0 auto!important;
    box-shadow:none!important;border:0!important;
    font-family:Tahoma,Arial,sans-serif!important;font-size:10pt!important;
    line-height:1.5!important;break-inside:auto}
  body.printing-nova-thermal #print-area .nova-receipt-row,
  body.printing-nova-thermal #print-area .nova-receipt-service,
  body.printing-nova-thermal #print-area .nova-receipt-total{break-inside:avoid}
}
"""
if 'NOVA_BATCH10_THERMAL' in style:raise RuntimeError('NOVA10 CSS already applied')
css.write_text(style+'\n'+extension,encoding='utf-8')
print("NOVA_BATCH10_THERMAL_RECEIPTS_APPLIED without editing pharmacy or A4 lab/invoice")
