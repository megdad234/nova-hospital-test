"""Ensure a source snapshot can never be published as a commercial installer."""
import importlib.util
import json
from pathlib import Path
import tempfile

module_path = Path(__file__).with_name("commercial_pharmacy_release_gate.py")
spec = importlib.util.spec_from_file_location("commercial_pharmacy_release_gate", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    stage = root / "commercial_pharmacy_stage"
    stage.mkdir()
    (stage / "EXTRACTION_MANIFEST.json").write_text(
        json.dumps({"status": "SOURCE_SNAPSHOT_ONLY_NOT_INSTALLABLE"}), encoding="utf-8")
    (stage / "ISOLATION_AUDIT.json").write_text(
        json.dumps({"isolation_complete": False}), encoding="utf-8")
    (stage / "COMMERCIAL_IDENTITY.json").write_text(
        json.dumps({"standalone_verified": False, "use_hospital_database": False,
                    "use_hospital_windows_service": False}), encoding="utf-8")
    problems = module.verify(stage, root / "missing-evidence.json")
    assert any("dependencies" in p for p in problems), problems
    assert any("identity" in p for p in problems), problems
    assert any("evidence" in p for p in problems), problems
    (stage / "ISOLATION_AUDIT.json").write_text(
        json.dumps({"isolation_complete": True}), encoding="utf-8")
    (stage / "COMMERCIAL_IDENTITY.json").write_text(
        json.dumps({"standalone_verified": True, "use_hospital_database": False,
                    "use_hospital_windows_service": False}), encoding="utf-8")
    evidence = root / "evidence.json"
    evidence.write_text(json.dumps({"checks": {}, "installer": {}}), encoding="utf-8")
    problems = module.verify(stage, evidence)
    assert any("first_admin" in p for p in problems)
    assert any("coexistence_with_hospital" in p for p in problems)
    assert any("installer artifact" in p for p in problems)
    assert any("missing acceptance log and hash" in p for p in problems)
print("COMMERCIAL_PHARMACY_RELEASE_GATE_NEGATIVE_TESTS_PASSED")
