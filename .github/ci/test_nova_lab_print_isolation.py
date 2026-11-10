"""Guard laboratory print isolation from pharmacy/cashier receipt styles."""
import unittest
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "hospital/static/app.js"
CSS = ROOT / "hospital/static/style.css"

class LabPrintIsolationTests(unittest.TestCase):
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

    def test_lab_dropdown_preserves_existing_save_contract(self):
        patch = (ROOT / ".github/ci/nova_batch04_lab_reception.py").read_text(encoding="utf-8")
        for token in (
            "function novaLabResultControl(x)",
            "this.nextElementSibling.value=this.value",
            'type="hidden"',
            "editable?novaLabResultControl(x)",
            "if(value && !choices.includes(value))choices=[value,...choices]",
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
        self.assertIn("if(value && !choices.includes(value))", renderer)
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
assert(malaria.includes('<select')&&malaria.includes('selected')&&malaria.includes('type="hidden"'));
assert(malaria.includes('data-line="1"'));
assert(malaria.includes('this.nextElementSibling.value=this.value'));
const legacy=fn({id:2,code:'SPECIES',name:'Plasmodium species (if identified)',value:'Previously recorded species'});
assert(legacy.includes('Previously recorded species')&&legacy.includes('selected'));
const unrelated=fn({id:3,code:'METHOD',name:'Method',value:'Other assay'});
assert(!unrelated.includes('<select')&&unrelated.includes('Other assay'));
const urineNit=fn({id:6,code:'NIT',name:'Nitrite',section_name:'Urine examination',value:'Negative'});
assert(urineNit.includes('<select')&&urineNit.includes('Negative')&&urineNit.includes('type="hidden"'));
const urineLegacy=fn({id:7,code:'LEU',name:'Leukocyte esterase',section_name:'Urinalysis',value:'+++'});
assert(urineLegacy.includes('<select')&&urineLegacy.includes('+++')&&urineLegacy.includes('selected'));
const stoolMucus=fn({id:8,code:'MUCUS',name:'Mucus',section_name:'Stool examination',value:'Present'});
assert(stoolMucus.includes('<select')&&stoolMucus.includes('Present'));
const sameCodeElsewhere=fn({id:9,code:'NIT',name:'Nitrite',section_name:'Other assay',value:'Negative'});
assert(!sameCodeElsewhere.includes('<select'));
const malariaLegacy=fn({id:10,code:'MP',name:'Malaria parasite',section_name:'Malaria',value:'P. falciparum +++'});
assert(!malariaLegacy.includes('<select')&&malariaLegacy.includes('P. falciparum +++'));
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
