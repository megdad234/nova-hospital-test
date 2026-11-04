"""Strict release gate for commercial pharmacy.

This intentionally rejects source-only snapshots. It can be used by the
future standalone Windows installer job to prevent misleading release artifacts.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

REQUIRED = (
    "first_admin", "employee_roles", "shifts", "pharmacy_pos",
    "stock_and_expiry", "purchases_and_suppliers", "insurance_standalone",
    "reports", "thermal_receipt", "backup_and_restore",
    "lan_clients", "windows_clean_install", "windows_upgrade",
    "windows_uninstall", "coexistence_with_hospital",
)
def verify(stage: Path, evidence: Path) -> list[str]:
    errors = []
    manifest_path = stage / "EXTRACTION_MANIFEST.json"
    audit_path = stage / "ISOLATION_AUDIT.json"
    identity_path = stage / "COMMERCIAL_IDENTITY.json"
    for path in (manifest_path, audit_path, identity_path):
        if not path.is_file():
            errors.append("missing: " + str(path))
    if errors:
        return errors
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "SOURCE_SNAPSHOT_ONLY_NOT_INSTALLABLE":
        errors.append("unknown source snapshot provenance")
    if audit.get("isolation_complete") is not True:
        errors.append("hospital dependencies not signed off")
    if identity.get("standalone_verified") is not True:
        errors.append("commercial service/database identity not runtime-verified")
    if identity.get("use_hospital_database") is not False:
        errors.append("hospital database access forbidden")
    if identity.get("use_hospital_windows_service") is not False:
        errors.append("hospital Windows service reuse forbidden")
    blockers_path = stage / "HOSPITAL_COUPLING_BLOCKERS.json"
    if not blockers_path.is_file():
        errors.append("hospital coupling audit absent")
    else:
        blockers = json.loads(blockers_path.read_text(encoding="utf-8"))
        if blockers.get("standalone_network_and_schema_clear") is not True:
            errors.append("hospital API/schema/import coupling remains")
    if not evidence.is_file():
        errors.append("Windows acceptance evidence absent")
        return errors
    data = json.loads(evidence.read_text(encoding="utf-8"))
    for item in REQUIRED:
        check = data.get("checks", {}).get(item, {})
        if check.get("status") != "passed":
            errors.append("acceptance not passed: " + item)
        log_path = check.get("log_path")
        log_hash = check.get("log_sha256")
        if not log_path or not log_hash:
            errors.append("missing acceptance log and hash: " + item)
        elif not Path(log_path).is_file():
            errors.append("acceptance log file absent: " + item)
        elif hashlib.sha256(Path(log_path).read_bytes()).hexdigest().lower() != str(log_hash).lower():
            errors.append("acceptance log hash mismatch: " + item)
    installer = data.get("installer", {})
    if not installer.get("path") or not installer.get("sha256"):
        errors.append("installer artifact and hash absent")
    else:
        target = Path(installer["path"])
        if not target.is_file():
            errors.append("installer missing on build runner")
        elif hashlib.sha256(target.read_bytes()).hexdigest().lower() != installer["sha256"].lower():
            errors.append("installer SHA256 mismatch")
    return errors

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, default=Path("commercial_pharmacy_stage"))
    parser.add_argument("--evidence", type=Path, default=Path("commercial_pharmacy_acceptance.json"))
    args = parser.parse_args()
    problems = verify(args.stage, args.evidence)
    if problems:
        print("COMMERCIAL_PHARMACY_RELEASE_BLOCKED")
        for issue in problems:
            print(" -", issue)
        return 2
    print("COMMERCIAL_PHARMACY_RELEASE_GATES_PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
