'use strict';
/* NOVA Batch12 — insurance at the pharmacy counter.
   No change to cash sales, invoice calculation or the original claims engine. */
(function(){
  state.novaInsuredMember=null;
  state.novaInsuranceVerified=false;
  let insuranceSearchRows=[];
  let hospitalSearchRows=[];
  let selectedHospitalPatient=null;
  let lastMonthlyStatement=null;
  const safe=value=>esc(String(value??''));
  const escapeCSV=value=>{
    let v=String(value??'');
    if(/^[=+\-@\t\r]/.test(v)&&!/^-[0-9]+$/.test(v))v="'"+v;
    return '"'+v.replace(/"/g,'""')+'"';
  };
  function contractChoice(){
    return (state.insurance||[]).find(x=>String(x.id)===String(state.insuranceContractId));
  }
  function currentInsured(){
    const r=state.novaInsuredMember;
    if(!r)return null;
    if(String(r.contract_id)!==String(state.insuranceContractId)
       ||String(r.authority_id)!==String(state.authorityId)){
      state.novaInsuredMember=null;state.novaInsuranceVerified=false;
      return null;
    }
    return r;
  }
  const oldConfirmSale=confirmSale;
  confirmSale=async function(){
    if(state.authorityId&&Number(state.coverage)>0 || state.insuranceContractId){
      if(!contractChoice())return toast('اختر عقد التأمين أولاً',true);
      if(!currentInsured())return toast('اختر اسم المستفيد ورقم بطاقته قبل إتمام البيع',true);
      if(state.novaInsuranceVerified!==true)return toast('أكد مراجعة بطاقة المستفيد وأهلية العلاج قبل الحفظ',true);
    }
    return oldConfirmSale();
  };

  function insuredPanel(){
    const panel=document.querySelector('.salearea>.nova-pos-checkout');
    if(!panel)return;
    const head=panel.querySelector('.panel-head');
    if(!head)return;
    const customer=currentInsured();
    const authorized=!!state.authorityId;
    const node=document.createElement('div');
    node.className='nova-insured-panel';
    node.innerHTML='<div class="nova-insured-title"><b>صرف الأدوية بالتأمين</b>'+
      '<small>رقم البطاقة وملف المريض محفوظان في فاتورة البيع</small></div>'+
      (!authorized?'<p class="muted-note">للبيع العادي ما مطلوب تسجيل المريض. اختر جهة تأمين أسفل السلة لتفعيل بيانات المستفيد.</p>':
       !contractChoice()?'<div class="warnbox">اختر عقد التأمين من حقل «العقد التأميني» الموجود أسفل السلة، ثم ابحث عن المستفيد. لا يمكن اعتماد تغطية بدون عقد وبطاقة.</div>':
       '<div class="nova-insured-search"><input type="text" id="nova-insured-search" placeholder="ابحث باسم المريض أو رقم البطاقة" autocomplete="off" maxlength="100">'+
       '<button class="btn outline small" type="button" id="nova-insured-find">بحث</button>'+
       '<button class="btn outline small" type="button" id="nova-insured-new">تسجيل مستفيد</button></div>'+
       '<div id="nova-insured-results"></div>'+
       (customer?'<div class="nova-insured-selected"><b>'+safe(customer.patient_name)+'</b>'+
       '<span>ملف المريض: <b dir="ltr">'+safe(customer.patient_no)+'</b></span>'+
       '<span>رقم البطاقة: <b dir="ltr">'+safe(customer.card_no)+'</b></span>'+
       '<span>الجهة: '+safe(customer.insurer_name)+'</span>'+
       '<span>التغطية المعتمدة بالعقد: <b>'+safe(customer.coverage)+'%</b></span></div>'+
       '<label class="nova-insured-verify"><input type="checkbox" id="nova-insured-verify" '+(state.novaInsuranceVerified?'checked':'')+
       '> راجعت البطاقة والأهلية والوصفة والأدوية المشمولة في العقد قبل الصرف</label>':
       '<p class="muted-note">اختر بطاقة من نتائج البحث. لا تكفي كتابة نسبة تغطية يدوياً.</p>'));
    head.insertAdjacentElement('afterend',node);
    const search=$('nova-insured-search');
    if(search){search.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();novaSearchInsured()}};
      $('nova-insured-find').onclick=novaSearchInsured;
      $('nova-insured-new').onclick=novaOpenInsuredEnrollment;}
    $('nova-insured-verify')?.addEventListener('change',e=>{state.novaInsuranceVerified=e.target.checked});
    $('pos-insurance')?.addEventListener('change',()=>{
       state.novaInsuredMember=null;state.novaInsuranceVerified=false;
       nav('pos');
    });
    $('pos-authority')?.addEventListener('change',()=>{
       state.novaInsuredMember=null;state.novaInsuranceVerified=false;
    });
  }
  async function novaSearchInsured(){
    try{
      const q=$('nova-insured-search')?.value.trim()||'';
      if(!q)throw Error('أدخل اسم المستفيد أو رقم بطاقته');
      if(!state.insuranceContractId)throw Error('اختر عقد التأمين');
      const data=await api('nova-insured-search?contract_id='+
           encodeURIComponent(state.insuranceContractId)+'&q='+encodeURIComponent(q));
      insuranceSearchRows=data||[];
      const holder=$('nova-insured-results');
      if(!holder)return;
      holder.innerHTML=insuranceSearchRows.length?insuranceSearchRows.map((r,i)=>
        '<button type="button" class="nova-insured-result" data-insured-index="'+i+'"><b>'+
        safe(r.patient_name)+'</b><span dir="ltr">'+safe(r.card_no)+'</span>'+
        '<small>ملف '+safe(r.patient_no)+' | التغطية '+safe(r.coverage)+'%</small></button>').join(''):
        '<p class="warnbox">لم نجد مستفيداً مسجلاً بهذه البيانات. تأكد من البطاقة أو سجّله من زر «تسجيل مستفيد».</p>';
      holder.querySelectorAll('[data-insured-index]').forEach(button=>{
        button.onclick=()=>novaSelectInsured(insuranceSearchRows[Number(button.dataset.insuredIndex)]);
      });
    }catch(e){toast('بحث التأمين: '+e.message,true)}
  }
  function novaSelectInsured(item){
    if(!item||!contractChoice())return;
    state.novaInsuredMember={...item};
    state.novaInsuranceVerified=false;
    state.customerId=String(item.partner_id);
    state.authorityId=String(item.authority_id);
    state.insuranceContractId=String(item.contract_id);
    state.coverage=Number(item.coverage);
    nav('pos');
    toast('تم اختيار المستفيد؛ راجع البطاقة ثم أكد أهلية الصرف');
  }
  function novaOpenInsuredEnrollment(){
    if(!contractChoice())return toast('اختر عقد التأمين أولاً',true);
    selectedHospitalPatient=null;
    modal('تسجيل مستفيد تأمين مرتبط بملف المريض',
      '<div class="nova-insured-enroll"><p class="help">ابحث عن ملف المريض الموجود أولاً. لو ماف ملف، أدخل الاسم وسينشئ NOVA ملفاً واحداً في قاعدة المستشفى المركزية.</p>'+
      '<label>بحث عن مريض مسجل بالاسم أو رقم الملف أو الهاتف</label>'+
      '<div class="nova-insured-search"><input id="nova-hospital-patient-q" placeholder="اسم المريض أو رقم الملف" maxlength="80">'+
      '<button type="button" class="btn outline" id="nova-hospital-find">بحث</button></div>'+
      '<div id="nova-hospital-patient-results"></div>'+
      '<div id="nova-selected-hospital-patient" class="nova-insured-selected" hidden></div>'+
      '<div class="formgrid"><label>اسم مريض جديد (فقط إن لم يكن مسجلاً)<input id="nova-new-patient-name" maxlength="160"></label>'+
      '<label>الهاتف<input id="nova-new-patient-phone" maxlength="35"></label>'+
      '<label>رقم بطاقة التأمين<input id="nova-new-insured-card" maxlength="100" required></label>'+
      '<label>نوع المستفيد<select id="nova-new-insured-relation">'+
      [['primary','مشترك أساسي'],['spouse','زوج / زوجة'],['child','ابن / ابنة'],['father','أب'],['mother','أم']].
      map(([key,label])=>'<option value="'+key+'">'+label+'</option>').join('')+
      '</select></label></div>'+
      '<label class="nova-insured-verify"><input type="checkbox" id="nova-new-insured-confirm"> تأكدت من هوية المريض والبطاقة وسريان تغطيته</label>'+
      '<button class="btn section" type="button" id="nova-insured-save">حفظ المستفيد وربطه بالتأمين</button></div>');
    $('nova-hospital-find').onclick=novaFindHospitalPatient;
    $('nova-hospital-patient-q').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();novaFindHospitalPatient()}};
    $('nova-insured-save').onclick=novaSaveInsuredEnrollment;
  }
  async function novaFindHospitalPatient(){
    try{
      const term=$('nova-hospital-patient-q')?.value.trim()||'';
      if(!term)throw Error('اكتب الاسم أو رقم الملف');
      hospitalSearchRows=await api('nova-hospital-patient-search?q='+encodeURIComponent(term));
      const host=$('nova-hospital-patient-results');
      if(!host)return;
      host.innerHTML=hospitalSearchRows.length?hospitalSearchRows.map((p,i)=>
        '<button class="nova-insured-result" type="button" data-patient-index="'+i+'"><b>'+
        safe(p.full_name)+'</b><small dir="ltr">'+safe(p.patient_no)+'</small>'+
        '<small>'+safe(p.phone||'')+'</small></button>').join(''):
        '<p class="muted-note">لا يوجد ملف مطابق؛ يمكنك تسجيل مريض جديد أدناه.</p>';
      host.querySelectorAll('[data-patient-index]').forEach(b=>b.onclick=()=>{
        selectedHospitalPatient=hospitalSearchRows[Number(b.dataset.patientIndex)];
        $('nova-selected-hospital-patient').hidden=false;
        $('nova-selected-hospital-patient').innerHTML='المريض المختار: <b>'+
          safe(selectedHospitalPatient.full_name)+'</b> — <span dir="ltr">'+
          safe(selectedHospitalPatient.patient_no)+'</span>'+
          '<button type="button" class="btn outline small" id="nova-unpick-patient">إلغاء</button>';
        $('nova-unpick-patient').onclick=()=>{
          selectedHospitalPatient=null;$('nova-selected-hospital-patient').hidden=true;
          $('nova-new-patient-name').disabled=false;$('nova-new-patient-phone').disabled=false;
        };
        $('nova-new-patient-name').value=selectedHospitalPatient.full_name;
        $('nova-new-patient-phone').value=selectedHospitalPatient.phone||'';
        $('nova-new-patient-name').disabled=true;$('nova-new-patient-phone').disabled=true;
      });
    }catch(e){toast('بحث ملفات المرضى: '+e.message,true)}
  }
  async function novaSaveInsuredEnrollment(){
    try{
      const card=$('nova-new-insured-card')?.value.trim()||'';
      if(!card)throw Error('رقم بطاقة التأمين مطلوب');
      if(!$('nova-new-insured-confirm')?.checked)throw Error('أكد التحقق من البطاقة والأهلية أولاً');
      const row=await api('nova-insured-enroll',{
        contract_id:Number(state.insuranceContractId),
        patient_id:selectedHospitalPatient?.id||null,
        full_name:selectedHospitalPatient?.full_name||$('nova-new-patient-name')?.value||'',
        phone:selectedHospitalPatient?.phone||$('nova-new-patient-phone')?.value||'',
        card_no:card,relation:$('nova-new-insured-relation').value,
        eligibility_confirmed:true
      });
      await refresh();
      closeModal();
      novaSelectInsured(row);
      toast('تم حفظ البطاقة وربط المستفيد بملف المستشفى');
    }catch(e){toast('لم يتم تسجيل المستفيد: '+e.message,true)}
  }
  const existingNav=nav;
  nav=function(page){
    existingNav(page);
    if(page==='pos')insuredPanel();
  };

  const previousReceipt=receipt;
  receipt=function(s){
    const html=previousReceipt(s);
    const card=s?.insurance_details;
    if(!card)return html;
    const details='<div class="receipt-insured-identity"><b>بيانات التأمين</b>'+
      '<div>المستفيد: '+safe(card.patient_name)+'</div>'+
      '<div>رقم الملف: <b dir="ltr">'+safe(card.patient_no)+'</b></div>'+
      '<div>رقم البطاقة: <b dir="ltr">'+safe(card.card_no)+'</b></div>'+
      '<div>جهة التأمين: '+safe(card.insurer_name)+'</div></div>';
    return html.replace('<div class="receipt-divider"></div>',
      details+'<div class="receipt-divider"></div>');
  };

  const oldClaims=claims;
  claims=function(){
    return oldClaims()+
      '<div class="panel nova-insurance-statement"><div class="panel-head"><h2>كشف أدوية التأمين التفصيلي</h2>'+
      '<span class="tag">مراجعة المطالبات الشهرية</span></div>'+
      '<p class="help">يعرض أسماء المستفيدين وأرقام البطاقات والأدوية والكميات والمرتجعات وحصة الشركة لكل فاتورة مرة واحدة، بما فيها الفواتير القديمة غير الموثقة بعلامة واضحة.</p>'+
      '<div class="nova-insurance-statement-toolbar">'+
      '<label>الشركة<select id="nova-claim-detail-authority">'+
      state.partners.filter(p=>p.kind==='authority').map(p=>
      '<option value="'+Number(p.id)+'">'+safe(p.name)+'</option>').join('')+'</select></label>'+
      '<label>الشهر<input type="month" id="nova-claim-detail-month" value="'+today().slice(0,7)+'"></label>'+
      '<button type="button" class="btn" id="nova-claim-detail-show">عرض الكشف</button>'+
      '<button type="button" class="btn outline" id="nova-claim-detail-excel">Excel (CSV)</button>'+
      '<button type="button" class="btn outline" id="nova-claim-detail-pdf">طباعة / PDF</button>'+
      '</div><div id="nova-claim-detail-results"></div></div>';
  };
  const oldClaimsNav=nav;
  nav=function(page){
    oldClaimsNav(page);
    if(page==='claims'){
      $('nova-claim-detail-show')?.addEventListener('click',novaLoadMonthly);
      $('nova-claim-detail-excel')?.addEventListener('click',novaExportMonthly);
      $('nova-claim-detail-pdf')?.addEventListener('click',novaPrintMonthly);
    }
  };
  async function novaLoadMonthly(){
    try{
      const authority=$('nova-claim-detail-authority')?.value;
      const period=$('nova-claim-detail-month')?.value;
      if(!authority||!period)throw Error('حدد الشركة والشهر');
      const data=await api('nova-insurance-monthly-detail?authority_id='+
        encodeURIComponent(authority)+'&period='+encodeURIComponent(period));
      lastMonthlyStatement=data;
      const root=$('nova-claim-detail-results');if(!root)return;
      const names=['الفاتورة','التاريخ','المريض','رقم البطاقة','الدواء','الوحدة',
        'الكمية','مرتجع','السعر','الإجمالي','حصة التأمين (مرة واحدة)','حالة المطالبة'];
      root.innerHTML='<p><b>عدد الفواتير: '+safe(data.invoice_count)+
        '</b> · حصة التأمين: <b>'+fmt(data.covered_invoices_total)+' ج.س</b></p>'+
        '<div class="nova-claim-table">'+table(names,data.rows.map(row=>
          '<tr><td dir="ltr">'+safe(row.ref)+'</td>'+
          '<td dir="ltr">'+safe(row.created_at)+'</td><td>'+safe(row.patient_name||'بيانات تاريخية ناقصة')+
          '</td><td dir="ltr">'+safe(row.card_no||'غير مسجل')+
          '</td><td>'+safe(row.medicine)+'</td><td>'+safe(row.unit_name)+'</td>'+
          '<td>'+safe(row.qty)+'</td><td>'+safe(row.returned_qty)+'</td>'+
          '<td>'+fmt(row.unit_price)+'</td><td>'+fmt(row.line_total)+'</td>'+
          '<td>'+fmt(row.covered_invoice_once)+'</td><td>'+
          (row.claim_id?'مُدرج بمطالبة رقم '+safe(row.claim_id):'لم يجمع في مطالبة بعد')+
          '</td></tr>'))+'</div><p class="muted-note">'+safe(data.note)+'</p>';
    }catch(e){lastMonthlyStatement=null;toast('تعذر تحميل كشف التأمين: '+e.message,true)}
  }
  function novaMonthlyRows(){
    if(!lastMonthlyStatement)throw Error('اعرض الكشف أولاً');
    const cols=['رقم الفاتورة','التاريخ','اسم المريض','رقم الملف','رقم البطاقة',
      'الدواء','وحدة التعبئة','الكمية','المرتجع','سعر الوحدة',
      'قيمة السطر','حصة التأمين للفاتورة','رقم المطالبة'];
    const rows=lastMonthlyStatement.rows.map(r=>[
      r.ref,r.created_at,r.patient_name||'غير موثق تاريخياً',r.patient_no||'',
      r.card_no||'غير مسجل',r.medicine,r.unit_name,r.qty,r.returned_qty,
      r.unit_price,r.line_total,r.covered_invoice_once,r.claim_id||'']);
    return [cols,...rows];
  }
  function novaExportMonthly(){
    try{
      const rows=novaMonthlyRows();
      const csv='\ufeff'+rows.map(row=>row.map(escapeCSV).join(',')).join('\r\n');
      const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
      const a=document.createElement('a');a.href=url;
      a.download='NOVA_Pharmacy_Insurance_'+lastMonthlyStatement.period+'.csv';
      document.body.appendChild(a);a.click();a.remove();
      setTimeout(()=>URL.revokeObjectURL(url),8000);
    }catch(e){toast(e.message,true)}
  }
  function novaPrintMonthly(){
    try{
      const rows=novaMonthlyRows();
      const existing=document.getElementById('nova-claim-print-frame');if(existing)existing.remove();
      const frame=document.createElement('iframe');frame.id='nova-claim-print-frame';
      frame.style.cssText='position:fixed;left:-15000px;top:0;width:1100px;height:900px;border:0';
      const body='<h2>NOVA — كشف مطالبة أدوية التأمين '+safe(lastMonthlyStatement.period)+'</h2>'+
        '<p>عدد الفواتير '+safe(lastMonthlyStatement.invoice_count)+
        ' — حصة التأمين '+fmt(lastMonthlyStatement.covered_invoices_total)+' ج.س</p>'+
        '<table><thead><tr>'+rows[0].map(x=>'<th>'+safe(x)+'</th>').join('')+
        '</tr></thead><tbody>'+rows.slice(1).map(row=>
        '<tr>'+row.map(x=>'<td>'+safe(x)+'</td>').join('')+'</tr>').join('')+'</tbody></table>';
      frame.srcdoc='<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'+
       '<style>@page{size:A4 landscape;margin:10mm}body{font:9pt Tahoma,Arial;direction:rtl}'+
       'table{width:100%;border-collapse:collapse}th,td{border:1px solid #bbb;padding:4px;font-size:7pt;overflow-wrap:anywhere}'+
       'thead{display:table-header-group}tr{break-inside:avoid}</style></head><body>'+body+'</body></html>';
      frame.onload=()=>{const win=frame.contentWindow;
        win.addEventListener('afterprint',()=>frame.remove(),{once:true});
        win.focus();win.print();setTimeout(()=>frame.remove(),120000)};
      document.body.appendChild(frame);
    }catch(e){toast(e.message,true)}
  }
})();
