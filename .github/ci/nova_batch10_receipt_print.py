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

receipt_fn=r"""function novaPrintReceipt(inv,index){
  const last=inv?.payments||[];
  const selected=index??(last.length-1),p=last[selected];
  const remainAtReceipt=Math.max(0,Number(inv?.patient_due||0)-
    last.slice(0,selected+1).reduce((n,x)=>n+Number(x.cash_amount||0)+Number(x.bank_amount||0),0));
  if(!p)return notice('لا توجد دفعة مسجلة لإصدار الإيصال',true);
  const brand=state.brand||{};
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
  const receiptHTML='<article class="nova-thermal nova-thermal-v2" dir="rtl">'+
    '<div class="nova-receipt-head"><h2>'+text(brand.hospital_name||'NOVA Hospital')+'</h2>'+
    (brand.hospital_name_en?'<p lang="en" dir="ltr">'+text(brand.hospital_name_en)+'</p>':'')+
    '<strong>إيصال تحصيل — مستشفى</strong></div>'+
    '<div class="nova-receipt-divider"></div>'+
    row('رقم الإيصال',p.payment_no,'ltr')+
    row('رقم الفاتورة',inv.invoice_no,'ltr')+
    row('التاريخ والوقت',clock,'ltr')+
    row('المريض',inv.patient_name)+
    (p.cashier_name?row('الكاشير',p.cashier_name):'')+
    '<div class="nova-receipt-divider"></div>'+
    (items?'<div class="nova-receipt-service-title">الخدمات</div>'+items+
      '<div class="nova-receipt-divider"></div>':'')+
    (cash>0?row('نقدي',money(cash)):'')+
    (bank>0?row('تحويل بنكي',money(bank))+
      (p.bank_name?row('البنك',p.bank_name):'')+
      (p.bank_reference?row('رقم العملية',p.bank_reference,'ltr'):''):'')+
    '<div class="nova-receipt-divider"></div>'+
    '<div class="nova-receipt-total">'+row('قيمة هذه الدفعة',money(receiptTotal))+'</div>'+
    row('المتبقي بعد هذه الدفعة',money(remainAtReceipt))+
    '<div class="nova-receipt-divider"></div>'+
    '<div class="nova-receipt-foot">'+(brand.hospital_phone?
       '<span dir="ltr">'+text(brand.hospital_phone)+'</span>':'')+
    '<strong>شكراً لزيارتكم</strong></div></article>';
  novaPrintThermalDocument(receiptHTML);
}
/* Keep thermal tickets independent of hospital A4 page settings. */
function novaPrintThermalDocument(receiptHTML){
  const previous=document.getElementById('nova-thermal-frame');
  if(previous)previous.remove();
  const frame=document.createElement('iframe');
  frame.id='nova-thermal-frame';
  frame.title='طباعة إيصال حراري 80mm';
  frame.setAttribute('aria-hidden','true');
  frame.style.cssText='position:fixed;left:0;top:0;width:1px;height:1px;border:0;opacity:0;pointer-events:none';
  const printCSS=[
    '*{box-sizing:border-box}',
    'html,body{margin:0!important;padding:0!important;direction:rtl;color:#000;background:#fff}',
    'body{width:80mm!important;min-width:80mm!important;max-width:80mm!important;padding:4mm!important;font:10pt/1.45 Tahoma,Arial,sans-serif!important}',
    '.nova-thermal-v2{width:72mm!important;max-width:72mm!important;margin:0!important;padding:0!important;background:white!important;color:#000!important;direction:rtl;font:10pt/1.45 Tahoma,Arial,sans-serif!important;overflow-wrap:anywhere}',
    '.nova-receipt-head{text-align:center;margin:0 0 2mm}',
    '.nova-receipt-head h2{font-size:16pt;line-height:1.3;margin:0 0 1mm;font-weight:800}',
    '.nova-receipt-head p{font-size:9pt;margin:1mm 0}',
    '.nova-receipt-head strong{display:block;font-size:11pt}',
    '.nova-receipt-divider{margin:2.4mm 0;border-top:1px dashed #555}',
    '.nova-receipt-row{display:flex;justify-content:space-between;align-items:baseline;gap:3mm;padding:1.2mm 0;break-inside:avoid}',
    '.nova-receipt-row span{flex:0 0 auto}',
    '.nova-receipt-row strong{flex:0 1 auto;text-align:left;overflow-wrap:anywhere}',
    '.nova-receipt-ltr{direction:ltr!important;unicode-bidi:isolate;text-align:left!important;font-variant-numeric:tabular-nums}',
    '.nova-receipt-service-title{font-weight:800;margin-bottom:1mm}',
    '.nova-receipt-service{display:flex;justify-content:space-between;gap:3mm;padding:1mm 0;border-bottom:1px dotted #bbb;break-inside:avoid}',
    '.nova-receipt-service span:first-child{flex:1;min-width:0}',
    '.nova-receipt-service span:last-child{flex:0 0 auto;font-weight:700}',
    '.nova-receipt-total{font-size:12pt;font-weight:800;border-top:1px solid #777;border-bottom:1px solid #777;margin:1mm 0;padding:1mm 0;break-inside:avoid}',
    '.nova-receipt-foot{display:flex;flex-direction:column;gap:1mm;text-align:center;font-size:9pt;margin-top:2mm}',
    '@media print{html,body{width:80mm!important}.nova-thermal-v2{width:72mm!important}}'
  ].join('\n');
  frame.srcdoc='<!doctype html><html lang="ar" dir="rtl"><head>'+
    '<meta charset="utf-8"><title>NOVA — إيصال حراري</title><style>'+printCSS+'</style>'+
    '</head><body>'+receiptHTML+'</body></html>';
  let printed=false;
  let released=false;
  const cleanup=()=>{if(released)return;released=true;frame.remove()};
  frame.onload=async()=>{
    if(printed)return;printed=true;
    try{
      const doc=frame.contentDocument;
      if(!doc)throw Error('لا يمكن تحميل مستند الطباعة');
      if(doc.fonts?.ready)await doc.fonts.ready;
      const sheet=doc.querySelector('.nova-thermal-v2');
      if(!sheet)throw Error('محتوى الإيصال غير موجود');
      // One custom-length page. No hospital A4 CSS can leak into this frame.
      const px=Math.max(sheet.scrollHeight,sheet.getBoundingClientRect().height);
      const heightMM=Math.max(85,Math.min(900,Math.ceil(px*25.4/96+15)));
      const page=doc.createElement('style');
      page.textContent='@page{size:80mm '+heightMM+'mm;margin:0}';
      doc.head.appendChild(page);
      const win=frame.contentWindow;
      win.addEventListener('afterprint',cleanup,{once:true});
      win.focus();win.print();
      setTimeout(cleanup,120000);
    }catch(e){cleanup();notice('تعذر فتح الإيصال الحراري: '+e.message,true)}
  };
  document.body.appendChild(frame);
}"""

finance=ROOT/'hospital/static/finance-ui.js'
s=finance.read_text(encoding='utf-8')
anchor='function novaPrintReceipt(inv,index){'
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
if s.count('novaPrintReceipt(financeState.invoice);')!=1:
    raise RuntimeError('NOVA10 existing automatic partial-payment receipt printing missing')
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


# NOVA10_PHARMACY_ISOLATED_80MM — isolate the proven pharmacy SALE receipt
# from the surrounding application page and its @page/A4 rules. Purchase invoices
# still use the original A4-capable handler, and Windows printer selection is untouched.
pharmacy_path=ROOT/'pharmacy/static/app.js'
pharmacy=pharmacy_path.read_text(encoding='utf-8')
pharmacy_fn=r"""async function printReceipt(){
  const source=document.getElementById('printable');
  if(!source){toast('لا توجد فاتورة قابلة للطباعة',true);return}
  const b=nativeBridge();let paper=window.MADAR_PRINT_PAPER||'thermal80';
  if(b){try{const devices=await b.get_devices();paper=devices?.settings?.paper||paper}catch(e){/* use saved/default paper */}}
  // Preserve the original behavior for A4 purchase invoices and explicit A4 mode.
  if(paper==='a4'||(!source.classList.contains('thermal-receipt')&&!source.classList.contains('receipt-test'))){
    document.body.classList.remove('paper-thermal80','paper-thermal58','paper-a4');
    document.body.classList.add('paper-'+paper);
    document.body.classList.add('printing-receipt');
    const clean=()=>document.body.classList.remove('printing-receipt');
    window.addEventListener('afterprint',clean,{once:true});
    window.print();setTimeout(clean,120000);
    return;
  }
  novaPrintPharmacyThermalDocument(source.outerHTML,paper==='thermal58'?58:80);
}
function novaPrintPharmacyThermalDocument(receiptHTML,paperWidth){
  const old=document.getElementById('nova-pharmacy-print-frame');
  if(old)old.remove();
  const width=paperWidth===58?58:80;
  const inside=width===58?48:72;
  const frame=document.createElement('iframe');
  frame.id='nova-pharmacy-print-frame';
  frame.title='إيصال الصيدلية الحراري';
  frame.setAttribute('aria-hidden','true');
  frame.style.cssText='position:fixed;top:0;left:0;width:1px;height:1px;border:0;opacity:0;pointer-events:none';
  const css=[
    '*{box-sizing:border-box}',
    'html,body{margin:0!important;padding:0!important;color:#101010!important;background:white!important}',
    'body{width:'+width+'mm!important;max-width:'+width+'mm!important;padding:0 '+((width-inside)/2)+'mm!important;font:10pt/1.5 Tahoma,Arial,sans-serif!important;direction:rtl}',
    '#printable{display:block!important;position:static!important;width:'+inside+'mm!important;max-width:'+inside+'mm!important;min-width:0!important;margin:0!important;padding:0!important;border:0!important;box-shadow:none!important;direction:rtl!important;overflow-wrap:anywhere;color:#101010!important;font:10pt/1.5 Tahoma,Arial,sans-serif!important}',
    '#printable .receipt-center{text-align:center}',
    '#printable h2{font-size:16pt;line-height:1.3;margin:0 0 1mm;font-weight:800}',
    '#printable p{margin:1mm 0 2mm}',
    '#printable .receipt-divider{border:0;border-bottom:1px dashed #444;margin:2.5mm 0}',
    '#printable .receipt-line{padding:1mm 0;border-bottom:1px dotted #bbb;break-inside:avoid}',
    '#printable .receipt-line-name{font-weight:700;overflow-wrap:anywhere}',
    '#printable .receipt-line-nums,#printable .receipt-sum{display:flex;justify-content:space-between;align-items:start;gap:2mm;break-inside:avoid}',
    '#printable .receipt-grand{font-size:12pt;font-weight:800;border-top:1px solid #888;padding-top:1mm;margin-top:1mm}',
    '#printable table{width:100%;border-collapse:collapse}',
    '#printable th,#printable td{border:1px solid #ccc;padding:1mm;overflow-wrap:anywhere}',
    '@media print{html,body{width:'+width+'mm!important}#printable{width:'+inside+'mm!important}}'
  ].join('\\n');
  frame.srcdoc='<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>NOVA — إيصال الصيدلية</title><style>'+css+'</style></head><body>'+receiptHTML+'</body></html>';
  let invoked=false,released=false;
  const cleanup=()=>{if(released)return;released=true;frame.remove()};
  frame.onload=async()=>{
    if(invoked)return;invoked=true;
    try{
      const doc=frame.contentDocument;
      if(!doc)throw Error('مستند الطباعة غير متاح');
      if(doc.fonts?.ready)await doc.fonts.ready;
      const ticket=doc.getElementById('printable');
      if(!ticket)throw Error('الإيصال غير موجود');
      // Size only this document; do not affect A4 reports or printer defaults.
      const px=Math.max(ticket.scrollHeight,ticket.getBoundingClientRect().height);
      const heightMM=Math.max(85,Math.min(2000,Math.ceil(px*25.4/96+17)));
      const page=doc.createElement('style');
      page.textContent='@page{size:'+width+'mm '+heightMM+'mm;margin:0}';
      doc.head.appendChild(page);
      const win=frame.contentWindow;
      win.addEventListener('afterprint',cleanup,{once:true});
      win.focus();win.print();
      setTimeout(cleanup,120000);
    }catch(e){cleanup();toast('تعذر طباعة إيصال الصيدلية: '+e.message,true)}
  };
  document.body.appendChild(frame);
}
"""
pharmacy,n=re.subn(r'async function printReceipt\(\)\{.*?\n\}\n(?=function printPurchase\()',lambda _:pharmacy_fn+'\n',pharmacy,count=1,flags=re.S)
if n!=1:raise RuntimeError('NOVA10 pharmacy printReceipt source anchor has changed')
if 'class="thermal-receipt"' not in pharmacy:
    raise RuntimeError('NOVA10 proven pharmacy receipt HTML is missing')
pharmacy_path.write_text(pharmacy,encoding='utf-8')
print('NOVA10_PHARMACY_ISOLATED_80MM: pharmacy sale/test thermal only; purchases keep original print')
