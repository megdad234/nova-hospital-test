"""Synthetic regression for commercial pharmacy branding extraction."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

script = Path(__file__).with_name("patch_commercial_brand.py")
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    static = root / "pharmacy" / "static"
    static.mkdir(parents=True)
    js = """async function loadNovaHospitalBrand(){
 try{const r=await fetch('/api/hospital/lab/brand');
 if(r.ok){window.NOVA_HOSPITAL_BRAND=await r.json();}
 }catch(e){}
}
loadNovaHospitalBrand();
"""
    (static / "app.js").write_text(js, encoding="utf-8")
    (static / "index.html").write_text(
        "<title>NOVA Hospital — صيدلية المستشفى</title>", encoding="utf-8")
    env = dict(os.environ, NOVA_EXTRACTION_ROOT=str(root))
    result = subprocess.run([sys.executable, str(script)], env=env,
                            text=True, capture_output=True)
    assert result.returncode == 0, (result.stdout, result.stderr)
    new_js = (static / "app.js").read_text(encoding="utf-8")
    new_html = (static / "index.html").read_text(encoding="utf-8")
    assert "/api/hospital/lab/brand" not in new_js
    assert "NOVA Pharmacy" in new_js
    assert "NOVA Pharmacy" in new_html
print("COMMERCIAL_PHARMACY_BRANDING_REGRESSION_PASSED")
