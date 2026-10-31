# -*- coding:utf-8 -*-
"""NOVA Batch05 user interfaces: pharmacy draft carts/tasks; cashier queue and receipt."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]
def change(name,callback):
    p=ROOT/name;s=p.read_text(encoding='utf-8');t=callback(s)
    if t==s:raise RuntimeError('NOVA05_UI_NOT_CHANGED '+name)
    p.write_text(t,encoding='utf-8')
    print('NOVA05_UI_OK',name)
def one(s,a,b):
    if s.count(a)!=1:raise RuntimeError('NOVA05_UI_ANCHOR '+repr(a[:70])+' count '+str(s.count(a)))
    return s.replace(a,b)

def pharmacy(s):
    s,n=re.subn(r"(\['dashboard','[^']+','[^']+'\],)",lambda m:m.group(1)+"['nova-tasks','☷','مهام الصيدلية'],",s,count=1)
    if n!=1:raise RuntimeError('NOVA05_TASKS_MENU')
    s=one(s,'const content={dashboard:dashboard,pos:pos',"const content={'nova-tasks':novaTaskPage,dashboard:dashboard,pos:pos")
    start='return '+chr(96)+'<div class="salearea">'
    bar='<div class="nova-holdbar"><b>الفواتير المعلقة</b><button class="btn" onclick="novaHoldNow()">تعليق الفاتورة</button><button class="btn" onclick="novaShowHeld()">عرض المعلقة</button><div id="nova-holdlist"></div></div>'
    s=one(s,start,start+bar)
    s+="""
// NOVA_BATCH05_EXTENSION: drafts do not reserve inventory.
async function novaHoldNow(){
 try{
  if(!state.saleRows.length)return toast('السلة فارغة',true);
  const label=prompt('اسم الفاتورة المعلقة','فاتورة معلقة');if(label===null)return;
  await api('hold-sale',{label,items:state.saleRows.map(x=>({package_id:x.package_id,qty:x.qty})),
    partner_id:state.customerId||null,authority_id:state.authorityId||null,coverage:state.coverage||0});
  state.saleRows=[];state.idempotency=token();redraw();
  toast('تم تعليق الفاتورة دون خصم المخزون');await novaShowHeld();
 }catch(e){toast(e.message,true)}
}
async function novaShowHeld(){
 try{
  const list=await api('held-sales'),area=$('nova-holdlist');if(!area)return;
  area.innerHTML=list.length?list.map(x=>'<div class="nova-held-row"><b>'+esc(x.label)+'</b> <small>'+
    x.item_count+' صنف</small><button class="btn" onclick="novaResumeHeld('+x.id+')">استرجاع</button>'+
    '<button class="btn" onclick="novaRemoveHeld('+x.id+')">حذف</button></div>').join(''):'لا توجد فواتير معلقة';
 }catch(e){toast(e.message,true)}
}
async function novaResumeHeld(id){
 try{
  if(state.saleRows.length&&!confirm('استرجاع الفاتورة سيستبدل السلة الحالية. متابعة؟'))return;
  const x=(await api('held-sales')).find(x=>x.id===id);
  if(!x)throw Error('الفاتورة غير موجودة');
  state.saleRows=x.cart.items.map(y=>({package_id:y.package_id,qty:y.qty}));
  state.customerId=x.cart.partner_id||'';
  state.authorityId=x.cart.authority_id||'';
  state.coverage=x.cart.coverage||0;
  state.idempotency=token();nav('pos');
  toast('تم استرجاع السلة. الأسعار والرصيد يتراجعوا عند البيع الفعلي.');
 }catch(e){toast(e.message,true)}
}
async function novaRemoveHeld(id){
 if(!confirm('حذف الفاتورة المعلقة؟'))return;
 try{await api('held-sale-delete',{held_id:id});await novaShowHeld()}catch(e){toast(e.message,true)}
}
function novaTaskPage(){
 const t=state.novaTaskData;
 if(!t&&!state.novaTaskBusy){
   state.novaTaskBusy=true;
   api('pharmacy-tasks').then(x=>{state.novaTaskData=x;if(state.page==='nova-tasks')nav('nova-tasks')})
       .catch(e=>toast(e.message,true)).finally(()=>state.novaTaskBusy=false);
 }
 const cards=[['held_carts','فواتير معلقة','pos'],
   ['receipts_outstanding','مشتريات بانتظار استلام','purchases'],
   ['reorder_items','أصناف تحتاج إعادة طلب','stock'],
   ['expiry_90_days','تشغيلات قريبة الصلاحية','stock'],
   ['unpriced_packages','عبوات بلا أسعار','catalog']];
 return '<div class="panel"><div class="panel-head"><h2>مهام الصيدلية</h2>'+
  '<button class="btn" onclick="state.novaTaskData=null;nav(\\'nova-tasks\\')">تحديث</button></div>'+
  '<p>مؤشرات اليوم من قاعدة السيرفر المركزية؛ لا تعني حجز مخزون.</p></div>'+
  '<div class="nova-task-grid">'+cards.map(([key,label,link])=>
    '<button class="nova-task-card" onclick="nav(\\''+link+'\\')"><b>'+
      (t?t[key]:'—')+'</b><span>'+esc(label)+'</span></button>').join('')+'</div>';
}
"""
    return s
change('pharmacy/static/app.js',pharmacy)

def cashier(s):
    # Replace only the superficial cashier list. All payment/refund functions remain unchanged.
    view="""function financeCashierView(){
 const invoices=financeState.invoices;
 return '<div class="grid">'+stat('طلبات معلقة',invoices.filter(x=>x.status==='pending').length)+
 stat('تم تحصيلها',invoices.filter(x=>x.status==='settled').length)+
 stat('المتبقي على المرضى',money(invoices.filter(x=>x.status==='pending').reduce((n,x)=>n+x.remaining,0)))+'</div>'+
 panel('طلبات الكاشير — استقبال ومعمل','<div class="toolbar">'+
 '<input id="nova-queue-search" type="search" placeholder="اسم المريض أو رقم الملف أو الفاتورة">'+
 '<select id="nova-queue-status"><option value="pending">معلقة</option><option value="partial">دفع جزئي</option>'+
 '<option value="settled">مدفوعة</option><option value="all">الكل</option></select>'+
 '<button id="nova-queue-refresh" class="outline">تحديث</button></div>'+
 '<div id="nova-queue-data">جاري تحميل الطلبات...</div>'+
 '<div class="toolbar"><button class="outline" id="nova-queue-prev">السابق</button>'+
 '<span id="nova-queue-pages"></span><button class="outline" id="nova-queue-next">التالي</button></div>')+
 '<details class="nova-cashier-quick"><summary>+ إنشاء طلب خدمة مباشر عند الحاجة</summary>'+
 financeServicesView()+'</details>'+
 '<div id="finance-invoice-details"></div>';
}
"""
    s,n=re.subn(r"function financeCashierView\(\)\{.*?(?=function financeInvoiceForm\()",lambda m:view,s,count=1,flags=re.S)
    if n!=1:raise RuntimeError('NOVA05_CASHIER_VIEW_ANCHOR')
    s=one(s,"function wireFinanceCashier(){","function wireFinanceCashier(){novaWireQueue();wireFinanceReception();")
    s=one(s,'<button type="button" class="outline" id="print-invoice">طباعة الفاتورة / الإيصال</button>',
        '<button type="button" class="outline" id="print-invoice">طباعة الفاتورة</button><button type="button" class="outline" id="nova-print-receipt">إيصال آخر دفعة 80mm</button>')
    s=one(s,"$('print-invoice')?.addEventListener('click',()=>financePrintInvoice(financeState.invoice));",
       "$('print-invoice')?.addEventListener('click',()=>financePrintInvoice(financeState.invoice));\n   $('nova-print-receipt')?.addEventListener('click',()=>novaPrintReceipt(financeState.invoice));")
    s=one(s,"const inv=await api('invoices',{",
            "const inv=await api(state.role==='cashier'?'nova-cashier-quick-invoice':'invoices',{")
    s+="""
// NOVA_BATCH05_EXTENSION: unified cashier queue, server-side search & pagination.
let novaQueuePage=0,novaQueueTyping=null,novaQueuePoll=null;
function novaWireQueue(){
 const input=$('nova-queue-search');if(!input)return;
 input.oninput=()=>{clearTimeout(novaQueueTyping);novaQueueTyping=setTimeout(()=>novaLoadQueue(0),250)};
 $('nova-queue-status').onchange=()=>novaLoadQueue(0);
 $('nova-queue-refresh').onclick=()=>novaLoadQueue(novaQueuePage);
 $('nova-queue-prev').onclick=()=>novaLoadQueue(Math.max(0,novaQueuePage-1));
 $('nova-queue-next').onclick=()=>novaLoadQueue(novaQueuePage+1);
 novaLoadQueue(0);
}
async function novaLoadQueue(page){
 const box=$('nova-queue-data');if(!box||state.section!=='cashier')return;
 const q=$('nova-queue-search').value,status=$('nova-queue-status').value;
 try{
   const d=await api('cashier-queue?q='+encodeURIComponent(q)+'&status='+status+'&page='+page);
   if(state.section!=='cashier'||$('nova-queue-search')?.value!==q)return;
   novaQueuePage=d.page;
   const rows=d.rows.map(x=>{
     const remain=Math.max(0,x.patient_due-x.paid),label=x.status==='settled'?'مدفوعة':x.paid>0?'دفع جزئي':'بانتظار الدفع';
     return '<tr><td dir="ltr">'+esc(x.number)+'</td><td>'+esc(x.patient_name)+
       '<small> '+esc(x.patient_no)+'</small></td><td>'+esc(x.kind==='legacy_lab'?'معمل قديم':'الخدمات')+
       '</td><td>'+money(remain)+'</td><td>'+label+'</td><td>'+
       '<button type="button" class="outline" data-nova-row="'+x.id+'" data-nova-kind="'+esc(x.kind)+'">فتح</button></td></tr>';
   });
   box.innerHTML=table(['الطلب','المريض','المصدر','المتبقي','الحالة',''],rows);
   $('nova-queue-pages').textContent='صفحة '+(d.page+1)+' من '+Math.max(1,Math.ceil(d.total/d.page_size))+' · '+d.total+' طلب';
   $('nova-queue-prev').disabled=d.page===0;
   $('nova-queue-next').disabled=(d.page+1)*d.page_size>=d.total;
   box.querySelectorAll('[data-nova-row]').forEach(btn=>btn.onclick=async()=>{
     try{
       const id=Number(btn.dataset.novaRow);
       if(btn.dataset.novaKind==='legacy_lab'){
         if(!confirm('تحويل طلب المعمل القديم إلى فاتورة موحدة بدون تحصيل مكرر؟'))return;
         const invoice=await api('nova-legacy-adopt',{order_id:id});
         await novaLoadQueue(novaQueuePage);await financeOpenInvoice(invoice.id);
       } else await financeOpenInvoice(id);
     }catch(e){notice(e.message,true)}
   });
   clearTimeout(novaQueuePoll);
   novaQueuePoll=setTimeout(()=>{if(state.section==='cashier')novaLoadQueue(novaQueuePage)},25000);
 }catch(e){box.innerHTML='<p class="muted">خطأ تحميل الطلبات: '+esc(e.message)+'</p>'}
}
function novaPrintReceipt(inv){
 const p=inv?.payments?.[inv.payments.length-1];if(!p)return notice('لا توجد دفعة مسجلة',true);
 const brand=state.brand||{},area=$('print-area');
 area.innerHTML='<article class="nova-thermal" dir="rtl"><h3>'+esc(brand.hospital_name||'مستشفى')+
 '</h3><p>إيصال دفع رقم '+esc(p.payment_no)+'</p><p>المريض: '+esc(inv.patient_name)+
 '</p><p>الفاتورة: '+esc(inv.invoice_no)+'</p><p>التاريخ: '+esc(p.created_at)+'</p><hr>'+
 '<p>نقدي: '+money(p.cash_amount)+'</p><p>بنكي: '+money(p.bank_amount)+'</p>'+
 '<p><b>هذه الدفعة: '+money(p.cash_amount+p.bank_amount)+'</b></p>'+
 '<p>المتبقي: '+money(inv.remaining)+'</p><small>'+esc(brand.hospital_phone||'')+'</small></article>';
 document.body.classList.add('printing-nova-thermal');
 const clear=()=>{document.body.classList.remove('printing-nova-thermal');area.innerHTML=''};
 window.addEventListener('afterprint',clear,{once:true});window.print();
}
"""
    return s
change('hospital/static/finance-ui.js',cashier)
def patients(s):
    return one(s,"['admin','reception','lab','frontdesk'].includes(state.role)",
               "['admin','reception','lab','frontdesk','cashier'].includes(state.role)")
change('hospital/static/app.js',patients)
def routes(s):
    if "if path=='/api/hospital/invoice-payment':" not in s:raise RuntimeError('NOVA05_ADOPT_ANCHOR')
    s=one(s,"                    if path=='/api/hospital/invoice-payment':",
     """                    if path=='/api/hospital/nova-legacy-adopt':
                         core.require_role(role,'admin','cashier','frontdesk')
                         return self.reply(finance.adopt_lab_order(c,user,data))
                    if path=='/api/hospital/invoice-payment':""")
    # Explicit quick-order path avoids silently broadening all reception write permissions.
    s=one(s,"                    if path=='/api/hospital/nova-legacy-adopt':",
       """                    if path=='/api/hospital/nova-cashier-quick-invoice':
                         core.require_role(role,'admin','cashier','frontdesk')
                         return self.reply(finance.create_invoice(c,user,data),201)
                    if path=='/api/hospital/nova-legacy-adopt':""")
    s=s.replace("core.require_role(role,'admin','reception','lab');term=",
                "core.require_role(role,'admin','reception','lab','cashier');term=")
    s=s.replace("core.require_role(role,'admin','reception','lab');return self.reply(core.create_patient",
                "core.require_role(role,'admin','reception','lab','cashier');return self.reply(core.create_patient")
    return s
change('hospital/gateway.py',routes)
css="""
/* NOVA_BATCH05_EXTENSION: compact cashier and pharmacy cards */
.nova-holdbar{grid-column:1/-1;display:flex;align-items:center;flex-wrap:wrap;gap:8px;border:1px solid #cce5d7;border-radius:14px;background:#f5fcf8;padding:13px}
.nova-holdlist{flex:1}.nova-held-row{display:flex;gap:8px;align-items:center;background:#fff;padding:7px;border-radius:10px;width:100%}
.nova-held-row small{margin-inline-end:auto;color:#608076}
.nova-task-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin-top:15px}
.nova-task-card{padding:17px;text-align:start;display:grid;gap:8px;background:#fff;border:1px solid #d2e7de;border-radius:15px;cursor:pointer}
.nova-task-card b{font-size:1.9rem;color:#0e6758}
.nova-cashier-quick{border:1px solid #d5e5db;border-radius:13px;padding:15px;margin-top:16px}
.nova-cashier-quick summary{cursor:pointer;font-weight:700}
.nova-thermal{width:75mm;max-width:75mm;padding:3mm;margin:auto;font:11px/1.7 Arial,sans-serif}
.nova-thermal h3{text-align:center}
@media print{body.printing-nova-thermal .nova-thermal{box-shadow:none;border:0;width:75mm!important;max-width:75mm!important} }
"""
change('hospital/static/style.css',lambda s:s+css)
change('pharmacy/static/style.css',lambda s:s+css)
print('NOVA_BATCH05_UI_DONE')
