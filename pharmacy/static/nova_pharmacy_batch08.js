'use strict';
/* NOVA Batch08 — additive pharmacy improvements.
   Preserves the existing purchase screen, pay flows, imports and receipts.
   No browser-local database. Every draft is stored on the central server. */

(function(){
  const toMoney=n=>Number.isFinite(Number(n))?fmt(Math.round(Number(n))):'0';
  const textSafe=x=>esc(String(x??''));
  const maxMargin=1000;
  if(!Number.isFinite(Number(state.novaPurchaseMarkup)))state.novaPurchaseMarkup=0;

  window.novaPurchaseSuggestedPrice=function(row){
    if(row.nova_manual_sale_price===true&&Number.isSafeInteger(Number(row.nova_sale_price))&&Number(row.nova_sale_price)>0){
      return Number(row.nova_sale_price);
    }
    const pk=skuPack(row.package_id);
    const qty=Math.max(1,Number(row.qty)||1);
    const bonus=Math.max(0,Number(row.bonus)||0);
    const discount=Math.max(0,Number(row.discount)||0);
    const original=Math.max(0,Number(row.unit_cost)||0);
    // Estimate average acquisition cost per package, factoring in free bonus/discount.
    const avgCost=Math.max(0,(qty*original-discount)/(qty+bonus));
    const percent=Math.min(maxMargin,Math.max(0,Number(state.novaPurchaseMarkup)||0));
    let price=Math.round(avgCost*(1+percent/100));
    if(price<=0&&pk&&Number(pk.sale_price)>0)price=Number(pk.sale_price);
    return Math.max(0,price);
  };
  window.novaPurchasePricePayload=function(rows){
    return rows.map((row,i)=>{
      const price=novaPurchaseSuggestedPrice(row);
      if(!Number.isSafeInteger(price)||price<1){
        throw Error('سعر البيع غير محدد للصنف رقم '+(i+1)+'؛ أدخل سعر الشراء أو سعر البيع قبل الحفظ');
      }
      return {package_id:Number(row.package_id),price};
    });
  };
  window.novaManualPurchasePrice=function(index,value){
    const row=state.purchaseRows[index];if(!row)return;
    const p=Number(value);
    if(!Number.isSafeInteger(p)||p<=0){toast('أدخل سعر بيع صحيح أكبر من صفر',true);return;}
    row.nova_manual_sale_price=true;row.nova_sale_price=p;
  };
  window.novaSetPurchaseMarkup=function(value){
    const number=Number(value);
    if(!Number.isFinite(number)||number<0||number>maxMargin){
      toast('النسبة يجب أن تكون بين 0 و1000%',true);return;
    }
    state.novaPurchaseMarkup=number;
    // Explicit "apply to all" action resets per-line overrides, then user may edit a line.
    for(const item of state.purchaseRows)item.nova_manual_sale_price=false;
    redraw();
  };

  const originalNav=nav;
  nav=function(page){
    originalNav(page);
    if(page==='purchase')novaEnhancePurchase();
    if(page==='pos')novaFixPosScreen();
    if(page==='reports')novaLoadPharmacyReport();
  };

  function novaEnhancePurchase(){
    const header=document.querySelector('.madar-buy-header');
    if(!header)return;
    const controls=document.createElement('div');
    controls.className='nova-purchase-controls';
    controls.innerHTML=
      '<label class="field">نسبة الزيادة على تكلفة الشراء (%)'+
      '<input type="number" id="nova-purchase-markup" min="0" max="1000" step="0.5" value="'+
        textSafe(state.novaPurchaseMarkup)+'"></label>'+
      '<button type="button" class="btn outline small" id="nova-apply-markup">تطبيق النسبة على كل الأصناف</button>'+
      '<button type="button" class="btn outline small" id="nova-save-purchase-draft">حفظ كمسودة</button>'+
      '<button type="button" class="btn outline small" id="nova-open-purchase-drafts">المسودات المحفوظة</button>';
    header.insertAdjacentElement('afterend',controls);
    const marginInput=$('nova-purchase-markup');
    marginInput.onchange=()=>{
      const margin=Number(marginInput.value);
      if(!Number.isFinite(margin)||margin<0||margin>maxMargin){toast('نسبة غير صحيحة',true);return;}
      state.novaPurchaseMarkup=margin;
      // Keep manually edited prices until "تطبيق النسبة" is explicitly pressed.
      novaSyncPriceInputs();
    };
    $('nova-apply-markup').onclick=()=>novaSetPurchaseMarkup(marginInput.value);
    $('nova-save-purchase-draft').onclick=novaSavePurchaseDraft;
    $('nova-open-purchase-drafts').onclick=novaShowPurchaseDrafts;
    const rows=document.querySelectorAll('.madar-buy-line[data-buy-line]');
    rows.forEach(line=>{
      const index=Number(line.dataset.buyLine),row=state.purchaseRows[index];
      const container=line.querySelector('.madar-buy-line-fields');
      if(!container||!row)return;
      const field=document.createElement('div');
      field.className='field nova-purchase-price-field';
      field.innerHTML='<label>سعر البيع (ج.س) — قابل للتعديل</label>'+
        '<input type="number" min="1" step="1" data-nova-purchase-price="'+index+
        '" value="'+textSafe(novaPurchaseSuggestedPrice(row))+'">'+
        '<small class="muted">يُحفظ مع الفاتورة ويظهر في البيع</small>';
      container.appendChild(field);
      field.querySelector('input').addEventListener('change',event=>novaManualPurchasePrice(index,event.target.value));
    });
  }
  function novaSyncPriceInputs(){
    document.querySelectorAll('[data-nova-purchase-price]').forEach(el=>{
      const item=state.purchaseRows[Number(el.dataset.novaPurchasePrice)];
      if(item&&!item.nova_manual_sale_price)el.value=String(novaPurchaseSuggestedPrice(item));
    });
  }
  function novaDraftFields(){
    return {
      items:state.purchaseRows.map(r=>({...r})),
      supplier_id:Number(v('buy-supplier')||state.purchaseSupplier||0),
      invoice_ref:state.purchaseRef||'',
      invoice_date:state.purchaseDate||today(),
      note:state.purchaseNote||'',payment_method:state.purchasePay||'credit',
      paid:state.purchasePaid||'',bank_ref:state.purchaseBankRef||'',
      partial:Boolean(state.madarPartialPurchase),
      markup:state.novaPurchaseMarkup
    };
  }
  async function novaSavePurchaseDraft(){
    try{
      if(!state.purchaseRows.length)throw Error('أضف صنفاً واحداً على الأقل قبل حفظ المسودة');
      const label=prompt('اسم مسودة المشتريات','مسودة فاتورة مشتريات');
      if(label===null)return;
      await api('nova-purchase-draft-save',{label,draft:novaDraftFields()});
      toast('تم حفظ مسودة المشتريات على السيرفر، دون زيادة المخزون أو تسجيل مديونية');
    }catch(e){toast(e.message,true)}
  }
  async function novaShowPurchaseDrafts(){
    try{
      const drafts=await api('nova-purchase-drafts');
      modal('مسودات المشتريات المحفوظة',
        '<div class="nova-drafts-list">'+
        (drafts.length?drafts.map(d=>'<div class="nova-draft-item"><b>'+textSafe(d.label)+'</b><small>'+
          textSafe(d.updated_at)+'</small><button class="btn small" data-nova-draft-restore="'+d.id+
          '">استرجاع</button><button class="btn outline small" data-nova-draft-delete="'+d.id+
          '">حذف</button></div>').join(''):'لا توجد مسودات مشتريات محفوظة')+'</div>');
      document.querySelectorAll('[data-nova-draft-restore]').forEach(btn=>btn.onclick=()=>{
        const d=drafts.find(x=>x.id===Number(btn.dataset.novaDraftRestore));if(!d)return;
        if(state.purchaseRows.length&&!confirm('استرجاع المسودة سيستبدل بنود الفاتورة الحالية. هل تتابع؟'))return;
        const src=d.draft;
        state.purchaseRows=(src.items||[]).map(x=>({...x}));
        state.purchaseSupplier=String(src.supplier_id||'');
        state.purchaseRef=src.invoice_ref||'';state.purchaseDate=src.invoice_date||today();
        state.purchaseNote=src.note||'';state.purchasePay=src.payment_method||'credit';
        state.purchasePaid=src.paid??'';state.purchaseBankRef=src.bank_ref||'';
        state.madarPartialPurchase=!!src.partial;
        state.madarShowPurchaseDetails=!!(src.invoice_ref||src.note);
        state.novaPurchaseMarkup=Number(src.markup)||0;
        closeModal();nav('purchase');toast('تم استرجاع المسودة للمراجعة قبل الحفظ');
      });
      document.querySelectorAll('[data-nova-draft-delete]').forEach(btn=>btn.onclick=async()=>{
        if(!confirm('حذف المسودة المحفوظة دون أي تأثير على فواتير المشتريات؟'))return;
        try{
          await api('nova-purchase-draft-delete',{draft_id:Number(btn.dataset.novaDraftDelete)});
          await novaShowPurchaseDrafts();
        }catch(e){toast(e.message,true)}
      });
    }catch(e){toast(e.message,true)}
  }

  // This layer must show *why* stocked medication is not saleable. Do not hide
  // a stocked product merely because its price has not yet been entered.
  filterCards=function(){
    const holder=$('sale-tiles');if(!holder)return;
    const input=String(v('pos-scan')||'').trim().toLocaleLowerCase();
    const matched=state.products.filter(product=>{
      if(!product.active||Number(product.available)<=0)return false;
      const hay=[product.name,product.generic_name,product.sku,product.strength,product.manufacturer,
        ...product.packages.map(x=>x.barcode||'')].join(' ').toLocaleLowerCase();
      return !input||hay.includes(input);
    });
    const tiles=matched.slice(0,55).flatMap(product=>
      product.packages.map(pk=>{
        if(Number(pk.factor)>Number(product.available))return '';
        if(Number(pk.sale_price)<=0){
          return '<div class="product-card nova-not-priced"><span class="tag warn">بانتظار تحديد سعر البيع</span><b>'+
            textSafe(product.name)+' · '+textSafe(pk.unit_name)+'</b><small>الرصيد '+
            textSafe(product.available)+' '+textSafe(product.base_uom)+
            ' — الصنف مسجل بالمخزون</small></div>';
        }
        return pkgTile(product,pk);
      })
    ).filter(Boolean).slice(0,70);
    holder.innerHTML=tiles.join('')||
      '<div class="empty">'+(matched.length?'عبوات الصنف لا تتناسب مع الرصيد المتاح؛ راجع وحدات التعبئة.':
        input?'الصنف غير موجود برصيد صالح للبيع؛ راجع الدليل والمخزون.':'لا يوجد مخزون صالح للبيع حالياً.')+'</div>';
  };
  function novaFixPosScreen(){
    filterCards();
    const cart=$('content')?.querySelector('.sale-cart-list');if(!cart)return;
    const choose=cart.closest('.panel');
    if(!choose)return;
    if(!state.saleRows.length){
      const note=document.createElement('div');
      note.className='nova-payment-placeholder';
      note.innerHTML='<b>طرق الدفع المتاحة</b> <span>كاش · بنكك / تحويل بنكي · مختلط · آجل</span>'+
        '<small>أضف دواءً للسلة لتفعيل اختيار طريقة الدفع وإصدار الفاتورة.</small>';
      cart.insertAdjacentElement('afterend',note);
      for(const el of choose.querySelectorAll('.help.section')){
        if(el.textContent.includes('تغطية 100%'))el.textContent='السلة فارغة؛ أضف دواءً من البحث أو الباركود.';
      }
    }
    // Batch05 hold controls must be visible; no changes to the saved server drafts.
    const holdbar=$('content')?.querySelector('.nova-holdbar');
    if(holdbar)holdbar.setAttribute('aria-label','تعليق الفواتير واسترجاعها');
  }

  function novaExpiryItems(){
    const out=[],stamp=today();
    const start=new Date(stamp+'T00:00:00');
    for(const p of state.products||[])for(const l of p.lots||[]){
      if(l.status!=='sellable'||Number(l.qty_base)<=0||!l.expiry)continue;
      const expiry=new Date(l.expiry+'T00:00:00');
      const days=Math.round((expiry-start)/86400000);
      if(Number.isFinite(days)){
        out.push({name:p.name,batch:l.batch,qty:l.qty_base,unit:p.base_uom,expiry:l.expiry,days});
      }
    }
    return out.sort((a,b)=>a.days-b.days);
  }
  const originalDashboard=dashboard;
  dashboard=function(){
    const items=novaExpiryItems();
    const cards=[
      ['منتهية الصلاحية',items.filter(x=>x.days<0).length,'expired'],
      ['تنتهي خلال 7 أيام',items.filter(x=>x.days>=0&&x.days<=7).length,'7'],
      ['تنتهي خلال 30 يوماً',items.filter(x=>x.days>=0&&x.days<=30).length,'30'],
      ['تنتهي خلال 90 يوماً',items.filter(x=>x.days>=0&&x.days<=90).length,'90']
    ];
    return originalDashboard()+
      '<div class="panel nova-expiry-panel"><div class="panel-head"><h2>متابعة صلاحية الأدوية</h2>'+
      '<span class="muted">من أرصدة التشغيلات المستلمة</span></div><div class="nova-expiry-grid">'+
      cards.map(([label,count,kind])=>'<button class="nova-expiry-tile" type="button" onclick="novaShowExpiry(\''+
        kind+'\')"><strong>'+count+'</strong><span>'+label+'</span></button>').join('')+
      '</div><p class="muted-note">كل مربع يفتح قائمة الأدوية والتشغيلات والكميات. الأصناف المنتهية لا تُتاح للبيع.</p></div>';
  };
  window.novaShowExpiry=function(kind){
    const records=novaExpiryItems().filter(x=>kind==='expired'?x.days<0: x.days>=0&&x.days<=Number(kind));
    modal('تنبيهات الصلاحية — '+(kind==='expired'?'منتهية':kind+' يوم'),
      table(['الصنف','التشغيلة','تاريخ الصلاحية','الرصيد','المتبقي'],
        records.map(x=>'<tr><td>'+textSafe(x.name)+'</td><td>'+textSafe(x.batch.startsWith('UNRECORDED-')?'غير مدخل':x.batch)+
          '</td><td>'+textSafe(x.expiry)+'</td><td>'+textSafe(x.qty)+' '+textSafe(x.unit)+'</td><td>'+
          (x.days<0?'منتهي منذ '+Math.abs(x.days)+' يوم':x.days+' يوم')+'</td></tr>'))+
      '<div class="help section">تُحسب التنبيهات من المخزون الفعلي ولا تحذف التشغيلات أو تغير رصيدها.</div>');
  };

  const oldReports=reports;
  reports=function(){
    const first=today().slice(0,8)+'01';
    return '<section id="nova-business-report" class="panel nova-business-report">'+
      '<div class="panel-head"><div><h2>التقرير الشامل للمبيعات والمشتريات والأرباح</h2>'+
      '<p class="muted-note">تقرير مالي للفترة المختارة — المصروفات المسجلة فقط</p></div></div>'+
      '<div class="nova-business-tools">'+
      '<label>من تاريخ <input type="date" id="nova-report-from" value="'+first+'"></label>'+
      '<label>إلى تاريخ <input type="date" id="nova-report-to" value="'+today()+'"></label>'+
      '<button class="btn" onclick="novaLoadPharmacyReport()">عرض التقرير</button>'+
      '<button class="btn outline" onclick="novaPrintBusinessReport()">طباعة / PDF</button>'+
      '<button class="btn outline" onclick="novaExportBusinessCsv()">Excel (CSV)</button>'+
      '</div><div id="nova-business-data" class="nova-business-data">اختر الفترة واضغط عرض التقرير</div></section>'+
      oldReports();
  };
  let lastReport=null;
  window.novaLoadPharmacyReport=async function(){
    const dest=$('nova-business-data');if(!dest)return;
    try{
      const a=v('nova-report-from'),b=v('nova-report-to');
      if(!a||!b||a>b)throw Error('اختر فترة صحيحة');
      dest.textContent='جارٍ تحميل التقرير من السيرفر...';
      const report=await api('nova-pharmacy-finance?from='+encodeURIComponent(a)+'&to='+encodeURIComponent(b));
      lastReport=report;
      const sections=[
        ['المشتريات',[
          ['إجمالي المشتريات',report.purchases_gross],
          ['مردود المشتريات',report.purchase_returns],
          ['صافي مشتريات الموردين',report.purchases_net],
          ['المدفوع للموردين خلال الفترة',report.supplier_payments]]],
        ['المبيعات والأرباح',[
          ['إجمالي المبيعات',report.sales_gross],
          ['مردود المبيعات',report.sales_returns],
          ['صافي المبيعات',report.sales_net],
          ['تكلفة البضاعة المباعة',report.sold_cost],
          ['تكلفة البضاعة المرتجعة',report.returned_cost],
          ['صافي تكلفة المبيعات',report.net_cogs],
          ['مجمل الربح',report.gross_profit],
          ['المصروفات المسجلة',report.expenses],
          ['صافي النتيجة التشغيلية',report.operating_result]]],
        ['التحصيلات النقدية والبنكية',[
          ['تحصيلات المرضى كاش',report.patient_cash_collected],
          ['تحصيلات المرضى بنكي',report.patient_bank_collected],
          ['المبالغ المستردة كاش',report.cash_refunds],
          ['المبالغ المستردة بنكي',report.bank_refunds],
          ['صافي كاش المرضى',report.patient_cash_net],
          ['صافي بنكي المرضى',report.patient_bank_net]]]
      ];
      const sectionHTML=sections.map(([heading,items])=>'<div class="nova-report-section"><h3>'+heading+'</h3>'+
        table(['البيان','القيمة (ج.س)'],items.map(([label,amount])=>'<tr><td>'+textSafe(label)+
          '</td><td><b>'+toMoney(amount)+'</b></td></tr>'))+'</div>').join('');
      const pct=report.gross_margin_pct===null?'—':report.gross_margin_pct+'%';
      const exp=report.expenses_by_category||[];
      dest.innerHTML='<div class="nova-report-kpis">'+
        '<div><small>صافي المبيعات</small><b>'+toMoney(report.sales_net)+'</b></div>'+
        '<div><small>مجمل الربح</small><b>'+toMoney(report.gross_profit)+'</b></div>'+
        '<div><small>هامش مجمل الربح</small><b>'+pct+'</b></div>'+
        '<div><small>النتيجة بعد المصروفات</small><b>'+toMoney(report.operating_result)+'</b></div></div>'+
        '<div class="nova-report-sections">'+sectionHTML+'</div>'+
        '<div class="nova-report-section"><h3>تفصيل المصروفات</h3>'+
        table(['البند','عدد الحركات','القيمة'],exp.map(x=>'<tr><td>'+
          textSafe(x.category)+'</td><td>'+textSafe(x.count)+'</td><td>'+
          toMoney(x.amount)+'</td></tr>'))+'</div>'+
        '<p class="muted-note">القيمة الحالية للمخزون الصالح: '+toMoney(report.stock_current_sellable_value)+
        ' ج.س | مخزون منتهي: '+toMoney(report.stock_current_expired_value)+' ج.س</p>'+
        '<div class="nova-report-notes">'+(report.notes||[]).map(x=>'<p>'+textSafe(x)+'</p>').join('')+'</div>';
    }catch(e){lastReport=null;dest.textContent='تعذر تحميل التقرير: '+e.message;toast(e.message,true)}
  };
  window.novaPrintBusinessReport=function(){
    if(!lastReport)return toast('اعرض التقرير أولاً',true);
    document.body.classList.add('nova-print-business');
    const cleanup=()=>document.body.classList.remove('nova-print-business');
    window.addEventListener('afterprint',cleanup,{once:true});
    window.print();setTimeout(cleanup,12000);
  };
  window.novaExportBusinessCsv=function(){
    if(!lastReport)return toast('اعرض التقرير أولاً',true);
    const r=lastReport,rows=[['البيان','القيمة بالجنيه السوداني'],
      ['من تاريخ',r.from],['إلى تاريخ',r.to],
      ...[['المشتريات',r.purchases_gross],['مردود المشتريات',r.purchase_returns],
         ['صافي المشتريات',r.purchases_net],['المدفوع للموردين',r.supplier_payments],
         ['إجمالي المبيعات',r.sales_gross],['مردود المبيعات',r.sales_returns],
         ['صافي المبيعات',r.sales_net],['تكلفة البضاعة المباعة',r.sold_cost],
         ['تكلفة البضاعة المرتجعة',r.returned_cost],['صافي تكلفة المبيعات',r.net_cogs],
         ['مجمل الربح',r.gross_profit],['المصروفات',r.expenses],
         ['النتيجة التشغيلية',r.operating_result],
         ['صافي تحصيل المرضى كاش',r.patient_cash_net],
         ['صافي تحصيل المرضى بنك',r.patient_bank_net],
         ['القيمة الحالية للمخزون الصالح',r.stock_current_sellable_value]].map(x=>x),
      ['تصنيف المصروف','القيمة']];
    for(const item of r.expenses_by_category||[])rows.push([item.category,item.amount]);
    const csv='\ufeff'+rows.map(row=>row.map(v=>{
      let text=String(v??'');
      if(/^[=+\-@\t\r]/.test(text)&&!/^-[0-9]+$/.test(text))text="'"+text;
      return '"'+text.replace(/"/g,'""')+'"';
    }).join(',')).join('\r\n');
    const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
    const a=document.createElement('a');a.href=url;a.download='NOVA_Pharmacy_Statement_'+r.from+'_'+r.to+'.csv';
    document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2500);
  };
})();
