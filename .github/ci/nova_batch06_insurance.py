# -*- coding: utf-8 -*-
"""NOVA Batch 06: insurance beneficiary rates, patient relationship, immutable invoice snapshot.
Execute AFTER Batches 01-05. No live database access in CI.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

def change(path, fn):
    f = ROOT / path
    old = f.read_text(encoding="utf-8")
    new = fn(old)
    if old == new:
        raise RuntimeError("B06_NO_CHANGE " + path)
    f.write_text(new, encoding="utf-8")
    print("B06_CHANGED", path)

def one(s, old, new):
    count = s.count(old)
    if count != 1:
        raise RuntimeError("B06_ANCHOR "+repr(old[:95])+" "+str(count))
    return s.replace(old, new)

SCHEMA = '''
# NOVA_BATCH06_INSURANCE — kept separate from other modules.
NOVA_BENEFICIARIES = {
    "primary": "المشترك الأساسي",
    "spouse": "الزوج / الزوجة",
    "child": "الأبناء",
    "father": "الأب",
    "mother": "الأم",
    "unspecified": "غير محدد (فواتير سابقة)",
}

def nova_beneficiary(v):
    if not isinstance(v,str) or v not in NOVA_BENEFICIARIES or v == "unspecified":
        raise ValueError("نوع المستفيد من التأمين غير صحيح")
    return v

def nova_insurance_schema(c):
    c.execute("""CREATE TABLE IF NOT EXISTS nova_insurer_beneficiary_rates (
       insurer_id INTEGER NOT NULL REFERENCES nova_insurers(id),
       beneficiary_type TEXT NOT NULL CHECK(beneficiary_type IN
         ('primary','spouse','child','father','mother')),
       coverage INTEGER NOT NULL CHECK(coverage BETWEEN 0 AND 100),
       PRIMARY KEY(insurer_id,beneficiary_type))""")
    columns = {r["name"] for r in c.execute("PRAGMA table_info(nova_patient_insurance)")}
    if "beneficiary_type" not in columns:
        c.execute("ALTER TABLE nova_patient_insurance ADD COLUMN beneficiary_type TEXT NOT NULL DEFAULT 'primary'")
    columns = {r["name"] for r in c.execute("PRAGMA table_info(nova_invoices)")}
    if "beneficiary_type" not in columns:
        # Historical invoices cannot be assigned a relative relationship retroactively.
        c.execute("ALTER TABLE nova_invoices ADD COLUMN beneficiary_type TEXT NOT NULL DEFAULT 'unspecified'")

def nova_beneficiary_rates(c):
    return pharmacy.query(c, """SELECT r.insurer_id, r.beneficiary_type, r.coverage,
      i.name AS insurer_name FROM nova_insurer_beneficiary_rates r
      JOIN nova_insurers i ON i.id=r.insurer_id
      ORDER BY i.name,r.beneficiary_type""")

def nova_set_beneficiary_rate(c,actor,data):
    iid = num(data.get("insurer_id"),"شركة التأمين",1)
    kind = nova_beneficiary(data.get("beneficiary_type"))
    inherit = data.get("inherit") is True
    coverage = None if inherit else num(data.get("coverage"),"نسبة التغطية",0,100)
    start(c)
    try:
        if not pharmacy.one(c,"SELECT 1 ok FROM nova_insurers WHERE id=?",(iid,)):
            raise ValueError("شركة التأمين غير موجودة")
        if inherit:
            c.execute("DELETE FROM nova_insurer_beneficiary_rates WHERE insurer_id=? AND beneficiary_type=?",(iid,kind))
        else:
            c.execute("""INSERT INTO nova_insurer_beneficiary_rates(insurer_id,beneficiary_type,coverage)
                VALUES(?,?,?) ON CONFLICT(insurer_id,beneficiary_type)
                DO UPDATE SET coverage=excluded.coverage""",(iid,kind,coverage))
        audit(c,actor,"beneficiary_rate_changed",iid,
              {"beneficiary_type":kind,"coverage":coverage,"inherit":inherit})
        done(c)
    except Exception:
        rollback(c)
        raise
    return {"insurer_id":iid,"beneficiary_type":kind,"coverage":coverage,"inherit":inherit}
'''

def finance(s):
    # Run idempotent migrations during existing startup, after the original finance DDL.
    pat = r"(?ms)^(def init\(c\):\n)(.*?)(?=^def [a-zA-Z_])"
    m = re.search(pat,s)
    if not m:
        raise RuntimeError("B06_INIT_MISSING")
    block = m.group(0)
    if "nova_insurance_schema" in block:
        raise RuntimeError("B06_INIT_ALREADY")
    s = s[:m.start()] + block.rstrip("\n") + "\n    nova_insurance_schema(c)\n\n" + s[m.end():]
    s = one(s, "    member=text(data,'member_no',100)\n    start(c)",
            "    member=text(data,'member_no',100)\n    beneficiary=nova_beneficiary(data.get('beneficiary_type','primary'))\n    start(c)")
    # Match the existing statement without assuming its indentation or line breaks.
    pattern = (r"INSERT INTO nova_patient_insurance\\(patient_id,insurer_id,member_no,changed_at\\)"
               r"[\\s\\S]*?member_no=excluded\\.member_no,changed_at=excluded\\.changed_at"
               r"\\s*'''\\s*,\\s*\\(pid,iid,member,now\\(\\)\\)\\)")
    repl = """INSERT INTO nova_patient_insurance(patient_id,insurer_id,member_no,changed_at,beneficiary_type)
                 VALUES(?,?,?,?,?) ON CONFLICT(patient_id) DO UPDATE SET insurer_id=excluded.insurer_id,
                 member_no=excluded.member_no,changed_at=excluded.changed_at,
                 beneficiary_type=excluded.beneficiary_type''',(pid,iid,member,now(),beneficiary))"""
    s,n = re.subn(pattern,lambda m:repl,s,count=1)
    if n!=1:raise RuntimeError("B06_PATIENT_INSURANCE_SQL_ANCHOR "+str(n))
    s = one(s, "def _coverage(c,iid,cat,key,default):",
            "def _coverage(c,iid,cat,key,default,beneficiary_type='primary'):")
    s = one(s,
      """    return row['coverage'] if row else default

def _lines(c,keys,insurer_id):""",
      """    if row:return row['coverage']
    if beneficiary_type != 'unspecified':
        b=pharmacy.one(c,'SELECT coverage FROM nova_insurer_beneficiary_rates WHERE insurer_id=? AND beneficiary_type=?',(iid,beneficiary_type))
        if b:return b['coverage']
    return default

def _lines(c,keys,insurer_id,beneficiary_type='primary'):""")
    s = one(s, "price=s['price'];cov=_coverage(c,insurer_id,s['category_code'],key,insurer['default_coverage'] if insurer else 0)",
            "price=s['price'];cov=_coverage(c,insurer_id,s['category_code'],key,insurer['default_coverage'] if insurer else 0,beneficiary_type)")
    s = one(s,
      """    lines,insurer=_lines(c,data.get('services'),iid)
    return {'lines':lines,'insurer_id':iid,'insurer_name':insurer['name'] if insurer else '',""",
      """    linked=get_patient_insurance(c,pid)
    if 'beneficiary_type' in data and data['beneficiary_type']:
        beneficiary_type=nova_beneficiary(data['beneficiary_type'])
    elif linked and iid and linked['insurer_id']==iid:
        beneficiary_type=nova_beneficiary(linked['beneficiary_type'])
    else:beneficiary_type='primary'
    lines,insurer=_lines(c,data.get('services'),iid,beneficiary_type)
    return {'lines':lines,'beneficiary_type':beneficiary_type,'insurer_id':iid,'insurer_name':insurer['name'] if insurer else '',""")
    s = one(s,
      """member_no,total,insurer_due,patient_due,note,lab_order_id)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                 (invoice_no,pid,actor['id'],now(),iid or None,quoted['insurer_name'],member,
                  quoted['total'],quoted['insurer_due'],quoted['patient_due'],note,lab_order_id))""",
      """member_no,total,insurer_due,patient_due,note,lab_order_id,beneficiary_type)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                 (invoice_no,pid,actor['id'],now(),iid or None,quoted['insurer_name'],member,
                  quoted['total'],quoted['insurer_due'],quoted['patient_due'],note,lab_order_id,
                  quoted['beneficiary_type']))""")
    s = one(s,
      """key,insurer['default_coverage'] if insurer else 0)
            insurer_part=line['price']*coverage//100""",
      """key,insurer['default_coverage'] if insurer else 0,inv['beneficiary_type'])
            insurer_part=line['price']*coverage//100""")
    # Keep helper code top-level; init is executed after module import.
    s += "\n" + SCHEMA
    return s

change("hospital/finance.py", finance)

def gateway(s):
    # Admin-only rate administration, reception/cashier patient role rules unchanged.
    s=one(s,
      "                    if path=='/api/hospital/insurance-rates':",
      """                    if path=='/api/hospital/nova-beneficiary-rates':
                        core.require_role(role,'admin')
                        return self.reply(finance.nova_beneficiary_rates(c))
                    if path=='/api/hospital/insurance-rates':""")
    s=one(s,
      "                    if path=='/api/hospital/insurance-rate':",
      """                    if path=='/api/hospital/nova-beneficiary-rate':
                        core.require_role(role,'admin')
                        return self.reply(finance.nova_set_beneficiary_rate(c,user,data))
                    if path=='/api/hospital/insurance-rate':""")
    return s

change("hospital/gateway.py",gateway)

# UI change stays narrow and keeps all prior cashier, reception and finance functions.
FRONTEND = r"""
// NOVA_BATCH06_INSURANCE: beneficiary-specific coverages, editable patient insurance.
const novaBeneficiaryLabels={
 primary:'المشترك الأساسي',spouse:'الزوج / الزوجة',
 child:'الأبناء',father:'الأب',mother:'الأم'
};
const novaBeneficiaryOptions=()=>Object.entries(novaBeneficiaryLabels).map(([k,v])=>
 '<option value="'+k+'">'+esc(v)+'</option>').join('');
const novaOriginalPatientForm=financePatientForm;
financePatientForm=function(){
 return novaOriginalPatientForm().replace(
  '<div class="actions"><button class="primary"',
  '<label>نوع المستفيد من التأمين<select id="nova-new-beneficiary">'+novaBeneficiaryOptions()+
  '</select></label><div class="actions"><button class="primary"');
};
const novaOriginalServicesView=financeServicesView;
financeServicesView=function(){
 return novaOriginalServicesView()+
 panel('بيانات التأمين للمريض المختار',
  '<div id="nova-beneficiary-patient" hidden>'+
  '<p class="help">حدد الشركة أعلاه ونوع المستفيد ورقم البطاقة، ثم احفظ قبل إرسال طلب جديد.</p>'+
  '<div class="form"><label>نوع المستفيد<select id="nova-beneficiary-type">'+novaBeneficiaryOptions()+
  '</select></label><label>رقم بطاقة التأمين<input id="nova-beneficiary-member" maxlength="100"></label></div>'+
  '<div class="actions"><button type="button" id="nova-beneficiary-save" class="outline">حفظ بيانات تأمين المريض</button></div>'+
  '</div><p class="muted" id="nova-beneficiary-empty">اختر مريضاً لعرض بياناته التأمينية.</p>');
};
function novaBenefitSelected(info){
 const pane=$('nova-beneficiary-patient');if(!pane)return;
 pane.hidden=false;$('nova-beneficiary-empty').hidden=true;
 const type=(info&&novaBeneficiaryLabels[info.beneficiary_type])?info.beneficiary_type:'primary';
 $('nova-beneficiary-type').value=type;
 $('nova-beneficiary-member').value=info?.member_no||'';
 financeState.beneficiaryType=type;
 financeState.memberNo=info?.member_no||'';
 $('nova-beneficiary-save').onclick=async()=>{
   if(!financeState.patient)return notice('اختر المريض أولاً',true);
   try {
     const insurer_id=Number($('finance-insurer').value||0);
     await api('patient-insurance',{
       patient_id:financeState.patient.id,insurer_id,
       member_no:$('nova-beneficiary-member').value,
       beneficiary_type:$('nova-beneficiary-type').value
     });
     financeState.beneficiaryType=$('nova-beneficiary-type').value;
     financeState.memberNo=$('nova-beneficiary-member').value;
     notice('تم حفظ نوع المستفيد وبيانات التأمين');financeQuote();
   }catch(e){notice(e.message,true)}
 };
 $('nova-beneficiary-type').onchange=()=>{financeState.beneficiaryType=$('nova-beneficiary-type').value;financeQuote()};
}
function novaBeneficiaryAdminPanel(){
 const rates=novaInsuranceRates||[];
 const selections=financeState.insurers.map(x=>
  '<option value="'+x.id+'">'+esc(x.name)+'</option>').join('');
 const rows=rates.map(r=>'<tr><td>'+esc(r.insurer_name)+'</td><td>'+
  esc(novaBeneficiaryLabels[r.beneficiary_type]||r.beneficiary_type)+
  '</td><td>'+r.coverage+'%</td><td>'+
  '<button type="button" class="outline" data-nova-bene-edit="'+r.insurer_id+'" data-bene="'+esc(r.beneficiary_type)+'">تعديل</button></td></tr>');
 return panel('تغطية التأمين حسب صلة القرابة',
  '<p class="help">كل شركة لها نسبة افتراضية؛ ضع استثناءات للمشترك والزوج/الزوجة والأبناء والأب والأم. الأولوية لاستثناء الخدمة ثم القسم ثم نوع المستفيد ثم نسبة الشركة الافتراضية. النسب السابقة محفوظة داخل الفواتير.</p>'+
  '<form class="form" id="nova-beneficiary-rate-form"><label>شركة التأمين<select name="insurer_id" id="nova-beneficiary-insurer">'+selections+
  '</select></label><label>نوع المستفيد<select name="beneficiary_type" id="nova-beneficiary-kind">'+novaBeneficiaryOptions()+
  '</select></label><label>التغطية %<input name="coverage" id="nova-beneficiary-coverage" type="number" min="0" max="100" step="1" value="0" required></label>'+
  '<div class="actions"><button class="primary" type="submit">حفظ النسبة</button>'+
  '<button class="outline" type="button" id="nova-beneficiary-inherit">إلغاء الاستثناء والعودة للنسبة الافتراضية</button></div></form>'+
  table(['شركة التأمين','نوع المستفيد','التغطية','إجراء'],rows));
}
let novaInsuranceRates=null;
const novaOriginalFinanceSettings=viewFinanceSettings;
viewFinanceSettings=function(){return novaOriginalFinanceSettings()+novaBeneficiaryAdminPanel()};
const novaOriginalWireSettings=wireFinanceSettings;
wireFinanceSettings=function(){
 novaOriginalWireSettings();
 if(state.role!=='admin')return;
 const formEl=$('nova-beneficiary-rate-form');
 if(!formEl)return;
 const refresh=()=>{api('nova-beneficiary-rates').then(rows=>{
   novaInsuranceRates=rows;if(state.section==='services-admin')navigate('services-admin')
 }).catch(e=>notice(e.message,true))};
 if(novaInsuranceRates===null){refresh();return}
 form('nova-beneficiary-rate-form',async f=>{
   await api('nova-beneficiary-rate',{insurer_id:Number(f.get('insurer_id')),
     beneficiary_type:String(f.get('beneficiary_type')),coverage:Number(f.get('coverage'))});
   notice('تم حفظ تغطية نوع المستفيد');refresh();
 });
 $('nova-beneficiary-inherit').onclick=async()=>{
   if(!confirm('إلغاء استثناء التغطية لهذا النوع والعودة إلى نسبة الشركة؟'))return;
   try{await api('nova-beneficiary-rate',{insurer_id:Number($('nova-beneficiary-insurer').value),
       beneficiary_type:$('nova-beneficiary-kind').value,inherit:true});
       notice('تمت العودة لتغطية الشركة الافتراضية');refresh()}
   catch(e){notice(e.message,true)}
 };
 document.querySelectorAll('[data-nova-bene-edit]').forEach(b=>b.onclick=()=>{
   $('nova-beneficiary-insurer').value=b.dataset.novaBeneEdit;
   $('nova-beneficiary-kind').value=b.dataset.bene;
   const x=novaInsuranceRates.find(x=>x.insurer_id===Number(b.dataset.novaBeneEdit)&&
     x.beneficiary_type===b.dataset.bene);
   if(x)$('nova-beneficiary-coverage').value=x.coverage;
   formEl.scrollIntoView({behavior:'smooth',block:'center'});
 });
};
"""
def finance_ui(s):
    s = one(s,
      "const info=await api('patient-insurance/'+p.id);financeState.insuranceId=String(info.insurer_id||0);",
      "const info=await api('patient-insurance/'+p.id);financeState.insuranceId=String(info.insurer_id||0);")
    s = one(s,
      "$('finance-insurer').value=financeState.insuranceId;patientOptions();financeQuote()",
      "$('finance-insurer').value=financeState.insuranceId;novaBenefitSelected(info);patientOptions();financeQuote()")
    s = one(s,
      "member_no:val('new-patient-card')})",
      "member_no:val('new-patient-card'),beneficiary_type:$('nova-new-beneficiary')?.value||'primary'})")
    s = one(s,
      "financeState.insuranceId=insurer;$('finance-insurer').value=insurer;",
      "financeState.insuranceId=insurer;$('finance-insurer').value=insurer;\n    novaBenefitSelected({beneficiary_type:$('nova-new-beneficiary')?.value||'primary',member_no:val('new-patient-card')});")
    s = one(s,
      "services:[...financeState.chosen],insurer_id:Number($('finance-insurer').value||0)});",
      "services:[...financeState.chosen],insurer_id:Number($('finance-insurer').value||0),beneficiary_type:$('nova-beneficiary-type')?.value||financeState.beneficiaryType||'primary'});")
    s = one(s,
      "insurer_id:Number(f.get('insurer_id')||0),member_no:f.get('member_no'),note:f.get('note')});",
      "insurer_id:Number(f.get('insurer_id')||0),member_no:f.get('member_no')||financeState.memberNo||'',beneficiary_type:$('nova-beneficiary-type')?.value||financeState.beneficiaryType||'primary',note:f.get('note')});")
    s += "\n" + FRONTEND
    return s
change("hospital/static/finance-ui.js", finance_ui)
print("NOVA_BATCH06_INSURANCE_PATCH_APPLIED")
