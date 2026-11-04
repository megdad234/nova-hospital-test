"""Synthetic source launcher tests, no hospital process is started."""
from pathlib import Path
import tempfile
import unittest
from commercial_pharmacy.launch import prepare

class LaunchTests(unittest.TestCase):
    def test_commercial_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pharmacy = root / "pharmacy"
            pharmacy.mkdir()
            (pharmacy / "app.py").write_text("NOVA_COMMERCIAL_DATA_DIR commercial_pharmacy.sqlite3")
            (pharmacy / "server_host.py").write_text("pass\n")
            data = root / "commercial_data"
            command, env, cwd = prepare(root, data, 18763)
            self.assertEqual(cwd, root)
            self.assertEqual(command[-1], str(pharmacy / "server_host.py"))
            self.assertEqual(env["NOVA_COMMERCIAL_PORT"], "18763")
            self.assertEqual(env["NOVA_COMMERCIAL_DATA_DIR"], str(data))
            self.assertTrue(data.is_dir())

    def test_unpatched_app_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pharmacy = root / "pharmacy"
            pharmacy.mkdir()
            (pharmacy / "app.py").write_text("hospital.sqlite3")
            (pharmacy / "server_host.py").write_text("pass\n")
            with self.assertRaises(RuntimeError):
                prepare(root, root / "commercial_data")

    def test_hospital_directory_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pharmacy = root / "pharmacy"
            pharmacy.mkdir()
            (pharmacy / "app.py").write_text("NOVA_COMMERCIAL_DATA_DIR commercial_pharmacy.sqlite3")
            (pharmacy / "server_host.py").write_text("pass\n")
            hospital = root / "hospital"
            hospital.mkdir()
            with self.assertRaises(ValueError):
                prepare(root, hospital, protected_hospital_paths=[hospital])

if __name__ == "__main__":
    unittest.main()
