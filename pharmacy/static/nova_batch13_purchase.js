'use strict';
/* NOVA Batch13: approved premium purchase layout. Keeps legacy transaction routines.
   Search results use stock-first ordering, barcode is optional, and all changes
   to prices/barcodes/unit packages are submitted with the original invoice. */
(function(){
 const clean=x=>esc(String(x??''));
 const num=x=>Number(x);
 const norm=x=>String(x??'').trim().toLocaleLowerCase().replace(/[أإآ]/g,'ا').replace(/ى/g,'ي').replace(/ة/g,'ه');
 const all=()=>state.products.filter(p=>p.active).flatMap(p=>(p.packages||[]).map(pk=>({product:p,pk})));
 const foundPack=id=>{const x=skuPack(Number(id));return x&&x.product?.active!==false?x:null;};
 const current=()=>state.nova13Selected||0;
 const money=x=>fmt(Number(x)||0);
 const priceFor=row=>{
   const explicit=row.nova_manual_sale_price===true?Number(row.nova_sale_price):0;
   return explicit>0?explicit:Number(novaPurchaseSuggestedPrice(row))||0;
 };
 function selectedDetails(){
   const pk=foundPack(current());
   if(!pk)return '<div class="nova13-selection-empty">اختر الدواء من نتائج البحث لإضافة الكمية والباركود.</div>';
   const p=pk.product,entry=state.nova13Entry||{},barcode=entry.barcode===undefined?(pk.barcode||''):entry.barcode;
   const mode=entry.mode||'Package',qty=entry.qty===undefined?1:entry.qty;
   return '<div class="nova13-selected-head"><div><b>'+clean(p.name)+'</b><small>'+clean([p.generic_name,p.strength,p.manufacturer].filter(Boolean).join(' · '))+'</small></div>'+
     '<span class="tag good">'+(Number(p.available)>0?'متوفر بالمخزون':'من دليل الأدوية')+'</span></div>'+
     '<div class="nova13-stockline">الرصيد الحالي: <strong>'+Number(p.available||0)+' '+clean(p.base_uom)+'</strong> · عبوة الشراء: '+clean(pk.unit_name)+'</div>'+
     '<div class="nova13-entry-grid">'+
     '<label class="nova13-field nova13-wide">باركود هذه العبوة (اختياري)<input id="nova13-barcode" type="text" maxlength="80" value="'+clean(barcode)+'" autocomplete="off" placeholder="اضغط هنا وامسح الباركود"></label>'+
     '<div class="nova13-field nova13-wide"><span>طريقة البيع بعد الشراء</span><div class="nova13-unit-toggle">'+
     '<label><input type="radio" name="nova13-mode" value="Package" '+(mode==='Package'?'checked':'')+' onchange="nova13Mode(this.value)"> Package — علبة كاملة</label>'+
     '<label><input type="radio" name="nova13-mode" value="Unit" '+(mode==='Unit'?'checked':'')+' onchange="nova13Mode(this.value)"> Unit — شريط</label></div></div>'+
     (mode==='Unit'?'<label class="nova13-field">عدد الشرائط في العبوة<input id="nova13-strips" type="number" min="2" max="100" step="1" value="'+clean(entry.strips||3)+'"></label>':'')+
     '<label class="nova13-field">الكمية المشتراة<input id="nova13-qty" type="number" min="1" step="1" value="'+clean(qty)+'"></label>'+
     '<label class="nova13-field">سعر شراء '+clean(pk.unit_name)+' (ج.س)<input id="nova13-cost" type="number" min="0" step="1" value="'+clean(entry.cost===undefined?'':entry.cost)+'" placeholder="أدخل التكلفة"></label>'+
     '<label class="nova13-field">تاريخ الصلاحية<input id="nova13-expiry" type="date" value="'+clean(entry.expiry||'')+'"></label></div>'+
     '<div class="nova13-entry-actions"><button type="button" class="btn nova13-add" onclick="nova13AddSelected()">+ إضافة للفاتورة</button>'+
     '<button type="button" class="btn outline" onclick="nova13ShowQuickAdd()">+ صنف جديد</button></div>';
 }
 function totals(){
   const total=state.purchaseRows.reduce((a,r)=>a+Number(r.qty||0)*Number(r.unit_cost||0)-Number(r.discount||0),0);
   return '<div class="nova13-totals"><span>عدد الأصناف <b>'+state.purchaseRows.length+'</b></span><span>إجمالي المشتريات <b>'+money(total)+' ج.س</b></span></div>';
 }
 function line(row,i){
   const pk=foundPack(row.package_id),name=pk?.product?.name||'صنف غير معروف';
   const sale=priceFor(row),sub=Number(row.qty||0)*Number(row.unit_cost||0)-Number(row.discount||0);
   const unitCount=Number(row.nova13_unit_count||0);
   let unitInfo='';
   if(unitCount>1){
     const per=row.nova13_unit_manual?Number(row.nova13_unit_sale_price):Math.round(sale/unitCount);
     unitInfo='<div class="nova13-subprice"><span>سعر الشريط المحسوب: '+money(per)+' ج.س</span>'+
       '<label>تعديل سعر الشريط <input type="number" min="1" step="1" value="'+clean(per||'')+
       '" onchange="nova13SetUnitPrice('+i+',this.value)"></label></div>';
   }
   return '<tr class="nova13-row"><td><strong>'+clean(name)+'</strong><small>'+clean(pk?.unit_name||'')+
     (unitCount>1?' · Unit ('+unitCount+' شرائط)':' · Package')+'</small>'+
     '<button type="button" class="nova13-detail-button" onclick="togglePurchaseLineDetails('+i+')">'+(row.madarShowDetail?'إخفاء التفاصيل':'تفاصيل')+'</button></td>'+
     '<td><input type="number" min="1" step="1" value="'+clean(row.qty)+'" onchange="editBuy('+i+',\'qty\',this.value)"></td>'+
     '<td><input type="number" min="0" step="1" value="'+clean(row.unit_cost)+'" onchange="editBuy('+i+',\'unit_cost\',this.value)"></td>'+
     '<td><input type="number" min="1" step="1" value="'+clean(sale||'')+'" onchange="nova13SetPrice('+i+',this.value)">'+unitInfo+'</td>'+
     '<td class="nova13-money">'+money(sub)+'</td><td><button type="button" class="nova13-delete" onclick="removeBuy('+i+')" aria-label="حذف السطر">×</button></td></tr>'+
     '<tr class="nova13-subrow"><td colspan="6"><div class="nova13-row-details">'+
     '<label>الصلاحية <input type="date" value="'+clean(row.expiry||'')+'" onchange="editBuy('+i+',\'expiry\',this.value)"></label>'+
     (state.madarPartialPurchase?'<label>المستلم فعلياً <input type="number" min="0" max="'+clean(row.qty)+'" value="'+clean(row.received)+'" onchange="editBuy('+i+',\'received\',this.value)"></label>':'')+
     (row.madarShowDetail?'<label>بونص <input type="number" min="0" value="'+clean(row.bonus)+'" onchange="editBuy('+i+',\'bonus\',this.value)"></label>'+
       '<label>خصم السطر <input type="number" min="0" value="'+clean(row.discount)+'" onchange="editBuy('+i+',\'discount\',this.value)"></label>'+
       '<label>رقم التشغيلة <input type="text" value="'+clean(row.batch||'')+'" onchange="editBuy('+i+',\'batch\',this.value)"></label>':'')+
     '</div></td></tr>';
 }
 purchase=function(){
   const rows=state.purchaseRows.map(line).join('');
   const dateValue=state.purchaseDate||today();
   return '<div class="nova13-purchase">'+
     '<div class="panel nova13-header"><div class="madar-buy-header">'+
       sel('المورد','buy-supplier',state.suppliers.map(x=>[x.id,x.name]),state.purchaseSupplier,'onchange="state.purchaseSupplier=this.value"')+
       f('التاريخ','buy-date','date',dateValue,'onchange="state.purchaseDate=this.value"')+
       f('رقم فاتورة المورد (اختياري)','buy-ref','text',state.purchaseRef||'','oninput="state.purchaseRef=this.value"')+
       '</div><button type="button" class="btn outline small" onclick="addSupplier()">+ مورد جديد</button></div>'+
     '<div class="nova13-columns">'+
     '<section class="panel nova13-invoice"><div class="panel-head"><h2>أصناف الفاتورة <span class="tag">'+state.purchaseRows.length+'</span></h2>'+
       '<button type="button" class="btn outline small" onclick="if(confirm(\'حذف سطور الفاتورة؟\')){state.purchaseRows=[];redraw()}">مسح السطور</button></div>'+
       '<div class="nova13-table-scroll"><table><thead><tr><th>اسم الدواء</th><th>الكمية</th><th>سعر الشراء</th><th>سعر البيع</th><th>الإجمالي</th><th></th></tr></thead>'+
       '<tbody>'+rows+'</tbody></table>'+(rows?'':'<div class="empty">ابحث عن دواء في الجهة اليمنى وأضفه للفاتورة.</div>')+'</div>'+
       '<div class="nova13-options-slot"></div>'+
       '<details class="nova13-more"><summary>خيارات الفاتورة والاستلام والدفع</summary>'+
         '<div class="nova13-more-fields">'+
           '<label class="nova13-check"><input type="checkbox" '+(state.madarPartialPurchase?'checked':'')+' onchange="togglePurchasePartial(this.checked)"> استلام جزئي</label>'+
           f('ملاحظات الفاتورة','buy-note','text',state.purchaseNote||'','oninput="state.purchaseNote=this.value"')+
           sel('طريقة السداد','buy-method',[['credit','آجل'],['cash','كاش'],['bank','بنكي']],state.purchasePay,'onchange="state.purchasePay=this.value;redraw()"')+
           (state.purchasePay==='credit'?'':f('المدفوع الآن','buy-paid','number',state.purchasePaid,'min="0" oninput="state.purchasePaid=this.value"'))+
           (state.purchasePay==='bank'?f('رقم العملية البنكية','buy-bankref','text',state.purchaseBankRef,'oninput="state.purchaseBankRef=this.value"'):'')+
         '</div></details>'+
       totals()+
     '</section>'+
     '<section class="panel nova13-finder"><div class="panel-head"><h2>البحث وإضافة صنف</h2><button type="button" class="btn outline small" onclick="nova13ShowQuickAdd()">+ صنف جديد</button></div>'+
       '<div class="nova13-search"><input type="search" id="buy-search" value="'+clean(state.madarBuySearch||'')+
       '" placeholder="ابحث بالاسم أو امسح الباركود..." autocomplete="off" oninput="filterBuyChoices()"'+
       ' onkeydown="if(event.key===\'Enter\'){event.preventDefault();nova13ChooseFirst()}"><span>⌕</span></div>'+
       '<select id="buy-pkg" hidden aria-label="الصنف المختار"></select>'+
       '<div id="buy-count" class="muted-note">البحث واحد: الموجود بالمخزون أولاً ثم دليل الأدوية.</div>'+
       '<div id="buy-suggestions" class="nova13-results"></div>'+
       '<div id="nova13-selected" class="nova13-selected">'+selectedDetails()+'</div>'+
       '<div id="nova13-quick-form" class="nova13-quick" hidden></div>'+
     '</section></div>'+
     '<div class="panel nova13-footer"><div class="nova13-footer-actions">'+
       '<button type="button" class="btn" id="madar-purchase-submit" onclick="confirmPurchase()">✓ اعتماد واستلام الفاتورة</button>'+
       '<button type="button" class="btn outline" onclick="novaSavePurchaseDraft()">حفظ كمسودة</button>'+
       '<button type="button" class="btn outline" onclick="importDialog()">استيراد Excel</button>'+
       '<button type="button" class="btn outline" onclick="nav(\'purchases\')">سجل المشتريات</button>'+
       '<button type="button" class="btn outline" onclick="nav(\'purchase-returns\')">مرتجع مشتريات</button>'+
       '</div></div></div>';
 };
 window.nova13SetPrice=function(i,value){
   const row=state.purchaseRows[i],n=Number(value);
   if(!row||!Number.isSafeInteger(n)||n<=0)return toast('سعر البيع يجب أن يكون موجباً بالجنيه الصحيح',true);
   row.nova_sale_price=n;row.nova_manual_sale_price=true;redraw();
 };
 window.nova13SetUnitPrice=function(i,value){
   const row=state.purchaseRows[i],n=Number(value);
   if(!row||!Number.isSafeInteger(n)||n<=0)return toast('سعر الشريط يجب أن يكون موجباً بالجنيه الصحيح',true);
   row.nova13_unit_sale_price=n;row.nova13_unit_manual=true;redraw();
 };
 window.nova13UnitRules=function(rows){
   return rows.filter(r=>Number(r.nova13_unit_count)>1).map(r=>{
     const count=Number(r.nova13_unit_count),packPrice=priceFor(r);
     const unitPrice=r.nova13_unit_manual?Number(r.nova13_unit_sale_price):Math.round(packPrice/count);
     if(!Number.isSafeInteger(count)||count<2||count>100||!Number.isSafeInteger(unitPrice)||unitPrice<1)
       throw Error('راجع عدد الشرائط وسعر الشريط قبل اعتماد المشتريات');
     return {package_id:Number(r.package_id),strips:count,unit_price:unitPrice};
   });
 };
 window.nova13Barcodes=function(rows){
   return rows.filter(r=>r.nova13_barcode_dirty===true).map(r=>({
     package_id:Number(r.package_id),barcode:String(r.nova13_barcode||'').trim()
   }));
 };
 window.nova13Mode=function(mode){
   const prev=state.nova13Entry||{};
   prev.barcode=$('nova13-barcode')?.value??prev.barcode;
   prev.qty=$('nova13-qty')?.value??prev.qty;
   prev.cost=$('nova13-cost')?.value??prev.cost;
   prev.expiry=$('nova13-expiry')?.value??prev.expiry;
   prev.mode=mode==='Unit'?'Unit':'Package';
   state.nova13Entry=prev;
   $('nova13-selected').innerHTML=selectedDetails();
 };
 window.nova13SelectPack=function(id){
   const pk=foundPack(id);
   if(!pk)return toast('العبوة غير متاحة',true);
   state.nova13Selected=Number(id);
   state.nova13Entry={barcode:pk.barcode||'',mode:'Package',qty:1,cost:'',expiry:''};
   $('buy-pkg').value=String(id);
   $('nova13-selected').innerHTML=selectedDetails();
 };
 window.nova13ChooseFirst=function(){
   const first=$('buy-suggestions')?.querySelector('[data-nova13-choice]');
   if(first)nova13SelectPack(Number(first.dataset.nova13Choice));
 };
 filterBuyChoices=function(){
   const el=$('buy-suggestions');if(!el)return;
   const query=norm(v('buy-search')),sel=$('buy-pkg');state.madarBuySearch=v('buy-search');
   if(!query){el.innerHTML='';$('buy-count').textContent='ابدأ بالاسم أو الباركود؛ نتائج المخزون أولاً.';return}
   const matches=all().filter(({product:p,pk})=>{
     return norm([p.name,p.generic_name,p.strength,p.sku,p.manufacturer,pk.barcode,pk.unit_name].join(' ')).includes(query);
   }).sort((a,b)=>{
     const ae=norm(a.pk.barcode)===query?1:0,be=norm(b.pk.barcode)===query?1:0;
     if(ae!==be)return be-ae;
     return (Number(b.product.available)>0?1:0)-(Number(a.product.available)>0?1:0);
   }).slice(0,45);
   el.innerHTML=matches.map(({product:p,pk})=>'<button type="button" class="nova13-hit" data-nova13-choice="'+pk.id+
     '" onclick="nova13SelectPack('+pk.id+')"><span><strong>'+clean(p.name)+'</strong><small>'+
     clean([p.strength,p.generic_name,pk.unit_name,pk.barcode].filter(Boolean).join(' · '))+
     '</small></span><span class="tag '+(Number(p.available)>0?'good':'')+'">'+(Number(p.available)>0?'في المخزون':'في الدليل')+'</span></button>').join('');
   sel.replaceChildren(new Option('اختر الصنف',''));
   matches.forEach(({product:p,pk})=>sel.add(new Option(p.name,String(pk.id))));
   $('buy-count').textContent=matches.length?matches.length+' نتيجة — الأولوية لأصناف المخزون':'لم يتم العثور على الصنف؛ يمكنك إضافته هنا.';
   if(!matches.length)$('nova13-quick-form').hidden=false,nova13ShowQuickAdd(false);
 };
 window.nova13AddSelected=function(){
   const pk=foundPack(current());
   if(!pk)return toast('اختر صنفاً أولاً',true);
   const qty=Number(v('nova13-qty')),cost=Number(v('nova13-cost')),expiry=v('nova13-expiry');
   const mode=document.querySelector('input[name="nova13-mode"]:checked')?.value||'Package';
   const strips=mode==='Unit'?Number(v('nova13-strips')):0;
   const barcode=String(v('nova13-barcode')||'').trim();
   if(!Number.isSafeInteger(qty)||qty<1) return toast('أدخل كمية شراء صحيحة',true);
   if(!Number.isSafeInteger(cost)||cost<0) return toast('أدخل سعر شراء صحيح',true);
   if(!/^\d{4}-\d{2}-\d{2}$/.test(expiry))return toast('حدد تاريخ صلاحية صحيح',true);
   if(mode==='Unit'&&(!Number.isSafeInteger(strips)||strips<2||strips>100))
     return toast('أدخل عدد الشرائط الصحيح',true);
   if(mode==='Unit'&&(!Number.isInteger(Number(pk.factor)/strips)))
     return toast('التعبئة المسجلة لهذا الصنف لا تقبل القسمة على عدد الشرائط؛ صححها من إدارة العبوات قبل الاستلام',true);
   if(barcode&&state.products.some(p=>p.packages.some(b=>b.barcode===barcode&&Number(b.id)!==Number(pk.id))))
     return toast('الباركود مسجل بالفعل لعبوة أخرى؛ لا يمكن تكراره',true);
   if(barcode!==String(pk.barcode||'')&&pk.barcode&&!confirm('تغيير الباركود المسجل لهذه العبوة؟'))return;
   addBuyRow(Number(pk.id));
   const row=state.purchaseRows[state.purchaseRows.length-1];
   if(!row)return toast('تعذر إضافة الدواء',true);
   row.qty=qty;row.received=qty;row.unit_cost=cost;row.expiry=expiry;
   row.nova13_unit_count=mode==='Unit'?strips:0;
   row.nova13_barcode=barcode;row.nova13_barcode_dirty=barcode!==String(pk.barcode||'');
   row.nova_manual_sale_price=false;
   if(state.nova13Entry)state.nova13Entry.qty=1;
   state.madarBuySearch='';
   redraw();
 };
 window.nova13ShowQuickAdd=function(open=true){
   const host=$('nova13-quick-form');if(!host)return;
   host.hidden=!open;
   if(!open)return;
   host.innerHTML='<div class="nova13-quick-head"><b>إضافة صنف جديد داخل الفاتورة</b><button type="button" class="btn outline small" onclick="document.getElementById(\'nova13-quick-form\').hidden=true">إغلاق</button></div>'+
     '<div class="nova13-entry-grid">'+
       '<label class="nova13-field">الاسم التجاري *<input id="nova13-new-name" maxlength="140" value="'+clean(v('buy-search'))+'"></label>'+
       '<label class="nova13-field">الاسم العلمي<input id="nova13-new-generic" maxlength="160"></label>'+
       '<label class="nova13-field">التركيز<input id="nova13-new-strength" maxlength="80"></label>'+
       '<label class="nova13-field">الشركة المصنعة<input id="nova13-new-maker" maxlength="160"></label>'+
       '<label class="nova13-field">الباركود (اختياري)<input id="nova13-new-barcode" maxlength="80"></label>'+
       '<label class="nova13-field">عدد الشرائط في العلبة (اختياري)<input id="nova13-new-strips" type="number" min="2" max="100" placeholder="إذا سيباع بالشريط"></label>'+
     '</div><button type="button" class="btn section" onclick="nova13CreateQuick()">حفظ الصنف واختياره</button>';
 };
 window.nova13CreateQuick=async function(){
   const name=String(v('nova13-new-name')||'').trim(),strips=String(v('nova13-new-strips')||'').trim();
   if(!name)return toast('اكتب الاسم التجاري',true);
   const payload={name,generic_name:v('nova13-new-generic'),strength:v('nova13-new-strength'),
     manufacturer:v('nova13-new-maker'),barcode:v('nova13-new-barcode'),strips:strips||null};
   try{
     const result=await api('nova-purchase-quick-product',payload);
     await refresh();
     state.nova13Selected=Number(result.package_id);
     state.nova13Entry={barcode:payload.barcode||'',mode:strips?'Unit':'Package',strips:strips||3,qty:1,cost:'',expiry:''};
     state.madarBuySearch=name;
     nav('purchase');
     toast('تمت إضافة الصنف إلى الدليل؛ أدخل الكمية والسعر والصلاحية لإضافته للفاتورة');
   }catch(e){toast('تعذر إضافة الصنف: '+e.message,true)}
 };
 const oldNav=nav;
 nav=function(page){
   oldNav(page);
   if(page!=='purchase')return;
   const controls=document.querySelector('.nova-purchase-controls');
   const slot=document.querySelector('.nova13-options-slot');
   if(controls&&slot)slot.appendChild(controls);
   filterBuyChoices();
 };
})();
