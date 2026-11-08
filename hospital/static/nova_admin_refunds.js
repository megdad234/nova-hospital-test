/* NOVA_ADMIN_REFUNDS_V1: admin-only UI; existing full-refund API unchanged. */
async function novaRefundAdminView(){
 if(state.role!=='admin')throw Error('هذه الشاشة للمدير فقط');
 const [invoices,banks]=await Promise.all([api('invoices'),api('banks')]);
 window.novaRefundBanks=banks;
 const rows=invoices.filter(x=>Number(x.paid)>0).slice(0,200);
 return '<div class="adm-page">'+panel('إدارة استردادات المرضى — المدير فقط',
 '<p class="help">الاسترداد الكامل فقط متاح في هذه المرحلة. الاسترداد الجزئي غير مفعّل حتى اكتمال مراجعة قاعدة البيانات والقيود. لا يُحذف أي إيصال أصلي.</p>'+
 '<label>بحث برقم الفاتورة أو اسم المريض<input id="nova-refund-search" type="search" placeholder="بحث في الفواتير المحصلة"></label>'+
 '<div id="nova-refund-rows">'+novaRefundRows(rows)+'</div>')+
 '<div id="nova-refund-detail"></div></div>';
}
function novaRefundRows(rows){
 window.novaRefundRowsData=rows;
 return table(['الفاتورة','المريض','المدفوع','المسترد','الحالة',''],rows.map(x=>'<tr><td dir="ltr">'+esc(x.invoice_no)+'</td><td>'+esc(x.patient_name)+'</td><td>'+money(x.paid)+'</td><td>'+money(x.refunded)+'</td><td>'+esc(x.status==='void'?'ملغاة / مستردة':x.status==='settled'?'مدفوعة':'جزئية التحصيل')+'</td><td><button class="outline" type="button" data-nova-refund-id="'+Number(x.id)+'">التفاصيل</button></td></tr>'));
}
function novaWireRefundAdmin(){
 const search=$('nova-refund-search');
 if(search)search.addEventListener('input',()=>{
   const q=search.value.trim().toLowerCase();
   $('nova-refund-rows').innerHTML=novaRefundRows((window.novaRefundRowsData||[]).filter(x=>String(x.invoice_no+' '+x.patient_name).toLowerCase().includes(q)));
   novaWireRefundButtons();
 });
 novaWireRefundButtons();
}
function novaWireRefundButtons(){
 document.querySelectorAll('[data-nova-refund-id]').forEach(b=>b.onclick=()=>novaRefundOpen(Number(b.dataset.novaRefundId)));
}
async function novaRefundOpen(id){
 try{
 const inv=await api('invoice/'+id);
 const remaining=Number(inv.paid)-Number(inv.refunded||0);
 const box=$('nova-refund-detail');if(!box)return;
 const bankOptions=(window.novaRefundBanks||[]).filter(b=>b.active).map(b=>'<option value="'+Number(b.id)+'">'+esc(b.name)+'</option>').join('');
 box.innerHTML=panel('تفاصيل '+esc(inv.invoice_no)+' — '+esc(inv.patient_name),
 '<div class="grid">'+stat('المبلغ المدفوع',money(inv.paid))+stat('المسترد سابقاً',money(inv.refunded))+stat('المتبقي من التحصيل',money(remaining))+'</div>'+
 table(['الخدمة','حصة المريض'],inv.lines.map(x=>'<tr><td>'+esc(x.name)+'</td><td>'+money(x.patient_part)+'</td></tr>'))+
 (inv.refunds.length?'<h3>سجل الاستردادات</h3>'+table(['الرقم','النقدي','البنكي','التاريخ'],inv.refunds.map(x=>'<tr><td>'+esc(x.refund_no)+'</td><td>'+money(x.cash_amount)+'</td><td>'+money(x.bank_amount)+'</td><td>'+esc(x.created_at)+'</td></tr>')):'')+
 (remaining>0&&inv.status!=='void'&&!inv.refunds.length?
 '<h3>استرداد كامل المبلغ — المدير فقط</h3><p class="help">سيتم إلغاء الفاتورة، وقد يُلغى طلب المعمل الذي لم يبدأ تنفيذه. العملية لا يمكن التراجع عنها من هذه الشاشة. يتم منع الاسترداد إذا بدأت خدمة المعمل أو معالجة مطالبة التأمين.</p>'+
 '<form id="nova-refund-full-form"><div class="form"><label>نقدي<input name="cash_amount" type="number" min="0" step="1" value="'+remaining+'" required></label>'+
 '<label>بنكي<input name="bank_amount" type="number" min="0" step="1" value="0" required></label>'+
 '<label>البنك<select name="bank_id"><option value="">بدون بنك</option>'+bankOptions+'</select></label>'+
 '<label>رقم مرجع التحويل البنكي<input name="bank_reference" maxlength="120"></label>'+
 '<label class="wide">سبب الاسترداد (إلزامي)<input name="note" maxlength="500" required placeholder="سبب الاسترداد واسم مستلم المبلغ"></label></div>'+
 '<div class="actions"><button class="primary" type="submit">تأكيد الاسترداد الكامل</button></div></form>':
 '<p class="help">لا يوجد استرداد كامل متاح لهذه الفاتورة. قد تكون ملغاة أو مستردة مسبقاً.</p>'));
 form('nova-refund-full-form',async f=>{
   const cash=Number(f.get('cash_amount')),bank=Number(f.get('bank_amount'));
   if(!Number.isSafeInteger(cash)||!Number.isSafeInteger(bank)||cash<0||bank<0||cash+bank!==remaining)throw Error('يجب أن يساوي مجموع الاسترداد كامل المتبقي دون كسور');
   if(bank>0&&!f.get('bank_id'))throw Error('اختر البنك للاسترداد البنكي');
   if(bank===0&&(f.get('bank_id')||f.get('bank_reference')))throw Error('احذف بيانات البنك عند الاسترداد النقدي');
   const note=String(f.get('note')||'').trim();if(note.length<5)throw Error('اكتب سبباً واضحاً للاسترداد');
   if(!confirm('تأكيد استرداد كامل مبلغ '+money(remaining)+' وإلغاء الفاتورة '+inv.invoice_no+'؟ هذه عملية مالية فعلية.'))return;
   const result=await api('invoice-refund',{invoice_id:id,cash_amount:cash,bank_amount:bank,bank_id:Number(f.get('bank_id')||0),bank_reference:String(f.get('bank_reference')||''),note,idempotency_key:'nova-admin-refund-'+crypto.randomUUID()});
   notice('تم تسجيل الاسترداد: '+result.refund_no);
   await navigate('admin-refunds');
 });
 }catch(e){notice(e.message,true)}
}
