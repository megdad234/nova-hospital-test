'use strict';
// MADAR 1.4 usability layer. Existing transaction API and permissions remain authoritative.
// The purchase API already posts physically received stock atomically when an invoice is saved.
(function(){
  const normalize = value => String(value??'').toLocaleLowerCase().trim().replace(/[أإآ]/g,'ا').replace(/ى/g,'ي').replace(/ة/g,'ه');
  const searchProduct = (p, q) => normalize([p.name,p.generic_name,p.strength,p.sku,p.manufacturer,(p.packages||[]).map(x=>x.barcode).join(' ')].join(' ')).includes(q);
  let purchaseSaving = false;
  let catalogPage = 0;
  let catalogTerm = '';
  let stockTerm = '';
  const PAGE_SIZE = 60;
  const allPacks = () => state.products.filter(p=>p.active).flatMap(p=>p.packages.map(pk=>({product:p,pk,label:p.name+' — '+pk.unit_name+' (×'+pk.factor+')'+(pk.barcode?' · '+pk.barcode:'')})));

  // Find an item in the ready-made dictionary, never auto-select an unrelated medicine.
  filterBuyChoices = function(){
    const select=$('buy-pkg');if(!select)return;
    const q=normalize(v('buy-search'));state.madarBuySearch=v('buy-search');
    const found = q ? allPacks().filter(({product,pk})=>searchProduct(product,q)||normalize(pk.unit_name).includes(q)).slice(0,60) : [];
    select.replaceChildren(new Option(q?'اختر من نتائج البحث':'اكتب اسم الدواء للبحث في الدليل',''));
    for(const x of found)select.add(new Option(x.label,String(x.pk.id)));
    $('buy-count') && ($('buy-count').textContent=q?(found.length?'النتائج: '+found.length+(found.length===60?' (اكتب أكثر للتحديد)':''):'الصنف غير موجود؛ تقدر تضيفه من هنا'):'اكتب جزءاً من الاسم أو التركيز أو الباركود');
    if(found.length===1)select.value=String(found[0].pk.id);
  };

  const oldAddBuyBarcode = addBuyBarcode;
  addBuyBarcode=function(){
    const scan=v('buy-scan').trim();if(!scan)return;
    oldAddBuyBarcode();
    if($('buy-scan')){$('buy-scan').value='';$('buy-scan').focus()}
  };
  window.addBuyFromDictionary=function(){
    const id=Number(v('buy-pkg'));
    if(!id)return toast('ابحث عن اسم الدواء وحدده أولاً، أو اضغط «صنف جديد»',true);
    addBuyRow(id);
    state.madarBuySearch='';
    if($('buy-search')){$('buy-search').value='';$('buy-search').focus();filterBuyChoices()}
  };

  // If a pharmacist buys 66 packs, 66 are received by default, not 1.
  const previousEditBuy=editBuy;
  editBuy=function(i,key,value){
    const row=state.purchaseRows[i];if(!row)return;
    if(key==='received')row.madarManualReceipt=true;
    if(key==='qty'){
      const qty=Number(value);
      const previousQty=Number(row.qty);
      if(!row.madarManualReceipt && Number(row.received)===previousQty && Number.isFinite(qty)) row.received=qty;
    }
    previousEditBuy(i,key,value);
  };
  state.madarPartialPurchase = false;
  window.togglePurchasePartial=function(checked){
    state.madarPartialPurchase=!!checked;
    if(!checked)for(const r of state.purchaseRows){r.received=r.qty;r.madarManualReceipt=false}
    redraw();
  };
  window.togglePurchaseDetails=function(checked){state.madarShowPurchaseDetails=!!checked;redraw()};
  window.togglePurchaseLineDetails=function(index){
    const row=state.purchaseRows[index]; if(!row)return;row.madarShowDetail=!row.madarShowDetail;redraw();
  };

  // A compact buying form. Optional complexity remains accessible, but does not dominate daily operation.
  purchase=function(){
    const total=state.purchaseRows.reduce((acc,row)=>acc+Number(row.qty||0)*Number(row.unit_cost||0)-Number(row.discount||0),0);
    const rows=state.purchaseRows.map((row,i)=>{
      const product=skuPack(row.package_id);const name=product?.product.name||'صنف غير معروف';
      return `<div class="madar-buy-line" data-buy-line="${i}">
        <div class="madar-buy-line-title"><div><strong>${esc(name)}</strong> <span class="muted">${esc(product?.unit_name||'')} ×${product?.factor||1}</span></div><button class="btn danger small" onclick="removeBuy(${i})" aria-label="حذف ${esc(name)}">حذف ×</button></div>
        <div class="madar-buy-line-fields">
          ${f('الكمية المشتراة','buy-qty-'+i,'number',row.qty,`min="1" step="1" onchange="editBuy(${i},'qty',this.value)"`)}
          ${f('سعر شراء الوحدة','buy-cost-'+i,'number',row.unit_cost,`min="0" step="1" onchange="editBuy(${i},'unit_cost',this.value)"`)}
          ${f('تاريخ الصلاحية','buy-exp-'+i,'date',row.expiry,`onchange="editBuy(${i},'expiry',this.value)"`)}
          ${state.madarPartialPurchase?f('المستلم فعلياً','buy-received-'+i,'number',row.received,`min="0" max="${row.qty}" onchange="editBuy(${i},'received',this.value)"`):''}
        </div>
        <div class="madar-buy-line-foot"><span>قيمة السطر: <b>${fmt(Number(row.qty||0)*Number(row.unit_cost||0)-Number(row.discount||0))}</b></span><button class="btn outline small" onclick="togglePurchaseLineDetails(${i})">${row.madarShowDetail?'إخفاء التفاصيل':'بونص / خصم / تشغيلة'}</button></div>
        ${row.madarShowDetail?`<div class="madar-buy-line-fields madar-extras">
          ${f('البونص','buy-bonus-'+i,'number',row.bonus,`min="0" onchange="editBuy(${i},'bonus',this.value)"`)}
          ${f('الخصم بالجنيه','buy-discount-'+i,'number',row.discount,`min="0" onchange="editBuy(${i},'discount',this.value)"`)}
          ${f('رقم التشغيلة (اختياري)','buy-batch-'+i,'text',row.batch,`onchange="editBuy(${i},'batch',this.value)"`)}
        </div>`:''}
      </div>`;
    }).join('');
    return `<div class="madar-purchase-screen">
      <div class="panel"><div class="panel-head"><div><h2>فاتورة مشتريات</h2><p class="muted-note">الصنف والكمية والتكلفة والصلاحية؛ وباقي التفاصيل عند الحاجة.</p></div><button class="btn outline small" onclick="importDialog()">رفع فاتورة Excel</button></div>
        <div class="madar-buy-header">${sel('المورد','buy-supplier',state.suppliers.map(x=>[x.id,x.name]),state.purchaseSupplier,`onchange="state.purchaseSupplier=this.value"`)}${f('تاريخ الفاتورة','buy-date','date',state.purchaseDate,`onchange="state.purchaseDate=this.value"`)}</div><div class="madar-supplier-fast"><button class="btn outline small" onclick="addSupplier()">+ مورد جديد بدون مغادرة الفاتورة</button></div>
        <div class="madar-buy-advanced"><button class="btn outline small" onclick="togglePurchaseDetails(${!state.madarShowPurchaseDetails})">${state.madarShowPurchaseDetails?'إخفاء بيانات الفاتورة':'رقم فاتورة المورد / ملاحظات (اختياري)'}</button>${state.madarShowPurchaseDetails?`<div class="grid2 section">${f('رقم فاتورة المورد (اختياري)','buy-ref','text',state.purchaseRef,`oninput="state.purchaseRef=this.value"`)}${f('ملاحظة','buy-note','text',state.purchaseNote,`oninput="state.purchaseNote=this.value"`)}</div>`:''}</div>
        <div class="madar-purchase-finder"><div class="field"><label for="buy-search">ابحث في دليل الأدوية الجاهز</label><input id="buy-search" autocomplete="off" value="${esc(state.madarBuySearch||'')}" placeholder="الاسم أو التركيز أو المادة الفعالة" oninput="filterBuyChoices()" onkeydown="if(event.key==='Enter'){event.preventDefault();addBuyFromDictionary()}"></div>
          <div class="field"><label for="buy-pkg">نتائج البحث</label><select id="buy-pkg"><option value="">ابحث ثم اختر الصنف</option></select></div>
          <button class="btn" onclick="addBuyFromDictionary()">+ أضف للفاتورة</button><button class="btn outline" onclick="newProduct()">+ صنف جديد</button>
        </div><div id="buy-count" class="muted-note">ابحث عن الدواء في دليل الأصناف</div>
        <div class="field section"><label for="buy-scan">أو امسح الباركود مباشرة</label><input id="buy-scan" placeholder="باركود العلبة / الشريط ثم Enter" autocomplete="off" onkeydown="if(event.key==='Enter'){event.preventDefault();addBuyBarcode()}"></div>
      </div>
      <div class="panel"><div class="panel-head"><h2>الأصناف في الفاتورة <span class="tag">${state.purchaseRows.length} صنف</span></h2><button class="btn outline small" onclick="if(confirm('مسح سطور الفاتورة؟')){state.purchaseRows=[];redraw()}">مسح السطور</button></div>
        <label class="madar-partial-choice"><input type="checkbox" id="purchase-partial" ${state.madarPartialPurchase?'checked':''} onchange="togglePurchasePartial(this.checked)"> استلام جزئي (إذا المورد ما سلّم كل الكمية)</label>
        <div class="help madar-buy-auto-note">${state.madarPartialPurchase?'سيضاف للمخزون المستلم فعلياً فقط؛ الكمية المتبقية تظهر في سجل المشتريات للاستلام لاحقاً.':'✓ الاستلام الكامل تلقائي: بمجرد حفظ الفاتورة ستُضاف كل الكميات للمخزون، بدون خطوة اعتماد أخرى.'}</div>
        <div class="madar-buy-lines">${rows||'<div class="empty">ما في أصناف في الفاتورة. ابحث عن دواء واضغط إضافة.</div>'}</div>
      </div>
      <div class="panel madar-purchase-checkout"><div class="madar-purchase-total"><span>إجمالي المشتريات</span><strong>${fmt(total)}</strong></div>
        <div class="madar-pay-row">${sel('سداد المورد','buy-method',[['credit','آجل'],['cash','كاش'],['bank','تحويل بنكك']],state.purchasePay,`onchange="state.purchasePay=this.value;redraw()"`)}${state.purchasePay==='credit'?'':f('المبلغ المدفوع الآن','buy-paid','number',state.purchasePaid===''?total:state.purchasePaid,'min="0" oninput="state.purchasePaid=this.value"')}${state.purchasePay==='bank'?f('مرجع التحويل','buy-bankref','text',state.purchaseBankRef,`oninput="state.purchaseBankRef=this.value"`):''}</div>
        <div class="actions"><button class="btn madar-submit" id="madar-purchase-submit" ${purchaseSaving?'disabled':''} onclick="confirmPurchase()">✓ حفظ الفاتورة وإضافة الكمية للمخزون</button><button class="btn outline" onclick="openMarkup()" ${state.purchaseRows.length?'':'disabled'}>حساب سعر البيع</button></div>
      </div>
    </div>`;
  };
  // Keep all database writes to the original atomic purchase API; block duplicate clicks.
  confirmPurchase=async function(){
    if(purchaseSaving)return;
    const rows=state.purchaseRows.map(r=>({...r,received:state.madarPartialPurchase?Number(r.received):Number(r.qty)}));
    if(!rows.length)return toast('أضف صنفاً واحداً على الأقل',true);
    for(const r of rows){if(!Number.isSafeInteger(Number(r.qty))||Number(r.qty)<=0)return toast('راجع كمية المشتريات',true);
      if(!state.madarPartialPurchase||Number(r.received)+Number(r.bonus)>0){if(!r.expiry)return toast('أدخل تاريخ الصلاحية للأدوية المستلمة',true)}
    }
    const supplier=Number(v('buy-supplier')||state.purchaseSupplier);
    if(!supplier)return toast('اختر المورد أولاً',true);
    const method=v('buy-method')||state.purchasePay;
    const paid=method==='credit'?0:n('buy-paid');
    const body={supplier_id:supplier,invoice_ref:v('buy-ref')||state.purchaseRef,invoice_date:v('buy-date')||state.purchaseDate,note:v('buy-note')||state.purchaseNote,items:rows,payment_method:method,paid,bank_ref:v('buy-bankref')||state.purchaseBankRef};
    purchaseSaving=true;
    if($('madar-purchase-submit')){$('madar-purchase-submit').disabled=true;$('madar-purchase-submit').textContent='جارٍ الحفظ...'}
    try{
      const r=await api('purchase',body);
      state.purchaseRows=[];state.purchaseRef='';state.purchaseNote='';state.purchaseDate=today();state.purchasePaid='';state.purchaseBankRef='';state.madarBuySearch='';state.madarPartialPurchase=false;
      await refresh();nav('purchases');
      toast('✓ تم حفظ الفاتورة '+r.id+' وترحيل المستلم للمخزون مباشرة');
    }catch(e){toast(e.message,true)}
    finally{purchaseSaving=false;if($('madar-purchase-submit'))$('madar-purchase-submit').disabled=false}
  };

  // A fast medication index even with 1,800+ preloaded items; avoids rendering every row at once.
  catalog=function(){return `<div class="panel"><div class="panel-head"><div><h2>دليل الأدوية والأصناف</h2><p class="muted-note">الأصناف هنا مستقلة عن كميات مخزونك.</p></div><div class="actions"><button class="btn" onclick="newProduct()">+ صنف جديد</button><button class="btn outline" onclick="nav('catalog-upload')">استيراد برايس Excel</button></div></div>
    <div class="madar-catalog-search"><div class="field"><label for="madar-catalog-search">بحث في كل الأصناف</label><input id="madar-catalog-search" value="${esc(catalogTerm)}" placeholder="الاسم / المادة الفعالة / التركيز / الكود / الباركود" oninput="madarFilterCatalog(this.value)"></div><span id="madar-catalog-count" class="tag"></span></div>
    <div id="madar-catalog-result"></div><div id="madar-catalog-pages" class="actions section"></div>
    </div>`};
  window.madarFilterCatalog=function(term){catalogTerm=term;catalogPage=0;renderCatalogPage()};
  window.madarCatalogPage=function(step){catalogPage+=step;renderCatalogPage()};
  function renderCatalogPage(){const result=$('madar-catalog-result');if(!result)return;
    const query=normalize(catalogTerm);
    const found=state.products.filter(p=>!query||searchProduct(p,query));
    const pages=Math.max(1,Math.ceil(found.length/PAGE_SIZE));catalogPage=Math.max(0,Math.min(catalogPage,pages-1));
    const slice=found.slice(catalogPage*PAGE_SIZE,(catalogPage+1)*PAGE_SIZE);
    $('madar-catalog-count').textContent=found.length+' صنف';
    result.innerHTML=table(['الصنف','التركيز / المادة','الرصيد','العبوات والأسعار','الإجراءات'],slice.map(p=>`<tr><td><strong>${esc(p.name)}</strong><div class="muted">${esc(p.sku)}</div></td><td>${esc([p.strength,p.generic_name].filter(Boolean).join(' / ')||'—')}</td><td>${Number(p.available)||0} ${esc(p.base_uom)}</td><td>${p.packages.map(pk=>`<div class="madar-catalog-package">${esc(pk.unit_name)} ×${pk.factor} — ${fmt(pk.sale_price)} <button class="btn outline small" onclick="editPackageModal(${pk.id})">السعر/الباركود</button></div>`).join('')}</td><td><button class="btn outline small" onclick="editProductModal(${p.id})">تعديل</button></td></tr>`));
    $('madar-catalog-pages').innerHTML=`<button class="btn outline small" onclick="madarCatalogPage(-1)" ${catalogPage===0?'disabled':''}>السابق</button><span class="muted-note">صفحة ${catalogPage+1} من ${pages}</span><button class="btn outline small" onclick="madarCatalogPage(1)" ${catalogPage===pages-1?'disabled':''}>التالي</button>`;
  }

  // Search in POS must distinguish zero balance vs missing master item.
  const legacyPkgTile=pkgTile;
  pkgTile=function(p,pk){
    if(pk.sale_price<=0)return `<div class="product-card madar-not-saleable"><span class="tag warn">سعر البيع غير محدد</span><b>${esc(p.name)} · ${esc(pk.unit_name)}</b><small>الصنف مسجل في الدليل</small></div>`;
    return legacyPkgTile(p,pk);
  };
  filterCards=function(){const el=$('sale-tiles');if(!el)return;
    const term=normalize(v('pos-scan'));
    const found=state.products.filter(p=>p.active&&(!term?(p.available>0):searchProduct(p,term))).slice(0,45);
    const list=found.flatMap(p=>p.packages.map(pk=>pkgTile(p,pk))).slice(0,65);
    el.innerHTML=list.join('') || `<div class="empty">${term?'الصنف غير موجود في الدليل. يمكنك إضافته من شاشة الأدوية.':'لا توجد أدوية برصيد متاح للبيع حالياً.'}</div>`;
    if(term&&found.length&&found.every(p=>p.available<=0))el.insertAdjacentHTML('beforeend','<div class="madar-unavailable-tip">الأصناف دي مسجلة في الدليل، لكن ما عندها رصيد متاح للبيع.</div>');
  };

  // Searchable selection fields on all long lists, including exchanging and stock adjustments.
  function makeLongSelectSearch(root){
    const scope=root||document;
    for(const select of scope.querySelectorAll('select:not([data-madar-search-ready])')){
      select.dataset.madarSearchReady='1';
      if(select.id==='buy-pkg'||select.options.length<18)continue;
      const all=[...select.options].map(o=>({value:o.value,label:o.textContent,disabled:o.disabled}));
      const selected=select.value;
      const input=document.createElement('input');input.type='search';input.className='madar-select-search';input.placeholder='🔎 ابحث لتصفية القائمة ('+all.length+' خيار)';input.setAttribute('aria-label','بحث في '+(select.closest('.field')?.querySelector('label')?.textContent||'القائمة'));
      input.autocomplete='off';select.parentNode.insertBefore(input,select);
      input.addEventListener('input',()=>{
        const term=normalize(input.value);
        const filtered=term?all.filter(o=>normalize(o.label).includes(term)).slice(0,80):all.slice(0,80);
        const prev=select.value;select.replaceChildren(new Option(term?'اختر نتيجة البحث':'— اختر من القائمة —',''));
        for(const item of filtered)select.add(new Option(item.label,item.value,false,false));
        if(filtered.some(x=>x.value===prev))select.value=prev;
        else if(filtered.length===1)select.value=filtered[0].value;
        else select.value='';
      });
      // Keep the active selection visible even if it was beyond first 80 entries.
      const first=all.slice(0,80),active=all.find(x=>x.value===selected);
      select.replaceChildren(new Option('— ابحث أو اختر —',''));
      for(const item of first)select.add(new Option(item.label,item.value));
      if(active&&!first.some(x=>x.value===active.value))select.add(new Option(active.label,active.value));
      select.value=selected;
    }
  }

  // Page-level search for existing lists: invoices, clients, stock movements, suppliers.
  // It only filters what was already loaded from the API, so it never fabricates records.
  function addListFilters(){
    if(state.page==='catalog'||state.page==='pos'||state.page==='purchase')return;
    for(const table of $('content').querySelectorAll('.tablewrap table')){
      if(table.dataset.madarFiltered)return;
      table.dataset.madarFiltered='1';
      const rows=[...table.querySelectorAll('tbody tr')];
      if(rows.length<12)continue;
      const toolbar=document.createElement('div');toolbar.className='madar-list-filter';
      const input=document.createElement('input');input.type='search';input.className='madar-select-search';
      input.placeholder='🔎 بحث سريع في السجلات المعروضة';input.setAttribute('aria-label','تصفية الجدول');
      const counter=document.createElement('span');counter.className='muted-note';counter.textContent=rows.length+' سجل';
      toolbar.append(input,counter);table.closest('.tablewrap').before(toolbar);
      const terms=rows.map(x=>normalize(x.textContent));
      input.addEventListener('input',()=>{const q=normalize(input.value);let displayed=0;
        rows.forEach((row,i)=>{const visible=!q||terms[i].includes(q);row.hidden=!visible;displayed+=Number(visible)});
        counter.textContent=displayed+' من '+rows.length+' سجل';
      });
    }
  }
  const priorNav=nav;
  nav=function(page){priorNav(page);if(page==='catalog')renderCatalogPage();if(page==='purchase')filterBuyChoices();makeLongSelectSearch($('content'));addListFilters();};
  const priorModal=modal;
  modal=function(title,body){priorModal(title,body);makeLongSelectSearch($('modal-body'));};

  // Dynamically inserted lists (file previews / asynchronously fetched finance results).
  let enhancementPending=false;
  const enhanceObserver=new MutationObserver(()=>{
    if(enhancementPending)return;
    enhancementPending=true;
    requestAnimationFrame(()=>{enhancementPending=false;
      makeLongSelectSearch($('content'));makeLongSelectSearch($('modal-body'));addListFilters();
    });
  });
  enhanceObserver.observe($('content'),{subtree:true,childList:true});
  enhanceObserver.observe($('modal-body'),{subtree:true,childList:true});

  // Newly added catalog entries are not sellable until stock and sale price are known.
  // Preserve clear financial and pharmacy boundaries; no fake inventory quantities.
})();
