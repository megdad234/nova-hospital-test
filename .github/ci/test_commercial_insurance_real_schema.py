"""Exercise the real Batch12 insurance schema after commercial decoupling.

Uses a temporary SQLite database only; no customer/hospital data is touched.
"""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

here = Path(__file__).resolve().parent
fragment = (here / "nova_batch12_insurance_backend.pyfrag").read_text(encoding="utf-8")
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    static = root / "pharmacy" / "static"
    static.mkdir(parents=True)
    (static / "nova_pharmacy_batch08.js").write_text(
        "fetch('/api/v1/nova-hospital-patient-search')", encoding="utf-8")
    source = fragment + """
# GET route map
route_a = '/api/v1/nova-hospital-patient-search'
route_b = '/api/v1/nova-hospital-patient-search'
"""
    (root / "pharmacy" / "app.py").write_text(source, encoding="utf-8")
    env = dict(os.environ, NOVA_EXTRACTION_ROOT=str(root))
    completed = subprocess.run([sys.executable, str(here / "patch_commercial_insurance.py")],
                               env=env, capture_output=True, text=True)
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    modified = (root / "pharmacy" / "app.py").read_text(encoding="utf-8")
    assert "hospital_patients" not in modified
    assert "REFERENCES commercial_pharmacy_patients(id)" in modified
    namespace = {}
    exec(compile(modified, "<commercial-insurance-fixture>", "exec"), namespace)
    with sqlite3.connect(":memory:") as db:
        namespace["nova_insured_schema"](db)
        columns = [row[1] for row in db.execute(
            "PRAGMA table_info(commercial_pharmacy_patients)")]
        assert {"id", "patient_no", "full_name", "phone", "created_at", "created_by"} <= set(columns)
        foreign_keys = [row[2] for row in db.execute(
            "PRAGMA foreign_key_list(nova_pharmacy_insured_cards)")]
        assert "commercial_pharmacy_patients" in foreign_keys
        db.execute("INSERT INTO commercial_pharmacy_patients(patient_no,full_name,phone,created_at) VALUES(?,?,?,?)",
                   ("C-001", "Customer Test", "0912345678", "2026-11-04"))
        assert db.execute("SELECT COUNT(*) FROM commercial_pharmacy_patients").fetchone()[0] == 1
print("COMMERCIAL_INSURANCE_REAL_SCHEMA_TEST_PASSED")
