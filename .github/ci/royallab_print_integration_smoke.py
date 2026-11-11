"""Integration smoke test: extracted original source, lab-only patch, pharmacy unchanged."""
import hashlib,pathlib,subprocess,sys,tempfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/".github"/"ci"))
from royallab_lab_print_patch import apply
with tempfile.TemporaryDirectory() as temp:
 base=pathlib.Path(temp)
 with zipfile.ZipFile(ROOT/"NOVA_Hospital_GitHub_Ready_Source.zip") as z:
  for name in ("hospital/static/app.js","pharmacy/static/app.js"):
   target=base/name;target.parent.mkdir(parents=True,exist_ok=True)
   target.write_bytes(z.read(name))
 pharmacy=base/"pharmacy/static/app.js"
 original=hashlib.sha256(pharmacy.read_bytes()).hexdigest()
 original_hospital=(base/"hospital/static/app.js").read_text(encoding="utf-8-sig")
 patched=apply(base)
 result=patched.read_text(encoding="utf-8")
 assert "تقرير جزئي — توجد فحوصات أخرى" not in result
 assert result.count("async function printReport(id)")==1
 assert result.count("window.print()")==original_hospital.count("window.print()")
 assert hashlib.sha256(pharmacy.read_bytes()).hexdigest()==original
 assert result.count("lab/report/")==original_hospital.count("lab/report/")
 subprocess.run(["node","--check",str(patched)],check=True)
 try:apply(base)
 except RuntimeError:pass
 else:raise AssertionError("Repeated patch must fail closed")
 print("LAB_PRINT_PATCH_EXTRACTED_SOURCE_OK; PHARMACY_SHA256_UNCHANGED; NODE_SYNTAX_OK; REPEAT_REJECTED")
