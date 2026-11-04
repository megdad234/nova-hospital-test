"""Synthetic smoke tests for safe source staging, without a Windows installer."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SCRIPT = Path(__file__).with_name("stage_commercial_pharmacy.py")
with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    required = ["pharmacy/app.py", "pharmacy/desktop.py", "pharmacy/server_host.py",
                "pharmacy/static/index.html", "pharmacy/static/app.js",
                "pharmacy/windows-installer.iss"]
    for name in required + ["hospital/core.py", "windows/build-windows.ps1"]:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("pass\n" if p.suffix == ".py" else "fixture\n", encoding="utf-8")
    (root / "pharmacy" / "test_data.sqlite").write_bytes(b"private test data")
    env = dict(os.environ, NOVA_EXTRACTION_ROOT=str(root))
    run = subprocess.run([sys.executable, str(SCRIPT)], env=env,
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    out = root / "commercial_pharmacy_stage"
    manifest = json.loads((out / "EXTRACTION_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "SOURCE_SNAPSHOT_ONLY_NOT_INSTALLABLE"
    assert not (out / "pharmacy" / "test_data.sqlite").exists()
    assert (out / "hospital_reference" / "core.py").exists()
    assert manifest["pharmacy_files"] >= len(required)
    # Missing essential source must block a snapshot.
    (root / "pharmacy" / "app.py").unlink()
    blocked = subprocess.run([sys.executable, str(SCRIPT)], env=env,
                             capture_output=True, text=True)
    assert blocked.returncode != 0
    assert "MISSING_REQUIRED" in blocked.stdout + blocked.stderr
print("COMMERCIAL_PHARMACY_STAGE_SYNTHETIC_TESTS_PASSED")
