/* NOVA lab worklist: additive, paginated UI. No changes to result/print UI. */
const novaLabQueueState={
  period:'today',status:'all',sort:'newest',q:'',dateFrom:'',dateTo:'',
  page:1,pageSize:25,request:0,timer:null,today:''
};

function novaLabQueueView(){
  const html=
    '<div class="nova-lab-toolbar">'+
      '<label class="nova-lab-search-label">بحث المريض أو الفحص'+
        '<input id="nova-lab-q" type="search" maxlength="120" autocomplete="off" '+
        'placeholder="اسم المريض، رقم الملف، رقم الطلب أو الفحص" aria-label="بحث طلبات المعمل"></label>'+
      '<label>التاريخ<select id="nova-lab-period" aria-label="فترة الطلبات">'+
        '<option value="today">اليوم</option><option value="yesterday">أمس</option>'+
        '<option value="week">آخر 7 أيام</option><option value="all">جميع التواريخ</option>'+
        '<option value="custom">من تاريخ إلى تاريخ</option></select></label>'+
      '<label>الحالة<select id="nova-lab-status" aria-label="حالة النتائج">'+
        '<option value="all">كل الحالات</option>'+
        '<option value="unfinished">غير المكتملة</option>'+
        '<option value="waiting">بانتظار النتيجة</option>'+
        '<option value="draft">تحت الإدخال / مسودة</option>'+
        '<option value="partial">نتائج جزئية</option>'+
        '<option value="completed">مكتملة</option></select></label>'+
      '<label>الترتيب<select id="nova-lab-sort" aria-label="ترتيب الطلبات">'+
        '<option value="newest">الأحدث أولاً</option>'+
        '<option value="oldest">الأقدم أولاً</option></select></label>'+
      '<button type="button" class="outline" id="lab-refresh">تحديث</button>'+
    '</div>'+
    '<div class="nova-lab-dates" id="nova-lab-custom-dates" hidden>'+
      '<label>من تاريخ<input type="date" id="nova-lab-from" aria-label="من تاريخ"></label>'+
      '<label>إلى تاريخ<input type="date" id="nova-lab-to" aria-label="إلى تاريخ"></label>'+
    '</div>'+
    '<div class="nova-lab-alert" id="nova-lab-older-wrap" hidden>'+
      '<span id="nova-lab-older-count"></span>'+
      '<button class="outline" type="button" id="nova-lab-older">عرض غير المكتملة من الأيام السابقة</button>'+
    '</div>'+
    '<div class="nova-lab-counters" id="nova-lab-counters" aria-live="polite"></div>'+
    '<div id="lab-queue" aria-live="polite"><p class="muted">جاري تحميل الطلبات...</p></div>'+
    '<div class="nova-lab-paging">'+
      '<span id="nova-lab-page-info"></span>'+
      '<button type="button" class="outline" id="nova-lab-prev">السابق</button>'+
      '<button type="button" class="outline" id="nova-lab-next">التالي</button>'+
    '</div>'+
    '<p class="muted small">قائمة المعمل تعرض الطلبات المدفوعة فقط. '+
    'البحث يشمل جميع الطلبات القديمة، ولا يغيّر نتائج المرضى أو حالة السداد.</p>';
  return '<div class="grid">'+
    stat('بنود نتائج منشورة',state.labStats?.ready||0)+
    stat('بنود مسودات',state.labStats?.drafts||0)+
    '</div>'+panel('طلبات ونتائج المعمل',html)+
    '<div id="details"></div>'+viewLabStats();
}

function novaLabQueueLabel(order){
  const count=Number(order.tests_count||0);
  const approved=Number(order.approved_count||0);
  const drafts=Number(order.draft_count||0);
  if(count>0&&approved===count)return 'مكتمل';
  if(approved>0)return 'نتائج جزئية';
  if(drafts>0)return 'مسودة';
  return 'بانتظار النتيجة';
}

function novaLabQueueRows(rows){
  if(!rows.length)return '<div class="mutedbox">لا توجد طلبات تطابق البحث والفلاتر المحددة.</div>';
  return table(['رقم الطلب','المريض / الملف','تاريخ الطلب','الفحوصات','النتائج','المبلغ','إجراء'],
    rows.map(o=>{
      const approved=Number(o.approved_count||0);
      const count=Number(o.tests_count||0);
      const complete=count>0&&approved===count;
      const when=String(o.created_at||'').replace('T',' ').slice(0,16);
      return '<tr>'+
        '<td dir="ltr"><b>'+esc(o.order_no)+'</b></td>'+
        '<td><b>'+esc(o.patient_name)+'</b><small class="nova-lab-file" dir="ltr">'+
           esc(o.patient_no)+'</small></td>'+
        '<td dir="ltr">'+esc(when)+'</td>'+
        '<td class="nova-lab-preview">'+esc(o.tests_preview||'—')+'</td>'+
        '<td><span class="tag '+(complete?'green':'orange')+'">'+
          esc(novaLabQueueLabel(o))+'</span><small class="nova-lab-file">'+
          approved+'/'+count+' منشورة</small></td>'+
        '<td>'+money(o.total)+'</td>'+
        '<td><button type="button" class="outline" data-order="'+Number(o.id)+'">فتح</button></td>'+
      '</tr>';
    }));
}

function novaLabQueueSyncControls(){
  const s=novaLabQueueState;
  if(!$('nova-lab-period'))return;
  $('nova-lab-q').value=s.q;
  $('nova-lab-period').value=s.period;
  $('nova-lab-status').value=s.status;
  $('nova-lab-sort').value=s.sort;
  $('nova-lab-from').value=s.dateFrom;
  $('nova-lab-to').value=s.dateTo;
  $('nova-lab-custom-dates').hidden=s.period!=='custom';
}

async function novaLabQueueLoad(){
  const s=novaLabQueueState;
  const token=++s.request;
  const queue=$('lab-queue');
  if(!queue||state.section!=='lab')return;
  queue.setAttribute('aria-busy','true');
  const params=new URLSearchParams({
    period:s.period,status:s.status,sort:s.sort,
    q:s.q,page:String(s.page),page_size:String(s.pageSize)
  });
  if(s.period==='custom'){
    params.set('from',s.dateFrom);params.set('to',s.dateTo);
  }
  try{
    const data=await api('lab/queue?'+params.toString());
    if(token!==s.request||state.section!=='lab'||!$('lab-queue'))return;
    if(!data||!Array.isArray(data.items)||!data.summary)
      throw new Error('تعذر قراءة صفحة طلبات المعمل');
    s.today=String(data.today||'');
    s.page=Number(data.page)||1;
    queue.innerHTML=novaLabQueueRows(data.items);
    queue.querySelectorAll('[data-order]').forEach(button=>
      button.addEventListener('click',()=>openDetails(Number(button.dataset.order))));
    const counts=data.summary;
    $('nova-lab-counters').textContent=
      'طلبات الفترة: '+Number(counts.total||0)+
      ' · غير مكتملة: '+Number(counts.unfinished||0)+
      ' · مكتملة: '+Number(counts.completed||0);
    $('nova-lab-page-info').textContent=
      'النتائج: '+Number(data.total||0)+' · صفحة '+s.page+
      ' من '+Number(data.pages||1);
    $('nova-lab-prev').disabled=s.page<=1;
    $('nova-lab-next').disabled=s.page>=Number(data.pages||1);
    const older=Number(data.older_unfinished||0);
    $('nova-lab-older-wrap').hidden=older===0;
    $('nova-lab-older-count').textContent=
      older+' طلب غير مكتمل من الأيام السابقة';
    if(!s.dateFrom&&s.today)s.dateFrom=s.today;
    if(!s.dateTo&&s.today)s.dateTo=s.today;
    novaLabQueueSyncControls();
  }catch(error){
    if(token===s.request&&state.section==='lab'&&$('lab-queue')){
      // Never fall back to the legacy capped results and silently hide patients.
      queue.textContent='تعذر تحميل طلبات المعمل: '+String(error.message||error);
      if($('nova-lab-page-info'))$('nova-lab-page-info').textContent='';
      if($('nova-lab-prev'))$('nova-lab-prev').disabled=true;
      if($('nova-lab-next'))$('nova-lab-next').disabled=true;
    }
  }finally{
    if(token===s.request&&$('lab-queue'))$('lab-queue').removeAttribute('aria-busy');
  }
}

function novaLabQueueWire(){
  const s=novaLabQueueState;
  novaLabQueueSyncControls();
  const changed=()=>{
    s.page=1;
    s.request++;
    novaLabQueueLoad();
  };
  $('nova-lab-q').addEventListener('input',function(){
    s.q=this.value;
    s.page=1;s.request++;
    if(s.timer)clearTimeout(s.timer);
    s.timer=setTimeout(()=>{
      if(state.section==='lab'&&$('nova-lab-q'))novaLabQueueLoad();
    },250);
  });
  $('nova-lab-period').addEventListener('change',function(){
    s.period=this.value;
    if(s.period==='custom'&&!s.dateFrom){
      s.dateFrom=s.today||new Date().toLocaleDateString('en-CA');
      s.dateTo=s.dateFrom;
    }
    novaLabQueueSyncControls();changed();
  });
  $('nova-lab-status').addEventListener('change',function(){
    s.status=this.value;changed();
  });
  $('nova-lab-sort').addEventListener('change',function(){
    s.sort=this.value;changed();
  });
  $('nova-lab-from').addEventListener('change',function(){
    s.dateFrom=this.value;changed();
  });
  $('nova-lab-to').addEventListener('change',function(){
    s.dateTo=this.value;changed();
  });
  $('lab-refresh').addEventListener('click',()=>novaLabQueueLoad());
  $('nova-lab-older').addEventListener('click',function(){
    s.period='all';s.status='unfinished';
    s.sort='oldest';s.page=1;
    novaLabQueueSyncControls();novaLabQueueLoad();
  });
  $('nova-lab-prev').addEventListener('click',function(){
    if(s.page>1){s.page--;novaLabQueueLoad();}
  });
  $('nova-lab-next').addEventListener('click',function(){
    s.page++;novaLabQueueLoad();
  });
  novaLabQueueLoad();
}
