"""Integration smoke test: extracted original source, lab-only patch, pharmacy unchanged."""
import hashlib,pathlib,subprocess,sys,tempfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/".github"/"ci"))
from royallab_lab_print_patch import apply
from royallab_lab_a4_css_patch import apply as apply_css
with tempfile.TemporaryDirectory() as temp:
 base=pathlib.Path(temp)
 with zipfile.ZipFile(ROOT/"NOVA_Hospital_GitHub_Ready_Source.zip") as z:
  for name in ("hospital/static/app.js","hospital/static/style.css","pharmacy/static/app.js"):
   target=base/name;target.parent.mkdir(parents=True,exist_ok=True)
   target.write_bytes(z.read(name))
 pharmacy=base/"pharmacy/static/app.js"
 original=hashlib.sha256(pharmacy.read_bytes()).hexdigest()
 original_hospital=(base/"hospital/static/app.js").read_text(encoding="utf-8-sig")
 original_css=(base/"hospital/static/style.css").read_bytes()
 patched=apply(base)
 patched_css=apply_css(base)
 assert patched_css.read_bytes().startswith(original_css)
 assert "body.printing-lab #print-area .print-patient{break-inside:avoid-page" in patched_css.read_text(encoding="utf-8")
 result=patched.read_text(encoding="utf-8")
 assert "تقرير جزئي — توجد فحوصات أخرى" not in result
 assert result.count("async function printReport(id)")==1
 assert result.count("window.print()")==original_hospital.count("window.print()")
 assert hashlib.sha256(pharmacy.read_bytes()).hexdigest()==original
 assert result.count("lab/report/")==original_hospital.count("lab/report/")
 assert result.count("lab-print-group")==1
 assert result.count("section_name")==original_hospital.count("section_name")+2
 assert "flatMap((x,idx,visible)" in result
 assert "colspan=\\\"4\\\"" in result
 subprocess.run(["node","--check",str(patched)],check=True)
 try:apply(base)
 except RuntimeError:pass
 else:raise AssertionError("Repeated patch must fail closed")
 try:apply_css(base)
 except RuntimeError:pass
 else:raise AssertionError("Repeated CSS patch must fail closed")
 print("LAB_PRINT_PATCH_EXTRACTED_SOURCE_OK; A4_CSS_ADDITIVE_OK; PHARMACY_SHA256_UNCHANGED; NODE_SYNTAX_OK; REPEAT_REJECTED")
