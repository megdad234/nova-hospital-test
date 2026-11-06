/* NOVA Batch09: compact POS + reliable held-invoice dialog.
   Adds no new POS database or divergent business logic. */
'use strict';
(function(){
  const safe=x=>esc(String(x??''));
  function holdBarStatus(n){
    const bar=document.querySelector('.salearea>.nova-holdbar');
    if(!bar)return;
    bar.classList.add('nova-holdbar-compact');
    let el=bar.querySelector('.nova-held-count');
    if(!el){el=document.createElement('span');el.className='nova-held-count';bar.appendChild(el)}
    el.textContent=n===undefined?'':n+' فاتورة معلقة';
    const inline=bar.querySelector('#nova-holdlist');
    if(inline)inline.hidden=true;
  }
  async function held(){
    const list=await api('held-sales');
    if(!Array.isArray(list))throw Error('تعذر تحميل قائمة الفواتير المعلقة');
    return list;
  }
  async function refreshHoldCount(){
    try{holdBarStatus((await held()).length)}
    catch(e){holdBarStatus();toast('تعذر تحديث عدد الفواتير المعلقة: '+e.message,true)}
  }
  window.novaShowHeld=async function(){
    try{
      const records=await held();
      holdBarStatus(records.length);
      const rows=records.map(x=>
        '<div class="nova-hold-entry"><div><strong>'+safe(x.label)+'</strong>'+
        '<small>عدد الأصناف: '+safe(x.item_count)+' · '+safe(x.updated_at)+'</small></div>'+
        '<div class="actions"><button class="btn" type="button" data-resume-held="'+Number(x.id)+'">استرجاع للسلة</button>'+
        '<button class="btn outline" type="button" data-delete-held="'+Number(x.id)+'">حذف</button></div></div>').join('');
      modal('الفواتير المعلقة',records.length?rows:
        '<div class="help">لا توجد فواتير معلقة في حساب الموظف الحالي. الفواتير المعلقة محفوظة على السيرفر، ولا تُنقل تلقائياً بين حسابات الموظفين.</div>');
      document.querySelectorAll('[data-resume-held]').forEach(btn=>btn.onclick=()=>novaResumeHeld(Number(btn.dataset.resumeHeld)));
      document.querySelectorAll('[data-delete-held]').forEach(btn=>btn.onclick=()=>novaRemoveHeld(Number(btn.dataset.deleteHeld)));
    }catch(e){toast('فشل عرض الفواتير المعلقة: '+e.message,true)}
  };
  let resumedHeldId=null;
  let checkoutPending=false;
  async function saveCurrentAsHeld(label){
    const items=state.saleRows.map(r=>({package_id:Number(r.package_id),qty:Number(r.qty)}));
    if(!items.length)return null;
    const result=await api('hold-sale',{
      label,items,partner_id:state.customerId||null,
      authority_id:state.authorityId||null,coverage:state.coverage||0,
      pay_mode:state.payMode,insurance_contract_id:state.insuranceContractId||null
    });
    if(!result?.held_id)throw Error('لم يؤكد السيرفر حفظ الفاتورة المعلقة');
    return Number(result.held_id);
  }
  window.novaHoldNow=async function(){
    if(!state.saleRows.length){toast('أضف دواءً للسلة قبل التعليق',true);return}
    const label=prompt('اسم الفاتورة المعلقة','فاتورة معلقة');
    if(label===null)return;
    try{
      const id=await saveCurrentAsHeld(label);
      state.saleRows=[];resumedHeldId=null;state.idempotency=token();nav('pos');
      toast('تم تعليق الفاتورة وحفظها برقم '+id+' دون خصم المخزون');
      await novaShowHeld();
    }catch(e){toast('تعذر تعليق الفاتورة: '+e.message,true)}
  };
  window.novaResumeHeld=async function(id){
    try{
      const row=(await held()).find(r=>Number(r.id)===Number(id));
      if(!row||!Array.isArray(row.cart?.items)||!row.cart.items.length)throw Error('الفاتورة غير موجودة أو بلا أصناف');
      const products=row.cart.items.map(r=>({package_id:Number(r.package_id),qty:Number(r.qty)}));
      const bad=products.find(p=>!Number.isSafeInteger(p.package_id)||!Number.isSafeInteger(p.qty)||p.qty<1);
      if(bad)throw Error('محتوى فاتورة معلقة غير صالح');
      if(state.saleRows.length){
        if(!confirm('سيتم تعليق الفاتورة المفتوحة تلقائياً ثم استرجاع الفاتورة المختارة. متابعة؟'))return;
        const saved=await saveCurrentAsHeld('فاتورة معلقة تلقائياً قبل استرجاع #'+id);
        if(!saved)throw Error('تعذر حفظ الفاتورة المفتوحة');
      }
      state.saleRows=products;
      state.customerId=row.cart.partner_id||'';
      state.authorityId=row.cart.authority_id||'';
      state.coverage=Number(row.cart.coverage||0);
      state.insuranceContractId=String(row.cart.insurance_contract_id||'');
      state.payMode=['cash','bank','mixed','credit'].includes(row.cart.pay_mode)?row.cart.pay_mode:'cash';
      state.idempotency=token();
      resumedHeldId=Number(id);
      closeModal();nav('pos');
      toast('تم استرجاع '+products.length+' صنف. راجع الأسعار والرصيد قبل تأكيد البيع.');
      const basket=document.querySelector('.salearea .sale-cart-list');
      if(basket)basket.setAttribute('aria-label','السلة المسترجعة: '+row.label);
    }catch(e){toast('فشل استرجاع الفاتورة: '+e.message,true)}
  };
  // Keep the original checkout, insurance validations, and invoice printing.
  // Only act after its idempotency token confirms the server accepted the sale.
  const confirmSaleBeforeHeldCleanup=confirmSale;
  confirmSale=async function(){
    if(checkoutPending)return;
    checkoutPending=true;
    const before=state.idempotency;
    const heldId=resumedHeldId;
    try{
      await confirmSaleBeforeHeldCleanup();
      if(before!==state.idempotency){
        state.saleRows=[];
        resumedHeldId=null;
        if(heldId!==null){
          try{
            const removed=await api('held-sale-delete',{held_id:heldId});
            if(!removed?.deleted)throw Error('لم يؤكد السيرفر حذف المعلقة');
          }catch(e){
            toast('تم البيع بنجاح لكن تعذر إزالة الفاتورة من المعلقات: '+e.message,true);
          }
        }
        nav('pos');
      }
    }finally{checkoutPending=false}
  };
  window.novaRemoveHeld=async function(id){
    if(!confirm('حذف الفاتورة المعلقة من السيرفر؟ لن تُخصم أي كمية من المخزون.'))return;
    try{const result=await api('held-sale-delete',{held_id:Number(id)});
      if(!result?.deleted)throw Error('لم يؤكد السيرفر الحذف');
      toast('تم حذف الفاتورة المعلقة');await novaShowHeld();
    }catch(e){toast('تعذر الحذف: '+e.message,true)}
  };
  // Hook the existing nav, without replacing the existing POS/payment logic.
  const previousNav=nav;
  nav=function(page){
    previousNav(page);
    if(page==='pos'){
      const area=document.querySelector('.salearea');
      if(area){
        area.querySelectorAll(':scope > .panel').forEach((panel,i)=>panel.classList.add(i===0?'nova-pos-search':'nova-pos-checkout'));
        holdBarStatus();
        refreshHoldCount();
        // Keep the sale basket usable on short screens and assist keyboard/barcode users.
        const basket=area.querySelector('.sale-cart-list');
        if(basket){
          basket.setAttribute('role','region');
          basket.setAttribute('aria-label','أصناف فاتورة البيع — قائمة قابلة للتمرير');
          basket.setAttribute('tabindex','0');
        }
        const scan=area.querySelector('#pos-scan');
        if(scan){
          scan.setAttribute('autocomplete','off');
          scan.setAttribute('aria-label','البحث عن الدواء بالاسم أو الباركود');
        }
      }
    }
  };
})();
