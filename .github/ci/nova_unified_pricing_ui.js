/* NOVA pharmacy unified selling price editor.
   All writers use the same local server ledger; no product-only scalar price.
   No automatic source DB edits until a human confirms the full preview. */
(()=>{'use strict';
const el=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);return e};
const money=v=>Number(v||0).toLocaleString('en-US')+' ج.س';
const request=async(path,body)=>{
 const response=await fetch('/api/v1/'+path,{credentials:'same-origin',
   method:body===undefined?'GET':'POST',
   headers:{'Content-Type':'application/json'},
   body:body===undefined?undefined:JSON.stringify(body)});
 const payload=await response.json().catch(()=>({error:'تعذر قراءة استجابة النظام'}));
 if(!response.ok||payload.error)throw Error(payload.error||'فشلت العملية');
 return payload;
};
const panel=el('section');
panel.id='nova-unified-prices';
panel.hidden=true;
panel.style.cssText='position:fixed;inset:3% 5%;z-index:10020;direction:rtl;overflow:auto;background:#fff;color:#123c46;border-radius:18px;padding:20px;border:1px solid #bcd8db;box-shadow:0 18px 65px #0008';
const head=el('div');head.style.cssText='display:flex;justify-content:space-between;align-items:center;gap:8px';
head.append(el('h2','إدارة أسعار البيع الموحدة'));
const close=el('button','إغلاق');close.type='button';close.className='btn outline';head.append(close);panel.append(head);
const intro=el('p','ابحث عن الدواء، وستظهر كل تعبئاته معًا. عند الربط، تعديل سعر العلبة يحسب الشريط والعكس. ويمكن اختيار سعر مستقل صراحةً. تظهر معاينة قبل الحفظ.');
panel.append(intro);
const search=el('input');search.type='search';search.placeholder='بحث بالاسم، التركيز أو باركود أي تعبئة';search.style.cssText='padding:12px;width:100%;max-width:650px;border:1px solid #bad1d5;border-radius:10px;margin:12px 0';
search.setAttribute('aria-label','بحث أسعار الأصناف');panel.append(search);
const status=el('p','ادخل حرفين للبحث');status.setAttribute('role','status');panel.append(status);
const historyBtn=el('button','سجل جميع تغييرات الأسعار');historyBtn.type='button';historyBtn.className='btn outline small';
panel.append(historyBtn);
const list=el('div');list.style.cssText='display:grid;gap:12px;margin:14px 0';panel.append(list);
let version=0,delay,pending=false;
function inputFor(pack){
 const line=el('label');line.style.cssText='display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:7px;border-bottom:1px solid #e5eff0';
 const description=el('span',pack.unit_name+' × '+pack.factor+' · '+(pack.barcode||'بدون باركود'));line.append(description);
 const input=el('input');input.type='number';input.min='1';input.step='1';input.value=pack.sale_price;
 input.style.cssText='padding:8px;border:1px solid #bcd5d8;border-radius:8px;max-width:180px;min-width:120px';
 line.append(input);return {line,input};
}
function showProduct(packs){
 const product=packs[0],saved=new Map(packs.map(p=>[String(p.package_id),Number(p.sale_price)]));
 const card=el('article');card.style.cssText='border:1px solid #d3e6e8;border-radius:12px;padding:14px';
 card.append(el('strong',product.name+' · '+(product.strength||'')));
 const modeLabel=el('label',' سياسة التسعير: ');
 const mode=el('select');
 for(const [value,title] of [['linked','ربط العلبة والشريط تلقائيًا'],['independent','أسعار مستقلة — تحديد يدوي']]){
   const option=el('option',title);option.value=value;mode.append(option);
 }
 mode.style.cssText='display:block;max-width:100%;padding:8px;margin:7px 0;border-radius:8px';
 modeLabel.append(mode);card.append(modeLabel);
 const priceBox=el('div');card.append(priceBox);
 const controls=new Map();
 for(const pack of packs){
   const {line,input}=inputFor(pack);priceBox.append(line);
   controls.set(String(pack.package_id),input);
 }
 let source=null;
 const note=el('p','عند الربط، تغيير أي تعبئة سيحسب بقية الأسعار حسب معاملات التحويل المعتمدة.');
 note.style.cssText='font-size:13px;color:#456c70';card.append(note);
 const preview=el('p','');preview.style.cssText='font-weight:600';card.append(preview);
 const save=el('button','معاينة واعتماد أسعار الصنف');save.type='button';save.className='btn';
 card.append(save);
 function calculate(key){
   const anchor=packs.find(p=>String(p.package_id)===String(key));
   if(!anchor)return;
   const value=Number(controls.get(String(key)).value);
   if(!Number.isSafeInteger(value)||value<=0)return;
   source=key;
   if(mode.value==='linked'){
     for(const pack of packs){
       const projected=Math.max(1,Math.round(value*Number(pack.factor)/Number(anchor.factor)));
       if(String(pack.package_id)!==String(key))controls.get(String(pack.package_id)).value=String(projected);
     }
   }
   displayPreview();
 }
 function displayPreview(){
   let changes=[];
   for(const pack of packs){
     const value=Number(controls.get(String(pack.package_id)).value);
     if(value!==Number(pack.sale_price))changes.push(pack.unit_name+': '+money(pack.sale_price)+' ← '+money(value));
   }
   preview.textContent=changes.length?changes.join(' | '):'لا يوجد اختلاف عن الأسعار المحفوظة';
 }
 for(const pack of packs){
   controls.get(String(pack.package_id)).addEventListener('input',()=>calculate(String(pack.package_id)));
 }
 mode.addEventListener('change',()=>{source=null;
   for(const pack of packs)controls.get(String(pack.package_id)).value=String(pack.sale_price);
   displayPreview();
 });
 displayPreview();
 save.onclick=async()=>{
   if(pending)return;
   const snapshot=Object.fromEntries(packs.map(pk=>[String(pk.package_id),saved.get(String(pk.package_id))]));
   const changed=packs.filter(pk=>Number(controls.get(String(pk.package_id)).value)!==Number(pk.sale_price));
   if(!changed.length){status.textContent='لا توجد أسعار متغيرة';return}
   for(const pk of packs){
     const value=Number(controls.get(String(pk.package_id)).value);
     if(!Number.isSafeInteger(value)||value<=0||value>1000000000000){
       status.textContent='راجع الأسعار؛ يجب إدخال أرقام موجبة صحيحة';return;
     }
   }
   if(mode.value==='linked' && source===null){
     status.textContent='غيّر سعر إحدى التعبئات لتحديد سعر الأساس';return;
   }
   const proposals=(mode.value==='linked'?[packs.find(x=>String(x.package_id)===String(source))]:changed).map(pk=>({
     package_id:Number(pk.package_id),
     old_sale_price:Number(pk.sale_price),
     price:Number(controls.get(String(pk.package_id)).value),
     mode:mode.value,
     expected_related:snapshot
   }));
   const text=changed.map(pk=>pk.unit_name+': '+money(pk.sale_price)+' ← '+money(controls.get(String(pk.package_id)).value)).join('\n');
   if(!confirm('اعتماد أسعار بيع '+product.name+'؟\n\n'+text+'\n\nالتغيير لا يؤثر في الفواتير السابقة.'))return;
   pending=true;save.disabled=true;close.disabled=true;status.textContent='جارٍ الحفظ في قاعدة البيانات...';
   try{
     const result=await request('nova-unified-prices',{items:proposals});
     if(typeof refresh==='function')await refresh();
     if(typeof redraw==='function')redraw();
     status.textContent='تم تحديث '+result.updated+' سعر بنجاح. كل الشاشات ستقرأ السعر الجديد.';
     await doSearch();
   }catch(e){status.textContent=e.message}
   finally{pending=false;save.disabled=false;close.disabled=false}
 };
 return card;
}
async function doSearch(){
 const v=++version,q=search.value.trim();list.replaceChildren();
 if(q.length<2){status.textContent='اكتب حرفين أو أكثر للبحث';return}
 status.textContent='جارٍ جلب الأسعار المعتمدة من قاعدة البيانات...';
 try{
   const data=await request('nova-sale-price-catalog?q='+encodeURIComponent(q));
   if(v!==version)return;
   const groups=new Map();
   for(const p of data.rows||[]){
     if(!groups.has(String(p.product_id)))groups.set(String(p.product_id),[]);
     groups.get(String(p.product_id)).push(p);
   }
   status.textContent=groups.size+' صنف (كل تعبئاته ظاهرة)';
   for(const packs of groups.values())list.append(showProduct(packs));
 }catch(e){if(v===version)status.textContent=e.message}
}
search.addEventListener('input',()=>{clearTimeout(delay);delay=setTimeout(doSearch,220)});
close.onclick=()=>{if(pending)return;panel.hidden=true;version++};
historyBtn.onclick=async()=>{
 if(pending)return;const v=++version;list.replaceChildren();status.textContent='جارٍ تحميل سجل جميع تعديلات الأسعار...';
 try{
   const d=await request('nova-manual-price-history');
   if(v!==version)return;
   const entries=d.rows||[];status.textContent=entries.length+' تغيير مسجل';
   for(const r of entries){
     const item=el('div','#'+r.id+' · '+r.created_at+' · '+r.action+' · عبوة '+(r.package_id||'—')+
       ' · '+money(r.old)+' ← '+money(r.new));
     item.style.cssText='padding:9px;border-bottom:1px solid #dbe9ec';list.append(item);
   }
 }catch(e){if(v===version)status.textContent=e.message}
};
function open(packageId){
 if(typeof packageId==='number'){
   const pack=skuPack(packageId);
   if(pack)search.value=pack.product.name;
 }
 panel.hidden=false;search.focus();if(search.value.trim().length>=2)doSearch();
}
window.novaOpenUnifiedPrices=open;

// Old medicine catalogue's mixed price/barcode modal is separated.
// Barcode edits cannot write the sale_price column, even with stale UI state.
window.novaSaveBarcodeOnly=async id=>{
 const btn=document.getElementById('nova-only-barcode-save');
 if(btn)btn.disabled=true;
 try{
   await request('package',{package_id:id,barcode:v('edit-pk-barcode')});
   closeModal();
   if(typeof refresh==='function')await refresh();
   if(typeof redraw==='function')redraw();
   if(typeof toast==='function')toast('تم حفظ الباركود دون تغيير أسعار البيع');
 }catch(e){if(typeof toast==='function')toast(e.message,true)}
 finally{if(btn)btn.disabled=false}
};
editPackageModal=function(id){
 const pack=skuPack(id);
 if(!pack)return;
 const head=el('div');
 const barcode=f('باركود العبوة','edit-pk-barcode','text',pack.barcode||'');
 const info='<div class="help">السعر الحالي: '+money(pack.sale_price)+
  ' · أسعار العلبة والشريط تُدار من شاشة الأسعار الموحدة. حفظ الباركود لا يغير السعر.</div>';
 const buttons='<div class="actions section"><button id="nova-only-barcode-save" class="btn" onclick="novaSaveBarcodeOnly('+Number(id)+')">حفظ الباركود فقط</button>'+
   '<button class="btn outline" onclick="closeModal();novaOpenUnifiedPrices('+Number(id)+')">تعديل أسعار جميع التعبئات</button></div>';
 modal('باركود عبوة · '+pack.product.name,barcode+info+buttons);
};
document.addEventListener('DOMContentLoaded',()=>{
 document.body.append(panel);
 const launch=el('button','إدارة أسعار البيع الموحدة');
 launch.type='button';launch.className='btn outline small';launch.onclick=open;
 const previousNav=nav;
 nav=function(page){
   previousNav(page);
   launch.remove();
   if(!['stock','inventory','prices','pricing','products','catalog'].includes(page))return;
   const root=document.querySelector('main')||document.querySelector('#app');
   const target=root?.querySelector('.panel-head')||root?.querySelector('.panel')||root;
   if(target)target.prepend(launch);
 };
 const active=document.querySelector('[data-page].active');
 if(active)nav(active.getAttribute('data-page'));

 // LAN multi-user: check the central server's last approved price revision.
 // Refresh only on a revision change; preserve open sale rows, draft quantities
 // and purchase inputs. A stale checkout is also rejected by the backend.
 let previousRevision=null,pollBusy=false;
 const checkPriceRevision=async()=>{
   if(pollBusy||pending||document.hidden||typeof state!=='object'||!state.user)return;
   pollBusy=true;
   try{
     const info=await request('nova-price-revision');
     const next=Number(info.revision||0);
     if(previousRevision!==null&&next!==previousRevision){
       const oldPrices=(state.saleRows||[]).map(row=>({
         id:Number(row.package_id),price:skuPack(row.package_id)?.sale_price
       }));
       if(typeof refresh==='function')await refresh();
       const changed=oldPrices.some(p=>skuPack(p.id)?.sale_price!==p.price);
       if(typeof redraw==='function')redraw();
       if(changed&&typeof toast==='function')
         toast('تم تحديث سعر دواء في سلة البيع من جهاز آخر؛ راجع الإجمالي قبل الاعتماد',true);
     }
     previousRevision=next;
   }catch(e){/* Account may not have price/sale permissions; checkout still verifies quotes. */}
   finally{pollBusy=false}
 };
 setInterval(checkPriceRevision,15000);
 window.addEventListener('focus',checkPriceRevision);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)checkPriceRevision()});
 checkPriceRevision();
});
})();
