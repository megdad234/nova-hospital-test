"""Decouple NOVA Batch12 insured pharmacy patient records from hospital tables.

Operates only on the extracted, fully patched pharmacy/app.py. Preserves
the existing NOVA insurance contracts, coverage validation, sale snapshots,
and claims logic. This is not a replacement insurance engine.
"""
from __future__ import annotations
import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
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
TARGET.write_text(updated, encoding="utf-8")
assert "REFERENCES commercial_pharmacy_patients(id)" in updated
print("COMMERCIAL_INSURANCE_DECOUPLED_FROM_HOSPITAL_PATIENT_TABLE")
