"""Synthetic source audit; never starts hospital or commercial server."""
import importlib.util
from pathlib import Path
import tempfile

path = Path(__file__).with_name("audit_commercial_server_entrypoint.py")
spec = importlib.util.spec_from_file_location("commercial_entry_audit", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    pharmacy = root / "pharmacy"
    pharmacy.mkdir()
    (pharmacy / "app.py").write_text("DATA = 'NOVA_COMMERCIAL_DATA_DIR'\n")
    (pharmacy / "server_host.py").write_text("PORT = 18763\n")
    result = module.inspect(root)
    assert result["database_override_present"] is True
    assert result["port_override_present"] is False
    assert result["runtime_verified"] is False
    (pharmacy / "server_host.py").write_text("PORT = 'NOVA_COMMERCIAL_PORT'\n")
    assert module.inspect(root)["port_override_present"] is True
print("COMMERCIAL_SERVER_AUDIT_TEST_OK")
