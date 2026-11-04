"""Enforce standalone pharmacy identity without touching NOVA Hospital.

This creates a separate configuration and release contract in the extracted
source tree. It never changes the original hospital installer or database.
"""
from pathlib import Path
import json
import os
import secrets
import sys

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "commercial_pharmacy_stage"
MANIFEST = STAGE / "EXTRACTION_MANIFEST.json"
if not MANIFEST.is_file():
    raise SystemExit("RUN_STAGE_FIRST")
source = json.loads(MANIFEST.read_text(encoding="utf-8"))
if source.get("status") != "SOURCE_SNAPSHOT_ONLY_NOT_INSTALLABLE":
    raise SystemExit("UNRECOGNIZED_SOURCE_MANIFEST")
CONFIG = {
    "product_id": "nova-commercial-pharmacy",
    "product_name": "NOVA Pharmacy",
    "windows_service_name": "NOVACommercialPharmacyServer",
    "windows_service_display_name": "NOVA Commercial Pharmacy Server",
    "windows_app_id": "NOVACommercialPharmacy.Standalone",
    "install_subdirectory": "NOVA Commercial Pharmacy",
    "program_data_subdirectory": "NOVACommercialPharmacy",
    "database_file": "commercial_pharmacy.sqlite3",
    "default_port": 18763,
    "bind_address": "0.0.0.0",
    "admin_first_run": "preserve_existing_nova_pharmacy_admin_bootstrap",
    "printer_setup_during_install": False,
    "pharmacy_logo_setup_during_install": False,
    "employees_setup_during_install": False,
    "use_hospital_database": False,
    "use_hospital_windows_service": False,
    "migrate_hospital_patient_data": False,
    "standalone_verified": False,
}
(STAGE / "COMMERCIAL_IDENTITY.json").write_text(
    json.dumps(CONFIG, ensure_ascii=False, indent=2), encoding="utf-8")
readme = """# NOVA Commercial Pharmacy: isolated identity contract

This contract is not an installer and is not evidence of runtime separation.

- The commercial pharmacy must use its own Windows service, installation path,
  ProgramData directory, database and network port.
- First-run only creates the administrator. Other settings remain inside the app.
- Existing pharmacy POS, inventory, purchases, insurance, shifts, thermal
  receipts, reports, backups and premium Arabic RTL screens must remain intact.
- No production hospital database is copied or migrated.
- No hospital source or installer is overwritten.
- The final build is blocked until integration and Windows installation tests pass.
"""
(STAGE / "COMMERCIAL_IDENTITY.md").write_text(readme, encoding="utf-8")
print("COMMERCIAL_IDENTITY_CONTRACT_CREATED; STANDALONE_NOT_VERIFIED")
