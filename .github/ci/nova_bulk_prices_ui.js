/* NOVA supplier price-list review; never posts stock or purchase transactions. */
(()=>{'use strict';
let preview=[];
const el=(tag,txt)=>{const e=document.createElement(tag);if(txt!==undefined)e.textContent=txt;return e};
const panel=el('section');panel.id='nova-price-list-panel';panel.hidden=true;
panel.style.cssText='position:fixed;inset:6% 5%;z-index:9999;background:#fff;color:#153b43;overflow:auto;border:2px solid #0b8791;border-radius:16px;padding:22px;box-shadow:0 12px 50px #0006;direction:rtl';
const heading=el('h2','مراجعة برايس الموردين وتحديث أسعار البيع');panel.append(heading);
const close=el('button','إغلاق');close.onclick=()=>panel.hidden=true;panel.append(close);
panel.append(el('p','ارفع CSV أو Excel: الأعمدة name,purchase_price,strength,pack,barcode. لا يتم تعديل المخزون أو المشتريات.'));
const file=el('input');file.type='file';file.accept='.csv,.xlsx,text/csv';panel.append(file);
const pct=el('input');pct.type='number';pct.min='0';pct.max='1000';pct.placeholder='نسبة ربح جديدة (اختياري: اتركها للمحافظة على هامش الربح)';panel.append(pct);
const previewBtn=el('button','معاينة الأسعار');panel.append(previewBtn);
const approveBtn=el('button','اعتماد الأصناف المحددة');approveBtn.disabled=true;panel.append(approveBtn);
const historyBtn=el('button','سجل الاعتماد والتراجع');panel.append(historyBtn);
const status=el('p');panel.append(status);
const grid=el('div');panel.append(grid);
// Changing the source file or markup invalidates every prior approval token.
const invalidatePreview=()=>{preview=[];approveBtn.disabled=true;grid.replaceChildren();status.textContent='تغيرت بيانات البرايس؛ اضغط معاينة الأسعار مجدداً قبل الاعتماد.'};
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
previewBtn.onclick=async()=>{preview=[];approveBtn.disabled=true;grid.replaceChildren();try{
 if(!file.files[0])throw Error('اختر ملف CSV أولاً');
 if(file.files[0].size>6*1024*1024)throw Error('الملف كبير');
 const bytes=new Uint8Array(await file.files[0].arrayBuffer());let binary='';
 for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
 const parsed=await request('nova-price-list-parse',{filename:file.files[0].name,content_base64:btoa(binary)});
 const rows=parsed.rows;
 const payload={rows};if(pct.value!=='')payload.markup_percent=pct.value;
 const data=await request('nova-price-list-preview',payload);
 preview=Array.isArray(data.rows)?data.rows:[];grid.replaceChildren();approveBtn.disabled=true;
 const table=el('table');table.style.width='100%';
 const tr=el('tr');['اعتماد','الصنف','الحالة','سعر الشراء الجديد','سعر البيع السابق','سعر البيع المقترح'].forEach(h=>tr.append(el('th',h)));table.append(tr);
 preview.forEach(r=>{const line=el('tr');const td=el('td');const cb=el('input');cb.type='checkbox';cb.checked=!!r.selected;cb.disabled=r.status!=='matched';r._checkbox=cb;cb.onchange=()=>{approveBtn.disabled=!preview.some(item=>item.status==='matched'&&item._checkbox?.checked)};td.append(cb);line.append(td);
 [r.name,r.status,r.purchase_price,r.old_sale_price??'-',r.proposed_sale_price??'-'].forEach(v=>line.append(el('td',String(v))));table.append(line)});
 grid.append(table);approveBtn.disabled=!preview.some(item=>item.status==='matched'&&item._checkbox?.checked);status.textContent='المعاينة فقط؛ لم يتم تعديل أي سعر.';
 }catch(e){preview=[];approveBtn.disabled=true;status.textContent=e.message}};
approveBtn.onclick=async()=>{try{
 const items=preview.filter(r=>r._checkbox?.checked&&r.status==='matched').map(r=>({package_id:r.package_id,old_sale_price:r.old_sale_price,proposed_sale_price:r.proposed_sale_price,approval_token:r.approval_token}));
 if(!items.length)throw Error('حدد صنفاً واحداً على الأقل');
 if(!confirm('اعتماد '+items.length+' سعر بيع؟'))return;
 const data=await request('nova-price-list-approve',{items});status.textContent='تم اعتماد '+data.updated+' سعر. راجع السجل للتراجع.';approveBtn.disabled=true;
 }catch(e){status.textContent=e.message}};
historyBtn.onclick=async()=>{try{
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
  launch.onclick=()=>panel.hidden=false;
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