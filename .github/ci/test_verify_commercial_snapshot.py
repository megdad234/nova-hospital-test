"""Negative tests for commercial source integrity enforcement."""
import importlib.util
from pathlib import Path
import hashlib
import json
import tempfile

script = Path(__file__).with_name("verify_commercial_snapshot.py")
spec = importlib.util.spec_from_file_location("verify_commercial_snapshot", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    source = root / "pharmacy"
    source.mkdir()
    app = source / "app.py"
    app.write_text("print('pharmacy')", encoding="utf-8")
    manifest = {"sha256": {"pharmacy/app.py": hashlib.sha256(app.read_bytes()).hexdigest()}}
    (root / "EXTRACTION_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert module.verify_snapshot(root) == []
    app.write_text("print('tampered')", encoding="utf-8")
    assert any("integrity mismatch" in x for x in module.verify_snapshot(root))
    app.write_text("print('pharmacy')", encoding="utf-8")
    (source / "hospital.db").write_bytes(b"DO NOT DISTRIBUTE")
    assert any("live database included" in x for x in module.verify_snapshot(root))
    (source / "hospital.db").unlink()
    (source / "commercial_pharmacy.sqlite3-wal").write_bytes(b"test")
    assert module.verify_snapshot(root)
    manifest["sha256"]["../outside.py"] = "0" * 64
    (root / "EXTRACTION_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert any("unsafe manifest path" in issue for issue in module.verify_snapshot(root))
print("COMMERCIAL_SNAPSHOT_INTEGRITY_TESTS_PASSED")
