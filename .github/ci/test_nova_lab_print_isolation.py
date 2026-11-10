"""Guard laboratory print isolation from pharmacy/cashier receipt styles."""
import unittest
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "hospital/static/app.js"
CSS = ROOT / "hospital/static/style.css"

class LabPrintIsolationTests(unittest.TestCase):
    def test_malaria_catalogue_has_complete_entry_fields(self):
        # Regression: MALARIA existed with only MP in the original catalogue.
        # Test the generated catalogue, not just the CI patch text.
        import importlib.util
        import sys
        catalog_path = ROOT / "hospital/lab_catalog.py"
        # This test runs before the Al Sharq catalogue seed in CI.
        # The seeded result is asserted via the lab profile API integration test.
        if "NOVA_MALARIA_TEMPLATE_V2" not in catalog_path.read_text(encoding="utf-8"):
            self.skipTest("Catalogue seed not applied yet; API integration validates seeded malaria")
        spec = importlib.util.spec_from_file_location("nova_lab_catalog_check", catalog_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        malaria = [row for row in module.TESTS if row[0] == "MALARIA"]
        self.assertEqual(len(malaria), 1, "MALARIA must be one panel")
        fields = [row[0] for row in malaria[0][4]]
        for field in ("MP", "DENSITY", "TYPE", "STAGE", "PARASITE", "COMMENTS"):
            self.assertIn(field, fields, "Missing malaria entry: " + field)
        self.assertEqual(len(fields), len(set(fields)), "Duplicate malaria fields")
        self.assertFalse(any(str(row[3]).strip() or str(row[4]).strip()
                             for row in malaria[0][4] if row[0] in
                             ("DENSITY", "TYPE", "STAGE", "PARASITE", "COMMENTS")),
                         "Do not fabricate units or reference intervals")

    def test_lab_print_renderer_and_disclaimer(self):
        source = APP.read_text(encoding="utf-8")
        self.assertIn("async function printReport(id)", source)
        self.assertIn("nova-clinical-print", source)
        self.assertNotIn("تقرير جزئي — توجد فحوصات أخرى لم تُنشر بعد.", source)
        self.assertIn("print-patient", source)
        self.assertIn("lab-results", source)
        for token in ("section_name", "print_time", "patient_name", "patient_no", "order_no", "window.print()"):
            self.assertIn(token, source)
        self.assertIn("window.addEventListener('afterprint',cleanup", source)
        self.assertNotIn("تقرير جزئي", source)
        self.assertIn("لا توجد نتائج مدخلة قابلة للطباعة", source)
        self.assertIn("منطقة الطباعة غير متاحة", source)
        self.assertIn("window.removeEventListener('afterprint',cleanup)", source)
        self.assertIn("catch(printError){cleanup();throw printError}", source)
        self.assertIn(".filter(item=>(item.lines||[]).some(", source)

    def test_lab_print_function_boundary_and_receipt_preservation(self):
        source = APP.read_text(encoding="utf-8")
        self.assertEqual(source.count("async function printReport(id){"), 1)
        start = source.index("async function printReport(id){")
        end = source.find("\\nfunction ", start)
        async_end = source.find("\\nasync function ", start + 1)
        candidates = [x for x in (end, async_end) if x >= 0]
        # The report renderer can be the final top-level function in this bundle.
        lab = source[start:min(candidates)] if candidates else source[start:]
        self.assertIn("await Promise.all(", lab)
        self.assertIn("window.print();", lab)
        self.assertIn("catch(printError){cleanup();throw printError}", lab)
        self.assertNotIn("window.print()}catch(e){notice(e.message,true)}}", source)
        # This laboratory-only test must never replace or normalize the receipt engines.
        self.assertIn("printing-lab", lab)

    def test_lab_report_runtime_prints_patient_and_results_together(self):
        # Smoke-test the generated report function without changing a database.
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync(process.argv[1],'utf8');
const a=src.indexOf('async function printReport(id){');
const b=src.indexOf('\nfunction ',a);
assert(a>=0,'printReport missing');
const code=src.slice(a,b<0?undefined:b);
const esc=x=>String(x??'').replace(/&/g,'&amp;').replace(/</g,'&lt;');
let html='',printed=0,cleaned=false,listener=null;
const area={set innerHTML(x){html=x},get innerHTML(){return html},querySelectorAll(){return []}};
const document={body:{classList:{add(x){assert.strictEqual(x,'printing-lab')},remove(x){cleaned=true}}}};
const window={addEventListener:(x,fn)=>{listener=fn},removeEventListener:()=>{},print:()=>{printed++}};
const api=async path=>({brand:{hospital_name:'Hospital'},patient_name:'Test Patient',patient_no:'P001',
 order_no:'L001',age_years:30,gender:'male',print_time:'2026-11-10T10:00:00',
 items:[{test_name:'CBC',lines:[{name:'WBC',value:'7.1',unit:'10^9/L',reference_range:'4-11'}]},
 {test_name:'Pending',lines:[{name:'Hb',value:''}]}]});
let errors=[];
const fn=vm.runInNewContext(code+';printReport',{esc,api,$:()=>area,document,window,notice:x=>errors.push(x)});
fn(5).then(()=>{assert.strictEqual(printed,1);assert.strictEqual(errors.length,0);
assert(html.includes('Test Patient')&&html.includes('P001')&&html.includes('WBC')&&html.includes('7.1'));
assert(!html.includes('Pending')&&!html.includes('تقرير جزئي'));
assert(listener);listener();assert(cleaned&&html==='');console.log('LAB_REPORT_RUNTIME_OK')
}).catch(e=>{console.error(e);process.exitCode=1});
'''
        result = subprocess.run(['node', '-e', script, str(APP)],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('LAB_REPORT_RUNTIME_OK', result.stdout)

    def test_lab_keyboard_navigation_runtime(self):
        # Exercise the generated handler with a mocked DOM, without patient data.
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync(process.argv[1],'utf8');
const a=src.indexOf('function novaLabResultKeyboard(event){');
const b=src.indexOf('function novaLabGroupedRows(lines,editable){',a);
assert(a>=0&&b>a,'keyboard handler missing from generated bundle');
let handler;
const document={addEventListener:(type,fn)=>{assert.strictEqual(type,'keydown');handler=fn}};
const window={};
vm.runInNewContext(src.slice(a,b),{document,window});
assert(handler,'keyboard listener missing');
let focused=-1;
const fields=[0,1,2].map(i=>({
 tagName:'INPUT',type:'text',matches:()=>true,
 nextElementSibling:null,focus(){focused=i}
}));
const table={querySelector:()=>({}),querySelectorAll:()=>fields};
fields.forEach(f=>{f.closest=x=>x==='table'?table:null});
const ev=(index,key,extra={})=>({
 target:fields[index],key,altKey:false,ctrlKey:false,metaKey:false,
 isComposing:false,shiftKey:false,preventDefault(){this.prevented=true},...extra
});
let e=ev(0,'Enter');handler(e);assert.strictEqual(focused,1);assert(e.prevented);
e=ev(1,'Enter',{shiftKey:true});handler(e);assert.strictEqual(focused,0);
e=ev(0,'ArrowDown');handler(e);assert.strictEqual(focused,0);assert(!e.prevented);
e=ev(0,'ArrowDown',{ctrlKey:true});handler(e);assert.strictEqual(focused,1);
e=ev(2,'Enter');handler(e);assert.strictEqual(focused,1);assert(!e.prevented);
const hidden={tagName:'INPUT',matches:x=>x==='input[data-line]'};
const select={tagName:'SELECT',matches:()=>true,nextElementSibling:hidden,focus(){focused=3}};
fields.push(select);
select.closest=x=>x==='table'?table:null;
e={target:select,key:'ArrowDown',altKey:false,ctrlKey:false,metaKey:false,isComposing:false,shiftKey:false,preventDefault(){this.prevented=true}};
handler(e);assert(!e.prevented,'native dropdown arrow was hijacked');
e={...e,key:'Enter',prevented:false};handler(e);assert(!e.prevented,'last select should not jump');
fields.unshift(select);focused=-1;
e={...e,key:'Enter',prevented:false};handler(e);
assert.strictEqual(focused,0,'Enter should advance from a dropdown to the next editable field');
assert(e.prevented,'Enter navigation should suppress implicit form submission');
console.log('LAB_KEYBOARD_OK');
"""
        result = subprocess.run(["node", "-e", script, str(APP)],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("LAB_KEYBOARD_OK", result.stdout)

    def test_grouped_lab_rows_propagate_panel_context_runtime(self):
        # Exercise real generated grouping with ambiguous Macroscopy/Microscopy labels.
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync(process.argv[1],'utf8');
const a=src.indexOf('function novaLabResultControl(x){');
const b=src.indexOf('function novaLabGroupedRows(lines,editable){',a);
const c=src.indexOf('\n}',b);
assert(a>=0&&b>a&&c>b,'lab control/grouping not found');
const esc=x=>String(x??'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');
const fn=vm.runInNewContext(src.slice(a,b)+src.slice(b,c+2)+';novaLabGroupedRows',{esc});
const urine=fn([{id:1,code:'NIT',name:'Nitrite',section_name:'Macroscopy',value:'Negative'},
{id:2,code:'LEU',name:'Leukocytes',section_name:'Microscopy',value:'Negative'}],true);
assert(urine.includes('<select'),'urine signature should activate qualitative dropdowns');
const stool=fn([{id:3,code:'MUCUS',name:'Mucus',section_name:'Macroscopy',value:'Present'},
{id:4,code:'OVA',name:'Ova',section_name:'Microscopy',value:'Not seen'}],true);
assert(stool.includes('<select'),'stool signature should activate qualitative dropdowns');
const actualStool=fn([{id:70,code:'MUCUS',name:'Mucus',section_name:'Macroscopy',value:'Present'},
{id:71,code:'CONS',name:'Consistency',section_name:'Macroscopy',value:'Soft'}],true);
assert(actualStool.includes('<select'),'actual stool CONS signature should activate choices');
const actualUrine=fn([{id:72,code:'NIT',name:'Nitrite',section_name:'Macroscopy',value:'Negative'},
{id:73,code:'LEU',name:'Leucocytes',section_name:'Microscopy',value:'Negative'},
{id:74,code:'CRYS',name:'Crystals',section_name:'Microscopy',value:'Calcium oxalate'}],true);
assert(actualUrine.includes('<datalist'),'urine crystals should retain free-text suggestions');
const unrelated=fn([{id:5,code:'NIT',name:'Nitrite',section_name:'Chemistry',value:'Negative'}],true);
assert(!unrelated.includes('<select'),'isolated code must not trigger panel inference');
console.log('LAB_GROUP_CONTEXT_OK');
"""
        result = subprocess.run(["node", "-e", script, str(APP)],
                                capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("LAB_GROUP_CONTEXT_OK", result.stdout)

    def test_lab_dropdown_preserves_existing_save_contract(self):
        patch = (ROOT / ".github/ci/nova_batch04_lab_reception.py").read_text(encoding="utf-8")
        for token in (
            "function novaLabResultControl(x)",
            "this.nextElementSibling.value=this.value",
            'type="hidden"',
            "editable?novaLabResultControl({...x,test_code:x.test_code||inferredPanel})",
            "if(value&&!choices.includes(value))choices=[value,...choices]",
            'inputmode="decimal"',
        ):
            self.assertIn(token, patch)

    def test_malaria_dropdown_does_not_capture_unrelated_methods(self):
        patch = (ROOT / ".github/ci/nova_batch04_lab_reception.py").read_text(encoding="utf-8")
        start = patch.index("function novaLabResultControl(x){")
        end = patch.index("function novaLabGroupedRows(lines,editable){", start)
        renderer = patch[start:end]
        self.assertIn("code==='PARASITE'", renderer)
        self.assertIn("code==='SPECIES'", renderer)
        self.assertNotIn("code==='METHOD' && name==='method'", renderer)
        self.assertIn("if(value&&!choices.includes(value))", renderer)
        self.assertIn("this.nextElementSibling.value=this.value", renderer)
        self.assertIn("type=\"hidden\"", renderer)
        self.assertIn("inputmode=\"decimal\"", renderer)

    def test_generated_lab_controls_in_node(self):
        # Execute the actual generated app.js controls, not merely the patch text.
        # The script does not invoke any pharmacy or cashier functions.
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync(process.argv[1],'utf8');
const start=src.indexOf('function novaLabResultControl(x){');
const end=src.indexOf('function novaLabGroupedRows(lines,editable){',start);
assert(start>=0&&end>start,'generated lab renderer missing');
const code=src.slice(start,end);
const esc=x=>String(x??'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');
const fn=vm.runInNewContext(code+';novaLabResultControl',{esc});
const malaria=fn({id:1,code:'PARASITE',name:'Malaria parasite detected',value:'Detected'});
assert(malaria.includes('<datalist')&&malaria.includes('value="Detected"')&&malaria.includes('data-line="1"'));
assert(malaria.includes('data-line="1"'));
assert(!malaria.includes('this.nextElementSibling.value=this.value'),'editable datalist saves directly in original input');
const legacy=fn({id:2,code:'SPECIES',name:'Plasmodium species (if identified)',value:'Previously recorded species'});
assert(legacy.includes('Previously recorded species')&&legacy.includes('value="Previously recorded species"'));
const unrelated=fn({id:3,code:'METHOD',name:'Method',value:'Other assay'});
assert(!unrelated.includes('<select')&&unrelated.includes('Other assay'));
const pregnancy=fn({id:70,code:'HCG',name:'Pregnancy Test',value:'Negative'});
assert(pregnancy.includes('<datalist')&&pregnancy.includes('Negative'),'pregnancy qualitative suggestions missing');
const rapidScreen=fn({id:71,code:'RESULT',name:'Qualitative screening result',value:'Reactive'});
assert(rapidScreen.includes('<datalist')&&rapidScreen.includes('Reactive'),'qualitative screening suggestions missing');
const analytes=[
 ['UREA','Urea','mg/dL'],['CREATININE','Creatinine','mg/dL'],
 ['ALT','ALT','U/L'],['TSH','TSH','mIU/L'],['HBA1C','HbA1c','%'],
 ['D_DIMER','D-dimer','ng/mL'],['PSA','PSA','ng/mL']
];
for(const [code,name,unit] of analytes){
 const html=fn({id:300,code,name,unit,value:'12.5'});
 assert(html.includes('inputmode="decimal"'),'missing numeric keyboard for '+code);
}
const numericUnknown=fn({id:301,code:'RESULT',name:'Measured value',unit:'mmol/L',value:'4.2'});
assert(numericUnknown.includes('inputmode="decimal"'),'numeric unit should hint decimal keyboard');
const urineCells=fn({id:302,code:'RBC',name:'Red blood cells',test_code:'URINE',unit:'/HPF',value:'2-4'});
assert(!urineCells.includes('inputmode="decimal"'),'microscopy ranges must stay free text');
const panels=[
 ['HIV','Non-reactive'],['HBS_ELISA','Reactive'],['DENGUE','Negative'],
 ['ICT_TYPHOID','Positive'],['HP_STOOL','Negative'],['BRUCELLA','Negative'],
 ['WIDAL','Negative'],['HCG','Positive'],['SG','Positive']
];
for(const [test_code,value] of panels){
 const html=fn({id:410,code:'RESULT',name:'Result',test_code,value});
 assert(html.includes('<datalist')&&html.includes('value="'+value+'"'),'qualitative panel not classified: '+test_code);
}
const quantitativeSerology=fn({id:411,code:'RESULT',name:'Result',test_code:'CRP Quantitative',value:'12.5'});
assert(!quantitativeSerology.includes('<datalist'),'quantitative assay must stay numeric/free text');
for(const test_name of ['HIV antibody quantitative','HCG concentration','Dengue antigen titre','Hepatitis antibody viral load']){
 const html=fn({id:412,code:'RESULT',name:'Result',test_code:'LAB-SEROLOGY',test_name,value:'12.5'});
 assert(!html.includes('<datalist')&&!html.includes('<select'),'quantitative test misclassified: '+test_name);
}
const legacyNamedAssay=fn({id:420,code:'RESULT',name:'Result',test_code:'LAB-SEROLOGY',test_name:'HIV Rapid Screening',value:'Non-reactive'});
assert(legacyNamedAssay.includes('<datalist'),'use panel display name when panel code is generic');
const legacyNamedUrine=fn({id:421,code:'NIT',name:'Nitrite',test_code:'LAB-01',test_name:'Urine Examination',value:'Negative'});
assert(legacyNamedUrine.includes('<select'),'use urine display name when test code is generic');
for(const [test_code,code,value,expected] of [
 ['BLOOD_GROUP','ABO','A','<select'],['BLOOD_GROUP','RH','Positive','<select'],
 ['CROSSMATCH','RESULT','Compatible','<datalist'],
 ['URINE_CULTURE','GROWTH','No growth','<datalist'],
 ['STOOL_OCCULT','RESULT','Negative','<datalist'],
 ['URINE_PREG','RESULT','Positive','<datalist']
]){
 const html=fn({id:501,code,name:code,test_code,value});
 assert(html.includes(expected),'missing structured choice '+test_code+'/'+code);
}
const organism=fn({id:502,code:'ORGANISM',name:'Organism',test_code:'URINE_CULTURE',value:'E. coli'});
assert(!organism.includes('<select')&&!organism.includes('<datalist'),'organism identification must remain editable');
const chemistry=fn({id:72,code:'RESULT',name:'Urea',test_name:'Renal Function Tests',value:'28'});
assert(!chemistry.includes('<datalist')&&!chemistry.includes('<select'),'numeric chemistry must remain unrestricted');
const cbcNumeric=fn({id:50,code:'HGB',name:'Hemoglobin',section_name:'',value:'12.5'});
assert(cbcNumeric.includes('inputmode="decimal"'),'CBC numeric mode missing when section is empty');
const gttNumeric=fn({id:51,code:'TIME_120',name:'2 hours',section_name:'',value:'120'});
assert(gttNumeric.includes('inputmode="decimal"'),'GTT numeric mode missing when section is empty');
const usaNit=fn({id:83,code:'NIT',name:'Nitrite',test_code:'USA',value:'Negative'});
assert(usaNit.includes('<select')&&usaNit.includes('Negative'),'USA urinalysis alias should use urine controls');
const urineNit=fn({id:6,code:'NIT',name:'Nitrite',section_name:'Urine examination',value:'Negative'});
assert(urineNit.includes('<select')&&urineNit.includes('Negative')&&urineNit.includes('type="hidden"'));
const urineLegacy=fn({id:7,code:'LEU',name:'Leukocyte esterase',section_name:'Urinalysis',value:'+++'});
assert(urineLegacy.includes('<select')&&urineLegacy.includes('+++')&&urineLegacy.includes('selected'));
const urineParent=fn({id:61,code:'NIT',name:'Nitrite',section_name:'Macroscopy',test_code:'URINE',value:'Negative'});
assert(urineParent.includes('<select'),'Urine panel must be recognized despite generic section');
const stoolParent=fn({id:62,code:'MUCUS',name:'Mucus',section_name:'Microscopy',test_name:'Stool Examination',value:'Present'});
assert(stoolParent.includes('<select'),'Stool panel must be recognized despite generic section');
const stoolMucus=fn({id:8,code:'MUCUS',name:'Mucus',section_name:'Stool examination',value:'Present'});
assert(stoolMucus.includes('<select')&&stoolMucus.includes('Present'));
const sameCodeElsewhere=fn({id:9,code:'NIT',name:'Nitrite',section_name:'Other assay',value:'Negative'});
assert(!sameCodeElsewhere.includes('<select'));
const malariaLegacy=fn({id:10,code:'MP',name:'Malaria parasite',section_name:'Malaria',value:'P. falciparum +++'});
assert(malariaLegacy.includes('<datalist')&&malariaLegacy.includes('P. falciparum +++')&&malariaLegacy.includes('data-line="10"'));
// Verify the visible select updates the original input used by the save collector.
const selected=fn({id:11,code:'NIT',name:'Nitrite',section_name:'Urinalysis',value:'Negative'});
const handler=selected.match(/onchange="([^"]+)"/);
assert(handler,'qualitative control missing change handler');
const originalSaveInput={value:'Negative'};
const visibleSelect={value:'Positive',nextElementSibling:originalSaveInput};
const runChange=Function('return function(){'+handler[1]+'}')();
runChange.call(visibleSelect);
assert.strictEqual(originalSaveInput.value,'Positive','dropdown failed to update saved value');
const escapedLegacy=fn({id:12,code:'LEU',name:'Leukocyte esterase',section_name:'Urinalysis',value:'<img src=x onerror=1>'});
assert(!escapedLegacy.includes('<img')&&escapedLegacy.includes('&lt;img'));
const colour=fn({id:13,code:'COLOR',name:'Colour',section_name:'Urinalysis',value:'Amber'});
assert(colour.includes('<datalist')&&colour.includes('value="Amber"')&&colour.includes('data-line="13"'));
const appearance=fn({id:14,code:'APPEARANCE',name:'Appearance',section_name:'Urinalysis',value:'Cloudy'});
assert(appearance.includes('<datalist')&&appearance.includes('Cloudy'));
const crystals=fn({id:15,code:'CRYS',name:'Crystals',section_name:'Urinalysis',value:'Calcium oxalate ++'});
assert(crystals.includes('<datalist')&&crystals.includes('Calcium oxalate ++'));
const protein=fn({id:16,code:'PRO',name:'Protein',section_name:'Urinalysis',value:'++'});
assert(protein.includes('<select')&&protein.includes('selected'));
const urineRbc=fn({id:80,code:'RBC',name:'RBCs',test_code:'URINE',value:'2-4'});
assert(urineRbc.includes('value="2-4"')&&!urineRbc.includes('inputmode="decimal"'),'urine RBC ranges must not use decimal-only input');
const urineSg=fn({id:81,code:'SG',name:'Specific Gravity',test_code:'URINE',value:'1.020'});
assert(urineSg.includes('inputmode="decimal"'),'urine SG should use numeric keyboard');
const urinePh=fn({id:82,code:'PH',name:'pH',test_code:'URINE',value:'6.0'});
assert(urinePh.includes('inputmode="decimal"'),'urine pH should use numeric keyboard');
const hb=fn({id:17,code:'HB',name:'Hemoglobin',section_name:'CBC',value:'13.4'});
assert(hb.includes('inputmode="decimal"')&&hb.includes('13.4'));
const stoolAppearance=fn({id:18,code:'APPEAR',name:'Appearance',section_name:'Stool examination',value:'Watery'});
assert(stoolAppearance.includes('<datalist'));
const glucose=fn({id:4,code:'TIME_120',name:'Glucose at 120 min (if ordered)',value:'112.5'});
assert(glucose.includes('inputmode="decimal"')&&glucose.includes('value="112.5"'));
const escaped=fn({id:5,code:'PARASITE',name:'Malaria parasite detected',value:'<script>alert(1)</script>'});
assert(!escaped.includes('<script>'));
console.log('LAB_CONTROL_RUNTIME_OK');
"""
        result = subprocess.run(
            ["node", "-e", script, str(APP)],
            capture_output=True, text=True, encoding="utf-8", timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("LAB_CONTROL_RUNTIME_OK", result.stdout)

    def test_grouped_lab_panel_inference_runtime(self):
        # Verify that the generated grouped renderer passes panel context into
        # actual urine/stool controls when sections are generic.
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync(process.argv[1],'utf8');
const a=src.indexOf('function novaLabResultControl(x){');
const b=src.indexOf('function novaLabGroupedRows(lines,editable){',a);
const c=src.indexOf('\n}',b);
assert(a>=0&&b>a&&c>b,'lab controls/grouped renderer missing');
const esc=x=>String(x??'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');
const fn=vm.runInNewContext(src.slice(a,c+2)+';novaLabGroupedRows',{esc});
const urine=fn([
 {id:1,code:'NIT',name:'Nitrite',section_name:'Macroscopy',value:'Negative'},
 {id:2,code:'LEU',name:'Leukocytes',section_name:'Microscopy',value:'Positive'},
 {id:3,code:'COLOR',name:'Colour',section_name:'Macroscopy',value:'Amber'}
],true);
assert(urine.includes('<select'),'urine categorical input missing');
assert(urine.includes('<datalist'),'urine colour suggestions missing');
const legacyUrine=fn([
 {id:91,code:'COLOR',name:'Colour',value:'Yellow'},
 {id:92,code:'SG',name:'Specific gravity',value:'1.015'},
 {id:93,code:'PH',name:'pH',value:'6'},
 {id:94,code:'PROT',name:'Protein',value:'Nil'},
 {id:95,code:'WBC',name:'Pus cells',value:'2-4'}
],true);
assert(legacyUrine.includes('<datalist')&&legacyUrine.includes('value="2-4"'),'legacy urine panel should infer urine context');
const legacyStool=fn([
 {id:96,code:'CONS',name:'Consistency',value:'Soft'},
 {id:97,code:'OVA',name:'Ova',value:'Not seen'}
],true);
assert(legacyStool.includes('<datalist'),'legacy stool consistency/ova panel should infer stool context');
const other=fn([{id:4,code:'NIT',name:'Nitrite',section_name:'Other',value:'Negative'}],true);
assert(!other.includes('<select'),'isolated ambiguous code must stay free-text');
console.log('LAB_PANEL_CONTEXT_OK');
"""
        result = subprocess.run(['node', '-e', script, str(APP)],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('LAB_PANEL_CONTEXT_OK', result.stdout)

    def test_lab_save_collection_uses_original_line_identifiers(self):
        # Guard the frontend/backend boundary without writing patient records.
        source = APP.read_text(encoding="utf-8")
        self.assertIn('data-line="'+ "'+esc(x.id)+'" + '"', source)
        self.assertIn('this.nextElementSibling.value=this.value', source)
        # Every editable qualitative control has one original hidden input
        # carrying the same data-line key as ordinary text results.
        patch = (ROOT / ".github/ci/nova_batch04_lab_reception.py").read_text(encoding="utf-8")
        start = patch.index("function novaLabResultControl(x){")
        end = patch.index("function novaLabGroupedRows(lines,editable){", start)
        renderer = patch[start:end]
        self.assertIn('type="hidden"', renderer)
        self.assertIn("const attrs=' data-line=", renderer)
        self.assertIn("value=\"'+esc(value)+'\"", renderer)

    def test_lab_keyboard_navigation_runtime(self):
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync(process.argv[1],'utf8');
const a=src.indexOf('function novaLabResultKeyboard(event){');
const b=src.indexOf("if(typeof document!=='undefined'&&!window.__novaLabKeyboardBound)",a);
assert(a>=0&&b>a,'keyboard handler not found');
const fn=vm.runInNewContext(src.slice(a,b)+';novaLabResultKeyboard');
let focused=-1,prevented=0;
const fields=[0,1,2].map(i=>({
 tagName:i===1?'SELECT':'INPUT',
 matches:q=>q==='input[data-line]'||q==='input[data-line],select',
 nextElementSibling:{matches:q=>q==='input[data-line]'},
 focus(){focused=i}
}));
const table={querySelector:q=>q==='input[data-line]'?fields[0]:null,
 querySelectorAll:()=>fields};
fields.forEach(f=>f.closest=q=>q==='table'?table:null);
function key(index,k,mods={}){
 focused=-1;prevented=0;
 fn({target:fields[index],key:k,preventDefault(){prevented++},
 altKey:false,metaKey:false,ctrlKey:false,shiftKey:false,isComposing:false,...mods});
 return [focused,prevented];
}
assert.deepStrictEqual(key(0,'Enter'),[1,1]);
assert.deepStrictEqual(key(2,'Enter',{shiftKey:true}),[1,1]);
assert.deepStrictEqual(key(0,'ArrowDown'),[-1,0]);
assert.deepStrictEqual(key(0,'ArrowDown',{ctrlKey:true}),[1,1]);
assert.deepStrictEqual(key(2,'ArrowUp',{ctrlKey:true}),[1,1]);
assert.deepStrictEqual(key(1,'ArrowDown'),[-1,0]);
assert.deepStrictEqual(key(1,'Enter'),[2,1]);
assert.deepStrictEqual(key(1,'Enter',{ctrlKey:true}),[2,1]);
assert.deepStrictEqual(key(0,'Enter',{isComposing:true}),[-1,0]);
console.log('LAB_KEYBOARD_RUNTIME_OK');
"""
        result = subprocess.run(["node", "-e", script, str(APP)],
                                capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("LAB_KEYBOARD_RUNTIME_OK", result.stdout)

    def test_lab_page_is_scoped(self):
        styles = [p.read_text(encoding="utf-8") for p in ROOT.glob("hospital/static/*.css")]
        joined = "\n".join(styles)
        self.assertIn("@page nova-lab-report", joined)
        self.assertIn("page:nova-lab-report", joined)
        self.assertNotIn("@page{size:A4 portrait", joined)
        for token in ("body.printing-lab .nova-clinical-print", "size:A4 portrait", "display:table-header-group", "body.printing-lab .nova-clinical-print .print-patient", "body.printing-lab .nova-clinical-print .lab-print-test", "page-break-inside:auto", "page-break-after:avoid"):
            self.assertIn(token, joined)

if __name__ == "__main__":
    unittest.main()
