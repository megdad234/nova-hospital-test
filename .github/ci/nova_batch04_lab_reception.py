# coding: utf-8
"""NOVA batch 04: laboratory workspace/report + reception workspace.
Patches only CI-extracted sources. Fails on unexpected code drift.
Never opens or writes a customer's installed database.
"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
done=[]
def decode(s):
    return s.replace("~",chr(96)).replace("@{","$"+"{")
def sub(path,old,new,count=1):
    file=ROOT/path
    s=file.read_text(encoding="utf-8")
    old,new=decode(old),decode(new)
    if s.count(old)!=count:
        raise RuntimeError("NOVA04_ANCHOR %s: %d/%d %s"%(path,s.count(old),count,old[:85]))
    file.write_text(s.replace(old,new),encoding="utf-8")
    done.append(path)
def regex(path,pattern,repl,count=1):
    file=ROOT/path;s=file.read_text(encoding='utf-8')
    new,n=re.subn(decode(pattern),lambda m:decode(repl),s,count=count,flags=re.M)
    if n!=count:raise RuntimeError('NOVA04_REGEX_ANCHOR '+path+': '+str(n))
    file.write_text(new,encoding='utf-8');done.append(path)
def add(path,s):
    file=ROOT/path;orig=file.read_text(encoding='utf-8')
    if 'NOVA04_EXTENSION' in orig:raise RuntimeError('NOVA04 already applied: '+path)
    file.write_text(orig+"\n"+decode(s),encoding="utf-8");done.append(path)

# Laboratory: categories already stored on tests; persist parameter sections
# without changing or overwriting existing published result values.
sub("hospital/lab.py",
 "'hospital_phone':'', 'lab_title'",
 "'hospital_phone':'', 'hospital_website':'', 'lab_title'")
sub("hospital/lab.py",
 "    c.executescript(SCHEMA)\n    cols={row['name'] for row in c.execute('PRAGMA table_info(hospital_lab_tests)')}",
 """    c.executescript(SCHEMA)
    for table in ('hospital_lab_parameters','hospital_lab_lines'):
        existing={r['name'] for r in c.execute('PRAGMA table_info('+table+')')}
        if 'section_name' not in existing:
            c.execute("ALTER TABLE "+table+" ADD COLUMN section_name TEXT NOT NULL DEFAULT ''")
    cols={row['name'] for row in c.execute('PRAGMA table_info(hospital_lab_tests)')}""")

sub("hospital/lab.py",
 "        for key,val in DEFAULT_BRAND.items():",
 """        # Apply section names to new seed rows in the same first installation.
        for test_code,groups in lab_catalog.PARAMETER_SECTIONS.items():
            for section,codes in groups.items():
                for code in codes:
                    c.execute('''UPDATE hospital_lab_parameters SET section_name=?
                        WHERE section_name='' AND test_id=(SELECT id FROM hospital_lab_tests WHERE code=?)
                        AND code=?''',(section,test_code,code))
        c.execute('''UPDATE hospital_lab_lines SET section_name=
          COALESCE((SELECT p.section_name FROM hospital_lab_parameters p
                    WHERE p.id=hospital_lab_lines.parameter_id),'')
          WHERE section_name='' AND parameter_id IS NOT NULL''')
        for key,val in DEFAULT_BRAND.items():""")
sub("hospital/lab.py",
 "(item_id,parameter_id,code,name,unit,reference_range) VALUES(?,?,?,?,?,?)",
 "(item_id,parameter_id,code,name,unit,reference_range,section_name) VALUES(?,?,?,?,?,?,?)")
sub("hospital/lab.py",
 "(item_id,p['id'],p['code'],p['name'],p['unit'],select_range(pat,p))",
 "(item_id,p['id'],p['code'],p['name'],p['unit'],select_range(pat,p),p['section_name'])")
add("hospital/lab_catalog.py", """
# NOVA04_EXTENSION — grouping affects input and print layout, not medical reference ranges.
PARAMETER_SECTIONS={
  'URINE':{
    'Macroscopy':('COLOR','APPEAR','SG','PH','PROT','GLUC','KET','BLOOD','NIT','LEU'),
    'Microscopy':('WBC','RBC','EPI','CRYS')},
  'STOOL':{
    'Macroscopy':('COLOR','CONS','MUCUS'),
    'Microscopy':('RBC','PUS','OVA','PARASITE')}
}
""")

# Reception: correction is by patient ID, never by matching name; audit changes.
sub("hospital/core.py","\ndef patients(c, term=''):",
 """
def update_patient(c,actor,data):
    pid=integer(data.get('patient_id'),'رقم الملف',1)
    allowed={'full_name','phone','gender','age_years'}
    if any(k not in allowed|{'patient_id'} for k in data):
        raise ValueError('حقل غير مسموح بتعديله')
    c.execute('BEGIN IMMEDIATE')
    try:
        current=pharmacy.one(c,'SELECT * FROM hospital_patients WHERE id=?',(pid,))
        if not current:raise ValueError('ملف المريض غير موجود')
        updates={}
        if 'full_name' in data:updates['full_name']=safe_text(data,'full_name',160,True)
        if 'phone' in data:updates['phone']=safe_text(data,'phone',35)
        if 'gender' in data:
            value=safe_text(data,'gender',12)
            if value not in ('','male','female'):raise ValueError('الجنس غير معروف')
            updates['gender']=value
        if 'age_years' in data:
            value=data.get('age_years')
            updates['age_years']=None if value is None or str(value).strip()=='' else integer(value,'العمر')
            if updates['age_years'] is not None and updates['age_years']>125:raise ValueError('العمر غير صحيح')
        if updates:
            c.execute('UPDATE hospital_patients SET '+','.join(k+'=?' for k in updates)+' WHERE id=?',
                      (*updates.values(),pid))
            track(c,actor['id'],'patient_corrected',pid,
                  {'before':{k:current[k] for k in updates},'after':updates})
        c.execute('COMMIT')
    except Exception:c.execute('ROLLBACK');raise
    return dict(pharmacy.one(c,'SELECT * FROM hospital_patients WHERE id=?',(pid,)))

def patient_activity(c,pid):
    patient=pharmacy.one(c,'SELECT id,patient_no,full_name FROM hospital_patients WHERE id=?',(pid,))
    if not patient:raise ValueError('ملف المريض غير موجود')
    result=[]
    for row in pharmacy.query(c,'''SELECT id,invoice_no,status,created_at FROM nova_invoices
                                WHERE patient_id=? ORDER BY id DESC LIMIT 30''',(pid,)):
        names=pharmacy.query(c,'SELECT name FROM nova_invoice_lines WHERE invoice_id=?',(row['id'],))
        result.append({'kind':'services','no':row['invoice_no'],'status':row['status'],
                       'created_at':row['created_at'],'services':[x['name'] for x in names]})
    for row in pharmacy.query(c,'''SELECT id,order_no,status,created_at FROM hospital_orders
                                WHERE patient_id=? ORDER BY id DESC LIMIT 30''',(pid,)):
        # Lab requests that belong to a unified invoice are not presented twice.
        if 'lab_order_id' in {v['name'] for v in c.execute('PRAGMA table_info(nova_invoices)')} and pharmacy.one(c,'SELECT 1 AS n FROM nova_invoices WHERE lab_order_id=? LIMIT 1',(row['id'],)):
            continue
        names=pharmacy.query(c,'SELECT test_name FROM hospital_order_items WHERE order_id=?',(row['id'],))
        result.append({'kind':'laboratory','no':row['order_no'],'status':row['status'],
                       'created_at':row['created_at'],'services':[x['test_name'] for x in names]})
    result.sort(key=lambda x:x['created_at'],reverse=True)
    return {'patient':dict(patient),'visits':result[:30]}

def patients(c, term=''):""")
# Finance invoice relation may instead be stored under another link: the next step validates schema.
# Endpoint roles keep receptionist away from payment references and other cashier-only data.
regex("hospital/gateway.py",
 r"(?=^ {20}if path=='/api/hospital/patients':\n +core\.require_role\(role,'admin','reception','lab'\);term=)",
 """                    if path.startswith('/api/hospital/patient-activity/'):
                         core.require_role(role,'admin','reception')
                         return self.reply(core.patient_activity(c,core.integer(path.rsplit('/',1)[-1],'المريض',1)))
""")
regex("hospital/gateway.py",
 r"(?=^ {20}if path=='/api/hospital/patients':\n +core\.require_role\(role,'admin','reception','lab'\);return self\.reply\(core\.create_patient)",
 """                    if path=='/api/hospital/patient-edit':
                         core.require_role(role,'admin','reception')
                         return self.reply(core.update_patient(c,user,data))
""")

# Laboratory picker: existing search, selected checkboxes, favorites and totals are retained.
sub("hospital/static/app.js",
 "function testChoices(){const list=state.tests.filter(t=>searchTest(t,state.filter));",
 "function testChoices(){const list=state.tests.filter(t=>searchTest(t,state.filter)&&(!state.labCategory||t.category===state.labCategory));")
# Categories as easy-to-scan filters; native existing checkbox handlers are used on the initial render.
sub("hospital/static/app.js",
 """<div class="quick-tests">@{state.tests.filter(t=>t.popular)""",
 """<div class="nova-lab-categories"><label>قسم الفحوصات<select id="nova-lab-category" onchange="novaChooseLabCategory(this.value)"><option value="">كل الأقسام</option>@{[...new Set(state.tests.map(t=>t.category).filter(Boolean))].sort().map(c=>~<option value="@{esc(c)}" @{state.labCategory===c?'selected':''}>@{esc(c)}</option>~).join('')}</select></label></div><h3>الفحوصات الشائعة</h3><div class="quick-tests">@{state.tests.filter(t=>t.popular)""")
add("hospital/static/app.js", """
// NOVA04_EXTENSION — category filter using existing medical test selection IDs.
function novaChooseLabCategory(category){
  state.labCategory=category;
  const box=$('test-options');
  if(!box)return;
  box.innerHTML=testChoices();
  box.querySelectorAll('[data-pickcheck]').forEach(el=>el.addEventListener('change',()=>{
    const id=Number(el.dataset.pickcheck);
    if(el.checked)state.selected.add(id);else state.selected.delete(id);
    const count=$('selected-count');if(count)count.textContent=state.selected.size+' فحص محدد';
  }));
}
// Structured inputs and printouts use the SAME saved section names.
// Fixed choices only where the result has a well-defined categorical meaning.
// Preserve every existing saved value, including values outside these options.
function novaLabResultControl(x){
  const code=String(x.code||'').trim().toUpperCase(),name=String(x.name||'').toLowerCase();
  const section=String(x.section_name||'').toLowerCase();
  const panel=String(x.test_code||x.test_name||x.panel_code||x.panel_name||'').toLowerCase();
  const context=section+' '+panel;
  const urine=/\\burine\\b|urinalysis|\\busa\\b|بول/.test(context);
  const stool=/\\bstool\\b|faec|fecal|براز/.test(context);
  let choices=null,allowOther=false;
  if((code==='PARASITE' && /malaria|parasite detected|blood film|b\\.f/.test(name+' '+panel))||
     (code==='MP' && /malaria|parasite|blood film|b\.f/.test(name+' '+panel)))
    {choices=['No malaria parasite seen','Malaria parasite seen','Other'];allowOther=true;}
  else if(code==='SPECIES' && name.includes('plasmodium'))
    choices=['P. falciparum','P. vivax','P. malariae','P. ovale','P. knowlesi','Mixed infection','Not identified'];
  if(code==='DENSITY'&&/malaria|blood film|b\\.f/.test(name+' '+panel))
    {choices=['(+)','(++)','(+++)','(++++)','Hyper parasitemia','Other'];allowOther=true;}
  else if((code==='TYPE'||code==='SPECIES')&&/malaria|plasmodium|blood film|b\\.f/.test(name+' '+panel))
    {choices=['P. falciparum','P. malariae','P. ovale','P. vivax','P. knowlesi','Mixed infection','Other'];allowOther=true;}
  else if(code==='STAGE'&&/malaria|parasite|blood film|b\\.f/.test(name+' '+panel))
    {choices=['Ring','Late Trophozoite','Gametocyte','Schizont','Ring and Gametocyte','Other'];allowOther=true;}
  if(urine){
    if(/^(WBC|RBC|PUS)$/.test(code)||/pus cells|red blood cells|r\\.b\\.c/.test(name)){
      // Microscopic cell counts are free-text ranges such as 2-4 / HPF.
    }
    else if(code==='NIT')choices=['Nil','Positive','Negative'];
    else if(code==='LEU')choices=['Negative','Trace','Positive'];
    else if(code==='KET'||/ketone/.test(name))choices=['Nil','Trace','(+)','(++)','(+++)','Negative','+','++','+++'];
    else if(/^(PRO|PROT|PROTEIN|GLU|GLUC|GLUCOSE|BLOOD|BLD)$/.test(code))
      choices=['Nil','Trace','(+)','(++)','(+++)','(++++)','Negative','+','++','+++','++++'];
    else if(/^(COLOR|COLOUR)$/.test(code)||/colour|color/.test(name))
      {choices=['Yellow','Deep Yellow','Pale Yellow','Reddish','Brownish','Black','Amber','Dark','Other'];allowOther=true;}
    else if(/^(APPEARANCE|APPEAR|CLARITY)$/.test(code)||/appearance|clarity/.test(name))
      {choices=['Clear','Slightly cloudy','Cloudy','Turbid','Other'];allowOther=true;}
    else if(/^(BIL|BILI|BILIRUBIN|URO|UROBILINOGEN|YEAST|MUC|THREADS)$/.test(code)||/bilirubin|urobilinogen|yeast|mucous thread/.test(name))
      {choices=['Nil','Trace','(+)','(++)','(+++)','(++++)','Present','Other'];allowOther=true;}
    else if(/^(CRYS|CRYSTALS)$/.test(code)||/crystal/.test(name))
      {choices=['Nil','Calcium oxalate','Uric acid','Triple phosphate','Amorphous urates','Amorphous phosphates','Other'];allowOther=true;}
    else if(/^(CRYS|EPI|CAST|BACT|PARASITE)$/.test(code)||/crystal|cast|bacteria|epithelial|parasite/.test(name))
      {choices=['Nil','Few','Moderate','Many','(+)','(++)','(+++)','Absent','Present','Other'];allowOther=true;}
  }else if(stool){
    if(code==='MUCUS')choices=['Absent','Present'];
    else if(/colour|color/.test(name)){choices=['Brown','Yellow','Green','Black','Red','Other'];allowOther=true;}
    else if(code==='CONS'||/consistency|appearance/.test(name)){choices=['Formed','Soft','Loose','Watery','Other'];allowOther=true;}
    else if(/^(OVA|PARASITE|CYST|WORM|OCCULT_BLOOD)$/.test(code)||/ova|cyst|parasite|worm|blood/.test(name)){choices=['Not seen','Seen','Other'];allowOther=true;}
  }
  // Qualitative assays across the wider catalogue: suggest conventional reporting
  // terms without forcing a choice or replacing laboratory-specific interpretations.
  // Never classify generic RESULT fields as qualitative by name alone.
  if(!choices && !urine && !stool){
    const assay=(panel+' '+name).toLowerCase();
    const qualitativeCode=/^(HCG|PREGNANCY|HBSAG|HCV|HIV|VDRL|RPR|DENGUE|MALARIA_RDT|ICT_TYPHOID|HP_STOOL|HP_SERUM|RF_LATEX|ASO_LATEX)$/i.test(code);
    const qualitativeName=/\\b(qualitative|screening|rapid test|antigen detected|antibody detected|reactive|non-reactive|pregnancy test|sickling test)\\b/.test(assay);
    const resultField=/^(RESULT|SCREEN|SCREENING|AG|AB|HBSAG|HCG|PREGNANCY|VDRL|RPR)$/i.test(code);
    if(qualitativeCode||(resultField&&qualitativeName)){
      choices=/pregnancy|\\bhcg\\b/.test(assay)?['Positive','Negative','Indeterminate']:
        /sickling/.test(assay)?['Positive','Negative','Indeterminate']:
        ['Negative','Positive','Non-reactive','Reactive','Indeterminate'];
      allowOther=true;
    }
  }
  // Existing results, including unusual microscopy descriptions, remain editable.
  // Mixed fields use a list of suggestions, never a restrictive dropdown.
  const value=String(x.value??'');
  const attrs=' data-line="'+esc(x.id)+'" aria-label="نتيجة '+esc(x.name)+'"';
  // WBC/RBC in urine or stool are microscopy ranges (e.g. 2-4 /HPF), not CBC decimals.
  const microscopyCount=(urine||stool)&&/^(WBC|RBC|PUS)$/.test(code);
  // Catalogue-wide input hints: measurable analytes use decimal keyboards,
  // while microscopy ranges, titres and qualitative assays remain unrestricted.
  // This is an input hint only, never a medical interpretation or validation.
  const unit=String(x.unit||'').trim();
  const numericUnit=/^(?:mg\\/d[lL]|g\\/d[lL]|mmol\\/L|µmol\\/L|umol\\/L|mEq\\/L|ng\\/mL|pg\\/mL|µg\\/dL|ug\\/dL|IU\\/L|U\\/L|mIU\\/L|mU\\/L|fL|pg|%|mm\\/hr|mm\\/h)$/i.test(unit);
  const numericAnalyte=/^(?:GLUCOSE|RBS|FBS|FPG|PPBS|UREA|BUN|CREATININE|CREAT|URIC|URIC_ACID|NA|K|CL|CA|CALCIUM|MG|MAGNESIUM|PHOS|PHOSPHORUS|ALT|AST|ALP|GGT|BILIRUBIN|TBIL|DBIL|ALBUMIN|TOTAL_PROTEIN|CHOLESTEROL|TRIGLYCERIDES|TG|HDL|LDL|VLDL|TSH|T3|T4|FT3|FT4|HBA1C|CRP|ESR|PSA|AFP|AMH|INSULIN|C_PEPTIDE|PTH|VITD|B12|IRON|FERRITIN|TIBC|PT|PTT|INR|D_DIMER|TROPONIN|AMYLASE|LIPASE)$/i.test(code);
  const microscopyField=(urine||stool)&&/^(WBC|RBC|PUS|EPI|CRYS|CAST|BACT|YEAST)$/.test(code);
  const numeric=!microscopyCount&&!microscopyField&&!choices&&(
    /^(FASTING|TIME_30|TIME_60|TIME_90|TIME_120|TIME_150|TIME_180|TIME_240|WBC|RBC|HGB|HB|HCT|MCV|MCH|MCHC|PLT|PLATELETS|RDW|NEUT|LYMPH|MONO|EOS|BASO)$/.test(code)||
    (urine&&/^(SG|PH)$/.test(code))||numericUnit||numericAnalyte
  );
  if(choices&&allowOther){
    const listId='nova-lab-choices-'+String(x.id).replace(/[^a-zA-Z0-9_-]/g,'');
    return '<input list="'+listId+'"'+attrs+' value="'+esc(value)+'" maxlength="4000" autocomplete="off" dir="auto">'+
      '<datalist id="'+listId+'">'+choices.map(v=>'<option value="'+esc(v)+'"></option>').join('')+'</datalist>';
  }
  if(choices){
    if(value&&!choices.includes(value))choices=[value,...choices];
    return '<select aria-label="نتيجة '+esc(x.name)+'" onchange="this.nextElementSibling.value=this.value"><option value="">— اختر النتيجة —</option>'+
      choices.map(v=>'<option value="'+esc(v)+'"'+(v===value?' selected':'')+'>'+esc(v)+'</option>').join('')+
      '</select><input type="hidden"'+attrs+' value="'+esc(value)+'">';
  }
  return '<input'+attrs+' value="'+esc(value)+'" maxlength="4000" autocomplete="off" dir="auto"'+
    (numeric?' inputmode="decimal"':'')+'>';
}
function novaLabResultKeyboard(event){
  const target=event.target;
  if(!target||!target.matches||!target.matches('input[data-line],select'))return;
  const table=target.closest('table');
  if(!table||!table.querySelector('input[data-line]'))return;
  if(target.tagName==='SELECT'&&!target.nextElementSibling?.matches('input[data-line]'))return;
  if(event.altKey||event.metaKey||event.isComposing)return;
  if(!['Enter','ArrowDown','ArrowUp'].includes(event.key))return;
  // Native up/down must remain available to select an option or edit text.
  // Ctrl+up/down provides explicit navigation for text fields.
  if(event.key!=='Enter'&&!event.ctrlKey)return;
  // Enter advances from a closed select; native arrow keys still select options.
  const fields=[...table.querySelectorAll('input[data-line]:not([type="hidden"]),select')]
    .filter(el=>el.tagName!=='SELECT'||el.nextElementSibling?.matches('input[data-line]'));
  const index=fields.indexOf(target);
  if(index<0)return;
  const step=event.key==='ArrowUp'||(event.key==='Enter'&&event.shiftKey)?-1:1;
  const next=fields[index+step];
  if(!next)return;
  event.preventDefault();
  next.focus();
}
if(typeof document!=='undefined'&&!window.__novaLabKeyboardBound){
  window.__novaLabKeyboardBound=true;
  document.addEventListener('keydown',novaLabResultKeyboard);
}
function novaLabGroupedRows(lines,editable){
  // Section labels such as Macroscopy/Microscopy are not panel identifiers.
  // Infer only from distinctive parameter signatures when the API omits parent metadata.
  const codes=new Set((lines||[]).map(x=>String(x.code||'').trim().toUpperCase()));
  const urineSignature=(['NIT','LEU','KET'].filter(c=>codes.has(c)).length>=2)||(['NIT','LEU','KET','PROT','GLUC','CRYS','EPI'].filter(c=>codes.has(c)).length>=3)||(['NIT','PROT','GLUC'].filter(c=>codes.has(c)).length>=2)||(['COLOR','APPEAR','SG','PH','PROT','GLUC','WBC','RBC','CRYS','EPI'].filter(c=>codes.has(c)).length>=4&&['SG','PH','CRYS','EPI'].some(c=>codes.has(c)));
  const stoolSignature=(codes.has('MUCUS')&&
    [...codes].some(c=>/^(OVA|CYST|WORM|PARASITE|CONS|CONSISTENCY|OCCULT_BLOOD)$/.test(c)))||
    (['CONS','CONSISTENCY'].some(c=>codes.has(c))&&['OVA','CYST','WORM'].some(c=>codes.has(c)));
  const inferredPanel=urineSignature?'URINE':stoolSignature?'STOOL':'';
  const groups=new Map();
  for(const line of lines||[]){
    const section=line.section_name||'';
    if(!groups.has(section))groups.set(section,[]);
    groups.get(section).push(line);
  }
  return [...groups.entries()].map(([section,rows])=>
    (section?'<tr class="nova-lab-section"><th colspan="4">'+esc(section)+'</th></tr>':'')+
    rows.map(x=>'<tr><td><b>'+esc(x.name)+'</b></td>'+
      '<td>'+(editable?novaLabResultControl({...x,test_code:x.test_code||inferredPanel}):'<b dir="auto">'+esc(x.value)+'</b>')+'</td>'+
      '<td dir="ltr">'+(esc(x.unit)||'—')+'</td>'+
      '<td dir="ltr" class="reference">'+(esc(x.reference_range)||'—')+'</td></tr>').join('')
  ).join('');
}
""")
# Make both the lab data entry and the read-only mode use section rows.
regex("hospital/static/app.js",
      r"\$\{lines\.map\(x=>~<tr><td><b>\$\{esc\(x\.name\)\}</b>.*?\.join\(''\)\}",
      "@{novaLabGroupedRows(lines,true)}")
# The hospital website is optional; address remains stored for other documents but is not shown on labs.
sub("hospital/static/app.js",
 """<label>رقم التواصل<input name="hospital_phone" maxlength="200" value="@{esc(b.hospital_phone)}"></label>""",
 """<label>رقم التواصل<input name="hospital_phone" maxlength="200" value="@{esc(b.hospital_phone)}"></label><label>الموقع الإلكتروني — يظهر أسفل نتيجة المعمل<input name="hospital_website" maxlength="200" value="@{esc(b.hospital_website||'')}"></label>""")

# Replace report renderer in one operation because all its HTML is one JS line.
regex("hospital/static/app.js",r"^async function printReport\(id\)\{[\s\S]*?(?=^(?:async )?function [A-Za-z_$][\w$]*\()",
 """async function printReport(id){
  try{
    const d=await api('lab/report/'+id),brand=d.brand||{};
    const logo=brand.hospital_logo?~<img class="print-logo" src="@{esc(brand.hospital_logo)}" alt="شعار المستشفى">~:'';
    const name=brand.hospital_name||'اسم المستشفى',english=brand.hospital_name_en||'';
    const timestamp=String(d.print_time||'').replace('T',' ').slice(0,19);
    const tests=(d.items||[]).filter(item=>(item.lines||[]).some(x=>String(x.value||'').trim())).map(item=>{
      const groups=new Map();
      for(const line of (item.lines||[]).filter(x=>String(x.value||'').trim())){
        const key=line.section_name||'';
        if(!groups.has(key))groups.set(key,[]);
        groups.get(key).push(line);
      }
      const rows=[...groups.entries()].map(([section,items])=>
        (section?~<tr class="nova-lab-section"><th colspan="4">@{esc(section)}</th></tr>~:'')+
        items.map(x=>~<tr><td>@{esc(x.name)}</td><td><strong dir="auto">@{esc(x.value)}</strong></td><td dir="ltr">@{esc(x.unit)||'—'}</td><td dir="ltr">@{esc(x.reference_range)||'—'}</td></tr>~).join('')
      ).join('');
      return ~<section class="lab-print-test"><h3 class="print-test">@{esc(item.test_name)}</h3><table class="lab-results"><thead><tr><th>Test</th><th>Result</th><th>Unit</th><th>Reference Range</th></tr></thead><tbody>@{rows}</tbody></table></section>~;
    }).join('');
    if(!tests.trim())throw new Error('لا توجد نتائج مدخلة قابلة للطباعة لهذا الطلب');
    const html=~<article class="lab-print nova-clinical-print" dir="rtl">
      <header class="print-head">@{logo}<div class="print-hospital"><h2>@{esc(name)}</h2>
      @{english?~<p lang="en" dir="ltr">@{esc(english)}</p>~:''}
      <h3>المختبر / Laboratory</h3></div></header>
      <div class="print-patient"><b>اسم المريض: @{esc(d.patient_name)}</b>
      <span>رقم الملف: @{esc(d.patient_no)}</span>
      @{d.age_years!==null&&d.age_years!==undefined?~<span>العمر: @{esc(d.age_years)} سنة</span>~:''}
      @{d.gender?~<span>الجنس: @{d.gender==='male'?'ذكر':'أنثى'}</span>~:''}
      <span>رقم الطلب: @{esc(d.order_no)}</span><span>التاريخ: @{esc(timestamp)}</span></div>
      @{tests}
      
      <footer class="print-foot"><span>@{esc(brand.hospital_phone||'')}&nbsp;&nbsp; @{esc(brand.hospital_website||'')}</span>
      <small>Powered by NOVA Hospital System</small></footer></article>~;
    const area=$('print-area');if(!area)throw new Error('منطقة الطباعة غير متاحة، أعد فتح شاشة المعمل');area.innerHTML=html;
    document.body.classList.add('printing-lab');
    const cleanup=()=>{document.body.classList.remove('printing-lab');area.innerHTML='';window.removeEventListener('afterprint',cleanup)};
    window.addEventListener('afterprint',cleanup,{once:true});
    try{
      await Promise.all([...area.querySelectorAll('img')].map(x=>x.decode?.().catch(()=>{})||Promise.resolve()));
      window.print();
    }catch(printError){cleanup();throw printError}
  }catch(e){notice(e.message,true)}
}""")
# Reception summary, collapsed registration, selected patient history and corrections.
sub("hospital/static/finance-ui.js",
 "  return ~<div class=\"split\">@{panel('المريض'",
 "  return ~@{novaReceptionSummary()}<div class=\"split\">@{panel('المريض'")
sub("hospital/static/finance-ui.js",
 """@{panel('تسجيل مريض جديد — اختياري',financePatientForm())}</div>""",
 """@{panel('تسجيل مريض جديد — اختياري',~<details class="nova-reception-new" id="nova-new-patient"><summary>+ فتح استمارة مريض جديد</summary>@{financePatientForm()}</details>~)}</div>""")
sub("hospital/static/finance-ui.js",
 """</div>~)}@{panel('تسجيل مريض جديد""",
 """</div><div id="nova-patient-activity" class="nova-patient-activity"></div>~)}@{panel('تسجيل مريض جديد""")
sub("hospital/static/finance-ui.js",
 """@{panel('آخر الطلبات',invoiceTable(financeState.invoices.filter(x=>x.status==='pending').slice(0,25)))}""",
 """@{panel('طلبات اليوم وحالتها',invoiceTable(financeState.invoices.filter(x=>String(x.created_at||'').slice(0,10)===new Date().toLocaleDateString('sv-SE')).slice(0,30)))}""")
sub("hospital/static/finance-ui.js",
 """<small dir="ltr">@{esc(p.patient_no)}</small>""",
 """<small dir="ltr">@{esc(p.patient_no)}</small><small>@{esc(p.phone||'بدون هاتف')} @{p.age_years!==null&&p.age_years!==undefined?' · '+esc(p.age_years)+' سنة':''}</small>""")
sub("hospital/static/finance-ui.js",
 "$('finance-insurer').value=financeState.insuranceId;patientOptions();financeQuote()});",
 "$('finance-insurer').value=financeState.insuranceId;patientOptions();financeQuote();novaReceptionPatientCard(p)});")
sub("hospital/static/finance-ui.js",
 "notice('تم تسجيل المريض');patientOptions();financeQuote()",
 "notice('تم تسجيل المريض');patientOptions();financeQuote();novaReceptionPatientCard(p)")
add("hospital/static/finance-ui.js", """
// NOVA04_EXTENSION — receptionist view is intentionally separate from cashier amounts/references.
function novaReceptionSummary(){
  const today=new Date().toLocaleDateString('en-CA');
  const rows=financeState.invoices.filter(x=>String(x.created_at||'').slice(0,10)===today);
  const pending=rows.filter(x=>x.status==='pending').length;
  return ~<section class="nova-reception-hero">
    <div><strong>مكتب الاستقبال</strong><p>ابحث عن المريض أولاً، ثم أنشئ طلب خدمات جديد.</p></div>
    <div class="nova-reception-metrics">
      <span>الطلبات المعروضة اليوم <b>@{rows.length}</b></span>
      <span>بانتظار الكاشير <b>@{pending}</b></span>
      <span>تمت التسوية <b>@{rows.filter(x=>x.status==='settled').length}</b></span>
    </div>
  </section>~;
}
async function novaReceptionPatientCard(patient){
 const box=$('nova-patient-activity');if(!box)return;
 box.innerHTML='<p class="muted">جاري فتح سجل المريض...</p>';
 try{
  const info=await api('patient-activity/'+patient.id);
  if(financeState.patient?.id!==patient.id)return;
  const p=financeState.patient;
  const status={pending:'بانتظار الدفع',settled:'تم الدفع',paid:'تم الدفع',completed:'مكتمل',void:'ملغى'};
  const visits=(info.visits||[]).map(v=>
    ~<tr><td dir="ltr">@{esc(v.no)}</td><td>@{esc((v.services||[]).join('، '))}</td>
     <td>@{esc(String(v.created_at||'').replace('T',' ').slice(0,16))}</td>
     <td><span class="tag @{v.status==='pending'?'orange':'green'}">@{esc(status[v.status]||v.status)}</span></td></tr>~).join('');
  box.innerHTML=~<div class="nova-profile">
    <div class="panel-head"><h3>@{esc(p.full_name)}</h3><span class="tag">@{esc(p.patient_no)}</span></div>
    <p>الهاتف: @{esc(p.phone||'غير مسجل')} · العمر: @{p.age_years??'—'}</p>
    <details><summary>تصحيح بيانات المريض</summary>
      <form id="nova-patient-edit" class="form">
      <label>الاسم<input name="full_name" maxlength="160" required value="@{esc(p.full_name)}"></label>
      <label>الهاتف<input name="phone" maxlength="35" value="@{esc(p.phone||'')}"></label>
      <label>العمر (اختياري)<input name="age_years" type="number" min="0" max="125" value="@{esc(p.age_years??'')}"></label>
      <label>الجنس<select name="gender"><option value="">غير محدد</option>
      <option value="male" @{p.gender==='male'?'selected':''}>ذكر</option>
      <option value="female" @{p.gender==='female'?'selected':''}>أنثى</option></select></label>
      <div class="actions"><button type="submit" class="primary">حفظ التصحيح</button></div>
      </form></details>
    <h4>الطلبات والزيارات السابقة</h4>
    <div class="table-wrap"><table><thead><tr><th>الرقم</th><th>الخدمات</th><th>التاريخ</th><th>الحالة</th></tr></thead>
    <tbody>@{visits||'<tr><td colspan="4">ما في طلبات سابقة</td></tr>'}</tbody></table></div>
  </div>~;
  form('nova-patient-edit',async data=>{
    const changed=await api('patient-edit',{patient_id:p.id,...Object.fromEntries(data)});
    const idx=state.patients.findIndex(x=>x.id===p.id);
    if(idx!==-1)state.patients[idx]=changed;
    financeState.patient=changed;
    $('finance-selected-patient').textContent='المريض: '+changed.full_name+' — '+changed.patient_no;
    patientOptions();notice('تم تصحيح بيانات المريض');await novaReceptionPatientCard(changed);
  });
 }catch(e){box.textContent='تعذر تحميل ملف المريض: '+e.message}
}
""")

# Premium CSS: use existing green NOVA design system, not a new app.
add("hospital/static/style.css", """
/* NOVA04_EXTENSION — reception and laboratory */
.nova-reception-hero{background:linear-gradient(120deg,#0b594f,#127866);color:#fff;display:flex;justify-content:space-between;gap:18px;align-items:center;padding:22px 26px;border-radius:18px;box-shadow:0 8px 22px #093c301c}
.nova-reception-hero strong{font-size:1.34rem}.nova-reception-hero p{margin:6px 0 0;opacity:.88}
.nova-reception-metrics{display:flex;gap:12px;flex-wrap:wrap}.nova-reception-metrics span{display:grid;gap:5px;padding:10px 16px;border-radius:12px;background:#ffffff20;font-size:.82rem}
.nova-reception-metrics b{font-size:1.3rem}.nova-reception-new>summary,.nova-profile details>summary{color:#096b5e;font-weight:750;cursor:pointer;padding:12px}
.nova-reception-new[open]>summary{margin-bottom:12px}.nova-profile{border:1px solid #cee5dc;border-radius:14px;padding:18px;margin-top:15px;background:#f9fdfa}
.nova-profile h4{margin:16px 0 9px}.nova-profile p{font-size:.86rem;color:#45665e}
.nova-patient-activity:empty{display:none}.nova-lab-categories{border:1px solid #d2e6de;padding:10px;border-radius:12px;background:#f6fcf9;margin-bottom:13px}
.nova-lab-categories select{padding:10px;border-radius:9px;border:1px solid #bcd7ca;min-width:220px;margin-inline-start:10px}
.nova-lab-section th{background:#e6f2eb!important;color:#125545;font-weight:850;font-size:.94rem;text-align:start;padding:12px}
.nova-clinical-print .print-head{justify-content:center;text-align:center;border-bottom:2px solid #305d55;padding-bottom:12px}
.nova-clinical-print .print-logo{max-height:85px;max-width:95px;object-fit:contain}
.nova-clinical-print .print-hospital h3{margin:4px 0;font-size:1rem}
.nova-clinical-print .print-foot{font-size:11px;display:flex;flex-direction:column;gap:5px}
.nova-clinical-print .print-foot small{font-size:8px;color:#888}
.nova-clinical-print .lab-print-test{break-inside:avoid}
@media(max-width:900px){.nova-reception-hero{flex-direction:column;align-items:stretch}}
@media print{
  @page nova-lab-report{size:A4 portrait;margin:10mm 12mm}
  body.printing-lab .nova-clinical-print{page:nova-lab-report;width:auto!important;max-width:none!important;min-height:0!important;margin:0!important;padding:0!important;box-shadow:none!important;break-before:auto!important;page-break-before:auto!important}
  body.printing-lab .nova-clinical-print .print-head{margin:0 0 7mm!important;padding:0 0 3mm!important;break-after:avoid-page;page-break-after:avoid}
  body.printing-lab .nova-clinical-print .print-patient{margin:0 0 4mm!important;break-after:avoid-page;page-break-after:avoid}
  body.printing-lab .nova-clinical-print .lab-print-test{break-inside:auto;page-break-inside:auto;margin:0 0 4mm!important}\n  body.printing-lab .nova-clinical-print .lab-print-test .print-test{break-after:avoid-page;page-break-after:avoid;margin-bottom:2mm}
  body.printing-lab .nova-clinical-print .lab-results{width:100%;border-collapse:collapse}
  body.printing-lab .nova-clinical-print .lab-results tr{break-inside:avoid;page-break-inside:avoid}
  body.printing-lab .nova-clinical-print .lab-results thead{display:table-header-group}
  body.printing-lab .nova-clinical-print .print-foot{display:flex!important;position:static!important;margin-top:4mm!important;break-inside:avoid}
}
""")

# Additional end-to-end HTTP acceptance checks on a disposable test database.
qa=ROOT/"tests/test_nova_batch04.py"
if qa.exists():raise RuntimeError('NOVA04 test file already exists')
qa.write_text('''import unittest
import urllib.error
from tests.test_hospital_gateway import HospitalServerFixture

class NovaReceptionAndLabAcceptance(HospitalServerFixture,unittest.TestCase):
    def test_same_patient_name_is_allowed_and_edits_target_only_selected_id(self):
        front=self.make_user('reception','novaReception04')
        p1=front.post('/api/hospital/patients',{'full_name':'Ahmed Common Name','age_years':'30'})
        p2=front.post('/api/hospital/patients',{'full_name':'Ahmed Common Name','age_years':'40'})
        self.assertNotEqual(p1['id'],p2['id'])
        self.assertNotEqual(p1['patient_no'],p2['patient_no'])
        changed=front.post('/api/hospital/patient-edit',{
            'patient_id':p1['id'],'full_name':'Ahmed Corrected Name','phone':'0112345678','age_years':'31'})
        self.assertEqual(changed['patient_no'],p1['patient_no'])
        self.assertEqual(changed['age_years'],31)
        original=next(p for p in front.get('/api/hospital/patients?q=Ahmed') if p['id']==p2['id'])
        self.assertEqual(original['full_name'],'Ahmed Common Name')
        with self.assertRaises(urllib.error.HTTPError) as x:
            front.post('/api/hospital/patient-edit',{'patient_id':p2['id'],'patient_no':'HACK'})
        self.assertEqual(x.exception.code,400)

    def test_reception_history_is_authorized_and_contains_no_payment_references(self):
        front=self.make_user('reception','novaReceptionHistory')
        cashier=self.make_user('cashier','novaRestrictedCashier')
        patient=front.post('/api/hospital/patients',{'full_name':'Synthetic Reception History'})
        s=next(x for x in front.get('/api/hospital/services') if x['code']=='CONS-GP')
        invoice=front.post('/api/hospital/invoices',{'patient_id':patient['id'],'services':[s['key']]})
        history=front.get('/api/hospital/patient-activity/'+str(patient['id']))
        self.assertEqual(history['visits'][0]['no'],invoice['invoice_no'])
        self.assertEqual(history['visits'][0]['status'],'pending')
        self.assertNotIn('bank_reference',history['visits'][0])
        self.assertNotIn('amount',history['visits'][0])
        with self.assertRaises(urllib.error.HTTPError) as x:
            cashier.get('/api/hospital/patient-activity/'+str(patient['id']))
        self.assertEqual(x.exception.code,403)

    def test_lab_sections_are_seeded_and_hospital_website_is_saved(self):
        tests=self.admin.get('/api/hospital/tests')
        for code in ('URINE','STOOL'):
            tid=next(x['id'] for x in tests if x['code']==code)
            profile=self.admin.get('/api/hospital/lab/profile/'+str(tid))
            sections={x['section_name'] for x in profile['parameters']}
            self.assertTrue({'Macroscopy','Microscopy'}.issubset(sections))
        # Verify real API persistence of the expanded malaria panel on a fresh DB.
        malaria_id=next(x['id'] for x in tests if x['code']=='MALARIA')
        malaria=self.admin.get('/api/hospital/lab/profile/'+str(malaria_id))
        codes={p['code'] for p in malaria['parameters']}
        self.assertTrue({'MP','DENSITY','TYPE','STAGE','PARASITE','COMMENTS'}.issubset(codes),
                        'Malaria microscopy template missing persisted fields')
        brand=self.admin.post('/api/hospital/lab/brand',{
          'hospital_name':'مستشفى تجريبي','hospital_name_en':'Synthetic Hospital',
          'hospital_phone':'099999999','hospital_website':'hospital.example'})
        self.assertEqual(brand['hospital_website'],'hospital.example')
        self.assertEqual(self.admin.get('/api/hospital/lab/brand')['hospital_name'],'مستشفى تجريبي')

if __name__=='__main__':unittest.main()
''',encoding="utf-8")
done.append("tests/test_nova_batch04.py")
print("NOVA04_APPLIED",len(done),sorted(set(done)))
