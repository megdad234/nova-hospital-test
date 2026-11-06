/* NOVA supplier price-list review; never posts stock or purchase transactions. */
(()=>{'use strict';
let preview=[];
const el=(tag,txt)=>{const e=document.createElement(tag);if(txt!==undefined)e.textContent=txt;return e};
const panel=el('section');panel.id='nova-price-list-panel';panel.hidden=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-modal','true');panel.setAttribute('aria-label','مراجعة برايس الموردين');
panel.style.cssText='position:fixed;inset:6% 5%;z-index:9999;background:#fff;color:#153b43;overflow:auto;border:2px solid #0b8791;border-radius:16px;padding:22px;box-shadow:0 12px 50px #0006;direction:rtl';
const heading=el('h2','مراجعة برايس الموردين وتحديث أسعار البيع');panel.append(heading);
const close=el('button','إغلاق');close.type='button';close.onclick=()=>{if(approvalPending)return;invalidatePreview();panel.hidden=true};panel.append(close);
panel.append(el('p','ارفع CSV أو Excel: الأعمدة name,purchase_price,strength,pack,barcode. لا يتم تعديل المخزون أو المشتريات.'));
const file=el('input');file.type='file';file.accept='.csv,.xlsx,text/csv';file.setAttribute('aria-label','ملف برايس المورد');panel.append(file);
const pct=el('input');pct.type='number';pct.min='0';pct.max='1000';pct.step='0.01';pct.setAttribute('aria-label','نسبة الربح الاختيارية');pct.placeholder='نسبة ربح جديدة (اختياري: اتركها للمحافظة على هامش الربح)';panel.append(pct);
const previewBtn=el('button','معاينة الأسعار');panel.append(previewBtn);
const approveBtn=el('button','اعتماد الأصناف المحددة');approveBtn.disabled=true;panel.append(approveBtn);
const historyBtn=el('button','سجل الاعتماد والتراجع');panel.append(historyBtn);
const status=el('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');panel.append(status);
const summary=el('p');summary.style.cssText='font-weight:700;margin:12px 0';panel.append(summary);
const search=el('input');search.type='search';search.placeholder='بحث داخل نتائج المعاينة بالاسم أو الحالة';search.setAttribute('aria-label','بحث في نتائج البرايس');search.style.cssText='width:100%;max-width:440px;padding:10px;border:1px solid #bdd3d7;border-radius:10px;margin:8px 0';panel.append(search);
const filterBar=el('div');filterBar.style.cssText='display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:8px 0';
const showReview=el('input');showReview.type='checkbox';showReview.checked=false;
const reviewLabel=el('label',' إظهار الأصناف غير المطابقة (للمراجعة فقط)');reviewLabel.prepend(showReview);
const ignored=new Set();
const showIgnored=el('input');showIgnored.type='checkbox';
const ignoredLabel=el('label',' إظهار المستبعدة من المراجعة');ignoredLabel.prepend(showIgnored);
const changesOnly=el('input');changesOnly.type='checkbox';changesOnly.checked=true;
const changesLabel=el('label',' الأسعار المتغيرة فقط');changesLabel.prepend(changesOnly);
const selectedOnly=el('input');selectedOnly.type='checkbox';
const selectedLabel=el('label',' المحددة فقط');selectedLabel.prepend(selectedOnly);
filterBar.append(reviewLabel,changesLabel,selectedLabel,ignoredLabel);panel.append(filterBar);
const grid=el('div');panel.append(grid);
const applyFilters=()=>{const q=search.value.trim().toLowerCase();grid.querySelectorAll('tr[data-search]').forEach(row=>{const matched=row.dataset.status==='matched';row.hidden=(!showIgnored.checked&&ignored.has(Number(row.dataset.line)))||(!showReview.checked&&!matched)||(changesOnly.checked&&matched&&Number(row.dataset.newPrice)===Number(row.dataset.oldPrice))||(selectedOnly.checked&&!row.querySelector('input[type=checkbox]')?.checked)||(!!q&&!row.dataset.search.includes(q))})};
showReview.onchange=applyFilters;changesOnly.onchange=applyFilters;selectedOnly.onchange=applyFilters;showIgnored.onchange=applyFilters;search.oninput=applyFilters;
// Changing the source file or markup invalidates every prior approval token.
let previewVersion=0;
const invalidatePreview=()=>{ignored.clear();previewVersion++;preview=[];approveBtn.disabled=true;grid.replaceChildren();summary.textContent='';status.textContent='تغيرت بيانات البرايس؛ اضغط معاينة الأسعار مجدداً قبل الاعتماد.'};
file.addEventListener('change',invalidatePreview);
pct.addEventListener('input',invalidatePreview);
const csvParse=(txt)=>{
 const rows=[];let row=[],field='',quoted=false;
 for(let i=0;i<txt.length;i++){const c=txt[i];if(c==='"'){if(quoted&&txt[i+1]==='"'){field+='"';i++}else quoted=!quoted}
 else if(c===','&&!quoted){row.push(field);field=''}
 else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&txt[i+1]==='\n')i++;row.push(field);if(row.some(x=>x.trim()))rows.push(row);row=[];field=''}
 else field+=c}
 if(quoted)throw Error('علامات اقتباس CSV غير مكتملة');
 row.push(field);if(row.some(x=>x.trim()))rows.push(row);
 if(rows.length<2||rows.length>20001)throw Error('الملف فارغ أو أكبر من 20 ألف صنف');
 const headers=rows.shift().map(x=>x.trim().toLowerCase().replace(/^\uFEFF/,''));
 if(!headers.includes('name')||!headers.includes('purchase_price'))throw Error('الأعمدة المطلوبة: name,purchase_price');
 return rows.map((r,i)=>Object.fromEntries(headers.map((h,j)=>[h,r[j]||'']).concat([['line',i+2]])));
};
const request=async(path,body)=>{
 const res=await fetch('/api/v1/'+path,{credentials:'same-origin',method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
 const data=await res.json();if(!res.ok||data.error)throw Error(data.error||'تعذر الاتصال');return data;
};
previewBtn.onclick=async()=>{if(approvalPending)return;const version=++previewVersion;preview=[];approveBtn.disabled=true;grid.replaceChildren();summary.textContent='';previewBtn.disabled=true;status.textContent='جارٍ فحص ملف المورد ومطابقة الأسعار...';try{
 if(!file.files[0])throw Error('اختر ملف CSV أو Excel أولاً');
 if(pct.value!==''&&(!Number.isFinite(Number(pct.value))||Number(pct.value)<0||Number(pct.value)>1000))throw Error('نسبة الربح يجب أن تكون بين 0 و1000');
 if(file.files[0].size>6*1024*1024)throw Error('الملف كبير');
 const bytes=new Uint8Array(await file.files[0].arrayBuffer());let binary='';
 for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
 const parsed=await request('nova-price-list-parse',{filename:file.files[0].name,content_base64:btoa(binary)});
 const rows=parsed.rows;
 const payload={rows};if(pct.value!=='')payload.markup_percent=pct.value;
 const data=await request('nova-price-list-preview',payload);
 if(version!==previewVersion)return;
 preview=Array.isArray(data.rows)?data.rows:[];grid.replaceChildren();approveBtn.disabled=true;
 const table=el('table');table.style.width='100%';
 const tr=el('tr');['اعتماد','الصنف','الحالة','سعر الشراء الجديد','سعر البيع السابق','سعر البيع المقترح','الفرق','إجراء'].forEach(h=>tr.append(el('th',h)));table.append(tr);
 const matches=preview.filter(r=>r.status==='matched').length;
 summary.textContent='إجمالي صفوف البرايس '+preview.length+' · مطابق '+matches+' · يحتاج مراجعة '+(preview.length-matches)+' · غير المطابق مخفي افتراضياً. تنبيه: المطابقة الحالية ليست فلترة مؤكدة لرصيد المخزون.';
 preview.forEach(r=>{const line=el('tr');line.dataset.status=r.status;line.dataset.line=String(r.line);line.dataset.oldPrice=String(r.old_sale_price??'');line.dataset.newPrice=String(r.proposed_sale_price??'');line.dataset.search=String(r.name||'').toLowerCase()+' '+String(r.status||'').toLowerCase();const td=el('td');const cb=el('input');cb.type='checkbox';cb.checked=!!r.selected;cb.disabled=r.status!=='matched';r._checkbox=cb;cb.onchange=()=>{approveBtn.disabled=!preview.some(item=>item.status==='matched'&&item._checkbox?.checked);applyFilters()};td.append(cb);line.append(td);
 [r.name,r.status,r.purchase_price,r.old_sale_price??'-',r.proposed_sale_price??'-',r.status==='matched'?String(Number(r.proposed_sale_price)-Number(r.old_sale_price)):'-'].forEach(v=>line.append(el('td',String(v))));const action=el('td');if(r.status!=='matched'){if(Array.isArray(r.suggestions)&&r.suggestions.length){const details=el('details');const toggle=el('summary','أقرب '+r.suggestions.length+' خيارات (للمراجعة)');details.append(toggle);r.suggestions.forEach(x=>{const option=el('div',String(x.name)+' · '+String(x.strength)+' · '+String(x.pack));option.style.cssText='padding:4px 0;border-bottom:1px solid #ddd';details.append(option)});action.append(details)}const skip=el('button','استبعاد من المراجعة');skip.type='button';skip.onclick=()=>{ignored.add(Number(r.line));applyFilters()};action.append(skip)}line.append(action);table.append(line)});
 grid.append(table);applyFilters();approveBtn.disabled=!preview.some(item=>item.status==='matched'&&item._checkbox?.checked);status.textContent='المعاينة فقط؛ لم يتم تعديل أي سعر.';
 }catch(e){if(version!==previewVersion)return;preview=[];approveBtn.disabled=true;summary.textContent='';status.textContent=e.message}finally{if(version===previewVersion&&!approvalPending)previewBtn.disabled=false}};
let approvalPending=false;
approveBtn.onclick=async()=>{if(approvalPending)return;try{
 const items=preview.filter(r=>r._checkbox?.checked&&r.status==='matched').map(r=>({package_id:r.package_id,old_sale_price:r.old_sale_price,proposed_sale_price:r.proposed_sale_price,approval_token:r.approval_token}));
 if(!items.length)throw Error('حدد صنفاً واحداً على الأقل');
 if(!confirm('اعتماد '+items.length+' سعر بيع؟'))return;
 approvalPending=true;approveBtn.disabled=true;previewBtn.disabled=true;historyBtn.disabled=true;close.disabled=true;file.disabled=true;pct.disabled=true;status.textContent='جارٍ اعتماد الأسعار المحددة...';
 const data=await request('nova-price-list-approve',{items});invalidatePreview();status.textContent='تم اعتماد '+data.updated+' سعر. راجع السجل للتراجع.';
 }catch(e){status.textContent=e.message}finally{approvalPending=false;previewBtn.disabled=false;historyBtn.disabled=false;close.disabled=false;file.disabled=false;pct.disabled=false}};
historyBtn.onclick=async()=>{if(approvalPending)return;invalidatePreview();summary.textContent='سجل اعتماد وتراجع الأسعار';try{
 const data=await request('nova-price-list-history');grid.replaceChildren();
 const records=Array.isArray(data)?data:(data.rows||[]);
 records.forEach(r=>{const div=el('div',r.created_at+' · '+r.action+' · #'+r.id+' ');if(r.action==='bulk_supplier_price_list_approved'){
 const b=el('button','تراجع');b.onclick=async()=>{if(!confirm('استرجاع جميع أسعار هذه العملية؟'))return;try{await request('nova-price-list-rollback',{audit_id:r.id});status.textContent='تم التراجع';historyBtn.click()}catch(e){status.textContent=e.message}};div.append(b)}
 grid.append(div)});
 }catch(e){status.textContent=e.message}};
document.addEventListener('DOMContentLoaded',()=>{
  // Price-list upload belongs to the existing prices screen, never to checkout.
  const launch=el('button','تحديث الأسعار من برايس');
  launch.id='nova-price-list-launch';
  launch.className='btn outline small';
  launch.onclick=()=>{invalidatePreview();panel.hidden=false;file.focus()};
  document.body.append(panel);
  const previousNav=nav;
  nav=function(page){
    previousNav(page);
    launch.remove();
    if(page!=='prices')return;
    const main=document.querySelector('main')||document.querySelector('#app');
    const target=main?.querySelector('.panel-head')||main?.querySelector('.panel');
    if(target)target.append(launch);
  };
  const active=document.querySelector('[data-page="prices"].active');
  if(active)nav('prices');
});
})();