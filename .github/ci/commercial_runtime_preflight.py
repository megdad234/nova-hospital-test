"""Commercial pharmacy installer readiness verifier.

Checks patched source files, forbidden hospital coupling, and independent
database configuration before packaging. A passing preflight is NOT a Windows
installation test or authorization to publish a release.
"""
from __future__ import annotations
import argparse
import ast
import json
from pathlib import Path
import re

def inspect(stage: Path):
    errors = []
    pharmacy = stage / "pharmacy"
    app = pharmacy / "app.py"
    ui = pharmacy / "static" / "app.js"
    insurance = pharmacy / "static" / "nova_pharmacy_batch08.js"
    for file in (app, ui, insurance):
        if not file.is_file():
            errors.append(f"missing source: {file.relative_to(stage)}")
    if errors:
        return {"preflight_passed": False, "errors": errors}
    source = app.read_text(encoding="utf-8")
    ast.parse(source)
    tree = ast.parse(source)
    names = {target.id: node.value for node in tree.body
             if isinstance(node, ast.Assign)
             for target in node.targets if isinstance(target, ast.Name)
             and target.id in {"DATA", "DB"}}
    if set(names) != {"DATA", "DB"}:
        errors.append("pharmacy database globals missing")
    if "commercial_pharmacy.sqlite3" not in source:
        errors.append("commercial database name missing")
    if "NOVA_COMMERCIAL_DATA_DIR" not in source:
        errors.append("commercial ProgramData override missing")
    if "REFERENCES hospital_patients(id)" in source:
        errors.append("hospital patient foreign key remains")
    if "/api/v1/nova-hospital-patient-search" in source:
        errors.append("hospital patient search route remains")
    if "commercial_pharmacy_patients" not in source:
        errors.append("commercial insured patient registry missing")
    js = ui.read_text(encoding="utf-8")
    if "/api/hospital/lab/brand" in js:
        errors.append("hospital branding HTTP request remains")
    if "nova-hospital-patient-search" in insurance.read_text(encoding="utf-8"):
        errors.append("POS still calls hospital patient search")
    for name in ("EXTRACTION_MANIFEST.json", "ISOLATION_AUDIT.json",
                 "COMMERCIAL_IDENTITY.json", "HOSPITAL_COUPLING_BLOCKERS.json"):
        if not (stage / name).is_file():
            errors.append("missing evidence: " + name)
    blocker_file = stage / "HOSPITAL_COUPLING_BLOCKERS.json"
    if blocker_file.is_file():
        blockers = json.loads(blocker_file.read_text(encoding="utf-8"))
        if blockers.get("unresolved"):
            errors.append(f"remaining hospital dependencies: {len(blockers['unresolved'])}")
    return {"preflight_passed": not errors, "errors": errors,
            "windows_installer_verified": False, "release_authorized": False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, default=Path("commercial_pharmacy_stage"))
    args = parser.parse_args()
    result = inspect(args.stage)
    args.stage.mkdir(parents=True, exist_ok=True)
    (args.stage / "COMMERCIAL_RUNTIME_PREFLIGHT.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["preflight_passed"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
