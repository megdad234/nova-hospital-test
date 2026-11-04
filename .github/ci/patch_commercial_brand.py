"""Remove hospital branding HTTP dependency from extracted commercial POS.

Runs only after all NOVA patches and before commercial staging. Preserves
the existing pharmacy's configurable branding and thermal receipt engine.
"""
from pathlib import Path
import os
import re

ROOT = Path(os.environ.get('NOVA_EXTRACTION_ROOT', str(Path(__file__).resolve().parents[2]))).resolve()
ui = ROOT / "pharmacy/static/app.js"
html = ROOT / "pharmacy/static/index.html"
if not ui.is_file() or not html.is_file():
    raise SystemExit("COMMERCIAL_BRAND_SOURCE_MISSING")
js = ui.read_text(encoding="utf-8")
pattern = r"async function loadNovaHospitalBrand\(\)\{[\s\S]*?\n\}\s*loadNovaHospitalBrand\(\);"
replacement = """async function loadNovaHospitalBrand(){
  window.NOVA_HOSPITAL_BRAND={
    hospital_name:'NOVA Pharmacy',
    hospital_phone:'',
    hospital_logo:''
  };
  const title=document.querySelector('.sidebar .brand h1');
  if(title)title.textContent='NOVA Pharmacy';
}
loadNovaHospitalBrand();"""
changed, count = re.subn(pattern, lambda m: replacement, js, count=1)
if count != 1:
    raise SystemExit("COMMERCIAL_BRAND_EXPECTED_HOSPITAL_FETCH_NOT_FOUND")
if "/api/hospital/lab/brand" in changed:
    raise SystemExit("COMMERCIAL_BRAND_HOSPITAL_API_REMAINS")
page = html.read_text(encoding="utf-8")
page = page.replace("NOVA Hospital — صيدلية المستشفى", "NOVA Pharmacy — إدارة الصيدلية")
page = page.replace("NOVA — صيدلية المستشفى", "NOVA Pharmacy — إدارة الصيدلية")
page = page.replace("Hospital Pharmacy", "Commercial Pharmacy")
page = page.replace("وحدة الصيدلية — نظام المستشفى الموحد", "نظام إدارة الصيدلية المستقل")
ui.write_text(changed, encoding="utf-8")
html.write_text(page, encoding="utf-8")
print("COMMERCIAL_BRAND_NO_HOSPITAL_HTTP_DEPENDENCY")
