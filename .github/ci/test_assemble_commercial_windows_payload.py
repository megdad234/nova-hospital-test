"""Isolated fixture tests for the commercial Windows payload assembler."""
import importlib.util
import json
from pathlib import Path
import tempfile

script = Path(__file__).with_name("assemble_commercial_windows_payload.py")
spec = importlib.util.spec_from_file_location("commercial_payload_assembler", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    stage, runtime, output = root / "stage", root / "runtime", root / "output"
    stage.mkdir()
    runtime.mkdir()
    (runtime / "python.exe").write_bytes(b"synthetic-test-runtime")
    (stage / "EXTRACTION_MANIFEST.json").write_text(
        json.dumps({"status": "SOURCE_SNAPSHOT_ONLY_NOT_INSTALLABLE"}))
    (stage / "HOSPITAL_COUPLING_BLOCKERS.json").write_text(
        json.dumps({"standalone_network_and_schema_clear": True, "unresolved": []}))
    for relative in module.REQUIRED:
        file = stage / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("pass\n")
    module.assemble(stage, runtime, output)
    assert (output / "pharmacy/app.py").is_file()
    assert (output / "runtime/python.exe").is_file()
    assert not (output / "hospital_reference").exists()
    try:
        module.assemble(stage, runtime, output)
    except FileExistsError:
        pass
    else:
        raise AssertionError("Overwriting an existing payload must be refused")
    (stage / "pharmacy" / "hospital.sqlite3").write_bytes(b"synthetic-test-database")
    try:
        module.assemble(stage, runtime, root / "second-output")
    except ValueError:
        pass
    else:
        raise AssertionError("Copying a database into payload must be refused")
print("COMMERCIAL_WINDOWS_PAYLOAD_ASSEMBLER_TEST_OK")
