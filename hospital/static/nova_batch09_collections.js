/* NOVA Batch09 — admin-only inspectable collection ledger, dedicated bank filters.
   Preserves existing hospital overview and insurer receivable reports. */
'use strict';
(function(){
 const eventText={payment:'تحصيل',refund:'استرداد',settlement:'تسوية تأمين'};
 const safe=v=>esc(String(v??''));
 const fmtNum=v=>money(Number(v||0));
 const filters={scope:'patient',method:'all',bank_id:'0',staff_id:'0',page:0};
 let current=null;
 const oldAdminView=viewAdminPage;
 viewAdminPage=async function(section){
   const existing=await oldAdminView(section);
   if(section!=='admin-finance')return existing;
   const block='<section class="panel nova-collections" id="nova-collection-panel" dir="rtl">'+
     '<div class="panel-head"><div><h2>كشف التحصيل التفصيلي</h2>'+
     '<p class="muted">تفاصيل النقدي والبنوك وأرقام العمليات، مع فصل تسويات شركات التأمين</p></div></div>'+
     '<div class="nova-collections-controls no-print">'+
     '<label>مصدر التحصيل<select id="nova-col-scope"><option value="patient">تحصيلات المرضى (مطابقة لإجمالي الأدمن)</option>'+
     '<option value="insurance">تسويات شركات التأمين</option><option value="all">كل المصادر — بدون ازدواج</option></select></label>'+
     '<label>طريقة التحصيل<select id="nova-col-method"><option value="all">الكاش والبنوك</option>'+
     '<option value="bank">البنوك فقط</option><option value="cash">الكاش فقط</option></select></label>'+
     '<label>البنك<select id="nova-col-bank"><option value="0">كل البنوك</option></select></label>'+
     '<label>الموظف<select id="nova-col-staff"><option value="0">كل الموظفين</option></select></label>'+
     '<button type="button" class="primary" id="nova-col-show">عرض الكشف</button>'+
     '<button type="button" class="outline" id="nova-col-xlsx">Excel (.xlsx)</button>'+
     '<button type="button" class="outline" id="nova-col-pdf">طباعة / PDF كامل</button></div>'+
     '<div id="nova-col-content" aria-live="polite">جارٍ تحميل تفاصيل التحصيل...</div></section>';
   const end=existing.lastIndexOf('</div>');
   return end>=0?existing.slice(0,end)+block+existing.slice(end):existing+block;
 };
 const oldWire=wireAdminPage;
 wireAdminPage=function(section){
   oldWire(section);
   if(section!=='admin-finance')return;
   const scope=$('nova-col-scope'),method=$('nova-col-method');
   if(!scope||!method)return;
   scope.value=filters.scope;method.value=filters.method;
   for(const id of ['nova-col-scope','nova-col-method','nova-col-bank','nova-col-staff']){
      $(id).onchange=()=>{filters[id.replace('nova-col-','').replace('bank','bank_id').replace('staff','staff_id')]=$(id).value;
         filters.page=0;novaLoadCollections();};
   }
   $('nova-col-show').onclick=()=>{filters.page=0;novaLoadCollections()};
   $('nova-col-xlsx').onclick=()=>novaExportCollections();
   $('nova-col-pdf').onclick=()=>novaPrintCollections();
   novaLoadCollections();
 };
 function query(page,all){
   const pairs=new URLSearchParams({from:adminState.from,to:adminState.to,scope:filters.scope,
    method:filters.method,bank_id:filters.bank_id,staff_id:filters.staff_id,page:String(page??filters.page)});
   return 'admin/'+(all?'collection-export':'collection-detail')+'?'+pairs.toString();
 }
 function renderRow(r){
   const neg=Number(r.amount)<0;
   return '<tr'+(neg?' class="nova-col-refund"':'')+'>'+
     '<td dir="ltr">'+safe(r.created_at)+'</td>'+
     '<td>'+safe(eventText[r.event]||r.event)+'</td>'+
     '<td dir="ltr">'+safe(r.document_no)+'</td>'+
     '<td dir="ltr">'+safe(r.invoice_no)+'</td>'+
     '<td>'+safe(r.person)+'</td>'+
     '<td>'+safe(r.department||'—')+'</td>'+
     '<td>'+safe(r.employee)+'</td>'+
     '<td>'+safe(r.method==='bank'?'بنكي':'كاش')+'</td>'+
     '<td>'+safe(r.method==='bank'?r.bank_name:'—')+'</td>'+
     '<td dir="ltr">'+safe(r.bank_reference||'—')+'</td>'+
     '<td class="nova-col-money">'+fmtNum(r.amount)+'</td></tr>';
 }
 function renderFull(data){
   const s=data.summary;
   const tiles=[['تحصيل نقدي',s.cash_gross],['تحصيل بنكي',s.bank_gross],
     ['مرتجعات نقدي',s.cash_refunds],['مرتجعات بنكي',s.bank_refunds],
     ['صافي النقدي',s.cash_net],['صافي البنكي',s.bank_net],
     ['صافي التحصيل',s.net],['عدد الحركات',s.count]];
   const cards='<div class="nova-col-kpis">'+tiles.map(([n,v])=>
     '<div><small>'+safe(n)+'</small><strong>'+((n==='عدد الحركات')?safe(v):fmtNum(v))+'</strong></div>').join('')+'</div>';
   const rows=data.rows.length?data.rows.map(renderRow).join(''):
       '<tr><td colspan="11">لا توجد حركات مطابقة للفترة أو البنك المحدد.</td></tr>';
   const header=['الوقت','الحركة','رقم الإيصال','رقم الفاتورة','المريض / الشركة',
     'القسم','الموظف','الطريقة','البنك','رقم العملية','المبلغ'];
   return cards+'<div class="nova-col-table"><table><thead><tr>'+
     header.map(h=>'<th>'+h+'</th>').join('')+'</tr></thead><tbody>'+rows+'</tbody></table></div>'+
     '<div class="nova-col-footer no-print"><span>عدد الحركات المطابقة: '+safe(data.total_rows)+
     ' · صفحة '+(data.filters.page+1)+' من '+Math.max(1,Math.ceil(data.total_rows/data.page_size))+'</span>'+
     '<button type="button" class="outline" id="nova-col-prev" '+(data.filters.page<1?'disabled':'')+'>السابق</button>'+
     '<button type="button" class="outline" id="nova-col-next" '+(!data.has_more?'disabled':'')+'>التالي</button></div>'+
     '<p class="muted small">'+safe(data.note)+'</p>';
 }
 async function novaLoadCollections(){
    const dest=$('nova-col-content');if(!dest)return;
    dest.textContent='جارٍ تحميل كشف التحصيل...';
    try{
      const data=await api(query(filters.page));
      if(!$('nova-col-content'))return;
      current=data;
      const bank=$('nova-col-bank'),staff=$('nova-col-staff');
      if(bank&&bank.options.length===1){
        bank.innerHTML='<option value="0">كل البنوك</option>'+
          data.banks.map(b=>'<option value="'+Number(b.id)+'">'+safe(b.name)+'</option>').join('');
      }
      if(staff&&staff.options.length===1){
        staff.innerHTML='<option value="0">كل الموظفين</option>'+
          data.staff.map(u=>'<option value="'+Number(u.id)+'">'+safe(u.full_name)+'</option>').join('');
      }
      if(bank)bank.value=filters.bank_id;if(staff)staff.value=filters.staff_id;
      dest.innerHTML=renderFull(data);
      $('nova-col-prev').onclick=()=>{filters.page=Math.max(0,filters.page-1);novaLoadCollections()};
      $('nova-col-next').onclick=()=>{filters.page++;novaLoadCollections()};
    }catch(e){current=null;dest.textContent='خطأ تحميل كشف التحصيل: '+e.message;notice(e.message,true)}
 }
 async function novaDownloadEntireData(){
   const data=await api(query(0,true));
   if(!data?.base64||!data.filename)throw Error('ملف التصدير غير متوفر');
   const binary=atob(data.base64);
   const bytes=new Uint8Array(binary.length);
   for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);
   const url=URL.createObjectURL(new Blob([bytes],{type:data.content_type}));
   const link=document.createElement('a');link.href=url;link.download=data.filename;
   document.body.appendChild(link);link.click();link.remove();
   setTimeout(()=>URL.revokeObjectURL(url),10000);
 }
 async function novaExportCollections(){
   try{await novaDownloadEntireData();notice('تم إعداد كشف Excel كاملاً حسب الفلاتر الحالية')}
   catch(e){notice('فشل تصدير Excel: '+e.message,true)}
 }
 async function novaPrintCollections(){
   try{
     // Fetch EVERY page, not only the first 80 visible rows.
     const allRows=[];
     let page=0,meta=null;
     do{
       meta=await api(query(page,false));
       allRows.push(...meta.rows);
       if(!meta.has_more)break;
       page++;
       if(page>1500)throw Error('التقرير أكبر من حد الطباعة؛ استخدم تصدير Excel');
     }while(true);
     const area=$('print-area');
     if(!area)throw Error('مساحة الطباعة غير متوفرة');
     const name=state.brand?.hospital_name||'NOVA Hospital';
     const payload={...meta,rows:allRows};
     area.innerHTML='<article class="adm-print-sheet nova-collections-print" dir="rtl">'+
       '<header class="adm-print-head"><div><h1>'+safe(name)+'</h1>'+
       '<h2>كشف التحصيل التفصيلي</h2><p>'+safe(adminState.from)+' إلى '+safe(adminState.to)+'</p></div></header>'+
       renderFull({...payload,has_more:false,filters:{...payload.filters,page:0},page_size:Math.max(1,allRows.length)})+
       '<footer>عدد العمليات: '+allRows.length+' — المبالغ بالجنيه السوداني — تقرير NOVA</footer></article>';
     // Preview before printing; do not modify shared receipt print engine.
     const existing=$('nova-collection-preview');if(existing)existing.remove();
     const overlay=document.createElement('div');
     overlay.id='nova-collection-preview';
     overlay.style.cssText='position:fixed;inset:0;z-index:99999;background:rgba(15,23,42,.72);display:flex;flex-direction:column;padding:16px;box-sizing:border-box;direction:rtl';
     const toolbar=document.createElement('div');
     toolbar.style.cssText='background:#fff;border-radius:12px 12px 0 0;padding:12px;display:flex;gap:12px;align-items:center';
     const printBtn=document.createElement('button');printBtn.type='button';printBtn.textContent='طباعة / حفظ PDF';printBtn.className='primary';
     const closeBtn=document.createElement('button');closeBtn.type='button';closeBtn.textContent='إغلاق المعاينة';closeBtn.className='outline';
     toolbar.append(printBtn,closeBtn);
     const preview=document.createElement('div');preview.style.cssText='background:#f1f5f9;overflow:auto;flex:1;padding:16px;border-radius:0 0 12px 12px';
     const sheet=area.firstElementChild.cloneNode(true);sheet.style.cssText='background:white;max-width:1100px;margin:auto;padding:20px;direction:rtl';
     preview.appendChild(sheet);overlay.append(toolbar,preview);document.body.appendChild(overlay);
     const close=()=>{overlay.remove();area.innerHTML='';document.body.classList.remove('printing-admin','nova-collection-printing')};
     closeBtn.onclick=close;
     printBtn.onclick=()=>{overlay.style.display='none';document.body.classList.add('printing-admin','nova-collection-printing');window.addEventListener('afterprint',close,{once:true});window.print();setTimeout(()=>{if(document.body.contains(overlay)){document.body.classList.remove('printing-admin','nova-collection-printing');overlay.style.display='flex'}},1200)};
   }catch(e){notice('فشل إعداد PDF: '+e.message,true)}
 }
})();
