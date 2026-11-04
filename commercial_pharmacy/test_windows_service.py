"""Service command tests do not register or start any Windows service."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from commercial_pharmacy.windows_service import pharmacy_command, parse_service_port

class WindowsServiceTests(unittest.TestCase):
    def test_service_port_parser(self):
        self.assertEqual(parse_service_port(["exe", "--service", "--port", "18763"]), 18763)
        self.assertIsNone(parse_service_port(["exe", "--service"]))
        with self.assertRaises(ValueError):
            parse_service_port(["exe", "--port", "10080"])
        with self.assertRaises(ValueError):
            parse_service_port(["exe", "--port"])

    def test_refuses_missing_pharmacy_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                pharmacy_command(Path(tmp))

    def test_refuses_undeclared_python_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pharmacy").mkdir()
            (root / "pharmacy" / "server_host.py").write_text("pass\n")
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(RuntimeError):
                    pharmacy_command(root)

    def test_uses_dedicated_bundled_python_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pharmacy").mkdir()
            (root / "pharmacy" / "server_host.py").write_text("pass\n")
            runtime = root / "runtime"
            runtime.mkdir()
            python = runtime / "python.exe"
            python.write_bytes(b"fixture")
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(pharmacy_command(root), [str(python), str(root / "pharmacy" / "server_host.py")])

    def test_detects_dedicated_bundled_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pharmacy").mkdir()
            server = root / "pharmacy" / "server_host.py"
            server.write_text("pass\n")
            runtime = root / "runtime"
            runtime.mkdir()
            python = runtime / "python.exe"
            python.write_bytes(b"test runtime")
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(pharmacy_command(root), [str(python), str(server)])

    def test_uses_explicit_commercial_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pharmacy").mkdir()
            server = root / "pharmacy" / "server_host.py"
            server.write_text("pass\n")
            python = root / "commercial-python.exe"
            python.write_bytes(b"fixture")
            with patch.dict(os.environ, {"NOVA_COMMERCIAL_PYTHON": str(python)}):
                self.assertEqual(pharmacy_command(root), [str(python), str(server)])

if __name__ == "__main__":
    unittest.main()
