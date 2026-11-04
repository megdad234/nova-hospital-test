"""Commercial pharmacy separation contract tests (no production data)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    for rel in ("pharmacy/app.py", "pharmacy/desktop.py", "pharmacy/server_host.py",
                "pharmacy/static/index.html", "pharmacy/static/app.js",
                "pharmacy/windows-installer.iss", "hospital/core.py",
                "windows/build-windows.ps1"):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("import hospital.core\n" if rel == "pharmacy/app.py" else
                        ("pass\n" if path.suffix == ".py" else "fixture\n"), encoding="utf-8")
    env = dict(os.environ, NOVA_EXTRACTION_ROOT=str(root))
    for name in ("stage_commercial_pharmacy.py", "audit_commercial_pharmacy.py",
                 "commercial_pharmacy_identity.py", "audit_commercial_windows_identity.py"):
        result = subprocess.run([sys.executable, str(HERE / name)], env=env,
                                text=True, capture_output=True)
        assert result.returncode == 0, f"{name}: {result.stdout} {result.stderr}"
    stage = root / "commercial_pharmacy_stage"
    audit = json.loads((stage / "ISOLATION_AUDIT.json").read_text(encoding="utf-8"))
    assert any(i["module"] == "hospital.core" for i in audit["imports"])
    assert audit["isolation_complete"] is False
    identity = json.loads((stage / "COMMERCIAL_IDENTITY.json").read_text(encoding="utf-8"))
    assert identity["windows_service_name"] != "NOVAHospitalServer"
    assert identity["use_hospital_database"] is False
    assert identity["use_hospital_windows_service"] is False
    assert identity["standalone_verified"] is False
    assert identity["printer_setup_during_install"] is False
    assert identity["employees_setup_during_install"] is False
    assert identity["default_port"] != 10080
    windows = json.loads((stage / "WINDOWS_COEXISTENCE_AUDIT.json").read_text(encoding="utf-8"))
    assert windows["runtime_verified"] is False
    assert windows["release_allowed"] is False
    assert windows["conflicts"] == []
    assert (stage / "pharmacy" / "app.py").read_text(encoding="utf-8") == "import hospital.core\n"
    assert (root / "pharmacy" / "app.py").read_text(encoding="utf-8") == "import hospital.core\n"
print("COMMERCIAL_PHARMACY_ISOLATION_CONTRACT_TESTS_PASSED")
