"""Decouple NOVA Batch12 insured pharmacy patient records from hospital tables.

Operates only on the extracted, fully patched pharmacy/app.py. Preserves
the existing NOVA insurance contracts, coverage validation, sale snapshots,
and claims logic. This is not a replacement insurance engine.
"""
from __future__ import annotations
import ast
import os
from pathlib import Path
import re

ROOT = Path(os.environ.get("NOVA_EXTRACTION_ROOT", str(Path(__file__).resolve().parents[2]))).resolve()
TARGET = ROOT / "pharmacy" / "app.py"
if not TARGET.is_file():
    raise SystemExit("COMMERCIAL_INSURANCE_MISSING_PHARMACY_SOURCE")
source = TARGET.read_text(encoding="utf-8")
tree = ast.parse(source)
targets = {
    "nova_insured_schema", "nova_insured_search", "nova_patient_search",
    "nova_insured_enroll", "nova_insured_sale_snapshot",
}
nodes = {node.name: node for node in tree.body
         if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in targets}
if set(nodes) != targets:
    raise SystemExit("COMMERCIAL_INSURANCE_REQUIRED_FUNCTIONS_MISSING: " +
                     ",".join(sorted(targets - set(nodes))))
lines = source.splitlines(keepends=True)
patched = []
for name, node in nodes.items():
    original = "".join(lines[node.lineno-1:node.end_lineno])
    if "hospital_patients" not in original:
        raise SystemExit("COMMERCIAL_INSURANCE_EXPECTED_HOSPITAL_LINK_NOT_FOUND: " + name)
    revised = original.replace("hospital_patients", "commercial_pharmacy_patients")
    if name == "nova_insured_schema":
        anchor = 'c.executescript("""CREATE TABLE IF NOT EXISTS nova_pharmacy_insured_people('
        if original.count(anchor) != 1:
            raise SystemExit("COMMERCIAL_INSURANCE_SCHEMA_ANCHOR_CHANGED")
        replacement = '''c.executescript("""CREATE TABLE IF NOT EXISTS commercial_pharmacy_patients(
      id INTEGER PRIMARY KEY,
      patient_no TEXT NOT NULL UNIQUE,
      full_name TEXT NOT NULL,
      phone TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL,
      created_by INTEGER);
    CREATE INDEX IF NOT EXISTS ix_commercial_pharmacy_patients_name
      ON commercial_pharmacy_patients(full_name);
    CREATE TABLE IF NOT EXISTS nova_pharmacy_insured_people('''
        revised = revised.replace(anchor, replacement, 1)
    if name == "nova_insured_enroll":
        revised = revised.replace("'hospital_patient_created_from_pharmacy'",
                                  "'commercial_pharmacy_patient_created'")
    patched.append((node.lineno-1, node.end_lineno, revised))
for start, end, replacement in sorted(patched, reverse=True):
    lines[start:end] = [replacement]
updated = "".join(lines)
ast.parse(updated)
if updated == source:
    raise SystemExit("COMMERCIAL_INSURANCE_NO_CHANGE")
old_endpoint = "/api/v1/nova-hospital-patient-search"
new_endpoint = "/api/v1/nova-pharmacy-customer-search"
if updated.count(old_endpoint) != 2:
    raise SystemExit("COMMERCIAL_INSURANCE_HOSPITAL_ROUTE_ANCHOR_CHANGED")
updated = updated.replace(old_endpoint, new_endpoint)
ui_path = ROOT / "pharmacy" / "static" / "nova_pharmacy_batch08.js"
if not ui_path.is_file():
    raise SystemExit("COMMERCIAL_INSURANCE_MISSING_POS_UI")
ui = ui_path.read_text(encoding="utf-8")
if "nova-hospital-patient-search" not in ui:
    raise SystemExit("COMMERCIAL_INSURANCE_MISSING_PATIENT_UI_ANCHOR")
ui = ui.replace("nova-hospital-patient-search", "nova-pharmacy-customer-search")
ui = ui.replace("قاعدة المستشفى المركزية", "قاعدة بيانات الصيدلية المستقلة")
ui = ui.replace("مرتبط بملف المريض", "مرتبط بملف عميل الصيدلية")
TARGET.write_text(updated, encoding="utf-8")
ui_path.write_text(ui, encoding="utf-8")
assert "REFERENCES commercial_pharmacy_patients(id)" in updated
print("COMMERCIAL_INSURANCE_DECOUPLED_FROM_HOSPITAL_PATIENT_TABLE")
