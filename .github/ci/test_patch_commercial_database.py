"""Synthetic test for actual NOVA pharmacy DATA/DB global isolation."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

patch = Path(__file__).with_name("patch_commercial_database.py")
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    pharmacy = root / "pharmacy"
    pharmacy.mkdir()
    original = """from pathlib import Path
DATA = Path('hospital-shared-data')
DB = DATA / 'nova.sqlite3'
def check():
    return str(DB)
"""
    (pharmacy / "app.py").write_text(original, encoding="utf-8")
    env = dict(os.environ, NOVA_EXTRACTION_ROOT=str(root))
    result = subprocess.run([sys.executable, str(patch)], env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, (result.stdout, result.stderr)
    source = (pharmacy / "app.py").read_text(encoding="utf-8")
    assert "commercial_pharmacy.sqlite3" in source
    assert "NOVA_COMMERCIAL_DATA_DIR" in source
    assert "hospital-shared-data" not in source
    namespace = {"__name__": "fixture"}
    exec(compile(source, "fixture.py", "exec"), namespace)
    assert namespace["DB"].parent == namespace["DATA"]
    assert namespace["DB"].name == "commercial_pharmacy.sqlite3"
print("COMMERCIAL_DATABASE_GLOBALS_SYNTHETIC_TEST_PASSED")
