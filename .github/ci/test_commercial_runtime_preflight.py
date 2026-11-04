"""Verify preflight blocks hospital coupling and missing commercial DB config."""
import importlib.util
import json
from pathlib import Path
import tempfile

script = Path(__file__).with_name("commercial_runtime_preflight.py")
spec = importlib.util.spec_from_file_location("commercial_preflight", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    pharmacy = root / "pharmacy"
    static = pharmacy / "static"
    static.mkdir(parents=True)
    (pharmacy / "app.py").write_text("DATA='hospital'; DB='hospital.db'\n", encoding="utf-8")
    (static / "app.js").write_text("fetch('/api/hospital/lab/brand')", encoding="utf-8")
    (static / "nova_pharmacy_batch08.js").write_text(
        "fetch('/api/v1/nova-hospital-patient-search')", encoding="utf-8")
    for name in ("EXTRACTION_MANIFEST.json", "ISOLATION_AUDIT.json",
                 "COMMERCIAL_IDENTITY.json"):
        (root / name).write_text("{}", encoding="utf-8")
    (root / "HOSPITAL_COUPLING_BLOCKERS.json").write_text(
        json.dumps({"unresolved": [{"type": "hospital_api"}]}), encoding="utf-8")
    result = module.inspect(root)
    assert result["preflight_passed"] is False
    assert result["windows_installer_verified"] is False
    assert any("hospital" in error for error in result["errors"])
    (root / "HOSPITAL_COUPLING_BLOCKERS.json").write_text(
        json.dumps({"unresolved": [], "standalone_network_and_schema_clear": False}), encoding="utf-8")
    result = module.inspect(root)
    assert "hospital coupling audit not cleared" in result["errors"]
print("COMMERCIAL_PREFLIGHT_NEGATIVE_TEST_PASSED")
