"""Make the extracted pharmacy server use its own data directory and port."""
from pathlib import Path
import os
import ast

root = Path(os.environ.get("NOVA_EXTRACTION_ROOT", Path(__file__).resolve().parents[2])).resolve()
target = root / "pharmacy" / "server_host.py"
source = target.read_text(encoding="utf-8")
anchors = {
    "port=int(os.getenv('PHARMACY_PORT','8443'))": "port=int(os.getenv('NOVA_COMMERCIAL_PORT','18763'))",
    "local=Path(os.getenv('PROGRAMDATA') or (Path.home()/'.hospital-pharmacy'))/'HospitalPharmacyServer'": "local=Path(os.getenv('NOVA_COMMERCIAL_DATA_DIR') or str(Path(os.getenv('PROGRAMDATA') or (Path.home()/'.local'/'share'))/'NOVACommercialPharmacy')).expanduser().resolve()",
    "app.DATA=local/'data';app.DB=app.DATA/'pharmacy.sqlite3'": "app.DATA=local;app.DB=local/'commercial_pharmacy.sqlite3'",
    "Hospital Pharmacy server listening on": "NOVA Commercial Pharmacy server listening on",
}
for old, new in anchors.items():
    if source.count(old) != 1:
        raise SystemExit("COMMERCIAL_SERVER_HOST_ANCHOR_DRIFT: " + old)
    source = source.replace(old, new, 1)
ast.parse(source)
if "PHARMACY_PORT" in source or "HospitalPharmacyServer" in source:
    raise SystemExit("COMMERCIAL_SERVER_HOST_HOSPITAL_IDENTITY_REMAINS")
target.write_text(source, encoding="utf-8")
print("COMMERCIAL_SERVER_HOST_ISOLATED")
