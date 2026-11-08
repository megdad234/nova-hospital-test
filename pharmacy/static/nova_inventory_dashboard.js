/* Inventory dashboard: wraps stock page only; original functions remain untouched. */
(function(){
  const originalStock=stock;
  let tab='balances',term='',expiryOnly=false;
  const moneySafe=n=>Number.isFinite(n)?Math.round(n).toLocaleString('en-US')+' ج.س':'—';
  const safe=s=>esc(String(s==null?'':s));
  function inventoryData(){
    const products=Array.isArray(state.products)?state.products:[];
    const rows=[];
    for(const p of products){
      for(const l of (p.lots||[])){
        const qty=Number(l.qty_base)||0;
        const cost=Number(l.unit_cost_milli)||0;
        const valid=l.status==='sellable'&&(!l.expiry||l.expiry>=new Date().toISOString().slice(0,10));
        const expired=l.expiry&&l.expiry<new Date().toISOString().slice(0,10);
        rows.push({p,l,qty,cost:qty*cost/1000,valid,expired});
      }
    }
    return rows;
  }
  function content(){
    const rows=inventoryData(),live=rows.filter(r=>r.qty>0);
    const good=live.filter(r=>r.valid),expired=live.filter(r=>r.expired);
    const cost=good.reduce((a,r)=>a+r.cost,0);
    const unknown=good.filter(r=>!r.l.unit_cost_milli).length;
    const count=new Set(good.map(r=>r.p.id)).size;
    const value=expired.reduce((a,r)=>a+r.cost,0);
    const cards=[['قيمة المخزون الصالح بالتكلفة',moneySafe(cost)],['الأصناف المتوفرة',count+' صنف'],['المنتهي بالتكلفة',moneySafe(value)],['تشغيلات بلا تكلفة',unknown+' تشغيلة']];
    const tabs=[['balances','الأرصدة'],['moves','الحركات'],['expiry','الصلاحيات'],['valuation','التقييم']];
    const button=(id,label)=>'<button class="btn '+(tab===id?'':'outline')+'" onclick="novaInventoryTab(\''+id+'\')">'+label+'</button>';
    const filtered=live.filter(r=>(!term||(r.p.name+' '+r.l.batch+' '+(r.p.sku||'')).toLowerCase().includes(term.toLowerCase()))&&(!expiryOnly||r.expired));
    const rowHtml=filtered.map(r=>'<tr><td>'+safe(r.p.name)+'</td><td>'+safe(r.l.batch)+'</td><td>'+safe(r.l.expiry)+'</td><td>'+safe(r.qty)+' '+safe(r.p.base_uom)+'</td><td>'+moneySafe(r.cost)+'</td><td>'+(typeof can==='function'&&can('stock_adjust')?'<button class="btn outline" onclick="novaInventoryAdjust('+Number(r.p.id)+','+Number(r.l.id)+')">تعديل موثق</button>':'—')+'</td></tr>').join('');
    const balance='<div class="panel"><div class="panel-head"><h2>أرصدة الأصناف والتشغيلات</h2></div><input id="nova-inv-search" placeholder="بحث باسم الدواء أو التشغيلة أو كود الصنف" value="'+safe(term)+'" oninput="novaInventorySearch(this.value)"><div id="nova-inv-table">'+table(['الصنف','التشغيلة','الصلاحية','الرصيد','التكلفة','إجراء'],rowHtml? [rowHtml]:[])+'</div></div>';
    const valuation='<div class="panel"><h2>تقييم المخزون الحالي</h2><p class="help">تقييم تكلفة التشغيلات المسجلة فقط؛ لا يمثل النقدية ولا سعر البيع أو ربحاً محققاً. التشغيلات بلا تكلفة تحتاج مراجعة.</p>'+table(['الصنف','التشغيلة','الصلاحية','الرصيد','القيمة بالتكلفة'],good.map(r=>'<tr><td>'+safe(r.p.name)+'</td><td>'+safe(r.l.batch)+'</td><td>'+safe(r.l.expiry)+'</td><td>'+safe(r.qty)+' '+safe(r.p.base_uom)+'</td><td>'+moneySafe(r.cost)+'</td></tr>'))+'</div>';
    const expiries='<div class="panel"><h2>الصلاحيات</h2>'+table(['الصنف','التشغيلة','الصلاحية','الكمية','الحالة'],live.map(r=>'<tr><td>'+safe(r.p.name)+'</td><td>'+safe(r.l.batch)+'</td><td>'+safe(r.l.expiry)+'</td><td>'+safe(r.qty)+'</td><td>'+(r.expired?'منتهي':r.l.status==='quarantine'?'محجوز':'صالح')+'</td></tr>'))+'</div>';
    const movements='<div class="panel"><h2>آخر حركات المخزون</h2>'+table(['التاريخ','الصنف','النوع','الكمية','المستند'],(state.moves||[]).slice(0,90).map(x=>'<tr><td>'+safe(x.created_at)+'</td><td>'+safe(x.name)+'</td><td>'+safe(x.kind)+'</td><td>'+safe(x.qty_base)+'</td><td>'+safe(x.document)+'</td></tr>'))+'</div>';
    return '<section class="nova-inventory-dashboard"><div class="panel"><div class="panel-head"><h2>إدارة المخزون</h2><span class="help">بيانات حية من أرصدة NOVA</span></div><div class="nova-inv-cards">'+cards.map(x=>'<div class="nova-inv-card"><small>'+x[0]+'</small><strong>'+x[1]+'</strong></div>').join('')+'</div><div class="actions">'+tabs.map(x=>button(x[0],x[1])).join('')+'</div></div>'+(tab==='balances'?balance:tab==='moves'?movements:tab==='expiry'?expiries:valuation)+'<details class="panel"><summary>عرض المخزون السابق وأدوات التسوية الأصلية</summary>'+originalStock()+'</details></section>';
  }
  stock=function(){try{return content()}catch(e){console.error('NOVA inventory dashboard fallback',e);return originalStock()}};
  window.novaInventoryTab=function(t){if(!['balances','moves','expiry','valuation'].includes(t))return;tab=t;redraw()};
  window.novaInventorySearch=function(t){term=t;const focused=document.activeElement;const cursor=focused?.selectionStart;redraw();const input=document.getElementById('nova-inv-search');if(input){input.focus();try{input.setSelectionRange(cursor,cursor)}catch(_){}}};
  window.novaInventoryAdjust=function(pid,lid){
    if(typeof can!=='function'||!can('stock_adjust'))return toast('لا تملك صلاحية تسوية المخزون',true);
    stockAdjustModal();
    const product=document.getElementById('adj-product');
    if(product){product.value=String(pid);if(typeof adjLoadLots==='function')adjLoadLots()}
    const lot=document.getElementById('adj-lot');
    if(lot){lot.value=String(lid);if(typeof adjSyncLot==='function')adjSyncLot()}
  };
  const style=document.createElement('style');
  style.textContent='.nova-inv-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:16px 0}.nova-inv-card{border:1px solid var(--border,#d9e2e7);border-radius:12px;padding:15px;display:flex;flex-direction:column;gap:8px}.nova-inv-card small{opacity:.7}.nova-inv-card strong{font-size:1.3rem}.nova-inventory-dashboard .actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.nova-inventory-dashboard input{max-width:100%;margin:10px 0}';
  document.head.appendChild(style);
})();
