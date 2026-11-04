"""Synthetic regression for the real NOVA Batch12 insurance decoupling patch."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

PATCH = Path(__file__).with_name("patch_commercial_insurance.py")
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    pharmacy = root / "pharmacy"
    pharmacy.mkdir()
    (pharmacy / "static").mkdir()
    (pharmacy / "static" / "nova_pharmacy_batch08.js").write_text("nova-hospital-patient-search; قاعدة المستشفى المركزية", encoding="utf-8")
    source = '''
def nova_insured_schema(c):
    c.executescript("""CREATE TABLE IF NOT EXISTS nova_pharmacy_insured_people(
    patient_id INTEGER REFERENCES hospital_patients(id));""")
def nova_insured_search(c, contract_id, term):
    return c.execute("SELECT * FROM hospital_patients")
def nova_patient_search(c, term):
    return c.execute("SELECT * FROM hospital_patients")
def nova_insured_enroll(c, p, uid):
    x="INSERT INTO hospital_patients(name) VALUES(?)"
    y="hospital_patient_created_from_pharmacy"
    return x, y
def nova_insured_sale_snapshot(c, member, contract, uid, coverage, sale_id):
    return c.execute("SELECT * FROM hospital_patients")
'''
    source += "\n# /api/v1/nova-hospital-patient-search\n# /api/v1/nova-hospital-patient-search\n"
    (pharmacy / "app.py").write_text(source, encoding="utf-8")
    env = dict(os.environ, NOVA_EXTRACTION_ROOT=str(root))
    result = subprocess.run([sys.executable, str(PATCH)], env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, (result.stdout, result.stderr)
    patched = (pharmacy / "app.py").read_text(encoding="utf-8")
    assert "hospital_patients" not in patched
    assert "commercial_pharmacy_patients" in patched
    assert "commercial_pharmacy_patient_created" in patched
    assert "CREATE INDEX IF NOT EXISTS ix_commercial_pharmacy_patients_name" in patched
print("COMMERCIAL_INSURANCE_DECOUPLING_SYNTHETIC_TEST_PASSED")
