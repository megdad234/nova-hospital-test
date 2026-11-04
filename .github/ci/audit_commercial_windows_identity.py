"""Audit standalone configuration against NOVA's actual Windows installer scripts.

This test deliberately does not modify or uninstall the hospital product.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "commercial_pharmacy_stage"
config_path = STAGE / "COMMERCIAL_IDENTITY.json"
if not config_path.exists():
    raise SystemExit("MISSING_COMMERCIAL_IDENTITY")
config = json.loads(config_path.read_text(encoding="utf-8"))
required = {
    "windows_service_name", "windows_app_id", "install_subdirectory",
    "program_data_subdirectory", "database_file", "default_port",
}
missing = required - config.keys()
if missing:
    raise SystemExit("MISSING_IDENTITY_FIELDS: " + ",".join(sorted(missing)))
files = list((STAGE / "windows_reference").rglob("*")) + list((STAGE / "pharmacy").rglob("*"))
evidence = {"status": "source_inventory_only", "runtime_verified": False,
            "commercial_identity": config, "source_identifiers": [],
            "conflicts": [], "release_allowed": False}
for p in files:
    if not p.is_file() or p.suffix.lower() not in {".py", ".ps1", ".iss", ".js", ".json"}:
        continue
    try:
        content = p.read_text(encoding="utf-8")
    except UnicodeError:
        continue
    for index, line in enumerate(content.splitlines(), 1):
        if re.search(r"(?i)(?:AppId|AppName|DefaultDirName|service.?name|display.?name|ProgramData|sqlite|port|localhost|127\\.0\\.0\\.1)", line):
            evidence["source_identifiers"].append({
                "file": str(p.relative_to(STAGE)), "line": index,
                "excerpt": line.strip()[:180]})
if config["default_port"] in (0, 80, 443, 10080):
    evidence["conflicts"].append("reserved or hospital-default port")
if not isinstance(config["default_port"], int) or not (1024 <= config["default_port"] <= 65535):
    evidence["conflicts"].append("invalid commercial port")
for k in ("windows_service_name", "windows_app_id", "install_subdirectory", "program_data_subdirectory", "database_file"):
    if not config[k] or "hospital" in config[k].lower():
        evidence["conflicts"].append("hospital identity collision: " + k)
if config.get("use_hospital_database") is not False:
    evidence["conflicts"].append("hospital database usage")
if config.get("use_hospital_windows_service") is not False:
    evidence["conflicts"].append("hospital service usage")
(STAGE / "WINDOWS_COEXISTENCE_AUDIT.json").write_text(
    json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
if evidence["conflicts"]:
    raise SystemExit("COMMERCIAL_IDENTITY_CONFLICTS: " + "; ".join(evidence["conflicts"]))
print("WINDOWS_IDENTITY_CONTRACT_AUDITED; RUNTIME_COEXISTENCE_NOT_YET_VERIFIED")
