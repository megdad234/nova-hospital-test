"""Synthetic packaging dependency audit tests."""
import importlib.util
from pathlib import Path
import tempfile

script = Path(__file__).with_name("audit_commercial_runtime_dependencies.py")
spec = importlib.util.spec_from_file_location("runtime_dependency_audit", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "pharmacy").mkdir()
    (root / "pharmacy" / "app.py").write_text("import json\nimport imaginary_vendor_package\nfrom . import helpers\n", encoding="utf-8")
    (root / "pharmacy" / "helpers.py").write_text("import os\n", encoding="utf-8")
    report = module.inspect(root)
    assert "imaginary_vendor_package" in report["external_import_candidates"]
    assert "json" in report["stdlib_imports"]
    assert report["runtime_installed"] is False
    assert report["windows_installer_verified"] is False
    assert not report["syntax_errors"]
    (root / "pharmacy" / "helpers.py").write_text("broken = (\n", encoding="utf-8")
    assert module.inspect(root)["syntax_errors"]
print("COMMERCIAL_DEPENDENCY_AUDIT_TEST_OK")
